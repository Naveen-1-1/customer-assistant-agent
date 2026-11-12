"""Every write in τ²-bench's 114 retail tasks replays cleanly against a fresh store."""

import json

import pytest

from customer_workflow_agent.evalkit.replay import apply_action, write_actions
from customer_workflow_agent.store import InMemoryBackend, RetailStore, StoreError
from customer_workflow_agent.store.models import WorkingDB
from tests.conftest import PROJECT_ROOT

TASKS = json.loads((PROJECT_ROOT / "data" / "tasks.json").read_text())

# Expected actions that τ²-bench's own tools also reject (the task expects the attempt to fail).
EXPECTED_FAILURES = {
    ("64", 0): "invalid_status",  # exchange on an order that is still pending
    ("105", 0): "insufficient_gift_card_balance",  # $17.00 gift card vs $21.10 difference
}


@pytest.mark.parametrize("task", TASKS, ids=[t["id"] for t in TASKS])
def test_task_writes_replay(task: dict, real_db: WorkingDB):
    store = RetailStore(InMemoryBackend(real_db))
    for i, action in enumerate(write_actions(task)):
        expected = EXPECTED_FAILURES.get((task["id"], i))
        if expected is None:
            apply_action(store, action["name"], action["arguments"], f"{task['id']}-{i}")
        else:
            with pytest.raises(StoreError) as e:
                apply_action(store, action["name"], action["arguments"], f"{task['id']}-{i}")
            assert e.value.code == expected
