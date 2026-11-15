"""A barebones web page for user testing: a person plays the customer and chats with the
baseline agent on one τ²-bench task.

    python -m agent.ui.backend.server                      # http://127.0.0.1:8000
    python -m agent.ui.backend.server --port 8001 --model poolside/laguna-xs-2.1

The page itself lives in `agent/ui/frontend/` and is served as static files.

Each session gets a fresh store. The person talks to the agent exactly as the simulated customer
does: their message goes to `BaselineAgent.reply`, and the agent's reply comes back. When the
session ends, it writes the same run folder as a simulated run (`trajectory.json`,
`reward.json`, `config.json`, with mode "human") to
`var/eval/user-testing-<date>/case-<task>/runs/run-<n>/`.
"""

import argparse
import time
import traceback
import uuid
from datetime import datetime
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from langchain_core.rate_limiters import InMemoryRateLimiter
from pydantic import BaseModel

from agent.baseline.agent import FIRST_MESSAGE, BaselineAgent
from agent.baseline.model_client import InfraError
from agent.evaluation.grader import db_state, load_db, load_tasks
from agent.evaluation.outputs import next_run_numbers, notes, run_folder, write_run
from agent.evaluation.run_tasks import summary_event
from agent.settings import get_settings
from agent.store import InMemoryBackend, RetailStore

FRONTEND = Path(__file__).resolve().parents[1] / "frontend"
MODEL = "poolside/laguna-xs-2.1"

app = FastAPI(title="Customer agent: user testing")
app.state.model = MODEL
settings = get_settings()
limiter = InMemoryRateLimiter(requests_per_second=35 / 60, check_every_n_seconds=0.1)
sessions: dict[str, "Session"] = {}


class Session:
    def __init__(self, task: dict, model: str):
        self.task = task
        self.id = uuid.uuid4().hex[:8]
        self.conv_id = f"{task['id']}-baseline-human-{self.id}"
        self.store = RetailStore(InMemoryBackend(load_db()))
        self.agent = BaselineAgent(self.store, settings, limiter, model)
        self.started = time.monotonic()
        self.events: list[dict] = []
        self.seen_calls = 0
        self.status = "ok"
        self.ended = False
        self.meta = {
            "task_id": task["id"],
            "agent": "baseline",
            "mode": "human",
            "model": model,
            "user_model": "human",
            "trial": None,
        }
        self.log("meta", conv_id=self.conv_id, started_at=datetime.now().isoformat(), **self.meta)
        self.log("agent", text=FIRST_MESSAGE)

    def log(self, kind: str, **data) -> None:
        self.events.append({"type": kind, "t": round(time.monotonic() - self.started, 2), **data})

    def new_tool_calls(self) -> list[dict]:
        calls = []
        for c in self.agent.tools.calls[self.seen_calls :]:
            call = {
                "name": c.name,
                "arguments": c.arguments,
                "result": c.result[:2000],
                "error": c.error,
                "write": c.write,
            }
            self.log("tool", **call)
            calls.append(call)
        self.seen_calls = len(self.agent.tools.calls)
        return calls

    def finish(self, termination: str) -> dict:
        """Write the run folder (grading it). Returns the grade summary for the page."""
        self.ended = True
        self.events.append(
            summary_event(
                self.status,
                termination,
                llm_calls_agent=self.agent.llm_calls,
                llm_calls_customer=0,
                seconds=time.monotonic() - self.started,
            )
        )
        out = settings.var_dir / "eval" / f"user-testing-{datetime.now():%Y%m%d}"
        task_id = self.task["id"]
        n = next_run_numbers(out, task_id, 1)[0]
        self.events[0]["trial"] = n
        folder = run_folder(out, task_id, n)
        g = write_run(folder, self.task, self.events, db_state(self.store))
        return {
            "log": str(folder),  # shown as "Run folder" on the page
            "end_state_match": bool(g["end_state_match"]),
            "verdict": g["verdict"],
            "notes": notes(g),
        }


class Start(BaseModel):
    task_id: str


class Message(BaseModel):
    text: str


@app.get("/")
def page() -> FileResponse:
    return FileResponse(FRONTEND / "index.html")


@app.get("/api/tasks")
def tasks() -> list[dict]:
    return [
        {"id": t["id"], "reason": t["user_scenario"]["instructions"]["reason_for_call"][:90]}
        for t in sorted(load_tasks().values(), key=lambda t: int(t["id"]))
    ]


@app.post("/api/sessions")
def start(body: Start) -> dict:
    task = load_tasks().get(body.task_id)
    if task is None:
        raise HTTPException(404, f"no task {body.task_id}")
    s = Session(task, app.state.model)
    sessions[s.id] = s
    return {
        "session_id": s.id,
        "scenario": task["user_scenario"]["instructions"],
        "greeting": FIRST_MESSAGE,
    }


@app.post("/api/sessions/{sid}/messages")
async def message(sid: str, body: Message) -> dict:
    s = sessions.get(sid)
    if s is None or s.ended:
        raise HTTPException(404, "no open session")
    s.log("customer", text=body.text)
    try:
        reply, stuck = await s.agent.reply(body.text)
    except InfraError as e:
        s.status = "infra_error"
        s.log("error", error=str(e))
        return {"reply": None, "tools": s.new_tool_calls(), "error": f"model API failed: {e}"}
    except Exception as e:  # keep the transcript for review
        s.status = "crash"
        s.log("error", error=f"{type(e).__name__}: {e}", traceback=traceback.format_exc())
        return {"reply": None, "tools": s.new_tool_calls(), "error": f"{type(e).__name__}: {e}"}
    tools = s.new_tool_calls()
    s.log("agent", text=reply)
    return {"reply": reply, "tools": tools, "stuck": stuck}


@app.post("/api/sessions/{sid}/end")
def end(sid: str) -> dict:
    s = sessions.get(sid)
    if s is None or s.ended:
        raise HTTPException(404, "no open session")
    return s.finish("human_ended")


app.mount("/static", StaticFiles(directory=FRONTEND), name="static")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p.add_argument("--model", default=MODEL, help="NIM model id for the agent")
    p.add_argument("--host", default="127.0.0.1")
    p.add_argument("--port", type=int, default=8000)
    args = p.parse_args()
    app.state.model = args.model
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
