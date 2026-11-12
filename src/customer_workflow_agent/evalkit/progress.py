"""Write docs/pitch/progress.md: each pilot task's baseline and workflow results so far.

    python -m customer_workflow_agent.evalkit.progress

Baseline results come from `var/eval/pilot-baseline*`, workflow results from `var/eval/wf-iter*`
(the latest iteration that ran the task, after the fixes made so far).
"""

import json
from datetime import datetime
from pathlib import Path

from customer_workflow_agent.evalkit.findings import early_stop
from customer_workflow_agent.evalkit.workflow_adapter import popup_answer
from customer_workflow_agent.settings import get_settings

# Generic type, short task name. Mixed tasks are filed under their main action.
TASKS = {
    "0": ("Multi-item exchange with fallback", "Exchange keyboard + thermostat, fallback spec"),
    "99": ("Multi-item exchange with fallback", "Exchange bike + puzzle with preferences"),
    "107": ("Multi-item exchange with fallback", "Worn boots: same spec, else fallback spec"),
    "71": ("Combined edits to a pending order", "Redirect order home + change two items"),
    "72": ("Combined edits to a pending order", "Redirect order home + change two items (v2)"),
    "15": ("Item change with payment choice", "Resize pending boots, PayPal for difference"),
    "100": ("Item change with payment choice", "Modify pending items + return, card payment"),
    "59": ("Conditional cancellation", "Two pending orders: cancel one, re-address other"),
    "74": ("Conditional cancellation", "Laptop upgrade + cancel a forgotten order"),
    "76": ("Conditional cancellation", "Cancel for the right reason (partial not allowed)"),
    "81": ("Conditional cancellation", "Cancel every order holding listed items"),
    "82": ("Return under refund rules", "Return pricier tablet; refund-method pressure"),
    "92": ("Return under refund rules", "Return skateboards; adds items at confirmation"),
    "2": ("Product question + action", "Count t-shirt options + return three items"),
    "3": ("Product question + action", "Count t-shirt options + change pending t-shirt"),
    "4": ("Product question + action", "Count t-shirt options + change all t-shirts"),
    "45": ("Request with unclear references", "Vacuum exchange with a mistyped order id"),
    "79": ("Request with unclear references", "Swap bottle to match another order's bottle"),
    "94": ("Request with unclear references", "Laptop exchange; which laptop is unclear"),
    "51": ("Return under refund rules", "Return a camera; order number uncertain, insists on card"),
    "39": ("Address change", "Update default address after a move (address in a recent order)"),
    "9": ("Change of mind at confirmation", "Exchange bottle + lamp; at confirmation, lamp only"),
    "18": (
        "Change of mind at confirmation",
        "Return a chair; at confirmation, exchange it instead",
    ),
    "24": ("Change of mind at confirmation", "Cancel the grill; at confirmation, keep it"),
    "16": ("Conditional cancellation", "Cancel all pending orders + return only the watch"),
    "98": (
        "Multi-item exchange with fallback",
        "Exchange bike + puzzle; cancel an order (99's twin)",
    ),
    "34": ("Partial cancellation request", "Cancel some items if possible, else re-address order"),
    "33": ("Partial cancellation request", "Cancel some items if possible, else change address"),
    "57": ("Partial cancellation request", "If not shipped, cancel only the air purifier"),
    "43": ("Product/order question + action", "Where did my order ship + tracking; change address"),
    # Same failure modes, other processes (picked by mode, not by task type).
    "55": ("Cancel/return everything", "Cancel pending orders, then return all delivered items"),
    "103": (
        "Several requests in one chat",
        "Return 3 items, re-address + recolor an order, tracking",
    ),
    "80": ("Exchange with a set payment", "Exchange a t-shirt, pay the difference by gift card"),
}
# Taken out of the comparison, with the reason (calibrated from the runs so far).
DROPPED = {
    "15": "baseline 3/3 correct: no failure to show",
    "59": "orders carry no dates; the simulated customer guessed which order was older",
    "45": "the baseline's only failure was a safe one: weak evidence",
    "3": "workflow applies 'all t-shirts' and ignores the 'small' filter (changed an XXL one); "
    "not a quick fix",
    "71": "after 2 fix rounds the address + item change works, but 'cancel this and start over' at "
    "a popup is read as an order cancellation (classification); twin task 72 kept",
    "81": "workflow cancels one of the two orders; finding every order holding listed items isn't "
    "supported (not a quick fix)",
    "76": "workflow didn't get a clean run in 2 rounds (cancellation reasons, runs out of turns)",
    "79": "stretch task; workflow 🟡🟠 in its round",
    "4": "workflow 1 correct of 3 valid runs over 2 rounds (one popup per order; model output "
    "errors)",
    "82": "the pricier tablet is in another order; the workflow queues the customer's 'what does "
    "it cost?' instead of answering mid-request (not a quick fix)",
    "107": "baseline 2/3 correct: weak contrast; budget moved to stronger candidates",
    "9": "baseline handles it (2/2 correct): no contrast to show",
    "51": "baseline 2/3 correct and its only failure was a safe one: weak evidence",
    "24": "baseline handles it (2/2 correct): no contrast",
    "18": "baseline handles it (3/3 correct): no contrast; the simulated customer often skips "
    "its scripted rethink at the popup",
    "39": "the baseline's wrong addresses came from the simulated customer, which invented one "
    "(its script says it's in a recent order): no agent-caused failure",
    "92": "added then withdrawn: harder than needed",
    "94": "added then withdrawn: harder than needed",
    "72": "workflow failed 3 rounds: the customer's mid-flow 'only the backpack' is lost, and a "
    "typed No re-shows the same popup (not a quick fix)",
    "16": "workflow never finished (×2): 'cancel all my pending orders' made the watch return "
    "list every item, and a typed No re-shows the same popup; baseline got it right once",
    "98": "workflow 0/2: exchange loops (a camera from another order; 'larger frame size' kept "
    "after the customer answered), then the skateboard looked up in the wrong order; not small "
    "fixes. Its baseline transcripts are kept as notes",
    "33": "needs the default address set from an order's address (the workflow offers only the "
    "current default); the baseline's wrong address came from the simulated customer",
    "57": "baseline handles it (2/2 correct): no contrast",
    "43": "baseline handles it (2/2 correct): no contrast",
    "55": "the simulated customer keeps items and picks 'ordered by mistake' against its script "
    "(both agents), so the end state can't be judged; the baseline's unrequested transfer is "
    "kept as a note",
    "103": "baseline 1/1 correct once the simulator-invented addresses are excluded (no "
    "contrast); the workflow once created a cancel from the customer's 'cancel' that meant return",
    "80": "baseline handles it (2/2 correct): no contrast",
    "100": "workflow 0/2: the simulated customer refused the PayPal-only return refund again and "
    "again (its card preference is for the pending-order change), and the workflow never reached "
    "the item change; the baseline transcripts are kept as notes",
    "0": "baseline handles it (2/2 valid runs correct): no contrast",
}
MARK = {"ok": "✅", "harmful": "🔴", "incomplete": "🟠", "safe": "🟡", "excluded": "⚪"}

