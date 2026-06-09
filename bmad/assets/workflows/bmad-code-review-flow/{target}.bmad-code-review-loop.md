Control node for the BMAD code-review loop.

The controller owns the retry/check mechanics for this loop. The child lanes
carry the blind-hunter, edge-case, acceptance-auditor, gap-analysis, synthesis,
and apply-findings instructions. This node exists so the implementation-review
approval check can decide whether another loop iteration is needed.

Do not spawn model-native subagents. Re-run or continue only through the child
lanes in this graph stage.
