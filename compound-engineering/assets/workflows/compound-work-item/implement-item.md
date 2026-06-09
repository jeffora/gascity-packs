Implement this Compound Engineering shared-drain item with {{implementation_target}}.

Run inside the existing shared worktree lifecycle. Resolve the assigned drain
member from metadata, validate ownership and context path {{context_path}} when
set, apply the smallest implementation changes for this item, run focused
verification, write an item summary to
`{{artifact_root}}/task-<source-anchor-id>-summary.md`, and close only the
source anchor on success. Record the summary path, changed files, and
verification result on the source anchor before closing it.

Do not invoke provider-native subagents. This Gas City lane is the work
delegation mechanism for ce-work.
