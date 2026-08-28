"""Task 1.2 - Multi-Agent Orchestration (hub-and-spoke).

Topology: one coordinator decomposes the goal, delegates to specialised
subagents, and aggregates their results. All inter-agent communication routes
back through the coordinator - subagents never talk to each other - which is
what keeps observability and error handling in one place.

Two subagent types exist so the coordinator has something to choose between:
routing every query through the full multi-researcher pipeline regardless of
complexity is itself a documented failure mode, not just an inefficiency.

Run: python -m domain_1_agentic_architecture.task_1_2_multi_agent_orchestration
"""

import asyncio

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ToolUseBlock

# NARROW DECOMPOSITION RISK: the coordinator is told to keep subagent
# assignments broad. Scoping "AI in creative industries" down to visual arts
# would silently lose music, writing and film - the subagent cannot recover a
# dimension the coordinator never asked about.
MAX_BUDGET_USD = 1.0

COORDINATOR_PROMPT = """You are a research coordinator.

First, judge the query's complexity. A narrow, single-fact question ("when was
X founded?") does not need the full research pipeline - delegate it directly
to a fact-checker subagent and stop. Only decompose into multiple research
assignments for genuinely broad, multi-dimensional topics. Choosing the full
pipeline for every query, regardless of complexity, wastes turns and budget.

When you do decompose: keep each assignment BROAD enough that the subagent can
adapt - name the area to cover, not the specific conclusions to reach - and
PARTITION assignments so they cover distinct subtopics or source types. Two
researchers given overlapping assignments duplicate work instead of extending
coverage.

Spawn subagents in parallel when their assignments are independent.

After the subagents report, evaluate the combined coverage. If a dimension of
the goal is missing or thin, delegate again with a targeted assignment to
close the gap, then re-run synthesis - do not just append the new findings.
"""

RESEARCHER = AgentDefinition(
    description="Researches one area of a broader topic. Use for open-ended, "
                "multi-source investigation the coordinator delegates.",
    # ISOLATED CONTEXT: this prompt plus the coordinator's Agent-tool prompt is
    # the subagent's whole context. It does not inherit the coordinator's
    # conversation or any sibling's findings, so anything it needs must be
    # stated explicitly in the delegation prompt.
    prompt="You research one assigned area and report concrete findings. "
           "State what you covered and what you could not cover.",
    tools=["WebSearch", "Read", "Grep", "Glob"],
    model="haiku",
)

# DYNAMIC SUBAGENT SELECTION: a second, narrower subagent type gives the
# coordinator something to choose between. Without an alternative, every query
# - simple or broad - routes through the same full research pipeline, which is
# the inefficiency the coordinator prompt above is now told to avoid.
FACT_CHECKER = AgentDefinition(
    description="Answers one narrow, well-defined factual question with a "
                "single lookup. Use for queries that do not need multi-source "
                "research - a date, a name, a single statistic.",
    prompt="You answer exactly one factual question. Look it up, state the "
           "answer and your source, and stop - do not broaden the scope.",
    tools=["WebSearch"],
    model="haiku",
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
            agents={"researcher": RESEARCHER, "fact-checker": FACT_CHECKER},
            env={
                "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
                "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "2",
            },
            model="haiku",
            max_budget_usd=MAX_BUDGET_USD,
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
