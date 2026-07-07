# Automatic PR-Review Flow — Capabilities Review & Design

**Prepared for**: unta-city adjunct
**Scope**: `rigs/gascity-packs/github/` (webhook/event intake) + `rigs/gascity-packs/pr-pipeline/` (author-side PR discipline, incl. `mol-pr-review`)
**Goal being evaluated**: for nominated repos, PRs matching criteria are automatically reviewed, with results posted as **inline comments** and an **approve/request-changes decision**.

**Bottom line up front**: the webhook-to-automatic-dispatch machinery already exists and works end-to-end. The review *logic* (`mol-pr-review`'s 11-category scorecard) already exists and works end-to-end. What does **not** exist anywhere in either pack is the GitHub-write step that turns a computed verdict into an inline-commented, approved/changes-requested PR review. That's the one real gap, and it's a bounded one — a single new capability plus two configuration/wiring pieces.

---

## 1. Capabilities of each pack

### `github/` pack — webhook/event intake

- **Two long-running services** (`github-webhook` public, `github-admin` tenant-only) run `scripts/github_intake_service.py`, backed by shared state in `.gc/services/github/`.
- **Auth**: GitHub App only (not PAT). JWT-signed installation tokens, minted per-use. Two credential-provisioning paths: manual env vars / `gc github import-app`, or an identity-resolver + publisher pattern (`docs/github-app-identity.md`) recommended for production because it survives restarts/rotation. Per-address (`@mayor`-style) profiles can carry their own distinct App identity/installation.
- **Webhook handling**: verifies `X-Hub-Signature-256` (HMAC-SHA256), persists the delivery, then runs the event through `rules.toml` matching (see §2) and, separately, an addressed-comment (`@mention`) pipeline and a legacy `/gc fix` slash-command pipeline.
- **Rule matching is generic dotted-field equality** against the raw webhook JSON — not a purpose-built branch/label/path/size filter DSL. Anything present in the payload (label name, action, PR state, branch ref string, etc.) can be matched, but only by exact string equality; there's no glob, regex, or numeric-threshold (e.g. diff size) primitive today.
- **Repo → rig binding already exists**: `rules.toml`'s `[[repo]]` table has a `rig` field that explicitly binds `owner/repo` to a local Gas City rig; if omitted it falls back to a derived slug. This is exactly the "nominated repos, cloned as rigs" binding the goal calls for.
- **Permission verification already exists**, but only on the `/gc fix` path: `repository_permission()` calls `GET /repos/{owner}/{repo}/collaborators/{username}/permission` and requires `write`/`maintain`/`admin` before dispatching. The addressed-message path instead uses a static `authorized_users` allow-list per repo in `rules.toml`. Rule-triggered `order`/`command` actions (the mechanism a new auto-review rule would use) have **no built-in permission check of their own** — the rule author is trusted to gate via `match` conditions.
- **GitHub write primitives that exist today**: `post_issue_comment` (plain top-level comment via `POST /issues/{n}/comments`), `create_pull_request`, `git_push_branch` (via installation token). **No** inline/diff-attached review-comment call, **no** `POST /pulls/{n}/reviews` (approve/request-changes) call, anywhere in the pack.
- **What's missing for PR review specifically**: an inline-review-comment write primitive, a review-submission (approve/request-changes) write primitive, and a rule action type (or order) that runs `mol-pr-review` and posts its result back.

### `pr-pipeline/` pack — author-side PR discipline

- Explicitly scoped to **author-side** work ("planning, building, and shipping the PRs your city sends out"). Both the README and `mol-pr-review.formula.toml` explicitly disclaim incoming-PR review/merge as "a separate, maintainer-side concern, not covered by this pack." The automatic-review flow this report is designing is exactly that disclaimed concern — so it must live in new/adjacent surface area, not by mutating `mol-pr-review`'s stated scope.
- **`mol-pr-review` formula** (4 steps) already implements the review *logic* end-to-end:
  1. `intake` — resolves the PR (by URL or number), fetches metadata via `gh pr view`, diff via `gh pr diff`, prepares a report path.
  2. `scorecard` — the **11-category scorecard**: (1) Behavioral Correctness, (2) Contract & Interface Fidelity, (3) Change Impact/Blast Radius, (4) Concurrency/Ordering/State Safety, (5) Error Handling & Resilience, (6) Security Surface, (7) Resource Lifecycle & Cleanup, (8) Release Safety, (9) Test Evidence Quality, (10) Architectural Consistency, (11) Debuggability & Operability. Each finding is scored blocker/major/minor/nit. Decision policy is mechanical: unresolved blocker in categories 1–4 → `block`; unresolved blocker in 5–8 → `request_changes`; unmitigated major in 1–8 → `request_changes`; only minor/nit or no findings → `approve`.
  3. `recurring-themes` — flags 7 known fixup-pattern themes against the scorecard categories.
  4. `produce-report` — writes a markdown report to `.gc/pr-pipeline/reviews/pr-<N>.md` and records the `verdict:` in the root bead's notes.
- **Critically, `mol-pr-review` performs no GitHub-side write at all.** It only reads (`gh pr view`/`gh pr diff`) and writes locally (markdown file + bead notes). It never calls `gh pr review`, `gh pr comment`, or any comment/review API. The verdict it computes (`approve` / `request_changes` / `block`) is exactly the decision the goal wants posted back to GitHub — it just isn't posted anywhere today.
- **`templates/adoption-review-comment.md`** is the one artifact in the pack that documents *posting* a review-shaped comment back to GitHub, but it is maintainer-side spec/documentation only — not a formula or command. It reuses the same 11-category scorecard for a human-facing "adoption synthesis comment" and explicitly specifies `gh pr comment <number> --body-file <path>` (a plain top-level comment) as the posting mechanism — again, not inline/diff-attached, and not an approve/request-changes submission. No command in the pack executes this template's procedure; it's left to "a maintainer-side adoption workflow" outside the pack.
- Other formulas (`mol-pr-start`, `mol-pr-blast-radius`, `mol-pr-ship`, `mol-pr-triage`, `mol-pr-from-issue`) are all author-side (planning, ship-readiness, triage routing) and none push or open PRs themselves — irrelevant to the incoming-review flow except as prior art for formula/command structure.

---

## 2. Design for the automatic flow

### 2.1 End-to-end flow

```
GitHub PR opened/synchronize
        │  webhook (signature-verified)
        ▼
github/ intake service: rules.toml matching
        │  rule.event = "pull_request"
        │  rule.match = { action = "opened" }  (or "synchronize")
        │  rule.match on repo.rig-bound repos only (via [[repo]] table)
        ▼
matched rule → action: { type = "order", name = "pr-auto-review", rig = <bound rig> }
        │  env: GC_GITHUB_REPO, GC_GITHUB_ITEM_NUMBER (=PR number), GC_GITHUB_PR_URL,
        │       GC_GITHUB_EVENT_PAYLOAD_FILE, minted installation token (github_app_token_env)
        ▼
new order "pr-auto-review" (github/orders/ or pr-pipeline/orders/, city-local):
        │  1. gc sling <rig>/<agent> mol-pr-review --formula --var pr=$GC_GITHUB_ITEM_NUMBER
        │  2. read the produced .gc/pr-pipeline/reviews/pr-<N>.md + verdict from bead notes
        │  3. NEW: gc github post-review <N> --verdict <verdict> --report <path>
        ▼
NEW command in github/: gc github post-review
        │  - maps verdict → GitHub review event: approve → APPROVE,
        │    request_changes → REQUEST_CHANGES, block → REQUEST_CHANGES + human escalation
        │  - posts per-finding inline comments via POST /pulls/{n}/reviews
        │    (comments[] array, each with path + line/side, taken from the
        │    scorecard findings which already carry file/line context from `gh pr diff`)
        │  - submits the review in the SAME call (event=APPROVE|REQUEST_CHANGES|COMMENT),
        │    using an installation token scoped to the PR's repo
        ▼
PR shows: N inline review comments anchored to diff lines + one top-level
          review verdict (approved / changes requested), attributed to the bot App
```

### 2.2 Why this shape

- **Reuses existing, working pieces**: `rules.toml` matching, rig binding, and `gc order run` dispatch are unmodified and already battle-tested by the existing `/gc fix` and addressed-message flows. `mol-pr-review` is unmodified and already produces a correct verdict + findings.
- **New surface is minimal and additive**: one new rule type of action (already generic — `type = "order"` already supports this, no schema change needed on the `github` side), one new order that chains `mol-pr-review` → a new posting command, and one new GitHub-write command (`post-review`).
- **Respects the existing scope boundary**: `mol-pr-review` stays author-side-agnostic (it doesn't know or care whether it's being run by a human, by `pr/review`, or by an auto-review order) — the GitHub-posting responsibility is added in `github/`, which is where all other GitHub-write primitives (`post_issue_comment`, `create_pull_request`) already live. This avoids scope creep into `pr-pipeline/`'s explicitly-disclaimed "maintainer-side" territory while still using its formula.

### 2.3 Criteria matching specifics

Given `rules.toml`'s actual matching primitive (dotted-path exact-string equality, confirmed in `github_intake_common.py`), nominated-repo auto-review criteria map like this:

| Desired criterion | `rules.toml` mechanism today | Gap |
|---|---|---|
| Which repos participate | `[[repo]]` table presence + `rig` binding | none — already works |
| PR opened / updated | `rule.event = "pull_request"`, `rule.match.action = "opened"` / `"synchronize"` (two rules, or one rule matched twice) | none |
| Target branch (e.g. only `main`) | `rule.match."pull_request.base.ref" = "main"` | none (exact match only; fine for a fixed base branch) |
| Label-gated (e.g. only when `needs-review` label present) | `rule.event = "pull_request"`, `rule.match.action = "labeled"`, `rule.match."label.name" = "needs-review"` | none |
| Path filters (e.g. skip docs-only PRs) | — | **gap**: no payload field carries changed-file paths; would need the order itself to `gh pr diff --name-only` and early-exit, since `rules.toml` can't inspect diff contents pre-dispatch |
| Size filters (e.g. skip PRs > N files/lines) | — | **gap**: same as above — push size-based skip logic into the order/formula, not `rules.toml` |
| Author allow/deny-list | no dedicated field, but `rule.match."pull_request.user.login"` works for a single exact login; no list primitive | **gap for lists**: would need either multiple rules (one per login) or a small extension to `normalize_rule`/`matching_rules` to support a `match_any` list — smallest-diff option is to keep it out of `rules.toml` and filter in the order script instead, consistent with the path/size approach |

**Recommendation**: keep `rules.toml` responsible only for cheap, payload-native gates (event type, action, base branch, label), and push all diff-shape gates (paths, size, author lists) into the `pr-auto-review` order script, which runs after dispatch and can cheaply `exit 0` without side effects if it decides not to review. This avoids extending the `rules.toml` schema at all for v1.

---

## 3. Step-by-step implementation to stand this up in a city

1. **GitHub App setup** (if not already done for the target org): create a GitHub App (or extend the existing intake App) with permissions `contents: read`, `pull_requests: write` (this already covers review submission and review-comment creation — no separate "checks" or "reviews" permission scope exists in GitHub's model beyond `pull_requests: write`), `issues: write` (already requested by the pack's manifest). Install it on the nominated repos.
2. **Webhook**: point the App's webhook at the existing `github-webhook` service endpoint; no new endpoint needed — it's the same intake service already handling `/gc fix` and addressed messages.
3. **Credentials**: provision via the existing identity-resolver/publisher pattern (`docs/github-app-identity.md`) so the App's private key/installation tokens survive restarts — do not hand-roll a second credential path for this feature.
4. **Bind nominated repos to rigs** in the city-local `rules.toml`, one `[[repo]]` entry per nominated repo:
   ```toml
   [[repo]]
   full_name = "org/nominated-repo"
   rig = "nominated-repo-rig"        # must already exist as a cloned rig in this city
   installation_id = 12345678
   ```
5. **Add auto-review rules** to the same `rules.toml`:
   ```toml
   [[rule]]
   id = "auto-review-pr-opened"
   event = "pull_request"
   [rule.match]
   action = "opened"
   "pull_request.base.ref" = "main"
   [[rule.action]]
   type = "order"
   name = "pr-auto-review"
   rig = "nominated-repo-rig"
   github_app_token_env = "GH_INSTALL_TOKEN"

   [[rule]]
   id = "auto-review-pr-updated"
   event = "pull_request"
   [rule.match]
   action = "synchronize"
   "pull_request.base.ref" = "main"
   [[rule.action]]
   type = "order"
   name = "pr-auto-review"
   rig = "nominated-repo-rig"
   github_app_token_env = "GH_INSTALL_TOKEN"
   ```
   Repeat per nominated repo/rig, or generalize the order to resolve `rig` from `GC_GITHUB_REPO` via the existing `[[repo]].rig` lookup instead of hardcoding per rule (preferred — avoids rule duplication per repo).
6. **Build the `pr-auto-review` order** (new, city-local or upstreamed into `github/orders/` once proven): a short script that (a) applies the path/size/author skip-gates from §2.3 using `$GC_GITHUB_EVENT_PAYLOAD_FILE` + `gh pr diff --name-only`, (b) on pass, runs `gc sling <rig>/<agent> mol-pr-review --formula --var pr=$GC_GITHUB_ITEM_NUMBER`, (c) reads the resulting verdict + report, (d) invokes the new `gc github post-review` command (§3.7).
7. **Build `gc github post-review`** (new command in `github/`, alongside `comment-issue`/`create-pr`): implements `POST /repos/{owner}/{repo}/pulls/{n}/reviews` with `event` mapped from the `mol-pr-review` verdict and `comments[]` built from the scorecard findings (each finding already carries file path; line numbers need to be threaded through from the `gh pr diff` parse in `mol-pr-review`'s `scorecard` step — confirm/extend that step to retain line anchors per finding, since today the report step only needs them for the markdown, not for a machine-consumable structure). If a finding can't be anchored to a specific diff line (e.g. an architectural or cross-cutting concern), fall back to including it in the review's top-level `body` rather than dropping it.
8. **Permissions for the posting call**: use the same per-repo/per-rig installation token minted for the order (`github_app_token_env`) — no new auth mechanism needed, just the `pull_requests: write` scope from step 1.
9. **Verify end-to-end** on a low-stakes nominated repo first: open a throwaway PR, confirm the rule matches, the order runs, `mol-pr-review` produces a verdict, and the review posts with correct inline anchoring and correct approve/request-changes state.

---

## 4. Gaps between what exists today and full auto-inline-comment + approve

| Capability | Status |
|---|---|
| Webhook receipt, signature verification | **Exists** (`github/`) |
| Criteria matching (event/action/branch/label) | **Exists** (`rules.toml`, exact-match only) |
| Path/size/author-list filters | **Missing** — recommend implementing in the new order script, not `rules.toml`, to avoid schema changes |
| Repo → rig binding | **Exists** (`rules.toml` `[[repo]].rig`) |
| Automatic dispatch on match (no human step) | **Exists** (`gc order run` via rule action) |
| Review logic / 11-category scorecard | **Exists** (`mol-pr-review`) |
| Verdict computation (approve/request_changes/block) | **Exists** (`mol-pr-review`, local-only today) |
| Per-finding file/line anchoring in a machine-usable form | **Partially exists** — `gh pr diff` gives the data, but `mol-pr-review`'s scorecard step targets a human-readable markdown report, not a structured (path, line) list; needs a small extension to retain that structure |
| Posting a plain top-level PR comment | **Exists** (`post_issue_comment` in `github/`) |
| Posting an **inline**, diff-anchored review comment | **Missing — needs building** |
| Submitting a PR review with **approve/request-changes** state | **Missing — needs building** |
| Permission checks on the auto-review trigger path itself | **Missing for the new order/action** — `repository_permission()` exists but is only wired into the `/gc fix` dispatch path today; the new `pr-auto-review` order has no built-in actor-permission check (arguably less critical here since the trigger is "PR opened/updated" on a nominated repo, not an arbitrary commenter, but see safeguards below re: fork PRs) |

**Net new work required**: (1) the `gc github post-review` command (the single load-bearing gap), (2) the `pr-auto-review` order/formula glue, (3) extending `mol-pr-review`'s scorecard step to retain structured (path, line, severity, body) findings alongside its markdown output, (4) the path/size/author skip-gate logic. Everything else — matching, dispatch, rig binding, auth, review logic — ships today.

---

## 5. Risks and safeguards

- **Auto-approve policy**: an App-authored `APPROVE` review can satisfy branch-protection "required approvals" unattended. Recommend: (a) never auto-approve on repos with a single required-approval count without a second human reviewer also required, or (b) configure the App's review as advisory-only initially (`event = COMMENT` instead of `APPROVE`/`REQUEST_CHANGES`) until confidence is established, graduating to real approve/request-changes later. This should be a per-repo `rules.toml`/`[[repo]]` setting, not global.
- **Fork PRs / untrusted contributors**: `pull_request` events from forks carry attacker-influenced diffs and, for `pull_request_target`-style setups, can be a privilege-escalation vector if the review order ever checks out and executes fork code. `mol-pr-review` only reads via `gh pr diff`/`gh pr view` (no code execution), which is the safe posture — keep it that way; do not extend the auto-review order to run the PR's own code/tests as part of triggering the review.
- **Rate limits / noisy reviews**: re-running full review on every `synchronize` (every push) on active PRs could spam inline comments and burn API quota/App rate limits. Recommend: debounce (e.g. only re-review after N minutes of push inactivity, reusing the existing cooldown-order pattern already used by `github-addressed-message-router`), and on re-review, dismiss/update the prior bot review rather than adding a new one (`PUT /repos/{owner}/{repo}/pulls/{n}/reviews/{review_id}` or dismiss-and-repost) to avoid comment pile-up.
- **No actor-permission gate on the trigger**: unlike `/gc fix`, the proposed rule triggers on the PR event itself, not on a commenter — so `repository_permission()`'s write-access check doesn't directly apply. The real control is which repos are nominated (`[[repo]]` presence) and which branches (`base.ref` match), which is sufficient as long as nomination is deliberate and repo lists aren't accidentally wildcarded.
- **Verdict-to-review-state mapping for `block`**: `mol-pr-review`'s `block` verdict (unresolved blocker in categories 1–4) is more severe than `request_changes`. GitHub's review API only has `APPROVE`/`REQUEST_CHANGES`/`COMMENT` — recommend mapping `block` to `REQUEST_CHANGES` plus an explicit escalation (e.g. mail to a human/maintainer channel or a distinct label) so `block` isn't silently indistinguishable from an ordinary `request_changes`.
- **Findings that can't be anchored to a diff line**: cross-cutting or architectural findings should degrade to the review's top-level body rather than being dropped, per §3.7 — otherwise valid findings silently disappear from the posted review.
