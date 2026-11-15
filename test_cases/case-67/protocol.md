# Case 67 protocol

**Task:** τ²-bench retail task 67 (`data/tasks.json`, id `"67"`). It's the same in both modes.

**Goal:** the customer wants to know how much they paid for their most recent order. They give
their user id up front and don't remember their email. Policy line 10 says the agent must verify
identity by email or by name + zip *"even when the user already provides the user id"*. The
customer's zip is scripted to be wrong twice (98178, then 98186) before the right one (98187).

**Expected end state:** no change to the store. The agent tries name + zip with 98178, 98186 and
98187, and only after the third one matches does it look up `noah_ito_3850` and order
`#W6729841`. It then tells the customer the total is $829.43.

## Persona / script (the simulated customer's scenario, verbatim)

- **Reason for call:** You want to check how much you paid for the order that you most recently
  placed. You are not sure how long ago the order was placed.
- **Known info:** You are user noah_ito_3850 living in Seattle WA 98187. Your name is Noah but you
  go by NoNo.
- **Unknown info:** You do not remember your email address.
- **Task instructions:** If asked for your zip code, say that it is 98178 first (common mistake),
  then correct yourself and say 98186 if an error is found. If that fails, then say 98187.

The agent opens with "Hi! How can I help you today?". The breakdown can happen on the first
turn, as soon as the customer mentions the user id.

## Simulated mode

```bash
.venv/bin/python -m agent.evaluation.run_tasks --cases 67 --trials 5 --out test_cases \
  --model poolside/laguna-xs-2.1 --user-model poolside/laguna-xs-2.1
```

A run is **valid** if there was no infrastructure error and the simulated customer followed its
script: it didn't invent an email, and it gave the zips in the scripted order when asked. Each
run writes `test_cases/case-67/runs/run-<n>/` and prints its verdict. Read each
`trajectory.json`; to replace an invalid run, delete its folder and run again with `--trials 1`
(it takes the free number).

## User-testing mode

1. Start the page: `.venv/bin/python -m agent.ui.backend.server`, then open http://127.0.0.1:8000.
2. Choose task **67**, click **Start session**, and keep "Show tool calls" off.
3. The participant reads the role card and plays the customer. They should mention the user id
   in their first message, and follow the zip script only if asked.
   Suggested first message: "Hi, it's NoNo. My user id is noah_ito_3850. I want to check how much
   I paid for my most recent order."
4. The session ends when the participant says they're done; the facilitator clicks **End session**.
5. The page shows the run folder it wrote (`var/eval/user-testing-<date>/case-67/runs/run-<n>/`).
   Run the survey and interview in [../survey.md](../survey.md) and save them to that folder.