# What the end-state check doesn't show, from reading the transcripts (kept by hand).
NOTES = [
    "**Wrong facts told (tasks 2, 3, 4; audited answer by answer):** asked how many t-shirt "
    "options are available (10 of 12 in stock), the baseline was wrong in 4 of 8 answers: "
    '"14 variants, 12 available" (2-t2), "14 variants" (4-t3), all 12 called available (4-t1), '
    'and "10 available" over a list of only 8 (2-t3). The other 4 said 12 total / 10 in stock. '
    'The workflow counts in code: "10 of 12 options are available right now".',
    "**Task 59 — needs review (simulator-driven):** orders carry no dates, and in every run "
    "(both agents) the simulated customer itself declared #W2702727 the older order and asked to "
    "cancel it; the scenario implies #W8268610. Not headline evidence unless a transcript shows "
    "the agent ignoring the contradiction (cancel #W2702727 *and* re-address it).",
    "**Tasks 71, 72 (baseline):** address changed but the item change dropped (×2); once the "
    "order was cancelled instead (72).",
    "**Task 3:** changed the t-shirt in the wrong order (that order can't be changed again). "
    "**Task 4:** changed one of the two orders and silently skipped the other.",
    "**Task 76 (baseline, transcript-checked):** what the customer approved ≠ what ran: the "
    'summary said "Reason: Item unavailable", the call recorded "no longer needed"; and the '
    'order the customer said was "ordered by mistake" was filed as "no longer needed". One '
    "other failing run was the simulator's own wrong reason (excluded from the claim).",
    '**Task 72 (workflow, round 4):** "pay the difference with PayPal" was taken as a '
    "separate change-the-order's-payment request; the popup stated it exactly and the customer "
    "still said yes. Limits of a popup: it only protects a customer who reads it.",
    '**Task 98 (baseline, transcript-checked):** 2 of 3 runs invented a rule: "a road bike and '
    'mountain bike are different product types, so I cannot exchange them" — the large mountain '
    "bike is an option of the same Bicycle product (run 3 offered it). In run 1 the customer, "
    "talked out of the exchange, ended with a return; the agent then exchanged a puzzle in an "
    "order the customer never mentioned (same item id) and never exchanged the camera.",
    '**Task 55 (baseline run 2, transcript-checked):** the customer asked "Can you help me '
    'process all of this?" and the agent transferred to a human unasked ("possibly due to memory '
    'issues or unauthorized purchases"); none of the 4 in-scope requests was done.',
    "**Task 100 (baseline, transcript-checked):** in both valid runs the agent changed options "
    'the customer wanted kept: "the exact same luggage set but red" became a 4-piece hardshell '
    "(theirs: 2-piece softshell, available in red); a skateboard asked for as 34 inch, custom "
    "design became plastic instead of bamboo (the bamboo one exists). Run 1 excluded: the "
    "simulated customer asked for a human.",
    "**Workflow fixes so far (each with a test):** zip picked from context; payment named in "
    'words ("card ending 2478"); order list shows items; filler option values ignored; items '
    "must be named by the customer (no invented items); every email in the message is tried; an "
    "item is found by name when the "
    'model mixes in the wanted options; naming items isn\'t "return everything"; asked to '
    "cancel some items of a pending order, it says only whole orders cancel (before round 18).",
    "**Task 34 (workflow, round 18, transcript-checked):** the partial-cancel fix works (it says "
    "only whole orders cancel; the customer picks the address change), but the address step "
    'fails next: a typed "use your default address" isn\'t applied (only the button is), a '
    'zip or "[Street address to be provided]" is taken as the street, and once the model-worded '
    "question said \"I've updated your address\" when nothing was written — the baseline's "
    "says-X-does-Y, in the one place the workflow lets the model write.",
    '**Harness fixes:** the agent may act on the customer\'s last message ("yes ###STOP###"); a '
    "typed popup reply counts as yes only if it starts as one. Runs whose popup answer the "
    "older reader got wrong are re-checked automatically and shown ⚪ (3 so far).",
]


