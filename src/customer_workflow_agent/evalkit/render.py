"""Turn a conversation log into a chat-style page and a PNG for the slides.

    python -m customer_workflow_agent.evalkit.render var/eval/<run>/<case>__<agent>__t1.jsonl \
        --highlight 7,8 --title "Task 72: address change lost" --out docs/pitch/img/72-baseline.png
    python -m customer_workflow_agent.evalkit.render --tau2 <sim_id> --out docs/pitch/img/72-top.png

Customer messages sit on the right, the agent's on the left; the agent's tool calls (baseline) and
the confirmation popups (workflow) appear between them, so what the customer was told sits next to
what actually ran. `--highlight` takes event numbers (shown on the page) to outline in red.
"""

import argparse
import html
import json
import math
import subprocess
import tempfile
from pathlib import Path

from customer_workflow_agent.baseline.tools import WRITE_TOOLS
from customer_workflow_agent.evalkit.tau2_logs import FILES
from customer_workflow_agent.settings import get_settings

CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
WIDTH = 1100
CSS = """
body { font: 15px/1.45 -apple-system, "Segoe UI", Helvetica, Arial, sans-serif; margin: 0;
       background: #f6f5f2; color: #1d1d1b; }
.wrap { padding: 22px 28px; }
h1 { font-size: 19px; margin: 0 0 4px; }
.sub { color: #6b6a66; font-size: 13px; margin-bottom: 14px; }
.row { display: flex; margin: 7px 0; align-items: flex-start; gap: 8px; }
.n { width: 26px; color: #9a988f; font-size: 11px; padding-top: 9px; text-align: right;
     flex: none; }
.msg { max-width: 760px; padding: 9px 13px; border-radius: 12px; white-space: pre-wrap; }
.agent .msg { background: #ffffff; border: 1px solid #e2e0da; }
.customer { flex-direction: row-reverse; } .customer .msg { background: #dbe8ff; }
.who { font-size: 11px; color: #6b6a66; margin-bottom: 2px; }
.tool .msg, .popup .msg { font: 12.5px/1.4 ui-monospace, Menlo, monospace; background: #f0efe9;
       border: 1px dashed #c9c6bc; max-width: 900px; }
.tool.write .msg { background: #fff3d6; border: 1px solid #e3b341; }
.tool.err .msg { background: #fde4e1; border: 1px solid #d9534f; }
.popup .msg { background: #e6f4ea; border: 1px solid #5aa469; }
.hl .msg { outline: 3px solid #d62728; outline-offset: 2px; }
"""


def _lines(text: str, per_line: int = 95) -> int:
    return sum(max(1, math.ceil(len(part) / per_line)) for part in text.split("\n"))


def from_ours(path: Path) -> tuple[list[dict], dict]:
    events = [json.loads(line) for line in path.read_text().splitlines() if line.strip()]
    summary = next(e for e in events if e["type"] == "summary")
    rows = []
    for e in events:
        if e["type"] in ("agent", "customer"):
            rows.append({"kind": e["type"], "text": e["text"]})
        elif e["type"] == "tool":
            args = json.dumps(e["arguments"])
            rows.append(
                {
                    "kind": "tool",
                    "write": e["write"],
                    "error": e["error"],
                    "text": f"{e['name']}({args})\n→ {e['result'][:240]}",
                }
            )
        elif e["type"] == "popup":
            s = e["summary"]
            text = "\n".join(
                [
                    f"[Popup] {s['title']}",
                    *s["lines"],
                    f"customer typed: {e['typed']!r} → {'YES' if e['confirmed'] else 'NO'}",
                ]
            )
            rows.append({"kind": "popup", "text": text})
    ok = "matches" if summary["end_state_match"] else "does NOT match"
    sub = (
        f"{summary['agent']} agent · model {summary['model']} · trial {summary['trial']} · "
        f"store {ok} the expected end state"
    )
    return rows, {"sub": sub}


