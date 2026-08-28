"""Task 1.3 - Subagent configuration with AgentDefinition.

AgentDefinition is where a subagent's system prompt, description and tool
restrictions are declared. `description` is what the coordinator matches against
when deciding whom to delegate to; `prompt` is the subagent's own system prompt.

Run: python -m domain_1_agentic_architecture.task_1_3_subagent_definitions
"""

import asyncio

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition

MAX_BUDGET_USD = 1.0

AGENTS = {
    "security-reviewer": AgentDefinition(
        # Read by the coordinator to decide WHEN to use this subagent. Vague
        # descriptions are the usual reason delegation never happens.
        description="Reviews code for security vulnerabilities. Use for auth, "
                    "input handling, and secrets management reviews.",
        prompt="You are a security reviewer. Report vulnerabilities with file "
               "and line references. Do not modify any file.",
        # TOOL RESTRICTION: a tool left out is absent from the subagent's
        # session entirely - no permission prompt, no error. This one physically
        # cannot write, so "do not modify" is enforced, not merely requested.
        tools=["Read", "Grep", "Glob"],
        model="haiku",
    ),
    "test-runner": AgentDefinition(
        description="Runs test suites and analyses failures. Use for test "
                    "execution and coverage questions.",
        prompt="You run tests and report which failed and why.",
        tools=["Bash", "Read", "Grep"],
        # maxTurns caps this subagent alone; its output is marked partial when
        # it stops here. Note the camelCase - AgentDefinition keeps the wire
        # spelling, unlike ClaudeAgentOptions which is snake_case.
        maxTurns=15,
    ),
}


async def main():
    async for message in query(
        # Naming the agent explicitly bypasses description-matching and
        # guarantees which subagent runs.
        prompt="Use the security-reviewer agent to review shared/tools.py.",
        options=ClaudeAgentOptions(
            allowed_tools=["Read", "Grep", "Glob", "Bash", "Agent", "Task"],
            agents=AGENTS,
            model="haiku",
            max_budget_usd=MAX_BUDGET_USD,
        ),
    ):
        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
