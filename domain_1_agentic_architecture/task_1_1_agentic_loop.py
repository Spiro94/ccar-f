"""Task 1.1 - Agentic Loop Implementation.

The lifecycle: your code sends a request -> Claude responds -> if it wants a
tool, your host runs it and appends the result to the history -> the history is
fed back so Claude can reason about the next step.

Model-driven, not a decision tree: nothing here dictates which tool runs in
which order. The sequence of calls is chosen by Claude from context on each
turn; the code only executes what it is asked for.
"""

from shared.client import client
from shared.tools import CALCULATOR_TOOL, WEB_SEARCH_TOOL, TOOL_FUNCTIONS

# A safety valve, NOT the stopping mechanism. Using an iteration limit as the
# primary way to end the loop is a loop anti-pattern; stop_reason is the control.
MAX_TURNS = 10

SYSTEM_PROMPT = (
    "You have a calculator tool. Use it for every arithmetic step, including ones "
    "you could do in your head. Never compute a result yourself and never state a "
    "number you have not received from the tool. Report the tool's output as the "
    "answer without recalculating or second-guessing it."
)

messages = [{
    "role": "user",
    "content": "Search the web for who won the 2022 FIFA World Cup, "
               "and separately compute 48271 * 91383 - 17**5.",
}]

for turn in range(MAX_TURNS):
    message = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=messages,
        tools=[CALCULATOR_TOOL, WEB_SEARCH_TOOL],
        tool_choice={"type": "auto"},
    )

    messages.append({"role": "assistant", "content": message.content})

    # stop_reason is the only field to inspect programmatically to control the
    # loop. Continue on "tool_use"; terminate on "end_turn".
    #
    # Anti-patterns this replaces:
    #   1. Parsing termination phrases ("I'm done", "Task complete") from text.
    #   2. Checking raw text content for completion signals.
    #   3. Using a hard iteration limit as the primary stopping mechanism.
    if message.stop_reason != "tool_use":
        for block in message.content:
            if block.type == "text":
                print(block.text)
        break

    results = []
    for block in message.content:
        if block.type != "tool_use":
            continue
        print("Calling tool: " + block.name + " with " + str(block.input))
        try:
            output = TOOL_FUNCTIONS[block.name](**block.input)
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": output,
            })
        except Exception as exc:
            results.append({
                "type": "tool_result",
                "tool_use_id": block.id,
                "content": type(exc).__name__ + ": " + str(exc),
                "is_error": True,
            })

    messages.append({"role": "user", "content": results})
else:
    # Reached only when the safety valve fires - an abnormal exit, kept distinct
    # from the stop_reason exit above so it is never mistaken for completion.
    print("Stopped after " + str(MAX_TURNS) + " turns without a final answer.")
