"""Entry point for ``python -m acash.paper`` (E3.5 operational CLI)."""

from __future__ import annotations

from acash.paper.cli import main

if __name__ == "__main__":
    raise SystemExit(main())