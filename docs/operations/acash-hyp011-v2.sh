#!/bin/bash
# acash-hyp011-v2 wrapper script.
#
# Canonical source (tracked, mode 0644, NEVER executed in place):
#   <repo>/docs/operations/acash-hyp011-v2.sh
# Installed deployment copy (mode 0755, the only executed copy):
#   /usr/local/sbin/acash-hyp011-v2
# installed under AUTHORIZE_HYP_011_V2_CANONICAL_DEPLOYMENT via:
#   sudo install -o root -g root -m 0755 \
#     /home/mew/Acash/docs/operations/acash-hyp011-v2.sh \
#     /usr/local/sbin/acash-hyp011-v2
#
# Two modes:
#   (dispatch, default)  Run the canonical HYP_011 V2 runner with the V2
#                        state-dir/segment contract. Requires per-session
#                        authorities from the caller (Authority B).
#   --deployment-preflight
#                        Authority-A static checks ONLY: host, runtime, state
#                        root, secrets presence, install paths, timer absence.
#                        Never invokes the runner, never requires a
#                        SegmentActivationAuthority, creates nothing, zero
#                        network, never prints secret values.

set -euo pipefail

# ------------------------------------------------------------------------------
# Configuration. Production defaults are compiled in; the *_DIR / *_FILE / BIN
# overrides below exist ONLY so offline tests can build a synthetic
# environment. Production runbooks never set them.
# ------------------------------------------------------------------------------
ACASH_REPO="${ACASH_REPO:-/home/mew/Acash}"
STATE_ROOT="${V2_STATE_ROOT:-/var/lib/acash/hyp011/v2}"
SECRETS_FILE="${V2_SECRETS_FILE:-/etc/acash/hyp011-v2.env}"
PYTHON_BIN="${V2_PYTHON_BIN:-${ACASH_REPO}/.venv/bin/python}"
SEGMENT_ID="HYP_011_PROSPECTIVE_V2"
APPROVED_RUNTIME_SHA="${APPROVED_RUNTIME_SHA:-}"
ACASH_EXPECTED_USER="${ACASH_EXPECTED_USER:-mew}"
SYSTEMCTL="${SYSTEMCTL:-systemctl}"
SYSTEMD_UNIT_DIR="${SYSTEMD_UNIT_DIR:-/etc/systemd/system}"

V1_EVIDENCE_REL="data/hyp_011/prospective"


fail() {
    echo "ERROR: $1" >&2
    exit 1
}


check_absent_v2_timer() {
    # Installed unit file (real dir or synthetic override).
    if [[ -f "${SYSTEMD_UNIT_DIR}/acash-hyp011-v2.timer" ]]; then
        fail "V2 timer is installed at ${SYSTEMD_UNIT_DIR}/acash-hyp011-v2.timer."
    fi
    if command -v "${SYSTEMCTL}" >/dev/null 2>&1; then
        if "${SYSTEMCTL}" cat acash-hyp011-v2.timer >/dev/null 2>&1; then
            fail "V2 timer unit is known to systemd."
        fi
        enabled_state="$("${SYSTEMCTL}" is-enabled acash-hyp011-v2.timer 2>/dev/null || true)"
        if [[ "${enabled_state}" == enabled* ]]; then
            fail "V2 timer is enabled."
        fi
        active_state="$("${SYSTEMCTL}" is-active acash-hyp011-v2.timer 2>/dev/null || true)"
        if [[ "${active_state}" == active* ]]; then
            fail "V2 timer is active."
        fi
    fi
}


