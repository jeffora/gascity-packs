Close the Superpowers implementation source anchor.

Resolve the source anchor using the same rules as the inherited worktree setup.
Read `work_dir`, verify the task summary exists, verify the expected task commit
or clean working-tree evidence exists, and confirm the source anchor still
matches the current drained item.

On success, close only the source anchor with `gc.outcome=pass`. Read the
source anchor back and verify it is closed before closing this step. Do not close
the drain-unit convoy, parent convoy, workflow root, or post-implementation
review steps.

Do not invoke provider-native subagents or upstream plugin runtime commands.
