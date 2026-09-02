"""Task 2.5 - Selecting built-in tools effectively.

Two skills the exam names, demonstrated against real files:

1. INCREMENTAL EXPLORATION: start with Grep to find entry points (which files
   define or reference a name), then Read only the files that matter, rather
   than reading every file upfront. explore_tool_functions_usage() below asks
   the agent to trace TOOL_FUNCTIONS - a name genuinely spread across several
   files in this repo (shared/tools.py defines it, several domain_1 task
   files import and dispatch through it) - this way, so the trace is real,
   not staged.

2. EDIT'S FALLBACK: Edit needs a UNIQUE text match to know what to change: a
   string that appears twice in a file makes Edit refuse rather than guess
   which occurrence you meant. The documented fallback is Read the whole
   file, then Write the corrected version back. edit_fallback_demo() forces
   exactly that situation with a real file containing a repeated line.

SAFETY: the fallback demo needs live Write/Edit access, which is not
something to hand an agent over this whole repo on a prompt's say-so alone -
Domain 1's Task 1.4 covers exactly why a prompt instruction isn't a
boundary. The first version of this file tried to enforce that with
can_use_tool - and the SDK warned at runtime that the callback never ran:
listing "Write"/"Edit" in allowed_tools auto-approves the WHOLE tool before
can_use_tool is ever consulted, so the "gate" was decorative. The fix,
straight from that warning: a PreToolUse hook, which fires regardless of
allowed_tools. scratch_file_only_gate below denies every Write/Edit call
whose file_path isn't the one designated scratch file - this is now a real
gate, not one that only looked like one.

Run: python -m domain_2_tool_design_mcp.task_2_5_builtin_tools
"""

import asyncio
import pathlib

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    ResultMessage,
    AssistantMessage,
    ToolUseBlock,
    HookMatcher,
)

SCRATCH_DIR = pathlib.Path(__file__).parent / "_scratch"
SCRATCH_FILE = SCRATCH_DIR / "edit_fallback_demo.txt"


async def explore_tool_functions_usage():
    """Grep first, Read only what Grep points at - not every file upfront."""
    options = ClaudeAgentOptions(
        allowed_tools=["Grep", "Glob", "Read"],
        model="haiku",
        max_budget_usd=1.0,
    )
    calls = []
    result = None
    async for message in query(
        prompt="Trace where TOOL_FUNCTIONS is defined and used in this repo. "
               "Start with Grep to find every file that references the name - "
               "do not Read files you haven't first located via Grep or Glob. "
               "Report which files define it and which import/dispatch through it.",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    calls.append(block.name)
        if isinstance(message, ResultMessage) and message.subtype == "success":
            result = message.result
    # The actual proof of "incremental": Grep/Glob calls should precede Reads,
    # not the other way around.
    print("Tool call order:", calls)
    print(result)


async def scratch_file_only_gate(input_data, tool_use_id, context):
    """PreToolUse hook: fires unconditionally, unlike can_use_tool with a
    whole-tool allow entry. Denies Write/Edit on anything but the scratch
    file - the actual enforcement boundary for this demo."""
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input", {})
    if tool_name in ("Write", "Edit"):
        path = tool_input.get("file_path", "")
        if pathlib.Path(path).resolve() != SCRATCH_FILE.resolve():
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason":
                        f"Only {SCRATCH_FILE} may be modified in this demo.",
                }
            }
    return {}


async def edit_fallback_demo():
    """A repeated line makes Edit's unique-match requirement fail on
    purpose, so the agent has to fall back to Read + Write."""
    SCRATCH_DIR.mkdir(exist_ok=True)
    SCRATCH_FILE.write_text(
        "status: pending\n"
        "note: first item\n"
        "status: pending\n"
        "note: second item\n"
    )

    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Write", "Edit"],
        hooks={"PreToolUse": [HookMatcher(matcher="Write|Edit", hooks=[scratch_file_only_gate])]},
        model="haiku",
        max_budget_usd=1.0,
    )
    calls = []
    async for message in query(
        prompt=f"In {SCRATCH_FILE}, change ONLY the second 'status: pending' "
               f"line (the one right before 'note: second item') to "
               f"'status: done'. Try Edit first; if it can't find a unique "
               f"match, fall back to Read then Write the corrected file.",
        options=options,
    ):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, ToolUseBlock):
                    calls.append(block.name)

    print("Tool call order:", calls)
    print("--- resulting file ---")
    print(SCRATCH_FILE.read_text())


async def main():
    print("=== Incremental exploration ===")
    await explore_tool_functions_usage()
    print("\n=== Edit-fails-on-non-unique-match fallback ===")
    await edit_fallback_demo()


asyncio.run(main())
