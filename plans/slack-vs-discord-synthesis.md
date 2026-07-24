# Slack pack family vs Discord pack — compare & contrast

Sources: `rigs/gascity-packs/plans/slack-pack-research.md` (slack-mini/slack-channel/slack-full),
`rigs/gascity-packs/plans/discord-pack-research.md` (discord). Spot-checked against
`slack-mini/pack.toml`, `slack-channel/pack.toml`, `slack-full/pack.toml`, `discord/pack.toml`,
`slack-mini/adapter/main.go`, `discord/scripts/discord_intake_common.py`, and beads `gp-00t` /
`gp-vwa` where the two docs' claims needed independent confirmation.

---

## 1. Shared architecture

Both pack families are **transport/bridge packs, not agent-defining packs**. Neither ships
`[[agent]]`/`[[order]]`/`named_session` declarations in `pack.toml` — both are confirmed (by grep,
independently, in each research doc) to define zero personas. The common shape:

```
named_session (defined elsewhere, e.g. rig/pool templates)
        ^
        |  addressed by / created via
        v
   gc's session API  <---extmsg bridge--->  provider adapter/service (Slack or Discord)
        ^                                              ^
        | agent runs `gc <pack> <verb>`                | provider webhook/gateway event
        v                                              v
   outbound relay  ------------------------->  provider REST API (chat.postMessage / POST messages)
```

- **Inbound**: a provider event (Slack `app_mention`/`message.*` webhook, Discord Gateway
  `MESSAGE_CREATE` or an Interactions POST) is normalized and delivered into gc's session layer.
  Slack does this via `POST /v0/city/{city}/extmsg/inbound` uniformly across all three tiers
  (confirmed in `slack-mini/adapter/main.go:507`, comment at line 7). Discord's primary path also
  posts to an extmsg inbound endpoint (`POST /v0/extmsg/inbound`, `discord_intake_common.py:2395`)
  but only when routing through the newer extmsg-group/thread-launch mechanism; Discord's
  parallel "legacy" path instead delivers directly into a session's transcript via
  `POST /v0/session/{selector}/messages` (see §3).
- **Outbound**: an agent (or operator) inside a gc session calls `gc <pack> <verb>` — never a raw
  API call — and the pack relays to the provider's REST API under the bot's identity, optionally
  overridden per-session (Slack's `identity`/`chat:write.customize`; Discord's bold-handle-prefix
  convention on `reply-current`).