def from_tau2(sim_id: str) -> tuple[list[dict], dict]:
    folder = get_settings().var_dir / "tau2-results"
    for model, name in FILES.items():
        sims = json.loads((folder / name).read_text())["simulations"]
        sim = next((s for s in sims if s["id"] == sim_id), None)
        if sim is None:
            continue
        rows = []
        for m in sim["messages"]:
            if m["role"] == "user" and m.get("content"):
                rows.append({"kind": "customer", "text": m["content"]})
            elif m["role"] == "assistant":
                if m.get("content"):
                    rows.append({"kind": "agent", "text": m["content"]})
                for c in m.get("tool_calls") or []:
                    rows.append(
                        {
                            "kind": "tool",
                            "write": c["name"] in WRITE_TOOLS,
                            "error": False,
                            "text": f"{c['name']}({json.dumps(c['arguments'])})",
                        }
                    )
            elif m["role"] == "tool" and str(m.get("content", "")).startswith("Error") and rows:
                rows[-1]["error"] = True
                rows[-1]["text"] += f"\n→ {m['content'][:200]}"
        reward = (sim["reward_info"] or {}).get("reward", 0)
        sub = (
            f"τ²-bench published run · agent {model} · customer GPT-4.1 · task {sim['task_id']} · "
            f"trial {sim.get('trial')} · reward {reward:.0f}"
        )
        return rows, {"sub": sub}
    raise SystemExit(f"simulation {sim_id} not found in {folder}")


def page(rows: list[dict], title: str, sub: str, highlight: set[int], start: int, end: int) -> str:
    out = [
        f"<html><head><meta charset='utf-8'><style>{CSS}</style></head><body><div class='wrap'>",
        f"<h1>{html.escape(title)}</h1><div class='sub'>{html.escape(sub)}</div>",
    ]
    for i, r in enumerate(rows, 1):
        if not start <= i <= end:
            continue
        cls = [r["kind"]]
        if r.get("write"):
            cls.append("write")
        if r.get("error"):
            cls.append("err")
        if i in highlight:
            cls.append("hl")
        who = {"agent": "Agent", "customer": "Customer"}.get(r["kind"], "")
        label = f"<div class='who'>{who}</div>" if who else ""
        out.append(
            f"<div class='row {' '.join(cls)}'><div class='n'>{i}</div>"
            f"<div>{label}<div class='msg'>{html.escape(r['text'])}</div></div></div>"
        )
    return "\n".join([*out, "</div></body></html>"])


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("log", nargs="?", help="our conversation .jsonl")
    p.add_argument("--tau2", help="a τ²-bench simulation id instead of our log")
    p.add_argument("--title", default="")
    p.add_argument("--highlight", default="", help="event numbers to outline, e.g. 7,8")
    p.add_argument("--range", default="", help="only events from-to, e.g. 5-14")
    p.add_argument("--out", required=True, help=".png (an .html is written next to it)")
    args = p.parse_args()
    rows, info = from_tau2(args.tau2) if args.tau2 else from_ours(Path(args.log))
    highlight = {int(x) for x in args.highlight.split(",") if x}
    start, end = (int(x) for x in args.range.split("-")) if args.range else (1, len(rows))
    doc = page(rows, args.title, info["sub"], highlight, start, end)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.with_suffix(".html").write_text(doc)
    shown = rows[start - 1 : end]
    height = 110 + sum(30 + 21 * _lines(r["text"]) for r in shown)
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                CHROME,
                "--headless=new",
                "--disable-gpu",
                "--hide-scrollbars",
                f"--user-data-dir={tmp}",
                f"--window-size={WIDTH},{height}",
                f"--screenshot={out.resolve()}",
                out.with_suffix(".html").resolve().as_uri(),
            ],
            check=True,
            capture_output=True,
        )
    print(f"wrote {out} ({len(shown)} events)")


if __name__ == "__main__":
    main()
