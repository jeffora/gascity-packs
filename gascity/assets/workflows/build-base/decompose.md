This is the `build-base` decompose stage. Treat it as a virtual contract that concrete formulas may override.

Convert the approved requirements and plan into executable work units. The
decomposition must preserve traceability back to the plan, create or identify
the implementation beads that will form the implementation convoy, and avoid
implementation choices not already supported by the approved artifacts.

Create a new implementation convoy for the work units. Do not reuse the source
or launch convoy from `gc.var.convoy_id`; that convoy only carried the original
workflow request. The implementation convoy must contain only the runnable work
unit beads that the drain stage should execute.

Record the implementation convoy ID on the workflow root bead as both:

- `gc.input_convoy_id=<implementation-convoy-id>` for the drain contract.
- `gc.build.implementation_convoy_id=<implementation-convoy-id>` for build
  reporting and downstream methodology-specific stages.

Use one quoted `bd update` command against the workflow root bead, for example:

`bd update "<workflow-root-id>" --set-metadata "gc.input_convoy_id=<implementation-convoy-id>" --set-metadata "gc.build.implementation_convoy_id=<implementation-convoy-id>"`

Close this step only after the decomposition artifact or task beads are
recorded on the workflow root bead and both convoy metadata fields are set
before closing. Verify the recorded implementation convoy is not the original
launch/source convoy.
