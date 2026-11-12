"""Replay a τ²-bench task's expected actions to get the store state a correct run ends in."""

import json
from functools import cache

from customer_workflow_agent.settings import get_settings
from customer_workflow_agent.store import InMemoryBackend, RetailStore, StoreError
from customer_workflow_agent.store.models import UserAddress, WorkingDB

ADDRESS_KEYS = ("address1", "address2", "city", "state", "country", "zip")
# App-only bookkeeping (op ids, transfer log, return blocks) that a correct run needn't match.
BOOKKEEPING = {"ledger", "transfers", "return_blocked_orders"}


@cache
def load_tasks() -> dict[str, dict]:
    return {t["id"]: t for t in json.loads(get_settings().tasks_path.read_text())}


@cache
def load_db() -> WorkingDB:
    return WorkingDB.model_validate_json(get_settings().db_original.read_bytes())


def apply_action(store: RetailStore, name: str, args: dict, op_id: str) -> None:
    """Run one τ²-bench expected action against our store (reads are skipped)."""
    a = dict(args)
    if name in ("modify_pending_order_address", "modify_user_address"):
        address = UserAddress(**{k: a.pop(k) for k in ADDRESS_KEYS})
        target = a.pop("order_id", None) or a.pop("user_id")
        getattr(store, name)(target, address, op_id=op_id)
    elif name == "transfer_to_human_agents":
        store.transfer_to_human_agents(None, a["summary"], op_id=op_id)
    elif name in (
        "cancel_pending_order",
        "modify_pending_order_payment",
        "modify_pending_order_items",
        "return_delivered_order_items",
        "exchange_delivered_order_items",
    ):
        getattr(store, name)(**a, op_id=op_id)


def write_actions(task: dict) -> list[dict]:
    actions = (task.get("evaluation_criteria") or {}).get("actions") or []
    return [
        a
        for a in actions
        if a["name"].startswith(("cancel", "modify", "return", "exchange", "transfer"))
    ]


def db_state(store: RetailStore) -> dict:
    return store._db.model_dump(exclude=BOOKKEEPING)


def expected_db(task: dict, db: WorkingDB) -> dict:
    """The final store for a correct run. An expected action that τ²-bench's own tools reject
    (tasks 64 and 105) leaves the store unchanged, as it does in τ²-bench."""
    store = RetailStore(InMemoryBackend(db))
    for i, action in enumerate(write_actions(task)):
        try:
            apply_action(store, action["name"], action["arguments"], f"gold-{i}")
        except StoreError:
            pass
    return db_state(store)
