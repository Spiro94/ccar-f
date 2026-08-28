"""Task 1.5 - Agent SDK hooks.

Hooks are programmatic interception points. PreToolUse runs BEFORE a tool
executes and can block it; PostToolUse runs AFTER and can rewrite the result
before Claude ever sees it.

Where this differs from Task 1.4: the gate there lived inside the executor,
which only works for tools you wrote. A hook intercepts any tool, including
built-ins and MCP tools whose implementation you do not own.

Run: python -m domain_1_agentic_architecture.task_1_5_agent_sdk_hooks
"""

import asyncio

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess
from datetime import datetime, timezone

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, HookMatcher

MAX_BUDGET_USD = 1.0

REFUND_LIMIT = 500


async def block_large_refunds(input_data, tool_use_id, context):
    """PreToolUse: check parameters before execution and refuse policy violations."""
    amount = input_data["tool_input"].get("amount", 0)
    if amount > REFUND_LIMIT:
        return {
            "hookSpecificOutput": {
                "hookEventName": input_data["hook_event_name"],
                "permissionDecision": "deny",
                # The reason is fed back to the model so it routes to escalation
                # instead of retrying the same call with the same amount.
                "permissionDecisionReason": (
                    f"Refunds over ${REFUND_LIMIT} require a human operator. "
                    "Escalate this case instead."
                ),
            }
        }
    # An empty dict means "no opinion" - the call proceeds through normal
    # permission evaluation.
    return {}


def _normalise_timestamp(value):
    """Unix epoch, ISO 8601, or already-normalised - all out as ISO 8601 UTC."""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value, tz=timezone.utc).isoformat()
    return str(value)


STATUS_ALIASES = {
    "OK": "success", "0": "success", "complete": "success", "COMPLETED": "success",
    "ERR": "error", "1": "error", "failed": "error", "FAILURE": "error",
}


async def normalise_tool_output(input_data, tool_use_id, context):
    """PostToolUse: reconcile heterogeneous formats from different MCP servers.

    Each server invents its own timestamp format and status vocabulary. Left
    alone, Claude has to reason about the differences on every turn and burns
    context doing it. Normalising here means the model sees one shape.
    """
    response = input_data.get("tool_response")
    if not isinstance(response, dict):
        return {}

    cleaned = dict(response)
    for key in ("timestamp", "created_at", "updated_at"):
        if key in cleaned:
            cleaned[key] = _normalise_timestamp(cleaned[key])
    if "status" in cleaned:
        raw = str(cleaned["status"])
        cleaned["status"] = STATUS_ALIASES.get(raw, raw.lower())

    return {
        "hookSpecificOutput": {
            "hookEventName": input_data["hook_event_name"],
            # Replaces what Claude sees. `additionalContext` would append a note
            # instead, leaving the original heterogeneous payload in place.
            "updatedToolOutput": cleaned,
        }
    }


async def main():
    options = ClaudeAgentOptions(
        hooks={
            # The matcher filters by tool name; a HookMatcher without one fires
            # for every tool of that event.
            "PreToolUse": [HookMatcher(matcher="process_refund", hooks=[block_large_refunds])],
            "PostToolUse": [HookMatcher(matcher="^mcp__", hooks=[normalise_tool_output])],
        },
        allowed_tools=["Read", "Grep", "Glob"],
        model="haiku",
        max_budget_usd=MAX_BUDGET_USD,
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query("Summarise the most recent order events.")
        async for message in client.receive_response():
            if hasattr(message, "result"):
                print(message.result)


asyncio.run(main())
