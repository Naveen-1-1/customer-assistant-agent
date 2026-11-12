# Baseline breakdowns: evidence for the pitch

CS 6983 · Group 5 · generated from the runs in `var/eval/` (2026-11-02). Every claim below was
checked in the transcript, not only in the end-state score.

## Setup (what was run)

- **Baseline:** a plain tool-calling agent built like τ²-bench's own reference agent: one LLM,
  τ²-bench's retail policy as its system prompt, and τ²-bench's 16 retail tools with their
  original descriptions. The store refuses only what its data forbids (wrong status, missing
  item, bad payment). No other checks, no confirmation step beyond what the model chooses to ask.
- **Model:** Laguna XS 2.1 (`poolside/laguna-xs-2.1`, via NVIDIA NIM), temperature 0.
- **Customer:** simulated by the same model from the task's τ²-bench scenario, with τ²-bench's
  user-simulator guidelines.
- **Tasks:** τ²-bench retail tasks picked where the published top models (Claude 3.7 Sonnet,
  GPT-4.1, o4-mini; 4 trials each) often fail. 3 runs per task, fresh store each run.
- **Scoring:** end state of the store vs. τ²-bench's expected end state, then every failing run's
  transcript read. A failure counts only if the **agent's own decision** caused it; runs where the
  simulated customer went off its script, or the harness or API failed, are excluded and listed in
  `progress.md`.

## Headline numbers

| | Valid runs correct |
|---|---|
| Baseline, all 30 tasks tried | **59%** (46 of 78): 11 harmful, 14 incomplete or wrong, 7 stopped with nothing done |
| Top models, same 30 tasks (published logs) | **55%** (197 of 360) |
| Top models, all 114 retail tasks | 75% |
| Baseline, the 8 evidence tasks below | **24%** (5 of 21) |
| Top models, the same 8 tasks | 35% (34 of 96) |

The baseline is not a strawman: on these tasks it is about as reliable as the top models. The
breakdowns below are what that unreliability looks like to a customer.

## The breakdowns, by failure mode

### A. Says one thing, does another

What the customer approved is not what ran.

- **Task 99** (exchange a bike and a puzzle, cancel "the skateboard, and only the skateboard"),
  runs 2 and 3. The agent said: *"I can cancel the skateboard from order #W8855135… The full
  amount ($202.13) will be refunded"* (run 3: *"This is a pending order, so I can cancel just the
  skateboard"*). It then called `cancel_pending_order(#W8855135)`, cancelling **all four items,
  $1,058.79**. Image: `img/99-baseline.png`.
- **Task 76** (cancel two orders with different reasons). The summary the customer approved said
  *"Reason: Item unavailable"*; the call recorded *"no longer needed"*. The order the customer said
  was *"ordered by mistake"* was filed as *"no longer needed"*. Image: `img/sample-76-baseline.png`.

### B. States wrong facts

- **Task 2** (how many t-shirt options are in stock, then return three items). The store has 12
  options, 10 in stock. Run 2: *"We have 14 t-shirt variants in our store, with 12 currently
  available."* Run 3: *"10 t-shirt options are available"*, then a list of only 8 in-stock
  shirts; and, after opening 2 of the customer's 5 orders, *"the cleaner, headphones, and smart
  watch … are not in any of your orders"*. They were in an order it never opened, so no return was
  made. Across tasks 2, 3 and 4 the t-shirt count or list was wrong in **4 of 8** answers.
  Image: `img/2-baseline.png`.

### C. Decides for the customer

- **Task 74** (upgrade a pending laptop, cancel a forgotten 5-item order), run 1: charged the
  laptop's price difference to **PayPal**; the customer never chose a payment method.
