"""Unit tests for NautilusTrader Catalog Exporter and Substrate Adapter Bridge (Phase 5).

Verifies:
1. Float-Free Nanosecond Precision: Timestamps are converted via extract_exact_nanoseconds().
2. Decimal Precision Preservation: Prices and quantities are preserved exactly in exported Parquet catalogs.
3. Explicit TradeId Mapping Policy: REJECT_ON_NULL raises DataContractError; USE_CANONICAL_SOURCE_ORDER_KEY maps safely without fabrication.
4. Transparent Error Policy: Native write failures raise NautilusCatalogExportError when fallback is disabled.
5. Substrate Runtime Check: Raises SubstrateRuntimeUnavailableError when nautilus_trader is not installed.
6. Full Substrate Execution Lifecycle & Shadow Accounting: Proves complete execution wiring (venue, instrument, catalog data, strategy, fills, ledger reconciliation).
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import importlib
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional
from unittest.mock import MagicMock, patch
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from acash.backtest.accounting import ACCOUNTING_TOLERANCE, ShadowAccountingLedger
from acash.backtest.nautilus_bridge import (
    ACASHNativeBacktestEngine,
    NautilusCatalogExportError,
    NautilusCatalogExporter,
    NautilusTraderSubstrate,
    SubstrateRuntimeUnavailableError,
    TradeIdMappingPolicy,
)
from acash.backtest.schema import BacktestEngineConfig, BacktestManifest
from acash.data.schema import DataContractError


def test_nautilus_catalog_exporter_bars_precision_and_nanoseconds() -> None:
    """Verifies that exported Bars catalog preserves exact integer nanoseconds and exact decimal prices."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        exporter = NautilusCatalogExporter(catalog_root=Path(tmp_dir) / "catalog")

        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        bars_table = pa.Table.from_pydict({
            "timestamp_utc": [t0],
            "bar_start_utc": [t0],
            "open": [Decimal("5000.123456789012345678")],
            "high": [Decimal("5005.987654321098765432")],
            "low": [Decimal("4995.000000000000000001")],
            "close": [Decimal("5002.555555555555555555")],
            "volume": [Decimal("100.123456789012345678")],
        })

        dest_file = exporter.export_bars_table(bars_table, symbol="ES")
        assert dest_file.exists()

        read_tbl = pq.read_table(dest_file)
        assert read_tbl["ts_event"][0].as_py() == 1768833000000000000
        assert read_tbl["ts_init"][0].as_py() == 1768833000000000000
        assert read_tbl["open"][0].as_py() == Decimal("5000.123456789012345678")
        assert read_tbl["close"][0].as_py() == Decimal("5002.555555555555555555")


def test_nautilus_catalog_exporter_trades_policy_and_non_fabrication() -> None:
    """Verifies that TradeIdMappingPolicy strictly manages nullable trade_id without fabrication."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        trades_table = pa.Table.from_pydict({
            "exchange_time_utc": pa.array([t0], type=pa.timestamp("ns", tz="UTC")),
            "source_order_key": ["00000000000000000100"],
            "trade_id": pa.array([None], type=pa.string()),
            "price": [Decimal("5000.25")],
            "size": [Decimal("10.0")],
            "aggressor_side": ["BUY"],
        })

        # 1. REJECT_ON_NULL raises DataContractError
        exporter_reject = NautilusCatalogExporter(
            catalog_root=Path(tmp_dir) / "cat_reject",
            trade_id_policy=TradeIdMappingPolicy.REJECT_ON_NULL,
        )
        with pytest.raises(DataContractError, match="Null trade_id cannot be exported"):
            exporter_reject.export_trades_table(trades_table, symbol="ES")

        # 2. USE_CANONICAL_SOURCE_ORDER_KEY maps explicitly to ORDKEY_...
        exporter_map = NautilusCatalogExporter(
            catalog_root=Path(tmp_dir) / "cat_map",
            trade_id_policy=TradeIdMappingPolicy.USE_CANONICAL_SOURCE_ORDER_KEY,
        )
        dest_file = exporter_map.export_trades_table(trades_table, symbol="ES")
        assert dest_file.exists()

        read_tbl = pq.read_table(dest_file)
        assert read_tbl["trade_id"][0].as_py() == "ORDKEY_00000000000000000100"
        assert read_tbl["ts_event"][0].as_py() == 1768833000000000000


def test_nautilus_catalog_exporter_raises_on_native_write_failure() -> None:
    """Verifies that native write failure raises NautilusCatalogExportError when fallback is disabled."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        exporter = NautilusCatalogExporter(
            catalog_root=Path(tmp_dir) / "catalog",
            allow_custom_arrow_fallback=False,
        )
        exporter._has_nautilus = True

        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        bars_table = pa.Table.from_pydict({
            "timestamp_utc": [t0],
            "bar_start_utc": [t0],
            "open": [Decimal("5000.00")],
            "high": [Decimal("5005.00")],
            "low": [Decimal("4995.00")],
            "close": [Decimal("5002.00")],
            "volume": [Decimal("100.0")],
        })

        with patch("importlib.import_module", side_effect=RuntimeError("Simulated native write corruption")):
            with pytest.raises(NautilusCatalogExportError, match="Native Nautilus catalog write_data"):
                exporter.export_bars_table(bars_table, symbol="ES")


