# Review: `gascity` Pack (0.1.6 RC)

**Reviewer scope:** full read of `pack.toml`, `roles/pack.toml`, `README.md`, both
`REQUIREMENTS.md` ledgers, `skills/mayor/SKILL.md`, all 30 files under
`formulas/*.toml`, all 6 files under `schemas/build/*.yaml`, all 7 scripts
under `assets/scripts/*.py`, all 4 gate scripts under
`assets/scripts/checks/*.sh`, all 8 files under `tests/*.py`, a structural
sample of the ~118 files under `assets/workflows/**/*.md`, the two
`gc-role-worker.template.md` copies, and the `roles/agents` / `roles/prompts`
directories. The full pack test suite was executed locally.

For readers unfamiliar with Gas City vocabulary: a **formula** is a declarative
workflow graph (TOML) that Gas City's `graph.v2` engine executes step by step,
routing each step to an agent role; a **bead** is a single unit of work/issue
tracked in the Gas City "beads" (`bd`) store; a **convoy** is a group of
related beads (e.g., all the implementation tasks for one feature) with
dependency edges between them, used to fan work out to parallel worker
sessions and fan the results back in; a **drain** is the mechanism that pulls
convoy members into worker sessions (either `separate` parallel sessions or one
`same-session` shared worker); an **expansion** is a formula that gets inlined
into a parent formula's step to add fanout/fanin sub-steps (e.g., multiple
review lanes that synthesize into one verdict).

---

## 1. What the pack provides

`gascity` is the base/reference "build methodology" pack for Gas City: it
ships the full software-delivery lifecycle (requirements → plan → plan review
→ decomposition → parallel or shared-session implementation → multi-lane
review with a fix loop → final report → optional publish) as a family of
composable `graph.v2` formulas, plus a coordinator skill ("the Mayor") that
turns a user's ask into approved planning artifacts and launches the right
formula. Other packs in this repository (`compound-engineering`, `superpowers`,
`bmad`, `gstack`) import this pack as `gc` and extend its virtual base
formulas with their own methodology-specific prompts/personas, while reusing
its durable graph/drain/artifact-validation machinery instead of raw
provider-native subagent dispatch.

**Inventory:**

- **30 formulas** (`formulas/*.toml`), split roughly into:
  - Virtual/internal base contracts (not user-launchable): `build-base`,
    `planning-base`, `decomposition-base`, `implementation-base`,
    `implementation-item-base`, `code-review-base`, `fix-loop-base`, and the
    five nested continuation-suffix bases
    (`build-from-requirements-base` → `build-from-plan-base` →
    `build-from-decompose-base` → `build-from-convoy-base` →
    `build-from-review-base`).
  - Concrete cataloged (user-runnable) entrypoints: `build-basic`,
    `build-from-requirements`, `build-from-plan`, `build-from-decompose`,
    `build-from-convoy`, `build-from-review`, `implement`, `review`,
    `gap-analysis`, `design-review`, `github-issue-triage`,
    `github-issue-fix`, `github-pr-review`.
  - Internal helpers/utilities: `do-work`, `do-work-item`,
    `same-session-implement`, `fix-convoy`, `publish`,
    `github-issue-triage-base`, `github-issue-fix-base`,
    `github-issue-fix-design-review-work`, `build-basic-review`
    (expansion).
- **6 build-artifact schemas** (`schemas/build/*.yaml`): requirements, plan,
  decomposition, review, implementation-summary, final-report — each an
  "immutable once published" schema ID (`gc.build.<artifact>.v1`) enforcing
  required front matter, allowed status values, and required Markdown section
  order.
- **1 skill** (`skills/mayor/SKILL.md`) — the only skill in the pack (verified
  by `tests/test_skill_frontmatter.py`, which pins the skill set to exactly
  `mayor`).
- **7 Python scripts + 4 shell gate scripts** implementing artifact-root
  resolution, build-artifact/verdict-report/context-bundle validation,
  bead/convoy creation from a task plan, and a GitHub API/report wrapper
  layer.
- **~118 workflow prompt assets** under `assets/workflows/<formula>/<step>.md`
  — the shadowable prose that each formula step's `description_file` points
  at.
- **11 rig-role agent definitions** under `roles/agents/*` (e.g.
  `implementation-worker`, `implementation-reviewer`, `task-decomposer`,
  `review-synthesizer`, `gap-analyst`, `publisher`, `run-operator`, etc.),
  each providerless (no hardcoded model/provider), routed to by formula step
  metadata (`gc.run_target`).

