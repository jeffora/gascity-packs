# Discord Pack — Implementation & Capabilities Report

**Audience:** unta-city adjunct — evaluating a human↔agent Discord comms surface across Gas City cities.
**Scope reviewed:** `rigs/gascity-packs/discord/` (pack.toml, README.md, all `commands/`, `doctor/`, `formulas/`, `scripts/`, `template-fragments/`, `tests/`).
**Status:** this pack replaces the older `discord-intake` pack. Do not import both into the same workspace — they intentionally share the `discord-interactions` and `discord-admin` service identities and will collide (README.md lines 8-11; enforced at runtime by `doctor/legacy-pack-conflict`).

---

## 1. Description of capabilities

### 1.1 Services

`pack.toml` declares three `proxy_process` services under `state_root = ".gc/services/discord"`:

| Service | Visibility | Entry point | Purpose |
|---|---|---|---|
| `discord-interactions` | `public` | `python3 -u scripts/discord_intake_service.py` | Discord Interactions Endpoint (slash commands, modals) |
| `discord-admin` | `tenant` | same script (`discord_intake_service.py`) | Operator/admin HTML status page; behavior branches on `GC_SERVICE_NAME` at runtime |
| `discord-gateway` | `private` | `python3 -u scripts/discord_gateway_service.py` | Persistent Discord Gateway (WebSocket) connection for chat ingestion |

### 1.2 Surfaces provided

