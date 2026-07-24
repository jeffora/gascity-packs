# Slack pack family — research notes (slack-mini, slack-channel, slack-full)

Source trees read in full for this doc:
`rigs/gascity-packs/slack-mini/`, `rigs/gascity-packs/slack-channel/`,
`rigs/gascity-packs/slack-full/`, plus the shared design memo at
`rigs/gascity-packs/docs/design/slack-pack-tiering.md`.

This doc is self-contained: a reader who has never opened these packs should
be able to understand what they do, how they're tiered, and how a message
flows end to end from either doc alone.

---

## 1. Purpose & scope

**Problem solved:** Gas City ("gc") runs multi-agent sessions (a "mayor"
session plus arbitrary named sessions per rig/pack). Humans want to talk to
those sessions from Slack — DM the bot, `@`-mention it in a channel, bind a
team channel to a set of sessions — and have agent replies land back in
Slack, optionally under a distinct per-agent identity, with reactions,
threading, file attachments, and (at the top tier) multi-rig routing and
slash-command/modal intake.

Each of the three packs is a **complete, independently-installable Slack
integration** for a gc city: a Go adapter binary that speaks the Slack Events
API and Slack Web API, plus a `gc <pack> <verb>` command surface. They are
**not layers that stack** — they are three alternative sizes of the same
integration, differing only in how much state and how many verbs they carry.

- **slack-mini** — Tier 1. "Talk to mayor from Slack." Single-file adapter,
  one outbound verb (`post-message`), `app_mention` → mayor. No on-disk
  registries at all. ~12–18 files.
- **slack-channel** — Tier 2. "Bind your team channel to your session
  graph." Multi-file adapter, 8 verbs, three on-disk registries (channel
  bindings, per-session identity, handle aliases). Single workspace,
  single rig. ~50–60 files.
- **slack-full** — Tier 3 (the original pack; the other two were later
  extracted from it). "Workspace-grade multi-rig orchestration surface."
  17 verbs, 6 registries, an operator CLI binary, OAuth app install, Block
  Kit modals, peer fanout, room launcher, file uploads, ~156+ files (roughly
  half tests).

**Decision guidance — which tier to pick:**

| If you need... | Pick |
| --- | --- |
| The mayor to post status into one channel, `@`-mention driven, nothing else | slack-mini |
| A handful of named sessions sharing one or more channels, each with a distinct Slack identity, address-by-`@handle` from any channel, reactions/threaded replies — but no slash commands or cross-rig routing | slack-channel |
| Slash commands, interactive modals/buttons, peer fanout across a room, launcher-mode session spawning (`@@handle`), multi-rig channel routing, file uploads, OAuth self-service app install | slack-full |

Each tier **strictly subsumes** the one below it (every Tier-N capability
exists in Tier N+1), which is what makes **upgrading** a pack swap: bot
token / signing secret / workspace id carry over unchanged, and any
on-disk registries the smaller pack wrote are read unchanged by the larger
pack. **Downgrading** is unsupported — the smaller pack doesn't know about
the larger pack's extra registry files, so they become orphaned (documented,
not auto-deleted). See the tiering memo
(`rigs/gascity-packs/docs/design/slack-pack-tiering.md`) for the full
migration and orphaning contract.

**Hard constraint: pick exactly one tier per city.** All three tiers declare
`[pack] name = "slack"` in a design sense — actually, in the shipped
`pack.toml`s the *pack* names differ (`slack-mini`, `slack-channel`,
`slack-full`) but the **gc `[[service]]` name and the `gc <verb>` CLI prefix
differ too** in the code as shipped today (`slack-mini`, `slack-channel`,
`slack` for slack-full — see §7 for the one real naming inconsistency found).
Regardless of exact naming, the tiering memo is explicit that the three are
**alternatives, not layers**: a city should install and run only one.

---

## 2. Roles/agents

**None of the three packs define any `agents/`, `orders/`, `[[agent]]`,
`[[order]]`, or named-session TOML blocks.** This was independently confirmed
by directory listing and grep across all three pack trees — there is no
`agents/` or `orders/` directory anywhere in `slack-mini/`, `slack-channel/`,
or `slack-full/`, and no `pack.toml` in this family declares an `[[agent]]`
or `[[order]]` table.

**What fills the gap instead:** the Slack pack family does not create or own
any personas. It is a *transport* — it bridges Slack conversations to gc's
existing agent surface:

- **Inbound**, every tier ultimately POSTs to gc's
  `/v0/city/{city}/extmsg/inbound` endpoint, addressed either to a
  hardcoded/configurable fallback session handle (`SLACK_MINI_INBOUND_TARGET`
  / `SLACK_CHANNEL_INBOUND_TARGET`, both defaulting to **`mayor`**) or,
  starting at Tier 2, to whatever session id a channel binding or handle
  alias names. The **mayor session is gc's own pre-existing agent surface**
  — the Slack pack does not spawn it, name it, or configure its behavior.
  It is simply the default addressee when nothing more specific is bound.
