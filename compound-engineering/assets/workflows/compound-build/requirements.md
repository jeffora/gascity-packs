Use the assigned Compound Engineering brainstorm skill materialized for this agent.

Run the brainstorm discipline against the build target and optional context path. Produce a requirements artifact in the build artifact root that preserves Compound Engineering requirement and assumption identifiers while satisfying the build-base requirements contract.

Read the requirements path from workflow root metadata
`gc.build.requirements_path`. After writing the artifact, update the workflow
root bead with:

- `gc.build.requirements_path=<requirements artifact path>`
- `gc.build.requirements_status=approved|draft|failed`
- `gc.build.requirements_summary=<one-sentence summary>`

Close this step only after the workflow root metadata and this step metadata
record the same requirements outcome.

Do not invoke provider-native subagents or upstream plugin runtime commands.
