"""What τ²-bench's published top-model runs show: which retail tasks they fail, and how.

    python -m customer_workflow_agent.evalkit.tau2_logs

Reads τ²-bench's published retail results (4 trials per task; GPT-4.1 playing the customer) from
`var/tau2-results/` (downloaded once from the τ²-bench repo; untrusted data, parsed as JSON only),
and writes `docs/pitch/top-model-failures.md` plus `var/tau2-results/failures.json`.
"""

import json
import re
import urllib.request
from collections import Counter, defaultdict
from pathlib import Path

from customer_workflow_agent.baseline.tools import WRITE_TOOLS
from customer_workflow_agent.evalkit.replay import load_tasks, write_actions
from customer_workflow_agent.settings import get_settings

BASE = "https://raw.githubusercontent.com/sierra-research/tau2-bench/main/data/tau2/results/final/"
_USER = "gpt-4.1-2025-04-14_4trials.json"  # every run used GPT-4.1 as the customer
FILES = {
    "claude-3.7-sonnet": f"claude-3-7-sonnet-20250219_retail_default_{_USER}",
    "gpt-4.1": f"gpt-4.1-2025-04-14_retail_default_{_USER}",
    "o4-mini": f"o4-mini-2025-04-16_retail_default_{_USER}",
    "gpt-4.1-mini": f"gpt-4.1-mini-2025-04-14_retail_base_{_USER}",
}
TOP = ("claude-3.7-sonnet", "gpt-4.1", "o4-mini")
AFFIRM = re.compile(
    r"\b(yes|yeah|yep|confirm|correct|go ahead|proceed|please do|sure|ok(ay)?|sounds good)\b", re.I
)


def load(model: str, folder: Path) -> dict:
    path = folder / FILES[model]
    if not path.exists():
        folder.mkdir(parents=True, exist_ok=True)
        urllib.request.urlretrieve(BASE + FILES[model], path)
    return json.loads(path.read_text())


def agent_writes(messages: list[dict]) -> list[dict]:
    """The agent's write calls, each with its result and the customer's last message before it."""
    results = {m.get("id"): m.get("content") for m in messages if m["role"] == "tool"}
    out, last_customer = [], ""
    for i, m in enumerate(messages):
        if m["role"] == "user" and m.get("content"):
            last_customer = m["content"]
        for call in m.get("tool_calls") or []:
            if m["role"] == "assistant" and call["name"] in WRITE_TOOLS:
                result = results.get(call.get("id"))
                if result is None:  # older files: the tool message follows the call
                    result = next(
                        (x.get("content") for x in messages[i + 1 :] if x["role"] == "tool"), ""
                    )
                out.append(
                    {
                        "name": call["name"],
                        "arguments": call["arguments"],
                        "error": str(result or "").startswith("Error"),
                        "result": str(result or "")[:300],
                        "customer_before": last_customer[:300],
                    }
                )
    return out


def failure_modes(sim: dict, gold: list[dict]) -> list[str]:
    """How a failing run differs from the expected writes (several can apply)."""
    done = [w for w in agent_writes(sim["messages"]) if not w["error"]]
    modes = []
    gold_names, done_names = Counter(a["name"] for a in gold), Counter(w["name"] for w in done)
    for w in agent_writes(sim["messages"]):
        if w["error"]:
            modes.append(f"write rejected: {w['name']}")
        elif w["name"] != "transfer_to_human_agents" and not AFFIRM.search(w["customer_before"]):
            modes.append("write without the customer's yes")
    for name in gold_names - done_names:
        modes.append(f"missing: {name}")
    for name in done_names - gold_names:
        modes.append(f"extra: {name}")
    for g in gold:
        same = [w for w in done if w["name"] == g["name"]]
        if same and g["arguments"] not in [w["arguments"] for w in same]:
            closest = same[0]["arguments"]
            keys = sorted(k for k in g["arguments"] if g["arguments"].get(k) != closest.get(k))
            modes.append(f"wrong args: {g['name']} ({', '.join(keys)})")
    comm = sim["reward_info"].get("communicate_checks") or []
    if any(not c.get("met", True) for c in comm):
        modes.append("didn't tell the customer required info")
    if not gold and not done:
        modes.append("no write expected; failed on communication/assertions")
    return modes or [f"other ({sim.get('termination_reason')})"]


