"""Per-task summary of our runs next to τ²-bench's published top-model pass rates.

    python -m customer_workflow_agent.evalkit.findings var/eval/<run> [var/eval/<run2> ...]

Prints a markdown table: for each task and agent, how many runs ended in the expected store state,
how they ended, and which writes they made. Runs that failed on the model API (`infra_error`) are
counted separately, never as the agent's failure.
"""

import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

from customer_workflow_agent.evalkit.simulator import stop_reason
from customer_workflow_agent.evalkit.tau2_logs import FILES, TOP
from customer_workflow_agent.settings import get_settings

YES = re.compile(r"\b(yes|proceed|go ahead|confirm|please do)\b", re.I)
ASKED = re.compile(r"\b(confirm|proceed|yes|go ahead|would you like me to)\b", re.I)


def top_model_passes() -> dict[str, str]:
    folder = get_settings().var_dir / "tau2-results"
    wins: dict[str, list[int]] = defaultdict(list)
    for model in TOP:
        path = folder / FILES[model]
        if not path.exists():
            return {}
        for s in json.loads(path.read_text())["simulations"]:
            wins[str(s["task_id"])].append(int((s["reward_info"] or {}).get("reward", 0) >= 0.999))
    return {t: f"{sum(w)}/{len(w)}" for t, w in wins.items()}


def early_stop(events: list[dict]) -> bool:
    """The simulated customer ended the chat in the same message as an answer ("Yes, go ahead
    ###STOP###") and the agent never got to act on it: the simulator's slip, not the agent's."""
    if not events or events[-1]["type"] != "customer":
        return False
    last = events[-1]["text"]
    if stop_reason(last) != "###STOP###" or not YES.search(last):
        return False
    agent = next((e["text"] for e in reversed(events) if e["type"] == "agent"), "")
    return bool(ASKED.search(agent))


def summaries(run_dirs: list[Path]) -> list[dict]:
    out = []
    for d in run_dirs:
        for f in sorted(d.glob("*.jsonl")):
            events = [json.loads(line) for line in f.read_text().strip().splitlines()]
            s = events[-1]
            s["file"] = str(f)
            s["early_stop"] = early_stop(events[:-1])
            out.append(s)
    return out


def main(argv: list[str]) -> None:
    rows: dict[tuple[str, str, str], list[dict]] = defaultdict(list)
    for s in summaries([Path(a) for a in argv]):
        rows[(s["task_id"], s["agent"], s["model"])].append(s)
    top = top_model_passes()
    print(
        "| Task | Top models pass | Agent | Model | Correct (valid runs) | Sim early stop / infra "
        "| Endings | Writes |"
    )
    print("|---|---|---|---|---|---|---|---|")
    for (tid, agent, model), runs in sorted(
        rows.items(), key=lambda kv: (int(kv[0][0]), kv[0][1:])
    ):
        ok = [r for r in runs if r["status"] == "ok" and not r["early_stop"]]
        endings = Counter(r["termination"] for r in ok)
        writes = Counter(",".join(w["op"] for w in r["writes"]) or "none" for r in ok)
        print(
            f"| {tid} | {top.get(tid, '?')} | {agent} | {model.split('/')[-1]} | "
            f"{sum(r['end_state_match'] for r in ok)}/{len(ok)} | "
            f"{sum(r['early_stop'] for r in runs)} / {sum(r['status'] != 'ok' for r in runs)} | "
            f"{', '.join(f'{k} ×{v}' for k, v in endings.items())} | "
            f"{'; '.join(f'{k} ×{v}' for k, v in writes.items())} |"
        )


if __name__ == "__main__":
    main(sys.argv[1:])
