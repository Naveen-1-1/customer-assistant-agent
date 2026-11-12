"""τ²-bench's retail tools over our store, for the baseline agent.

Names, arguments and descriptions are copied from τ²-bench's `src/tau2/domains/retail/tools.py`
(commit 5bfa7e37), so the baseline sees exactly what the agents in τ²-bench's published runs saw.
Like those tools, they check order status, items and payments (the store does), but not who is
asking or whether the customer confirmed: that is left to the policy in the prompt.
"""

import ast
import json
import operator
import uuid
from dataclasses import dataclass, field

from customer_workflow_agent.store import RetailStore, StoreError
from customer_workflow_agent.store.models import UserAddress

ORDER_ID = (
    "The order id, such as '#W0000000'. Be careful there is a '#' symbol at the beginning of the "
    "order id."
)
ITEM_IDS = (
    "The item ids to be {verb}, each such as '1008292230'. There could be duplicate items in the "
    "list."
)
NEW_ITEM_IDS = (
    "The item ids to be {verb} for, each such as '1008292230'. There could be duplicate items in "
    "the list. Each new item id should match the item id in the same position and be of the same "
    "product."
)
PAYMENT_METHOD_ID = (
    "The payment method id to pay or receive refund for the item price difference, such as "
    "'gift_card_0000000' or 'credit_card_0000000'. These can be looked up from the user or order "
    "details."
)
ADDRESS_PARAMS = {
    "address1": "The first line of the address, such as '123 Main St'.",
    "address2": "The second line of the address, such as 'Apt 1' or ''.",
    "city": "The city, such as 'San Francisco'.",
    "state": "The state, such as 'CA'.",
    "country": "The country, such as 'USA'.",
    "zip": "The zip code, such as '12345'.",
}
WRITE_TOOLS = {
    "cancel_pending_order",
    "exchange_delivered_order_items",
    "modify_pending_order_address",
    "modify_pending_order_items",
    "modify_pending_order_payment",
    "modify_user_address",
    "return_delivered_order_items",
    "transfer_to_human_agents",
}


def _string(description: str) -> dict:
    return {"type": "string", "description": description}


def _strings(description: str) -> dict:
    return {"type": "array", "items": {"type": "string"}, "description": description}


def _tool(name: str, description: str, params: dict[str, dict]) -> dict:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {"type": "object", "properties": params, "required": list(params)},
        },
    }


TOOL_SPECS: list[dict] = [
    _tool(
        "calculate",
        "Calculate the result of a mathematical expression.",
        {
            "expression": _string(
                "The mathematical expression to calculate, such as '2 + 2'. The expression can "
                "contain numbers, operators (+, -, *, /), parentheses, and spaces."
            )
        },
    ),
    _tool(
        "cancel_pending_order",
        "Cancel a pending order. If the order is already processed or delivered, it cannot be "
        "cancelled. The agent needs to explain the cancellation detail and ask for explicit user "
        "confirmation (yes/no) to proceed. If the user confirms, the order status will be changed "
        "to 'cancelled' and the payment will be refunded. The refund will be added to the user's "
        "gift card balance immediately if the payment was made using a gift card, otherwise the "
        "refund would take 5-7 business days to process. The function returns the order details "
        "after the cancellation.",
        {
            "order_id": _string(ORDER_ID),
            "reason": _string(
                "The reason for cancellation, which should be either 'no longer needed' or "
                "'ordered by mistake'."
            ),
        },
    ),
    _tool(
        "exchange_delivered_order_items",
        "Exchange items in a delivered order to new items of the same product type. For a "
        "delivered order, return or exchange can be only done once by the agent. The agent needs "
        "to explain the exchange detail and ask for explicit user confirmation (yes/no) to "
        "proceed.",
        {
            "order_id": _string(ORDER_ID),
            "item_ids": _strings(ITEM_IDS.format(verb="exchanged")),
            "new_item_ids": _strings(NEW_ITEM_IDS.format(verb="exchanged")),
            "payment_method_id": _string(PAYMENT_METHOD_ID),
        },
    ),
    _tool(
        "find_user_id_by_name_zip",
        "Find user id by first name, last name, and zip code. If the user is not found, the "
        "function will return an error message. By default, find user id by email, and only call "
        "this function if the user is not found by email or cannot remember email.",
        {
            "first_name": _string("The first name of the customer, such as 'John'."),
            "last_name": _string("The last name of the customer, such as 'Doe'."),
            "zip": _string("The zip code of the customer, such as '12345'."),
        },
    ),
    _tool(
        "find_user_id_by_email",
        "Find user id by email. If the user is not found, the function will return an error "
        "message.",
        {"email": _string("The email of the user, such as 'something@example.com'.")},
    ),
    _tool(
        "get_order_details",
        "Get the status and details of an order.",
        {"order_id": _string(ORDER_ID)},
    ),
    _tool(
        "get_product_details",
        "Get the inventory details of a product.",
        {
            "product_id": _string(
                "The product id, such as '6086499569'. Be careful the product id is different "
                "from the item id."
            )
        },
    ),
    _tool(
        "get_item_details",
        "Get the inventory details of an item.",
        {
            "item_id": _string(
                "The item id, such as '6086499569'. Be careful the item id is different from the "
                "product id."
            )
        },
    ),
    _tool(
        "get_user_details",
        "Get the details of a user, including their orders.",
        {"user_id": _string("The user id, such as 'sara_doe_496'.")},
    ),
    _tool(
        "list_all_product_types",
        "List the name and product id of all product types. Each product type has a variety of "
        "different items with unique item ids and options. There are only 50 product types in "
        "the store.",
        {},
    ),
    _tool(
        "modify_pending_order_address",
        "Modify the shipping address of a pending order. The agent needs to explain the "
        "modification detail and ask for explicit user confirmation (yes/no) to proceed.",
        {"order_id": _string(ORDER_ID), **{k: _string(v) for k, v in ADDRESS_PARAMS.items()}},
    ),
    _tool(
        "modify_pending_order_items",
        "Modify items in a pending order to new items of the same product type. For a pending "
        "order, this function can only be called once. The agent needs to explain the exchange "
        "detail and ask for explicit user confirmation (yes/no) to proceed.",
        {
            "order_id": _string(ORDER_ID),
            "item_ids": _strings(ITEM_IDS.format(verb="modified")),
            "new_item_ids": _strings(NEW_ITEM_IDS.format(verb="modified")),
            "payment_method_id": _string(PAYMENT_METHOD_ID),
        },
    ),
    _tool(
        "modify_pending_order_payment",
        "Modify the payment method of a pending order. The agent needs to explain the "
        "modification detail and ask for explicit user confirmation (yes/no) to proceed.",
        {"order_id": _string(ORDER_ID), "payment_method_id": _string(PAYMENT_METHOD_ID)},
    ),
    _tool(
        "modify_user_address",
        "Modify the default address of a user. The agent needs to explain the modification "
        "detail and ask for explicit user confirmation (yes/no) to proceed.",
        {
            "user_id": _string("The user id, such as 'sara_doe_496'."),
            **{k: _string(v) for k, v in ADDRESS_PARAMS.items()},
        },
    ),
    _tool(
        "return_delivered_order_items",
        "Return some items of a delivered order. The order status will be changed to 'return "
        "requested'. The agent needs to explain the return detail and ask for explicit user "
        "confirmation (yes/no) to proceed. The user will receive follow-up email for how and "
        "where to return the item.",
        {
            "order_id": _string(ORDER_ID),
            "item_ids": _strings(ITEM_IDS.format(verb="returned")),
            "payment_method_id": _string(PAYMENT_METHOD_ID),
        },
    ),
    _tool(
        "transfer_to_human_agents",
        "Transfer the user to a human agent, with a summary of the user's issue. Only transfer "
        "if\n -  the user explicitly asks for a human agent\n -  given the policy and the "
        "available tools, you cannot solve the user's issue.",
        {"summary": _string("A summary of the user's issue.")},
    ),
]

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def calculate(expression: str) -> str:
    """τ²-bench's calculator (digits, + - * /, parentheses), evaluated without `eval`."""
    if not all(c in "0123456789+-*/(). " for c in expression):
        raise ValueError("Invalid characters in expression")

    def ev(node: ast.AST) -> float:
        if isinstance(node, ast.Constant) and isinstance(node.value, int | float):
            return node.value
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.left), ev(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](ev(node.operand))
        raise ValueError("Invalid expression")

    return str(round(float(ev(ast.parse(expression, mode="eval").body)), 2))


