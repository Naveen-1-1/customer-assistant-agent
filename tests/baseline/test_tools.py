"""The baseline's tools behave like τ²-bench's: every expected action in the 114 retail tasks,
called through them with τ²-bench's own arguments, leaves the store where the replay does."""

import json

import pytest

from customer_workflow_agent.baseline.tools import TOOL_SPECS, BaselineTools, calculate
from customer_workflow_agent.evalkit.replay import db_state, expected_db
from customer_workflow_agent.store import InMemoryBackend, RetailStore
from customer_workflow_agent.store.models import WorkingDB
from tests.conftest import PROJECT_ROOT

TASKS = json.loads((PROJECT_ROOT / "data" / "tasks.json").read_text())
# Expected actions that τ²-bench's own tools also reject.
EXPECTED_ERRORS = {
    ("64", "exchange_delivered_order_items"),
    ("105", "exchange_delivered_order_items"),
}


@pytest.mark.parametrize("task", TASKS, ids=[t["id"] for t in TASKS])
def test_gold_actions_through_tools_match_replay(task: dict, real_db: WorkingDB):
    tools = BaselineTools(RetailStore(InMemoryBackend(real_db)))
    for action in task["evaluation_criteria"]["actions"]:
        result = tools.call(action["name"], action["arguments"])
        # Some expected reads fail on purpose (a mistyped email, a made-up product id).
        if tools.calls[-1].write and (task["id"], action["name"]) not in EXPECTED_ERRORS:
            assert not result.startswith("Error"), (action, result)
    assert db_state(tools.store) == expected_db(task, real_db)


def test_every_tool_has_a_spec_and_a_handler(real_store: RetailStore):
    names = {s["function"]["name"] for s in TOOL_SPECS}
    assert len(names) == 16
    tools = BaselineTools(real_store)
    for name in names:
        assert "not found" not in tools.call(name, {}).lower() or name == "list_all_product_types"


def test_errors_come_back_as_text_and_are_logged(real_store: RetailStore):
    tools = BaselineTools(real_store)
    assert tools.call("get_order_details", {"order_id": "W2378156"}).startswith("Error:")
    assert tools.call("no_such_tool", {}) == "Error: Tool 'no_such_tool' not found"
    assert [c.error for c in tools.calls] == [True, True]


def test_each_write_gets_its_own_op_id(real_store: RetailStore):
    """A repeated write is attempted again (and rejected by status), not silently skipped."""
    tools = BaselineTools(real_store)
    order_id = next(o for o, order in real_store._db.orders.items() if order.status == "pending")
    args = {"order_id": order_id, "reason": "no longer needed"}
    assert not tools.call("cancel_pending_order", args).startswith("Error")
    assert tools.call("cancel_pending_order", args).startswith("Error")


def test_calculate_matches_tau2():
    assert calculate("2 + 2") == "4.0"
    assert calculate("(269.16 + 249.01) - (272.33 + 262.47)") == "-16.63"
    with pytest.raises(ValueError):
        calculate("__import__('os')")
