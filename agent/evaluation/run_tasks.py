r"""Run τ²-bench tasks with the simulated customer against the baseline.

    python -m agent.evaluation.run_tasks --cases 19 --trials 5 --out test_cases \
        --model poolside/laguna-xs-2.1 --user-model poolside/laguna-xs-2.1

Each conversation starts from a fresh copy of the store and writes one folder,
`<out>/case-<task>/runs/run-<n>/`, with `trajectory.json`, `reward.json` and `config.json`
(see `agent/evaluation/outputs.py`). Run numbers continue from the folders already there, filling
gaps first, so deleting an invalid run and running `--trials 1` again replaces it.
Without `--out`, folders go to `var/eval/<timestamp>/` (not tracked by git).
"""

import argparse
import asyncio
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

from langchain_core.rate_limiters import InMemoryRateLimiter

from agent.baseline.agent import FIRST_MESSAGE, BaselineAgent
from agent.baseline.model_client import InfraError
from agent.evaluation.grader import db_state, load_db, load_tasks
from agent.evaluation.outputs import next_run_numbers, notes, run_folder, write_run
from agent.evaluation.simulated_customer import OPENERS, CustomerSimulator, stop_reason
from agent.settings import Settings, get_settings
from agent.store import InMemoryBackend, RetailStore


def summary_event(
    status: str,
    termination: str,
    *,
    llm_calls_agent: int | None,
    llm_calls_customer: int | None,
    seconds: float,
) -> dict:
    """How a conversation ended, as the grader reads it. Shared with the user-testing UI."""
    return {
        "type": "summary",
        "status": status,
        "termination": termination,
        "llm_calls_agent": llm_calls_agent,
        "llm_calls_customer": llm_calls_customer,
        "seconds": round(seconds, 1),
    }


async def run_conversation(
    task: dict,
    n: int,
    args: argparse.Namespace,
    settings: Settings,
    limiter: InMemoryRateLimiter,
) -> tuple[dict, list[dict], dict]:
    """One conversation. Returns its summary, its events and the store's final state."""
    conv_id = f"{task['id']}-baseline-run{n}-{uuid.uuid4().hex[:6]}"
    store = RetailStore(InMemoryBackend(load_db()))
    events: list[dict] = []
    started = time.monotonic()

    def log(kind: str, **data) -> None:
        events.append({"type": kind, "t": round(time.monotonic() - started, 2), **data})

    log(
        "meta",
        conv_id=conv_id,
        started_at=datetime.now().isoformat(),
        task_id=task["id"],
        agent="baseline",
        mode="simulated",
        model=args.model,
        user_model=args.user_model,
        trial=n,
        settings={
            "max_turns": args.max_turns,
            "rpm": args.rpm,
            "fixed_first_message": OPENERS.get(task["id"]),
        },
    )
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

    summary = summary_event(
        status,
        termination,
        llm_calls_agent=getattr(agent, "llm_calls", None),
        llm_calls_customer=sim.llm_calls,
        seconds=time.monotonic() - started,
    )
    events.append(summary)
    return summary, events, db_state(store)


async def main(args: argparse.Namespace) -> None:
    settings = get_settings()
    limiter = InMemoryRateLimiter(
        requests_per_second=args.rpm / 60, check_every_n_seconds=0.1, max_bucket_size=4
    )
    out = args.out or settings.var_dir / "eval" / datetime.now().strftime("%Y%m%d-%H%M%S")
    tasks = load_tasks()
    # Run numbers are chosen up front, so concurrent runs never pick the same folder.
    jobs = [
        (tasks[c], n) for c in args.cases.split(",") for n in next_run_numbers(out, c, args.trials)
    ]
    sem = asyncio.Semaphore(args.concurrency)

    async def one(task: dict, n: int) -> None:
        async with sem:
            summary, events, final = await run_conversation(task, n, args, settings, limiter)
            if summary["status"] == "infra_error" and args.retry_infra:
                summary, events, final = await run_conversation(task, n, args, settings, limiter)
            folder = run_folder(out, task["id"], n)
            g = write_run(folder, task, events, final)
            print(
                f"{folder}: {g['verdict']} (end state match={g['end_state_match']}, "
                f"{summary['termination']}, {g['customer_turns']} turns, {summary['seconds']}s)"
                f"\n    {notes(g) or 'no findings'}",
                flush=True,
            )

    await asyncio.gather(*(one(*j) for j in jobs))


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--cases", required=True, help="comma-separated τ²-bench task ids")
    p.add_argument("--model", required=True, help="NIM model id for the agent")
    p.add_argument("--user-model", required=True, help="NIM model id for the simulated customer")
    p.add_argument("--trials", type=int, default=1, help="runs per case")
    p.add_argument("--out", type=Path, help="root of the case folders (e.g. test_cases)")
    p.add_argument("--concurrency", type=int, default=3)
    p.add_argument("--rpm", type=float, default=35, help="requests per minute across all calls")
    p.add_argument("--max-turns", type=int, default=30, help="customer messages per conversation")
    p.add_argument("--retry-infra", action=argparse.BooleanOptionalAction, default=True)
    return p.parse_args(argv)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
