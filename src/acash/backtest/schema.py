"""Canonical Schema, Models, and Arrow Table Definitions for Backtesting Substrate (Phase 5).

Maintains strict deterministic content-derived manifest identities, dual-view double-entry accounting schemas,
and reality-gap execution telemetry models.
"""

from decimal import Decimal
from enum import Enum
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import pyarrow as pa

from pydantic import BaseModel, ConfigDict, Field

from acash.data.schema import DataContractError



class OrderType(str, Enum):
    """Supported order execution types in simulation."""

    LIMIT = "LIMIT"
    MARKET = "MARKET"
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill
    GTC = "GTC"  # Good 'til Cancelled


class BacktestOrderStatus(str, Enum):
    """Deterministic order lifecycle states."""

    CREATED = "CREATED"
    SUBMITTED = "SUBMITTED"
    ACCEPTED = "ACCEPTED"
    PARTIALLY_FILLED = "PARTIALLY_FILLED"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"
    EXPIRED = "EXPIRED"


class LiquidityType(str, Enum):
    """Execution liquidity role."""

    MAKER = "MAKER"
    TAKER = "TAKER"


class SimulationLatencyConfig(BaseModel):
    """Dual-sided simulation latency decomposition parameters in nanoseconds."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    signal_calc_latency_ns: int = Field(default=0, ge=0, description="Feature calculation to decision delay.")
    uplink_latency_ns: int = Field(default=0, ge=0, description="Client to simulated exchange gateway transit wire delay.")
    matching_engine_latency_ns: int = Field(default=0, ge=0, description="Internal exchange matching queue serialization delay.")
    downlink_latency_ns: int = Field(default=0, ge=0, description="Execution report ack downlink transit wire delay.")

    def total_roundtrip_latency_ns(self) -> int:
        """Calculate total roundtrip execution notification latency."""
        return (
            self.signal_calc_latency_ns
            + self.uplink_latency_ns
            + self.matching_engine_latency_ns
            + self.downlink_latency_ns
        )

    def total_match_latency_ns(self) -> int:
        """Calculate latency from decision timestamp to matching engine execution."""
        return self.signal_calc_latency_ns + self.uplink_latency_ns + self.matching_engine_latency_ns


class FeeModelConfig(BaseModel):
    """Trading venue fee schedule configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    maker_fee_bps: Decimal = Field(default=Decimal("0.0"), description="Maker rebate/fee in basis points.")
    taker_fee_bps: Decimal = Field(default=Decimal("1.0"), ge=Decimal("0.0"), description="Taker fee in basis points.")
    fixed_fee_per_trade: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Fixed dollar ticket fee per execution.")


class SlippageModelConfig(BaseModel):
    """Execution slippage and market impact configuration."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fixed_slippage_bps: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Constant fixed slippage proxy in bps.")
    impact_coefficient: Decimal = Field(default=Decimal("0.0"), ge=Decimal("0.0"), description="Linear depth impact coefficient.")


class BacktestEngineConfig(BaseModel):
    """Complete parameter specification for event backtesting substrate."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    engine_id: str = Field(description="Unique configuration identifier.")
    symbol: str = Field(description="Target trading instrument.")
    initial_cash: Decimal = Field(default=Decimal("100000.00"), gt=Decimal("0.0"), description="Starting cash allocation.")
    base_currency: str = Field(default="USD", description="Base accounting currency.")
    latency_config: SimulationLatencyConfig = Field(default_factory=SimulationLatencyConfig)
    fee_config: FeeModelConfig = Field(default_factory=FeeModelConfig)
    slippage_config: SlippageModelConfig = Field(default_factory=SlippageModelConfig)
    queue_priority_model: str = Field(default="FIFO", description="Order book queue priority matching model.")
    prng_seed: int = Field(default=42, description="Deterministic pseudo-random number generator seed.")

    def to_canonical_json(self) -> str:
        """Emit deterministic, sorted JSON representation for cryptographic hashing."""
        data = {
            "engine_id": self.engine_id,
            "symbol": self.symbol,
            "initial_cash": str(self.initial_cash),
            "base_currency": self.base_currency,
            "latency_config": self.latency_config.model_dump(),
            "fee_config": {
                "maker_fee_bps": str(self.fee_config.maker_fee_bps),
                "taker_fee_bps": str(self.fee_config.taker_fee_bps),
                "fixed_fee_per_trade": str(self.fee_config.fixed_fee_per_trade),
            },
            "slippage_config": {
                "fixed_slippage_bps": str(self.slippage_config.fixed_slippage_bps),
                "impact_coefficient": str(self.slippage_config.impact_coefficient),
            },
            "queue_priority_model": self.queue_priority_model,
            "prng_seed": self.prng_seed,
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))

    def compute_sha256(self) -> str:
        """Compute deterministic SHA-256 fingerprint."""
        return hashlib.sha256(self.to_canonical_json().encode("utf-8")).hexdigest()