- **Session ownership**: the *pack* never creates a "default" agent identity that ships with it —
  it either resolves an operator-declared binding (Slack `bind-dm`/`bind-room`/handle-alias;
  Discord `bind-dm`/`bind-room`) or, at the top of each provider's capability ladder, spawns a new
  session on demand from an *externally defined* template (Slack-full's room-launcher `@@handle`;
  Discord's launcher rooms and auto-thread-launch on `@mention`). Both launcher features are
  explicitly non-default, opt-in, and (per each doc) partially unfinished in different ways (see
  §3/§6).
- **Consumer-facing prompt content, not agent definitions**: both ship a reusable prompt
  *fragment* for an agent operating inside the provider's chat surface — `slack-full/template-
  fragments/slack-v0.template.md` and `discord/template-fragments/discord-v0.template.md` — rather
  than a baked-in persona. Both fragments establish the same core contract: normal assistant
  output is private to the session; the agent must explicitly call a publish/reply verb to make
  anything visible in the shared channel; and peer agents should be addressed by name/handle.
- **Naming conventions coupling the two**: both use a `commands/<verb>.sh` (or Python) shim +
  `command.toml` + `help.md` three-file gc convention per verb; both use `bind-dm`/`bind-room` verb
  names for the identical concept (bind a DM or room/channel to named session(s)); both use
  `import-app` for provider credential import and `sync-commands`/`sync-commands` (Slack) /
  `sync-commands` (Discord) for pushing slash-command schemas to the provider.

---

## 2. Side-by-side comparison

| Dimension | slack-mini | slack-channel | slack-full | discord |
| --- | --- | --- | --- | --- |
| **Roles/agents defined** | None | None | None | None |
| **Scope** | 1 workspace, mayor-only | 1 workspace, 1 rig, named sessions via binding | 1+ workspaces, multi-rig, OAuth self-service | 1 guild-scoped Discord app per city; slash-command intake + session chat |
| **Named sessions declared in pack** | None | None | None | None |
| **Orders/triggers** | None (event-driven only) | None | None | None (event-driven: Gateway message or Interaction POST; `mol-discord-fix-issue` formula dispatched per-request via `gc sling`, not on a cadence) |
| **Verb count** | 1 (`post-message`) | 8 | 17 | 11 (chat + intake combined) + formula |
| **Assets/scripts** | 1 Go file (~660 lines), no CLI, no registries | ~10 Go files, bash wrappers, 3 JSON registries | 33 Go files + CLI binary + Python scripts (~156+ files) | ~9,540 lines of Python across `scripts/*.py`, no Go |
| **Inbound path** | `app_mention` only → `POST /v0/city/{city}/extmsg/inbound` | + plain `message.*` in bound channels, `@handle` alias → per-target `POST .../extmsg/inbound` | + `@@handle` launcher, `<!subteam^…>` mentions, slash commands/modals via `/slack/interactions` | Gateway `MESSAGE_CREATE` → extmsg path (`POST /v0/extmsg/inbound`) or legacy path (`POST /v0/session/{selector}/messages`); slash command via `POST /v0/discord/interactions` |
| **Outbound path** | `gc slack-mini post-message` → adapter → `chat.postMessage` | `gc slack-channel <verb>` → adapter → Slack Web API, with identity override | mostly `gc slack <verb>` → gc `/extmsg/outbound` → adapter `/publish` → Slack (peer-fanout wired); `post-message` bypasses this | `gc discord reply-current`/`publish` → `publish_binding_message` → Discord REST `POST /channels/{id}/messages` (peer-fanout **documented but not wired** — see §6) |
| **Binding model** | None (single fallback target) | Channel bindings, per-session identity, handle aliases (3 registries) | + apps, channel_mappings, rig_mappings, room_launch_mappings (6 registries total) | Chat bindings (`dm:`/`room:`/`launch-room:` ids), channel/rig mappings for `/gc fix` dispatch — no separate "identity override" registry |
| **Required env/creds** | `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_WORKSPACE_ID`, `GC_CITY_NAME` | + `GC_CITY_PATH`/`SLACK_CHANNEL_REGISTRY_DIR` | same 4 secrets, conventionally in `~/.config/gc-slack-adapter/env` | Discord Application ID, Ed25519 public key, bot token (via `import-app`); `GC_DISCORD_API_BASE`, `GC_API_BASE_URL`, `GC_CITY_ROOT/PATH`, per-service `GC_SERVICE_NAME` |
| **Composition requirement** | Pick exactly one Slack tier per city (alternatives, not layers) | same | same | Discord is a straight replacement for the retired `discord-intake` pack; must never coexist with it (`doctor/legacy-pack-conflict` checks for residual state) |
| **Services declared** | 1 `proxy_process` (`slack-mini`) | 1 `proxy_process` (`slack-channel`) | 1 `proxy_process` (service name `slack`, pack name `slack-full` — intentional split, see §3) | 3 `proxy_process` services: `discord-interactions` (public), `discord-admin` (tenant), `discord-gateway` (private) |
| **Doctor checks** | None | None | 5 (`binaries`, `env`, `funnel`, `gc`, `python`) | 7 (`bd`, `gc`, `git`, `jq`, `openssl`, `python`, `legacy-pack-conflict`) |

---

## 3. Key differences and why they exist

**Provider protocol shape drives the transport split.** Slack is a single Events-API webhook +
Web-API REST pair — HMAC-signed HTTP in, HTTP out — so every Slack tier is a single `proxy_process`
service. Discord's provider model is fundamentally different: chat/gateway traffic is a
**persistent WebSocket** (Discord Gateway), while slash-command interactions are a **separate
public webhook**. That protocol asymmetry is why Discord ships **three** services
(`discord-gateway` for the always-on socket, `discord-interactions` for the public webhook,
`discord-admin` for an operator status page) where Slack ships **one** per tier. Discord's gateway
client is hand-rolled from raw TCP sockets (no `websockets`/`discord.py` dependency) — a
significant, self-acknowledged maintenance liability the Slack packs don't have an equivalent of,
since Slack requires no persistent connection at all.

**Three-tier Slack packaging vs one Discord pack.** Slack's tiering exists because Slack
integrations have a genuinely wide utility range that gc wants to let a city right-size (mayor-only
posting vs full multi-rig OAuth orchestration), and each smaller tier is a strict subset of the
next, making upgrade a clean binary swap. Discord has no equivalent tiering: it ships one pack that
already bundles both the lightweight "bind a channel to a session" use case *and* the heavier
"slash-command bug-fix intake" use case in a single deployable. This isn't a capability gap so
much as a different product decision — Discord's design doesn't split "just talk to mayor" from
"full intake dispatch" into separate installable sizes.

**Capability Slack has that Discord lacks: per-session identity override.** Slack (Tier 2+) has a
first-class `identity` verb backed by `chat:write.customize`, letting each named session post under
its own username/avatar. Discord has no equivalent registry — its outbound convention instead
relies on a *textual* prefix (`**handle:** `) baked into the reply body by agent discipline (per the
`discord-v0` prompt fragment), not a provider-level identity swap. This is plausibly a Discord API
capability gap (bot-token posts are always under the one bot identity; Discord's closest analogue,
webhooks-per-name, isn't used here) rather than a deliberate omission.

**Capability Discord has that Slack lacks: built-in slash-command-to-bugfix-workflow dispatch.**
Discord's `/gc fix` → bead → `mol-discord-fix-issue` formula → `gc sling` pipeline is a complete,
opinionated bug-intake product baked into the pack. Slack-full has the analogous *primitives*
(slash commands via `/slack/interactions`, channel/rig mapping registries) but no shipped formula
that consumes them the way Discord's does — Slack's slash-command surface is generic dispatch
infrastructure, not a pre-wired workflow.

**Auto-launch-on-mention is further along on Discord than Slack.** Discord's extmsg path
(`launch_thread_for_mentions`) auto-creates a thread + session + extmsg group the moment an
unmentioned agent is `@mentioned` in a root room, with dual inbound routing (extmsg-managed vs
legacy) already resolved in production code. Slack-full's structurally similar feature
(`enable-room-launch`, `@@handle`) has the mapping-write side implemuted but the adapter-side spawn
is a stub ("launcher not yet available"). Both docs flag their respective launcher's peer-fanout
wiring as incomplete (see §6), so this is a case of convergent partial-completion rather than one
side being simply "done."

**Service-name/pack-name mismatch (Slack-full only, confirmed).** `slack-full/pack.toml` names the
pack `slack-full` but its `[[service]]` block is still named `slack` (verified directly in
`slack-full/pack.toml`) — an intentional holdover so existing `/svc/slack/*` consumers don't break,
per the pack's own CHANGELOG. Discord has no equivalent mismatch: its three service names
(`discord-interactions`, `discord-admin`, `discord-gateway`) are all descriptive and don't shadow a
pack-name convention (verified directly in `discord/pack.toml`).

---

## 4. Reuse / DRY opportunities

- **Bridge shape is identical and could be a shared contract/interface**, even though the
  implementations are independent (Go for Slack, Python for Discord): inbound-normalize →
  `extmsg/inbound` (or direct session-message POST) → outbound verb → provider REST, with an
  identity/attribution layer in between. A shared "extmsg provider adapter" spec (request/response
  shapes, dedup-key conventions, `explicit_target` semantics) would let a third provider pack (see
  §5) implement against a contract instead of reverse-engineering it from two independent
  codebases.
- **Bind-dm/bind-room verb naming and semantics already converge** (`kind=dm`/`kind=room`,
  N-sessions-per-binding) — this is de facto shared convention today, just not factored into a
  shared library. A common "chat-binding CRUD" helper (even just a shared JSON-schema definition
  for the binding record) would reduce drift risk between the two pack families' registries.
  Slack-channel and Discord already independently converged on nearly-identical composite binding
  ids (`kind:conversation_id`) — worth codifying explicitly rather than leaving as a coincidence.
- **`reply-current` semantics (recover most-recent inbound context, reply into it) are duplicated
  logic** between `slack_chat_reply_current.py`/`slack-channel`'s in-memory `lastInbound` map and
  Discord's `find_latest_discord_reply_context` (which reads the session transcript for the latest
  `<discord-event>`/`<slack-event>`-style envelope). A shared "find the conversation this session
  should reply to" helper, parameterized by provider-specific envelope tag, could eliminate two
  independent implementations of the same idea.
- **Doctor-check patterns** (`env`, `python`, `gc`/`bd` presence) are near-identical simple
  `command -v`/env-presence checks reimplemented per pack (5 checks in slack-full, 7 in discord).
  A shared doctor-check library (or template) for "verify N env vars are set" / "verify binary X on
  PATH" / "verify python >= 3.11" would remove boilerplate duplicated across at least two, likely
  more, provider packs.
- **Peer-fanout is a shared unsolved problem, not two unrelated bugs.** Both docs independently
  flag the same shape of gap: peer-fanout policy flags exist on `bind-room`, a `retry-peer-fanout`
  verb exists, but the actual fanout delivery call is not invoked from the real publish path in
  either pack (Slack-full's is described as implemented via gc's extmsg outbound orchestrator in
  one context; Discord's own code comment claims the identical "handled by the extmsg outbound
  orchestrator... no pack-side fanout needed" — and in Discord's case this is independently
  confirmed false by its own tests). This suggests either (a) the orchestrator doesn't exist yet
  and both packs were written against a spec that was never finished, or (b) both packs have a
  latent bug from copy-pasting the same incorrect assumption. Worth resolving centrally rather than
  patching each pack independently — a good candidate for a follow-up bead.

---

## 5. Copier/integrator guidance — adding a third provider (e.g. Teams/Matrix)

**Reusable skeleton (provider-agnostic):**
- A `bind-dm <channel> <session...>` / `bind-room <channel> <session...>` verb pair, backed by a
  JSON registry (or your own storage) mapping conversation id → session id(s).
- An inbound path that normalizes the provider's event into gc's extmsg wire shape and posts to
  `/v0/extmsg/inbound` (or, if extmsg's group/thread machinery doesn't fit, direct
  `POST /v0/session/{selector}/messages` with a provider-tagged text envelope, mirroring Discord's
  legacy path) — either approach is precedented, so pick whichever matches how much of the
  provider's own thread/group model extmsg's schema can represent.
- An outbound `reply-current`/`publish` verb pair that resolves the "conversation to reply to"
  either from an in-memory last-inbound map (Slack-channel's approach — simpler, but lost on
  adapter restart) or from parsing the session's own transcript for the last inbound envelope
  (Discord's approach — durable across restarts, more code).
- A prompt fragment (`template-fragments/<provider>-v0.template.md`) establishing the
  explicit-publish-only contract: normal output is private, only an explicit reply/publish verb is
  human-visible, and peer agents are addressed by name/handle in a shared thread.
- A `command.toml`/`help.md`-documented `commands/<verb>.sh` (or `.py`) shim per verb, following gc's
  three-file convention.
- An `import-app` verb for credential onboarding, storing secrets with restrictive file permissions
  (both packs use `0o600`/`0o700`) — never in a JSON registry that gets synced/reloaded broadly.
- Doctor checks for required binaries/env vars/language runtime version.

**Per-provider specialization (do not try to generalize prematurely):**
- The wire protocol itself: webhook-only (Slack-style, single `proxy_process`) vs
  webhook+persistent-connection (Discord-style, needs a dedicated gateway-equivalent service if the
  new provider has one — Matrix's server-to-server federation and Teams' Bot Framework both differ
  again from both existing examples, so don't assume either pattern transfers wholesale).
- Signature/auth verification scheme (Slack: HMAC-SHA256 v0; Discord: Ed25519 via `openssl
  pkeyutl`) — this is provider-specific and worth keeping isolated behind a single
  `verify_signature`-shaped function per pack rather than trying to share code across providers
  with fundamentally different crypto.
- Identity-override mechanics (Slack's `chat:write.customize` scope vs Discord's textual-prefix
  convention) — whether the new provider supports per-message sender identity at the API level
  determines which pattern is even available; don't assume Slack's approach is portable.
  Tier/monolith decision: whether to split into capability tiers (Slack's model) or ship one pack
  covering the full range (Discord's model) should be driven by how wide the actual utility range
  is for that provider, not by symmetry with either existing pack family.
- Whether the provider needs a slash-command-to-workflow-dispatch feature at all (Discord's `/gc
  fix`) is a product decision, not an architectural requirement — Slack-full has the primitives but
  no shipped formula; a new provider pack should decide this independently based on whether that
  provider's community/workflow calls for it.

---

## 6. Known issues cross-cutting both

- **`gp-00t` (flat-layout rig-name==routes-path assumption)** — **Discord-only**, not applicable to
  the Slack pack family (Slack has no `/gc fix`-style rig-dispatch feature at all — it only maps
  channels to sessions/rigs at the session-binding level, not via `routes.jsonl` basename
  matching). Confirmed: `gp-00t`'s own notes describe two already-fixed instances (polecat gate,
  `rig_workdir`) and call for a sweep of remaining `path==rig`/`name-vs-path` comparisons across
  `discord/scripts/*.py`. The discord-pack-research doc independently confirms `rig_workdir`
  (`discord_intake_service.py:364`) already implements the defensive basename-fallback fix (exact
  match OR `os.path.basename(path) == rig`), consistent with `gp-00t`'s claim that this instance was
  fixed in commit `41e83e3`. The bead is about sweeping for *other* naive comparisons beyond the
  two already fixed — still open as of this doc.
- **`gp-vwa` (order + `github_app_token_env` doesn't deliver token — `gc order run` strips
  inherited env)** — **not applicable to either pack as shipped.** Neither the Slack family nor the
  Discord pack defines any `[[order]]` blocks (both confirmed by grep in their respective research
  docs), so neither exhibits this specific bug pattern. This is a gc-core / order-subsystem bug
  affecting packs that *do* use `type=order` with token-env indirection — orthogonal to both packs
  reviewed here, worth noting only so an integrator doesn't spend time looking for it in either.
- **Peer-fanout wired-but-not-invoked** — cross-cutting both, independently confirmed in each
  research doc (see §4 above): Slack-full and Discord both ship peer-fanout policy flags, a
  `retry-peer-fanout` verb, and exit-code/documentation describing fanout behavior, but the actual
  publish path in both packs does not call the fanout-delivery function. This is the one genuinely
  shared, unresolved issue between the two pack families and the strongest candidate for a joint
  follow-up bead rather than two separate provider-specific fixes.
