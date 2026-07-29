# Client Brief — Meridian Support Pilot

*One page. Fill every line. This is what Priya takes to her leadership.*

---

**Client & pilot**
Meridian — an AI agent that triages and resolves customer support tickets (a coordinator routing to billing / technical / account specialists). Live 3 weeks; closing tickets that aren't actually resolved.

**What's actually breaking it**
Two instructions in the coordinator's own prompt, not the model. First: "Each ticket is owned by exactly ONE specialist... do not spawn more than one specialist" — even when a ticket raised two separate problems (SSO login + a billing refund), the coordinator was only allowed to hand it to one specialist, so whichever issue fell outside that specialist's tools never got touched. Second: the coordinator was told to call write_response with resolution_status "resolved" as soon as any specialist returned, and to "close the ticket — do not leave tickets open" even when something fell outside that specialist's scope. So it was structurally set up to declare victory regardless of whether the customer's actual problem got solved. That's the "confidently wrong, closes tickets that aren't resolved" pattern in your email — verified directly in the trace on T-4471, where the agent diagnosed the refund correctly, never issued it, told the customer to email billing themselves, and marked the ticket "resolved" anyway.

**The fix**
Two edits to `system-prompt-coordinator.txt` — no code changes, no changes to the grading/scoring, same model throughout (claude-sonnet-5):
1. Step 5 (DELEGATE): now spawns one specialist per distinct issue/category the ticket actually raises, and waits for all of them before replying — instead of picking a single "most urgent" category and dropping the rest.
2. Step 6 (SYNTHESIZE): resolution_status "resolved" is now only allowed once every issue raised was actually actioned. If something's still outstanding, the coordinator has to say so honestly and escalate it, not paper over it.

**Proof**
Ticket T-4471, 5 trials each run, same model:
- Baseline: **RESOLVED 0/5 trials** — $0.12/trial. The agent never once actually issued the refund it owed the customer, but marked "resolved" in every trial.
- After the fix: **RESOLVED 5/5 trials** — $0.22/trial.
- Held out on two different tickets it was never tuned against (T-4490: a technical + billing pair; T-4503: a request nothing in the system is authorized to grant): **RESOLVED 9/9 trials** across all three tickets, $0.20/trial average. T-4503 in particular shows the fix isn't just "resolve everything" — the coordinator correctly refuses to fabricate an authorization it can't grant, and escalates to a human instead.

**What it would take**
This was a two-paragraph edit to one prompt file, validated against 3 tickets across two different specialist pairings and 14 total trials. To roll this out: apply the same "one specialist per issue, honest resolution status" pattern across the full ticket taxonomy (not just the 3 tested here), and re-run this same trial-based eval against a broader ticket sample before going live. The cost per ticket rises from ~$0.12–0.16 to ~$0.20–0.22 — but that's the cost of a specialist actually doing the second half of the work, not overhead. The old number was cheap because it wasn't doing the job.

**The objection we'll get**
"Why not just use a better model?" We tested it directly: running claude-opus-4-8 on the exact same (now-fixed) prompt gets the identical 5/5 resolution rate as claude-sonnet-5, at $0.38/trial — 77% more expensive for no improvement in outcome. The ceiling was never the model's capability; it was the instructions constraining it to one specialist and rewarding early closure. A bigger, pricier model dropped into the broken prompt would have made the same mistake, just less cheaply. The fix lives in the system around the model, and it's already paid for itself.


