"""Task 1.3.2 - Deterministic context passing between subagents.

1.3.1 relies on the coordinator's own judgment - a prompt instruction - to copy
researcher findings into the synthesizer's delegation. That is probabilistic:
nothing forces Claude to actually do it, the same gap Task 1.4 covers between a
prompt rule and a programmatic prerequisite. This file gets the same
researcher -> synthesizer handoff with a PROGRAMMATIC guarantee instead: the
Python code, not Claude, reads each researcher's result and builds the
synthesizer's prompt.

Trade-off: this can never skip a finding or forget the synthesis step, but it
also cannot adapt the plan the way 1.3.1's iterative refinement can - the
research areas and the two-phase structure are fixed before the first request,
not decided by a coordinator reading the goal.

Run: python -m domain_1_agentic_architecture.task_1_3_2_deterministic_handoff
"""

import asyncio
import json

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import query, ClaudeAgentOptions, AgentDefinition, ResultMessage

MAX_BUDGET_USD = 1.0

# Decomposition happens HERE, in Python, not inside a coordinator's judgment -
# the counterpart to 1.3.1's "keep assignments broad, let Claude decide the
# split." Fixed and explicit is the trade for guaranteed coverage.
RESEARCH_AREAS = [
    "AI in music production and composition",
    "AI in visual arts and design",
    "AI in film and video production",
]

# A single-purpose system prompt: this session is told to execute exactly one
# named delegation, not to decompose or plan. It is not a coordinator - it has
# no room to decide anything, which is the point of the deterministic version.
DELEGATE_ONLY_PROMPT = (
    "Delegate to exactly the subagent named in the user's instruction, passing "
    "its full instruction as the delegation prompt. Do not decompose further, "
    "do not add subagents of your own, and do not answer without delegating."
)

RESEARCHER = AgentDefinition(
    description="Researches one area of a broader topic.",
    # Structured per finding, same shape as 1.3.1: CLAIM / EVIDENCE / SOURCE as
    # separate fields, not prose. The model still produces free text here - the
    # deterministic guarantee below is about what the CODE does with that text,
    # not about replacing the model's own formatting discipline.
    prompt="You research one assigned area and report findings as a list. For "
           "EACH finding, report three fields: CLAIM, EVIDENCE, and SOURCE (a "
           "URL or document name - never omit this). State what you covered "
           "and what you could not cover.",
    tools=["WebSearch", "Read", "Grep", "Glob"],
    model="haiku",
)

SYNTHESIZER = AgentDefinition(
    description="Combines findings from multiple research subagents into one "
                "coherent answer, preserving source attribution.",
    prompt="You combine research findings into a single coherent synthesis. "
           "For every claim you include, cite which source and area it came "
           "from. When two sources disagree on a fact, present both values "
           "with their sources rather than picking one. Do not invent "
           "findings that were not given to you.",
    tools=[],
    model="haiku",
)


async def run(prompt, agents, allowed_tools):
    """One query() call, driven to completion. Returns the final result text."""
    result = None
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            system_prompt=DELEGATE_ONLY_PROMPT,
            allowed_tools=allowed_tools,
            agents=agents,
            model="haiku",
            max_budget_usd=MAX_BUDGET_USD,
        ),
    ):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            result = message.result
    return result


async def main():
    # Phase 1: one query per area, naming the subagent explicitly so this is a
    # single guaranteed delegation, not a decomposition Claude might reshape.
    # asyncio.gather runs the three sessions concurrently - a different
    # mechanism from 1.2's PARALLEL SPAWNING (several Task calls inside one
    # coordinator turn). Here it is several independent query() calls run
    # concurrently by the Python event loop instead.
    findings = await asyncio.gather(*[
        run(
            f"Use the researcher agent to investigate: {area}",
            {"researcher": RESEARCHER},
            ["WebSearch", "Read", "Grep", "Glob", "Agent", "Task"],
        )
        for area in RESEARCH_AREAS
    ])

    # Phase 2: THE explicit hand-off. No model judgment decides what the
    # synthesizer sees, and the code guarantees every finding is in it, unlike
    # 1.3.1's prompt instruction. STRUCTURED METADATA made concrete: `area` is
    # attached to each finding as a genuine field in a data structure - not
    # woven into a sentence the synthesizer has to parse back out - so content
    # (the finding) and its metadata (which area produced it) cannot get
    # separated the way free prose can lose that link.
    tagged_findings = [
        {"area": area, "finding": finding}
        for area, finding in zip(RESEARCH_AREAS, findings)
    ]
    for entry in tagged_findings:
        print(f"--- {entry['area']} ---\n{entry['finding']}\n")

    synthesis_prompt = (
        "Use the synthesizer agent to combine the following research findings "
        "into one coherent answer. Each entry's \"area\" field is metadata - "
        "keep it attached to its finding when you cite sources:\n\n"
        + json.dumps(tagged_findings, indent=2)
    )
    synthesis = await run(synthesis_prompt, {"synthesizer": SYNTHESIZER}, ["Agent", "Task"])

    print("=== synthesis ===")
    print(synthesis)


asyncio.run(main())
