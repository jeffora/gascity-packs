# Discord Pack Research

Source reviewed: `rigs/gascity-packs/discord/` (entire tree — `pack.toml`, `README.md`,
`REVIEW-implementation.md`, all `commands/`, `doctor/`, `formulas/`, `scripts/`,
`template-fragments/`, `tests/`, `.gitignore`). Pack version: `0.1.0`, `schema = 2`.

This document is written to stand alone (a reader who never opened the pack should
be able to follow it) and to be diffable against a parallel Slack-pack research doc.
Its H2 headers match the requested outline verbatim.

## 1. Purpose & scope

The Discord pack is a **workspace-hosted Discord provider extension for Gas City**
(the multi-agent orchestration system, "gc"). It lives outside `gc` core — README.md
line 5: "This pack keeps Discord outside core `gc`." — and gives a Gas City
workspace ("city") a Discord-facing surface for two distinct use cases:

1. **Slash-command bug-fix intake.** A human types `/gc fix` in a mapped Discord
   channel or names a mapped rig; the pack creates a bead, dispatches a formula
   (`mol-discord-fix-issue`) against a `rig/pool` sling target, and posts
   started/completed status updates back into the originating Discord
   conversation/thread.
2. **Session chat control plane.** Direct, explicit bindings between a Discord DM
   or room/thread and one or more named Gas City sessions ("agents"), so humans
   and agents can converse in Discord. This includes a newer "launcher room" UX
   where an unmentioned `@@rig/alias` in a root room spins up a thread-scoped
   agent session on demand.

`discord` is a **replacement for an older `discord-intake` pack** (README.md lines
8-11, 43-67). The two packs intentionally share the `discord-interactions` and
`discord-admin` service identities and must never be imported into the same
workspace at once — a `doctor/legacy-pack-conflict` check enforces this by
scanning for residual `discord-intake` state on disk (it is not a live
simultaneous-import guard, just a leftover-state guard).

**Deployment model:** the pack ships three long-running `proxy_process` services
(declared in `pack.toml`) that a Gas City workspace starts and supervises:

- `discord-interactions` (public) — Discord's Interactions Endpoint (slash
  commands/modals), served by `scripts/discord_intake_service.py`.
- `discord-admin` (tenant-visible) — an operator status/admin HTML page, same
  script, branching behavior on the `GC_SERVICE_NAME` env var at runtime.
- `discord-gateway` (private) — a persistent Discord Gateway (WebSocket)
  connection for inbound DMs and room/thread chat, served by
  `scripts/discord_gateway_service.py`.

All three run `health_path = "/healthz"` and share `state_root =
".gc/services/discord"`. Standing the pack up requires: creating a Discord
application + bot in the Developer Portal, importing its credentials via `gc
discord import-app`, pointing Discord's Interactions Endpoint URL at the
published `discord-interactions` service, mapping `/gc fix` dispatch targets,
registering the guild slash command, and (optionally) creating chat
bindings/launchers. Ambient/launcher room reads additionally require Discord's
privileged **Message Content Intent** to be enabled in the Developer Portal —
without it Discord silently strips message content on unmentioned guild
messages.

Agent-facing behavior is intentionally **explicit-publish-only**: a session's
normal assistant output never reaches Discord automatically. Only an explicit
`gc discord reply-current` / `gc discord publish` call sends a human-visible
message back out (see §6).

## 2. Roles/agents defined

**None.** `pack.toml` (42 lines) contains only `[pack]` metadata and three
`[[service]]` blocks (see §1); it defines **no `[[role]]`/agent blocks, no
`option_defaults`, no model/effort tiering, and no nudge/idle settings.** This
pack does not ship or own any agent identity of its own — it is a provider/bridge
that routes Discord traffic into whatever named sessions/agents already exist in
the target city (created elsewhere, e.g. from rig/pool templates), rather than
defining agents itself. Grepping the whole pack for `option_defaults`,
`[[role]]`, `named_session`, `[[order]]`, "patrol", and "cadence" turns up zero
matches outside this note.

The pack does ship one **prompt fragment** that gets attached to sessions it
creates or that are addressed through it (see §3/§5):