# Runs excluded after reading the transcript: the simulated customer, not the agent, went off
# its script. Keys are "<run dir>/<file stem>"; a bare task id excludes every run of that task.
REVIEWED_EXCLUSIONS = {
    "59": "orders carry no dates; the simulated customer guessed which order was older",
    "pilot-baseline-2/76__baseline__t2": "the simulated customer gave the wrong cancel reason",
    "wf-iter4/76__workflow__t2": "the simulated customer took a 31-inch board; its script says "
    "cancel when the exact board is unavailable",
    "wf-iter5/3__workflow__t2": "the simulated customer asked to change an XXL crew-neck t-shirt; "
    "its script says only the small ones, same size",
    "pilot-baseline/0__baseline__t2": "the simulated customer chose the white-backlight keyboard; "
    "its script says no backlight",
    "pilot-baseline/72__baseline__t2": "the simulated customer put off the backpack change itself",
    "wf-iter12/18__workflow__t2": "the simulated customer confirmed the return outright; its "
    "script says rethink at confirmation and exchange instead",
    "wf-iter12/24__workflow__t1": "the simulated customer said 'Yes, please go ahead and cancel "
    "it'; its script says regret at confirmation and keep the grill",
    "wf-iter11/72__workflow__t2": "the simulated customer asked for and confirmed the lamp change "
    "too; its script says change only the backpack",
    "pilot-baseline/4__baseline__t3": "the simulated customer chose to keep the second order "
    "unchanged; its script says change all t-shirts",
    "wf-iter5/4__workflow__t1": "the simulated customer left after the first order; its script "
    "says change all t-shirts",
    "wf-iter16/55__workflow__t2": "infra: the sign-in model call timed out on the API (15 s "
    "limit then), and the simulated customer then invented a zip not in its script",
    "pilot-baseline-6/33__baseline__t1": "the simulated customer invented the Seattle address; "
    "its script says don't reveal it (it's in the order)",
    "pilot-baseline-7/55__baseline__t1": "the simulated customer decided on its own to keep the "
    "air purifier and coffee maker and chose 'ordered by mistake'; its script says return "
    "everything",
    "pilot-baseline-7/103__baseline__t3": "the simulated customer invented its 'default' address "
    "(123 Main Street); the agent used it although the profile it had read says 921 Park Avenue",
    "pilot-baseline-7/80__baseline__t2": "the simulated customer (scripted to confuse) disowned "
    "a backpack in the order and asked for a human; the agent's wrong refund ($8.99, right: "
    "$7.99) is kept as a note",
    "wf-iter18/34__workflow__t3": "after declining three address popups the simulated customer "
    "chose to cancel the whole order (its script: just change the address) and confirmed a popup "
    "listing every item; the workflow's address bug that confused it is in the notes",
    "pilot-baseline-7/103__baseline__t2": "the simulated customer invented its 'default' address "
    "(1234 Michigan Ave), as in run 3",
    "wf-iter18/74__workflow__t1": "the simulated customer asked to cancel the laptop order ('I no "
    "longer need the laptop'; its script: upgrade it) and confirmed a popup showing exactly that",
    "pilot-baseline-2/100__baseline__t1": "the simulated customer said it didn't recognise its "
    "orders and asked for a human",
}

