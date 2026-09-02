"""Task 2.3 - Tool distribution across agents, and tool_choice.

Two related ideas the exam pairs under one task statement:

1. tool_choice controls WHETHER and WHICH tool gets called on a given request:
   "auto" (Claude decides), "any" (must call some tool, Claude picks which),
   or forced ({"type": "tool", "name": "..."}) - the same three modes covered
   in this repo's very first exchange, back when 5+5 wasn't triggering the
   calculator. This file adds the piece that wasn't needed then: forcing a
   SPECIFIC tool to run first in a pipeline, before the model is free to
   choose again on the next turn.

2. Tool DISTRIBUTION is a design-time decision, not a per-request one: which
   tools does a given agent get at all. Too many tools (the exam's own
   figure: 18 instead of 4-5) degrades selection reliability by increasing
   decision complexity, and an agent handed tools outside its specialization
   tends to misuse them - a synthesis agent that has WebSearch will search
   instead of synthesizing. The fix from the exam's own scenario (see the
   sample questions on this domain): give the narrow specialist ONE small,
   scoped tool for its 85% common case, and route the rare complex case back
   through the coordinator instead of over-provisioning the specialist.

Run: python -m domain_2_tool_design_mcp.task_2_3_tool_distribution_and_choice
"""

from shared.client import client

MODEL = "claude-haiku-4-5"

EXTRACT_METADATA_TOOL = {
    "name": "extract_metadata",
    "description": "Extract title, author and date from a document. Must run "
                   "before any enrichment tool, since enrichment needs these "
                   "fields as input.",
    "input_schema": {
        "type": "object",
        "properties": {"text": {"type": "string"}},
        "required": ["text"],
    },
}

ENRICH_WITH_TOPICS_TOOL = {
    "name": "enrich_with_topics",
    "description": "Tag a document with topic categories, given its already-"
                   "extracted metadata.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "author": {"type": "string"},
        },
        "required": ["title", "author"],
    },
}

VERIFY_FACT_TOOL = {
    "name": "verify_fact",
    "description": "Check one short factual claim (a date, a name, a "
                   "statistic) against a quick lookup. For SIMPLE fact checks "
                   "only - not for open-ended research.",
    "input_schema": {
        "type": "object",
        "properties": {"claim": {"type": "string"}},
        "required": ["claim"],
    },
}


def call_with_choice(tools, tool_choice, prompt):
    message = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice=tool_choice,
    )
    calls = [b.name for b in message.content if b.type == "tool_use"]
    return message.stop_reason, calls


if __name__ == "__main__":
    doc = "Title: Q3 Results. Author: J. Chen. Published 2026-09-01."

    # --- tool_choice: "auto" -------------------------------------------
    # Claude decides freely. A trivial factual question needs no tool at all.
    print("auto, no tool needed:",
          call_with_choice([EXTRACT_METADATA_TOOL], {"type": "auto"},
                           "What is the capital of France?"))

    # --- tool_choice: "any" ---------------------------------------------
    # Forces SOME tool call, Claude picks which. Guarantees no plain-text
    # reply - useful when a text answer would be useless, e.g. structured
    # extraction pipelines where "I don't know" isn't an acceptable output.
    print("any, forced to pick one:",
          call_with_choice([EXTRACT_METADATA_TOOL, ENRICH_WITH_TOPICS_TOOL],
                           {"type": "any"}, f"Process this document: {doc}"))

    # --- tool_choice: forced, specific tool -------------------------------
    # Guarantees extract_metadata runs FIRST, before enrichment - this is what
    # makes forced-first-step + follow-up-turn a genuine pipeline enforcement,
    # not just a hint. Without this, Claude might reach for enrich_with_topics
    # even though it needs fields extract_metadata hasn't produced yet.
    print("forced extract_metadata:",
          call_with_choice(
              [EXTRACT_METADATA_TOOL, ENRICH_WITH_TOPICS_TOOL],
              {"type": "tool", "name": "extract_metadata"},
              f"Process this document: {doc}"))

    # --- Scoped cross-role tool ------------------------------------------
    # A "synthesis agent" (simulated here as one call scoped to ONE narrow
    # tool) handling the 85% common case: a simple fact check it can do
    # itself, without round-tripping through a coordinator for a full
    # research pipeline it doesn't need. tools=[VERIFY_FACT_TOOL] alone - no
    # WebSearch, no document tools - is the tool-DISTRIBUTION decision: this
    # agent physically cannot misuse a broader tool it was never given.
    # tool_choice "any" here isolates what this line demonstrates: forced to
    # act, this agent has exactly one tool it COULD reach for.
    print("scoped specialist, simple fact check:",
          call_with_choice([VERIFY_FACT_TOOL], {"type": "any"},
                           "Quick check: does the claim 'the report was "
                           "authored by J. Chen' hold up? Verify it."))
