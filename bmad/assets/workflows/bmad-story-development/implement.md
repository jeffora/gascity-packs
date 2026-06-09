Run the BMAD story-development loop for the source-anchor worktree.

Use the `work_dir` already prepared by the inherited do-work lifecycle. The
child lanes replace BMAD quick-dev's native sub-agent/task handoff: implement
story, self-check, acceptance audit, and apply findings. Use the
implementation-review approval check to decide whether another loop iteration
is needed.

Do not invoke provider-native subagents. Re-run or continue only through this
Gas City graph stage's child steps.
