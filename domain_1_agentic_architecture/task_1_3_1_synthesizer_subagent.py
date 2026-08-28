"""Task 1.3.1 - Passing a subagent's result to another subagent.

Extends 1.2 with a second subagent role, a synthesizer, to show how one
subagent's output reaches another. Isolated context means there is no
automatic bridge between them: the coordinator is the only thing that sees
every researcher's final result, so it is the coordinator that must copy those
results, as text, into the synthesizer's delegation prompt. Split into its own
file so this second phase does not clutter 1.2, which only demonstrates
decomposition and delegation. Numbered under 1.3, not 1.2, to match the exam objective's own split: orchestration topology (1.2) vs. subagent invocation and context passing (1.3).

STRUCTURED METADATA, THE MAKE-OR-BREAK DETAIL: it is not enough for the
coordinator to relay findings - HOW it relays them decides whether attribution
survives. A finding flattened into a plain paragraph loses which claim came
from which source; the synthesizer then has nothing left to preserve. Content
(the claim) and metadata (its source) have to travel as separate, identifiable
fields all the way through, or a later question like "which source said X"
becomes unanswerable.

Run: python -m domain_1_agentic_architecture.task_1_3_1_synthesizer_subagent
"""

import asyncio

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import (
    query,
    ClaudeAgentOptions,
    AgentDefinition,
    ToolUseBlock,
    ResultMessage,
)

MAX_BUDGET_USD = 1.0

COORDINATOR_PROMPT = """You are a research coordinator.

Decompose the goal into assignments and delegate each one to a research
subagent. Keep each assignment BROAD enough that the subagent can adapt - name
the area to cover, not the specific conclusions to reach.

Spawn subagents in parallel when their assignments are independent.

After the subagents report, evaluate the combined coverage. If a dimension of
the goal is missing or thin, delegate again to close the gap before answering.

Once coverage is sufficient, delegate ONE more time - to the synthesizer
subagent. Its delegation prompt must include every researcher finding, WITH
EACH FINDING'S CLAIM, EVIDENCE AND SOURCE KEPT AS SEPARATE FIELDS - do not
compress a researcher's findings into a single unattributed paragraph. Return
the synthesizer's output as your final answer; do not synthesize the findings
yourself.
"""

RESEARCHER = AgentDefinition(
    description="Researches one area of a broader topic. Use for any open-ended "
                "investigation the coordinator delegates.",
    # Structured per finding, not prose: this is what makes attribution
    # possible downstream. A researcher that reports "AI tools are widely used
    # in film editing now" has already destroyed the one thing the synthesizer
    # will need to preserve.
    prompt="You research one assigned area and report findings as a list. For "
           "EACH finding, report three fields: CLAIM (the specific fact or "
           "statement), EVIDENCE (what supports it), and SOURCE (a URL or "
           "document name - never omit this, even if you have to name the "
           "search result it came from). State what you covered and what you "
           "could not cover.",
    tools=["WebSearch", "Read", "Grep", "Glob"],
    model="haiku",
)

SYNTHESIZER = AgentDefinition(
    description="Combines findings from multiple research subagents into one "
                "coherent answer, preserving source attribution. Use only "
                "after the research subagents have reported - it does no "
                "research of its own.",
    prompt="You combine research findings into a single coherent synthesis. "
           "For every claim you include, cite which source it came from - "
           "never state a finding without its attribution. When two sources "
           "disagree on a fact, do NOT arbitrarily pick one: present both "
           "values with their sources, and say the point is contested rather "
           "than silently resolving it. Do not invent findings that were not "
           "given to you.",
    # No tools: the synthesizer reasons only over the text it is handed. That is
    # the isolation boundary from 1.2 made concrete - its ENTIRE input is the
    # coordinator's prompt string, so anything not pasted in there does not
    # exist as far as this subagent is concerned.
    tools=[],
    model="haiku",
)


async def main():
    async for message in query(
        prompt="Research the current state of AI in the creative industries.",
        options=ClaudeAgentOptions(
            system_prompt=COORDINATOR_PROMPT,
            allowed_tools=["WebSearch", "Read", "Grep", "Glob", "Agent", "Task"],
            agents={"researcher": RESEARCHER, "synthesizer": SYNTHESIZER},
            env={
                "CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH": "1",
                "CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS": "2",
            },
            model="haiku",
            max_budget_usd=MAX_BUDGET_USD,
        ),
    ):
        for block in getattr(message, "content", None) or []:
            if isinstance(block, ToolUseBlock) and block.name in ("Task", "Agent"):
                print("Delegating to:", block.input.get("subagent_type"))

        if isinstance(message, ResultMessage):
            print(f"[{message.subtype}] cost=${message.total_cost_usd}")

        if hasattr(message, "result"):
            print(message.result)


asyncio.run(main())