@dataclass
class ToolCall:
    name: str
    arguments: dict
    result: str
    error: bool
    write: bool


@dataclass
class BaselineTools:
    """Runs the agent's tool calls against one store and keeps a log of them."""

    store: RetailStore
    calls: list[ToolCall] = field(default_factory=list)

    def call(self, name: str, arguments: dict) -> str:
        try:
            result, error = self._run(name, dict(arguments)), False
        except (StoreError, ValueError, TypeError, KeyError, SyntaxError, ZeroDivisionError) as e:
            result, error = f"Error: {e}", True
        self.calls.append(ToolCall(name, arguments, result, error, name in WRITE_TOOLS))
        return result

    def _run(self, name: str, a: dict) -> str:
        s, op_id = self.store, str(uuid.uuid4())  # a fresh op id: the store skips reused ones
        match name:
            case "calculate":
                return calculate(a["expression"])
            case "find_user_id_by_email":
                return s.find_user_id_by_email(a["email"])
            case "find_user_id_by_name_zip":
                return s.find_user_id_by_name_zip(a["first_name"], a["last_name"], a["zip"])
            case "get_user_details":
                return s.get_user(a["user_id"]).model_dump_json()
            case "get_order_details":
                return s.get_order(a["order_id"]).model_dump_json()
            case "get_product_details":
                return s.get_product(a["product_id"]).model_dump_json()
            case "get_item_details":
                return s.get_item(a["item_id"])[1].model_dump_json()
            case "list_all_product_types":
                return json.dumps(s.list_all_product_types())
            case "cancel_pending_order":
                return s.cancel_pending_order(
                    a["order_id"], a["reason"], op_id=op_id
                ).model_dump_json()
            case "modify_pending_order_address" | "modify_user_address":
                address = UserAddress(**{k: a[k] for k in ADDRESS_PARAMS})
                target = a["order_id"] if name == "modify_pending_order_address" else a["user_id"]
                return getattr(s, name)(target, address, op_id=op_id).model_dump_json()
            case "modify_pending_order_payment":
                return s.modify_pending_order_payment(
                    a["order_id"], a["payment_method_id"], op_id=op_id
                ).model_dump_json()
            case "modify_pending_order_items" | "exchange_delivered_order_items":
                return getattr(s, name)(
                    a["order_id"],
                    a["item_ids"],
                    a["new_item_ids"],
                    a["payment_method_id"],
                    op_id=op_id,
                ).model_dump_json()
            case "return_delivered_order_items":
                return s.return_delivered_order_items(
                    a["order_id"], a["item_ids"], a["payment_method_id"], op_id=op_id
                ).model_dump_json()
            case "transfer_to_human_agents":
                return s.transfer_to_human_agents(None, a["summary"], op_id=op_id)
        raise ValueError(f"Tool '{name}' not found")