- **Outbound**, a gc session (any session — mayor or any other) calls a
  `gc <pack> <verb>` command from inside its own execution context; the
  pack's job is only to relay that call to Slack's Web API under the
  session's optional identity override.
- At Tier 3, `slack-full` adds a **room-launcher** mode
  (`@@<handle>` in an enabled channel) that *can* spawn a new gc session on
  demand (`room_launch_dispatch.go`, `thread_session_registry.go`) — but even
  this is generic session-spawning through gc's existing session-create API,
  driven by an operator-supplied opaque "pool_template" string. The pack
  has, per its own `enable_room_launch.go` comment, "ZERO" opinion about what
  that pool template means; it is not an agent/persona defined by the pack.

**Contrast with an agents/orders-bearing pack (e.g. the sibling Discord
pack):** a pack that *does* ship `[[agent]]` / `[[order]]` / named-session
declarations would define its own persona(s) directly in `pack.toml` —
e.g. a named agent with a system prompt, a set of orders (skills/commands)
scoped to that agent, and possibly a named_session binding baked into the
pack itself, so importing the pack alone stands up a working agent identity.
The Slack pack family deliberately does none of this: it assumes the
consuming city (or a *different*, consumer-side pack — the README calls out
`oversight-rig` as the pack that actually names sessions like
`oversight-rig.chief-of-staff`) already has the agents/sessions it wants
wired up, and the Slack pack's only job is to plumb Slack traffic to and
from whatever session ids or aliases the operator points it at via CLI/verb
calls (`bind-dm`, `bind-room`, `identity`, `handle-alias`, `map-channel`,
`map-rig`). The one consumer-facing artifact that gestures at "persona" is
`slack-full/template-fragments/slack-v0.template.md` — a **composable prompt
fragment** ("You are bound to a Slack conversation... reply protocol...")
that a *consumer* pack can `{{ define "slack-v0" }}`-include into its own
agent's system prompt. That is prompt content the pack ships for others to
compose with, not an agent definition of its own.

---

## 3. Named sessions

**None declared**, for the same reason as §2 — no `pack.toml` in any of the
three tiers declares a named_session table. Session identity is entirely
extrinsic: every verb that needs a session id takes it as a `--session` flag
or falls back to the ambient `$GC_SESSION_ID` environment variable that gc
sets for a command invoked from inside a session. Channel bindings, identity
overrides, and handle aliases are keyed by whatever session id/alias string
the operator supplies at bind time — the packs have no built-in notion of
"the mayor" beyond a configurable *string* used as the inbound-routing
fallback default.

---

## 4. Orders shipped (command surface)

Terminology note: this pack family calls its order-analog surface
"commands" / "verbs" (`gc <pack> <verb>`), backed by `commands/<verb>.sh` +
`command.toml` + `help.md` per gc's three-file convention. Treated here as
the "Orders shipped" section for cross-pack comparability.

### slack-mini (Tier 1) — 1 verb

| Verb | Wraps | Flow role |
| --- | --- | --- |
| `post-message` | Bash wrapper → adapter's internal `/post-message` endpoint (via gc's `/svc/slack-mini` reverse proxy) | **Outbound only.** `--channel`, `--text`, `--thread-ts`. The adapter holds the bot token and calls Slack `chat.postMessage`; the token never enters the command environment. |

No operator CLI binary at this tier.

### slack-channel (Tier 2) — 8 verbs, all bash wrappers, no CLI binary

| Verb | Wraps (adapter endpoint) | Flow role |
| --- | --- | --- |
| `bind-dm <channel> <session...>` | `POST /bindings` (kind=dm) | Registers a DM channel → N sessions. Every non-mention message in that DM is delivered to all N. |
| `bind-room <channel> <session...>` | `POST /bindings` (kind=room) | Same, for a room/channel. |
| `publish --body <text>` | `POST /publish` | Outbound: post into the single channel the calling session is bound to (fails if bound to 0 or >1 channels). |
| `publish-to-channel --channel <id> --body <text>` | `POST /publish-to-channel` | Outbound: post to any channel id directly, bypassing binding lookup. |
| `reply-current --body <text> [--thread-current] [--reply-to <ts>]` | `POST /reply-current` | Outbound: reply into the conversation of the session's most recent inbound message (in-memory `lastInbound` map), optionally threaded. |
| `react [--emoji <name>]` | `POST /react` | Outbound: add an emoji reaction to the session's latest inbound message, or an explicit (channel, ts) pair. |
| `identity --as <name> [--avatar-url\|--avatar-emoji] [--remove]` | `POST /identity` / `DELETE /identity` | Registers/removes a per-session Slack username+avatar override (`chat:write.customize`). |
| `handle-alias --handle <h> --session <id> [--remove]` | `POST /handle-alias` / `DELETE /handle-alias` | Registers/removes a `@handle → session` alias so any channel can address that session by name. |

