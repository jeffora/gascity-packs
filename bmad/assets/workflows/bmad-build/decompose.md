Use the assigned BMAD epic/story decomposition skill materialized for this agent.

Create epics and stories from the approved PRD and architecture. Preserve
traceability to BMAD artifacts, create story beads for implementation, and
translate the resulting story set into the build-base decomposition output and
implementation convoy.

Record the implementation convoy ID on the workflow root bead as
`gc.input_convoy_id=<implementation-convoy-id>` with
`bd update <workflow-root-id> --set-metadata gc.input_convoy_id=<implementation-convoy-id>`
before closing.

Do not invoke provider-native subagents or upstream BMAD runtime commands.
