Create the Superpowers implementation convoy from the approved plan.

Read the approved requirements artifact, the approved Superpowers plan, and any
existing decomposition artifact path. The plan may contain the stock
Superpowers task structure with checkbox steps for test writing, verification,
implementation, and commit. Treat those checkbox steps as execution procedure,
not as task-bead content.

For each `### Task N` section, create one implementation bead containing only
the work unit scope:

- task title and plan section reference
- files to create, modify, or test
- behavior or acceptance criteria covered by this task
- dependencies on earlier tasks, when required
- links to the approved requirements and plan artifacts

Do not copy the plan checkbox steps into the implementation bead. The drained
Superpowers implementation workflow supplies that procedure for each convoy
member.

Create or update the implementation convoy with those beads and dependency
edges. Record the implementation convoy ID on the workflow root bead as
`gc.input_convoy_id=<implementation-convoy-id>` with
`bd update <workflow-root-id> --set-metadata gc.input_convoy_id=<implementation-convoy-id>`.

Write a decomposition artifact that maps every plan task to its bead ID and
dependency edges. Close this step only after the decomposition artifact exists,
the workflow root bead has `gc.input_convoy_id`, and the implementation convoy
is ready for drain before closing.

Do not invoke provider-native subagents or upstream plugin runtime commands.
