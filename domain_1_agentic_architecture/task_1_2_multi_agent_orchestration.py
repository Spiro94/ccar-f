"""Task 1.2 - Multi-Agent Orchestration (hub-and-spoke).

Topology: one coordinator decomposes the goal, delegates to specialised
subagents, and aggregates their results. All inter-agent communication routes
back through the coordinator - subagents never talk to each other - which is
what keeps observability and error handling in one place.

Run: python -m domain_1_agentic_architecture.task_1_2_multi_agent_orchestration
"""

import asyncio

from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ToolUseBlock

# NARROW DECOMPOSITION RISK: the coordinator is told to keep subagent
# assignments broad. Scoping "AI in creative industries" down to visual arts
# would silently lose music, writing and film - the subagent cannot recover a
# dimension the coordinator never asked about.
COORDINATOR_PROMPT = """You are a research coordinator.

Decompose the goal into assignments and delegate each one to a research
subagent. Keep each assignment BROAD enough that the subagent can adapt - name
the area to cover, not the specific conclusions to reach.

Spawn subagents in parallel when their assignments are independent.

After the subagents report, evaluate the combined coverage. If a dimension of
the goal is missing or thin, delegate again to close the gap before answering.
"""

RESEARCHER = AgentDefinition(
    description="Researches one area of a broader topic. Use for any open-ended "
                "investigation the coordinator delegates.",
    # ISOLATED CONTEXT: this prompt plus the coordinator's Agent-tool prompt is
    # the subagent's whole context. It does not inherit the coordinator's
    # conversation or any sibling's findings, so anything it needs must be
    # stated explicitly in the delegation prompt.
    prompt="You research one assigned area and report concrete findings. "
           "State what you covered and what you could not cover.",
    tools=["WebSearch", "Read", "Grep", "Glob"],
    model="sonnet",
)


async def main():
    async for message in query(
        prompt="Research the current state of AI in the creative industries.",
        options=ClaudeAgentOptions(
            system_prompt=COORDINATOR_PROMPT,
            # "Agent" must be allowed for the coordinator to spawn subagents at
            # all. The exam calls this the Task tool; Claude Code renamed it to
            # Agent in v2.1.63 and current SDKs emit "Agent" in tool_use blocks
            # while "Task" survives in the system:init tool list. Match both.
            allowed_tools=["WebSearch", "Read", "Grep", "Glob", "Agent", "Task"],
            agents={"researcher": RESEARCHER},
            env={
                "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
                "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "5",
            },
            max_budget_usd=5.0,
        ),
    ):
        for block in getattr(message, "content", None) or []:
            # PARALLEL SPAWNING: several of these blocks in one coordinator
            # response means the subagents run concurrently rather than in
            # sequence. One block per response is sequential delegation.
            if isinstance(block, ToolUseBlock) and block.name in ("Task", "Agent"):
                print("Delegating to:", block.input.get("subagent_type"))

        if hasattr(message, "result"):
            # Only the subagent's FINAL message reaches the coordinator. Its
            # intermediate tool calls and results stay in its own context - that
            # isolation is the point of delegating.
            print(message.result)


asyncio.run(main())
