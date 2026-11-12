"""One chat completion on a fixed NIM model: no fallback, so a run never switches models."""

import litellm
from langchain_core.rate_limiters import InMemoryRateLimiter
from langsmith import traceable

from customer_workflow_agent.llm.client import NO_THINKING
from customer_workflow_agent.settings import Settings


class InfraError(RuntimeError):
    """The model API failed after retries (timeout, 429, 5xx): not the agent's fault."""


@traceable(
    run_type="llm",
    process_inputs=lambda i: {"messages": i.get("messages"), "model": i.get("model")},
)
async def _completion(**kwargs):
    return await litellm.acompletion(**kwargs)


async def complete(
    settings: Settings,
    limiter: InMemoryRateLimiter,
    model: str,
    messages: list[dict],
    *,
    tools: list[dict] | None = None,
    temperature: float = 0.0,
    max_tokens: int = 1024,
    timeout_s: float = 60.0,
    retries: int = 3,
):
    """The assistant message of one completion. Raises InfraError when every attempt fails."""
    assert settings.nvidia_api_key is not None, "NVIDIA_API_KEY is not set (add it to .env)"
    kwargs: dict = {
        "model": f"openai/{model}",  # NVIDIA's API is OpenAI-compatible
        "api_base": settings.llm_base_url,
        "api_key": settings.nvidia_api_key.get_secret_value(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "timeout": timeout_s,
        "extra_body": NO_THINKING,
    }
    if tools:
        kwargs |= {"tools": tools, "tool_choice": "auto", "parallel_tool_calls": False}
    last: Exception | None = None
    for _ in range(retries + 1):
        await limiter.aacquire()
        try:
            response = await _completion(**kwargs)
            return response.choices[0].message
        except (
            litellm.Timeout,
            litellm.RateLimitError,
            litellm.InternalServerError,
            litellm.APIConnectionError,
            litellm.ServiceUnavailableError,
        ) as e:
            last = e
    raise InfraError(f"{model}: {type(last).__name__}: {last}")