- `template-fragments/discord-v0.template.md`, template name `discord-v0`
  (`{{ define "discord-v0" -}} ... {{- end }}`). Its operating contract for an
  agent dropped into a Discord thread:
  - "Everyone in this thread sees every message — humans and agents alike.
    There is no private channel."
  - Response heuristic: respond when named directly or when multiple agents
    are named; use judgment when no one is named but you have relevant info;
    stay silent if another agent already handled it; don't pile on if a
    conversation is human↔other-agent unless you have something important.
  - Hard boundary: "Normal assistant output stays private to the session. Do
    not assume a human on Discord can see it." If the event carries
    `reply_contract: explicit_publish_required`, that contract must be
    followed literally — plain output does not go back to Discord.
  - The only sanctioned reply path is `gc discord reply-current --body-file
    <path>`; agents must prefix replies with their handle in bold (e.g.
    `**randy:** `), must use `--body-file` (not inline `--body`) for anything
    non-trivial, must not pipe the command through filters that could hide
    failures, and may only claim success once the returned JSON has a
    non-empty `record.remote_message_id`.
  - Peer addressing convention: use `@name` to address a specific peer agent
    in the shared thread.
  - Threads are created automatically when a human `@mentions` an agent in a
    room; the agent must not try to create threads itself.

  This fragment is injected programmatically — see `_build_discord_prompt_fragment`
  in `scripts/discord_intake_common.py` (line ~2538) — when the bridge
  materializes a launcher-room thread session, not declared as a per-role
  template binding in `pack.toml` (there is none).

## 3. Named sessions

**None defined in `pack.toml`.** There is no `[[named_session]]` (or equivalent)
table in this pack — no template name/scope/mode triple is declared anywhere in
`pack.toml`, `README.md`, or the scripts' static config.

What the pack does instead, at runtime, is **create sessions on demand** from
existing city session templates when a launcher room or a fresh mention needs
one:

- `scripts/discord_intake_common.py: _create_session_from_template(template_name,
  alias, initial_message)` (line ~2510) calls the local `gc` API
  (`POST /v0/sessions`) to spin up a new session from a named template — the
  template name comes from the resolved `rig/alias` handle typed in Discord
  (e.g. `@@corp/sky`), not from any pack-declared named session.
- `create_agent_session` (line ~3265) and `ensure_room_launch_session_for_handle`
  / `ensure_room_launch_session` (lines ~3441, ~3581) drive on-demand,
  thread-scoped session creation for launcher rooms: the "mode" is effectively
  **on-demand, one session per (launch room, agent handle, thread)** rather
  than an always-on named session. Sessions created this way get the
  `discord-v0` prompt fragment injected via `_build_discord_prompt_fragment`.

In short: this pack is a consumer/creator of sessions via the generic `gc`
session API, not a definer of standing named sessions — that responsibility (if
any) lives with whatever rig/pool templates the city's other packs declare.

## 4. Orders shipped

**None.** `pack.toml` defines no `[[order]]` table and no patrol/cadence/condition
triggers of any kind — confirmed by grep across `pack.toml`, `README.md`, and
`REVIEW-implementation.md` for `order`, `patrol`, `cadence`. The pack's only
scheduled/continuously-running behavior is the `discord-gateway` **service**
(a persistent WebSocket client, not an order/patrol construct): it runs
`GatewayWorker.run_forever` in `scripts/discord_gateway_service.py`, handling
Discord's identify/resume/heartbeat protocol continuously while the workspace
is up, and reconnects with bounded backoff (5s–60s) on drop. There is no
condition-triggered or interval-cadence "order" object anywhere in this pack;
all "triggering" is event-driven (an inbound Discord Gateway `MESSAGE_CREATE`
event, or a slash-command interaction HTTP POST), not scheduled.

The closest thing to a recurring workflow is the **`mol-discord-fix-issue`
formula** (see §5), which is dispatched per-request via `gc sling`, not on a
cadence.

## 5. Assets/scripts/workflows bundled

### Commands (11, each a `commands/<name>.sh` shim + `commands/<name>/command.toml` +
`commands/<name>/help.md`, invoked as `gc discord <name>`)

All shims are near-identical: check `GC_CITY_PATH`/`GC_PACK_DIR` are set, then
`exec python3 "$GC_PACK_DIR/scripts/<script>.py" "$@"`.

