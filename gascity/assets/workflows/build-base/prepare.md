This is the `build-base` prepare stage. Treat it as a virtual contract that concrete formulas may override.

Launch inputs:

- artifact_root: {{artifact_root}}
- context_path: {{context_path}}
- requirements_path: {{requirements_path}}
- plan_path: {{plan_path}}
- decomposition_path: {{decomposition_path}}
- drain_policy: {{drain_policy}}
- implementation_target: {{implementation_target}}
- max_iterations: {{max_iterations}}
- push: {{push}}
- open_pr: {{open_pr}}

Validate the target, artifact root, and optional context inputs. Record the normalized artifact paths on the workflow root bead so later stages can reuse them without inventing new locations.

Persist the normalized values on the workflow root bead using `gc.var.<name>` for each launch input and `gc.build.<artifact>_path` for resolved artifact paths. If an optional path input is blank, derive it under the resolved artifact root and record the derived absolute path.

When updating metadata, store plain scalar strings without embedded quote
characters. Prefer a single JSON-object update with `bd update <root> --metadata
'{"gc.var.push":"false","gc.var.open_pr":"false","gc.var.max_iterations":"10"}'`
or individually quoted `--set-metadata 'key=value'` arguments. Do not write
values like `"false"` or `"10"` that include literal double quotes.

Do not edit source files. Close this step only after the required paths and input assumptions are explicit.