def test_nautilus_substrate_runtime_unavailable_in_unsupported_environment() -> None:
    """Verifies that NautilusTraderSubstrate raises SubstrateRuntimeUnavailableError when runtime is absent."""
    substrate = NautilusTraderSubstrate()
    substrate._has_runtime = False

    with pytest.raises(SubstrateRuntimeUnavailableError, match="NautilusTrader runtime package"):
        substrate.run_simulation(
            catalog_path="dummy_catalog",
            hypothesis_spec_sha256="0" * 64,
            strategy_config_hash="0" * 64,
            pyproject_toml_sha256="0" * 64,
            git_commit_hash="a" * 40,
        )


class MockFillRow:
    """Mock Nautilus fill report row."""
    def __init__(self, instrument_id: str, side: str, last_px: str, last_qty: str, commission: str) -> None:
        self.instrument_id = instrument_id
        self.side = side
        self.last_px = last_px
        self.last_qty = last_qty
        self.commission = commission


class MockNautilusBaseStrategy:
    """Mock Nautilus Strategy base class."""
    def __init__(self, config: Any) -> None:
        self.config = config
        self.order_factory = MagicMock()

    def subscribe_bars(self, bar_type: Any) -> None:
        pass

    def submit_order(self, order: Any) -> None:
        pass


def test_nautilus_substrate_full_execution_lifecycle_and_shadow_ledger_reconciliation() -> None:
    """Verifies the complete execution wiring: Engine Config -> Venue -> Instrument -> Data -> Strategy -> Run -> Fills -> Shadow Ledger."""
    config = BacktestEngineConfig(
        engine_id="BKT-TEST-NAUTILUS",
        symbol="ES.FUT",
        initial_cash=Decimal("100000.00"),
    )
    substrate = NautilusTraderSubstrate(config=config)
    substrate._has_runtime = True

    # Mock Nautilus components
    mock_engine = MagicMock()
    mock_catalog = MagicMock()
    mock_catalog.bars.return_value = ["mock_bar_1", "mock_bar_2"]
    mock_catalog.trade_ticks.return_value = []

    mock_fills = [
        MockFillRow("ES.FUT.SIM", "BUY", "5000.00", "2.0", "1.50"),
        MockFillRow("ES.FUT.SIM", "SELL", "5010.00", "2.0", "1.50"),
    ]
    mock_engine.trader.generate_order_fills_report.return_value = mock_fills

    mock_modules: Dict[str, Any] = {
        "nautilus_trader.backtest.engine": MagicMock(
            BacktestEngine=MagicMock(return_value=mock_engine),
            BacktestEngineConfig=MagicMock(),
        ),
        "nautilus_trader.config": MagicMock(BacktestVenueConfig=MagicMock()),
        "nautilus_trader.model.identifiers": MagicMock(
            TraderId=MagicMock(),
            InstrumentId=MagicMock(),
        ),
        "nautilus_trader.model.objects": MagicMock(
            Currency=MagicMock(from_str=MagicMock()),
            Money=MagicMock(from_str=MagicMock()),
            Quantity=MagicMock(from_str=MagicMock()),
        ),
        "nautilus_trader.persistence.catalog": MagicMock(
            ParquetDataCatalog=MagicMock(return_value=mock_catalog),
        ),
        "nautilus_trader.model.data": MagicMock(
            BarType=MagicMock(from_str=MagicMock()),
        ),
        "nautilus_trader.trading.strategy": MagicMock(
            Strategy=MockNautilusBaseStrategy,
            StrategyConfig=MagicMock(),
        ),
        "nautilus_trader.test_kit.providers": MagicMock(
            TestInstrumentProvider=MagicMock(default_fx_ccy=MagicMock(return_value="mock_instrument")),
        ),
        "nautilus_trader.model.enums": MagicMock(
            OrderSide=MagicMock(BUY="BUY", SELL="SELL"),
        ),
    }

    def custom_import(name: str, *args: Any, **kwargs: Any) -> Any:
        if name in mock_modules:
            return mock_modules[name]
        return importlib.__import__(name, *args, **kwargs)

    with patch("importlib.import_module", side_effect=custom_import):
        manifest, fills_tbl, equity_tbl = substrate.run_simulation(
            catalog_path="data/catalog",
            hypothesis_spec_sha256="0" * 64,
            strategy_config_hash="0" * 64,
            pyproject_toml_sha256="0" * 64,
            git_commit_hash="a" * 40,
        )

        # 1. Assert Engine lifecycle methods were called
        mock_engine.add_venue.assert_called_once()
        mock_engine.add_instrument.assert_called_once_with("mock_instrument")
        mock_engine.add_data.assert_called_once_with(["mock_bar_1", "mock_bar_2"])
        mock_engine.add_strategy.assert_called_once()
        mock_engine.run.assert_called_once()

        # 2. Assert Shadow Accounting Ledger re-accounted fills correctly
        # Bought 2 @ 5000 (fee 1.50) -> Sold 2 @ 5010 (fee 1.50)
        # Gross Realized PnL = (5010 - 5000)*2 = 20.00, Fees = 3.00, Net Equity = 100000 + 20 - 3 = 100017.00
        assert substrate.shadow_ledger.cumulative_realized_pnl == Decimal("20.00")
        assert substrate.shadow_ledger.cumulative_fees_paid == Decimal("3.00")
        assert substrate.shadow_ledger.calculate_balance_sheet_equity() == Decimal("100017.00")


        # 3. Assert exact double-entry internal conservation
        substrate.shadow_ledger.verify_internal_conservation()

        # 4. Assert Manifest accurately records execution summary
        assert manifest.execution_summary.total_fills == 2
        assert manifest.execution_summary.realized_pnl == Decimal("20.00")
        assert manifest.execution_summary.total_fees_paid == Decimal("3.00")
        assert manifest.execution_summary.ending_equity == Decimal("100017.00")