| Command | Script | Purpose |
|---|---|---|
| `bind-dm` | `discord_chat_bind.py --kind dm` | Bind one Discord DM channel to exactly one named session |
| `bind-room` | `discord_chat_bind.py --kind room` | Bind a channel/thread to one or more named sessions; optional ambient-read + peer-fanout policy flags; mutually exclusive with `enable-room-launch` for the same room |
| `enable-room-launch` | `discord_room_launch.py` | Turn a root room into a launcher (`mention_only` or `respond_all` with `--default-handle`) |
| `import-app` | `discord_intake_import.py` | Store Discord application id, Ed25519 public key, bot token (+ optional guild/channel/role allowlists) |
| `map-channel` | `discord_intake_map_channel.py` | Map a guild channel to a `rig/pool` sling target for `/gc fix` |
| `map-rig` | `discord_intake_map_rig.py` | Map a guild + rig name to a `rig/pool` sling target for `/gc fix <rig>` |
| `post-message` | `discord_intake_post_message.py` | Post a status message via the bot token (used by the formula) |
| `publish` | `discord_chat_publish.py` | Operator-facing: publish a human-visible message through a saved binding (`--binding room:<id>` / `--binding launch-room:<id>`) |
| `release-workflow` | `discord_intake_release_workflow.py` | Clear a stuck per-conversation `/gc fix` workflow lock |
| `reply-current` | `discord_chat_reply_current.py` | Agent-facing preferred reply path: resolves the latest `<discord-event>` in the current session transcript and replies through its saved binding |
| `retry-peer-fanout` | `discord_chat_retry_peer_fanout.py` | Re-drive saved peer-fanout target records on a publish record without reposting to Discord |
| `status` | `discord_intake_status.py` | Redacted snapshot: URLs, config, gateway state, mappings, bindings, launchers, recent activity |
| `sync-commands` | `discord_intake_sync_commands.py` | Register/replace the guild-scoped `/gc` slash command |

### Doctor checks (7, `doctor/<name>/doctor.toml` + `doctor/check-<name>.sh`)