All eight share `commands/_lib.sh`, which resolves the adapter's base URL
(gc's `/v0/city/{city}/svc/slack-channel` reverse-proxy path, overridable via
`SLACK_CHANNEL_ADAPTER_URL`) and POSTs JSON built with `jq`.

### slack-full (Tier 3) — 17 verbs total (9 inherited-shape + 8 new)

Command wrappers split cleanly into two implementation backends:

- **Python-backed** (`exec python3 "$GC_PACK_DIR/scripts/slack_chat_<verb>.py"`):
  `bind-dm`, `bind-room`, `handle-alias`, `identity`, `publish`,
  `publish-to-channel`, `react`, `reply-current`, `retry-peer-fanout`,
  `status`, `upload`.
- **Go-CLI-backed** (`exec "$GC_PACK_DIR/cli/gc-slack-cli" <verb> "$@"`):
  `enable-room-launch`, `import-app`, `map-channel`, `map-rig`,
  `post-message`, `sync-commands`, `sync-subteam-aliases`.

Confirmed: the Python scripts under `scripts/slack_chat_*.py` **are** the
actual outbound-verb implementations the bash wrappers call into — each
wrapper is a one-line `exec` into its matching script, and the scripts
themselves call gc's HTTP API (`/extmsg/outbound`, `/extmsg/bind`, etc.) or
the local adapter directly (`--via adapter` diagnostic path), never touch
Slack's API themselves except by delegating to the adapter's `/publish` /
`/publish-file` / `/react`. `slack_intake_common.py` is the shared helper
module (gc API base resolution, CSRF header, adapter-env fallback loading).

| Verb | Purpose | Backend |
| --- | --- | --- |
| `bind-dm` | Bind a DM to one named session | Python (`slack_chat_bind.py`) |
| `bind-room` | Bind a room to multiple sessions; creates a launcher-mode group with peer-fanout policy flags (`--enable-peer-fanout`, `--allow-untargeted-publication`, `--max-peer-triggered-publishes`, `--max-total-peer-deliveries`, `--default-handle`, `--handle H=S`, `--binding-owner`) | Python (`slack_chat_bind_room.py`) |
| `publish` | Publish to a session's saved gc binding; fails fast if unbound | Python (`slack_chat_publish.py`) |
| `publish-to-channel` | Publish to an arbitrary channel id, no binding required | Python (`slack_chat_publish_to_channel.py`) |
| `reply-current` | Reply to the latest Slack event seen by the session, via gc `/extmsg/outbound` (default) or `--via adapter` direct | Python (`slack_chat_reply_current.py`) |
| `react` | Add an emoji reaction (default: to latest inbound; or explicit `--conversation-id`/`--message-id`) | Python (`slack_chat_react.py`) |
| `identity` | Register/unregister a per-session `chat:write.customize` identity | Python (`slack_chat_identity.py`) |
| `handle-alias` | Register/unregister a cross-channel `@handle → session` alias | Python (`slack_chat_handle_alias.py`) |
| `upload` | Bidirectional file attachment: gc-routed (`/extmsg/outbound-file`, default) or `--via adapter` direct to `/publish-file` | Python (`slack_chat_upload.py`) |
| `status` | Read-only diagnostics: adapters, bindings, recent traffic (`--session`, `--since`, `--json`) | Python (`slack_chat_status.py`) |
| `retry-peer-fanout` | Re-drive failed peer-fanout deliveries via gc's retry endpoint, deduped against successful retries | Python (`slack_chat_retry_peer_fanout.py`) |
| `import-app` | Register a Slack app manifest into the apps registry (`apps.json`) | Go CLI (`cli/cmd/import_app.go`) |
| `map-channel` | Bind a Slack channel → session (or, deprecated, `--rig`); backs the adapter's `/slack/interactions` slash-command dispatcher | Go CLI (`cli/cmd/map_channel.go`) |
| `map-rig` | Bind a rig → set of channels as slash-command fall-through default; channel mapping wins over rig default | Go CLI (`cli/cmd/map_rig.go`) |
| `enable-room-launch` | Write `(workspace, channel) → pool_template` for `@@<handle>` launcher mode. **CLI-side write works; adapter-side spawn is currently a stub** (returns "launcher not yet available") | Go CLI (`cli/cmd/enable_room_launch.go`) |
| `sync-commands` | Register/refresh the city's slash commands against the live Slack app | Go CLI (`cli/cmd/sync_commands.go`) |
| `sync-subteam-aliases` | Reconcile `subteam-aliases.json` (Slack User Group id → gc handle) against Slack's live `usergroups.list`; non-destructive merge, `--dry-run`, `--output text\|json` | Go CLI (`cli/cmd/sync_subteam_aliases.go`) |
| `post-message` | One-shot Block Kit message post (or `--update <ts>`) direct to Slack `chat.postMessage`/`chat.update`, bypassing `/publish`'s session-attribution guard | Go CLI (`cli/cmd/post_message.go`) |

