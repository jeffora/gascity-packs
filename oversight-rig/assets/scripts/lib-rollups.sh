#!/usr/bin/env bash
#
# lib-rollups.sh — shared rollup enumeration for the escalate-rollups order.
#
# Why this exists
# ---------------
#
# project-lead is a RIG-SCOPED role, so the rollup beads it writes land in its
# own rig's bead store (pl-*, ag-*, aw-*), never the city store. An unscoped
# `gc bd list` resolves to the CITY store only, so it reports zero undelivered
# escalations no matter how many are waiting in the rigs.
#
# That made the whole outbound path fail silently: the condition check is
# *expected* to exit non-zero most of the time, so "never fires because it can
# only see an empty store" is indistinguishable from "nothing to escalate".
#
# Both the condition check and the delivery exec need the same enumeration, so
# it lives here rather than being duplicated (they had already drifted apart in
# their handling of the `delivered` label).
#
# Same root cause as c61745c (gascity ralph gates answering from the city store
# for rig-owned beads); the fix there was to name the store explicitly, and so
# is this one.

# list_undelivered_escalates
#
# Emits one TSV line per open, undelivered severity:escalate rollup bead:
#
#     <rig>\t<bead-id>
#
# <rig> is the store that OWNS the bead, and is empty for a city-level bead.
# The HQ rig is deliberately not addressable via `gc bd --rig` (it is the
# default store), so an empty field means "omit --rig", not "unknown".
#
# Note this is the owning store, which is not necessarily the same thing as the
# bead's `rig:` label — that label drives channel routing and is read
# separately by the caller.
list_undelivered_escalates() {
  local jq_filter='[.[] | select((.labels // []) | index("delivered") | not)] | .[].id'

  # City store: addressed by omitting --rig entirely.
  gc bd list --label rollup --label severity:escalate --status open --json 2>/dev/null \
    | jq -r "$jq_filter" 2>/dev/null \
    | sed 's/^/\t/'

  # Every non-HQ rig, named explicitly.
  local rig
  while IFS= read -r rig; do
    [ -n "$rig" ] || continue
    gc bd --rig "$rig" list --label rollup --label severity:escalate --status open --json 2>/dev/null \
      | jq -r "$jq_filter" 2>/dev/null \
      | sed "s/^/${rig}\t/"
  done < <(gc rig list --json 2>/dev/null | jq -r '.rigs[]? | select(.hq | not) | .name')
}

# gc_bd_scoped <rig> <bd-args...>
#
# Run `gc bd` against the store that owns the bead. Empty <rig> means the city
# store. Use this for every show/update on an enumerated bead — an unscoped
# call is what caused the original bug.
gc_bd_scoped() {
  local rig="$1"
  shift
  if [ -n "$rig" ]; then
    gc bd --rig "$rig" "$@"
  else
    gc bd "$@"
  fi
}