# Passed both checks: the baseline fails because of its own decisions (transcript-checked) and
# the workflow gets it right. Description: what the customer wants · what went wrong · the fix.
VERIFIED = {
    "2": "The customer asks how many t-shirt options are in stock, then returns a cleaner, "
    "headphones and a watch. **Baseline** (2 valid runs; run 1 excluded, the customer ended the "
    'chat in the same message as "yes"): run 2 said "14 variants, 12 available" (right: 12 and '
    '10); run 3 said "10 available" but listed only 8, then told the customer the items "are not '
    'in any of your orders" after opening 2 of 5 (they were in an unopened one), so no return '
    'was made. **Workflow:** answered "10 of '
    '12 options are available right now" from the catalog and made the exact return (one run got '
    'there only after a "couldn\'t find Vacuum Cleaner" loop, a bug since fixed with a test).',
    "4": "The customer asks how many t-shirt options are in stock, then changes every pending "
    "t-shirt (two orders) to purple, size S, polyester, v-neck. **Baseline:** told the customer "
    "12, 12 and 14 options in its 3 runs (right answer: 10); the item changes themselves were "
    'fine when made. **Workflow:** answered "10 of 12 options are available" from the catalog '
    "and changed both orders' t-shirts, one confirmation popup each.",
    "72": "The customer redirects a pending order to their default address and changes the "
    "backpack (grey, medium, polyester), changing their mind on the way (only the backpack, pay "
    'by PayPal). **Baseline:** made up rules ("the backpack is unavailable" though the one '
    'wanted is in stock, "only one type of change per order") and talked the customer into '
    "cancelling the whole order. **Workflow:** did the address change first and then the item "
    "change, each shown exactly in a popup; when the customer changed their mind at a popup, "
    "nothing was written until the right change was confirmed.",
    "99": "The customer exchanges a bike and a puzzle in one order, a camera in another, and asks "
    'to cancel "the skateboard, and only the skateboard". **Baseline** (re-checked run by run): '
    "in 2 of 3 runs told the customer it would cancel the skateboard and refund $202.13, then "
    "cancelled the whole 4-item order ($1,058.79); in run 1 it said only whole orders cancel "
    "and the simulated customer chose to (off its script), but it exchanged the bike alone and "
    "never the puzzle; in run 2 the split exchange left half refused (an order can be exchanged "
    "once); in run 3 it exchanged a puzzle in an order the customer never mentioned. "
    "**Workflow:** one confirmation popup for the bike "
    "and the puzzle together, and an exact camera exchange; once the popup let the customer "
    "catch and refuse a wrong camera variant. No order was cancelled: once the cancel list showed "
    "all four items and the customer declined; once the customer looked for the skateboard in "
    "the wrong order and the workflow kept repeating that order's details until the turn limit "
    "(a loop, but no wrong change).",
    "74": "The customer upgrades a pending laptop to i9 (256 GB, silver) and cancels another "
    'pending order "with five items" whose id they don\'t remember. **Baseline:** cancelled a '
    "3-item $3,228 order the customer didn't mean; charged the laptop's price difference to "
    "PayPal though the customer never chose a payment method; once left the laptop change "
    "undone. **Workflow:** listed the pending orders with their items so the customer picked the "
    "right one to cancel; asked which payment method to use for the price difference (Visa, gift "
    'card or PayPal); showed the exact laptop change, refund card and "can\'t be changed again" '
    "in a popup before making it. In its 2 correct runs it first took the laptop change for an "
    "exchange on a delivered order and set that aside (a detour, not a wrong change). Its third "
    "run stopped with nothing changed: six model-output errors set the laptop change aside, then "
    "it offered to cancel three wrong orders one at a time and the customer declined each popup "
    "(safe only because the customer read them).",
    "34": "The customer ordered office and hiking items in one pending order; they want to cancel "
    "only the office items if that's possible, else re-address the order to NYC. **Baseline:** in "
    '2 of 3 runs offered what it can\'t do ("remove the office items… refund of $1,093.34"), sent '
    "a call that would have swapped the office items for the hiking ones (refused only because "
    "the counts differed), never mentioned the address change, and cancelled the whole $1,527.24 "
    "order, hiking gear included. **Workflow:** once re-addressed the order to NYC as asked (its "
    "model-worded question once floated removing items; never acted on). Twice it took 'cancel "
    "the office items' for an item change and only offered a whole-order cancel, which the "
    "customer declined in the popup: nothing changed, but the customer never reached the address "
    "change. Fixed before round 18: asked to cancel some items, the workflow now says a pending "
    "order can only be cancelled whole and what it can do instead (rounds 15–17 still count).",
}


