"""Run τ²-bench tasks with the simulated customer against the baseline.

    python -m agent.evaluation.run_tasks --cases 99,74,2 \
        --model poolside/laguna-xs-2.1 --user-model poolside/laguna-xs-2.1 --trials 3

Each conversation starts from a fresh copy of the store and is written to
`var/eval/<run>/<case>__<agent>__t<k>.jsonl` (one event per line, then a summary line). The
summary says whether the store ended where τ²-bench's expected actions leave it, and which writes
the agent made.
"""

import argparse
import asyncio
import csv
import json
import time
import traceback
import uuid
from datetime import datetime
from functools import cache
from pathlib import Path

from langchain_core.rate_limiters import InMemoryRateLimiter

from agent.baseline.agent import FIRST_MESSAGE, BaselineAgent
from agent.baseline.model_client import InfraError
from agent.evaluation.grader import (
    db_state,
    expected_db,
    grade_run_dir,
    load_db,
    load_tasks,
    write_actions,
)
from agent.evaluation.simulated_customer import CustomerSimulator, stop_reason
from agent.settings import Settings, get_settings
from agent.store import InMemoryBackend, RetailStore


@cache
def expected_for(task_id: str) -> dict:
    return expected_db(load_tasks()[task_id], load_db())


def mismatch(final: dict, expected: dict) -> dict:
    """Which orders and users differ from the expected end state."""
    out = {}
    for kind in ("orders", "users"):
        keys = sorted(
            k
            for k in set(final[kind]) | set(expected[kind])
            if final[kind].get(k) != expected[kind].get(k)
        )
        if keys:
            out[kind] = keys
    return out


async def run_conversation(
    task: dict,
    agent_kind: str,
    trial: int,
    args: argparse.Namespace,
    settings: Settings,
    limiter: InMemoryRateLimiter,
    out_dir: Path,
) -> dict:
    conv_id = f"{task['id']}-{agent_kind}-t{trial}-{uuid.uuid4().hex[:6]}"
    store = RetailStore(InMemoryBackend(load_db()))
    events: list[dict] = []
    started = time.monotonic()

    def log(kind: str, **data) -> None:
        events.append({"type": kind, "t": round(time.monotonic() - started, 2), **data})

    meta = {
        "task_id": task["id"],
        "agent": agent_kind,
        "model": args.model,
        "user_model": args.user_model,
        "trial": trial,
    }
    log("meta", conv_id=conv_id, **meta)
    sim = CustomerSimulator(task, settings, limiter, args.user_model)
    status, termination, agent = "ok", "max_turns", None
    try:
        agent = BaselineAgent(store, settings, limiter, args.model)
        agent_text = FIRST_MESSAGE
        log("agent", text=agent_text)
        seen_calls = 0
        for _ in range(args.max_turns):
            customer = await sim.next_message(agent_text)
            log("customer", text=customer)
            reason = stop_reason(customer)
            said = customer.replace(reason, "").strip() if reason else customer
            # A simulated customer sometimes says "Yes, please proceed ###STOP###" in one
            # message. τ²-bench ends there; we let the agent act on that last message first,
            # so the run isn't lost to the simulator's timing.
            if reason and not (reason == "###STOP###" and len(said.split()) >= 3):
                termination = reason
                break
            agent_text, stuck = await agent.reply(said)
            for c in agent.tools.calls[seen_calls:]:
                log(
                    "tool",
                    name=c.name,
                    arguments=c.arguments,
                    result=c.result[:2000],
                    error=c.error,
                    write=c.write,
                )
            seen_calls = len(agent.tools.calls)
            log("agent", text=agent_text)
            if reason:
                termination = f"{reason} (after acting on last message)"
                break
            if stuck:
                termination = "agent_step_cap"
                break
    except InfraError as e:
        status = "infra_error"
        log("error", error=str(e))
    except Exception as e:  # a crash in our code or the agent: keep the transcript for review
        status = "crash"
        log("error", error=f"{type(e).__name__}: {e}", traceback=traceback.format_exc())

    summary = build_summary(
        task,
        meta,
        conv_id,
        status,
        termination,
        store,
        events,
        llm_calls_agent=getattr(agent, "llm_calls", None),
        llm_calls_customer=sim.llm_calls,
        seconds=time.monotonic() - started,
    )
    path = out_dir / f"{task['id']}__{agent_kind}__t{trial}.jsonl"
    path.write_text("\n".join(json.dumps(e, default=str) for e in [*events, summary]) + "\n")
    return summary