Registry-writing verbs (`import-app`, `map-channel`, `map-rig`,
`enable-room-launch`, `sync-subteam-aliases`) print a trailing reminder
(`MapRigRestartReminder` constant) that a SIGHUP (`pkill -HUP
gc-slack-adapter`) or `gc service restart slack` is needed for the adapter to
pick up the change.

---

## 5. Assets/scripts/workflows

### Adapter Go source, per tier

**slack-mini** (`adapter/main.go`, ~660 lines, single file, module
`github.com/sjarmak/gc-slack-mini-adapter`, `go 1.25.9`): config loader +
validation, HMAC signature verify, `/slack/events` handler (URL-verification
handshake + `app_mention`-only routing), `bridgeEvent`/`postInbound` (POST to
gc `/extmsg/inbound`), `registerAdapter` (self-register as extmsg adapter),
`/post-message` outbound handler (`chat.postMessage`), UDS listener helper.
No registries.

**slack-channel** (`adapter/*.go`, module `github.com/sjarmak/gc-slack-channel-adapter`,
`go 1.25.9`), split into:
- `config.go` — env parsing/validation, registry-dir derivation
  (`GC_CITY_PATH`-based default, `SLACK_CHANNEL_REGISTRY_DIR` override).
- `server.go` — the `server` struct: two locks (`writeMu` serializes
  mutators across the disk flush; `regMu` RWMutex guards the in-memory
  registry maps so inbound reads never block on file I/O), three in-memory
  registries (`channels`, `identities`, `aliases`) mirrored to JSON files,
  plus an in-memory `lastInbound` map keyed by session id.
- `inbound.go` — `/slack/events` handler; `routeEvent` widens Tier 1's
  `app_mention`-only path to also handle plain `message.*` events: a message
  in a bound channel fans out to every bound session; a leading `@handle`
  match routes to the aliased session (handle stripped); an unbound
  unaliased `app_mention` falls back to the default inbound target; a plain
  unbound message with no alias is dropped.
- `outbound.go` — `/publish`, `/publish-to-channel`, `/reply-current`,
  `/react` handlers; applies the session's identity override; implements
  idempotency-key dedup (`postDedupCache`) so a retried POST replays the
  cached receipt instead of re-posting to Slack.
- `registries_http.go` — `/bindings`, `/identity` (POST/DELETE),
  `/handle-alias` (POST/DELETE) — the verb-mutation endpoints.
- `dedup.go`, `signature.go`, `slackclient.go`, `store.go`, `httputil.go`,
  `wire.go`, `gcclient.go` — supporting HMAC verify, atomic JSON persistence,
  Slack Web API client, extmsg wire types, gc registration client.
