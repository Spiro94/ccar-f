"""Task 3.4 - Plan mode vs direct execution, and the Explore subagent.

Plan mode's job: explore and design BEFORE any file changes are made, so an
architectural mistake is caught by re-reading a plan, not by reverting a
half-finished migration. Direct execution's job: skip that ceremony when the
scope is already fully known - the exam's own contrast is "microservice
restructuring, library migrations affecting 45+ files, choosing between
integration approaches" (plan mode) versus "a single-file bug fix with a
clear stack trace, adding a date validation conditional" (direct execution).

recommend_mode() below is that decision rule as actual code, not a vibe -
useful for the same reason task_1_4's programmatic gate was: a written rule
you can point at is checkable, a felt sense of "this seems complex" is not.

The Explore subagent solves a DIFFERENT problem that often precedes this
decision: even a direct-execution task can need enough file reading to blow
up your main context before you've written a line of code. Explore runs that
reading in an isolated context and returns only a summary - Domain 1's
subagent isolation applied specifically to the "figure out what's going on
before I touch anything" phase.

Run: python -m domain_3_claude_code_configuration.task_3_4_plan_mode_vs_direct
"""

import asyncio
from dataclasses import dataclass

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage


@dataclass
class TaskProfile:
    files_touched: int
    architectural_decision: bool  # does this change how the system is structured?
    multiple_valid_approaches: bool  # is there more than one reasonable way to do it?
    scope_is_fully_known: bool  # could you name every file that needs to change, right now?


def recommend_mode(profile: TaskProfile) -> str:
    # Any ONE of these is sufficient on its own - they don't need to co-occur.
    # A 45+ file migration with only one sane approach still needs plan mode;
    # so does a 3-file change where the right architecture is genuinely unclear.
    if profile.architectural_decision:
        return "plan mode - architectural decisions need review before commitment"
    if profile.multiple_valid_approaches:
        return "plan mode - competing approaches should be compared before picking one"
    if profile.files_touched >= 45:
        return "plan mode - scope this large risks costly rework if wrong"
    if profile.scope_is_fully_known and profile.files_touched <= 3:
        return "direct execution - scope is small and already fully known"
    return "plan mode - default to exploring when scope isn't fully known yet"


async def explore_before_deciding():
    """A direct-execution-shaped task ('fix the bug in X') can still need a
    discovery phase first. Explore keeps that discovery from becoming the
    thing that fills up the main conversation's context."""
    options = ClaudeAgentOptions(
        allowed_tools=["Read", "Grep", "Glob", "Agent", "Task"],
        model="haiku",
        max_budget_usd=1.0,
    )
    result = None
    async for message in query(
        prompt="Use the Explore agent to find every place in this repo that "
               "defines a TOOL_FUNCTIONS dict, and report just the file paths "
               "and what tools each one dispatches - nothing else.",
        options=options,
    ):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            result = message.result
    return result


if __name__ == "__main__":
    cases = [
        TaskProfile(files_touched=45, architectural_decision=False,
                   multiple_valid_approaches=False, scope_is_fully_known=True),
        TaskProfile(files_touched=1, architectural_decision=False,
                   multiple_valid_approaches=False, scope_is_fully_known=True),
        TaskProfile(files_touched=3, architectural_decision=False,
                   multiple_valid_approaches=True, scope_is_fully_known=True),
        TaskProfile(files_touched=1, architectural_decision=True,
                   multiple_valid_approaches=False, scope_is_fully_known=True),
    ]
    for case in cases:
        print(case, "->", recommend_mode(case))

    print()
    print(asyncio.run(explore_before_deciding()))
