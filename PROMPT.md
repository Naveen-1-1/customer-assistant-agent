# Prompt: run a test case 5 times (Claude as the customer)

Paste this into Claude Code (the desktop app, so it has the browser pane) after cloning the repo.
Replace `<TASK_ID>` with the test case to run (19, 37 or 67).

```text
You are helping me run test case <TASK_ID> (τ²-bench retail task) 5 times against the baseline agent, in the repo I just cloned (customer-assistant-agent). Fresh machine: nothing is installed yet.

SETUP
1. Check out the branch `test-cases/submission`.
2. Make sure Python 3.13+ is available (install it if missing). Create `.venv` in the repo root and run `pip install -e .` inside it.
3. Copy `.env.example` to `.env`. Do NOT ask me to paste my API key into chat. Tell me to open `.env` myself and set `NVIDIA_API_KEY=` to my key from https://build.nvidia.com/settings/api-keys, then wait until I say it's done.
4. Start the user-testing UI with the launch config in `.claude/launch.json` ("user-testing-ui", i.e. `.venv/bin/python -m agent.ui.backend.server --port 8000`) and open http://localhost:8000 in the built-in browser pane so I can watch. Turn on "Show tool calls".

WHO PLAYS WHAT
- The agent is the baseline (Laguna XS 2.1 on NVIDIA NIM). Don't change any code, prompts or tools.
- YOU play the customer, typing into the page. Read the task's scenario from the role card (or `data/tasks.json`, id <TASK_ID>, `user_scenario`) and follow it literally:
  - Give info only when asked. Never invent ids, emails, addresses or details the scenario doesn't give.
  - Keep what it says to keep hidden hidden. Follow scripted lines and conditions exactly.
  - Confirm only what matches the goal. Don't check the agent's arithmetic or correct it unless the scenario says to.
  - Send ONE message per turn and wait for the reply. Never put "that's all" in the same turn as a confirmation; say "yes" on its own, and only end after the action has run or been clearly refused.
- Use the same customer behavior in all 5 runs so they're comparable.

EACH RUN (repeat 5 times)
1. Pick task <TASK_ID>, click "Start session", and play it to the end.
2. Click "End session". The page shows the verdict, notes and the log path (`var/eval/human-<date>/<TASK_ID>__baseline__h<k>.jsonl`).
3. Rename that log to `..._c<k>.jsonl` and set its `"user_model"` field to `"claude-customer"` on every line, so nobody mistakes it for real user testing.
4. If YOU made a mistake as the customer (ended early, invented a detail, broke the script), move the log to `var/eval/human-<date>/excluded/` and do one more run instead. Report it honestly.

AFTER 5 VALID RUNS
1. Run `.venv/bin/python -m agent.evaluation.grader var/eval/human-<date>` to grade the folder.
2. Read every transcript yourself as well, not just the grader.
3. Give me a short table: one row per run with the verdict, whether the end state matches τ²-bench, the grader notes that matter, and in one line what the agent did wrong (quote the key agent sentence and the tool call it made). End with "breakdown shown in X of 5 runs".
4. Don't commit anything, and don't put my API key in any file, log or message.
```

Note: these runs have Claude playing the customer. The graded submission's 5 baseline runs still need the
repo's simulated customer (`python -m agent.evaluation.run_tasks`).
