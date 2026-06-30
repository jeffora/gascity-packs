# input-notifier

A small, config-only pack that alerts the **human** when a Gas City session is
**waiting on input**. It ships one `session_live` hook and no agents, formulas,
or roles. It is the gate for moving cities from bypass mode to auto mode: in
auto/default permission modes, sessions stall silently on permission prompts;
this surfaces them. It also catches the idle "waiting for input" and
clarification / multiple-choice prompts that already stall bypass sessions.

## What it does

On every live session in a city that imports it, the `session_live` hook:

1. **Injects a Claude Code `Notification` hook** into the session's runtime
   claude settings (`<city>/.gc/settings.json`). gc regenerates that file from
   source *before* the session launches; the `session_live` step runs *after*
   launch and adds the hook on top, which Claude Code's settings file-watcher
   picks up **live, without a restart**. The injection is idempotent (matched
   on the hook script's basename) so repeated re-applies never duplicate it.
2. **Turns on tmux `monitor-bell`** for the session's window (socket-aware via
   `GC_TMUX_SOCKET`) and sets a red `window-status-bell-style`, so a bell from
   the hook flags the window-status entry as needing attention.

When the `Notification` hook fires, `notify-waiting.sh` reads the event JSON,
and — for the *waiting* notification types (`permission_prompt`, `idle_prompt`,
`elicitation_dialog`) — drives two **zero-infra** sinks:

- **tmux bell** — writes `BEL` to the pane tty so `monitor-bell` flags the
  window. (Ambient `$TMUX` targets the city's own server; no personal tmux
  server is ever touched.)
- **gc mail** — `gc mail send human --notify -s "[<city>] <session> waiting on
  input"` so it also lands in the gc inbox/banner.

Terminal/informational events (`auth_success`, `elicitation_complete`,
`elicitation_response`) are ignored.

### AskUserQuestion detector (the second layer)

`AskUserQuestion` / multiple-choice clarification prompts fire **no**
Notification hook at all — Claude Code treats them as a tool-call-in-flight, so
the `elicitation_dialog` matcher does not cover them and a gc idle-probe would
see the session as "working" (open issue
[anthropics/claude-code#59908](https://github.com/anthropics/claude-code/issues/59908)).
No hook config can ever cover this case, so the pack adds a focus-independent
detector that **layers alongside** the Notification hook (the hook owns
`permission_prompt` + best-effort `idle_prompt`; the detector owns the
question/clarification case). Both write the same two sinks.

`orders/detect-waiting.toml` is a `cooldown` `[order]` (30s) that runs
`assets/scripts/detect-waiting.sh`: it lists live sessions, `gc session peek`s
each, and matches the AskUserQuestion dialog's on-screen footer signature
(`Enter to select` — unique to that dialog; the permission prompt's footer is
`Esc to cancel · Tab to amend · ctrl+e to explain`, so there is no double-fire).
On a match it fires the tmux bell (BEL to the session's pane tty) and one
`gc mail send human --notify`, **de-duped** to once per dialog appearance (a
per-session marker under `$GC_CITY_RUNTIME_DIR/input-notifier-waiting`, cleared
when the dialog clears so a later question re-alerts). Focus-independent: peek
does not depend on terminal focus.

## Requirements

- `jq` and `tmux` on `PATH` (same class of dependency as terminal-ux's tmux
  requirement). Without `jq` the hook install is skipped (warned, non-fatal).
- `gc` resolvable at hook-fire time. The injected hook command exports the
  standard `$HOME/go/bin:$HOME/.local/bin` PATH prefix, mirroring the other
  managed hooks.
- The `Notification` idle trigger debounces ~60s; that delay is expected.

## Importing

Add `input-notifier` to a city's imports the same way other shared packs are
imported (by git source, pinned to a sha). It composes with any pack's roles.
New `session_live` lines apply to sessions started after the import; existing
live sessions pick the hook up after the next reconcile re-apply or restart.

## Reversal

Remove the import to stop applying it. The next time gc regenerates
`<city>/.gc/settings.json` (city start / hooks install) the injected
`Notification` hook is gone. To revert a running session in place:

```sh
# Drop the Notification hook from the live settings file:
jq 'del(.hooks.Notification)' "$GC_CITY/.gc/settings.json" > /tmp/s && \
  mv /tmp/s "$GC_CITY/.gc/settings.json"

# Turn off the window bell flag:
tmux -L "$GC_TMUX_SOCKET" set-option -w -t "$SESSION" monitor-bell off
```
