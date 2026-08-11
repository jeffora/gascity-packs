#!/usr/bin/env bash
#
# nudge-project-leads.sh — wake every project-lead session for a triage tick.
#
# Pure plumbing: enumerate active project-lead sessions, send each one
# the standard triage nudge. The decision of "what to escalate" stays
# entirely with the project-lead (informed by its rig's project-brief.md).
# This script never reads beads, never decides escalations.
#
# THREE TRAPS THIS SCRIPT MUST NOT REPEAT (found live 2026-08-11 — this
# script had never nudged anybody because of them, and reported success
# every time):
#   1. `gc session list --json` returns {sessions:[...]}, NOT a bare array.
#      Iterating `.[]` walks the top-level object's values and dies on the
#      boolean `ok`. Use `.sessions[]`.
#   2. Session templates are RIG-PREFIXED — "platform/oversight-rig.project-lead",
#      not "oversight-rig.project-lead". An exact match finds nothing. Match
#      on templates that END WITH the unqualified name.
#   3. `gc session nudge` takes the message POSITIONALLY. There is no
#      `--message` flag; passing one is a silent no-op under `>/dev/null 2>&1`.
#
# A patrol that cannot see any session is indistinguishable from a city with
# no sessions, so this script must not exit 0 just because its own lookup
# broke. It does a second, broader scan for anything template-shaped like a
# project-lead session; if that broader scan finds candidates but the exact
# match finds none, the lookup itself is treated as broken (non-zero exit)
# rather than as a legitimately empty roster.

set -euo pipefail

# Unqualified template name for this pack's project-lead. Actual session
# templates are rig-qualified, e.g. "platform/oversight-rig.project-lead".
template="oversight-rig.project-lead"

sessions_json="$(gc session list --json)"

matched_ids="$(
  jq -r --arg t "$template" \
    '.sessions[]? | select(.state == "active") | select(.template == $t or (.template | endswith("/" + $t))) | .id' \
    <<<"$sessions_json"
)"
mapfile -t session_ids <<<"$matched_ids"
[[ ${#session_ids[@]} -eq 1 && -z "${session_ids[0]}" ]] && session_ids=()

if [[ ${#session_ids[@]} -eq 0 ]]; then
  # Independent of $template on purpose: if $template itself is what's
  # broken, deriving the sanity check from it too would hide the break.
  broad_count="$(
    jq -r \
      '[.sessions[]? | select(.state == "active") | select(.template | contains("project-lead"))] | length' \
      <<<"$sessions_json"
  )"
  if [[ "$broad_count" -gt 0 ]]; then
    echo "found $broad_count active project-lead-shaped session(s) but none matched template '$template' exactly — lookup is broken, not empty" >&2
    exit 1
  fi
  echo "no active project-lead sessions"
  exit 0
fi

nudged=0
failed=0
for sid in "${session_ids[@]}"; do
  # --delivery queue, NOT the default wait-idle. wait-idle BLOCKS until the
  # target session goes idle, so patrolling N busy leads serialises into N
  # waits of unbounded length — measured ~4s against an idle lead but over two
  # minutes against working ones. This order's timeout is 30s, so on exactly
  # the ticks where the leads are busy (the ticks that matter) the patrol was
  # being killed part-way through, having nudged only some of them.
  #
  # This was invisible until the four bugs above were fixed: a patrol that
  # never nudged anybody always finished instantly. Fixing the nudges is what
  # made the blocking real.
  #
  # queue enqueues and returns (~2s), and the lead picks the nudge up when it
  # next goes idle — which is precisely the semantics a periodic triage patrol
  # wants. It must never matter to a patrol whether a lead is mid-tick.
  if gc session nudge "$sid" --delivery queue "Triage tick: read your brief, survey your rig, write rollups." >/dev/null 2>&1; then
    nudged=$((nudged + 1))
  else
    echo "nudge failed for $sid" >&2
    failed=1
  fi
done

echo "nudged $nudged project-lead session(s)"
exit "$failed"
