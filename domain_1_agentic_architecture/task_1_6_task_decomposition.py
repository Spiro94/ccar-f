"""Task 1.6 - Task decomposition strategies.

Prompt chaining: a fixed sequence of steps you write in advance. Right when the
workflow is predictable - the same review, in the same order, every time.

Dynamic decomposition: the agent builds a plan and revises it from intermediate
findings. Right when what to do next depends on what step one turned up. The
exam's own example is "add comprehensive tests to a legacy codebase": map
structure, find high-impact areas, then build a plan that adapts as
dependencies surface - see dynamic_decomposition_review() below.

Run: python -m domain_1_agentic_architecture.task_1_6_task_decomposition
"""

import asyncio

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import query, ClaudeAgentOptions

MAX_BUDGET_USD = 1.0

FILES = ["shared/tools.py", "domain_1_agentic_architecture/task_1_1_agentic_loop.py"]


async def run(prompt, resume=None):
    result = None
    options = ClaudeAgentOptions(allowed_tools=["Read", "Grep", "Glob"],
        model="haiku",
        max_budget_usd=MAX_BUDGET_USD,
        resume=resume)
    session_id = None
    async for message in query(prompt=prompt, options=options):
        if hasattr(message, "session_id"):
            session_id = message.session_id
        if hasattr(message, "result"):
            result = message.result
    return result, session_id


async def prompt_chaining_review():
    """Fixed steps. YOU own the control flow; the model fills in each stage."""
    findings, session = await run("List the functions defined in shared/tools.py.")
    risks, _ = await run("For each function you listed, name its failure modes.",
                         resume=session)
    return risks


async def per_file_then_cross_file_review():
    """PER-FILE + CROSS-FILE PASS.

    One prompt holding every file dilutes attention - defects in the middle of a
    long context get missed. So: analyse each file in isolation first, then run a
    SEPARATE pass whose only job is the integration view (data flow between the
    files), seeded with the per-file summaries rather than the files themselves.
    """
    per_file = []
    for path in FILES:
        summary, _ = await run(f"Review {path} in isolation. Report defects and "
                               f"the values it exports or consumes.")
        per_file.append(f"### {path}\n{summary}")

    joined = "\n\n".join(per_file)
    cross_file, _ = await run(
        "Here are independent per-file reviews:\n\n" + joined +
        "\n\nNow analyse ONLY the cross-file concerns: how data flows between "
        "these files, and any mismatch between what one exports and another "
        "expects. Ignore defects local to a single file."
    )
    return cross_file


async def dynamic_decomposition_review():
    """The plan is the model's to build and revise as findings come in.

    The exam's canonical example for this pattern: "add comprehensive tests to
    a legacy codebase" - map structure, identify high-impact areas, then build
    a prioritized plan that adapts as dependencies are discovered. Unlike the
    per-file pass above, the STEPS themselves aren't fixed in advance; what the
    agent does next depends on what the mapping step turns up. A fixed
    checklist ("test file 1, then file 2, then file 3") cannot adapt when step
    one reveals that files 4 and 5 share untested state file 3 depends on.
    """
    # run() only allows Read/Grep/Glob, so this asks for a PLAN, not written
    # test files - the point being demonstrated is adaptive planning, not the
    # test-writing itself.
    result, _ = await run(
        "This repository has no tests. Produce a plan for adding comprehensive "
        "test coverage to it. First map its structure and identify the "
        "highest-impact areas to cover. Then build a prioritized plan from "
        "what you found, adapting it as you discover dependencies between "
        "files - do not hand back a fixed, predetermined checklist decided "
        "before you looked at the code."
    )
    return result


async def main():
    print(await per_file_then_cross_file_review())


asyncio.run(main())
