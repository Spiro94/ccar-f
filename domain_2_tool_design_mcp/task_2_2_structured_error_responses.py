"""Task 2.2 - Structured error responses for MCP tools.

The MCP isError flag is HOW a tool reports failure; it says nothing about
WHAT kind of failure it was. A uniform "Operation failed" behind isError still
leaves Claude unable to decide whether to retry, rephrase, or give up - the
exact problem the exam names. The fix is structured error METADATA riding
alongside isError: an errorCategory (transient / validation / business /
permission) and an isRetryable flag, so the agent's next move is a decision
it can actually make instead of a guess.

Also demonstrated: a VALID EMPTY RESULT (a lookup that succeeded and found
nothing) is not an error at all and must not be reported as one - conflating
"found zero rows" with "the query failed" is its own named failure mode.

Run: python -m domain_2_tool_design_mcp.task_2_2_structured_error_responses
"""

import asyncio
import json

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import tool, create_sdk_mcp_server, query, ClaudeAgentOptions

# Simulated backend. "gold-1" and "gold-2" exist and have orders; "gold-3"
# exists but genuinely has none - that is the valid-empty-result case, not a
# failure. Anything else raises the four error categories in turn based on
# customer_id, purely so this file can demonstrate all four deterministically.
CUSTOMERS = {"gold-1": ["O-1", "O-2"], "gold-2": ["O-3"], "gold-3": []}


def _error(category, retryable, message):
    """One shape for every failure. Claude reads errorCategory and isRetryable
    to decide what to do next - not by re-parsing message text."""
    return {
        "content": [{"type": "text", "text": json.dumps({
            "errorCategory": category,
            "isRetryable": retryable,
            "message": message,
        })}],
        "is_error": True,
    }


@tool(
    "get_customer_orders",
    "Look up a customer's orders by ID. customer_id starting with 'gold-' is "
    "a real lookup; 'transient-', 'invalid-', 'forbidden-' or 'business-' "
    "trigger each documented error category for testing.",
    {"customer_id": str},
)
async def get_customer_orders(args):
    customer_id = args["customer_id"]

    if customer_id.startswith("transient-"):
        # TRANSIENT: the backend itself is fine, this one call wasn't. Retrying
        # the exact same call is the correct next move, so isRetryable is True.
        return _error("transient", True, "Order service timed out after 5s.")

    if customer_id.startswith("invalid-"):
        # VALIDATION: the input itself is malformed. Retrying the same call
        # cannot succeed - only a corrected input can - so isRetryable is False.
        return _error("validation", False,
                      "customer_id must match ^gold-[0-9]+$, got: " + customer_id)

    if customer_id.startswith("forbidden-"):
        # PERMISSION: the caller isn't allowed to see this customer's data.
        # Not retryable, and not something a corrected input fixes either -
        # it needs an authorization decision, which is why it's its own
        # category rather than folded into "validation".
        return _error("permission", False,
                      "Not authorized to view orders for " + customer_id)

    if customer_id.startswith("business-"):
        # BUSINESS: the request is well-formed and permitted, but violates a
        # policy - e.g. the account is suspended. customer-friendly, not
        # retryable, and distinct from "permission" (which is about WHO is
        # asking, not about the STATE of the account being asked about).
        return _error("business", False,
                      "This account is suspended pending fraud review; orders "
                      "cannot be retrieved until it is cleared.")

    orders = CUSTOMERS.get(customer_id)
    if orders is None:
        return _error("validation", False, "No such customer: " + customer_id)

    # VALID EMPTY RESULT: the lookup succeeded. Zero orders is a fact about the
    # customer, not a failure of the tool - is_error stays unset (False/absent).
    return {"content": [{"type": "text", "text": json.dumps({"orders": orders})}]}


orders_server = create_sdk_mcp_server(
    name="orders", version="1.0.0", tools=[get_customer_orders]
)


async def ask(customer_id):
    options = ClaudeAgentOptions(
        system_prompt=(
            "You have a get_customer_orders tool. Its errors carry an "
            "errorCategory and isRetryable field as JSON. Use them: retry "
            "transient errors once yourself without asking the user; for "
            "everything else, explain the specific category to the user "
            "rather than a generic 'something went wrong'."
        ),
        mcp_servers={"orders": orders_server},
        allowed_tools=["mcp__orders__get_customer_orders"],
        model="haiku",
        max_budget_usd=1.0,
    )
    result = None
    async for message in query(prompt=f"Look up orders for customer {customer_id}.", options=options):
        if hasattr(message, "result"):
            result = message.result
    return result


async def main():
    for customer_id in ["gold-1", "gold-3", "transient-x", "invalid-x", "forbidden-x", "business-x"]:
        print(f"=== {customer_id} ===")
        print(await ask(customer_id))
        print()


asyncio.run(main())
