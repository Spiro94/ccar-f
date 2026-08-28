"""Task 1.4.1 - Multi-concern decomposition, shared context, unified synthesis.

The official exam guide names this as its own skill, distinct from 1.4's single-
concern gate-and-escalate pattern: "Decomposing multi-concern customer requests
into distinct items, then investigating each in parallel using shared context
before synthesizing a unified resolution." A customer message is not always one
request - "refund my order AND update my email AND I was double-charged" is
three concerns in one message, and the failure mode is answering only the first
one, or answering all three as disconnected replies instead of one resolution.

SHARED CONTEXT, concretely: identity is verified ONCE via get_customer, and
that single verification gates every concern-specific tool below - the agent
does not, and structurally cannot, re-verify per concern. That is what "shared"
means here, not just "the same conversation".

Run: python -m domain_1_agentic_architecture.task_1_4_1_multi_concern_decomposition
"""

import json

from shared.client import client

MAX_TURNS = 10

CUSTOMERS = {"C-1001": {"name": "Dana R.", "tier": "gold", "verified": True}}
ORDERS = {
    "O-77": {"customer_id": "C-1001", "total": 240.00, "status": "delivered", "charge_count": 1},
    "O-80": {"customer_id": "C-1001", "total": 89.00, "status": "delivered", "charge_count": 2},
}
CONTACTS = {"C-1001": {"email": "dana.r@example.com"}}

GET_CUSTOMER_TOOL = {
    "name": "get_customer",
    "description": "Look up and verify a customer by ID.",
    "input_schema": {
        "type": "object",
        "properties": {"customer_id": {"type": "string", "description": "e.g. C-1001"}},
        "required": ["customer_id"],
    },
}

GET_ORDER_TOOL = {
    "name": "get_order",
    "description": "Look up an order by ID, including its total and how many "
                   "times it was charged.",
    "input_schema": {
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "e.g. O-77"}},
        "required": ["order_id"],
    },
}

PROCESS_REFUND_TOOL = {
    "name": "process_refund",
    "description": "Issue a refund against an order.",
    "input_schema": {
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "amount": {"type": "number"},
        },
        "required": ["order_id", "amount"],
    },
}

UPDATE_CONTACT_TOOL = {
    "name": "update_contact_info",
    "description": "Update a verified customer's contact email.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "email": {"type": "string"},
        },
        "required": ["customer_id", "email"],
    },
}

ESCALATE_TOOL = {
    "name": "escalate_to_human",
    "description": "Hand off one concern to a human operator. Use for anything "
                   "ambiguous or exceptional - a duplicate charge is not "
                   "something to resolve unilaterally.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string"},
            "root_cause": {"type": "string"},
            "recommendation": {"type": "string"},
        },
        "required": ["customer_id", "root_cause", "recommendation"],
    },
}

TOOLS = [GET_CUSTOMER_TOOL, GET_ORDER_TOOL, PROCESS_REFUND_TOOL, UPDATE_CONTACT_TOOL, ESCALATE_TOOL]

# The gate from Task 1.4, reused: one verification, shared by every
# concern-specific tool below rather than re-checked per concern.
verified_customers = set()


def get_customer(customer_id):
    record = CUSTOMERS.get(customer_id)
    if record is None:
        raise ValueError("no such customer: " + customer_id)
    if record["verified"]:
        verified_customers.add(customer_id)
    return json.dumps(record)


def get_order(order_id):
    order = ORDERS.get(order_id)
    if order is None:
        raise ValueError("no such order: " + order_id)
    return json.dumps(order)


def process_refund(order_id, amount):
    order = ORDERS.get(order_id)
    if order is None:
        raise ValueError("no such order: " + order_id)
    if order["customer_id"] not in verified_customers:
        raise PermissionError("prerequisite not met: verify the customer first")
    return json.dumps({"refunded": amount, "order_id": order_id})


def update_contact_info(customer_id, email):
    if customer_id not in verified_customers:
        raise PermissionError("prerequisite not met: verify the customer first")
    CONTACTS[customer_id]["email"] = email
    return json.dumps({"customer_id": customer_id, "email": email})


def escalate_to_human(customer_id, root_cause, recommendation):
    print("\n--- ESCALATION ---")
    print("customer:", customer_id, "| root cause:", root_cause, "| recommendation:", recommendation)
    print("--- END ---\n")
    return "Escalated. A human operator will take over this item."


TOOL_FUNCTIONS = {
    "get_customer": get_customer,
    "get_order": get_order,
    "process_refund": process_refund,
    "update_contact_info": update_contact_info,
    "escalate_to_human": escalate_to_human,
}

SYSTEM_PROMPT = (
    "You are a support agent. Customer messages may contain multiple distinct "
    "concerns. Decompose the message into its separate items before acting. "
    "Verify the customer's identity once with get_customer, then reuse that "
    "verification for every concern - do not verify more than once. Investigate "
    "and resolve what you can resolve directly; escalate anything ambiguous or "
    "exceptional, such as a duplicate charge, rather than deciding it yourself. "
    "Once every concern has been addressed, reply with ONE unified response "
    "that covers all of them together - do not answer only the first concern, "
    "and do not present three disconnected replies."
)

messages = [{
    "role": "user",
    "content": (
        "Hi, this is customer C-1001. I need help with a few things: (1) please refund order O-77 in "
        "full, (2) update my email to dana.new@example.com, and (3) I think "
        "I was double-charged on order O-80 - can you check that?"
    ),
}]

concerns_addressed = set()

for turn in range(MAX_TURNS):
    message = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
        tools=TOOLS,
    )

    messages.append({"role": "assistant", "content": message.content})

    if message.stop_reason != "tool_use":
        for block in message.content:
            if block.type == "text":
                print(block.text)
        break

    results = []
    for block in message.content:
        if block.type != "tool_use":
            continue
        # Rough per-concern visibility: which tools ran, in what order. A
        # genuinely decomposed run touches all three concern-specific tools
        # (refund, contact update, escalate) rather than stopping after one.
        if block.name in ("process_refund", "update_contact_info", "escalate_to_human"):
            concerns_addressed.add(block.name)
        print("Calling tool:", block.name, block.input)
        try:
            output = TOOL_FUNCTIONS[block.name](**block.input)
            results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
        except Exception as exc:
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": type(exc).__name__ + ": " + str(exc),
                "is_error": True,
            })

    messages.append({"role": "user", "content": results})
else:
    print("Stopped after " + str(MAX_TURNS) + " turns without a final answer.")

print("\nConcerns addressed:", concerns_addressed or "none - decomposition may have failed")
