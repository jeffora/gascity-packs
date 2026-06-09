Coordinate the Compound Engineering plan-review loop.

The child lanes are Gas City graph steps that replace the upstream document-review subagent fanout. Wait for all child lanes, then use the design-review approval check to decide whether another loop iteration is needed.

Do not spawn model-native subagents. Re-run or continue only through this
graph stage's child steps.
