# Case 37 protocol

**Task:** τ²-bench retail task 37 (`data/tasks.json`, id `"37"`). It's the same in both modes.

**Goal:** the customer's card has only $1,150 left, and their just-placed order `#W9348897`
(pending) costs $1,166.98. They ask, in order: split the payment (not allowed, policy line 102);
cancel just the most expensive item (not possible; it's the $481.50 action camera); switch every
item to its cheapest *available* option to get to $1,150 or less (possible: $1,130.85); and only
if that fails, cancel the whole order.

**Expected end state:** one item change on `#W9348897`, swapping the camera, desk lamp and t-shirt
for their cheapest available variants. The umbrella and backpack are already the cheapest
available, so they stay. The new total is $1,130.85, with the refund to `credit_card_8853416`.
The agent must say the camera is the most expensive item, at $481.50.

## Persona / script (the simulated customer's scenario, verbatim)

- **Reason for call:** You just placed an order but you realize that your card has only $1150
  credit left, but the order total is more than $1160. You wonder if the agent can help split the
  payment with another card. If that is not possible, you ask the agent what the most expensive
  item and its price, and whether you can just cancel that item. If that is not possible, you ask
  if you can switch all items to their cheapest options and bring the cost down to $1150. If that
  is possible, confirm and ask the agent to do it. If that is not possible, you ask the agent to
  just cancel the order so that you can order again.
- **Known info:** Your name is Daiki Sanchez, and you live in 46236, your email is
  daikisanchez1479@example.com.
- **Unknown info:** (none)
- **Task instructions:** You are a bit anxious and want to get things done quickly, and you speak
  very briefly. Do not end the conversation until your changes have been made.

The customer has only one card on file, and the email doesn't match any account, so the agent
has to fall back to name + zip. The agent opens with "Hi! How can I help you today?".

## Simulated mode

```bash
.venv/bin/python -m agent.evaluation.run_tasks --cases 37 --trials 5 --out test_cases \
  --model poolside/laguna-xs-2.1 --user-model poolside/laguna-xs-2.1
```

A run is **valid** if there was no infrastructure error and the simulated customer followed its
script: it didn't invent details, and it didn't skip a step or cancel before the switch was ruled
out. The customer doesn't check the agent's arithmetic; that's part of the persona. Each run writes
`test_cases/case-37/runs/run-<n>/` and prints its verdict. Read each `trajectory.json`; to replace
an invalid run, delete its folder and run again with `--trials 1` (it takes the free number).

## User-testing mode

1. Start the page: `.venv/bin/python -m agent.ui.backend.server`, then open http://127.0.0.1:8000.
2. Choose task **37**, click **Start session**, and keep "Show tool calls" off.
3. The participant reads the role card and plays the customer in their own words, following the
   order of the asks. They may check the numbers if they want to; record whether they did.
   Suggested first message: "Hi. I just placed an order but my card only has $1150 left and the
   order is over $1160. Can you split the payment with another card?"
4. The session ends when the participant says they're done; the facilitator clicks **End session**.
5. The page shows the run folder it wrote (`var/eval/user-testing-<date>/case-37/runs/run-<n>/`).
   Run the survey and interview in [../survey.md](../survey.md) and save them to that folder.
