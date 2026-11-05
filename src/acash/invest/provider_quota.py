"""Per-provider request/credit budgets (declared, reserved before use, persisted privately).

Endpoints differ in cost: one Twelve Data request can consume several credits, so a request is never
assumed to equal one unit. The ledger reserves before a call and records actual usage after it; a
provider with no verified entitlement is refused rather than silently allowed.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from acash.core.domain.exceptions import DataContractError

SCHEMA = "ACASH_PROVIDER_QUOTA_V1"
DEFAULT_PATH = Path("data/private/provider_quota.json")

#: Declared limits per provider. ``per_day`` is the ACASH budget, not the provider's full allowance.
BUDGETS: Dict[str, Dict[str, Any]] = {
    "MASSIVE_BASIC": {"per_minute": 5, "per_day": None, "credit_weight": 1,
                      "note": "Stocks Basic: 5 requests/minute; no published daily cap."},
    "TWELVE_DATA_BASIC": {"per_minute": 8, "per_day": 800, "credit_weight": "ENDPOINT_DEPENDENT",
                          "acash_daily_budget": 100,
                          "note": "8 credits/minute, 800/day; a request may cost several credits."},
    "ALPHA_VANTAGE_FREE": {"per_minute": 5, "per_day": 25, "credit_weight": 1,
                           "acash_daily_budget": 3,
                           "note": "25 requests/day; ACASH reserves at most 3/day, no polling."},
    "BOT_REFERENCE_FX": {"per_minute": 200, "per_day": None, "credit_weight": 1,
                         "note": "200 calls/hour product limit."},
}


def _today(now: Optional[datetime] = None) -> str:
    return (now or datetime.now(timezone.utc)).date().isoformat()


@dataclass
class QuotaLedger:
    path: Path = DEFAULT_PATH
    clock: Any = None

    def _now(self) -> datetime:
        return self.clock() if self.clock else datetime.now(timezone.utc)

    def load(self) -> Dict[str, Any]:
        if not self.path.is_file():
            return {"schema": SCHEMA, "day": _today(self._now()), "providers": {}}
        try:
            doc = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            raise DataContractError("QUOTA_LEDGER_UNREADABLE.") from None
        if doc.get("schema") != SCHEMA:
            raise DataContractError("QUOTA_LEDGER_SCHEMA_MISMATCH.")
        typed: Dict[str, Any] = doc
        return typed

    def _state(self, doc: Dict[str, Any], provider_id: str) -> Dict[str, Any]:
        day = _today(self._now())
        if doc.get("day") != day:
            doc["day"] = day
            doc["providers"] = {}
        budget = BUDGETS.get(provider_id)
        if budget is None:
            raise DataContractError(f"QUOTA_PROVIDER_UNKNOWN: {provider_id}.")
        providers: Dict[str, Any] = doc["providers"]
        state: Dict[str, Any] = providers.setdefault(provider_id, {"used": 0, "requests": 0})
        return state

    def remaining(self, provider_id: str) -> Dict[str, Any]:
        doc = self.load()
        state = self._state(doc, provider_id)
        budget = BUDGETS[provider_id]
        limit = budget.get("acash_daily_budget") or budget.get("per_day")
        return {"provider_id": provider_id, "used": state["used"], "requests": state["requests"],
                "limit": limit, "remaining": None if limit is None else max(0, int(limit) - int(state["used"]))}

    def reserve(self, provider_id: str, cost: int = 1) -> Dict[str, Any]:
        """Reserve budget before a call; refuse when the declared daily budget is exhausted."""
        if cost < 1:
            raise DataContractError("QUOTA_COST_INVALID.")
        doc = self.load()
        state = self._state(doc, provider_id)
        budget = BUDGETS[provider_id]
        limit = budget.get("acash_daily_budget") or budget.get("per_day")
        if limit is not None and state["used"] + cost > int(limit):
            raise DataContractError(f"QUOTA_EXHAUSTED: {provider_id}.")
        state["used"] += cost
        state["requests"] += 1
        payload = (json.dumps(doc, indent=2, sort_keys=True) + "\n").encode("utf-8")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        handle, temporary = tempfile.mkstemp(dir=str(self.path.parent), prefix=self.path.name, suffix=".tmp")
        try:
            with os.fdopen(handle, "wb") as out:
                out.write(payload)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temporary, self.path)
        except BaseException:
            Path(temporary).unlink(missing_ok=True)
            raise
        return {"provider_id": provider_id, "reserved": cost, **self.remaining(provider_id)}


def budgets() -> Dict[str, Any]:
    return {provider: dict(values) for provider, values in BUDGETS.items()}
