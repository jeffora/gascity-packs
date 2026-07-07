# Review: `gascity` pack `mayor` skill

Reviewed file: `rigs/gascity-packs/gascity/skills/mayor/SKILL.md` (218 lines, new).
Compared against: the built-in mayor prompt (`rigs/gascity/cmd/gc/prompts/mayor.md`),
the gastown-pack mayor prompt template (`rigs/gascity-packs/gastown/agents/mayor/prompt.template.md`),
and the seven `core.gc-*` skills a mayor session already loads (`gc-work`, `gc-dispatch`,
`gc-agents`, `gc-rigs`, `gc-mail`, `gc-city`, `gc-dashboard`, all under
`rigs/gascity/internal/bootstrap/packs/core/skills/`).

## 1. What the skill does and how it works

The skill's frontmatter (`skills/mayor/SKILL.md:1-4`) triggers on the literal word
"Mayor"/"mayor"/"$mayor"/"/mayor"/"@mayor" or on requests to plan, create beads,
schedule, start, or run a workflow. Once triggered, it hands the session a
five-part **planning-and-launch playbook**, not a dispatch playbook:

1. **Operating Model** (lines 16-30) — pick a rig root / plan slug / artifact
   root (defaulting to `<rig-root>/plans/<plan-slug>/`), inspect the repo before
   asking questions, interview one question at a time with a recommended
   answer attached, and keep artifact-approval gates separate from workflow
   execution (don't auto-approve requirements/plans unless the user explicitly
   asked for a fully autonomous run).
2. **Requirements** (lines 32-70) — write/revise a `requirements.md` with a
   fixed YAML frontmatter (`plan_slug`, `phase`, `rig`, `rig_root`,
   `artifact_root`, `status`, timestamps) and a fixed Markdown body (Problem
   Statement / Solution / User Stories / Out Of Scope / Other Notes). No
   engineering decisions belong here.
3. **Implementation Plan** (lines 72-116) — after requirements approval, write
   `implementation-plan.md` (adds `requirements_file` to the frontmatter; body
   is Summary / Current System / Proposed Implementation / Testing / Rollout /
   Open Questions), concrete enough to drive bead creation, and calls out
   "convoy boundaries" for work that should be grouped.
4. **Create Beads** (lines 118-157) — write `tasks.md` (adds
   `implementation_plan_file` to the frontmatter, plus a `## Bead Creation
   Payload` YAML block using nested `convoys[]`, never `epics[]`), then run a
   pack-supplied script twice — dry-run, then for real:
   `python3 <pack-root>/assets/scripts/create_beads_from_tasks.py <tasks.md>
   [--dry-run] [--city <path>]`. This script (present at
   `gascity/assets/scripts/create_beads_from_tasks.py`) is what actually turns
   the YAML payload into convoys and runnable beads — the skill does not
   describe calling `gc bd create`/`gc convoy create` by hand for this step.
5. **Formula Discovery / Execution** (lines 159-219) — before running any
   workflow, call `gc formula catalog --json` and only treat catalog-listed
   `name`s as user-runnable; inspect the chosen formula with `gc formula show
   <name> --json` to read its `vars` before filling them in (never passing
   reserved `graph.v2` vars like `convoy_id`/`issue`/`bead_id`); then launch
   with `gc sling <coordinator-target> <bead-or-convoy-id> --on <formula>
   --var k=v` (attached) or `gc sling <coordinator-target> <formula-name>
   --formula --var k=v` (targetless), defaulting the coordinator target to
   `gc.run-operator`. After launch, report the workflow root/bead IDs and the
   next checkpoint rather than assuming completion.

Net effect: the skill gives a mayor session a **repeatable artifact pipeline**
(idea → `requirements.md` → `implementation-plan.md` → `tasks.md` → beads →
formula run) with explicit approval gates between each artifact, plus a
formula-catalog-driven way to launch workflows instead of freehand `gc sling`.

## 2. How it differs from existing mayor guidance

### vs. the built-in `mayor.md` prompt (`rigs/gascity/cmd/gc/prompts/mayor.md`)

The built-in prompt is a five-line "how to work" loop: add rigs, add agents,
`gc bd create` a title, `gc sling <agent> <bead-id>`, monitor with `gc bd
list`/`gc session peek`. It has no concept of requirements/plan/tasks
artifacts, no approval gates, no formula catalog/discovery step, and no
convoy-grouping guidance. The new skill is a strict superset in ambition: it
assumes the built-in loop for simple one-off beads still exists, but adds a
whole planning phase in front of it for work that needs shaping first, and
replaces ad hoc `gc sling <agent> -f <formula>` with a discover-then-inspect
protocol.

### vs. the gastown-pack mayor prompt template (`gastown/agents/mayor/prompt.template.md`)

This is the more developed "prior guidance" a Gastown-pack mayor already
carries, and the contrast is sharper here:

- **Philosophy.** The gastown prompt's central directive is "Dispatch
  Liberally, Fix When Fast" — file a bead and immediately `gc sling` it to a
  polecat pool, only writing code directly for <5-minute fixes. The new skill
  never mentions polecats, pools, or fixing code directly at all; its
  explicit charter is "Do not implement source changes unless the user
  explicitly asks to run an implementation workflow through a formula." These
  are close to opposite postures on when a mayor-role session should touch
  code.
- **What "create work" means.** Gastown's prompt treats bead creation as a
  single `gc bd create "title"` call, with heavy emphasis on *which rig's
  database* to file into (two-level `hq-`/rig-prefix architecture, prefix
  routing, the "fix in beads rig vs. gastown rig vs. HQ" test). The new skill
  never discusses multi-rig prefix routing at all — it assumes one
  `rig_root`/`artifact_root` pair per plan and defers all the mechanics of
  *where beads land* to the `create_beads_from_tasks.py` script's `--city`
  flag and convoy nesting.
