# Reply to Priya — ready to send

**To:** Priya Anand — VP, Customer Operations, Meridian
**Subject:** Re: Honestly not sure this is going to work — it's fixable, and here's the proof

---

Hi Priya,

Straight answer first: **this is fixable, and it wasn't the model.**

**What was actually wrong**
We pulled the trace on T-4471 and found the coordinator was working from two instructions that guaranteed the behavior you saw. First, it was told to hand every ticket to exactly one specialist — so on a ticket like T-4471, which raised both an SSO login problem and a billing refund, it picked one and simply never acted on the other. Second, it was told to mark every ticket "resolved" once that one specialist came back, even when it explicitly knew part of the request was left untouched. On T-4471, that meant it correctly diagnosed the refund the customer was owed, never issued it, told them to go email billing separately, and closed the ticket as resolved anyway. That's the exact pattern that landed on your desk — and it's a rule in the prompt, not a limitation of the model.

**What we changed**
Two edits to the coordinator's instructions — no code changes, no changes to how we grade a ticket as resolved, same model the whole way:
1. It now delegates to a specialist for *every* distinct issue a ticket raises, not just the single most urgent one.
2. It's only allowed to mark a ticket "resolved" once every issue raised was actually acted on — not just diagnosed or explained. If something's still outstanding, it says so and escalates it honestly instead of closing the loop early.

**Proof**
Same ticket, same model, 5 runs each:
- Before: **0 out of 5** runs actually resolved the customer's issue, at ~$0.12/run — it was marking "resolved" every time regardless.
- After: **5 out of 5.**
- We then tested it against two tickets it had never seen tuned for — a different specialist pairing, and one where the "right" answer is to escalate to a human rather than resolve it — and it went **9 for 9** across all three, ~$0.20/run.

**On "did we bet on the wrong model"**
We tested that directly, so you don't have to take our word for it: running the exact same fixed instructions on a bigger, pricier model (Opus) produced the identical 5-out-of-5 result, at 77% higher cost per ticket. There was nothing left for a bigger model to fix — the ceiling was the instructions, not the model's capability.

**What it would take to roll out**
This was a two-paragraph prompt edit, validated across 3 tickets and 14 trials so far. Before going live broadly, we'd want to run the same eval across your full ticket taxonomy to confirm it holds up outside this sample. Per-ticket cost rises modestly (~$0.12–0.16 → ~$0.20–0.22) — that's the cost of the second issue actually getting handled, not overhead we added.

Happy to walk through the traces live if useful. This is a fixable pilot, not a failed bet.

— [Your name]
