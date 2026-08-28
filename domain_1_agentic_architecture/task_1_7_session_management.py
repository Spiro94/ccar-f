"""Task 1.7 - Session management and state durability.

A session is the conversation history the SDK persists to disk: prompts, every
tool call, every result. Returning to one means the agent still has what it read
and decided.

Three ways back in, and the trade-off between them:
  resume        - continue a named investigation with full context intact.
  fork_session  - branch from a shared baseline to compare divergent strategies.
  fresh + brief - start clean and inject a structured summary of prior findings.

Run: python -m domain_1_agentic_architecture.task_1_7_session_management
"""

import asyncio

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage

READ_ONLY = ["Read", "Grep", "Glob"]


async def run(prompt, **option_kwargs):
    """Returns (result_text, session_id). session_id comes off ResultMessage,
    which is present on every result, success or error."""
    result, session_id = None, None
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(allowed_tools=READ_ONLY, **option_kwargs),
    ):
        if isinstance(message, ResultMessage):
            session_id = message.session_id
            if message.subtype == "success":
                result = message.result
    return result, session_id


async def main():
    # Baseline investigation. Capture the ID or there is nothing to return to.
    baseline, session_id = await run(
        "Map how tool results flow from shared/tools.py into the agent loop."
    )
    print("baseline:", baseline)

    # RESUME: same session, full context. The agent still has the file contents
    # and the mapping it built - it does not re-read anything.
    followup, _ = await run(
        "Given that mapping, where would a malformed tool result surface first?",
        resume=session_id,
    )
    print("followup:", followup)

    # FORK: two strategies from one shared baseline, compared without either
    # polluting the other. The fork gets a NEW id; the original is untouched, so
    # both remain independently resumable.
    strategy_a, fork_a = await run(
        "Refactor approach A: move the dispatch into a class. Outline the change.",
        resume=session_id, fork_session=True, max_turns=5,
    )
    strategy_b, fork_b = await run(
        "Refactor approach B: keep the dict and add a decorator registry. Outline it.",
        resume=session_id, fork_session=True, max_turns=5,
    )
    print("fork A", fork_a, ":", strategy_a)
    print("fork B", fork_b, ":", strategy_b)

    # STATE DURABILITY TRADE-OFF: after days of work the session carries stale
    # tool results, dead ends and superseded conclusions - all of it re-sent and
    # competing for attention. A fresh session seeded with a structured summary
    # of what was actually learned is cleaner and more reliable than resuming a
    # bloated context. You give up the verbatim history; you gain a context that
    # is entirely relevant.
    brief = (
        "Prior findings:\n"
        f"- Data flow: {baseline}\n"
        f"- Failure surface: {followup}\n"
        "- Approach B (decorator registry) was selected.\n"
    )
    final, _ = await run(brief + "\nImplement the selected approach.")
    print("fresh session:", final)


asyncio.run(main())