def build_summary(
    task: dict,
    meta: dict,
    conv_id: str,
    status: str,
    termination: str,
    store: RetailStore,
    events: list[dict],
    *,
    llm_calls_agent: int | None,
    llm_calls_customer: int | None,
    seconds: float,
) -> dict:
    """The last line of a conversation log: how it ended and where the store ended up. Shared
    by simulated runs and by the human-testing UI, so both logs grade the same way."""
    final = db_state(store)
    expected = expected_for(task["id"])
    writes = [
        {"op": r.op, "target": r.target_id}
        for r in store._db.ledger.values()
        if r.op != "block_returns"
    ]
    return {
        "type": "summary",
        **meta,
        "conv_id": conv_id,
        "status": status,
        "termination": termination,
        "end_state_match": final == expected,
        "mismatch": mismatch(final, expected),
        "writes": writes,
        "expected_writes": [{"op": a["name"], "args": a["arguments"]} for a in write_actions(task)],
        "customer_turns": sum(1 for e in events if e["type"] == "customer"),
        "llm_calls_agent": llm_calls_agent,
        "llm_calls_customer": llm_calls_customer,
        "seconds": round(seconds, 1),
    }


async def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    limiter = InMemoryRateLimiter(
        requests_per_second=args.rpm / 60, check_every_n_seconds=0.1, max_bucket_size=4
    )
    run = args.run or datetime.now().strftime("%Y%m%d-%H%M%S")
    out_dir = settings.var_dir / "eval" / run
    out_dir.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks()
    jobs = [
        (tasks[c], a, t)
        for c in args.cases.split(",")
        for a in args.agents.split(",")
        for t in range(1, args.trials + 1)
    ]
    sem = asyncio.Semaphore(args.concurrency)

    async def one(task, agent_kind, trial):
        async with sem:
            s = await run_conversation(task, agent_kind, trial, args, settings, limiter, out_dir)
            if s["status"] == "infra_error" and args.retry_infra:
                s = await run_conversation(
                    task, agent_kind, trial, args, settings, limiter, out_dir
                )
            print(
                f"task {s['task_id']:>4} {s['agent']:<8} t{s['trial']} {s['status']:<11} "
                f"{s['termination']:<16} match={s['end_state_match']!s:<5} "
                f"turns={s['customer_turns']:<3} {s['seconds']}s "
                f"writes={[w['op'] for w in s['writes']]}",
                flush=True,
            )
            return s

    summaries = await asyncio.gather(*(one(*j) for j in jobs))
    with (out_dir / "summary.csv").open("w", newline="") as f:
        cols = [
            "task_id",
            "agent",
            "trial",
            "status",
            "termination",
            "end_state_match",
            "customer_turns",
            "seconds",
            "conv_id",
        ]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(summaries)
    print(f"\nwrote {len(summaries)} conversations to {out_dir}")
    graded = grade_run_dir(out_dir)
    print(f"graded {len(graded)} conversations -> {out_dir / 'grades.csv'}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--cases", required=True, help="comma-separated τ²-bench task ids")
    p.add_argument("--agents", default="baseline")
    p.add_argument("--model", required=True, help="NIM model id for the agent (both agents)")
    p.add_argument("--user-model", required=True, help="NIM model id for the simulated customer")
    p.add_argument("--trials", type=int, default=1)
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--rpm", type=float, default=35, help="requests per minute across all calls")
    p.add_argument("--max-turns", type=int, default=30, help="customer messages per conversation")
    p.add_argument("--retry-infra", action=argparse.BooleanOptionalAction, default=True)
    p.add_argument("--run", help="run name (default: timestamp)")
    return p.parse_args(argv)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
