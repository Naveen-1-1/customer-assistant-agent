# Case 19 protocol

**Task:** τ²-bench retail task 19 (`data/tasks.json`, id `"19"`). It's the same in both modes.

**Goal:** the customer wants to return a water bottle *and* exchange a pet bed and an office chair
for their cheapest versions, all in one delivered order. The store allows only one of the two
(a return or an exchange moves the order out of "delivered"), so the right outcome is that the
agent says so, tells the customer what each option saves, and lets the customer choose. This
customer then picks the return ($54.04 back, versus $41.64 for the exchanges).

**Expected end state:** one return of the water bottle on order `#W2890441`, refunded to the
original card (`credit_card_1061405`). The agent must say both amounts: $54.04 and $41.64.

## Persona / script (the simulated customer's scenario, verbatim)

- **Reason for call:** You want to return the water bottle, and exchange the pet bed and office
  chair to the cheapest version. Mention the two things together and you want to get both done.
  If and only if you can only do one of the two things, you prefer to do whatever saves you most
  money. Ask the agent how much money you can save in both options.
- **Known info:** You are Mei Davis in zipcode 80217.
- **Unknown info:** You do not remember your email address.
- **Task instructions:** You are in debt and sad today, but very brief.

The simulated customer gets these with τ²-bench's user-simulation guidelines
(`agent/evaluation/simulated_customer.py`). The agent opens with "Hi! How can I help you today?".
The customer's first message isn't fixed; it writes it from the scenario.

## Simulated mode

```bash
.venv/bin/python -m agent.evaluation.run_tasks --cases 19 --trials 5 --out test_cases \
  --model poolside/laguna-xs-2.1 --user-model poolside/laguna-xs-2.1
```

A run is **valid** if there was no infrastructure error and the simulated customer stayed on
script (it didn't invent an email, zip or order id, didn't repeat itself, and didn't change the
goal). Each run writes `test_cases/case-19/runs/run-<n>/` (`trajectory.json`, `reward.json`,
`config.json`) and prints its verdict. Read each `trajectory.json`; to replace an invalid run, delete
its folder and run again with `--trials 1` (it takes the free number).

## User-testing mode

1. Start the page: `.venv/bin/python -m agent.ui.backend.server`, then open http://127.0.0.1:8000.
2. Choose task **19**, click **Start session**, and keep "Show tool calls" off.
3. The participant reads the role card (the persona above) and plays the customer in their own
   words. They may add realistic detail, but must not invent ids, emails or addresses.
   Suggested first message: "Hi, I want to return the water bottle and exchange the pet bed and
   office chair for the cheapest versions. Both, please."
4. The session ends when the participant says they're done; the facilitator clicks **End session**.
5. The page shows the run folder it wrote (`var/eval/user-testing-<date>/case-19/runs/run-<n>/`).
   Run the survey and interview in [../survey.md](../survey.md) and save them to that folder.
