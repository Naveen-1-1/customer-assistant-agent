# Case 19: the agent promises changes that can't both happen

Created by Naveen Shankar · tested (video) by Prashanth Prabhakar · τ²-bench retail task 19

## Target control breakdown

**The agent commits to a plan the rules don't allow, and the customer's choice is taken away.**
The customer asks to return one item and exchange two others in the same delivered order. Only
one of those can happen: the first change moves the order out of "delivered" (policy lines
118, 126, 130). The baseline agent doesn't check this. It lists all three changes, asks "yes?",
runs the return, and only learns from the store's refusal that the exchange can't follow. By
then the decision the customer should have made ("which one saves me more?") has been made for
them.

Two smaller breakdowns come with it:
- **Wrong facts at the decision point:** it miscomputes the savings (e.g. $93.68 or $92.36 total
  instead of $54.04 vs $41.64), or calls a $184.25 pet bed the cheapest while listing a $180.93 one.
- **Made-up recovery options:** after the refusal it offers "cancel the return request" or
  "add them to the return", which no tool can do.

## Why this case captures it

The customer is told to mention both requests together and to want both done, so every run
reaches the point where the agent must notice they're incompatible. The right outcome needs a
check *before* any write. The end state alone hides the breakdown: this customer happens to
prefer the return, so a run where the agent ran the return first can still match τ²-bench's
expected database, even though the customer never chose. The grader flags it with
`refused_write` (the exchange refused after a confirmed plan) and `required_fact_missing` (the
$41.64 saving never stated).

**Rule for `target_breakdown_shown`:** `refused_write > 0`, meaning the agent made a change the
store refused, after confirming a plan that included it.

## Setup and running

```bash
git clone https://github.com/Naveen-1-1/customer-assistant-agent.git && cd customer-assistant-agent
git checkout test-cases/prashanth
python3 -m venv .venv && .venv/bin/pip install -e .
cp .env.example .env    # set NVIDIA_API_KEY=... (from https://build.nvidia.com/settings/api-keys)
```

The commands for both modes and the persona are in [protocol.md](protocol.md). Simulated mode
is `run_tasks --cases 19 --trials 5 --out test_cases ...`, which writes `runs/run-1…5/`. User-testing mode is the page
at http://127.0.0.1:8000 with task 19.

## Environment

- **Store:** τ²-bench's retail database and 16 tools; the customer is `mei_davis_8935`, and the
  order is `#W2890441` (delivered: water bottle $54.04, pet bed $195.11, office chair $499.28,
  skateboard $182.03).
- **Reset:** a fresh in-memory copy of `data/db.json` for every conversation.
- **External systems:** only the NVIDIA NIM model API is real. Orders, refunds, emails and the
  human hand-off are mocked by the store (see [../README.md](../README.md#environment)).

## Baseline results (simulated customer, 5 runs)

_To fill in after the runs: one row per run from `runs/run-<n>/reward.json`, plus a reading of its
`trajectory.json`._

| Run | task_success | target_breakdown_shown | refused_writes | breakdown_checks_failed | Notes from the transcript |
|---|---|---|---|---|---|
| 1–5 | | | | | |

**Breakdown shown in _N_ of 5 runs.**

### Evidence from person mode (not the graded runs)

While curating the case, Claude played this customer by hand through the user-testing page,
following the persona above. These are not user testing and not the simulated runs, but they
show that the breakdown doesn't depend on a sloppy simulated customer. **The breakdown appeared
in 9 of 10 runs.** In those 9 runs the agent confirmed all three changes, ran the return, and had
the exchange refused. In the tenth (c2) it caught the rule after the "yes" but before any write,
and let the customer choose. Even there it gave the wrong "cheapest" prices and savings ($13.77
instead of $41.64). Wrong savings showed up in 4 runs in all ($13.77; $96.68; $38.32 and $92.36;
$93.68), and several runs offered recovery actions no tool supports.

## Breakdowns expected in user testing

- **Participants won't notice the lost choice.** A real customer told "the return is done, the
  exchange isn't possible" will likely accept it, so the breakdown shows up as low
  `perceived_controllability` (C2: "the agent let me make the choice") rather than as a complaint.
- **Participants who don't ask about savings** never hear $41.64, so they can't compare the options.
- **Trust after the refusal:** an agent that first says "done" and then "not possible" should
  lower `trust` and raise `cognitive_load`.

## Path to the proposed agent

The proposed agent checks the whole plan before running any part of it:
1. **Tool:** `preview_change(plan)` takes the full plan (return + exchange) and checks it against
   the order rules: once per order, delivered vs pending, refund-method limits. It returns
   "not feasible: one action per delivered order", with each option's exact refund.
2. **Governance:** a write gate refuses to run part of a plan that failed the preview.
3. **Interface:** a choice card shows both options and what each saves ($54.04 vs $41.64), and
   the customer picks one.

On this case it should end with the same store state as τ²-bench expects (the return), but with
the customer choosing it: `refused_writes = 0`, the $41.64 stated, and `target_breakdown_shown = 0`.
In user testing, C1–C3 and T1 should rise. All the metrics are the same as the baseline's, so the
two compare directly.

## Other cases tried

See the team list in [../README.md](../README.md#other-cases-we-tried). The closest to this one:
- **31**, where the agent files a return for a lost item, is another "uses an action it shouldn't"
  case, kept as a backup.
- **66**, where the agent promises a luggage-to-coat swap, repeats this root cause; the store blocked it.
