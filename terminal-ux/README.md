# terminal-ux

A small, config-only pack that improves the terminal experience for
human-attached Gas City sessions. It ships one `session_live` hook and no
agents, formulas, or roles.

## What it does

On every live session in a city that imports it, the hook configures the
city's own tmux server (socket-aware via `gcmux` / `GC_TMUX_SOCKET`) to:

1. **Mouse-wheel scrollback** — the wheel scrolls the tmux copy-mode
   scrollback instead of leaking into a mouse-reporting TUI's own history
   scroll (the failure mode of a naive `mouse on`). Uses the same
   `WheelUpPane`/`WheelDownPane` root bindings as gastown, which the gascity
   runtime already expects (it un-parks copy-mode before delivering
   keystrokes). Shift+wheel still does native terminal text selection.
2. **Shift+Enter → newline in Claude Code** — forwards extended keys (CSI-u)
   through tmux so Claude Code receives `Shift+Enter` and inserts a newline
   rather than submitting the prompt.

## Requirements

The Shift+Enter path needs an **outer terminal that emits CSI-u**: Ghostty,
kitty, WezTerm, or iTerm2 with "Report modifiers using CSI u" enabled. tmux
cannot recover a modifier the host terminal never sends. Mouse scrollback has
no such requirement.

## Importing

Add `terminal-ux` to a city's imports the same way other shared packs are
imported (by git source). It composes with any pack's roles. New
`session_live` lines apply to sessions started after the import; existing live
sessions pick them up on restart (or apply the script once manually).

## Reversal

Remove the import to stop applying it. To revert a running session in place:

```sh
tmux -L "$GC_TMUX_SOCKET" set-option -t "$SESSION" mouse off
tmux -L "$GC_TMUX_SOCKET" set-option -s extended-keys off
tmux -L "$GC_TMUX_SOCKET" unbind-key -T root WheelUpPane
tmux -L "$GC_TMUX_SOCKET" unbind-key -T root WheelDownPane
```