- **Task 100** (pending order: "the exact same luggage set but red"; a skateboard with "34 inch,
  custom design"), both valid runs: the agent changed options the customer wanted kept. The
  luggage became a 4-piece hardshell (theirs: 2-piece softshell, available in red); the
  skateboard went from bamboo to plastic (the bamboo one exists).

### D. Invents rules or options

- **Task 34** (cancel only the office items of a pending order if possible, else re-address it),
  **2 of 3 runs.** The agent offered what the policy doesn't allow: *"We could remove the office
  items and keep only the hiking gear… refund of $1,093.34"*. The customer said yes; its call
  would have swapped the three office items for the two hiking items (refused only because the
  counts differed). It then offered *"place a new order for just the hiking gear, then cancel"*,
  which it can't do either, never mentioned the address change, and **cancelled the whole
  $1,527.24 order**, hiking gear included. Image: `img/34-baseline.png`.
- **Task 98** (exchange a bike for a larger frame, mountain bike OK), **2 of 3 runs**: *"A road
  bike and mountain bike are different product types, so I cannot exchange them."* False: the
  large mountain bike is an option of the same Bicycle product (run 3 offered it). The customer
  settled for a medium bike, not the larger one they wanted. Image: `img/98-baseline.png`.
- **Task 72**: *"the backpack is unavailable"* (the one wanted is in stock) and *"only one type
  of change per order"*; the customer was talked into cancelling the whole order.

### E. Acts on the wrong target

- **Task 74**, run 2: cancelled a 3-item $3,228 order the customer didn't mean (they asked for
  the one "with five items").
- **Tasks 98 and 99** (one run each): exchanged a jigsaw puzzle in an order the customer never
  mentioned (it holds the same item); in 98 the camera, in yet another order, was never
  exchanged.
- **Task 3**: changed the t-shirt in the wrong order, which then can't be changed again.

### Also seen once (not counted as recurring)

- **Task 55**: the customer asked *"Can you help me process all of this?"* and the agent
  transferred to a human unasked (*"possibly due to memory issues or unauthorized purchases"*).
- **Task 80**: *"you get the $8.99 difference refunded"*; the difference is $7.99.

## What makes these hard to fix inside the baseline

Every failure above is a free choice of the model: what to say, which tool to call, with which
arguments. Nothing ties the confirmation text to the call that runs, the policy exists only as
prompt text, and facts are read by the model out of raw JSON. The only levers are the prompt and
the model, and the top models fail these same tasks too.

## Related practice (checked 2026-11-02)

- **Approval before tool calls.** OpenAI Agents SDK: a tool can require approval
  (`needsApproval` / `needs_approval`), pausing the run until a person approves or rejects
  ([JS guide](https://openai.github.io/openai-agents-js/guides/human-in-the-loop),
  [Python guide](https://openai.github.io/openai-agents-python/human_in_the_loop)). LangChain's
  human-in-the-loop middleware interrupts on chosen tool calls with approve / edit / reject
  decisions ([docs](https://docs.langchain.com/oss/python/langchain/human-in-the-loop)).
  These approve the *call*; in a customer chat the customer only sees the agent's own words.
- **Guardrails.** OpenAI's *A practical guide to building agents* recommends layered guardrails
  and human intervention for high-risk actions such as cancelling orders or large refunds
  ([summary](https://www.maginative.com/article/how-to-build-ai-agents-a-detailed-practical-guide-from-openai/)).
  NVIDIA NeMo Guardrails adds input, dialog, output and execution rails
  ([repo](https://github.com/NVIDIA-NeMo/Guardrails)).
- **Procedures as structure.** Decagon's Agent Operating Procedures compile natural-language
  procedures into validated workflows ([Decagon](https://decagon.ai/product/aop)).
- **Measuring reliability.** τ-bench (Yao et al., ICLR 2025) introduced pass^k: success in
  *every* one of k tries drops fast as k grows ([paper](https://arxiv.org/abs/2406.12045)).
  τ²-bench (Barres et al., 2025) extends it ([paper](https://arxiv.org/abs/2506.07982),
  [code](https://github.com/sierra-research/tau2-bench)).

## Where the raw evidence is

- Per-conversation logs: `var/eval/pilot-baseline*/<task>__baseline__t<k>.jsonl` (every message,
  tool call, argument and result).
- Run tables and every exclusion with its reason: `docs/pitch/progress.md`.
- Top-model failure modes per task: `docs/pitch/top-model-failures.md`.
- Images: `docs/pitch/img/` (rendered with `python -m customer_workflow_agent.evalkit.render`).