# The verified failure in a few words: the end-state count alone misses wrong facts told.
# Workflow runs count from the round after the fix that addressed the task's failure (earlier
# rounds are still shown, as history). Default: every round.
COUNT_FROM_ROUND = {
    "2": 2,  # payment-by-name, item and early-stop fixes landed before round 2
    "72": 11,  # address-before-items queue fix landed before round 11
}

HOW_BASELINE_FAILS = {
    "2": "wrong t-shirt count or list in both valid runs; once said the items weren't in any "
    "order after opening 2 of 5, so no return",
    "4": "wrong fact told (t-shirt count) in 3 of 3 runs",
    "74": "cancelled the wrong order; chose the payment method itself; left a change undone",
    "72": "invented rules and talked the customer into cancelling the whole order",
    "99": "said 'cancel the skateboard, $202.13' but cancelled the whole $1,058.79 order (2 of 3); "
    "split or misdirected the exchange in all 3",
    "34": "offered an impossible 'remove items for a refund' (2 of 3), never offered the address "
    "change, cancelled the whole order incl. the items to keep",
}


def reviewed_out(path: Path, task_id: str) -> bool:
    return (
        task_id in REVIEWED_EXCLUSIONS or f"{path.parent.name}/{path.stem}" in REVIEWED_EXCLUSIONS
    )