**Maturity / status:** The pack labels itself Status: **Pilot** in both
`REQUIREMENTS.md` ledgers, and the working title in this review is "0.1.6 RC."
The `git log` for `rigs/gascity-packs/gascity/` (repo root:
`rigs/gascity-packs`) shows the pack has moved fast and recently through a
methodology-contract rewrite:

```
3b3b89f Release gascity pack 0.1.6 RC fixes (#110)
99464ed Normalize legacy work option metadata in task creation (#68)
af16409 fix(gascity): restore executable test script modes
f946ae5 fix(gascity): align build workflow with graph v2 validation
04343b0 docs: install via homebrew-core and gc import add in quick starts
af98392 docs: beginner-first READMEs for the build packs
d978aa8 merge origin/main: bring embed module, registry 0.1.2 release, and slack idempotency fixes into the methodology branch
a55eeec fix(gascity): re-declare producer artifact gates on step overrides
94c4438 feat(gascity): land build continuation entrypoints and starter review fanout
5fc675b fix(gascity): mark pack test scripts executable
07a4265 test: prove derived-pack compatibility for GC-METH-012
5274362 feat: make interaction/review modes and methodology metadata first-class
19aee2a feat(gascity): gate producer stages with bounded artifact validation
87c87b9 feat(gascity): add build artifact schemas and shared validator
24fb5b8 feat: reconcile base contract ledgers
06e3424 checkpoint: methodology pack integrations
2c68470 feat: make methodology packs import gascity base
26cbaee feat: add build methodology packs
a972fcf fix(gc): remove issue-fix design alias step
889c704 fix: address PR review gates
```

Reading this as a narrative: the pack started as a smaller GitHub-adapter-only
tool (`a972fcf`, `889c704`), then grew a full build-methodology base contract
(`26cbaee`, `2c68470`, `24fb5b8`), added artifact schemas and a shared
validator with bounded schema-repair gating (`87c87b9`, `19aee2a`), made
interaction/review modes and methodology metadata first-class compatibility
surfaces (`5274362`), proved derived-pack compatibility for the four vendored
methodology packs (`07a4265`), landed the nested `build-from-*` continuation
entrypoints and the `build-basic-review` starter fanout (`94c4438`), and then
spent the last several commits (`a55eeec` through `3b3b89f`) on graph-v2
validation alignment, executable-bit fixes for test/check scripts, and a
"0.1.6 RC" release/fixes pass. This is consistent with a pack that has just
finished a substantial architectural rewrite (continuation suffixes, mode
system, artifact validation gates) and is now in a stabilization/bugfix
period rather than long-since-settled.

---

## 2. How to implement/install it in a city

Based strictly on `pack.toml`, `roles/pack.toml`, `README.md`, and
`REQUIREMENTS.md` (no invented steps):

**Two separate packages, two import scopes.** The pack ships as two
independently versioned `pack.toml` units in the same repo path:

- `gascity` (`pack.toml`, `name = "gascity"`, `version = "0.1.0"`, `schema =
  2`) — the formulas + mayor skill, imported **once at city scope**.
- `gc-roles` (`roles/pack.toml`, `name = "gc-roles"`, `version = "0.1.0"`,
  `schema = 2`) — the rig-local worker/reviewer role agents, imported **once
  per rig** that should actually run work.

Neither `pack.toml` declares a `depends`/`requires` field — there is no
machine-enforced dependency; the two-import requirement is only documented in
prose (README) and will silently under-function if skipped (see Risks below).

