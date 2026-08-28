"""Task 1.4 - Workflow enforcement and escalation.

Instructing Claude in a prompt is probabilistic: "always look up the customer
first" is best-effort and skips in production often enough to matter (~12% in
the exam's figure). Business-critical ordering needs a PROGRAMMATIC PREREQUISITE
- a code-enforced gate in the dispatch path that a prompt cannot talk past.

Run: python -m domain_1_agentic_architecture.task_1_4_workflow_enforcement
"""

import json

from shared.client import client

MAX_TURNS = 10

CUSTOMERS = {"C-1001": {"name": "Dana R.", "tier": "gold", "verified": True}}
ORDERS = {"O-77": {"customer_id": "C-1001", "total": 240.00, "status": "delivered"}}

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
    "description": "Look up an order by ID, including its total.",
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
            "order_id": {"type": "string", "description": "e.g. O-77"},
            "amount": {"type": "number", "description": "Amount in USD"},
        },
        "required": ["order_id", "amount"],
    },
}

ESCALATE_TOOL = {
    "name": "escalate_to_human",
    "description": "Hand off to a human operator. Use when policy is ambiguous, "
                   "the case is an exception, or the customer asks for a human.",
    "input_schema": {
        "type": "object",
        "properties": {
            "customer_id": {"type": "string", "description": "Customer ID"},
            "root_cause": {"type": "string", "description": "What actually went wrong"},
            "attempted": {"type": "string", "description": "Paths already tried"},
            "recommendation": {"type": "string", "description": "Recommended action"},
        },
        # The operator has NO access to the transcript, so the full handoff
        # package is required, not optional. A bare "customer is upset" hand-off
        # makes the human restart the investigation from zero.
        "required": ["customer_id", "root_cause", "attempted", "recommendation"],
    },
}

# Deterministic state: set by the executor, not by anything Claude says.
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

    # THE GATE. Blocks the downstream call until the prerequisite has actually
    # run. Claude may attempt process_refund first - this returns an error
    # instead of a refund, and Claude self-corrects by calling get_customer.
    if order["customer_id"] not in verified_customers:
        raise PermissionError(
            "prerequisite not met: call get_customer for "
            + order["customer_id"] + " before issuing a refund"
        )

    if amount > 500:
        # A threshold exception is not the agent's call to make - route it out.
        raise PermissionError("refunds over $500 must be escalated to a human")

    return json.dumps({"refunded": amount, "order_id": order_id})


def escalate_to_human(customer_id, root_cause, attempted, recommendation):
    print("\n--- ESCALATION ---")
    print("customer:", customer_id)
    print("root cause:", root_cause)
    print("attempted:", attempted)
    print("recommendation:", recommendation)
    print("--- END ---\n")
    return "Escalated. A human operator will take over."


TOOL_FUNCTIONS = {
    "get_customer": get_customer,
    "get_order": get_order,
    "process_refund": process_refund,
    "escalate_to_human": escalate_to_human,
}
TOOLS = [GET_CUSTOMER_TOOL, GET_ORDER_TOOL, PROCESS_REFUND_TOOL, ESCALATE_TOOL]

# The prompt still states the rule - prompt and gate are complementary. The
# prompt makes the correct path likely; the gate makes the wrong path
# impossible. Only the second one is a guarantee.
SYSTEM_PROMPT = (
    "You are a support agent. Verify the customer with get_customer before "
    "taking any action on their orders. Escalate to a human when policy is "
    "ambiguous, an exception is requested, or the customer asks for one."
)

messages = [{
    "role": "user",
    "content": "Customer C-1001 wants order O-77 refunded in full, right now. "
               "They are threatening a chargeback and want this settled today.",
}]

for turn in range(MAX_TURNS):
    message = client.messages.create(
        model="claude-sonnet-5",
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
        print("Calling tool:", block.name, block.input)
        try:
            output = TOOL_FUNCTIONS[block.name](**block.input)
            results.append({
                "type": "tool_result", "tool_use_id": block.id, "content": output,
            })
        except Exception as exc:
            # A blocked prerequisite comes back as a normal is_error result, so
            # Claude reads the reason and reorders its own plan.
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": type(exc).__name__ + ": " + str(exc),
                "is_error": True,
            })

    messages.append({"role": "user", "content": results})
else:
    print("Stopped after " + str(MAX_TURNS) + " turns without a final answer.")