def main() -> None:
    settings = get_settings()
    folder = settings.var_dir / "tau2-results"
    tasks = load_tasks()
    passes: dict[str, dict[str, list[int]]] = defaultdict(dict)
    failures: dict[str, list[dict]] = defaultdict(list)
    overall = {}
    for model in FILES:
        sims = load(model, folder)["simulations"]
        wins = [1 if (s["reward_info"] or {}).get("reward", 0) >= 0.999 else 0 for s in sims]
        overall[model] = sum(wins) / len(wins)
        for s, win in zip(sims, wins, strict=True):
            tid = str(s["task_id"])
            passes[tid].setdefault(model, []).append(win)
            if not win and model in TOP:
                gold = write_actions(tasks[tid])
                failures[tid].append(
                    {
                        "model": model,
                        "trial": s.get("trial"),
                        "sim_id": s["id"],
                        "termination": s.get("termination_reason"),
                        "modes": failure_modes(s, gold),
                        "writes": agent_writes(s["messages"]),
                    }
                )

    def fail_rate(tid: str) -> float:
        runs = [x for m in TOP for x in passes[tid].get(m, [])]
        return 1 - sum(runs) / len(runs)

    ranked = sorted(passes, key=lambda t: (-fail_rate(t), int(t)))
    (folder / "failures.json").write_text(json.dumps(failures, indent=1))

    lines = [
        "# Where top models fail on τ²-bench retail",
        "",
        "Source: τ²-bench's published results (`data/tau2/results/final/`), 4 trials per task, "
        "GPT-4.1 playing the customer. Generated by `python -m customer_workflow_agent.evalkit."
        "tau2_logs`.",
        "",
        "Overall pass rate: " + ", ".join(f"{m} {overall[m]:.2f}" for m in FILES),
        "",
        "## Tasks the top models fail most (Claude 3.7 Sonnet, GPT-4.1, o4-mini)",
        "",
        "| Task | Fail rate | "
        + " | ".join(FILES)
        + " | How they fail (count over failing runs) |",
        "|---|---|" + "---|" * len(FILES) + "---|",
    ]
    for tid in ranked:
        if fail_rate(tid) < 1 / 3:
            break
        modes = Counter(m for f in failures[tid] for m in set(f["modes"]))
        how = "; ".join(f"{m} ×{n}" for m, n in modes.most_common(4))
        cells = " | ".join(
            f"{sum(passes[tid].get(m, []))}/{len(passes[tid].get(m, []))}" for m in FILES
        )
        lines.append(f"| {tid} | {fail_rate(tid):.0%} | {cells} | {how} |")

    lines += ["", "## Expected vs. actual writes in one failing run per task", ""]
    for tid in ranked:
        if fail_rate(tid) < 1 / 3:
            break
        f = failures[tid][0]
        reason = tasks[tid]["user_scenario"]["instructions"]["reason_for_call"]
        lines += [
            f"### Task {tid} — {f['model']}, trial {f['trial']} (`{f['sim_id']}`)",
            f"*Customer's goal:* {reason[:400]}",
            "",
            "Expected: "
            + "; ".join(
                f"`{a['name']}` {json.dumps(a['arguments'])}" for a in write_actions(tasks[tid])
            )
            or "no writes",
            "",
            "Actual: "
            + (
                "; ".join(
                    f"`{w['name']}` {json.dumps(w['arguments'])}"
                    + (" (rejected)" if w["error"] else "")
                    for w in f["writes"]
                )
                or "no writes"
            ),
            "",
            "Modes: " + ", ".join(f["modes"]),
            "",
        ]
    out = settings.data_dir.parent / "docs" / "pitch" / "top-model-failures.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out} and {folder / 'failures.json'}")
    for m in FILES:
        print(f"{m}: pass^1 {overall[m]:.2f}")


if __name__ == "__main__":
    main()
