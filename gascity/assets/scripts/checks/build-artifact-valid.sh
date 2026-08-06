#!/usr/bin/env bash
set -euo pipefail

# Generic producer-stage build-artifact validation gate.
#
# The checked formula step names its artifact contract in step metadata:
#   gc.build.artifact_schema    - expected schema id (e.g. gc.build.requirements.v1)
#   gc.build.artifact_path_keys - comma-separated workflow-root metadata keys;
#                                 the first non-empty value is the artifact path
#
# The step bead (and the ralph control bead cloned from it) carries that
# metadata, so this script reads $GC_BEAD_ID, resolves the workflow root via
# gc.root_bead_id, resolves the artifact path, and validates the artifact with
# the shared base validator. All failures print machine-readable lines on
# stderr; the dispatcher records them in gc.attempt_log as repair context for
# the next bounded producer attempt. This gate never prompts.

fail() {
  echo "build-artifact-check: $*" >&2
  exit 1
}

BEAD_ID="${GC_BEAD_ID:-}"
[ -n "$BEAD_ID" ] || fail "GC_BEAD_ID is required"
command -v gc >/dev/null 2>&1 || fail "gc is required on PATH"
command -v python3 >/dev/null 2>&1 || fail "python3 is required on PATH"

gc_bd_show() {
  # gc_bd_show <bead-id> [args...] -> `gc bd show`, scoped to the store this
  # gate is running against.
  #
  # The dispatcher's gate env sets GC_STORE_PATH to the owning store (a rig root
  # for a rig-owned graph) but carries no GC_RIG/GC_RIG_ROOT/GC_BEADS_SCOPE_ROOT,
  # so an unscoped `gc bd` exhausts its resolution chain and answers from the
  # CITY store, where a rig bead does not exist — every rig ralph gate then
  # failed deterministically on an unresolvable bead (un-1b63). Bare `bd` was
  # immune here because it reads BEADS_DIR, which the gate env does set
  # correctly; routing these scripts through `gc bd` is what exposed this. -C
  # names the store explicitly and is honored without the existence probe the
  # bead-prefix path depends on. When GC_STORE_PATH is unset, or names the city
  # root, resolution falls back to the normal chain, so city-scoped gates are
  # unaffected.
  if [ -n "${GC_STORE_PATH:-}" ]; then
    gc bd show -C "$GC_STORE_PATH" "$@"
  else
    gc bd show "$@"
  fi
}

metadata_value() {
  # metadata_value <json> <key> -> prints metadata[key] or empty
  printf '%s' "$1" | python3 -c '
import json
import sys

key = sys.argv[1]
try:
    data = json.load(sys.stdin)
except Exception:
    print("")
    raise SystemExit(0)
if isinstance(data, list):
    data = data[0] if data else {}
if not isinstance(data, dict):
    print("")
    raise SystemExit(0)
metadata = data.get("metadata") or {}
value = metadata.get(key, "") if isinstance(metadata, dict) else ""
print(value if isinstance(value, str) else "")
' "$2"
}

GC_ERR="$(mktemp)"
trap 'rm -f "$GC_ERR"' EXIT
SHOW_JSON="$(gc_bd_show "$BEAD_ID" --json 2>"$GC_ERR")" \
  || fail "gc bd show $BEAD_ID failed (store ${GC_STORE_PATH:-<unset>}): $(tail -c 400 "$GC_ERR" | tr '\n' ' ')"

SCHEMA="$(metadata_value "$SHOW_JSON" "gc.build.artifact_schema")"
PATH_KEYS="$(metadata_value "$SHOW_JSON" "gc.build.artifact_path_keys")"
[ -n "$SCHEMA" ] || fail "step metadata gc.build.artifact_schema is missing on $BEAD_ID"
[ -n "$PATH_KEYS" ] || fail "step metadata gc.build.artifact_path_keys is missing on $BEAD_ID"

ROOT_ID="$(metadata_value "$SHOW_JSON" "gc.root_bead_id")"
ROOT_JSON="$SHOW_JSON"
if [ -n "$ROOT_ID" ] && [ "$ROOT_ID" != "$BEAD_ID" ]; then
  ROOT_JSON="$(gc_bd_show "$ROOT_ID" --json 2>"$GC_ERR")" \
    || fail "gc bd show $ROOT_ID failed (store ${GC_STORE_PATH:-<unset>}): $(tail -c 400 "$GC_ERR" | tr '\n' ' ')"
fi

ARTIFACT_PATH=""
RESOLVED_KEY=""
IFS=',' read -r -a KEYS <<<"$PATH_KEYS"
for key in "${KEYS[@]}"; do
  key="$(printf '%s' "$key" | tr -d '[:space:]')"
  [ -n "$key" ] || continue
  value="$(metadata_value "$ROOT_JSON" "$key")"
  if [ -n "$value" ]; then
    ARTIFACT_PATH="$value"
    RESOLVED_KEY="$key"
    break
  fi
done
[ -n "$ARTIFACT_PATH" ] || fail "no artifact path recorded on workflow root ${ROOT_ID:-$BEAD_ID}; tried metadata keys: $PATH_KEYS. The producing stage must record the resolved artifact path before closing."

case "$ARTIFACT_PATH" in
  /*) ;;
  *)
    [ -n "${GC_WORK_DIR:-}" ] || fail "artifact path $ARTIFACT_PATH from $RESOLVED_KEY is relative and GC_WORK_DIR is unset"
    ARTIFACT_PATH="$GC_WORK_DIR/$ARTIFACT_PATH"
    ;;
esac
[ -f "$ARTIFACT_PATH" ] || fail "artifact $ARTIFACT_PATH from $RESOLVED_KEY does not exist"

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VALIDATOR=""
for candidate in \
  ${GC_WORK_DIR:+"$GC_WORK_DIR/gascity/assets/scripts/validate_build_artifact.py"} \
  "$SCRIPT_DIR/../validate_build_artifact.py"; do
  if [ -n "$candidate" ] && [ -f "$candidate" ]; then
    VALIDATOR="$candidate"
    break
  fi
done
[ -n "$VALIDATOR" ] || fail "validate_build_artifact.py not found beside $SCRIPT_DIR or under GC_WORK_DIR"

if OUTPUT="$(python3 "$VALIDATOR" --schema "$SCHEMA" --path "$ARTIFACT_PATH" 2>&1)"; then
  echo "build artifact valid: schema=$SCHEMA path=$ARTIFACT_PATH"
  exit 0
fi

echo "build-artifact-check: schema=$SCHEMA path=$ARTIFACT_PATH failed validation" >&2
printf '%s\n' "$OUTPUT" >&2
exit 1
