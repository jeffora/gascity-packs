#!/bin/sh
# detect-waiting.sh — focus-independent detector for AskUserQuestion / multiple-
# choice clarification prompts, run as a cooldown [order] (see pack.toml).
#
# WHY THIS EXISTS: AskUserQuestion (multiple-choice / clarification) prompts fire
# NO Claude Code Notification hook (open issue anthropics/claude-code#59908; the
# elicitation_dialog matcher does not cover them, and CC treats the prompt as a
# tool-call-in-flight, so a gc idle-probe would see the session as "working").
# So no hook config can ever cover this case. This detector closes that gap and
# LAYERS alongside the Notification hook: the hook owns permission_prompt (and
# best-effort idle_prompt); this owns the question/clarification case. Both write
# the SAME two sinks (tmux bell flag + gc mail send human --notify).
#
# MECHANISM: each tick, list live sessions, `gc session peek` each, and look for
# the AskUserQuestion dialog's on-screen signature. The footer
# "Enter to select" is unique to that dialog — the permission prompt's footer is
# "Esc to cancel / Tab to amend / ctrl+e to explain", so there is no double-fire.
#
# DE-DUPE: a per-session marker fires the alert ONCE per dialog appearance and is
# cleared when the dialog clears, so a later question re-alerts.
#
# Focus-independent: peek + capture do not depend on terminal focus. Socket-aware
# and role-agnostic. Reversible: remove the import and the [order] is gone.

# Signature unique to the AskUserQuestion multiple-choice dialog (NOT the
# permission prompt). Kept as a fixed string so a UI tweak is a one-line change.
DIALOG_SIGNATURE='Enter to select'

CITY="${GC_CITY:-${GC_CITY_PATH:-}}"
# tmux server for the bell: explicit socket, else the city dir basename
# (gcmux names the per-city server after the city, e.g. tmux -L gasland).
SOCKET="${GC_TMUX_SOCKET:-$( [ -n "$CITY" ] && basename "$CITY" )}"
gcmux() { tmux ${SOCKET:+-L "$SOCKET"} "$@"; }

# Per-session de-dupe markers (survive across ticks; per-city).
STATE_DIR="${GC_CITY_RUNTIME_DIR:-${TMPDIR:-/tmp}}/input-notifier-waiting"
mkdir -p "$STATE_DIR" 2>/dev/null

command -v gc  >/dev/null 2>&1 || exit 0
command -v jq  >/dev/null 2>&1 || exit 0

# Active, non-closed sessions only (asleep/closed cannot display a dialog).
sessions_json="$(gc session list --json 2>/dev/null)" || exit 0
ids="$(printf '%s' "$sessions_json" | jq -r '.sessions[]? | select(.state=="active" and (.closed|not)) | .id' 2>/dev/null)"

seen_ids=""
for id in $ids; do
    seen_ids="$seen_ids $id"
    marker="$STATE_DIR/$id.waiting"
    content="$(gc session peek "$id" --lines 40 2>/dev/null)"

    if printf '%s' "$content" | grep -qF "$DIALOG_SIGNATURE"; then
        # Dialog is on screen. Fire once per appearance.
        [ -f "$marker" ] && continue
        : > "$marker"

        session_name="$(printf '%s' "$sessions_json" | jq -r --arg i "$id" '.sessions[]? | select(.id==$i) | .session_name // .name // empty' 2>/dev/null)"
        city_label="$( [ -n "$CITY" ] && basename "$CITY" || echo city )"
        # Best-effort: the question line (the "?" line above the options).
        question="$(printf '%s' "$content" | grep -E '\?\s*$' | grep -v '> ' | tail -1 | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')"

        # ── Sink A: tmux bell -> window-status flag (best-effort) ──
        if [ -n "$session_name" ] && command -v tmux >/dev/null 2>&1; then
            gcmux set-option -w -t "$session_name" monitor-bell on 2>/dev/null
            pane_tty="$(gcmux display-message -p -t "$session_name" '#{pane_tty}' 2>/dev/null)"
            if [ -n "$pane_tty" ] && [ -w "$pane_tty" ]; then
                printf '\a' > "$pane_tty" 2>/dev/null
            fi
        fi

        # ── Sink B: gc mail -> human, with a nudge ──
        gc mail send human --notify \
            ${CITY:+--city "$CITY"} \
            -s "[$city_label] ${session_name:-$id} waiting on input" \
            -m "AskUserQuestion (multiple-choice): ${question:-session is waiting on a human choice}" \
            >/dev/null 2>&1
    else
        # No dialog now: clear the marker so the next question re-alerts.
        [ -f "$marker" ] && rm -f "$marker"
    fi
done

# Garbage-collect markers for sessions that no longer exist.
for m in "$STATE_DIR"/*.waiting; do
    [ -e "$m" ] || continue
    mid="$(basename "$m" .waiting)"
    case " $seen_ids " in
        *" $mid "*) : ;;
        *) rm -f "$m" ;;
    esac
done

exit 0
