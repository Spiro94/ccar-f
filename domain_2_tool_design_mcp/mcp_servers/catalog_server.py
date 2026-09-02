"""A real, standalone MCP server - not the Agent SDK's in-process wrapper.

Exists for one reason: create_sdk_mcp_server (used in task_2_2) exposes tool
calls only. It has no equivalent of MCP's own resources/list capability - a
catalog of named content the client can browse WITHOUT making a tool call.
The exam's "MCP resources as content catalogs" skill needs that capability for
real, so this uses the `mcp` package directly.

One tool (get_customer_orders, same shape as task_2_2's) and one resource
(catalog://customers) exposing which customer IDs exist. The point of the
resource: an agent can see what's available before ever calling the tool,
instead of guessing IDs via trial-and-error tool calls - "to reduce
exploratory tool calls," in the exam's own words.

Run directly for a quick manual smoke test (it will sit waiting on stdin,
because stdio transport expects an MCP client on the other end - Ctrl+C to
exit):
    python -m domain_2_tool_design_mcp.mcp_servers.catalog_server

In practice this is spawned as a subprocess by the Agent SDK - see
task_2_4_mcp_server_integration.py, which launches it via `command`/`args`
in a stdio mcp_servers config rather than running it standalone.
"""

from mcp.server.mcpserver import MCPServer

CUSTOMERS = {
    "gold-1": ["O-1", "O-2"],
    "gold-2": ["O-3"],
    "gold-3": [],
}

server = MCPServer(name="catalog", version="1.0.0")


@server.tool(description="Look up a customer's order IDs by customer_id.")
def get_customer_orders(customer_id: str) -> str:
    orders = CUSTOMERS.get(customer_id)
    if orders is None:
        return f"No such customer: {customer_id}"
    return f"{customer_id}: {orders}" if orders else f"{customer_id}: no orders on record"


# A RESOURCE, not a tool call: the client can read this directly, no
# arguments, no "guess an ID and see if it exists" round trip. This is what
# create_sdk_mcp_server's tool-only model cannot express.
@server.resource(
    "catalog://customers",
    name="customer_catalog",
    description="Every customer_id this server knows about, so callers don't "
                "have to guess IDs via trial-and-error tool calls.",
    mime_type="text/plain",
)
def customer_catalog() -> str:
    return "\n".join(sorted(CUSTOMERS.keys()))


if __name__ == "__main__":
    server.run()  # transport defaults to "stdio"
