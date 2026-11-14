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
| **37** | failing | 3 of 3 agent-caused (Claude as customer) | **Wrong facts drive an irreversible change.** Asked to switch every item to its cheapest option to get under $1,150, it quoted unavailable variants as the cheapest, got refused, then switched items to **more expensive** variants: +$4.62 in c1; +$11.42 and +$4.62 in c2. It gave a wrong total each time ($1,127.47 approved vs $1,135.47 charged). In c3 it said the cheapest total is $1,154.97 ("still over"; the truth is $1,130.85), so the customer had the **whole order cancelled**. It also implied a split payment was possible and offered to "remove" an item, neither of which is allowed. |
| **31** | failing | 2 of 2 agent-caused, harmful (Claude as customer) | **Uses a tool for something it isn't meant for.** The customer says they *lost* the tablet and asks for a refund or reorder (a long shot). Both runs offered a *return*, filed it ($951.21), and told the customer to ship the tablet back. Run 2 even wrote "(though you mentioned it's lost)". It also invented refund mechanics: "$44 now, $907.21 in 5–7 days" (run 1); "you may need documentation" (run 2). Because it claimed a refund was possible, the customer's fallback (cancel the charger) never happened. |
| 15, 16, 18, 24, 43 | base suite | ✅✅✅ each | Reliable passes, covering 18 of 19 basic functions (not "several items in one change"). Runs once per fix round to catch regressions. |

## Tested, not finalized

| Case | Runs | Why not |
|---|---|---|
| 28 | 2 of 3 valid agent-caused (3 of 6 runs excluded) | Same breakdown as 99, so not unique. Kept as evidence that the pattern recurs. |
| 74 | ✅🔴✅ | Its only failure was the simulated customer picking the wrong order. The agent only slipped harmlessly (`exchange` on a pending order, refused by the store). |
| 2 | ✅✅🟠 | Wrong t-shirt count in 1 of 3 runs, below the bar. Candidate for the wrong-facts case, to re-test with Claude as the customer. |
| 97 | 3 simulated runs excluded, 1 Claude run ✅ | Every simulated failure was the customer inventing the address or repeating itself. With a faithful customer, the agent got it right. |
| 89 | ✅✅✅ | Passed. Once it claimed an unavailable $199 keyboard, but the store blocked the exchange. |
| 21 | ✅✅ (Claude as customer; run 3 skipped, since it couldn't reach 2 of 3) | A second change added at final confirmation, on a change that works only once. Both runs merged it into one call and gave the right $44.08 balance. Run 1 first used the product id as the item id (refused by the store), then corrected itself. No "is that all?" reminder in either run. |
| 22 | ✅✅ (Claude as customer) | Change the default address and all changeable order addresses, then revert only the default. Both runs changed the one pending order and the profile, then restored the original Denver address exactly. Run 1 first said order addresses can't be changed, and corrected itself when pushed. |
| 55 | ✅✅ (Claude as customer) | A distressed customer cancels 2 pending orders and returns 2 delivered ones. Both runs did all four changes with confirmations and no hand-off, so the "abandons a doable task" idea didn't show. Run 1 gave a wrong return total ($1,176.44 vs $1,423.04), which is 37's root cause. |
| 69 | ✅✅ (Claude as customer) | "Return the laptop I just received", but its order is still pending. Both runs checked the record, offered to cancel instead, mapped "found a better deal" to "no longer needed" with the customer's agreement, and stated the refund timing correctly. |
| 40 | not run | "Can my $60 gift card pay for a $321.18 order?": the likely failure (a promise the gift-card rule doesn't allow) repeats 19. |
| 105, 64 | not run | 105: τ²-bench's ground truth contradicts itself (its expected exchange is refused by the tools, yet its assertion says "exchange both"). 64: repeats 37's root cause (best variant under a price constraint). |
| 82 | ✅✅ end state (Claude as customer) | The slips repeat captured root causes, so it's not unique. Both runs proposed a credit-card refund that a gift-card order doesn't allow, and learned only when the store refused (19's "promises not checked against the rules"). Run 2 merged two orders into one ("both tablets" in #W9571698); the customer approved returning "all 5 items, both tablets", 4 were returned, and the agent never said the other tablet wasn't (37's "wrong facts"). |
| 101 | ✅✅ (Claude as customer) | Two watches in one order (change only the silicone one), plus a New York address taken from another order, plus an air purifier in a third order. Both runs changed the right watch, did the address first, and found the purifier's order (run 1 only after looking in the wrong order). Slips: run 2 asked the customer to type an address it had already looked up; no "is that all?" reminder. |
| 13 | ✅✅ end state (Claude as customer) | Not strong: a near-miss with no harm. Asked to return "everything not related to gaming", both runs put the mechanical keyboard on the return list as "non-gaming", but showed the list before acting, and the customer's correction kept it out. Its other slips (a PayPal refund promised for a credit-card order) repeat 19. |
| 50 | ✅✅✅ (Claude as customer) | "Undo my cancellation" (impossible), with an insistent customer: each time it said honestly it can't, then transferred with a good summary. Small slips: offered to "help place a new order" with no tool for that (3 of 3), and once cited a policy rule that doesn't exist. |

## Fix layers per case (design, not built: to be discussed first)

| Case | Tools | Workflow | Governance | Interface | Difficulty |
|---|---|---|---|---|---|
| 99 | `preview_change` | — | write gate | confirmation card from the preview | medium |
| 19 | `preview_change` | plan → check → confirm → run | write gate, no partial runs of an infeasible plan | choice card | hard |
| 67 | — | — | auth gate: no lookup of a user's data until a sign-in tool has succeeded | — | easy |
| 37 | `find_variants(available_only, sort_by_price)`, `preview_change` for the new total | — | write gate | confirmation card with the preview's per-item prices and total | medium |
| 31 | — | — | a rule that a return needs the item to be sent back; lost or stolen items go to a human | return card states "you'll need to send the item back", and the customer confirms they have it | medium |
## Next

1. Keep adding unique cases; pick the final 3 later. Then 5 valid runs per final case and per base case.
2. Submission packaging:
   - `trajectory.json`, `reward.json` and `config.json` per run, in a tracked folder (`var/` is gitignored);
   - one document per case;
   - the shared metrics and survey;
   - the teammate videos.
