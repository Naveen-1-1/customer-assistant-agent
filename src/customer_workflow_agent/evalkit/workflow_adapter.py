"""Drive the workflow graph with a text-only customer, the way the chat page would.

The simulated customer can only type, so the graph's pauses are rendered as text: reply buttons
become "Options: …", and the Yes/No popup becomes a "[Confirmation]" block whose typed answer is
mapped to the popup's yes/no. Supervisor approval stays off (it is not a τ²-bench rule).
"""

import re
from dataclasses import dataclass, field

from langchain_core.rate_limiters import InMemoryRateLimiter
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from customer_workflow_agent.deps import Deps
from customer_workflow_agent.graph.builder import build_graph, read_chat, run_config
from customer_workflow_agent.llm.service import RouterLLMService
from customer_workflow_agent.settings import Settings
from customer_workflow_agent.store import RetailStore

# The reply must *start* as a yes: "I need to correct this…" contains "correct" but is a no.
YES = re.compile(
    r"^\W*(yes|yeah|yep|yup|sure|ok(ay)?|correct|confirm(ed)?|i confirm|go ahead|proceed|"
    r"please (proceed|do|go ahead|confirm)|sounds good|looks good|perfect|do it|"
    r"that'?s (right|correct|fine|good)|that (looks|works|is|sounds) (good|correct|right|fine)?)\b",
    re.I,
)
NO = re.compile(
    r"\b(no|nope|not|don'?t|do not|wait|hold on|but|actually|instead|stop|cancel that)\b", re.I
)
# A sentence that opens as a no: "Wait, …", "No, only the lamp", "I need to correct this …".
NO_START = re.compile(
    r"^\W*(no|nope|not|don'?t|do not|wait|hold on|actually|cancel that|stop|"
    r"i need to (correct|change|fix|update|clarify|cancel)|that'?s (not|wrong|incorrect))\b",
    re.I,
)


# A yes taken back right away: "Yes, I confirm. However, only the backpack…". Only the very next
# sentence counts, so a new topic later on ("Now, about the skateboard… Actually…") doesn't.
CORRECTION = re.compile(
    r"^\W*(however|but|actually|wait|on second thought)\b|"
    r"\b(instead|changed? my mind|i'?ve decided to only|i have decided to only)\b",
    re.I,
)


def popup_answer(text: str) -> bool:
    """The popup button a typed reply amounts to: the first sentence that clearly says yes or no
    decides, as the customer's click would. "Ugh, fine! … Yes, I confirm" is a yes; "Yes, please
    change the address. Can it ship in 5 days? If not…" is a yes; "Yes, but actually…",
    "I need to correct this…" and "Yes, I confirm. However, only the backpack…" are no. With
    neither, it's a No, which keeps the request open."""
    sentences = re.split(r"(?<=[.!?])\s+|\n+", text.strip())
    for i, sentence in enumerate(sentences):
        if NO_START.match(sentence):
            return False
        if YES.match(sentence):
            # "Okay, I'll be direct:" then "NO - do not cancel…": the "okay" only opens the no.
            following = sentences[i + 1] if i + 1 < len(sentences) else ""
            return not (
                NO.search(sentence) or CORRECTION.search(following) or NO_START.match(following)
            )
    return False


def render_popup(pause: dict) -> str:
    s = pause["summary"]
    lines = [f"[Confirmation] {s['title']}", *[f"- {line}" for line in s["lines"]]]
    if s.get("amount") is not None:
        lines.append(f"{s.get('amount_label') or 'Amount'}: ${s['amount']:.2f}")
    lines.append("Please reply yes to confirm or no to change something.")
    return "\n".join(lines)


def render_pause(pause: dict | None, ended: bool, show_buttons: bool = True) -> str:
    texts = [m["text"] for m in (pause or {}).get("messages", []) if m["role"] != "customer"]
    if pause and pause["type"] == "confirm":
        texts.append(render_popup(pause))
    elif pause and pause.get("suggestions") and show_buttons:
        texts.append("Options: " + " | ".join(s["label"] for s in pause["suggestions"]))
    if ended:
        texts.append("[The chat has ended.]")
    return "\n\n".join(t for t in texts if t)


@dataclass
class WorkflowAgent:
    store: RetailStore
    settings: Settings
    limiter: InMemoryRateLimiter
    model: str
    thread_id: str
    pause: dict | None = None
    values: dict = field(default_factory=dict)
    popups: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        # One fixed model: the "fallback" is the same model, so a run never switches models. Each
        # call gets the baseline's 60 s, so a slow API hits both agents alike.
        s = self.settings.model_copy(
            update={
                "llm_primary_model": self.model,
                "llm_fallback_model": self.model,
                "llm_timeout_s": 60.0,
                "approval_enabled": False,
            }
        )
        self.llm = RouterLLMService(s, rate_limiter=self.limiter)
        self.graph = build_graph(Deps(self.store, self.llm, s), InMemorySaver())
        self.cfg = run_config(self.thread_id, s)

    @property
    def ended(self) -> bool:
        return self.values.get("phase") == "ended" and self.pause is None

    async def _run(self, inp) -> str:
        await self.graph.ainvoke(inp, self.cfg)
        self.values, interrupts = await read_chat(self.graph, self.cfg)
        self.pause = interrupts[0].value if interrupts else None
        # Before verification the buttons are the landing page's demo customers, not replies.
        return render_pause(self.pause, self.ended, show_buttons=bool(self.values.get("user_id")))

    async def start(self) -> str:
        return await self._run({})

    async def reply(self, customer_text: str) -> tuple[str, bool]:
        """Same shape as BaselineAgent.reply; the second value is always False here."""
        # The simulated customer sometimes echoes the "Options: …" line back; a real customer
        # clicks a button or types, so that echo is dropped.
        customer_text = "\n".join(
            line for line in customer_text.splitlines() if not line.strip().startswith("Options:")
        ).strip()[:2000]  # the chat box's limit (CustomerReply)
        if self.pause and self.pause["type"] == "confirm":
            yes = popup_answer(customer_text)
            self.popups.append(
                {
                    "summary": self.pause["summary"],
                    "action": self.pause.get("action"),
                    "typed": customer_text,
                    "confirmed": yes,
                }
            )
            out = await self._run(Command(resume={"confirmed": yes}))
            if (
                not yes
                and len(customer_text.split()) > 3
                and self.pause
                and self.pause["type"] == "await_customer"
            ):
                # A typed "no, only the lamp please" carries the change too: hand it on now, as a
                # customer would click No and then type it.
                out = await self._run(Command(resume={"text": customer_text}))
            return out, False
        if self.pause and self.pause["type"] == "await_customer":
            return await self._run(Command(resume={"text": customer_text})), False
        return render_pause(self.pause, self.ended), False
