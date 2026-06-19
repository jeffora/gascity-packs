#!/bin/sh
# tmux-terminal-ux.sh — terminal ergonomics for human-attached sessions.
# Usage: tmux-terminal-ux.sh <session>
#
# Applies two improvements to the city's tmux server for this session:
#   1. Mouse-wheel scrollback — "mouse on" lets the wheel reach tmux, and the
#      WheelUpPane/WheelDownPane root bindings force copy-mode scrollback even
#      over a mouse-reporting TUI (Claude Code). Without the bindings, "mouse
#      on" alone hands the wheel to the app's own history scroll. Once in
#      copy-mode the wheel passes through (-M); -e exits at the bottom.
#      Shift+wheel still does native terminal selection. The gascity runtime
#      expects this binding (it un-parks copy-mode before delivering keys), so
#      it is safe on any city.
#   2. Shift+Enter newline — extended-keys + terminal-features ':extkeys'
#      forward CSI-u modified keys through tmux so Claude Code receives
#      Shift+Enter and inserts a newline instead of submitting. Requires an
#      outer terminal that emits CSI-u (e.g. Ghostty, kitty, WezTerm,
#      iTerm2 with "Report modifiers using CSI u").
#
# Role-agnostic and socket-aware: gcmux pins every command to the city's own
# tmux server (GC_TMUX_SOCKET), never the operator's personal server.
SESSION="$1"

# Socket-aware tmux command (uses GC_TMUX_SOCKET when set).
gcmux() { tmux ${GC_TMUX_SOCKET:+-L "$GC_TMUX_SOCKET"} "$@"; }

# ── Mouse-wheel scrollback ────────────────────────────────────────────
gcmux set-option -t "$SESSION" mouse on
gcmux set-option -t "$SESSION" set-clipboard on
gcmux bind-key -T root WheelUpPane   if-shell -F -t= "#{pane_in_mode}" "send-keys -M" "copy-mode -e"
gcmux bind-key -T root WheelDownPane send-keys -M

# ── Shift+Enter → newline (forward extended keys) ─────────────────────
gcmux set-option -s  extended-keys on
gcmux set-option -as terminal-features '*:extkeys'