def misread_popup(events: list[dict]) -> bool:
    """The harness turned a typed reply into the wrong popup button (an older reader did, e.g.
    "I need to correct this…" counted as yes): the run says nothing about the agent."""
    return any(e["type"] == "popup" and popup_answer(e["typed"]) != e["confirmed"] for e in events)


def outcome(events: list[dict]) -> str:
    s = events[-1]
    if s["status"] != "ok" or early_stop(events[:-1]) or misread_popup(events):
        return "excluded"
    if s["end_state_match"]:
        return "ok"
    wrote = [w for w in s["writes"] if w["op"] != "transfer_to_human_agents"]
    if not wrote:
        return "safe"
    expected = {
        (w["op"], w["args"].get("order_id") or w["args"].get("user_id"))
        for w in s["expected_writes"]
    }
    # A change of a kind, or to an order, the task never asked for is harmful; expected kinds
    # of change with something missing or a wrong detail (variant, reason) are incomplete.
    unexpected = [w for w in wrote if (w["op"], w["target"]) not in expected]
    return "harmful" if unexpected else "incomplete"


def runs(dirs: list[Path], task_id: str, agent: str) -> list[str]:
    out = []
    for d in dirs:
        for f in sorted(d.glob(f"{task_id}__{agent}__t*.jsonl")):
            events = [json.loads(line) for line in f.read_text().strip().splitlines()]
            out.append("excluded" if reviewed_out(f, task_id) else outcome(events))
    return out


def cell(results: list[str]) -> str:
    if not results:
        return "⏳ not run yet"
    valid = [r for r in results if r != "excluded"]
    marks = "".join(MARK[r] for r in results)
    return f"**{sum(r == 'ok' for r in valid)}/{len(valid)}** {marks}"


def valid_cell(results: list[str]) -> str:
    """Valid runs only; excluded ones are just counted (their reasons are in progress.md)."""
    valid = [r for r in results if r != "excluded"]
    excluded = len(results) - len(valid)
    marks = "".join(MARK[r] for r in valid)
    note = f" (+{excluded} excluded)" if excluded else ""
    return f"**{sum(r == 'ok' for r in valid)}/{len(valid)}** {marks}{note}"


def main() -> None:
    settings = get_settings()
    root = settings.var_dir / "eval"
    baseline_dirs = sorted(p for p in root.glob("pilot-baseline*") if p.is_dir())
    wf_dirs = sorted(
        (p for p in root.glob("wf-iter*") if p.is_dir()),
        key=lambda p: int(p.name.removeprefix("wf-iter")),
    )
    lines = [
        "# Pilot progress: baseline vs. workflow",
        "",
        f"_Updated {datetime.now():%Y-%m-%d %H:%M} by `python -m customer_workflow_agent.evalkit."
        "progress`._",
        "",
        "Baseline: plain tool-calling agent on Laguna XS 2.1, 3 runs per task. Workflow: this "
        "repo's agent on Nemotron 3.5 Lightning, latest iteration with fixes. Customer simulated "
        "by Laguna XS 2.1 from the τ²-bench scenario.",
        "",
        "✅ correct end state · 🔴 harmful (changed an order/thing never asked about) · "
        "🟠 incomplete or wrong detail · 🟡 safe failure (nothing changed) · ⚪ excluded "
        "(simulator ended early or server error) · counts are correct/valid runs. A failure goes "
        "in the pitch only after its transcript shows the agent, not the simulated customer, "
        "caused it.",
        "",
        "Workflow column: the latest fix round in bold, earlier rounds after it (each round "
        "includes the fixes made before it).",
        "",
        "| S.no | Task type (generic) | Task (τ²-bench id) | Baseline | Workflow | Status |",
        "|---|---|---|---|---|---|",
    ]
    for n, (tid, (kind, name)) in enumerate(TASKS.items(), start=1):
        rounds = [(d.name.removeprefix("wf-iter"), runs([d], tid, "workflow")) for d in wf_dirs]
        rounds = [(r, res) for r, res in rounds if res]
        wf = ""
        if rounds:
            latest, res = rounds[-1]
            history = " → ".join(f"r{r} {''.join(MARK[x] for x in res)}" for r, res in rounds[:-1])
            wf = f"{cell(res)} (round {latest})" + (f" · earlier: {history}" if history else "")
        status = f"⏹ stopped: {DROPPED[tid]}" if tid in DROPPED else "▶ active"
        lines.append(
            f"| {n} | {kind} | {name} ({tid}) | {cell(runs(baseline_dirs, tid, 'baseline'))} | "
            f"{wf or '⏳ not run yet'} | {status} |"
        )
    lines += ["", "## Notes", "", *[f"- {n}" for n in NOTES]]
    lines += [
        "",
        "## Runs excluded after transcript review (simulator off its script)",
        "",
        *[f"- `{k}`: {why}" for k, why in REVIEWED_EXCLUSIONS.items()],
    ]
    out = settings.data_dir.parent / "docs" / "pitch" / "progress.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out}")
    write_verified(out.parent / "verified-tasks.md", baseline_dirs, wf_dirs)


