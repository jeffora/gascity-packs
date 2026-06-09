Prepare BMAD story development.

Resolve the BMAD PRD, architecture, epics/stories output, worktree, artifact root, and current sprint/status context. Write a compact context file for the implementation and review lanes.

Close with `gc.outcome=pass` only after the context file exists and its path is
recorded on the workflow root and this step.

Do not invoke provider-native subagents or upstream BMAD runtime commands. This
graph stage converts BMAD's sub-agent/task handoff into Gas City lanes.
