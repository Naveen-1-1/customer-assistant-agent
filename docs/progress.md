# Curated test cases: progress

CS 6983 · Group 5 · branch `test-cases` · updated 2026-11-14 · due **Mon 2026-11-16, 11:59 pm**

## Setup

- **Agent:** τ²-bench's reference agent (its prompt + the retail policy, all 16 tools) on
  Laguna XS 2.1 (NVIDIA NIM). Fresh copy of the store for every run.
- **Customer:** Claude, playing the task's τ²-bench scenario exactly through the UI
  (`python -m agent.ui.backend.server`). Logs are labelled `claude-customer`. The first rounds
  used a Laguna-played customer, which broke its script too often.
- **Grading:** `python -m agent.evaluation.grader <run dir>`, 39 checks read from the log plus
  the store. Every failing transcript is also read by hand; a failure counts only if the agent
  caused it, in at least 2 of 3 valid runs.

## Finalized

| Case | Role | Valid runs | Breakdown |
|---|---|---|---|
| **99** | failing | 🔴✅🟠 (2 of 3 agent-caused) | Says "I'll cancel just the skateboard", and the call cancels the whole order ($1,058.79). Once also picked the wrong camera after quoting a refund for the right one. |
| **19** | failing | 3 of 3 agent-caused | Promises the return *and* the exchange in one order, where only one is allowed; the second is refused after the first ran, so the customer never chooses. Once quoted wrong "cheapest" prices ($13.77 vs $41.64 saved). |
| **67** | failing | 3 of 3 agent-caused (Claude as customer) | **Skips identity verification.** The customer says "my user id is noah_ito_3850", and the agent calls `get_user_details` on it straight away, then shows the order's items, total, card and status to someone it never verified. The policy (line 10) requires email or name + zip *"even when the user already provides the user id"*. The end state and the $829.43 are right, so only the `unauthenticated_calls` check shows it. |
| 15, 16, 18, 24, 43 | base suite | ✅✅✅ each | Reliable passes, covering 18 of 19 basic functions (not "several items in one change"). Runs once per fix round to catch regressions. |

## Tested, not finalized

| Case | Runs | Why not |
|---|---|---|
| 28 | 2 of 3 valid agent-caused (3 of 6 runs excluded) | Same breakdown as 99, so not unique. Kept as evidence that the pattern recurs. |
| 74 | ✅🔴✅ | Its only failure was the simulated customer picking the wrong order. The agent only slipped harmlessly (`exchange` on a pending order, refused by the store). |
| 2 | ✅✅🟠 | Wrong t-shirt count in 1 of 3 runs, below the bar. Candidate for the wrong-facts case, to re-test with Claude as the customer. |
| 97 | 3 simulated runs excluded, 1 Claude run ✅ | Every simulated failure was the customer inventing the address or repeating itself. With a faithful customer, the agent got it right. |
| 89 | ✅✅✅ | Passed. Once it claimed an unavailable $199 keyboard, but the store blocked the exchange. |
| 50 | ✅✅✅ (Claude as customer) | "Undo my cancellation" (impossible), with an insistent customer: each time it said honestly it can't, then transferred with a good summary. Small slips: offered to "help place a new order" with no tool for that (3 of 3), and once cited a policy rule that doesn't exist. |

## Fix layers per case (design, not built: to be discussed first)

| Case | Tools | Workflow | Governance | Interface | Difficulty |
|---|---|---|---|---|---|
| 99 | `preview_change` | — | write gate | confirmation card from the preview | medium |
| 19 | `preview_change` | plan → check → confirm → run | write gate, no partial runs of an infeasible plan | choice card | hard |
| 67 | — | — | auth gate: no lookup of a user's data until a sign-in tool has succeeded | — | easy |

## Next

1. 5 valid runs per final case (99, 19, 67) and per base case.
2. Submission packaging:
   - `trajectory.json`, `reward.json` and `config.json` per run, in a tracked folder (`var/` is gitignored);
   - one document per case;
   - the shared metrics and survey;
   - the teammate videos.
