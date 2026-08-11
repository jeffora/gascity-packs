#!/usr/bin/env bash
#
# has-undelivered-escalates.sh — condition check for escalate-rollups order.
#
# Exits 0 (fire the order) when there is at least one open rollup bead
# with severity:escalate that has not yet been labeled delivered.
# Exits non-zero otherwise.
#
# Enumeration lives in lib-rollups.sh because it must cover every rig's store,
# not just the city's — see the comment there.

set -euo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib-rollups.sh
. "${script_dir}/lib-rollups.sh"

count=$(list_undelivered_escalates | grep -c . || true)

[[ "$count" -gt 0 ]]
