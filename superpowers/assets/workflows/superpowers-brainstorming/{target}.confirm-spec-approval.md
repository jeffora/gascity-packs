Confirm Superpowers spec approval.

This lane represents the stock `User reviews spec?` approval gate after the
spec review and feedback pass, corresponding to stock checklist item 8. A
change request loops back through the written spec pass; approval lets the
workflow transition to downstream planning. Use workflow root metadata
`gc.var.brainstorming_approval_mode` when present; otherwise default to
`autonomous`.

In `interactive` mode, use the passive wait + mail human gate pattern. This is
not a timeout-driven task.

1. Before waiting, update workflow root metadata with:
   - `gc.build.spec_gate_status=waiting-human`
   - `gc.build.spec_gate_bead_id=<this bead id>`
   - `gc.build.spec_gate_artifact_path=<approval-summary path>`
   - preserve any existing `gc.build.spec_gate_mail_sent=true`
2. Park the current session so idle handling does not recycle it while the
   human decides:
   ```bash
   SESSION_TARGET="${GC_SESSION_ID:-${GC_SESSION_NAME:-}}"
   SESSION_ATTACH="${GC_SESSION_NAME:-$SESSION_TARGET}"
   WAIT_NOTE="Waiting for human approval of Superpowers written spec on bead $GC_BEAD_ID."
   if [ -n "$SESSION_ATTACH" ]; then
     WAIT_NOTE="$WAIT_NOTE Resume with: gc session attach $SESSION_ATTACH"
   fi
   if [ -n "$SESSION_TARGET" ] && ! gc wait list --session "$SESSION_TARGET" | grep -Fq "$WAIT_NOTE"; then
     gc session wait "$SESSION_TARGET" \
       --sleep \
       --on-beads "$GC_BEAD_ID" \
       --note "$WAIT_NOTE"
   fi
   ```
3. If workflow root metadata does not already have
   `gc.build.spec_gate_mail_sent=true`, send exactly one mail with
   `gc mail send human ...`. Include the written spec path, spec review report
   path, approval summary path, workflow root id, this bead id, and the
   requested response options: approve, request changes, or reject. After
   sending, update workflow root metadata with
   `gc.build.spec_gate_mail_sent=true` and `gc.build.spec_gate_mail_to=human`.
4. Wait for explicit human feedback from the active session or mail thread. If
   the session idles, detaches, or
   restarts before the human responds, do not close this bead. A resumed worker
   must read the gate metadata and continue waiting from this gate.
5. Use `done` only after explicit approval by setting
   `design_review.verdict=done`. If the human requests changes, record the
   requested revisions in the approval summary and close with
   `design_review.verdict=iterate`. Close fail only for explicit rejection or
   abort, not for silence.

In `autonomous` mode, approve only when the spec review has no required issues,
the apply pass made no required changes in this attempt, and the requirements
artifact has no unresolved questions. Otherwise close with
`design_review.verdict=iterate`.

When iterating, write a concise spec revision summary that the next
`write-requirements-spec` attempt can apply directly. The summary must name the
specific requirements sections, ambiguity, contradiction, or scope issue that
caused the loopback.

On approval, mark the requirements artifact approved and update workflow root
metadata with `gc.build.requirements_status=approved`,
`gc.build.requirements_path=<absolute path>`,
`gc.build.spec_gate_status=approved`, and a short requirements summary. For a
human-requested iteration, update `gc.build.spec_gate_status=revision_requested`.

Close with `gc.outcome=pass`, `design_review.verdict=done|iterate`,
`design_review.output_path=<approval-summary path>`, and
`gc.continuation_group=superpowers-spec-fixes`.

Do not invoke provider-native subagents or upstream plugin runtime commands.
This Gas City lane owns the approval decision.