**Prerequisites** (from README):
- Gas City installed and a city running (`gc init`, `gc start`).
- The target project added as a rig (`gc rig add .` inside the repo).
- `bd`/beads and Dolt are implied by the surrounding Gas City runtime (this
  pack's scripts shell out to `bd`, `gc bd`, `gc convoy`, `gc hook`, `gc
  runtime drain-ack`) but the pack itself does not install or configure them.
- Python 3 with PyYAML available on the machine that runs
  `assets/scripts/*.py` (the mayor's `create_beads_from_tasks.py` step and
  every `build-artifact-valid.sh` check invoke `python3` directly).
- `gh` CLI on PATH for any GitHub adapter workflow (`github_api.py` shells out
  to `gh api`).
- `jq` on PATH for the shell gate scripts
  (`design-review-approved.sh`, `gap-analysis-approved.sh`,
  `implementation-review-approved.sh`).

**Concrete install/launch flow (from README "Quick Start"):**

1. Import the pack at city scope:
   ```sh
   gc import add --name gc https://github.com/gastownhall/gascity-packs.git//gascity
   ```
2. Add the rig-scoped roles import in `city.toml`, then run `gc import
   install`:
   ```toml
   [[rigs]]
   name = "your-project"

   [rigs.imports.gc]
   source = "https://github.com/gastownhall/gascity-packs.git//gascity/roles"
   ```
   (For local pack development, point `source` at a local clone path instead,
   e.g. `../gascity-packs/gascity`.)
3. Create a bead for the work and launch the starter factory:
   ```sh
   gc bd create "Add a --json flag to the export command"
   gc sling gc.run-operator <bead-id> --on build-basic \
     --var artifact_root=plans/json-flag/build
   ```
4. Watch it run via `gc session attach <name>` or by inspecting the workflow
   root bead's metadata as stages complete; read results under
   `artifact_root` (`requirements.md`, `implementation-plan.md`, review
   reports, `factory-run.md`).

Alternatively, drive the whole flow conversationally with `Use skill
gc.mayor`, which interviews the user, writes `requirements.md` /
`implementation-plan.md` / `tasks.md` under `<rig-root>/plans/<plan-slug>/`
(falling back to `<rig-root>/gc-plans/<plan-slug>/` if `plans/` already exists
and looks foreign — this fallback logic lives in and is unit-tested by
`assets/scripts/artifacts.py` / `tests/test_artifacts.py`), and after
approval runs `assets/scripts/create_beads_from_tasks.py` in `--dry-run` then
for real to materialize beads/convoys via `gc bd` / `gc convoy`.

**Config knobs exposed** (documented in README, all `--var` overrides at
launch or pinnable per-rig as `formula_vars`):

| Variable | Default | Effect |
|---|---|---|
| `artifact_root` | required | Where build artifacts land under the rig |
| `interaction_mode` | `interactive` | `interactive` / `autonomous` / `headless` — how much the workflow blocks on questions |
| `review_mode` | `agent` | `report` / `agent` / `interactive` — review's authority to write findings vs. apply fixes |
| `drain_policy` | `separate` | `separate` (parallel worker sessions per convoy member) or `same-session` (serial, one shared worker) |
| `implementation_target` | `gc.implementation-worker` | Which rig role implements each item |
| `push` / `open_pr` | `false` | Gate publish-stage push/PR side effects |
| `max_iterations` | `10` | Bound on implementation/review fix-loop attempts |

**What changes on disk / in the bead store when installed and run:** installing
only adds the pack's formulas/skill/roles to the city/rig import graph (no
bead-store writes at install time). Running a workflow creates: a workflow
root bead plus per-stage step beads (and, for drains, one convoy + N member
beads per implementation item) in the rig's bead store; Markdown artifact
files under the resolved `artifact_root` (`requirements.md`,
`implementation-plan.md`, `decomposition.md`, `implementation-summary.md`,
`reviews/attempt-<n>/{report,fixes}.md`, `final-report.md`); and, for the
mayor's default `plans/` root, a `.gc-plans` marker file the first time it
creates the directory (so later runs know the directory is GC-owned rather
than "foreign").

---

## 3. Risks / gaps / rough edges

**Test suite status: all green, but purely static/asset-level.** Running
`python3 -m pytest tests/ -q` (after installing `pytest` + `pyyaml` into a
throwaway venv — neither is bundled or pinned anywhere in the pack, see
below) produced:

```
167 passed, 11055 subtests passed in 4.63s
```

No failures, no skips. However, essentially every test in the suite —
including the large `test_formula_assets.py` (4,515 lines, 77 top-level test
methods, the bulk of the subtest count) and
`test_derived_pack_compatibility.py` — is a **static text/structure assertion
over TOML and Markdown files** (e.g., "does `build-basic` extend `build-base`
and preserve stage order," "do all `[metadata.gc.run_target]` values resolve
to a providerless role agent," "do all formulas have a
`formulas/REQUIREMENTS.md` row"). There is **no integration test that actually
executes a formula graph** end-to-end through a real or simulated `gc`
runtime — nothing exercises the drain/fan-in mechanics, the bounded
schema-repair retry loop, the `build-artifact-valid.sh` gate against a live
bead store, or the GitHub adapter comment/PR flows against a real API. The
Python-level unit tests (`test_artifacts.py`, `test_validators.py`,
`test_create_beads_from_tasks.py`, `test_github_api.py`,
`test_github_reports.py`) do properly unit-test the standalone scripts in
isolation (artifact-root resolution, schema validation edge cases,
plan-parsing/topo-sort, GitHub URL parsing, comment rendering/redaction), and
those are meaningfully thorough (e.g. secret-path detection in context
bundles has ten-plus adversarial cases). But the "it fits together at runtime"
claim in the README and REQUIREMENTS ledgers is not proven by this test
suite — it is proven only by static conformance checks.

**No pinned test/runtime dependencies.** There is no `pytest.ini`,
`conftest.py`, `pyproject.toml`, or `requirements*.txt` anywhere in the pack
or its parents. `pytest` was not installed in the ambient Python 3.14
environment and had to be installed manually into a scratch venv; PyYAML
happened to already be present. A fresh contributor or CI runner has no
documented, reproducible way to know which Python/pytest/PyYAML versions this
suite expects, and the README's "Evidence Index" commands (`python3 -m pytest
gascity/tests/... -q`) assume `pytest` is already on PATH without saying how
it gets there.

**Duplicate `gc-role-worker.template.md` — byte-identical, not drifted (yet), but a
maintenance hazard.** The task's specific instruction was to check for drift
between `roles/template-fragments/gc-role-worker.template.md` and the
top-level `template-fragments/gc-role-worker.template.md`. `diff` between the
two files returns **no differences** (exit code 0) — they are exact
duplicates today. That is good news for correctness right now, but it is a
structural risk: nothing in the pack (no test, no build step) enforces that
these two copies stay in sync. This large (239-line) file defines the
claim/close protocol every rig-role worker agent depends on (the
`gc hook --claim --json` loop, continuation-group handling, close-metadata
rules). If a future edit updates one copy and not the other — an easy mistake
since they live in different directories with no cross-reference comment in
either file — rig-local workers and city-scope-imported workers would
silently diverge in claim/close behavior with no test catching it. Recommend
either: (a) making one a symlink/copy-on-build of the other, or (b) adding a
test (mirroring the existing `test_skill_frontmatter.py` pattern) that asserts
byte-equality between the two paths.

**No enforced pack dependency between `gascity` and `gc-roles`.** Both
`pack.toml` files are minimal (`name`, `version`, `schema` only) with no
`depends`/`requires` field. The two-import requirement (city-scope formulas +
per-rig roles) is entirely a documentation convention in `README.md`. The
README itself acknowledges the failure mode: "A city that imports only the
formulas can read the mayor skill, but default formula steps will not have
rig-local `gc.*` role agents to route to." This is a silent-degradation risk
for new adopters who only follow the "first import" line and skip the
per-rig roles import — formulas will still catalog and launch, but routing
will fail at the first step that needs a rig-local agent, with no compile-time
or install-time check to catch the omission earlier.

**Derived-pack compatibility is asserted, not independently verified here.**
`REQUIREMENTS.md`'s "Deferred Follow-Up Requirements" section explicitly notes
GC-METH-012 depends on `tests/test_derived_pack_compatibility.py` proving
consistency across `compound-engineering`, `superpowers`, `bmad`, and
`gstack` — all four of which live as sibling packs outside the reviewed
directory. That test does pass today (folded into the 167/167), but this
review did not read those four sibling packs, so "gascity's contract is
honored by every derived pack" is taken on faith from that one static test,
not independently confirmed against the derived packs' own formula graphs.

**Mode/authority surface is wide and easy to misconfigure.** `interaction_mode`
(3 values) × `review_mode` (3 values) × `drain_policy` (2 values) ×
per-formula `allowed_drain_policies`/`interaction_modes`/`review_modes`
metadata subsets is a meaningfully large combinatorial surface for a "Pilot"
labeled pack. The `prepare` stage documentation (`assets/workflows/build-base/
prepare.md`) does specify a fail-closed contract (record `gc.build.status
=blocked` and stop for unsupported combinations), and
`test_methodology_metadata_uses_only_allowed_vocabulary` /
`test_methodology_mode_vars_have_valid_defaults` guard the *declared*
vocabulary — but there is no runtime test proving the *blocked* path actually
fires correctly for every unsupported combination, since (per the point
above) nothing in this suite executes a real workflow.

**Artifact-root "foreign directory" heuristic is implicit and a little
surprising.** `assets/scripts/artifacts.py::_plans_root_is_foreign` silently
redirects the default artifact root from `<rig>/plans` to `<rig>/gc-plans`
whenever an existing `plans/` directory doesn't look GC-owned (no
`.gc-plans` marker, no recognized artifact filenames, no `github/` subdir).
This is well-unit-tested (`test_artifacts.py`), and the README does document
the fallback, but the heuristic is easy to trip silently in any project that
already has an unrelated `plans/` directory for other purposes — a user could
get artifacts routed to `gc-plans/` instead of `plans/` without any prompt or
warning, only discoverable by reading the resolved path back out.

**Design ambition vs. documentation depth is uneven.** The two `REQUIREMENTS.md`
ledgers are unusually rigorous (stable IDs, explicit "how to reconcile"
sections, evidence indices) — this is a strength, not a gap, but it does mean
the bar for keeping them in sync with formula changes is high, and the ledger
itself says "Behavior-changing code, formula, or prompt edits require a
corresponding requirements edit" as a maintenance rule that depends entirely
on author discipline (`test_base_formula_requirements_cover_formula_set` only
proves *a row exists per formula*, not that the row is still accurate).

**Nothing catastrophic found in the scripts.** The Python scripts
(`artifacts.py`, `validate_build_artifact.py`, `validate_context_bundle.py`,
`validate_verdict_report.py`, `create_beads_from_tasks.py`, `github_api.py`,
`github_reports.py`) are careful about path-escape prevention (`resolve_artifact_path`
rejects paths outside root), secret-path avoidance in context bundles (an
extensive, well-tested denylist), safe subprocess usage (`gh api` and `gc
bd`/`gc convoy` invoked as argument lists, not through a shell), and
sanitizing untrusted GitHub issue/PR content before echoing it into rendered
comments (`UNSAFE_MARKER_RE`, heading-demotion in
`demote_markdown_headings`). No obvious injection or path-traversal bug was
found in this review's reading of these files.

---

## 4. Recommendation for broad rollout

**Go, with caveats.** The pack is architecturally coherent, its static
conformance test suite is comprehensive and currently 100% green
(167 passed / 11,055 subtests), the documented install/launch flow is
concrete and grounded in real README/REQUIREMENTS text, and the standalone
Python utilities are well-unit-tested and defensively written. The "Pilot"
label and 0.1.6-RC-shaped recent git history (a major continuation-entrypoint
and mode-system rewrite landing over the last ~15 commits) argue for treating
this as a "ready to roll out with a watch list" release rather than a fully
hardened one.

Punch list before/alongside wider fleet rollout:

1. **Add a runtime/integration smoke test** — even one end-to-end run of
   `build-basic` (or a mocked equivalent) against a real or fake `gc`/`bd`
   runtime, exercising at least one drain + one schema-repair retry + one
   review/fix loop iteration — to validate what the current suite can only
   assert statically.
2. **Pin test dependencies.** Add a `requirements-dev.txt` or
   `pyproject.toml` (or at minimum, document `pip install pytest pyyaml` in
   the README) so `python3 -m pytest gascity/tests/ -q` is reproducible for
   new contributors and CI.
3. **De-duplicate or lock the two `gc-role-worker.template.md` copies** — add
   a byte-equality test (cheap, mirrors `test_skill_frontmatter.py`) or make
   one a generated copy of the other, so future edits can't silently diverge
   the claim/close protocol between city-scope and rig-scope role workers.
4. **Consider a machine-checked dependency between `gascity` and `gc-roles`**
   (or at minimum a `gc formula show`/`gc import` warning) so omitting the
   per-rig roles import fails fast instead of degrading silently at first
   routed step.
5. **Independently validate at least one derived pack** (e.g.
   `compound-engineering` or `superpowers`) against this base's current
   contract before treating GC-METH-012 as closed for fleet purposes, since
   this review did not read those sibling packs.
6. Given the "Pilot" status and recency of the mode/continuation-entrypoint
   rewrite, prefer a staged rollout (a small number of pilot rigs running
   `build-basic` and `github-issue-fix` first) before wiring this pack into
   every city as a default.
