# Decisions and why

CS 6983 · Group 5 · project pitch work, 2026-11-01 to 2026-11-02. One entry per decision:
what we chose, what else we considered, why, what it costs us, and where the evidence is.

---

## 1. Task family and user: a customer fixing a retail order over chat

- **Chosen:** customer self-service for retail orders (cancel, return, exchange, change items,
  address or payment). The only user is the customer.
- **Considered:** customer plus a supervisor who approves risky changes (the repo has an approval
  path); several users at once.
- **Why:** it is the task our existing agent already serves, the delegation is easy to see (the
  customer hands over money-moving, often once-only changes), and committing to the simpler user
  first leaves room to add the supervisor if the evidence is thin.
- **Trade-off:** the supervisor-approval path isn't evaluated; approval stays off in every run.

## 2. Dataset: τ²-bench retail

- **Chosen:** τ²-bench's retail domain: 114 tasks, the written policy, the store database,
  copied unmodified at commit `5bfa7e37b36656b37dc6d022156be6563c1007f3` (`data/README.md`).
- **Considered:** writing our own tasks; the original τ-bench; other agent benchmarks.
- **Why:** a real policy, a real database and an end-state check, from the benchmark industry
  uses for exactly this kind of agent (Sierra's τ-bench line). Our agent was built on the same
  data, so both systems face identical tasks. Hand-written tasks would invite tasks tuned to make
  the baseline fail.
- **Trade-off:** the customer is simulated, and the end-state score misses wrong facts told
  along the way, so every failing transcript is read by hand (decision 9).

## 3. Proof the tasks are hard: τ²-bench's published top-model logs

- **Chosen:** the published retail results for Claude 3.7 Sonnet, GPT-4.1, o4-mini and
  GPT-4.1-mini (4 trials per task, GPT-4.1 playing the customer). Overall pass rates 0.79, 0.74,
  0.71, 0.66. Summary: `top-model-failures.md`.
- **Considered:** running frontier models ourselves.
- **Why:** it shows the tasks we pick are hard for the best models too, at no cost, so a failure
  isn't just "the small model is weak". We compare **failure modes**, not headline scores.
- **Trade-off:** their simulated customer is a different model from ours, so pass rates are
  indicative only.

## 4. Baseline: a standard tool-calling agent, built like τ²-bench's reference agent

- **Chosen:** one LLM, τ²-bench's agent instructions plus the retail policy as its system
  prompt, τ²-bench's 16 retail tools with their original names, arguments and descriptions
  (`src/customer_workflow_agent/baseline/`). The store refuses only what its data forbids (wrong
  status, missing item, bad payment); there are no other checks. LiteLLM is called directly, no
  new dependencies.
- **Considered:** an off-the-shelf agent framework (OpenAI Agents SDK, LangChain); a baseline
  with tuned prompts.
- **Why:** it is how industry builds these agents today, and it matches the agent behind the
  published scores in decision 3. Frameworks give the same loop. A tuned baseline would no longer
  be "what is used today".
- **Trade-off:** confirmation is up to the model; it usually asks, but nothing ties what it asks
  to what it calls (that is breakdown A, not a flaw in the setup).

## 5. Comparison: a controlled before/after

- **Chosen:** same tasks, same simulated customer, same starting store (fresh each run), same
  model for the agent; only the harness differs. The workflow's fallback model is set to the same
  model during runs, so a run never switches models, and both agents get 60 s per model call.
- **Considered:** comparing against published numbers; different models per side.
- **Why:** any difference can then be pinned on the harness, not the model or the customer.
- **Trade-off:** one model per side; results are about this model on these tasks.

## 6. Models: stable and fast first (NVIDIA NIM key only)

All calls go through the NVIDIA NIM API. We needed many repeats quickly, so stability and latency
came before raw capability. A stability gate (repeated calls) and small bake-offs decided:

| Model | Result | Use |
|---|---|---|
| Laguna XS 2.1 (`poolside/laguna-xs-2.1`) | 14/15 stable calls, p95 8.5 s; best baseline in the bake-off; stuck closest to the script as the customer | **Baseline agent and simulated customer** |
| Nemotron 3.5 Lightning (`nvidia/nemotron-3.5-lightning-30b-a3b`) | stable API and strict JSON output for the workflow's extraction calls; as a free-form agent it dropped "#" from order ids and looped | **Workflow model** |
| Nemotron 3.5 Bolt (`nvidia/nemotron-3.5-bolt-e4b`) | 15/15, p95 2.4 s | fallback candidate |
| Mistral Large 4 | p50 9 s, p95 32 s | out: too slow to iterate |
| MiniMax | throttled | out |
| Others tried | 404 or timeouts | out |
| `nemotron-3-super` (the repo's configured fallback) | 404 | **pending:** switch the production fallback to Bolt |

- **Why not frontier models:** the tasks are ones frontier models also fail (decision 3), and
  using the same model on both sides (decision 5) is what makes the comparison fair. We avoided
  the trap of a weak baseline model "fixed" by a stronger one.
- **Known limit:** Lightning sometimes returns valid JSON that doesn't match the strict schema,
  which the workflow shows as "Sorry, I'm having trouble understanding". Not fixed; counted
  against the workflow.

## 7. Simulated customer

- **Chosen:** Laguna XS 2.1 with τ²-bench's user-simulator guidelines (verbatim) and each task's
  scenario; fixed temperature; it ends with `###STOP###`, `###TRANSFER###` or
  `###OUT-OF-SCOPE###`. It typed its answers to the workflow's buttons and popups, which the
  harness maps to clicks (decision 12).
- **Considered:** Lightning as the customer (bake-off on tasks 0 and 82).
- **Why:** it followed the scripts more closely.
- **Trade-off:** it still goes off script at times (invents an address or a zip, keeps items it
  should return, asks for a human). Those runs are excluded, the same way for both agents.

## 8. Task selection and calibration

- **Chosen:** start from tasks where top models fail often, keep strong multi-step tasks only, and
  tag each by whether our workflow can do it as is, with a small fix, or not at all. Then keep
  calibrating:
  - **stop** a task when the baseline handles it (no contrast),
  - **stop** it when the workflow can't do it after repeated rounds (not a small fix),
  - **stop** it when its failures are simulator-driven,
  - **add** tasks that set up the same failure *mode* in other processes, rather than harder tasks.
- **Why:** the evidence we need is "the standard agent fails where a structured one can work",
  and making tasks harder for its own sake would test the wrong thing.
- **Bookkeeping:** "stopped" keeps the row and its reason in `progress.md`; nothing is deleted.
  33 tasks were considered and 30 were run on the baseline.

## 9. What counts as evidence

- **Chosen:** a breakdown counts only if it **recurs** (2 of 3 runs, or the same pattern in 2 or
  more tasks) and the transcript shows the **agent's own decision** caused it. Excluded, and
  listed with reasons in `progress.md`:
  - the simulated customer going off its script,
  - harness errors,
  - API timeouts,
  - popup replies the harness read wrongly.
- **Why:** end-state scores alone both miss failures (wrong facts told) and include
  failures that aren't the agent's.
- **Corrections we made by re-checking:** task 99's "said X, did Y" happened in 2 of 3 runs, not
  3 of 3; the t-shirt count was wrong in 4 of 8 answers, not 7 of 8. The documents state the
  corrected numbers.

## 10. "Verified": two labels

- **Chosen:** at first, all valid workflow runs had to be correct (at least 2). We then switched,
  by group decision, to two labels:
  - **Verified:** right at least twice and never harmful (tasks 2, 99, 74).
  - **Safe, fix pending:** right at least once, never harmful, the other runs stopping with
    nothing changed, for a cause with a known fix (task 34).
- **Why:** a safe stop is a different kind of failure from a wrong change, but the label must say
  exactly what the runs show.
- **Where:** `verified-tasks.md`, generated from the runs.

## 11. Fixing the workflow during evaluation

- **Chosen:** only small fixes: a deterministic rule or a clarifying message, each with a test.
  Examples:
  - every zip and email in a message is tried;
  - a payment method named in words;
  - item names in the order list;
  - "only whole orders cancel" for partial cancels.

  A task's runs count from the round after the fix that addressed it, except task 34, where all
  rounds still count (the more conservative choice). Each task has a fix limit: past it, the task
  is stopped.
- **Why:** big rewrites would have turned evidence gathering into the final project.
- **Regression check:** after each fix, the verified tasks were re-run and passed (99 and 74).
  The fix was also checked against every past customer message, which caught two false
  triggers before any run.

## 12. Harness rules for a text-only customer

- **Chosen:**
  - the workflow's buttons are shown as "Options: …";
  - its confirmation popup is shown as a "[Confirmation]" block;
  - a typed reply counts as Yes only if it starts as one (it is No otherwise, so nothing runs on
    doubt);
  - a reply that says Yes and ends the chat in the same message is acted on first;
  - typed text is capped at the chat box's 2000 characters.

  After each change to the reply reader, every past popup was re-checked, and runs it had misread
  are excluded automatically.
- **Why:** a real customer clicks; the simulated one types, and mapping its words wrongly would
  credit or blame the agent for the harness.

## 13. Running the evaluation

- **Chosen:** about 36–40 requests per minute in total, split across baseline and workflow runs
  and adjusted each round (more for the workflow once the baseline pilot was done). Logs per
  conversation in `var/eval/<run>/` (every message, tool call, argument, result and popup),
  traced in LangSmith (project `customer-workflow-agent-eval`).
- **Why:** stay under the API's limits without stalling either side.

## 14. Pitch framing

- **Chosen:** the deck shows observed breakdowns of the baseline only and presents the
  improvements as planned changes, each tied to a breakdown, with a controlled evaluation plan.
  Tasks are grouped by customer-service process and failure mode, with specific transcripts as
  examples. Prototype results are kept for the final.
- **Why:** the pitch rubric asks for baseline observations and a plan; the final project is where
  the improved system is evaluated against the same baseline.

## 15. Branch and repository

- **Chosen:** branch `pitch/baseline-evidence` off `main`; nothing stripped from the repo; new
  code in new folders (`baseline/`, `evalkit/`) with tests; nothing committed or pushed until the
  group asks.

---

**Where things are:** `evidence.md` (breakdowns, numbers, related work) · `progress.md` (every
task, run and exclusion) · `verified-tasks.md` · `top-model-failures.md` · `pitch-deck.pptx` ·
`img/`.
