"""Framework doctor: ADAPTER / NATIVE / SMOKE / QUALIFIED / PRODUCTION per framework."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from acash.integrations.framework_integration import acceptance_matrix  # noqa: E402


def main() -> int:
    print(json.dumps(acceptance_matrix(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
