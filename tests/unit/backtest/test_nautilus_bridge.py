"""Unit and Real Integration Tests for NautilusTrader Catalog Exporter and Substrate Adapter Bridge (Phase 5).

Strictly enforces:
1. Real Runtime Execution: Executes live un-mocked NautilusTrader BacktestEngine and ParquetDataCatalog (@pytest.mark.nautilus).
2. Float-Free Nanosecond Precision: Timestamps are converted via extract_exact_nanoseconds().
3. Zero Silent Rounding & Decimal Preservation: Validates that every source Decimal is exactly representable, rejecting non-representable values with DataContractError.
4. Explicit TradeId Mapping Policy: REJECT_ON_NULL raises DataContractError; USE_CANONICAL_SOURCE_ORDER_KEY maps safely without fabrication.
5. Non-Empty Canonical Tables: Asserts non-empty PyArrow fills_table and equity_table emitted from real engine execution.
6. Proper Futures Contract Modeling: Uses real FuturesContract (ES.SIM) with index asset class and exact multiplier/lot.
7. Shadow Accounting Reconciliation: Asserts exact internal conservation (|residual| <= 10^-10) on live Nautilus fills.
8. Provenance & Reproducibility Evidence: Records exact Nautilus version, Python version, uv.lock hash, and git commit.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import importlib
from pathlib import Path
import tempfile
from typing import Any, Dict, List, Optional
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
from acash.backtest.schema import (
    CANONICAL_BACKTEST_FILLS_SCHEMA,
    CANONICAL_EQUITY_CURVE_SCHEMA,
    BacktestEngineConfig,
    BacktestManifest,
    load_current_environment_provenance,
)
from acash.data.schema import DataContractError


# Check if live nautilus_trader runtime is installed
try:
    importlib.import_module("nautilus_trader")
    HAS_NAUTILUS = True
except ImportError:
    HAS_NAUTILUS = False


def test_nautilus_catalog_exporter_bars_precision_and_nanoseconds() -> None:
    """Verifies that exported Bars catalog preserves exact integer nanoseconds and exact decimal prices without mutation."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cat_dir = Path(tmp_dir) / "catalog"
        exporter = NautilusCatalogExporter(catalog_root=cat_dir)

        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        bars_table = pa.Table.from_pydict({
            "timestamp_utc": [t0],
            "bar_start_utc": [t0],
            "open": [Decimal("5000.25")],
            "high": [Decimal("5005.75")],
            "low": [Decimal("4995.00")],
            "close": [Decimal("5002.50")],
            "volume": [Decimal("100.0")],
        })

        dest_file = exporter.export_bars_table(bars_table, symbol="ES", price_precision=2, size_precision=0)
        assert dest_file.exists()

        read_tbl = pq.read_table(dest_file)
        assert read_tbl["ts_event"][0].as_py() == 1768833000000000000
        assert read_tbl["ts_init"][0].as_py() == 1768833000000000000

        if HAS_NAUTILUS:
            data_mod = importlib.import_module("nautilus_trader.model.data")
            obj_mod = importlib.import_module("nautilus_trader.model.objects")
            cat_mod = importlib.import_module("nautilus_trader.persistence.catalog")

            BarType = getattr(data_mod, "BarType")
            Price = getattr(obj_mod, "Price")
            ParquetDataCatalog = getattr(cat_mod, "ParquetDataCatalog")

            cat = ParquetDataCatalog(str(cat_dir))
            loaded = cat.bars(bar_types=[BarType.from_str("ES.SIM-1-MINUTE-LAST-EXTERNAL")])
            assert len(loaded) == 1
            # Exact source values survived without numeric mutation
            assert loaded[0].open == Price.from_str("5000.25")
            assert loaded[0].close == Price.from_str("5002.50")


