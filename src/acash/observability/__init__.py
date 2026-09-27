"""CORE-001 read-only observability boundary.

This package DERIVES presentation from canonical evidence. It NEVER creates
authority, mutates state, accesses the network, or touches credentials.
All reads use ``Path.read_text``; no write/truncate/rename/delete call may
exist in this package (enforced by unit test).
"""
