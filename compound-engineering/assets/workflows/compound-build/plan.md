Use the assigned Compound Engineering planning skill materialized for this agent.

Create a plan artifact from the requirements output. Preserve Compound Engineering traceability identifiers and include the stage handoff details needed by the build-base plan, plan-review, and decompose stages.

Read the requirements artifact from workflow root metadata
`gc.build.requirements_path` and write the plan artifact to
`gc.build.plan_path`. After writing the artifact, update the workflow root bead
with:

- `gc.build.plan_path=<plan artifact path>`
- `gc.build.plan_status=approved|draft|failed`
- `gc.build.plan_summary=<one-sentence summary>`

Close this step only after the workflow root metadata and this step metadata
record the same plan outcome.

Do not invoke provider-native subagents or upstream plugin runtime commands. If
upstream methodology would require document-review or research subagents, record
the needed graph lanes as required follow-up.
