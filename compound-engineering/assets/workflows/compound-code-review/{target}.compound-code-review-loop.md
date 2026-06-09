Control node for the Compound Engineering code-review loop.

The controller owns the retry/check mechanics for this loop. The child lanes
carry reviewer selection, conditional gates, actual reviewer work, gap
analysis, synthesis, and fix instructions. The selector runs before this loop;
inside the loop, each conditional gate either opens its paired reviewer bead or
closes the paired reviewer bead with a no-op artifact. This node exists so the
implementation-review approval check can decide whether another loop iteration
is needed.

Do not spawn model-native subagents. Re-run or continue only through the child
lanes in this graph stage.
