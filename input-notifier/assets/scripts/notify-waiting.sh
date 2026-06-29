#!/bin/sh
# notify-waiting.sh — Claude Code `Notification` hook for the input-notifier pack.
#
# Runs as a subprocess of the session's `claude` process (inside the tmux
# pane), so it inherits the session env (GC_SESSION_NAME, GC_AGENT, GC_CITY,
# PATH) and ambient tmux context ($TMUX / $TMUX_PANE). Reads the Notification
# event JSON on stdin and, when the event means the session is WAITING ON A
# HUMAN, drives two zero-infra sinks:
#
#   A. tmux bell  — writes BEL to the pane tty so monitor-bell flags the
#                   window-status entry (set up by install-notify-hook.sh).
#   B. gc mail    — `gc mail send human --notify` so it lands in the inbox/banner.
#
# Fire-and-forget: always exits 0; a Notification hook cannot (and must not)
# block the notification. Judgment lives here (shell), not in any framework Go.

# ── Read the event and pull the fields we need ────────────────────────
payload="$(cat 2>/dev/null)"

field() { printf '%s' "$payload" | jq -r "$1 // empty" 2>/dev/null; }
if command -v jq >/dev/null 2>&1 && [ -n "$payload" ]; then
    ntype="$(field '.notification_type')"
    message="$(field '.message')"
else
    # No jq / no payload: assume it is worth surfacing rather than swallow it.
    ntype=""
    message="$payload"
fi

# ── Decide whether this event means "waiting on a human" ──────────────
# Alert on the waiting states; ignore the terminal/informational ones
# (auth_success, elicitation_complete, elicitation_response). An empty type
# (older Claude Code without notification_type) is treated as worth surfacing.
case "$ntype" in
    permission_prompt|idle_prompt|elicitation_dialog|"")
        : # waiting — surface it
        ;;
    *)
        exit 0
        ;;
esac

session="${GC_SESSION_NAME:-${GC_AGENT:-session}}"
city="$(basename "${GC_CITY:-${GC_CITY_PATH:-city}}")"
label="$([ -n "$ntype" ] && echo "$ntype" || echo "waiting")"

# ── Sink A: tmux bell → window-status flag ────────────────────────────
# Inside tmux, $TMUX is set so tmux targets the right server automatically.
if [ -n "$TMUX" ] && command -v tmux >/dev/null 2>&1; then
    pane_tty="$(tmux display-message -p -t "${TMUX_PANE:-}" '#{pane_tty}' 2>/dev/null)"
    if [ -n "$pane_tty" ] && [ -w "$pane_tty" ]; then
        printf '\a' > "$pane_tty" 2>/dev/null
    else
        printf '\a' > /dev/tty 2>/dev/null
    fi
fi

# ── Sink B: gc mail → human, with a nudge ─────────────────────────────
if command -v gc >/dev/null 2>&1; then
    gc mail send human --notify \
        -s "[$city] $session waiting on input" \
        -m "$label: ${message:-session is waiting for human input}" \
        >/dev/null 2>&1
fi

exit 0