- **Slash-command intake (`/gc fix`)** — opens a modal for `summary`/`context`, or accepts a `prompt` option plus an optional `rig` option. Accepted requests dispatch the `mol-discord-fix-issue` formula against a mapped `rig/pool` target (`discord_intake_service.py: accept_fix_request`).
- **DM chat** — `gc discord bind-dm <conversation_id> <session_name>` binds one Discord DM channel to exactly one named Gas City session.
- **Room chat** — `gc discord bind-room` binds a channel/thread to one or more named sessions, with optional ambient-read (unmentioned-message intake) and peer-fanout policy flags.
- **Launcher rooms** — `gc discord enable-room-launch` turns a root room into a launchpad: an unmentioned `@@rig/alias` (double-@, qualified handle) spins up a thread-scoped session on demand; the visible Discord thread is created only on the agent's first reply.
- **Status/inspection** — `gc discord status [--json]` renders a redacted snapshot: URLs, app config presence, gateway state, mappings, bindings, launchers, recent ingress/publish/launch activity.
- **Outbound replies** — `gc discord reply-current` (agent path: resolves the latest `<discord-event>` from the current session's own transcript and reuses its binding/conversation metadata) and `gc discord publish` (operator path: requires an explicit `--binding`). Both call a shared `publish_binding_message`.
- **Workflow status callback** — `gc discord post-message --request-id ... --body ...`, used by the `mol-discord-fix-issue` formula to post started/completed updates back into the originating conversation.
- **Operator recovery** — `gc discord release-workflow` clears a stuck per-conversation workflow lock; `gc discord retry-peer-fanout <publish-id>` re-drives saved peer-fanout target records (see §4.1 — this currently has nothing to act on in practice).
- **Command registration** — `gc discord sync-commands <guild_id>...` registers/replaces the guild-scoped `/gc` command; must be re-run whenever the command schema changes, since Discord otherwise continues enforcing the stale schema client-side.

### 1.3 How inbound Discord events reach named sessions

`discord-gateway` runs a **hand-rolled WebSocket client** built directly on raw TCP sockets (`GatewayWebSocket` in `discord_gateway_service.py`, ~140 lines: manual HTTP Upgrade handshake, manual frame framing/masking/fragmentation) — no `websockets` or `discord.py` dependency. `GatewayWorker.run_forever` drives the identify/resume/heartbeat state machine, identifying with intents `GUILDS | GUILD_MESSAGES | DIRECT_MESSAGES | MESSAGE_CONTENT`.

Inbound `MESSAGE_CREATE` events flow through `process_inbound_message`, which:

1. Ignores bot-authored messages (including its own).
2. For guild messages: checks room-launcher config first, then falls back to bound-room/ambient-read resolution, then requires an explicit bot mention if neither claims the room.
3. Claims the event exactly once via idempotent ingress tracking (`save_chat_ingress_if_absent`, keyed by the Discord message id), with reclaim logic for stale/failed claims.
4. Delivers a normalized `<discord-event>` envelope into the target named session(s) by POSTing to `gc`'s own local control API (`/v0/session/{selector}/messages`), discovered via `city.toml` or `GC_API_BASE_URL` (default `http://127.0.0.1:8372`).
5. Ambient-read rooms require an exact `@session_name` target unless the room is a "sticky" single-session binding explicitly configured to allow untargeted ambient delivery.
6. Launcher rooms resolve `@@rig/alias` mentions, create/materialize a per-thread session on demand, and track the "last addressed" agent for un-mentioned follow-ups inside a managed thread.

The `<discord-event>` envelope explicitly marks `reply_contract: explicit_publish_required` and `normal_output_visibility: internal_only` — an agent's ordinary output is **not** surfaced to Discord automatically; only an explicit `gc discord publish` / `reply-current` call sends a reply out.

### 1.4 How agents reply back out

`gc discord reply-current` is the documented, preferred agent-side path: it reads the current session's own transcript via the local `gc` API to find the latest `<discord-event>`'s binding/conversation/reply-threading metadata, then calls `publish_binding_message`, which resolves the actual destination (including creating a launcher-room thread on first reply) and posts via the bot token to `POST /channels/{id}/messages`. `gc discord publish` is the more general operator path requiring an explicit `--binding`.

---

## 2. How to implement / stand this up in a city

1. **Import the pack** in the workspace's `pack.toml`, e.g. `[imports.discord] source = "../packs/discord"`.
2. **Create a Discord application + bot** in the Discord Developer Portal. Record the **Application ID**, the **Interactions Public Key** (Ed25519, 64 hex chars), and the **bot token**.
3. **Enable Message Content Intent** on the bot in the Developer Portal if you want launcher rooms or ambient-read room bindings — the gateway always *requests* this intent bit, but Discord silently strips message content unless the portal toggle is also on (for guild messages, additionally unless the bot is directly mentioned).
4. **Start the workspace** so `discord-interactions`, `discord-admin`, and `discord-gateway` come up (`gc service list` to confirm).
5. **Import app credentials**:
   ```bash
   gc discord import-app \
     --application-id <id> --public-key <hex> --bot-token "$DISCORD_BOT_TOKEN" \
     [--command-name gc] [--guild-allowlist <id>]... [--channel-allowlist <id>]... [--role-allowlist <id>]...
   ```
6. **Point Discord's Interactions Endpoint URL** at the public interactions service URL (`gc discord status` shows it), path `/v0/discord/interactions`. Discord immediately fires a PING to verify — the service must answer it signed.
7. **Map dispatch targets** for the `/gc fix` command (at least one, per guild):
   ```bash
   gc discord map-channel <guild_id> <channel_id> <rig>/<pool> [--fix-formula mol-discord-fix-issue]
   gc discord map-rig <guild_id> <rig_name> <rig>/<pool> [--fix-formula mol-discord-fix-issue]
   ```
   Rig mapping takes priority over channel mapping when the command's `rig` option is present.
8. **Register the slash command** per guild: `gc discord sync-commands <guild_id> [<guild_id>...]`. Re-run after any schema change.
9. **Bind chat surfaces**:
   - `gc discord bind-dm <dm_channel_id> <session_name>`
   - `gc discord bind-room [--guild-id <id>] [--enable-ambient-read] [--allow-untargeted-ambient-delivery] [--enable-peer-fanout] [...budget flags] <conversation_id> <session_name...>`
   - `gc discord enable-room-launch --guild-id <id> [--response-mode mention_only|respond_all] [--default-handle <rig>/<alias>] [...] <conversation_id>`
   - `bind-room` and `enable-room-launch` are mutually exclusive for the same conversation (enforced with a `ValueError` and covered by tests).
10. **Verify** with `gc discord status --json`, and optionally `gc discord post-message --request-id ... --body ...` for a manual status ping.

### Where secrets/config live

State lives under `$GC_SERVICE_STATE_ROOT` (default `<city_root>/.gc/services/discord`):

- `data/config.json` — app metadata, policy allowlists, channel/rig mappings, chat bindings/launchers (`0o640`).
- `secrets/bot-token.txt` — plaintext bot token (`0o600`; `secrets/` dir `0o700`). Only accessed via `save_bot_token`/`load_bot_token`.
- `data/requests/`, `data/receipts/`, `data/workflows/`, `data/pending-modals/`, `data/chat-publishes/`, `data/chat-ingress/`, `data/chat-launches/`, `data/channel-metadata/`, `data/peer-root-budgets/`, `data/locks/` — per-record JSON with retention-based pruning (e.g. chat ingress/publish records kept 7 days, room-launch records 90 days, pending modals 15 minutes).

Relevant env vars: `GC_CITY_ROOT`/`GC_CITY_PATH`, `GC_SERVICE_NAME` (distinguishes `discord-interactions` vs `discord-admin` behavior in the same script), `GC_SERVICE_STATE_ROOT`, `GC_SERVICE_SECRETS_DIR`, `GC_SERVICE_SOCKET`, `GC_PUBLISHED_SERVICES_DIR`, `GC_SERVICE_PUBLIC_URL`, `GC_DISCORD_API_BASE` (test/staging override), `GC_API_BASE_URL`, `GC_SESSION_NAME`/`GC_SESSION_ID`/`GC_ALIAS`.

---

## 3. Prerequisites, security/policy considerations, constraints

### 3.1 Prerequisites (verified by `doctor/`)

`bd`, `gc`, `git`, `jq`, `openssl`, and `python3 >= 3.11` (hard version-gated, exits with an error on older Python). Plus the **legacy-pack-conflict** check: if `.gc/services/discord-intake/data/config.json` or its `secrets/bot-token.txt` exist on disk, the doctor fails and instructs the operator to migrate off `discord-intake` before using this pack — a residual-state guard, not a live dual-import guard.

### 3.2 Interactions endpoint security

Signature verification (`verify_discord_signature`) builds an Ed25519 public-key PEM from the stored hex key and shells out to `openssl pkeyutl -verify` over the raw `timestamp+body` message — accepting only a clean `exit 0`. The interactions handler additionally enforces a request-size cap, requires a configured public key (503 otherwise), and rejects requests whose `X-Signature-Timestamp` is more than 10 seconds from local time (401, before signature verification even runs) — a replay-window guard. Discord's own PING (`type: 1`) verification requests are answered directly.

### 3.3 Guild/channel/role policy — important gap

The `policy.guild_allowlist` / `channel_allowlist` / `role_allowlist` config **only gates the `/gc fix` slash command path** (`policy_reason`, checked in `accept_fix_request`). **DM bindings, room bindings, ambient-read rooms, and launcher rooms have no equivalent allowlist enforcement** in the gateway — routing there is governed solely by whether a binding/launcher record exists for that conversation id. This is a reasonable default-deny posture (nothing routes without an explicit binding), but it is a materially different security model from the slash-command path, and it is not called out as such in the docs. **Recommendation:** if this pack is used for cross-city human↔agent chat, treat binding creation itself (who is allowed to run `bind-dm`/`bind-room`/`enable-room-launch`) as the real access-control boundary, since Discord-side guild/role allowlists won't apply once a binding exists.

### 3.4 Secret handling

Bot token stored in plaintext at `secrets/bot-token.txt` (`0o600`), never exposed by status/admin endpoints beyond a boolean `bot_token_present`. Status/admin-page rendering routes everything through dedicated redaction functions that strip message bodies/free text before HTML-escaping and dumping to the admin page. No secret-rotation tooling exists — re-running `import-app` simply overwrites the token file.

### 3.5 Rate limiting / retries

Discord REST calls retry up to 2 additional times on HTTP 429, honoring `Retry-After` (header or JSON body) with a 1.0s default; non-429 errors raise immediately with no backoff. Gateway reconnects use a bounded backoff (5s–60s). Peer-fanout-specific per-root/per-session throttles exist in code but are currently unreachable (see below).

### 3.6 Known constraints / gaps

- **Peer fanout is fully implemented but never invoked in production.** `discord_intake_common.py` contains a complete peer-fanout pipeline (target resolution, envelope building, budget checks, delivery, finalization), but it is called from nowhere — `publish_binding_message` explicitly comments that peer notification is "now handled by the extmsg outbound orchestrator via transcript membership — no pack-side fanout needed," and no such orchestrator exists inside this pack's own files. This is confirmed by the pack's own tests, which assert `peer_delivery` is **absent** from the publish record and that delivery is **not** called, despite test names suggesting fanout occurs. As a direct consequence: (a) `gc discord retry-peer-fanout` has nothing real to act on — its own tests only pass because they inject a synthetic `peer_delivery` record directly, bypassing the publish path; (b) the documented exit-code-2 "peer fanout needs attention" contract on `publish`/`reply-current` is currently unreachable. This contradicts substantial still-current documentation across the README, `bind-room`/`enable-room-launch`/`publish`/`reply-current`/`retry-peer-fanout` help text, and CLI flags. Whether an equivalent mechanism genuinely exists elsewhere in `gc` core could not be verified from this pack's source alone. **This should be resolved or the docs corrected before promoting peer-fanout flags as a supported feature.**
- **Hand-rolled WebSocket client.** The gateway's WebSocket implementation (handshake, frame parsing/masking, fragmentation) is custom, not a vetted library. It is tested, but any future Discord gateway protocol change would require hand-patching this code rather than a dependency bump.
- **Naming split is intentional, not legacy cruft.** `discord_intake_*.py` scripts handle the `/gc fix` slash-command intake pipeline; `discord_chat_*.py` scripts handle the session chat control plane (bindings, publish/reply). Both share one large (~4900-line) `discord_intake_common.py`, whose name understates how much chat/gateway/peer-fanout logic it now holds — a naming smell, but not a functional gap. The `discord_intake_*` vs `discord-intake` (the old, separate pack) distinction is easy to confuse; be precise in any cross-city documentation.
- **Test coverage gaps:** no dedicated tests for the `map-channel`, `map-rig`, `sync-commands`, or `room-launch` CLI entry points as standalone scripts (their underlying `common` functions are tested, but not the argparse wrappers); only the legacy-pack-conflict doctor check has automated tests — the other five doctor checks (bd/gc/git/jq/openssl/python) are untested simple presence/version checks.
- **Operational trap:** after migrating from `discord-intake` to this pack, forgetting to re-run `gc discord sync-commands` leaves Discord enforcing the old command schema (e.g. a previously-required `rig` option) at the Discord API layer, producing a confusing client-side validation error unrelated to this pack's own logic.

---

## 4. Recommendation for a cross-city Discord comms surface

The pack is a reasonably complete, security-conscious foundation for human↔agent Discord comms (signed interactions, idempotent ingress, explicit-publish-only outbound, redacted status/secrets) and its core paths — `/gc fix` intake, DM binding, room binding, and launcher rooms — are exercised by a substantial test suite. It is workable to roll out today for a single city's Discord surface using DM binding, room binding, and/or launcher rooms, with the following caveats before treating it as a cross-city standard:

1. **Do not advertise or rely on peer-fanout / multi-session cross-notification** until either the fanout call is wired back into `publish_binding_message` or the docs/CLI flags are corrected to match actual (non-)behavior — right now the flags and help text promise something the code does not do.
2. **Treat binding creation as the real authorization boundary** for chat surfaces, since Discord-side guild/channel/role allowlists don't apply to DM/room/launcher routing — document who is permitted to run `bind-dm`/`bind-room`/`enable-room-launch` per city, especially if this becomes a shared cross-city convenience.
3. **One Discord application per city (or per intended isolation boundary)** given the `discord-intake`-vs-`discord` service-identity collision guard — plan bot/app provisioning accordingly if multiple cities want independent Discord presences.
4. Budget for the operational footguns already documented in the pack itself: re-sync commands after any schema change, and never import both `discord` and `discord-intake` into the same workspace.

With those caveats communicated, this pack is a solid basis to recommend for enabling a human↔agent Discord surface across cities, provided the peer-fanout gap is either fixed or its scope explicitly narrowed in city-facing documentation before wider rollout.