- **Formula launch mechanics.** Gastown's prompt doesn't discuss `gc formula
  catalog`/`gc formula show` at all — formulas are launched by convention
  (`mol-do-work`, `mol-polecat-work`, etc., documented in `gc-dispatch`, see
  below) with the mayor expected to already know the formula name. The new
  skill adds a discovery-first requirement: don't present a formula as
  runnable unless it appears in `gc formula catalog --json`, and always `gc
  formula show` it first to read `vars`.
  - This is close to `gc-dispatch`'s built-in-formula catalog (`mol-do-work`,
    `mol-polecat-commit`, `mol-polecat-report`, `mol-polecat-work`,
    `mol-idea-to-plan`, patrol formulas) but the mayor skill treats that list
    as untrustworthy/incomplete and insists on live discovery instead.
- **Rig wake/sleep, prefix conflicts, PR repo defaults, `gc handoff`, session-
  end git-push checklist** — all present in the gastown prompt, all absent
  from the new skill. The skill is narrowly scoped to the planning-artifact →
  bead → formula-launch pipeline and says nothing about rig lifecycle,
  handoff, or git hygiene.

### vs. the `core.gc-*` skills a mayor already loads

The seven core skills (`gc-work`, `gc-dispatch`, `gc-agents`, `gc-rigs`,
`gc-mail`, `gc-city`, `gc-dashboard`) are **mechanical command references** —
each documents one `gc` subsystem's CLI surface (`gc bd ...`, `gc sling
...`, `gc agent ...`, `gc rig ...`, `gc mail ...`, `gc <city lifecycle>
...`, `gc dashboard ...`) with no opinion about workflow, sequencing, or
approval gates. `gc-dispatch` in particular already documents `gc sling`,
`gc convoy`, and the built-in/gastown formula catalog in the same mechanical
style.

The new mayor skill sits one layer above all of them: it is a **process/
workflow layer that composes those primitives** — it tells the mayor *when*
to use `gc bd create`/`gc convoy` vs. write an artifact file first, *when* to
call `gc formula catalog`/`gc formula show` before `gc sling`, and enforces
gating (don't skip from idea straight to bead creation without an approved
plan) that none of the core skills express an opinion on. It doesn't
duplicate their command syntax — it references the pack's own script
(`create_beads_from_tasks.py`) rather than raw `gc bd`/`gc convoy` calls for
the bead-creation step, and references `gc sling`/`gc formula` the same way
`gc-dispatch` does but adds the discovery/inspection discipline on top.

## 3. What changes for a city that adopts it

- **A new default entry point for "shape work first."** Any mention of
  Mayor/`$mayor`/`/mayor`/`@mayor`, or a request to plan/create beads/
  schedule/start/run a workflow, now pulls in a structured artifact pipeline
  (`requirements.md` → `implementation-plan.md` → `tasks.md`) with named
  frontmatter schemas and approval gates, instead of the mayor free-styling a
  plan in chat and firing off `gc bd create` calls directly. Cities that want
  a paper trail for requirements/design before beads exist gain one "for
  free" whenever this skill fires — but only when the skill's trigger phrase
  or intent (plan/create beads/schedule/run a workflow) is present; a plain
  one-off task request may still fall through to the built-in `mayor.md` loop
  or the gastown prompt's polecat-first behavior.
- **A behavioral tension with the gastown "dispatch liberally" mayor.** In any
  city running the gastown pack, this skill's "do not implement source
  changes unless explicitly asked to run an implementation workflow through a
  formula" instruction can conflict with the gastown prompt's "fix directly
  when it's <5 minutes" guidance and its default of immediately slinging
  every filed bead to a polecat pool. Whichever guidance the session actually
  attends to first (prompt template vs. skill trigger) will determine
  real behavior; this pack does not reconcile the two, so a city adopting it
  alongside gastown should expect the mayor to sometimes gate on formal
  plan/task artifacts and sometimes short-circuit straight to `gc bd
  create` + `gc sling <polecat>`, depending on how the request is phrased.
- **Bead creation moves off ad hoc `gc bd create` for planned work.** For
  work that went through the requirements/plan/tasks pipeline, bead and
  convoy creation runs through `assets/scripts/create_beads_from_tasks.py`
  (dry-run then real) rather than a human/agent hand-typing `gc bd create`/
  `gc convoy create` calls. Cities adopting this skill should expect
  convoy structure (nested `convoys[]`, resolved local-key dependencies) to
  come from that script's parsing of `tasks.md`, and should keep it in sync
  with any `gc convoy`/`gc bd` schema changes — the skill's guidance ("Do not
  emit `epics[]`") already reflects one such migration (epics deprecated in
  favor of convoys, per `gc-dispatch`'s migration note).
- **Formula selection becomes catalog-gated.** A city adopting this skill
  should keep `[catalog]` metadata current on any formula it wants the mayor
  to offer end users — formulas not opted into the catalog will not be
  presented as runnable, even if they exist and are otherwise usable via
  `gc sling ... --formula`.
- **No change to rig/agent lifecycle, mail, or dashboard behavior.** The
  skill does not touch `gc-agents`, `gc-rigs`, `gc-mail`, `gc-city`, or
  `gc-dashboard` concerns at all, so cities adopting it see no change to how
  rigs are added/suspended, how agents are managed, or how mail/dashboard
  work — only to the planning-and-bead-creation and formula-launch behavior
  described above.
