# Customer-assistant agent: curated test cases

CS 6983 Group 5 (Naveen Shankar, Prashanth Prabhakar, Shaunak Soni). Three test cases of a
tool-calling customer-support agent on τ²-bench's retail store, each capturing one control
breakdown. The full submission (case documents, protocols, metrics, survey) is in
[test_cases/](test_cases/README.md). This page is the checklist each of us follows.

## Who does what

Each case is tested by someone who didn't create it. The tester works on their own branch, does
the 5 graded runs, records the video, and merges back.

| Case | Created by | Tested by | Tester's branch | Document to follow |
|---|---|---|---|---|
| 19 | Naveen Shankar | Prashanth Prabhakar | `test-cases/prashanth` | [test_cases/case-19](test_cases/case-19/README.md) |
| 37 | Prashanth Prabhakar | Shaunak Soni | `test-cases/shaunak` | [test_cases/case-37](test_cases/case-37/README.md) |
| 67 | Shaunak Soni | Naveen Shankar | `test-cases/naveen` | [test_cases/case-67](test_cases/case-67/README.md) |

Due **Mon 2026-11-16, 11:59 pm**.

## Steps for the tester (replace `<id>` with your case and `<you>` with your first name)

### 1. Set up (once, from a fresh clone)

Needs Python 3.13+ and your own NVIDIA API key (free at https://build.nvidia.com/settings/api-keys).

```bash
git clone https://github.com/Naveen-1-1/customer-assistant-agent.git
cd customer-assistant-agent
git checkout test-cases/<you>
python3 -m venv .venv
.venv/bin/pip install -e .
cp .env.example .env
```

Open `.env` and set `NVIDIA_API_KEY=` to your key. Never commit `.env`.

### 2. Do the 5 graded runs (simulated customer)

```bash
.venv/bin/python -m agent.evaluation.run_tasks --cases <id> --trials 5 --out test_cases \
  --model poolside/laguna-xs-2.1 --user-model poolside/laguna-xs-2.1
```

- This writes `test_cases/case-<id>/runs/run-1…5/`, each with `trajectory.json`, `reward.json` and
  `config.json`, and prints each run's verdict. It takes a few minutes per run.
- Read every `trajectory.json`. If the simulated customer broke its script (invented an email,
  zip or order id, repeated itself, or dropped its goal), delete that run's folder and run the
  same command with `--trials 1`; the new run takes the freed number. Repeat until there are 5
  valid runs.
- Fill the **Baseline results** table in `test_cases/case-<id>/README.md`: one row per run, using
  the numbers in its `reward.json` plus a one-line note on what the agent did. Then fill in the
  line "Breakdown shown in N of 5 runs".

### 3. Record the video

Use only the case's document (`test_cases/case-<id>/README.md` and `protocol.md`). Record:
1. the setup from a fresh clone (step 1);
2. one simulated run, sent to a scratch folder so it isn't added to the graded set:
   `run_tasks --cases <id> --trials 1 --out var/eval/video …`;
3. user-testing mode: start `.venv/bin/python -m agent.ui.backend.server`, open
   http://127.0.0.1:8000, pick task `<id>`, read the role card, and play the customer;
4. the breakdown with the baseline agent. If it doesn't happen in that run, say so; the document
   explains what's expected.

Upload the video somewhere the team and the instructors can open, and put the link in the Video
column of [test_cases/README.md](test_cases/README.md).

### 4. Push and merge

```bash
git add test_cases/case-<id> test_cases/README.md
git commit -m "Case <id>: 5 baseline runs, results and video link"
git push -u origin test-cases/<you>
```

Then open a pull request from `test-cases/<you>` into `test-cases/execution`. Each tester changes
only their own case's folder and one row of `test_cases/README.md`, so the three merges shouldn't
conflict.

## What not to change

Everything below is fixed for the graded runs. Changing it would make runs disagree with each
other or with the documents:
- the agent, its prompt and tools (`agent/baseline/`), the simulated customer, and `data/`;
- the grader (`agent/evaluation/grader.py`), the 12 core metrics and each case's breakdown rule
  (`agent/evaluation/outputs.py`, [test_cases/metrics.md](test_cases/metrics.md)).

The survey and interview ([test_cases/survey.md](test_cases/survey.md)) and the wording of the
documents can still change.

## Submitting (once all three are merged)

One person submits a single link on Canvas that gives access to:
- the repository, branch `test-cases/execution`;
- the three case documents ([test_cases/](test_cases/README.md));
- the three videos (linked from [test_cases/README.md](test_cases/README.md)).
