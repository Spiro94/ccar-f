"""Task 2.4 - Integrating an MCP server into an agent workflow.

Two distinct integration paths the exam names, both demonstrated here:

1. IN CODE: pass mcp_servers={"name": {"command": ..., "args": [...]}} to
   ClaudeAgentOptions - the Agent SDK spawns the server as a subprocess over
   stdio. See main() below, which does exactly this for the standalone server
   in mcp_servers/catalog_server.py.

2. VIA CONFIG FILE (.mcp.json): the same shape, but written to a JSON file
   instead of Python. See example.mcp.json in this directory - deliberately
   named "example.mcp.json", NOT ".mcp.json", so nothing in this repo
   auto-loads it. A real ".mcp.json" at a project's root is picked up
   automatically (via the default "project" setting source) the moment
   someone runs Claude Code with that directory as their cwd; naming a demo
   file that would make this repo silently behave differently for anyone who
   opens a Claude Code session here.

PROJECT vs USER SCOPE: a real .mcp.json at the project root is committed to
git and shared with the whole team - the right place for tooling everyone on
the project needs (a shared database server, an internal API). ~/.claude.json
is per-machine and personal - the right place for something experimental, or
credentialed to just you, that shouldn't end up in a teammate's session.

ENV VAR EXPANSION: example.mcp.json's "env" block uses "${SOME_TOKEN}" -
Claude Code expands that from the process environment when it starts the
server, so a credential never has to be committed to the config file itself.

MCP RESOURCES, THE REASON THIS FILE EXISTS AT ALL: a resource existing on the
server is not enough by itself. Discovering and reading one goes through
THREE SEPARATE built-in tools - ListMcpResourcesTool, ReadMcpResourceTool,
ReadMcpResourceDirTool - which must be in allowed_tools same as any other
tool. On a first pass with an implicit prompt ("what customers does it know
about?") and no mention of these tools by name, Haiku never reached for them
even with them allowed - it treated get_customer_orders as the only path
and asked to guess an ID. Only naming ListMcpResourcesTool/ReadMcpResourceTool
explicitly in the prompt got it to use them, at which point ToolSearch loaded
their deferred schemas and both ran correctly. That gap - a capability being
available doesn't mean a weaker model reliably discovers it - is itself very
on-theme for a tool-design domain, so the prompt below is written the way
that actually works rather than the way that was hoped to work.

Run: python -m domain_2_tool_design_mcp.task_2_4_mcp_server_integration
"""

import asyncio
import pathlib
import sys

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import query, ClaudeAgentOptions, SystemMessage, ResultMessage

SERVER_SCRIPT = pathlib.Path(__file__).parent / "mcp_servers" / "catalog_server.py"

# Code-based stdio config: spawns `python3 catalog_server.py` as a subprocess.
# The command/args shape here is IDENTICAL to what goes inside a .mcp.json
# "mcpServers" block - see example.mcp.json for that form of the same thing.
MCP_SERVERS = {
    "catalog": {
        "command": sys.executable,
        "args": [str(SERVER_SCRIPT)],
    }
}


async def main():
    options = ClaudeAgentOptions(
        mcp_servers=MCP_SERVERS,
        # Wildcard covers this server's own tool; the three ...McpResource...
        # names are SEPARATE built-in tools that let Claude browse and read
        # MCP resources at all. A resource existing on the server is not
        # enough by itself - without these, Claude has no way to discover it.
        allowed_tools=[
            "mcp__catalog__*",
            "ListMcpResourcesTool",
            "ReadMcpResourceTool",
        ],
        model="haiku",
        max_budget_usd=1.0,
    )

    async for message in query(
        prompt="Use ListMcpResourcesTool to see what MCP resources are "
               "available, then use ReadMcpResourceTool to read the "
               "catalog://customers resource. Report what it contains, then "
               "look up orders for the first customer ID listed.",
        options=options,
    ):
        # Confirms the subprocess actually connected - "failed" or
        # "needs-auth" here means the rest of the run can't be trusted.
        if isinstance(message, SystemMessage) and message.subtype == "init":
            servers = message.data.get("mcp_servers", [])
            print("MCP server status:", servers)

        if isinstance(message, ResultMessage) and message.subtype == "success":
            print("\n" + message.result)


asyncio.run(main())
