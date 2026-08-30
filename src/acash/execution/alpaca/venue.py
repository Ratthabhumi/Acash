"""Typed Alpaca venue configuration (8F-2: Concrete Alpaca Paper Transport).

Replaces the free-form ``base_url: str`` endpoint with a **typed venue** whose
base URL is *derived*, never caller-injected. A caller therefore cannot construct
an ``AlpacaEndpoint`` pointing at an arbitrary host and hope the venue semantics
are right; the endpoint is bound to a fixed, named Alpaca domain (paper vs live)
at construction time.

This directly implements the locked requirement:

$$\boxed{\text{typed venue config, not free URL string}}$$

and the cross-venue separation (paper adapter -> live, paper credential -> live,
live credential -> paper) by making the venue an explicit, single-source enum that
both the credential provider and the transport must agree on.
"""

from dataclasses import dataclass
from enum import Enum

from acash.execution.alpaca.credentials import LIVE_API_HOST, PAPER_API_HOST


class AlpacaVenue(str, Enum):
    """Named Alpaca trading venue. The single source of host/paper-live semantics.

    ``base_url`` is always *derived* from the venue — it cannot be overridden by a
    caller with a free URL string. ``ALPACA_PAPER`` maps to the paper domain and
    ``ALPACA_LIVE`` to the live domain (BMAP-10: distinct domains & key sets).
    """

    PAPER = "ALPACA_PAPER"
    LIVE = "ALPACA_LIVE"

    @property
    def host(self) -> str:
        """Fixed Alpaca API host for this venue (paper vs live)."""
        if self is AlpacaVenue.PAPER:
            return PAPER_API_HOST
        return LIVE_API_HOST

    @property
    def is_paper(self) -> bool:
        """True for the sandbox/paper venue only."""
        return self is AlpacaVenue.PAPER

    @property
    def base_url(self) -> str:
        """REST/trading base URL derived from the venue (never injected)."""
        return f"https://{self.host}/v2"


@dataclass(frozen=True)
class AlpacaEndpoint:
    """The concrete network endpoint a transport binds to (typed venue).

    Carries the named ``AlpacaVenue``; ``base_url``/``is_paper`` are derived
    properties, so there is no free-form URL surface to misconfigure.
    """

    venue: AlpacaVenue

    @property
    def base_url(self) -> str:
        return self.venue.base_url

    @property
    def is_paper(self) -> bool:
        return self.venue.is_paper

    @property
    def host(self) -> str:
        return self.venue.host


def paper_endpoint() -> AlpacaEndpoint:
    """Convenience factory: a paper-only endpoint (default for the paper phase)."""
    return AlpacaEndpoint(venue=AlpacaVenue.PAPER)


def live_endpoint() -> AlpacaEndpoint:
    """Factory for the live endpoint (explicitly opted into; not the default)."""
    return AlpacaEndpoint(venue=AlpacaVenue.LIVE)
