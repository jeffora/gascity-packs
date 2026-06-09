Finalize the approved Superpowers requirements artifact.

Validate that workflow root metadata points to an existing requirements artifact
and that the artifact is approved by the written-spec loop. On success,
preserve the normalized requirements path and approval metadata for the
downstream planning lane.

This lane represents the stock brainstorming terminal state, where Superpowers
would invoke `writing-plans`. In Gas City, do not invoke that skill directly;
close this expansion and let the parent `superpowers-build` plan step route the
approved requirements artifact to `superpowers.writing-plans`.

This is stock checklist item 9 expressed through the Gas City parent formula:
the transition is durable metadata plus the next graph step, not a provider
native skill invocation.

Do not invoke provider-native subagents. Close this sink step with
`gc.outcome=pass`.
