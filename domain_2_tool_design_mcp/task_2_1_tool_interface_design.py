"""Task 2.1 - Tool interface design: descriptions as the selection mechanism.

Tool descriptions are the PRIMARY signal Claude uses to pick a tool - not the
tool's name, not its parameter names, the description text. Minimal or
overlapping descriptions cause misrouting between similar tools. This is the
exact lesson from turn one of this repo's own history: shared/tools.py's
CALCULATOR_TOOL originally read "A tool for performing mathematical
calculations" and Claude never called it for "what's 5+5?" - not because the
tool was broken, but because nothing in the description said it applied to
trivial arithmetic.

This file reproduces the exam's own worked failure - analyze_content vs
analyze_document, near-identical descriptions causing misrouting - then fixes
it the way the exam's Skills bullets prescribe: differentiate first, then (if
that's not enough) split into purpose-specific tools with defined contracts.

Run: python -m domain_2_tool_design_mcp.task_2_1_tool_interface_design
"""

from shared.client import client

MODEL = "claude-haiku-4-5"

# --- The failure case: two tools, nearly identical descriptions ------------
# Both accept a URL/text and "process" it. Nothing here tells Claude which one
# applies to a live web page versus an already-downloaded document - that is
# the exact ambiguity the exam names (analyze_content vs analyze_document).
AMBIGUOUS_TOOLS = [
    {
        "name": "analyze_content",
        "description": "Analyzes content and returns information about it.",
        "input_schema": {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"],
        },
    },
    {
        "name": "analyze_document",
        "description": "Analyzes a document and returns information about it.",
        "input_schema": {
            "type": "object",
            "properties": {"input": {"type": "string"}},
            "required": ["input"],
        },
    },
]

# --- The fix, step 1: differentiate the descriptions ------------------------
# Same two tools, same names - only the description text changed. Per the exam:
# "Renaming tools and updating descriptions to eliminate functional overlap."
# Here we keep the names but add exactly what was missing: input format,
# boundary, and an explicit "not this" pointing at the sibling tool.
DIFFERENTIATED_TOOLS = [
    {
        "name": "analyze_content",
        "description": (
            "Fetches a LIVE web page by URL and extracts its current content. "
            "Input must be an http(s) URL. Use this for anything reachable on "
            "the open web right now. Do NOT use this for a document the user "
            "already provided or pasted in - use analyze_document for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "An http(s) URL"}},
            "required": ["input"],
        },
    },
    {
        "name": "analyze_document",
        "description": (
            "Analyzes a document's TEXT that the user already supplied in the "
            "conversation (pasted text, an uploaded file's contents, or a "
            "quoted excerpt). Input is the document text itself, not a URL. "
            "Do NOT use this to fetch anything from the web - use "
            "analyze_content for that."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"input": {"type": "string", "description": "The document's text"}},
            "required": ["input"],
        },
    },
]

# --- The fix, step 2: split into purpose-specific tools ---------------------
# The exam's other named example: splitting a generic analyze_document into
# extract_data_points, summarize_content, verify_claim_against_source. Splitting
# is the heavier fix - reach for it when even a well-written single description
# still has to cover too many distinct behaviors to stay unambiguous.
SPLIT_TOOLS = [
    {
        "name": "extract_data_points",
        "description": "Pulls out specific structured data points (dates, "
                       "amounts, names) from a document's text. Returns a list "
                       "of {field, value} pairs. Use for extraction, not summary.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "summarize_content",
        "description": "Produces a short prose summary of a document's text. "
                       "Use when the user wants the gist, not a structured "
                       "field list - for that, use extract_data_points instead.",
        "input_schema": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
    {
        "name": "verify_claim_against_source",
        "description": "Checks whether a specific claim is supported by a "
                       "given document's text. Use only when there is one "
                       "explicit claim to check - not for open-ended analysis.",
        "input_schema": {
            "type": "object",
            "properties": {
                "claim": {"type": "string"},
                "text": {"type": "string"},
            },
            "required": ["claim", "text"],
        },
    },
]


def which_tool_called(tools, prompt):
    """Send one prompt against one tool set, return the tool name Claude picked."""
    message = client.messages.create(
        model=MODEL,
        max_tokens=256,
        messages=[{"role": "user", "content": prompt}],
        tools=tools,
        tool_choice={"type": "any"},
    )
    for block in message.content:
        if block.type == "tool_use":
            return block.name
    return None


if __name__ == "__main__":
    # Genuinely ambiguous: a URL-shaped string with no explicit "fetch this" or
    # "here's the text I pasted" framing. Nothing in the PROMPT disambiguates -
    # only the TOOL DESCRIPTION can, which is the point: this isolates
    # description quality as the variable, rather than testing whether Claude
    # can read an unambiguous prompt.
    ambiguous_input = "Look into this for me: https://acmecorp.com/reports/q3-2026"

    print("--- Same ambiguous input, three description qualities ---")
    print("Ambiguous descriptions ->", which_tool_called(AMBIGUOUS_TOOLS, ambiguous_input))
    print("Differentiated descriptions ->", which_tool_called(DIFFERENTIATED_TOOLS, ambiguous_input))

    # The split set answers a different question: given ONE clearly-scoped
    # request each, does each purpose-specific tool actually get picked for
    # its own purpose? One prompt against three tools proves nothing; three
    # prompts, each matching one tool's stated job, does.
    print("\n--- Purpose-specific tools, one matching prompt each ---")
    document_text = "Q3 revenue was $4.2M, up 12% YoY."
    print("extraction request ->", which_tool_called(
        SPLIT_TOOLS, f"Extract the revenue figure and growth percentage from: {document_text}"))
    print("summary request ->", which_tool_called(
        SPLIT_TOOLS, f"Give me a one-sentence summary of: {document_text}"))
    print("verification request ->", which_tool_called(
        SPLIT_TOOLS, f"Does this support the claim that revenue grew over 10%? Text: {document_text}"))
