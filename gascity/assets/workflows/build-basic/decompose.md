Use the built-in Gas City `create-beads` decomposition flow.

Create task beads or a decomposition artifact from the approved requirements
and implementation plan. Preserve traceability from each work item back to the
relevant acceptance criteria and plan section, and record the implementation convoy
that the `implement` formula will drain.

Create a new implementation convoy for the work units. Do not reuse the source
or launch convoy from `gc.var.convoy_id`.

Record the decomposition output on the workflow root bead, then set both
`gc.input_convoy_id=<implementation-convoy-id>` and
`gc.build.implementation_convoy_id=<implementation-convoy-id>` on the workflow
root bead with a quoted command like:

`bd update "<workflow-root-id>" --set-metadata "gc.input_convoy_id=<implementation-convoy-id>" --set-metadata "gc.build.implementation_convoy_id=<implementation-convoy-id>"`

before closing, verify both metadata fields exist on the workflow root and point
to the new implementation convoy.