def test_nautilus_catalog_exporter_unrepresentable_precision_rejection() -> None:
    """Negative Test: Verifies that unrepresentable prices/quantities raise DataContractError instead of being silently rounded."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        exporter = NautilusCatalogExporter(catalog_root=Path(tmp_dir) / "catalog")
        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)

        # 1. Unrepresentable price (3 decimals when target instrument precision is 2)
        bars_bad_price = pa.Table.from_pydict({
            "timestamp_utc": [t0],
            "bar_start_utc": [t0],
            "open": [Decimal("5000.123")],  # 3 decimals cannot be represented at precision=2
            "high": [Decimal("5005.00")],
            "low": [Decimal("4995.00")],
            "close": [Decimal("5002.00")],
            "volume": [Decimal("100.0")],
        })
        with pytest.raises(DataContractError, match="cannot be exactly represented at target instrument price precision"):
            exporter.export_bars_table(bars_bad_price, symbol="ES", price_precision=2, size_precision=0)

        # 2. Unrepresentable volume (fractional volume when target size precision is 0)
        bars_bad_vol = pa.Table.from_pydict({
            "timestamp_utc": [t0],
            "bar_start_utc": [t0],
            "open": [Decimal("5000.25")],
            "high": [Decimal("5005.00")],
            "low": [Decimal("4995.00")],
            "close": [Decimal("5002.00")],
            "volume": [Decimal("100.75")],  # Fractional lot cannot be represented at size_precision=0
        })
        with pytest.raises(DataContractError, match="cannot be exactly represented at target instrument size precision"):
            exporter.export_bars_table(bars_bad_vol, symbol="ES", price_precision=2, size_precision=0)


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
        cat_map_dir = Path(tmp_dir) / "cat_map"
        exporter_map = NautilusCatalogExporter(
            catalog_root=cat_map_dir,
            trade_id_policy=TradeIdMappingPolicy.USE_CANONICAL_SOURCE_ORDER_KEY,
        )
        dest_file = exporter_map.export_trades_table(trades_table, symbol="ES")
        assert dest_file.exists()

        read_tbl = pq.read_table(dest_file)
        assert read_tbl["ts_event"][0].as_py() == 1768833000000000000

        if HAS_NAUTILUS:
            id_mod = importlib.import_module("nautilus_trader.model.identifiers")
            obj_mod = importlib.import_module("nautilus_trader.model.objects")
            cat_mod = importlib.import_module("nautilus_trader.persistence.catalog")

            InstrumentId = getattr(id_mod, "InstrumentId")
            Price = getattr(obj_mod, "Price")
            ParquetDataCatalog = getattr(cat_mod, "ParquetDataCatalog")

            cat = ParquetDataCatalog(str(cat_map_dir))
            loaded_ticks = cat.trade_ticks(instrument_ids=[InstrumentId.from_str("ES.SIM")])
            assert len(loaded_ticks) == 1
            assert str(loaded_ticks[0].trade_id) == "ORDKEY_00000000000000000100"
            assert loaded_ticks[0].price == Price.from_str("5000.25")


def test_nautilus_catalog_exporter_raises_on_native_write_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that native write failure strictly raises NautilusCatalogExportError when fallback is disallowed."""
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

        def mock_import(name: str) -> Any:
            if name == "nautilus_trader.persistence.catalog":
                class MockCatalog:
                    def __init__(self, *args: Any, **kwargs: Any) -> None: pass
                    def write_data(self, *args: Any, **kwargs: Any) -> None:
                        raise RuntimeError("Disk I/O failure")
                return type("Mod", (), {"ParquetDataCatalog": MockCatalog})
            return importlib.__import__(name)

        monkeypatch.setattr(importlib, "import_module", mock_import)

        with pytest.raises(NautilusCatalogExportError, match="Native Nautilus catalog write_data\\(\\) failed"):
            exporter.export_bars_table(bars_table, symbol="ES")


def test_nautilus_substrate_empty_catalog_rejection() -> None:
    """Verifies that running simulation on an empty catalog raises DataContractError."""
    if not HAS_NAUTILUS:
        pytest.skip("nautilus_trader runtime not installed in environment.")

    with tempfile.TemporaryDirectory() as tmp_dir:
        substrate = NautilusTraderSubstrate(config=BacktestEngineConfig(engine_id="BKT-EMPTY-TEST", symbol="ES"))
        with pytest.raises(DataContractError, match="contains 0 bars or ticks"):
            substrate.run_simulation(
                catalog_path=tmp_dir,
                hypothesis_spec_sha256="0" * 64,
                strategy_config_hash="0" * 64,
                pyproject_toml_sha256="0" * 64,
                git_commit_hash="a" * 40,
                canonical_data_hashes=["a" * 64],
            )



