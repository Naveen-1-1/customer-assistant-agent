"""A payment method the customer names in words is picked even when the model leaves it out."""

import pytest

from customer_workflow_agent.graph.action import apply_choice, named_payment_choice
from customer_workflow_agent.graph.common import address_and_payment_first
from customer_workflow_agent.graph.subgraphs.return_items import SPEC as RETURNS
from customer_workflow_agent.graph.subgraphs.swap_items import said_by_customer
from customer_workflow_agent.llm.schemas import ItemRef, ItemsTurn, ReturnTurn
from tests.graph.helpers import make

LABELS = ["Mastercard card ending 2478", "gift card (balance $59.00)", "PayPal"]


@pytest.mark.parametrize(
    ("text", "index"),
    [
        ("I'll use my Mastercard card ending 2478 for any price differences.", 0),
        ("the one ending in 2478 please", 0),
        ("Fine, I'll take the gift card.", 1),
        ("PayPal is fine", 2),
        ("whatever works", None),
        ("my card", None),
    ],
)
def test_named_payment_choice(text: str, index: int | None):
    assert named_payment_choice(text, LABELS) == index


def test_two_cards_of_one_brand_stay_ambiguous():
    labels = ["Visa card ending 1111", "Visa card ending 2222"]
    assert named_payment_choice("my Visa", labels) is None
    assert named_payment_choice("Visa ending 2222", labels) == 1


def test_apply_choice_uses_the_named_method_when_the_model_gives_no_number():
    """τ²-bench task 0: the answer came with a new question, and the model filled neither."""
    turn = make(ItemsTurn, relation="also_new_request")
    choices = {
        "kind": "payment",
        "values": ["credit_card_9513926"],
        "index": None,
        "labels": LABELS[:1],
    }
    text = "I'll use my Mastercard card ending 2478. Now, show me the thermostat options?"
    assert apply_choice({}, turn, choices, text)["payment_method_id"] == "credit_card_9513926"
    assert apply_choice({}, turn, choices, "hmm, not sure") == {}


@pytest.mark.parametrize(
    ("product", "text", "said"),
    [
        ("Smart Thermostat", "and the thermostat for a Google Home one", True),
        ("Mechanical Keyboard", "exchange my keyboard for a clicky one", True),
        ("Headphones", "I'd like to exchange a couple of items", False),  # τ²-bench task 0
        ("T-Shirt", "the tshirt in blue", True),
    ],
)
def test_items_must_come_from_the_customers_words(product: str, text: str, said: bool):
    assert said_by_customer(product, text) is said


@pytest.mark.parametrize(
    ("text", "all_items"),
    [
        ("I want to return the headphones, the vacuum cleaner and the smart watch", False),
        ("Please return everything in that order", True),
    ],
)
def test_naming_items_is_not_returning_everything(text: str, all_items: bool):
    """τ²-bench task 2: the model flagged 'all items' although three were named."""
    turn = make(
        ReturnTurn,
        all_items=True,
        items=[ItemRef(product="headphones", options=[], quantity=1)],
    )
    assert bool(RETURNS.merge({}, turn, text, None).get("all_items")) is all_items


def test_address_change_goes_before_the_item_change_on_the_same_order():
    """τ²-bench task 72: items first would lock the order and lose the address change."""
    reqs = [
        {"type": "modify_order_items", "order_id": None},
        {"type": "cancel_order", "order_id": "#W1"},
        {"type": "modify_order_address", "order_id": None},
    ]
    assert [r["type"] for r in address_and_payment_first(reqs)] == [
        "modify_order_address",
        "modify_order_items",
        "cancel_order",
    ]
    other_order = [
        {"type": "modify_order_items", "order_id": "#W1"},
        {"type": "modify_order_address", "order_id": "#W2"},
    ]
    assert address_and_payment_first(other_order) == other_order
