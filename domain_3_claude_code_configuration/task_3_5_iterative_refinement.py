"""Task 3.5 - Iterative refinement techniques.

Four distinct techniques the exam names. This file demonstrates the two that
are actually checkable by running them, and encodes the third as a rule
rather than a vibe:

1. CONCRETE EXAMPLES vs vague prose - the claim ("natural language
   descriptions produce inconsistent results") is empirical, so
   compare_vague_vs_examples() runs BOTH prompts against the SAME held-out
   input and reports whether they actually diverge, rather than asserting
   they would.

2. TEST-DRIVEN ITERATION - write the test suite first, run it, feed the
   failure back, let Claude fix the implementation, re-run. tdd_loop() does
   exactly that against a real scratch file, gated the same way task_2_5's
   Edit-fallback demo was (a PreToolUse hook, not can_use_tool - that
   shadowing bug is still real, see domain_2's README).

3. SINGLE MESSAGE vs SEQUENTIAL - not something to run, a rule to apply:
   batch_or_sequential() below is that rule as code.

4. The INTERVIEW PATTERN (Claude asks clarifying questions before
   implementing, in unfamiliar domains) is demonstrated inline in
   interview_before_implementing() - a live check that a prompt inviting
   questions actually gets questions back rather than a guessed
   implementation.

Run: python -m domain_3_claude_code_configuration.task_3_5_iterative_refinement
"""

import asyncio
import pathlib

import shared.env  # noqa: F401  - loads .env for the claude CLI subprocess

from claude_agent_sdk import query, ClaudeAgentOptions, ResultMessage, HookMatcher

SCRATCH_DIR = pathlib.Path(__file__).parent / "_scratch"
SCRATCH_FILE = SCRATCH_DIR / "name_normalizer.py"


async def ask(prompt, allowed_tools=None, hooks=None):
    options = ClaudeAgentOptions(
        allowed_tools=allowed_tools or [],
        hooks=hooks,
        model="haiku",
        max_budget_usd=1.0,
    )
    result = None
    async for message in query(prompt=prompt, options=options):
        if isinstance(message, ResultMessage) and message.subtype == "success":
            result = message.result
    return result


async def compare_vague_vs_examples():
    """Same transformation, same held-out input. Vague prose leaves the
    target FORMAT genuinely underspecified - "Last, First"? Title case?
    Which name goes first? - concrete examples pin it down."""
    held_out_input = "maria del carmen lopez-garcia"

    vague = await ask(
        f'Normalize this name to a standard format: "{held_out_input}". '
        f"Reply with ONLY the normalized name, nothing else."
    )

    with_examples = await ask(
        "Normalize names to this format, following these examples exactly:\n"
        '  "john SMITH" -> "Smith, John"\n'
        '  "mary-jane o\'brien" -> "O\'Brien, Mary-Jane"\n'
        '  "AHMED al-farsi" -> "Al-Farsi, Ahmed"\n\n'
        f'Now normalize: "{held_out_input}". Reply with ONLY the normalized '
        f"name, nothing else."
    )

    print("vague prose        ->", repr(vague))
    print("with 3 examples     ->", repr(with_examples))
    print("expected format     -> 'Lopez-Garcia, Maria Del Carmen' (Last, First)")


async def scratch_file_only_gate(input_data, tool_use_id, context):
    tool_name = input_data.get("tool_name")
    tool_input = input_data.get("tool_input", {})
    if tool_name in ("Write", "Edit"):
        path = tool_input.get("file_path", "")
        if pathlib.Path(path).resolve() != SCRATCH_FILE.resolve():
            return {
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "deny",
                    "permissionDecisionReason": f"Only {SCRATCH_FILE} may be modified in this demo.",
                }
            }
    return {}


def run_scratch_tests():
    """Runs whatever is currently in SCRATCH_FILE against a fixed test suite.
    Returns (passed: bool, output: str) - the "share the failure" half of
    test-driven iteration needs a real failure message to share."""
    import subprocess
    test_code = '''
import sys
sys.path.insert(0, "%s")
from name_normalizer import normalize_name

cases = [
    ("john SMITH", "Smith, John"),
    ("mary-jane o'brien", "O'Brien, Mary-Jane"),
    ("AHMED al-farsi", "Al-Farsi, Ahmed"),
]
failures = []
for raw, expected in cases:
    got = normalize_name(raw)
    if got != expected:
        failures.append(f"normalize_name({raw!r}) == {got!r}, expected {expected!r}")

if failures:
    print("FAILED:")
    for f in failures:
        print(" -", f)
    sys.exit(1)
print("ALL PASSED")
''' % SCRATCH_DIR
    result = subprocess.run(["python3", "-c", test_code], capture_output=True, text=True)
    passed = result.returncode == 0
    return passed, (result.stdout + result.stderr)


async def tdd_loop(max_iterations=3):
    """Write the failing state first (no implementation exists), run the
    tests, feed the actual failure text back, let Claude fix it, repeat."""
    SCRATCH_DIR.mkdir(exist_ok=True)
    SCRATCH_FILE.write_text("def normalize_name(raw):\n    raise NotImplementedError\n")

    hooks = {"PreToolUse": [HookMatcher(matcher="Write|Edit", hooks=[scratch_file_only_gate])]}

    for i in range(max_iterations):
        passed, output = run_scratch_tests()
        print(f"--- iteration {i}: {'PASS' if passed else 'FAIL'} ---")
        print(output)
        if passed:
            return True
        await ask(
            f"The file {SCRATCH_FILE} contains a normalize_name(raw) function "
            f"that fails these tests:\n\n{output}\n\n"
            f"Fix the implementation in {SCRATCH_FILE} so all cases pass. "
            f"Read the file first, then Edit or Write it.",
            allowed_tools=["Read", "Write", "Edit"],
            hooks=hooks,
        )
    return False


async def interview_before_implementing():
    """In an unfamiliar domain, does a prompt inviting questions actually
    get questions back, or does Claude just guess and implement?"""
    return await ask(
        "I want to add caching to our lookup service. Before you implement "
        "anything, ask me the questions you'd need answered first - don't "
        "write any code yet."
    )


def batch_or_sequential(issues):
    """issues: list of (description, interacts_with: set[int]) by index.
    Interacting issues go in ONE message (fixing one may change what's needed
    for another); independent issues are fixed one at a time so each can be
    verified in isolation before moving on."""
    has_interactions = any(interacts for _, interacts in issues)
    if has_interactions:
        return "single message", [desc for desc, _ in issues]
    return "sequential", [desc for desc, _ in issues]


if __name__ == "__main__":
    print("=== 1. Concrete examples vs vague prose ===")
    asyncio.run(compare_vague_vs_examples())

    print("\n=== 2. Test-driven iteration ===")
    passed = asyncio.run(tdd_loop())
    print("Final result:", "PASSED" if passed else "did not converge")

    print("\n=== 3. Batch vs sequential ===")
    print(batch_or_sequential([
        ("cache invalidation strategy", {1}),
        ("cache key format", {0}),
    ]))
    print(batch_or_sequential([
        ("typo in error message", set()),
        ("missing null check in unrelated function", set()),
    ]))

    print("\n=== 4. Interview pattern ===")
    print(asyncio.run(interview_before_implementing()))