class BacktestFillRecord(BaseModel):
    """Sovereign record of an individual simulated order execution."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    fill_id: str
    order_id: str
    symbol: str
    fill_timestamp_utc: str
    side: str
    fill_price: Decimal
    fill_qty: Decimal
    fee_paid: Decimal
    liquidity_type: LiquidityType
    slippage_incurred_bps: Decimal


class BacktestExecutionSummary(BaseModel):
    """Aggregate execution and portfolio performance summary."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    total_orders: int
    total_fills: int
    total_volume_traded: Decimal
    total_fees_paid: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    ending_equity: Decimal
    net_return_pct: Decimal
    sharpe_ratio: Optional[Decimal] = None
    sortino_ratio: Optional[Decimal] = None
    max_drawdown_pct: Decimal
    win_rate_pct: Decimal
    profit_factor: Optional[Decimal] = None


class RealityGapSummary(BaseModel):
    """Empirical reality gap decomposition metrics comparing analytical assumption to simulated realization."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    phase4_analytical_edge_bps: Decimal
    phase5_simulated_realized_bps: Decimal
    reality_gap_bps: Decimal
    spread_drag_bps: Decimal
    latency_slip_drag_bps: Decimal
    queue_position_drag_bps: Decimal


class BacktestManifest(BaseModel):
    """Immutable, content-derived provenance manifest for Phase 5 backtesting runs."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    manifest_id: str = Field(description="Deterministic 32-character content-derived hash.")
    manifest_version: str = Field(default="1.0.0")
    hypothesis_id: str
    hypothesis_spec_sha256: str
    canonical_data_hashes: List[str]
    engine_config_hash: str
    strategy_config_hash: str
    prng_seed: int
    pyproject_toml_sha256: str
    uv_lock_sha256: Optional[str] = None
    git_commit_hash: str
    execution_summary: BacktestExecutionSummary
    reality_gap: RealityGapSummary
    # Auxiliary runtime metadata (MUST NEVER participate in manifest_id or reproducibility hash)
    computed_at_utc: str
    wall_clock_duration_ms: int

    def model_post_init(self, __context: Any) -> None:
        """Validate that environment hashes are valid cryptographic fingerprints, not placeholders."""
        if not self.pyproject_toml_sha256 or len(self.pyproject_toml_sha256) < 32 or "pinned_" in self.pyproject_toml_sha256:
            raise DataContractError(
                f"Invalid pyproject_toml_sha256 fingerprint: '{self.pyproject_toml_sha256}'. "
                "Placeholder or invalid hashes are strictly forbidden for pinned reproducibility."
            )
        if not self.git_commit_hash or len(self.git_commit_hash) < 7 or "current_git" in self.git_commit_hash:
            raise DataContractError(
                f"Invalid git_commit_hash: '{self.git_commit_hash}'. "
                "Placeholder or invalid git commits are strictly forbidden for pinned reproducibility."
            )
        if self.uv_lock_sha256 is not None and ("pinned_" in self.uv_lock_sha256 or len(self.uv_lock_sha256) < 32):
            raise DataContractError(
                f"Invalid uv_lock_sha256 fingerprint: '{self.uv_lock_sha256}'."
            )


    def to_canonical_json(self) -> str:
        """Emit canonical JSON excluding volatile runtime metadata."""
        data = {
            "manifest_id": self.manifest_id,
            "manifest_version": self.manifest_version,
            "hypothesis_id": self.hypothesis_id,
            "hypothesis_spec_sha256": self.hypothesis_spec_sha256,
            "canonical_data_hashes": sorted(self.canonical_data_hashes),
            "engine_config_hash": self.engine_config_hash,
            "strategy_config_hash": self.strategy_config_hash,
            "prng_seed": self.prng_seed,
            "pyproject_toml_sha256": self.pyproject_toml_sha256,
            "uv_lock_sha256": self.uv_lock_sha256,
            "git_commit_hash": self.git_commit_hash,
            "execution_summary": {
                "total_orders": self.execution_summary.total_orders,
                "total_fills": self.execution_summary.total_fills,
                "total_volume_traded": str(self.execution_summary.total_volume_traded),
                "total_fees_paid": str(self.execution_summary.total_fees_paid),
                "realized_pnl": str(self.execution_summary.realized_pnl),
                "unrealized_pnl": str(self.execution_summary.unrealized_pnl),
                "ending_equity": str(self.execution_summary.ending_equity),
                "net_return_pct": str(self.execution_summary.net_return_pct),
                "sharpe_ratio": str(self.execution_summary.sharpe_ratio) if self.execution_summary.sharpe_ratio is not None else None,
                "sortino_ratio": str(self.execution_summary.sortino_ratio) if self.execution_summary.sortino_ratio is not None else None,
                "max_drawdown_pct": str(self.execution_summary.max_drawdown_pct),
                "win_rate_pct": str(self.execution_summary.win_rate_pct),
                "profit_factor": str(self.execution_summary.profit_factor) if self.execution_summary.profit_factor is not None else None,
            },
            "reality_gap": {
                "phase4_analytical_edge_bps": str(self.reality_gap.phase4_analytical_edge_bps),
                "phase5_simulated_realized_bps": str(self.reality_gap.phase5_simulated_realized_bps),
                "reality_gap_bps": str(self.reality_gap.reality_gap_bps),
                "spread_drag_bps": str(self.reality_gap.spread_drag_bps),
                "latency_slip_drag_bps": str(self.reality_gap.latency_slip_drag_bps),
                "queue_position_drag_bps": str(self.reality_gap.queue_position_drag_bps),
            },
        }
        return json.dumps(data, sort_keys=True, separators=(",", ":"))


