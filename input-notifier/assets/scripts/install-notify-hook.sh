#!/bin/sh
# install-notify-hook.sh — session_live installer for the input-notifier pack.
# Usage: install-notify-hook.sh <session> <city_root> <notify_script>
#
# Idempotent and re-appliable (it is a session_live command: run at startup
# after session_setup, and re-applied by the reconciler on live drift).
#
# Two effects, both reversible:
#   1. Injects a Claude Code `Notification` hook into <city_root>/.gc/settings.json
#      whose command is <notify_script>. gc regenerates that file from source
#      BEFORE the session launches, then this runs AFTER launch, so the hook is
#      added on top and Claude Code's settings watcher picks it up live (no
#      restart). Matched on the script basename so re-runs never duplicate it.
#   2. Turns on tmux monitor-bell for the session's window so a bell from the
#      hook flags the window-status entry as needing attention. Socket-aware via
#      GC_TMUX_SOCKET (this script runs in gc's process, like terminal-ux).
#
# Non-fatal by design: any step that cannot run (no jq, no settings file, no
# tmux) is skipped with a warning; the session still works.
SESSION="$1"
CITY_ROOT="$2"
NOTIFY_SCRIPT="$3"

if [ -z "$SESSION" ] || [ -z "$CITY_ROOT" ] || [ -z "$NOTIFY_SCRIPT" ]; then
    echo "input-notifier: usage: install-notify-hook.sh <session> <city_root> <notify_script>" >&2
    exit 0
fi

SETTINGS="$CITY_ROOT/.gc/settings.json"

# ── 1. Inject the Notification hook (idempotent) ──────────────────────
if ! command -v jq >/dev/null 2>&1; then
    echo "input-notifier: jq not found; cannot install Notification hook" >&2
elif [ ! -f "$SETTINGS" ]; then
    echo "input-notifier: $SETTINGS not found; skipping hook install" >&2
else
    # The hook command exports the standard gc PATH prefix (mirrors the other
    # managed hooks) so `gc` resolves at hook-fire time, then runs the notifier.
    NOTIFY_CMD="export PATH=\"\$HOME/go/bin:\$HOME/.local/bin:\$PATH\" && exec $NOTIFY_SCRIPT"
    tmpf="$SETTINGS.input-notifier.tmp.$$"
    if jq --arg cmd "$NOTIFY_CMD" '
        (.hooks //= {})
        | (.hooks.Notification //= [])
        | if ([.hooks.Notification[].hooks[]?.command] | any(test("notify-waiting\\.sh")))
          then .
          else .hooks.Notification += [{matcher: "", hooks: [{type: "command", command: $cmd}]}]
          end
    ' "$SETTINGS" > "$tmpf" 2>/dev/null && [ -s "$tmpf" ]; then
        mv -f "$tmpf" "$SETTINGS"
    else
        rm -f "$tmpf"
        echo "input-notifier: failed to merge Notification hook into $SETTINGS" >&2
    fi
fi

# ── 2. tmux monitor-bell for this session's window ────────────────────
# Socket-aware: pin to the city's own tmux server when GC_TMUX_SOCKET is set.
gcmux() { tmux ${GC_TMUX_SOCKET:+-L "$GC_TMUX_SOCKET"} "$@"; }
if command -v tmux >/dev/null 2>&1 && gcmux has-session -t "$SESSION" 2>/dev/null; then
    gcmux set-option   -t "$SESSION" monitor-bell on 2>/dev/null
    gcmux set-option -w -t "$SESSION" monitor-bell on 2>/dev/null
    # Make the flagged window obvious in the status line (idempotent).
    gcmux set-option -g window-status-bell-style "fg=black,bg=red,bold" 2>/dev/null
fi

exit 0
