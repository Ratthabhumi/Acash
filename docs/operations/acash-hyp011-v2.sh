#!/bin/bash
# acash-hyp011-v2 wrapper script
# Version: V2 Deployment Preparation (not activated)
# Generated from canonical repository at research/hyp011-v2-activation-prep

set -euo pipefail

# ==============================================================================
# V2 RUNTIME CONFIGURATION — EDIT WITH AUTHORIZATION ONLY
# ==============================================================================

# Canonical repository path (immutable-ish deployment checkout)
ACASH_REPO="/home/mew/Acash"

# V2 external mutable state root (NOT in git working tree)
STATE_ROOT="/var/lib/acash/hyp011/v2"

# Explicit supported Python interpreter (pinned per CI matrix + locked deps)
PYTHON_BIN="${ACASH_REPO}/.venv/bin/python"

# Secrets file (separate from state, 0600 perms)
SECRETS_FILE="/etc/acash/hyp011-v2.env"

# Segment identity (V2 fresh segment)
SEGMENT_ID="HYP_011_PROSPECTIVE_V2"

# ==============================================================================
# VALIDATION
# ==============================================================================

if [[ ! -d "${ACASH_REPO}" ]]; then
    echo "ERROR: ACASH_REPO not found at ${ACASH_REPO}" >&2
    exit 1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
    echo "ERROR: Python interpreter not found at ${PYTHON_BIN}" >&2
    exit 1
fi

if [[ ! -f "${SECRETS_FILE}" ]]; then
    echo "ERROR: Secrets file not found at ${SECRETS_FILE}" >&2
    exit 1
fi

if [[ ! -d "${STATE_ROOT}" ]]; then
    echo "ERROR: State root not found at ${STATE_ROOT}" >&2
    echo "Run deployment authorization first: AUTHORIZE_HYP_011_V2_CANONICAL_DEPLOYMENT" >&2
    exit 1
fi

# Verify state root ownership/permissions (fail closed)
STATE_OWNER=$(stat -c '%U' "${STATE_ROOT}")
if [[ "${STATE_OWNER}" != "mew" ]]; then
    echo "ERROR: State root owned by ${STATE_OWNER}, expected 'mew'" >&2
    exit 1
fi

STATE_PERMS=$(stat -c '%a' "${STATE_ROOT}")
if [[ "${STATE_PERMS}" != "700" ]]; then
    echo "ERROR: State root permissions ${STATE_PERMS}, expected 700" >&2
    exit 1
fi

# Verify secrets permissions
SECRETS_PERMS=$(stat -c '%a' "${SECRETS_FILE}")
if [[ "${SECRETS_PERMS}" != "600" ]]; then
    echo "ERROR: Secrets file permissions ${SECRETS_PERMS}, expected 600" >&2
    exit 1
fi

# ==============================================================================
# EXECUTION
# ==============================================================================

cd "${ACASH_REPO}"

# Source secrets (ACASH_ALPACA_API_KEY_ID, ACASH_ALPACA_API_SECRET)
set -a
source "${SECRETS_FILE}"
set +a

# Run the canonical runner with V2 contract.
# NOTE: scripts/ is not a Python package, so invoke the runner file directly.
exec "${PYTHON_BIN}" "${ACASH_REPO}/scripts/process_hyp_011_prospective_shadow.py" \
    --state-dir "${STATE_ROOT}" \
    --segment-id "${SEGMENT_ID}" \
    "$@"