deployment_preflight() {
    # Host / runtime / state / secrets / install contract checks.
    # Read-only: creates nothing, invokes nothing, accesses no network.

    [[ -d "${ACASH_REPO}" ]] || fail "ACASH_REPO not found at ${ACASH_REPO}."

    head_sha="$(git -C "${ACASH_REPO}" rev-parse HEAD 2>/dev/null)" \
        || fail "cannot resolve git HEAD in ${ACASH_REPO}."
    [[ -n "${APPROVED_RUNTIME_SHA}" ]] \
        || fail "APPROVED_RUNTIME_SHA is not supplied."
    [[ "${head_sha}" == "${APPROVED_RUNTIME_SHA}" ]] \
        || fail "git HEAD (${head_sha}) != APPROVED_RUNTIME_SHA."

    [[ -z "$(git -C "${ACASH_REPO}" status --porcelain 2>/dev/null)" ]] \
        || fail "working tree in ${ACASH_REPO} is not clean."

    [[ -x "${PYTHON_BIN}" ]] || fail "Python interpreter not executable at ${PYTHON_BIN}."

    [[ -d "${STATE_ROOT}" ]] \
        || fail "state root not found at ${STATE_ROOT}."
    # External state: never inside the repository checkout.
    case "${STATE_ROOT}" in
        "${ACASH_REPO}"|"${ACASH_REPO}"/*)
            fail "state root ${STATE_ROOT} must live outside the repository checkout."
            ;;
    esac
    # Distinct from the preserved V1 evidence path.
    if [[ "${STATE_ROOT}" == "${ACASH_REPO}/${V1_EVIDENCE_REL}" ]]; then
        fail "state root must not be the V1 evidence path."
    fi
    state_owner="$(stat -c '%U' "${STATE_ROOT}")"
    [[ "${state_owner}" == "${ACASH_EXPECTED_USER}" ]] \
        || fail "state root owned by ${state_owner}, expected '${ACASH_EXPECTED_USER}'."
    [[ "$(stat -c '%a' "${STATE_ROOT}")" == "700" ]] \
        || fail "state root must have mode 700."

    [[ -f "${SECRETS_FILE}" ]] || fail "secrets file not found at ${SECRETS_FILE}."
    [[ "$(stat -c '%a' "${SECRETS_FILE}")" == "600" ]] \
        || fail "secrets file must have mode 600."
    # Presence of credential VARIABLE NAMES only; values are never printed.
    # (Sourced in a subshell so a malformed file cannot alter this shell.
    # Ambient environment is unset first so the check is purely file-derived:
    # pre-exported variables must never mask a missing secrets file.)
    cred_names="$(unset ACASH_ALPACA_API_KEY_ID ACASH_ALPACA_API_SECRET; set -a; . "${SECRETS_FILE}"; set +a; printf '%s|%s' "${ACASH_ALPACA_API_KEY_ID:-}" "${ACASH_ALPACA_API_SECRET:-}")" \
        || fail "secrets file cannot be sourced."
    if [[ "${cred_names}" == "|" || "${cred_names}" == "|"* || "${cred_names}" == *"|" ]]; then
        fail "required credential variable names are not present in secrets file."
    fi

    [[ -f "${ACASH_REPO}/docs/operations/acash-hyp011-v2.service" ]] \
        || fail "V2 service template missing in ${ACASH_REPO}."

    check_absent_v2_timer

    echo "DEPLOYMENT_PREFLIGHT = PASS"
    echo "NETWORK_REQUESTS = 0"
    echo "V2_STATE_CREATED = false"
    echo "V2_ACTIVATION_AUTHORITY_CREATED = false"
    echo "V2_TIMER_INSTALLED = false"
}


if [[ "${1:-}" == "--deployment-preflight" ]]; then
    shift
    if [[ "$#" -gt 0 ]]; then
        fail "--deployment-preflight takes no arguments."
    fi
    deployment_preflight
    exit 0
fi

# ------------------------------------------------------------------------------
# Dispatch path (Authority B only): validate, then exec the canonical runner.
# ------------------------------------------------------------------------------

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
if [[ "${STATE_OWNER}" != "${ACASH_EXPECTED_USER}" ]]; then
    echo "ERROR: State root owned by ${STATE_OWNER}, expected '${ACASH_EXPECTED_USER}'" >&2
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

cd "${ACASH_REPO}"

# Source secrets (ACASH_ALPACA_API_KEY_ID, ACASH_ALPACA_API_SECRET)
set -a
# shellcheck disable=SC1090
source "${SECRETS_FILE}"
set +a

# Run the canonical runner with V2 contract.
# NOTE: scripts/ is not a Python package, so invoke the runner file directly.
exec "${PYTHON_BIN}" "${ACASH_REPO}/scripts/process_hyp_011_prospective_shadow.py" \
    --state-dir "${STATE_ROOT}" \
    --segment-id "${SEGMENT_ID}" \
    "$@"
