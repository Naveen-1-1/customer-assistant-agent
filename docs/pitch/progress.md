# Pilot progress: baseline vs. workflow

_Updated 2026-11-02 10:43 by `python -m customer_workflow_agent.evalkit.progress`._

Baseline: plain tool-calling agent on Laguna XS 2.1, 3 runs per task. Workflow: this repo's agent on Nemotron 3.5 Lightning, latest iteration with fixes. Customer simulated by Laguna XS 2.1 from the τ²-bench scenario.

✅ correct end state · 🔴 harmful (changed an order/thing never asked about) · 🟠 incomplete or wrong detail · 🟡 safe failure (nothing changed) · ⚪ excluded (simulator ended early or server error) · counts are correct/valid runs. A failure goes in the pitch only after its transcript shows the agent, not the simulated customer, caused it.

Workflow column: the latest fix round in bold, earlier rounds after it (each round includes the fixes made before it).

| S.no | Task type (generic) | Task (τ²-bench id) | Baseline | Workflow | Status |
|---|---|---|---|---|---|
| 1 | Multi-item exchange with fallback | Exchange keyboard + thermostat, fallback spec (0) | **2/2** ✅⚪✅ | **2/2** ✅✅ (round 3) · earlier: r1 🟡 → r2 ✅ | ⏹ stopped: baseline handles it (2/2 valid runs correct): no contrast |
| 2 | Multi-item exchange with fallback | Exchange bike + puzzle with preferences (99) | **0/3** 🔴🔴🔴 | **2/2** ✅✅⚪ (round 18) · earlier: r9 ✅✅ | ▶ active |
| 3 | Multi-item exchange with fallback | Worn boots: same spec, else fallback spec (107) | **2/3** 🟠✅✅ | ⏳ not run yet | ⏹ stopped: baseline 2/3 correct: weak contrast; budget moved to stronger candidates |
| 4 | Combined edits to a pending order | Redirect order home + change two items (71) | **1/3** ✅🟠🟠 | **0/2** 🔴🟠 (round 6) · earlier: r4 🟠🟠 | ⏹ stopped: after 2 fix rounds the address + item change works, but 'cancel this and start over' at a popup is read as an order cancellation (classification); twin task 72 kept |
| 5 | Combined edits to a pending order | Redirect order home + change two items (v2) (72) | **1/2** ✅⚪🔴 | **0/2** 🟠🔴 (round 14) · earlier: r4 🔴✅ → r6 ✅🟠 → r11 ✅⚪ → r13 ⚪⚪ | ⏹ stopped: workflow failed 3 rounds: the customer's mid-flow 'only the backpack' is lost, and a typed No re-shows the same popup (not a quick fix) |
| 6 | Item change with payment choice | Resize pending boots, PayPal for difference (15) | **3/3** ✅✅✅ | ⏳ not run yet | ⏹ stopped: baseline 3/3 correct: no failure to show |
| 7 | Item change with payment choice | Modify pending items + return, card payment (100) | **0/2** ⚪🟠🟠 | **0/2** 🟡🟡 (round 19) | ⏹ stopped: workflow 0/2: the simulated customer refused the PayPal-only return refund again and again (its card preference is for the pending-order change), and the workflow never reached the item change; the baseline transcripts are kept as notes |
| 8 | Conditional cancellation | Two pending orders: cancel one, re-address other (59) | **0/0** ⚪⚪⚪ | **0/0** ⚪⚪ (round 3) · earlier: r2 ⚪ | ⏹ stopped: orders carry no dates; the simulated customer guessed which order was older |
| 9 | Conditional cancellation | Laptop upgrade + cancel a forgotten order (74) | **0/3** 🟠🔴🟠 | **2/2** ⚪✅✅ (round 18) · earlier: r4 ✅⚪ → r10 🟡✅ | ▶ active |
| 10 | Conditional cancellation | Cancel for the right reason (partial not allowed) (76) | **1/3** 🟠✅⚪🟠 | **0/2** 🟠🟠 (round 7) · earlier: r4 🟠⚪ | ⏹ stopped: workflow didn't get a clean run in 2 rounds (cancellation reasons, runs out of turns) |
| 11 | Conditional cancellation | Cancel every order holding listed items (81) | **2/3** ✅🟠✅ | **0/2** 🟠🟠 (round 8) | ⏹ stopped: workflow cancels one of the two orders; finding every order holding listed items isn't supported (not a quick fix) |
| 12 | Return under refund rules | Return pricier tablet; refund-method pressure (82) | **1/3** 🟠✅🔴 | **0/1** ⚪🔴 (round 7) | ⏹ stopped: the pricier tablet is in another order; the workflow queues the customer's 'what does it cost?' instead of answering mid-request (not a quick fix) |
| 13 | Return under refund rules | Return skateboards; adds items at confirmation (92) | ⏳ not run yet | ⏳ not run yet | ⏹ stopped: added then withdrawn: harder than needed |
| 14 | Product question + action | Count t-shirt options + return three items (2) | **1/2** ⚪✅🟡 | **2/2** ✅✅ (round 6) · earlier: r1 ⚪ → r2 ✅ → r3 ✅⚪ | ▶ active |
| 15 | Product question + action | Count t-shirt options + change pending t-shirt (3) | **2/3** 🔴✅✅ | **0/1** 🔴⚪ (round 5) | ⏹ stopped: workflow applies 'all t-shirts' and ignores the 'small' filter (changed an XXL one); not a quick fix |
| 16 | Product question + action | Count t-shirt options + change all t-shirts (4) | **2/2** ✅✅⚪ | **0/2** 🟠🟡 (round 10) · earlier: r5 ⚪✅ | ⏹ stopped: workflow 1 correct of 3 valid runs over 2 rounds (one popup per order; model output errors) |
| 17 | Request with unclear references | Vacuum exchange with a mistyped order id (45) | **2/3** 🟡✅✅ | ⏳ not run yet | ⏹ stopped: the baseline's only failure was a safe one: weak evidence |
| 18 | Request with unclear references | Swap bottle to match another order's bottle (79) | **0/3** 🟡🟠🔴 | **0/2** 🟡🟠 (round 5) | ⏹ stopped: stretch task; workflow 🟡🟠 in its round |
| 19 | Request with unclear references | Laptop exchange; which laptop is unclear (94) | ⏳ not run yet | ⏳ not run yet | ⏹ stopped: added then withdrawn: harder than needed |
| 20 | Return under refund rules | Return a camera; order number uncertain, insists on card (51) | **2/3** ✅✅🟡 | **2/2** ✅✅ (round 11) | ⏹ stopped: baseline 2/3 correct and its only failure was a safe one: weak evidence |
| 21 | Address change | Update default address after a move (address in a recent order) (39) | **0/3** 🟠🟠🟡 | **0/2** 🟡🟠 (round 11) | ⏹ stopped: the baseline's wrong addresses came from the simulated customer, which invented one (its script says it's in a recent order): no agent-caused failure |
| 22 | Change of mind at confirmation | Exchange bottle + lamp; at confirmation, lamp only (9) | **3/3** ✅✅✅ | **1/2** ✅🟠 (round 12) | ⏹ stopped: baseline handles it (2/2 correct): no contrast to show |
| 23 | Change of mind at confirmation | Return a chair; at confirmation, exchange it instead (18) | **3/3** ✅✅✅ | **0/1** 🔴⚪ (round 12) | ⏹ stopped: baseline handles it (3/3 correct): no contrast; the simulated customer often skips its scripted rethink at the popup |
| 24 | Change of mind at confirmation | Cancel the grill; at confirmation, keep it (24) | **3/3** ✅✅✅ | **1/1** ⚪✅ (round 12) | ⏹ stopped: baseline handles it (2/2 correct): no contrast |
| 25 | Conditional cancellation | Cancel all pending orders + return only the watch (16) | **1/1** ✅ | **0/2** 🟠🟡 (round 12) | ⏹ stopped: workflow never finished (×2): 'cancel all my pending orders' made the watch return list every item, and a typed No re-shows the same popup; baseline got it right once |
| 26 | Multi-item exchange with fallback | Exchange bike + puzzle; cancel an order (99's twin) (98) | **1/3** 🔴🟡✅ | **0/2** 🟠🔴 (round 15) | ⏹ stopped: workflow 0/2: exchange loops (a camera from another order; 'larger frame size' kept after the customer answered), then the skateboard looked up in the wrong order; not small fixes. Its baseline transcripts are kept as notes |
| 27 | Partial cancellation request | Cancel some items if possible, else re-address order (34) | **1/3** 🔴🔴✅ | **0/1** 🟡⚪⚪ (round 18) · earlier: r15 ✅ → r17 🟡🟡 | ▶ active |
| 28 | Partial cancellation request | Cancel some items if possible, else change address (33) | **2/2** ⚪✅✅ | ⏳ not run yet | ⏹ stopped: needs the default address set from an order's address (the workflow offers only the current default); the baseline's wrong address came from the simulated customer |
| 29 | Partial cancellation request | If not shipped, cancel only the air purifier (57) | **3/3** ✅✅✅ | ⏳ not run yet | ⏹ stopped: baseline handles it (2/2 correct): no contrast |
| 30 | Product/order question + action | Where did my order ship + tracking; change address (43) | **3/3** ✅✅✅ | ⏳ not run yet | ⏹ stopped: baseline handles it (2/2 correct): no contrast |
| 31 | Cancel/return everything | Cancel pending orders, then return all delivered items (55) | **1/2** ⚪🟡✅ | **0/1** 🟠 (round 17) · earlier: r16 🟡⚪ | ⏹ stopped: the simulated customer keeps items and picks 'ordered by mistake' against its script (both agents), so the end state can't be judged; the baseline's unrequested transfer is kept as a note |
| 32 | Several requests in one chat | Return 3 items, re-address + recolor an order, tracking (103) | **1/1** ✅⚪⚪ | **1/2** 🔴✅ (round 16) | ⏹ stopped: baseline 1/1 correct once the simulator-invented addresses are excluded (no contrast); the workflow once created a cancel from the customer's 'cancel' that meant return |
| 33 | Exchange with a set payment | Exchange a t-shirt, pay the difference by gift card (80) | **2/2** ✅⚪✅ | ⏳ not run yet | ⏹ stopped: baseline handles it (2/2 correct): no contrast |

## Notes

- **Wrong facts told (tasks 2, 3, 4; audited answer by answer):** asked how many t-shirt options are available (10 of 12 in stock), the baseline was wrong in 4 of 8 answers: "14 variants, 12 available" (2-t2), "14 variants" (4-t3), all 12 called available (4-t1), and "10 available" over a list of only 8 (2-t3). The other 4 said 12 total / 10 in stock. The workflow counts in code: "10 of 12 options are available right now".
- **Task 59 — needs review (simulator-driven):** orders carry no dates, and in every run (both agents) the simulated customer itself declared #W2702727 the older order and asked to cancel it; the scenario implies #W8268610. Not headline evidence unless a transcript shows the agent ignoring the contradiction (cancel #W2702727 *and* re-address it).
- **Tasks 71, 72 (baseline):** address changed but the item change dropped (×2); once the order was cancelled instead (72).
- **Task 3:** changed the t-shirt in the wrong order (that order can't be changed again). **Task 4:** changed one of the two orders and silently skipped the other.
- **Task 76 (baseline, transcript-checked):** what the customer approved ≠ what ran: the summary said "Reason: Item unavailable", the call recorded "no longer needed"; and the order the customer said was "ordered by mistake" was filed as "no longer needed". One other failing run was the simulator's own wrong reason (excluded from the claim).
- **Task 72 (workflow, round 4):** "pay the difference with PayPal" was taken as a separate change-the-order's-payment request; the popup stated it exactly and the customer still said yes. Limits of a popup: it only protects a customer who reads it.
- **Task 98 (baseline, transcript-checked):** 2 of 3 runs invented a rule: "a road bike and mountain bike are different product types, so I cannot exchange them" — the large mountain bike is an option of the same Bicycle product (run 3 offered it). In run 1 the customer, talked out of the exchange, ended with a return; the agent then exchanged a puzzle in an order the customer never mentioned (same item id) and never exchanged the camera.
- **Task 55 (baseline run 2, transcript-checked):** the customer asked "Can you help me process all of this?" and the agent transferred to a human unasked ("possibly due to memory issues or unauthorized purchases"); none of the 4 in-scope requests was done.
- **Task 100 (baseline, transcript-checked):** in both valid runs the agent changed options the customer wanted kept: "the exact same luggage set but red" became a 4-piece hardshell (theirs: 2-piece softshell, available in red); a skateboard asked for as 34 inch, custom design became plastic instead of bamboo (the bamboo one exists). Run 1 excluded: the simulated customer asked for a human.
- **Workflow fixes so far (each with a test):** zip picked from context; payment named in words ("card ending 2478"); order list shows items; filler option values ignored; items must be named by the customer (no invented items); every email in the message is tried; an item is found by name when the model mixes in the wanted options; naming items isn't "return everything"; asked to cancel some items of a pending order, it says only whole orders cancel (before round 18).
- **Task 34 (workflow, round 18, transcript-checked):** the partial-cancel fix works (it says only whole orders cancel; the customer picks the address change), but the address step fails next: a typed "use your default address" isn't applied (only the button is), a zip or "[Street address to be provided]" is taken as the street, and once the model-worded question said "I've updated your address" when nothing was written — the baseline's says-X-does-Y, in the one place the workflow lets the model write.
- **Harness fixes:** the agent may act on the customer's last message ("yes ###STOP###"); a typed popup reply counts as yes only if it starts as one. Runs whose popup answer the older reader got wrong are re-checked automatically and shown ⚪ (3 so far).

## Runs excluded after transcript review (simulator off its script)

- `59`: orders carry no dates; the simulated customer guessed which order was older
- `pilot-baseline-2/76__baseline__t2`: the simulated customer gave the wrong cancel reason
- `wf-iter4/76__workflow__t2`: the simulated customer took a 31-inch board; its script says cancel when the exact board is unavailable
- `wf-iter5/3__workflow__t2`: the simulated customer asked to change an XXL crew-neck t-shirt; its script says only the small ones, same size
- `pilot-baseline/0__baseline__t2`: the simulated customer chose the white-backlight keyboard; its script says no backlight
- `pilot-baseline/72__baseline__t2`: the simulated customer put off the backpack change itself
- `wf-iter12/18__workflow__t2`: the simulated customer confirmed the return outright; its script says rethink at confirmation and exchange instead
- `wf-iter12/24__workflow__t1`: the simulated customer said 'Yes, please go ahead and cancel it'; its script says regret at confirmation and keep the grill
- `wf-iter11/72__workflow__t2`: the simulated customer asked for and confirmed the lamp change too; its script says change only the backpack
- `pilot-baseline/4__baseline__t3`: the simulated customer chose to keep the second order unchanged; its script says change all t-shirts
- `wf-iter5/4__workflow__t1`: the simulated customer left after the first order; its script says change all t-shirts
- `wf-iter16/55__workflow__t2`: infra: the sign-in model call timed out on the API (15 s limit then), and the simulated customer then invented a zip not in its script
- `pilot-baseline-6/33__baseline__t1`: the simulated customer invented the Seattle address; its script says don't reveal it (it's in the order)
- `pilot-baseline-7/55__baseline__t1`: the simulated customer decided on its own to keep the air purifier and coffee maker and chose 'ordered by mistake'; its script says return everything
- `pilot-baseline-7/103__baseline__t3`: the simulated customer invented its 'default' address (123 Main Street); the agent used it although the profile it had read says 921 Park Avenue
- `pilot-baseline-7/80__baseline__t2`: the simulated customer (scripted to confuse) disowned a backpack in the order and asked for a human; the agent's wrong refund ($8.99, right: $7.99) is kept as a note
- `wf-iter18/34__workflow__t3`: after declining three address popups the simulated customer chose to cancel the whole order (its script: just change the address) and confirmed a popup listing every item; the workflow's address bug that confused it is in the notes
- `pilot-baseline-7/103__baseline__t2`: the simulated customer invented its 'default' address (1234 Michigan Ave), as in run 3
- `wf-iter18/74__workflow__t1`: the simulated customer asked to cancel the laptop order ('I no longer need the laptop'; its script: upgrade it) and confirmed a popup showing exactly that
- `pilot-baseline-2/100__baseline__t1`: the simulated customer said it didn't recognise its orders and asked for a human
