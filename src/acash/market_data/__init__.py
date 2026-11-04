"""Outbound market-data HTTP adapters, kept outside ``acash.invest`` and ``acash.dashboard_api``.

Those packages are network-free by test-enforced policy; this package is the only place the
market-data refresh opens HTTPS connections, and only to the fixed allowlist in ``providers``.
"""