@pytest.mark.nautilus
@pytest.mark.skipif(not HAS_NAUTILUS, reason="Real Nautilus integration requires nautilus_trader package.")
def test_nautilus_substrate_real_unmocked_execution_lifecycle_and_non_empty_tables() -> None:
    """Invariant: Real, un-mocked NautilusTrader BacktestEngine execution producing real fills, non-empty tables, and Shadow Ledger zero residual."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        cat_dir = Path(tmp_dir) / "catalog"
        exporter = NautilusCatalogExporter(catalog_root=cat_dir)

        t0 = datetime(2026, 1, 19, 14, 30, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 1, 19, 14, 31, 0, tzinfo=timezone.utc)

        bars_table = pa.Table.from_pydict({
            "timestamp_utc": [t0, t1],
            "bar_start_utc": [t0, t1],
            "open": [Decimal("5000.00"), Decimal("5002.00")],
            "high": [Decimal("5005.00"), Decimal("5010.00")],
            "low": [Decimal("4995.00"), Decimal("5000.00")],
            "close": [Decimal("5002.00"), Decimal("5008.00")],
            "volume": [Decimal("100.0"), Decimal("100.0")],
        })

        # 1. Export canonical table to Nautilus Parquet catalog
        exporter.export_bars_table(bars_table, symbol="ES", price_precision=2, size_precision=0)

        # 2. Instantiate and run real NautilusTraderSubstrate
        config = BacktestEngineConfig(
            engine_id="BKT-REAL-NAUTILUS",
            symbol="ES",
            initial_cash=Decimal("100000.00"),
            base_currency="USD",
        )
        substrate = NautilusTraderSubstrate(config=config)

        # Provenance metadata
        pyproject_sha, uv_lock_sha, git_commit = load_current_environment_provenance()
        valid_sha = "a" * 64
        data_sha = "b" * 64

        assert substrate.nautilus_version == "1.231.0"
        assert substrate.python_version.startswith("3.")

        manifest, fills_table, equity_table = substrate.run_simulation(
            catalog_path=cat_dir,
            hypothesis_spec_sha256=valid_sha,
            strategy_config_hash=valid_sha,
            canonical_data_hashes=[data_sha],
            pyproject_toml_sha256=pyproject_sha,
            uv_lock_sha256=uv_lock_sha,
            git_commit_hash=git_commit,
        )


        # 3. Assertions proving real execution
        assert manifest is not None
        assert manifest.execution_summary.total_fills == 1
        assert manifest.pyproject_toml_sha256 == pyproject_sha
        assert manifest.uv_lock_sha256 == uv_lock_sha
        assert manifest.git_commit_hash == git_commit

        # Assert non-empty canonical Arrow tables emitted
        assert fills_table.num_rows == 1
        assert equity_table.num_rows == 2
        pydict_eq = equity_table.to_pydict()
        assert pydict_eq["unrealized_pnl"][0] == Decimal("0.0")
        assert pydict_eq["unrealized_pnl"][1] == Decimal("300.0")
        assert pydict_eq["margin_utilized"][1] == Decimal("25040.0")

        # Check fill details
        pydict_fills = fills_table.to_pydict()
        assert pydict_fills["symbol"][0] == "ES.SIM"
        assert pydict_fills["side"][0] == "BUY"
        assert pydict_fills["fill_price"][0] == Decimal("5002.00")
        assert pydict_fills["fill_qty"][0] == Decimal("1")


        # 4. Assert exact double-entry internal conservation on real fills
        substrate.shadow_ledger.verify_internal_conservation()
        assert substrate.shadow_ledger.calculate_balance_sheet_equity() == manifest.execution_summary.ending_equity