def calculate_backtest_manifest_id(
    hypothesis_spec_sha256: str,
    canonical_data_hashes: List[str],
    engine_config_hash: str,
    strategy_config_hash: str,
    prng_seed: int,
) -> str:
    """Calculate deterministic 32-character content-derived manifest ID.

    Ensures rerun of identical inputs produces identical manifest ID.
    Volatile runtime timestamps are strictly excluded.
    """
    sorted_data_hashes = sorted(canonical_data_hashes)
    payload = {
        "hypothesis_spec_sha256": hypothesis_spec_sha256,
        "canonical_data_hashes": sorted_data_hashes,
        "engine_config_hash": engine_config_hash,
        "strategy_config_hash": strategy_config_hash,
        "prng_seed": prng_seed,
    }
    canonical_str = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical_str.encode("utf-8")).hexdigest()[:32]


# -------------------------------------------------------------------------
# PyArrow Canonical Schemas for Event-Driven Backtesting
# -------------------------------------------------------------------------

CANONICAL_BACKTEST_FILLS_SCHEMA = pa.schema(
    [
        pa.field("fill_id", pa.utf8(), nullable=False),
        pa.field("order_id", pa.utf8(), nullable=False),
        pa.field("symbol", pa.utf8(), nullable=False),
        pa.field("fill_timestamp_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
        pa.field("side", pa.utf8(), nullable=False),
        pa.field("fill_price", pa.decimal128(38, 18), nullable=False),
        pa.field("fill_qty", pa.decimal128(38, 18), nullable=False),
        pa.field("fee_paid", pa.decimal128(38, 18), nullable=False),
        pa.field("liquidity_type", pa.utf8(), nullable=False),
        pa.field("slippage_incurred_bps", pa.decimal128(38, 18), nullable=False),
    ]
)

CANONICAL_EQUITY_CURVE_SCHEMA = pa.schema(
    [
        pa.field("timestamp_utc", pa.timestamp("ns", tz="UTC"), nullable=False),
        pa.field("cash_balance", pa.decimal128(38, 18), nullable=False),
        pa.field("realized_pnl", pa.decimal128(38, 18), nullable=False),
        pa.field("unrealized_pnl", pa.decimal128(38, 18), nullable=False),
        pa.field("total_equity", pa.decimal128(38, 18), nullable=False),
        pa.field("margin_utilized", pa.decimal128(38, 18), nullable=False),
        pa.field("accounting_residual", pa.decimal128(38, 18), nullable=False),
    ]
)


def load_current_environment_provenance(
    workspace_root: Optional[Union[str, Path]] = None,
) -> Tuple[str, Optional[str], str]:
    """Load exact SHA-256 fingerprints of pyproject.toml, uv.lock, and Git HEAD commit."""
    root = Path(workspace_root) if workspace_root else Path(__file__).resolve().parent.parent.parent.parent

    # 1. pyproject.toml hash
    pyproject_path = root / "pyproject.toml"
    if not pyproject_path.exists():
        raise DataContractError(f"pyproject.toml not found at {pyproject_path}")
    pyproject_sha256 = hashlib.sha256(pyproject_path.read_bytes()).hexdigest()

    # 2. uv.lock hash
    uv_lock_path = root / "uv.lock"
    uv_lock_sha256 = hashlib.sha256(uv_lock_path.read_bytes()).hexdigest() if uv_lock_path.exists() else None

    # 3. git commit hash
    git_head_path = root / ".git" / "HEAD"
    git_commit = "0000000000000000000000000000000000000000"
    if git_head_path.exists():
        content = git_head_path.read_text(encoding="utf-8").strip()
        if content.startswith("ref:"):
            ref_rel = content[4:].strip()
            ref_path = root / ".git" / ref_rel
            if ref_path.exists():
                git_commit = ref_path.read_text(encoding="utf-8").strip()
            else:
                # Packed refs or detached HEAD fallback
                packed_refs_path = root / ".git" / "packed-refs"
                if packed_refs_path.exists():
                    for line in packed_refs_path.read_text(encoding="utf-8").splitlines():
                        if line and not line.startswith("#") and ref_rel in line:
                            git_commit = line.split()[0]
                            break
        else:
            git_commit = content

    return pyproject_sha256, uv_lock_sha256, git_commit

