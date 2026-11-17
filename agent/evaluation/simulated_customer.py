"""The simulated customer: an LLM playing a τ²-bench task's scenario, as τ²-bench's UserSimulator.

The guidelines and scenario layout are copied from τ²-bench (commit 5bfa7e37):
`data/tau2/user_simulator/simulation_guidelines.md` and `src/tau2/data_model/tasks.py`.
The customer sees only what the agent says, never its tool calls. Our one addition: a case can
fix the customer's first message (`OPENERS`), as its protocol does for user testing.
"""

import textwrap
from dataclasses import dataclass, field

from langchain_core.rate_limiters import InMemoryRateLimiter

from agent.baseline.model_client import complete
from agent.settings import Settings

GUIDELINES = """\
# User Simulation Guidelines
You are playing the role of a customer contacting a customer service representative.
Your goal is to simulate realistic customer interactions while following specific scenario instructions.

## Core Principles
- Generate one message at a time, maintaining natural conversation flow.
- Strictly follow the scenario instructions you have received.
- Never make up or hallucinate information not provided in the scenario instructions. Information that is not provided in the scenario instructions should be considered unknown or unavailable.
- Avoid repeating the exact instructions verbatim. Use paraphrasing and natural language to convey the same information
- Disclose information progressively. Wait for the agent to ask for specific information before providing it.

## Task Completion
- The goal is to continue the conversation until the task is complete.
- If the instruction goal is satisified, generate the '###STOP###' token to end the conversation.
- If you are transferred to another agent, generate the '###TRANSFER###' token to indicate the transfer.
- If you find yourself in a situation in which the scenario does not provide enough information for you to continue the conversation, generate the '###OUT-OF-SCOPE###' token to end the conversation.
Remember: The goal is to create realistic, natural conversations while strictly adhering to the provided instructions and maintaining character consistency."""

STOP_TOKENS = ("###STOP###", "###TRANSFER###", "###OUT-OF-SCOPE###")

# A test case whose protocol fixes the customer's first message (the same line a person types in
# user testing). The simulated customer sends it word for word, then plays the scenario from there.
OPENERS = {
    "67": "Hi, it's NoNo. My user id is noah_ito_3850. I want to check how much I paid for my "
    "most recent order.",
}


def scenario_text(task: dict) -> str:
    """τ²-bench's rendering of a task's user scenario."""
    scenario = task["user_scenario"]
    ins = scenario["instructions"]
    lines = [
        f"Domain: {ins['domain']}",
        f"Reason for call:\n{textwrap.indent(ins['reason_for_call'], '\t')}",
    ]
    if ins.get("known_info") is not None:
        lines.append(f"Known info:\n{textwrap.indent(ins['known_info'], '\t')}")
    if ins.get("unknown_info") is not None:
        lines.append(f"Unknown info:\n{textwrap.indent(ins['unknown_info'], '\t')}")
    lines.append(f"Task instructions:\n{textwrap.indent(ins['task_instructions'], '\t')}")
    out = []
    if scenario.get("persona") is not None:
        out += ["Persona:", textwrap.indent(scenario["persona"], "\t")]
    out += ["Instructions:", textwrap.indent("\n".join(lines), "\t")]
    return "\n".join(out)


def stop_reason(text: str) -> str | None:
    return next((t for t in STOP_TOKENS if t in text), None)


@dataclass
class CustomerSimulator:
    task: dict
    settings: Settings
    limiter: InMemoryRateLimiter
    model: str
    temperature: float = 0.0
    # (speaker, text) with speaker "agent" or "customer"
    history: list[tuple[str, str]] = field(default_factory=list)
    llm_calls: int = 0

    @property
    def system_prompt(self) -> str:
        return f"{GUIDELINES}\n\n<scenario>\n{scenario_text(self.task)}\n</scenario>"

    async def next_message(self, agent_text: str) -> str:
        opener = OPENERS.get(self.task["id"])
        if opener and not self.history:
            # The case's protocol fixes the first message; the simulator continues from it.
            self.history += [("agent", agent_text), ("customer", opener)]
            return opener
        self.history.append(("agent", agent_text))
        # Roles flipped, as in τ²-bench: the agent speaks as "user" to the simulator's LLM.
        messages = [{"role": "system", "content": self.system_prompt}] + [
            {"role": "user" if who == "agent" else "assistant", "content": text}
            for who, text in self.history
        ]
        msg = await complete(
            self.settings, self.limiter, self.model, messages, temperature=self.temperature
        )
        self.llm_calls += 1
        text = (msg.content or "").strip()
        self.history.append(("customer", text))
        return text
