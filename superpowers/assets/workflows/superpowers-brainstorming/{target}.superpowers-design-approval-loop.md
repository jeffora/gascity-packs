Coordinate the Superpowers design approval loop.

Each attempt follows the stock Superpowers sequence before writing a spec:
brainstorm the design candidate, then confirm design approval. Stop only when
the approval lane records `design_review.verdict=done`.

Do not invoke provider-native subagents. Continue only through this graph
stage's lanes.