`bd`, `gc`, `git`, `jq`, `openssl` — simple `command -v` presence checks with a
purpose-specific message (e.g. openssl "for Discord Ed25519 signature
verification"). `python` additionally hard version-gates on Python ≥ 3.11,
exiting 2 with a clear message otherwise. `legacy-pack-conflict` checks
`$GC_CITY_ROOT (or GC_CITY_PATH)/.gc/services/discord-intake/{data/config.json,
secrets/bot-token.txt}` and fails (exit 2) with a migration instruction if
either exists — the residual-state guard mentioned in §1. Only
`legacy-pack-conflict` has automated tests (`tests/test_discord_doctor_scripts.py`);
the other six are untested simple checks.

### Formula: `formulas/mol-discord-fix-issue.formula.toml`

A 6-step, Discord-first bugfix workflow attached to the bead created by `/gc
fix`. Declared vars include `issue`, `discord_request_id`,
`discord_guild_id`, `discord_channel_id`, `discord_thread_id`,
`discord_conversation_id`, plus base64-encoded `discord_jump_url_b64`,
`discord_requester_b64`, `discord_summary_b64`, `discord_context_b64` (base64
used for safe interpolation into shell heredocs). Steps: `load-context` (prime
session, `bd show`, post a "work started" Discord message exactly once via
`gc discord post-message --request-id ...`, recording the posted message id on
bead metadata to dedupe) → `workspace-setup` (git worktree + deterministic
`fix-discord-<issue>` branch) → `understand-bug` → `write-tests-first`
(TDD-required) → `implement-fix` → `wrap-up` (post a completion message with
branch/worktree, then **always** release the intake workflow lock via
`gc discord release-workflow --request-id ...` in a trap, even if the Discord
post failed, before finishing via `gt done` or a manual worktree-removal +
`bd close` fallback).

### Scripts (`scripts/*.py`, ~9,540 total lines)

- **`discord_intake_common.py`** (~4,920 lines) — the shared library nearly
  everything else imports. Central responsibilities:
  - State-root path helpers (`state_root`, `data_dir`, `secrets_dir`,
    `config_path`, `secret_path`, per-record dirs for requests/receipts/
    workflows/pending-modals/chat-publishes/chat-ingress/room-launches/
    channel-metadata/peer-root-budgets/locks) and atomic JSON/text writers
    with restrictive permissions (`atomic_write_json` default `0o640`,
    `atomic_write_text` default `0o600`).
  - Config model: `default_config`, `normalize_config`, chat binding/rig/channel
    mapping CRUD (`set_chat_binding`, `set_channel_mapping`, `set_rig_mapping`,
    `set_room_launcher`), peer-fanout policy normalization
    (`normalize_room_peer_policy`, `normalize_room_launch_peer_policy`),
    redaction (`redact_config`, `redact_chat_ingress_record`,
    `redact_chat_publish_record`, `redact_room_launch_record`,
    `redact_request_record`, `redact_gateway_status`).
  - Discord REST + signature verification: `discord_api_request` (base URL
    `DISCORD_API_BASE = os.environ.get("GC_DISCORD_API_BASE",
    "https://discord.com/api/v10")`), `verify_discord_signature` (Ed25519 via
    a shelled-out `openssl pkeyutl -verify -pubin -rawin` over
    `timestamp+body`, using throwaway `0o600` temp files it deletes in a
    `finally`), `post_channel_message` (`POST /channels/{id}/messages`),
    `sync_guild_commands` (`build_command_payload` + Discord's
    application-command registration endpoint).
  - Local `gc` control-plane client: `gc_api_base_url()` (default port
    `DEFAULT_GC_API_PORT = 9443`, overridable via `city.toml`'s `[api]` table
    or `GC_API_BASE_URL`; if a cross-city supervisor is discovered via
    `GET {DEFAULT_SUPERVISOR_API_BASE}/v0/cities` where
    `DEFAULT_SUPERVISOR_API_BASE = "http://127.0.0.1:8372"`, requests are
    instead scoped under `/v0/city/<workspace_name>`), `gc_api_request` (the
    single low-level HTTP wrapper all local API calls route through).
  - Session-delivery + extmsg bridge (see §6 for the full inbound/outbound
    path): `normalize_to_extmsg_message`, `deliver_to_extmsg` (`POST
    /v0/extmsg/inbound`), `launch_thread_for_mentions`, `add_participants_to_thread`
    (extmsg groups/participants/bindings/transcript-membership calls),
    `resolve_at_mentions`/`resolve_nl_agent_mentions`/`resolve_mention_targets`,
    `_create_session_from_template`, `_build_discord_prompt_fragment`,
    `deliver_session_message` (`POST /v0/session/{selector}/messages` or
    `.../submit`), `find_latest_discord_reply_context` /
    `load_session_transcript_raw` (`GET /v0/session/{selector}/transcript?
    format=raw&tail=N`) used by `reply-current` to recover the last
    `<discord-event>` envelope from a session's own transcript.
  - Publish + peer-fanout pipeline: `publish_binding_message` (the single
    function both `publish` and `reply-current` call), `resolve_publish_destination`,
    `_resolve_peer_targets`, `_build_peer_envelope`, `_apply_peer_fanout`,
    `retry_peer_fanout`, `peer_delivery_exit_code`. **Important:**
    `publish_binding_message` builds and saves the chat-publish record but
    never calls `_apply_peer_fanout`/`deliver_session_message` — the code
    comment at that call site reads: *"Peer notification is now handled by
    the extmsg outbound orchestrator via transcript membership — no
    pack-side fanout needed."* No such orchestrator exists inside this
    pack's files. This is independently confirmed by
    `tests/test_discord_chat_scripts.py`, which repeatedly asserts
    `deliver_session_message.assert_not_called()` after a publish, and
    asserts `peer_delivery` is absent from the resulting record even in
    tests whose names suggest fanout occurs (see §7).
  - Workflow-target validation: `validate_fix_dispatch_target` (line ~1675)
    enforces the target has a `rig/pool` shape.
- **`discord_gateway_service.py`** (~2,320 lines) — the `discord-gateway`
  service entry point. Implements a **hand-rolled WebSocket client from raw
  TCP sockets** (`GatewayWebSocket`: manual HTTP Upgrade handshake, manual
  frame masking/fragmentation — no `websockets` or `discord.py` dependency).
  `GatewayWorker` drives identify/resume/heartbeat with
  `GATEWAY_INTENTS = (1 << 0) | (1 << 9) | (1 << 12) | (1 << 15)` = `GUILDS |
  GUILD_MESSAGES | DIRECT_MESSAGES | MESSAGE_CONTENT`. Two parallel inbound
  routing paths exist:
  1. **`_record_extmsg_inbound`** (line ~1919) is tried first on every
     `MESSAGE_CREATE`: for a root-room message with an explicit `@mention`
     and no matching legacy binding, it calls `launch_thread_for_mentions`
     to create a Discord thread + extmsg group + agent session(s), then
     posts a normalized `ExternalInboundMessage` to `/v0/extmsg/inbound`; for
     a message inside an already-extmsg-managed thread, it normalizes and
     posts every message to the same endpoint (adding new `@mention`ed
     participants along the way). It explicitly skips (returns `False`) when
     an **explicit legacy room binding already claims the channel**
     (`bound_room_claims_message`), so sticky bound rooms are not hijacked
     by the newer extmsg auto-launch path.
  2. **`process_inbound_message`** (line ~1243, "legacy" path) runs when the
     extmsg path declines. It: ignores bot-authored messages; for guild
     messages resolves room-launcher config, else falls back to a
     bound-room/ambient-read binding, else requires an explicit bot mention;
     claims the event exactly once via `save_chat_ingress_if_absent` keyed
     by the Discord message id (with reclaim logic for stale
     `processing`/`failed` receipts); and finally builds one of three
     `<discord-event>` text envelopes (`build_bound_room_envelope` (~line
     690), `build_room_launch_envelope` (~730),
     `build_room_launch_thread_envelope` (~776)) and delivers it into the
     resolved named session(s) via `deliver_session_message` → `POST
     /v0/session/{selector}/messages`.
  Serves `GET /healthz` and `GET /v0/discord/gateway/status` on a small local
  HTTP server (line ~2244).
- **`discord_intake_common.py`'s sibling intake scripts** — the
  `discord_intake_*.py` naming covers the `/gc fix` slash-command pipeline;
  `discord_chat_*.py` covers the session chat control plane. Both share
  `discord_intake_common.py`, whose name understates how much
  chat/gateway/peer-fanout logic it now holds (a documented naming smell in
  `REVIEW-implementation.md`, not a functional bug).
  - `discord_intake_service.py` (~1,368 lines) — the `discord-interactions` /
    `discord-admin` HTTP service (behavior branches on `GC_SERVICE_NAME`).
    Serves the interactions endpoint (`POST /v0/discord/interactions`,
    verifying signatures and answering Discord's `type: 1` PING directly),
    plus JSON/HTML endpoints `GET /healthz`, `GET /v0/discord/status`, `GET
    /v0/discord/requests`, `POST /v0/discord/app/import`, `POST
    /v0/discord/bot-token/import`, `POST /v0/discord/commands/sync`.
    `accept_fix_request` enforces `policy_reason` (guild/channel/role
    allowlist) before creating a bead and dispatching. `run_fix_dispatch`
    shells out `gc sling <target> <bead_id> --on <formula>` (env
    `GC_BIN`/`BD_BIN` overridable binary names) with `--var key=value` pairs
    from `build_fix_vars`. `rig_workdir(rig)` (line ~364) resolves a rig's
    working directory by reading `.beads/routes.jsonl` line by line and
    matching each entry's `path` against the rig name **either by exact path
    or by `os.path.basename(path)`** — see §7 for why this matters relative
    to known flat-layout assumptions elsewhere in Gas City packs.
  - `discord_intake_import.py`, `discord_intake_map_channel.py`,
    `discord_intake_map_rig.py`, `discord_intake_post_message.py`,
    `discord_intake_release_workflow.py`, `discord_intake_sync_commands.py`,
    `discord_intake_status.py` — thin argparse CLIs over the corresponding
    `discord_intake_common.py` functions (import app/bot-token, set a
    channel/rig mapping, post a status message, release a workflow lock,
    sync guild slash commands, render a status snapshot).
  - `discord_chat_bind.py`, `discord_chat_publish.py`,
    `discord_chat_reply_current.py`, `discord_chat_retry_peer_fanout.py` —
    thin argparse CLIs for binding creation, operator publish, agent
    reply-current, and peer-fanout retry, all delegating to
    `discord_intake_common.py`.
  - `discord_room_launch.py` — CLI for `enable-room-launch`; resolves
    `--default-handle` via `common.resolve_agent_handle` and calls
    `common.set_room_launcher`.

### Template fragment

`template-fragments/discord-v0.template.md` — see §2.

### Tests (`tests/test_*.py`, skimmed)

- `test_discord_chat_scripts.py` — bind/publish/reply-current/retry-peer-fanout
  behavior, including the peer-fanout non-invocation assertions noted above,
  and that `bind-room` and `enable-room-launch` are mutually exclusive per
  conversation (`ValueError`).
- `test_discord_doctor_scripts.py` — only the legacy-pack-conflict doctor check
  is exercised.
- `test_discord_gateway_service.py` — gateway WebSocket framing/handshake,
  `process_inbound_message` routing branches (mentions, ambient-read,
  launcher rooms, idempotent ingress claiming).
- `test_discord_intake_common.py` — config normalization, mapping resolution,
  redaction, signature verification helper behavior.
- `test_discord_intake_service.py` — `/gc fix` interaction handling, policy
  allowlist enforcement, dispatch subprocess behavior.
- `test_discord_release_workflow.py` — workflow-lock release semantics.

No dedicated tests exist for the `map-channel`, `map-rig`, `sync-commands`, or
`room-launch` CLI entry points as standalone scripts — their underlying
`common` functions are tested, but not the argparse wrappers (`REVIEW-implementation.md`
§3.6, independently consistent with the test file list above).

## 6. End-to-end wiring

There is no `pack.toml`→named_session→agent→prompt→order chain in this pack
(§§2-4 establish those tables are absent). The real wiring is
`pack.toml` (services) → running Python service → Discord REST/Gateway calls
↔ local `gc` control-plane API → named session(s) → prompt fragment →
explicit reply command → Discord REST. Concretely:

### Inbound (Discord → agent)

1. Discord delivers a Gateway `MESSAGE_CREATE` event over the persistent
   WebSocket connection opened by the **`discord-gateway`** service
   (`scripts/discord_gateway_service.py`), identified with intents `GUILDS |
   GUILD_MESSAGES | DIRECT_MESSAGES | MESSAGE_CONTENT` (bitmask
   `GATEWAY_INTENTS = (1<<0)|(1<<9)|(1<<12)|(1<<15)`).
2. `GatewayWorker.handle_gateway_message` first tries
   `_record_extmsg_inbound`: if this is a root-room message with an explicit
   `@mention` and no existing legacy binding claims the channel, it calls
   `common.launch_thread_for_mentions(...)` (creates the Discord thread,
   an **extmsg group**, and one or more new agent sessions via
   `_create_session_from_template` → `POST /v0/sessions`), then normalizes the
   message with `common.normalize_to_extmsg_message(...)` and posts it via
   `common.deliver_to_extmsg(...)` → **`POST /v0/extmsg/inbound`** on the
   local `gc` API. Inside an already-managed extmsg thread, every message is
   normalized and posted the same way (with `explicit_target` set from
   `@mention`s or NL name matches), and new `@mention`s trigger
   `common.add_participants_to_thread(...)` (which itself calls
   `POST /v0/extmsg/groups`, `POST /v0/extmsg/groups/participants`, `POST
   /v0/extmsg/bindings`, `POST /v0/extmsg/transcript/membership`).
3. If step 2 declines (explicit legacy binding claims the room, or no
   `@mention` in an unmanaged room), `process_inbound_message` (the "legacy"
   path) runs instead: it ignores bot-authored messages; for a guild message
   checks room-launcher config, then bound-room/ambient-read binding, then
   falls back to requiring an explicit bot mention; claims the event exactly
   once via `common.save_chat_ingress_if_absent` (idempotency keyed by
   Discord message id, with reclaim rules for stale `processing`/`failed`
   receipts); resolves target session(s) (bound session name(s), or a
   launcher's on-demand thread session via
   `common.ensure_room_launch_session_for_handle`); builds a `<discord-event>`
   text envelope (functions `build_bound_room_envelope` /
   `build_room_launch_envelope` / `build_room_launch_thread_envelope`) whose
   fields include `binding_id`, `ingress_receipt_id`, `conversation`,
   `discord_message_id`, `from_display`/`from_user_id`,
   `publish_binding_id`/`publish_conversation_id`/`publish_trigger_id`/
   `publish_reply_to_discord_message_id`, and critically
   **`normal_output_visibility: internal_only`** and **`reply_contract:
   explicit_publish_required`** plus a literal `reply_tool: gc discord
   reply-current --conversation-id <id> --reply-to <id> --body-file <path>`
   line; and delivers that envelope via `common.deliver_session_message(...)`
   → **`POST /v0/session/{selector}/messages`** (or `.../submit`) on the local
   `gc` API.
4. The `/gc fix` slash-command path is separate and HTTP-only: Discord POSTs
   the interaction to the public **`discord-interactions`** service at
   **`/v0/discord/interactions`**; `discord_intake_service.py` verifies the
   Ed25519 signature (`common.verify_discord_signature`, shelling out to
   `openssl pkeyutl -verify -pubin -rawin`) and a ≤10-second timestamp
   freshness window before doing anything else, answers Discord's `type: 1`
   PING directly, then on a real `/gc fix` submission calls
   `accept_fix_request` → policy allowlist check → `create_fix_bead` → `run_fix_dispatch`,
   which shells `gc sling <rig>/<pool> <bead_id> --on mol-discord-fix-issue
   --var key=value ...` (binaries overridable via `GC_BIN`/`BD_BIN` env vars).
   The dispatched formula's steps use `gc discord post-message` /
   `gc discord release-workflow` to talk back to the same conversation (see
   §5's formula summary).
5. Either way, the agent session receives a message whose prompt context
   includes the `discord-v0` template fragment
   (`template-fragments/discord-v0.template.md`) — for extmsg-managed
   sessions injected via `_build_discord_prompt_fragment` at session-creation
   time — instructing it that its normal output is private and that it must
   call `gc discord reply-current` to speak back to Discord.

### Outbound (agent → Discord)

1. The agent (or an operator) runs **`gc discord reply-current --body-file
   <path>`** (preferred) or **`gc discord publish --binding <id> --body-file
   <path>`** (operator/cross-binding path).
2. `discord_chat_reply_current.py` calls
   `common.find_latest_discord_reply_context(...)`, which reads the current
   session's own transcript via **`GET /v0/session/{selector}/transcript?
   format=raw&tail=N`** on the local `gc` API and extracts the most recent
   `<discord-event>` envelope's `publish_binding_id` /
   `publish_conversation_id` / reply-threading fields.
3. Both scripts converge on **`common.publish_binding_message(...)`**, which
   calls `resolve_publish_destination(...)` (creates the managed Discord
   thread on the launcher's first reply if needed) and
   `common.post_channel_message(...)` → Discord REST **`POST
   /channels/{channel_id}/messages`** (via `discord_api_request`, base URL
   `DISCORD_API_BASE = os.environ.get("GC_DISCORD_API_BASE",
   "https://discord.com/api/v10")`, bot-token-authenticated, retrying up to 2×
   on HTTP 429 honoring `Retry-After`). The response's message `id` becomes
   `record.remote_message_id` — the field the prompt fragment tells agents to
   check before claiming success. The publish record is saved via
   `common.save_chat_publish(...)`, but (see §5/§7) **no peer-fanout delivery
   call happens from this path today**, despite `record.peer_delivery` /
   exit-code-2 semantics being documented and partially implemented
   (`_apply_peer_fanout`, `retry_peer_fanout`).
4. `gc discord post-message` (used by the `mol-discord-fix-issue` formula) is
   a simpler variant: it resolves a target channel/thread from a saved
   `request_id` (or explicit `--channel-id`/`--thread-id`) and calls
   `common.post_channel_message` directly — no chat-binding indirection.

### Naming/label conventions found in code

- Chat binding ids: `f"{kind}:{conversation_id}"` via
  `chat_binding_id(kind, conversation_id)` (e.g. `room:1234567890`,
  `dm:1234567890`); launcher ids as `f"launch-room:{conversation_id}"`.
- Channel/rig mapping keys: `normalize_channel_key(guild_id, channel_id)` and
  `normalize_rig_key(guild_id, rig_name)` = `f"{guild_id}/{channel_id}"` /
  `f"{guild_id}/{rig_name}"`.
- `<discord-event>` / `</discord-event>` is the literal envelope delimiter
  agents' prompts are told to parse; `discord_human_message` and
  `discord_peer_publication` are the two `kind` values in use.
- extmsg conversation `kind` values: `dm`, `thread`, `room`
  (`normalize_to_extmsg_message`).

## 7. Watch-outs for a copier/integrator

- **`gp-00t`-style flat-layout rig-name==routes-path assumption — present as a
  pattern, but implemented defensively, not naively.** `discord_intake_service.py:
  rig_workdir(rig)` (line ~364) resolves a rig's working directory by reading
  `.beads/routes.jsonl` and matching each entry's `path` field against the rig
  name **by exact path match OR by `os.path.basename(path) == rig`** — i.e. it
  does not assume the rig name literally *is* the routes path; it accepts a
  routes entry whose path's basename equals the rig name, which tolerates
  non-flat layouts where the rig lives in a subdirectory. It does, however,
  still assume rig names are unique by basename within `routes.jsonl` (a
  `corp/api` and `other/api` rig would collide on `basename == "api"`), and it
  requires the resolved path to be inside (or equal to) the city root
  (`resolved == root_abs or resolved.startswith(root_abs + os.sep)`), silently
  returning `""` (falls back to city root) if no entry matches or the match
  escapes the root. Copiers should verify `.beads/routes.jsonl` has unique
  basenames per rig if they rely on `map-rig`/`/gc fix <rig>` dispatch.
- **`gp-vwa`-style order+`github_app_token_env` delivery bug — not applicable.**
  This pack defines no `[[order]]` blocks at all (§4), so there is no
  order-based credential-delivery path to exhibit that bug pattern. Grepping
  the whole pack for `github_app_token_env`, `token_env`, and any per-order
  env-var wiring turns up nothing; the only token handling is the pack's own
  `secrets/bot-token.txt` file (see below), read directly by
  `save_bot_token`/`load_bot_token`, not routed through an order/env-var
  indirection layer.
- **Peer fanout is documented and CLI-flagged but not actually wired.**
  `bind-room --enable-peer-fanout`, `enable-room-launch`'s default
  peer-fanout-on-for-threads behavior, the `retry-peer-fanout` command, and
  the exit-code-2 "peer fanout needs attention" contract described in
  `publish`/`reply-current` help text all describe behavior that
  `publish_binding_message` does not currently invoke (its own comment says
  peer notification is "now handled by the extmsg outbound orchestrator ...
  no pack-side fanout needed" — no such orchestrator exists in this pack).
  Confirmed independently via `tests/test_discord_chat_scripts.py`'s
  `deliver_session_message.assert_not_called()` assertions after publish.
  `retry-peer-fanout`'s own tests only pass by injecting a synthetic
  `peer_delivery` record directly, bypassing the real publish path. Do not
  advertise this as working functionality to an integrator without flagging
  it.
- **Guild/channel/role allowlists only gate `/gc fix`.** `policy.guild_allowlist`
  / `channel_allowlist` / `role_allowlist` (set via `import-app`) are checked
  only in `accept_fix_request`'s `policy_reason`. DM bindings, room bindings,
  ambient-read rooms, and launcher rooms have **no equivalent allowlist
  enforcement** — routing is governed solely by whether a binding/launcher
  record exists for that conversation id. The real access-control boundary
  for chat surfaces is therefore "who is allowed to run
  `bind-dm`/`bind-room`/`enable-room-launch`", not any Discord-side
  allowlist.
- **Required env/creds:**
  - Discord app: **Application ID**, **Interactions public key** (Ed25519 hex,
    64 chars), **bot token** — imported via `gc discord import-app`
    (`--bot-token` or `--bot-token-file`); stored at
    `secrets/bot-token.txt` with `0o600` perms (dir `0o700`), read only via
    `save_bot_token`/`load_bot_token`; never exposed by status endpoints
    beyond a boolean `bot_token_present`. No rotation tooling — re-running
    `import-app` overwrites the token file.
  - `GC_DISCORD_API_BASE` — override for Discord's own API base
    (default `https://discord.com/api/v10`); useful for tests/staging.
  - `GC_API_BASE_URL` — override for the local `gc` control-plane API base
    (otherwise derived from `city.toml`'s `[api]` table, default port `9443`,
    or from supervisor discovery against `http://127.0.0.1:8372/v0/cities`
    when a multi-city supervisor is present).
  - `GC_CITY_ROOT` / `GC_CITY_PATH`, `GC_SERVICE_NAME` (distinguishes
    `discord-interactions` vs `discord-admin` in the one shared script),
    `GC_SERVICE_STATE_ROOT`, `GC_SERVICE_SECRETS_DIR`, `GC_SERVICE_SOCKET`,
    `GC_PUBLISHED_SERVICES_DIR`, `GC_SERVICE_PUBLIC_URL`,
    `GC_SESSION_NAME`/`GC_SESSION_ID` (session identity for peer-fanout /
    reply-current attribution), `GC_BIN`/`BD_BIN` (override the `gc`/`bd`
    binary names used by subprocess dispatch).
- **Message Content Intent is a hard prerequisite** for launcher rooms and
  ambient-read room bindings — Discord silently strips `content` on
  unmentioned guild messages unless this privileged Developer Portal toggle
  is enabled, even though the gateway always requests the `MESSAGE_CONTENT`
  intent bit.
- **`sync-commands` must be re-run after any command-schema change**,
  including immediately after migrating from `discord-intake` — Discord keeps
  enforcing the old registered schema (e.g. a previously required `rig`
  option) at the Discord API layer until the guild command is re-synced,
  producing a confusing client-side validation error unrelated to this
  pack's own logic.
- **One Discord application per city (or per isolation boundary).** Because
  `discord-interactions`/`discord-admin` service identities are shared and
  guarded against colliding with `discord-intake`, plan bot/app provisioning
  per city rather than assuming a single shared Discord app across multiple
  Gas City workspaces.
- **`bind-room` and `enable-room-launch` are mutually exclusive** for the same
  conversation id (raises `ValueError`, covered by tests) — a copier scripting
  bulk binding setup must check for this before applying both.
- **Hand-rolled WebSocket client** in `discord_gateway_service.py` (manual
  HTTP Upgrade handshake, manual frame masking/fragmentation) is tested but
  not a vetted library — any future Discord Gateway protocol change requires
  hand-patching this code rather than a dependency bump.
- **Version/ref pins:** Discord REST pinned to API version `v10`
  (`DISCORD_API_BASE` default `.../api/v10`); Gateway connection forces
  `v=10&encoding=json` (compress param stripped) in `gateway_connect_url`;
  Python ≥ 3.11 hard-gated by the `python` doctor check; pack itself is
  `version = "0.1.0"`, `schema = 2`. No pinned Discord library version since
  none is used (raw sockets).