- `interactions.go` — `/slack/interactions` handler: verifies signature,
  acks with 200 (no custom modal handling — that's Tier 3).

**slack-full** (`adapter/*.go`, module `github.com/sjarmak/gc-slack-adapter`,
`go 1.25.9`), the largest surface — 33 Go source files. Beyond the Tier-1/2
concerns, notable files:
- `apps_registry.go` — the apps registry (`apps.json`), written by both the
  CLI (`import-app`) and the adapter's own OAuth callback (`oauth.go`);
  generation-stamped to avoid a SIGHUP racing an OAuth write.
- `oauth.go` — `/slack/oauth/start` + `/slack/oauth/callback`: self-service
  Slack app install flow (see §7 "docs/install.md").
- `interactions.go` / `interactions_modal.go` / `interactions_payloads.go` —
  full `/slack/interactions` dispatch for slash commands, `block_actions`,
  and `view_submission` (modal submit); channel-mapping and rig-mapping
  registries drive routing; unsupported interaction types get an ephemeral
  "unsupported" reply.
- `rig_dispatch.go` / `rig_mapping.go` / `rig_workdir.go` — multi-rig
  channel routing: a channel maps to a rig (fall-through default) or a
  session (override, wins); dispatch runs `bd`/`gc` subprocesses.
- `room_launch_dispatch.go` / `room_launch_mapping.go` /
  `thread_session_registry.go` / `thread_handle_stickiness.go` /
  `thread_teardown_subscriber.go` — the `@@<handle>` launcher: mapping
  registry write path is complete; the actual thread-scoped session-spawn
  dispatch is a stub today (see §4 "Not yet implemented").
- `double_handle_prefix.go` / `subteam_mention_prefix.go` /
  `subteam_alias_map.go` / `user_alias_map.go` — Tier-3-only address
  parsing: doubled `@@handle` launcher tokens, Slack User Group
  (`<!subteam^S…>`) mention normalization (both labeled and unlabeled
  forms), and the outbound inverse (`@handle` → Slack mention rewriting via
  an operator-curated allowlist file).
- `dispatch_drops.go` — bounded dispatch-goroutine pool
  (`SLACK_DISPATCH_CONCURRENCY`, default 50) with drop-on-saturation and a
  `dispatch_dropped_total` counter surfaced on `/healthz`.
- `confined_open.go`, `tmp_sweep.go` — safe-path file open for
  `/publish-file` reads (confined to `FILE_UPLOAD_ROOT`) and the inbound-file
  retention janitor.
- `registry_reload.go` — the all-or-nothing SIGHUP reload across the five
  CLI-written registries.

### CLI structure (slack-full only)

`cli/main.go` wires a Cobra root (`gc-slack-cli`, module
`github.com/sjarmak/gc-slack-cli`, depends only on stdlib +
`github.com/spf13/cobra` v1.10.2 — deliberately no import of gc internals so
the pack stays self-contained). `cli/cmd/*.go` — one file per verb
(`import_app.go`, `map_channel.go`, `map_rig.go`, `enable_room_launch.go`,
`post_message.go`, `sync_commands.go`, `sync_subteam_aliases.go`), plus
`citypath.go` (city-root resolution: `GC_CITY_PATH` env override, else
walk-up-from-cwd) and `restart_reminder.go` (the shared SIGHUP-reminder
string). `cli/internal/state/{apps,channels,rigs,rooms,workspace,blockkit}/`
hold the typed registry read/write helpers shared across verbs — the same
on-disk JSON contract the adapter reads. `cli/PORTING.md` documents the
"one leaf per commit" porting convention from the pre-relocation `gc`
binary's `cmd/gc/cmd_slack_*.go` originals; `cli/README.md` is a short
pointer summarizing the module's isolation rule.

### Python scripts (slack-full only)

Confirmed as the actual outbound/registry-verb implementations (see §4);
`slack_intake_common.py` is the one shared module (gc API base resolution
including opportunistic load of `~/.config/gc-slack-adapter/env` when env
vars are missing from the calling session's environment, CSRF header
constant, small `_request` HTTP helper).

### Doctor checks (slack-full only)

Five checks under `doctor/<name>/doctor.toml` + `doctor/check-<name>.sh`:
`binaries` (adapter + CLI built in place), `env` (four must-set vars present
in-process or in the adapter env file), `funnel` (Tailscale reachability to
the public listener), `gc` (gc CLI on PATH), `python` (python3 ≥ 3.11 on
PATH). Neither slack-mini nor slack-channel ships a `doctor/` directory.

### Schemas

- **slack-channel** (`schema/*.schema.json`): `channel_mappings`,
  `identities`, `handle_aliases` — each documents its file path
  (`<GC_CITY_PATH>/.gc/slack-channel/<file>.json`), composite/simple key
  shape, and that the adapter is sole reader+writer (verbs never touch the
  files directly).
- **slack-full** (`schema/*.schema.json`): `apps` (composite key
  `<workspace_id>:<app_id>`), `channel_mappings` (composite key
  `<workspace_id>:<channel_id>`, **adapter loads once at startup, no
  auto-reload — restart or SIGHUP required**), `rig_mappings` (composite key
  `<workspace_id>:<rig_name>`, SIGHUP-reloadable).
- **slack-mini** ships no `schema/` directory — consistent with having no
  registries.

### Manifests

All three ship a Slack app manifest at `manifest/app.json` (import via
"Create New App → From a manifest"), scoped tightly to what that tier's
adapter needs:

| | slack-mini | slack-channel | slack-full |
| --- | --- | --- | --- |
| Bot scopes | `app_mentions:read`, `chat:write`, `chat:write.public` | + `channels:history`, `groups:history`, `im:history`, `mpim:history`, `chat:write.customize`, `reactions:write` | + `commands`, `files:read`, `files:write` (drops none) |
| Event subscriptions | `app_mention` only | `app_mention` + `message.channels`/`.groups`/`.im`/`.mpim` | same as slack-channel |
| Interactivity | disabled | disabled (adapter *can* ack if operator manually enables it in Slack + points it at `/slack/interactions`) | disabled in the checked-in manifest; the adapter fully implements `/slack/interactions` dispatch, so this is enabled by the operator post-install, not by the manifest |
| `manifest/README.md` | — | — | Yes — documents `gc slack import-app` flow and the OAuth self-service alternative |

---

## 6. End-to-end wiring

All three tiers share the same physical shape: the adapter is a gc
`[[service]] kind = "proxy_process"` — gc supervises the binary, binds a
Unix domain socket at `$GC_SERVICE_SOCKET` for internal (gc-facing) verbs +
`/healthz`, and reverse-proxies `/svc/<service-name>/*` to that socket. The
adapter **also** independently binds a public TCP port (`LISTEN_PUBLIC`) for
Slack's own webhook traffic — that port is outside proxy_process's
lifecycle management and must be exposed to the internet by something like
Tailscale Funnel.

### slack-mini

**Inbound:** Slack `app_mention` event → HTTPS POST to
`https://<funnel-host>/slack/events` (public TCP, default
`0.0.0.0:8775`) → adapter verifies `X-Slack-Signature`/`X-Slack-Request-Timestamp`
HMAC-v0 against `SLACK_SIGNING_SECRET` (5-minute replay window, fails closed)
→ strips the leading `<@BOTID>` mention token → builds an
`externalInboundMessage` (`conversation.provider=slack`,
`conversation.account_id=$SLACK_WORKSPACE_ID`,
`explicit_target=$SLACK_MINI_INBOUND_TARGET` default `mayor`,
`dedup_key="slack-"+ts`) → `POST $GC_API_BASE_URL/v0/city/{GC_CITY_NAME}/extmsg/inbound`
(default `GC_API_BASE_URL=http://127.0.0.1:9443`). gc routes that inbound to
the mayor session (or whatever `SLACK_MINI_INBOUND_TARGET` names).

**Outbound:** a session runs `gc slack-mini post-message --channel C… --text
"…"` → the bash wrapper POSTs JSON to
`${GC_API_BASE_URL}/v0/city/{city}/svc/slack-mini/post-message` — i.e. gc's
reverse proxy for the `slack-mini` service, which forwards to the adapter's
UDS `POST /post-message` handler → adapter calls Slack `chat.postMessage`
with `Authorization: Bearer $SLACK_BOT_TOKEN`.

**Self-registration:** on start (if `REGISTER_ON_START=true`, default), the
adapter POSTs to `/v0/city/{city}/extmsg/adapters` with
`provider=slack`, `account_id=$SLACK_WORKSPACE_ID`,
`callback_url = $GC_API_BASE_URL + $GC_SERVICE_URL_PREFIX` (proxy_process
mode) — gc's extmsg HTTP layer appends `/post-message` itself when it needs
to call the adapter back (not used at Tier 1, since there is no gc→adapter
outbound call path beyond the reverse-proxied verb, but the registration
contract is shared code with Tier 2/3).

### slack-channel

**Inbound:** same signature-verification + `/slack/events` entry point, but
`routeEvent` now also accepts `message.*` events (not just `app_mention`):
1. If the channel has a binding (`bind-dm`/`bind-room`), every bound session
   is a target.
2. If the message body leads with a registered `@handle`, that session is
   also (or instead) a target, with the handle stripped from the text.
3. If neither matched and the event was an `app_mention`, fall back to
   `SLACK_CHANNEL_INBOUND_TARGET` (default `mayor`).
4. Otherwise (plain unbound message, no alias) — dropped.

Each resolved target gets its own `POST /v0/city/{city}/extmsg/inbound` call
(`dedup_key = "slack-"+ts+"-"+target`, so N bound sessions don't collapse
into one gc-side dedup), and the delivery is recorded in the in-memory
`lastInbound[sessionID]` map for `reply-current`/`react` to use later.
Also serves `/slack/interactions` (signature-verified ack only — no modal
logic).

**Outbound:** `gc slack-channel <verb>` → bash wrapper (`_lib.sh`
`sc_call`) → `${GC_API_BASE_URL}/v0/city/{city}/svc/slack-channel/<endpoint>`
→ gc's `/svc/slack-channel/*` reverse proxy → adapter UDS → one of
`/publish`, `/publish-to-channel`, `/reply-current`, `/react`,
`/bindings`, `/identity`, `/handle-alias` → for the posting endpoints, the
adapter injects the session's `identities.json` override (username/icon)
into the `chat.postMessage` call, then calls Slack directly with
`SLACK_BOT_TOKEN`.

**On-disk state:** three JSON registries under
`<GC_CITY_PATH>/.gc/slack-channel/` (or `$SLACK_CHANNEL_REGISTRY_DIR`),
written atomically (`saveJSONAtomic`) by the adapter itself in response to
the `/bindings`/`/identity`/`/handle-alias` verb calls — never written
directly by the bash wrappers.

### slack-full

**Inbound (Events API):** `/slack/events` on `LISTEN_PUBLIC` (default
`:8765`, reference deployment `:8775` behind Funnel) — HMAC-verified against
either the multi-app `apps.json` registry (per-`team_id` signing secret,
looked up first) or the single `SLACK_SIGNING_SECRET` env var fallback.
Routing is the widest of the three tiers: `app_mention`, plain `message.*`,
`@handle` alias, `@@handle` launcher-mode double-handle, and
`<!subteam^S…>` User Group mentions (both labeled and unlabeled forms,
resolved via `subteam-aliases.json` / `handle_aliases`) are all recognized
address forms, dispatched onto a bounded goroutine pool
(`SLACK_DISPATCH_CONCURRENCY`, default 50; drops with a logged/`healthz`
-exposed counter on saturation) before landing on gc's
`/v0/city/{city}/extmsg/inbound`.

**Inbound (Interactions API):** `/slack/interactions` on the same public
listener — slash commands, `block_actions` (button clicks etc.), and
`view_submission` (modal submits). Channel-scoped actions resolve through
`channel_mappings.json` (session override, wins) falling back to
`rig_mappings.json` (rig default). `view_submission` has no channel context,
so the modal opener must stash `{"session_id":"…"}` in
`view.private_metadata`; the adapter strict-decodes it and posts a
system-reminder to that session. Workspace gate: `payload.team.id` must
match `SLACK_WORKSPACE_ID`/apps-registry record on both branches.

**Outbound (adapter side):** the internal mux on `LISTEN_INTERNAL` (TCP
`127.0.0.1:8766`) or `GC_SERVICE_SOCKET` (proxy_process mode) exposes
`/publish` (requires `session_id` or must fail 400 — "fails closed against
identity-less channel-root posts under the default bot identity"),
`/publish-file`, `/react`, `/identity` (POST/DELETE), `/handle-alias`
(POST/DELETE).

**Outbound (verb → adapter path):** most verbs go **through gc**, not
straight to the adapter: `gc slack reply-current` (default) →
`slack_chat_reply_current.py` → `POST {city}/extmsg/outbound` → gc records
the transcript entry, fires peer-fanout system reminders to other sessions
bound to the same room, then calls the registered adapter's `/publish`
internally. `--via adapter` bypasses gc and POSTs the adapter's `/publish`
directly (diagnostics only — no transcript, no peer fanout). `gc slack
post-message` is the one verb that skips `/publish`'s session-attribution
guard entirely, going straight to Slack's `chat.postMessage`/`chat.update`
for intentional bot-identity system posts.

**Service env split** (documented precisely in the README):
`GC_SERVICE_NAME=slack`, `GC_SERVICE_SOCKET=/tmp/gcsvc-<uid>/<hash>/slack-*.sock`,
`GC_SERVICE_URL_PREFIX=/svc/slack`, `GC_SERVICE_STATE_ROOT`,
`GC_SERVICE_RUN_ROOT` are controller-injected; `GC_API_BASE_URL` and
`GC_CITY_NAME` are **not** injected even under proxy_process — they must be
present in the sourced env file before `gc start` or the supervisor won't
pass them to the spawned adapter.

**SIGHUP reload:** five CLI-written registries (`apps.json`,
`channel_mappings.json`, `rig_mappings.json`, `room_launch_mappings.json`,
`subteam-aliases.json`) are picked up on `pkill -HUP gc-slack-adapter` (or
`gc service restart slack`), all-or-nothing — a single parse failure aborts
the whole reload cycle with in-memory state untouched. `identities.json`,
`handle-aliases.json`, and the thread-session store are adapter-owned
(written in-process, not by the CLI) and do **not** participate in SIGHUP
reload — hand-editing them while the adapter runs will be silently
overwritten.

---

## 7. Watch-outs for a copier/integrator

- **Pick exactly one tier per city.** The tiering memo states this
  explicitly and it is structurally enforced by pack-name uniqueness
  (`pack.toml [pack] name` must be unique per city) — the memo's mental
  model treats all three as registering the conceptual name `"slack"`, so
  installing two is a naming collision, not a composition. In the pack.toml
  files actually on disk today, note a discrepancy worth flagging to an
  integrator: `slack-mini`'s `pack.toml` names its pack **and** service
  `slack-mini`; `slack-channel` names both `slack-channel`; but
  **`slack-full`'s `pack.toml` names the pack `slack-full` while the
  `[[service]]` block inside it is still named `slack`** (a holdover from
  before the Tier-3 retitle — see slack-full's `CHANGELOG.md` "Renamed the
  pack directory... pack.toml name from slack to slack-full... the
  registered slack service name are unchanged"). This is intentional per
  the changelog (avoids breaking existing `/svc/slack/*` consumers) but
  means the three tiers' **service names are not uniformly parallel to
  their pack names** — double-check the actual `[[service]] name` in
  whichever tier you install, don't assume it matches the pack name.
- **Required secrets, every tier:** `SLACK_BOT_TOKEN` (`xoxb-…`),
  `SLACK_SIGNING_SECRET`, `SLACK_WORKSPACE_ID` (Slack team id), plus
  `GC_CITY_NAME`. slack-channel additionally requires `GC_CITY_PATH` (or
  `SLACK_CHANNEL_REGISTRY_DIR`) so the three registries have a directory to
  live in — the adapter refuses to start without one of those two set.
  slack-full's four must-set vars are conventionally placed at
  `${XDG_CONFIG_HOME:-$HOME/.config}/gc-slack-adapter/env` (mode 0600) and
  sourced before `gc start`; slack-mini/-channel READMEs suggest an
  analogous per-tier path (`~/.config/gc-slack-mini-adapter/env`, etc.) but
  don't hardcode it the way slack-full's `SETUP.md`/`docs/install.md` do.
- **`chat:write.public` blast radius (slack-mini, slack-channel):** both
  smaller tiers' manifests grant `chat:write.public`, letting the bot post
  to *any* public channel without being invited. slack-channel's README
  calls this out explicitly as a deliberate but revisable choice — drop the
  scope and rely on `conversations.join`/invite-only posting if that's too
  broad for your workspace.
- **`chat:write.customize` is required for identity overrides to render.**
  Without it (Tier 2/3), Slack silently ignores the `username`/`icon_*`
  fields and posts fall through under the default bot identity — no error,
  just silently wrong-looking output. Re-install the app after adding the
  scope.
- **Channel-mapping reload semantics differ by tier and by file, in
  slack-full specifically:** `channel_mappings.json` is documented in its
  own schema as loaded **once at startup with no reload** — restart
  required — while `rig_mappings.json` **does** support SIGHUP reload. This
  is a subtle inconsistency inside a single tier's registry set; don't
  assume every registry in slack-full behaves the same way on SIGHUP.
- **slack-channel's internal listener is dev-only when not proxy_process
  -supervised.** In standalone TCP mode (`GC_SERVICE_SOCKET` unset), the verb
  endpoints (including registry-mutating ones) are unauthenticated plain TCP
  on `127.0.0.1:8776` — fine for local dev, must not be exposed beyond
  loopback in any real deployment. Same caution applies conceptually to
  slack-mini and slack-full's internal listeners.
- **`/publish` requires session attribution (slack-full only).** A POST
  with neither `session_id` nor the legacy `metadata.source_session_id` is
  rejected 400. This is a deliberate fail-closed guard against
  identity-less channel-root posts; `gc slack post-message` is the
  documented escape hatch for intentional bot-identity system posts (it
  bypasses `/publish` and calls Slack directly).
- **slack-full's room-launcher (`enable-room-launch` / `@@<handle>`) is not
  fully implemented.** The CLI-side mapping write works; the adapter-side
  thread-scoped session spawn is currently a stub that replies "launcher not
  yet available" — don't advertise this feature as working end-to-end yet.
- **"Two adapters running" foot-gun (slack-full).** If a manually-started
  (`nohup ./run.sh`) adapter is left running when gc also starts the
  proxy_process-supervised one, both self-register with gc and the last one
  to register wins — outbound publishes silently go through whichever
  process registered last. Stop the manual one before `gc reload`.
- **Down-migration orphans state, does not delete it.** Swapping from a
  larger to a smaller tier leaves the smaller pack's adapter blind to the
  larger tier's extra registry files (`apps.json`, `rig_mappings.json`,
  `room_launch_mappings.json` when downgrading from slack-full; or
  `channel_mappings.json`/`identities.json`/`handle-aliases.json` when
  downgrading from slack-channel to slack-mini). Nothing is deleted
  automatically — archive manually if you want a clean re-upgrade path
  later.
- **Version pins:** all three adapters (and slack-full's CLI) target
  `go 1.25.9` in their respective `go.mod`s. slack-full's CLI depends on
  `github.com/spf13/cobra v1.10.2` (plus its `mousetrap`/`pflag`
  transitives) — the only third-party Go dependency anywhere in the family;
  every adapter binary is stdlib-only. slack-full's Python scripts require
  **Python 3.11+** (enforced by `doctor/check-python.sh`); no third-party
  Python packages are imported (stdlib `urllib`, `argparse`, `json` only).
- **Manifest fields an installer must fill in exactly:** all three
  `manifest/app.json`s are otherwise complete and importable as-is via
  Slack's "Create New App → From a manifest" flow — there are no
  placeholder tokens to hand-edit inside the JSON itself. The values an
  installer must *supply back to the adapter* after import are the three
  secrets (bot token, signing secret, team/workspace id) plus, for
  slack-channel, `GC_CITY_PATH`. slack-full's manifest additionally reminds
  that `slash_commands` is shipped empty — populated later by
  `gc slack sync-commands`, not by hand-editing the manifest.
- **Interactivity is off by default everywhere.** slack-channel's basic
  modal-button ack and slack-full's full slash-command/modal dispatch both
  require the operator to manually toggle **Interactivity** on in the Slack
  app dashboard and point its Request URL at `/slack/interactions` — the
  shipped manifests all declare `interactivity.is_enabled: false`.
