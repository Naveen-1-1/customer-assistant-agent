"""Pieces of the evaluation harness that run without a model."""

import pytest

from customer_workflow_agent.evalkit.replay import load_tasks
from customer_workflow_agent.evalkit.simulator import scenario_text, stop_reason
from customer_workflow_agent.evalkit.workflow_adapter import (
    popup_answer,
    render_pause,
    render_popup,
)


@pytest.mark.parametrize(
    ("typed", "yes"),
    [
        ("Yes, please go ahead.", True),
        ("Sounds good, thanks", True),
        ("yes", True),
        ("No, only exchange the desk lamp please", False),
        ("Yes, but actually change the color to black", False),
        ("Wait, I want to return it instead", False),
        ("Hmm, what is the refund amount again?", False),
        # τ²-bench task 82: a grumble first, then the yes.
        (
            "Ugh, fine! I guess I'll take the gift card then. Yes, I confirm - return everything.",
            True,
        ),
        # τ²-bench task 72: a yes taken back in the same message.
        ("Yes, I confirm these changes. However, I've decided to only modify the backpack.", False),
        (
            "Yes, that's correct. I'd like to confirm this and use PayPal instead of a gift card.",
            False,
        ),
        # τ²-bench task 99: a yes, then a new topic that happens to say "actually" later on.
        (
            "Yes, that looks correct now. I confirm the camera exchange. Now, about the "
            "skateboard: can I cancel it here? Actually, looking back at my request, I'm unsure.",
            True,
        ),
        # τ²-bench task 34: "Okay" opens a no.
        (
            "Okay, I'm going to be really direct here because I'm getting confused messages:\n\n"
            "**NO** - do NOT cancel the whole order.",
            False,
        ),
        # τ²-bench task 2: "correct" as a verb, not a yes.
        ("I need to correct this - I only want to return the headphones and the watch.", False),
        ("That looks correct. Please proceed with the address change.", True),
        ("I confirm the return of all three items.", True),
        # τ²-bench task 59: a clear yes, then a separate question with "if not" in it.
        (
            "Yes, please change the shipping address for order #W2702727 to 1234 Elm St. "
            "Now I need to know: can it ship in 5 days? If not, I want to cancel it.",
            True,
        ),
    ],
)
def test_typed_reply_maps_to_popup_button(typed: str, yes: bool):
    assert popup_answer(typed) is yes


def test_popup_and_buttons_render_as_text():
    pause = {
        "type": "confirm",
        "messages": [{"role": "agent", "text": "Here's what will change:"}],
        "summary": {
            "title": "Cancel order #W1",
            "lines": ["Reason: no longer needed"],
            "amount": 12.5,
            "amount_label": "Refund",
        },
    }
    text = render_pause(pause, ended=False)
    assert text.startswith("Here's what will change:")
    assert "[Confirmation] Cancel order #W1\n- Reason: no longer needed\nRefund: $12.50" in text
    assert render_popup(pause).endswith("Please reply yes to confirm or no to change something.")
    asked = {
        "type": "await_customer",
        "messages": [],
        "suggestions": [{"label": "Yes"}, {"label": "Skip"}],
    }
    assert render_pause(asked, ended=False) == "Options: Yes | Skip"
    assert render_pause(None, ended=True) == "[The chat has ended.]"


def test_scenario_is_rendered_like_tau2():
    text = scenario_text(load_tasks()["0"])
    assert text.startswith("Instructions:\n\tDomain: retail\n\tReason for call:\n\t\tYou received")
    assert "\tKnown info:\n\t\tYou are Yusuf Rossi in zip code 19122." in text


def test_stop_tokens():
    assert stop_reason("Thanks! ###STOP###") == "###STOP###"
    assert stop_reason("###TRANSFER###") == "###TRANSFER###"
    assert stop_reason("ok, bye") is None
