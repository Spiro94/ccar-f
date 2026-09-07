"""Task 3.6 - Integrating Claude Code into CI/CD pipelines.

This is the one task in this domain that's about the CLI directly, not the
Agent SDK - a CI runner shells out to `claude`, it doesn't import Python. The
exam's own named failure mode is right there in Question 10 of its sample
questions: a pipeline script runs `claude "..."` with no flags and hangs
forever, because the CLI's interactive mode waits for input CI can never
provide. -p/--print is the fix, not a Unix workaround like stdin redirection.

Everything below actually shells out to the real `claude` binary via
subprocess - not simulated - since this task IS the subprocess call.

Run: python -m domain_3_claude_code_configuration.task_3_6_cicd_integration
"""

import json
import subprocess


def run_headless(prompt, output_format="text", json_schema=None, model="claude-haiku-4-5"):
    """The -p flag, every time. Without it, this call blocks forever waiting
    for interactive input a CI runner will never send - see Question 10."""
    cmd = ["claude", "-p", prompt, "--model", model]
    if output_format != "text":
        cmd += ["--output-format", output_format]
    if json_schema is not None:
        cmd += ["--json-schema", json.dumps(json_schema)]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    return result


def structured_pr_finding(diff_summary):
    """--json-schema forces the shape a CI step can parse and post as an
    inline comment - the difference between "machine-parseable structured
    findings" and hoping the model's prose is grep-able."""
    schema = {
        "type": "object",
        "properties": {
            "hasIssues": {"type": "boolean"},
            "findings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "severity": {"type": "string", "enum": ["low", "medium", "high"]},
                        "description": {"type": "string"},
                    },
                    "required": ["severity", "description"],
                },
            },
        },
        "required": ["hasIssues", "findings"],
    }
    result = run_headless(
        f"Review this change for security or correctness issues: {diff_summary}",
        output_format="json",
        json_schema=schema,
    )
    return result


def review_with_isolated_session(diff_summary):
    """SESSION CONTEXT ISOLATION: the same session that wrote code has that
    code's rationale already in context - it reasons FROM its own decisions
    rather than questioning them. A fresh -p invocation per diff has no such
    context; it can only judge what's actually on the page. That is why CI
    review should be a NEW `claude -p` call per diff, never a continuation of
    whatever session generated the change."""
    return run_headless(
        f"Review this diff independently. You did not write this code and "
        f"have no context on why it was written this way - judge only what "
        f"is in front of you:\n\n{diff_summary}"
    )


if __name__ == "__main__":
    print("=== -p with --output-format json ===")
    result = run_headless("Say the word 'ready'.", output_format="json")
    print("returncode:", result.returncode)
    payload = json.loads(result.stdout)
    print("parsed JSON keys:", list(payload.keys()))
    print("result field:", payload.get("result"))

    print("\n=== --json-schema forcing structured findings ===")
    result = structured_pr_finding(
        "Added: def get_user(id): return db.execute(f'SELECT * FROM users WHERE id={id}')"
    )
    print("returncode:", result.returncode)
    print(json.loads(result.stdout).get("result"))