def label(wf_valid: list[str]) -> str | None:
    """'verified': right at least twice; 'safe': right at least once. Either way at least 2 valid
    runs and never a harmful or wrong change; the other runs stopped with nothing changed."""
    done = sum(r == "ok" for r in wf_valid)
    if len(wf_valid) < 2 or not done or any(r in ("harmful", "incomplete") for r in wf_valid):
        return None
    return "verified" if done >= 2 else "safe"


def write_verified(out: Path, baseline_dirs: list[Path], wf_dirs: list[Path]) -> None:
    """Only the tasks that passed both checks, with what happened on each side."""
    head = [
        "| S.no | Task type (generic) | Task (τ²-bench id) | Description | How the baseline fails "
        "| Baseline end state | Workflow end state |",
        "|---|---|---|---|---|---|---|",
    ]
    rows: dict[str, list[str]] = {"verified": [], "safe": []}
    for tid, desc in VERIFIED.items():
        start = COUNT_FROM_ROUND.get(tid, 1)
        counted = [d for d in wf_dirs if int(d.name.removeprefix("wf-iter")) >= start]
        earlier = [d for d in wf_dirs if int(d.name.removeprefix("wf-iter")) < start]
        wf = [r for d in counted for r in runs([d], tid, "workflow")]
        tier = label([r for r in wf if r != "excluded"])
        if tier is None:
            continue  # not proven yet: stays in progress.md only
        kind, name = TASKS[tid]
        base = runs(baseline_dirs, tid, "baseline")
        before = "".join(MARK[r] for d in earlier for r in runs([d], tid, "workflow"))
        history = f" · before the fix (rounds < {start}): {before}" if before else ""
        rows[tier].append(
            f"| {len(rows[tier]) + 1} | {kind} | {name} ({tid}) | {desc} | "
            f"{HOW_BASELINE_FAILS[tid]} | {valid_cell(base)} | {valid_cell(wf)}{history} |"
        )
    none = ["| — | — | None yet. | | | | |"]
    lines = [
        "# Verified tasks: the baseline fails, the workflow works",
        "",
        f"_Updated {datetime.now():%Y-%m-%d %H:%M}; generated with progress.md._",
        "",
        "Each task passed two checks: (1) the baseline fails in runs whose transcripts show the "
        "agent's own decision caused it (not the simulated customer going off script); (2) in at "
        "least 2 valid workflow runs, whose transcripts were read, the workflow never made a "
        "harmful or wrong change. **Verified** means it also got the task right at least twice; "
        "**safe, fix pending** means right at least once, its other runs stopping with nothing "
        "changed, for a cause with a known fix. Only valid runs are shown; runs excluded for a "
        "documented reason (simulated customer off script, harness error) are counted and listed "
        "in progress.md. Where a workflow fix addressed a task's failure, its runs count from the "
        "round after that fix; the earlier rounds are shown after the count.",
        "",
        "## Verified",
        "",
        *head,
        *(rows["verified"] or none),
        "",
        "## Safe, fix pending",
        "",
        *head,
        *(rows["safe"] or none),
    ]
    out.write_text("\n".join(lines) + "\n")


if __name__ == "__main__":
    main()
