"""The baseline: a plain LLM-and-tools support agent, built like τ²-bench's reference `LLMAgent`.

The policy goes in the system prompt and the model decides everything else: which tool to call,
with what arguments, and when to ask the customer. This is how industry guidance (and the agents
in τ²-bench's published runs) build a support agent; nothing outside the prompt enforces the
policy, the confirmation, or what the customer is shown.
"""

import json
from dataclasses import dataclass, field

from langchain_core.rate_limiters import InMemoryRateLimiter

from agent.baseline.model_client import complete
from agent.baseline.tools import TOOL_SPECS, BaselineTools
from agent.settings import Settings
from agent.store import RetailStore

# τ²-bench's AGENT_INSTRUCTION and SYSTEM_PROMPT (src/tau2/agent/llm_agent.py, commit 5bfa7e37).
AGENT_INSTRUCTION = """\
You are a customer service agent that helps the user according to the <policy> provided below.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.

Try to be helpful and always follow the policy. Always make sure you generate valid JSON only."""
SYSTEM_PROMPT = "<instructions>\n{instruction}\n</instructions>\n<policy>\n{policy}\n</policy>"
FIRST_MESSAGE = "Hi! How can I help you today?"  # τ²-bench's DEFAULT_FIRST_AGENT_MESSAGE


@dataclass
class BaselineAgent:
    store: RetailStore
    settings: Settings
    limiter: InMemoryRateLimiter
    model: str
    max_steps_per_turn: int = 12
    tools: BaselineTools = field(init=False)
    messages: list[dict] = field(init=False)
    llm_calls: int = 0

    def __post_init__(self) -> None:
        self.tools = BaselineTools(self.store)
        policy = (self.settings.data_dir / "policy.md").read_text()
        system = SYSTEM_PROMPT.format(instruction=AGENT_INSTRUCTION, policy=policy)
        self.messages = [
            {"role": "system", "content": system},
            {"role": "assistant", "content": FIRST_MESSAGE},
        ]

    async def reply(self, customer_text: str) -> tuple[str, bool]:
        """Handle one customer message: tool calls until the model answers. Returns the answer and
        whether the model hit the step cap (it kept calling tools without answering)."""
        self.messages.append({"role": "user", "content": customer_text})
        for _ in range(self.max_steps_per_turn):
            msg = await complete(
                self.settings, self.limiter, self.model, self.messages, tools=TOOL_SPECS
            )
            self.llm_calls += 1
            calls = msg.tool_calls or []
            if not calls:
                text = (msg.content or "").strip()
                self.messages.append({"role": "assistant", "content": text})
                return text, False
            self.messages.append(
                {
                    "role": "assistant",
                    "content": msg.content or "",
                    "tool_calls": [
                        {
                            "id": c.id,
                            "type": "function",
                            "function": {
                                "name": c.function.name,
                                "arguments": c.function.arguments,
                            },
                        }
                        for c in calls
                    ],
                }
            )
            for c in calls:
                try:
                    args = json.loads(c.function.arguments or "{}")
                except json.JSONDecodeError:
                    result = "Error: arguments are not valid JSON"
                else:
                    result = self.tools.call(c.function.name, args)
                self.messages.append({"role": "tool", "tool_call_id": c.id, "content": result})
        return "", True
