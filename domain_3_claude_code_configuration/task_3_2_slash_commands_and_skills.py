"""Task 3.2 - Custom slash commands and skills.

Slash commands (.claude/commands/*.md) and skills (.claude/skills/*/SKILL.md)
are both markdown-plus-frontmatter files, but the exam draws one distinction
that matters: commands are invoked, always; skills can be invoked OR
auto-triggered by Claude reading their description, and their frontmatter
carries fields commands don't have - context: fork, allowed-tools,
argument-hint. This file validates that frontmatter against the documented
schema, since a SKILL.md with a typo'd field silently does nothing (Claude
Code ignores unknown keys rather than erroring) - the failure is invisible
unless you check for it, which is what validate_skill() does here.

Run: python -m domain_3_claude_code_configuration.task_3_2_slash_commands_and_skills
"""

from pathlib import Path

import yaml

EXAMPLES = Path(__file__).parent / "examples"

# Every documented SKILL.md field. A key outside this set is either a typo
# or a field the docs don't mention - both worth surfacing, since Claude
# Code silently ignores unknown frontmatter keys rather than erroring.
KNOWN_SKILL_FIELDS = {
    "name", "description", "when_to_use", "argument-hint", "arguments",
    "disable-model-invocation", "user-invocable", "allowed-tools",
    "disallowed-tools", "model", "effort", "context", "agent", "background",
    "hooks", "paths", "shell", "metadata", "license", "compatibility",
}

# Fields whose value type is documented as a plain string. The YAML footgun
# this catches: writing argument-hint: [topic] parses as a ONE-ITEM LIST,
# not the literal string "[topic]" shown in the docs' own examples - found
# by running this validator against this repo's own deep-research example.
STRING_FIELDS = {"name", "description", "when_to_use", "argument-hint",
                  "context", "agent", "model", "effort", "shell", "license",
                  "compatibility"}


def parse_frontmatter(skill_md_path):
    text = skill_md_path.read_text()
    parts = text.split("---", 2)
    if len(parts) < 3:
        raise ValueError(f"{skill_md_path}: no YAML frontmatter block found")
    return yaml.safe_load(parts[1]) or {}


def validate_skill(skill_md_path):
    issues = []
    fm = parse_frontmatter(skill_md_path)

    unknown = set(fm) - KNOWN_SKILL_FIELDS
    if unknown:
        issues.append(f"unknown field(s), likely typo'd and silently ignored: {unknown}")

    for field in STRING_FIELDS & set(fm):
        if not isinstance(fm[field], str):
            issues.append(
                f"'{field}' should be a string per the docs, got {type(fm[field]).__name__} "
                f"({fm[field]!r}) - likely an unquoted [bracket] value parsed as a YAML list"
            )

    # context: fork without an agent field silently falls back to
    # general-purpose rather than erroring - worth flagging, not blocking.
    if fm.get("context") == "fork" and "agent" not in fm:
        issues.append("context: fork with no 'agent' set - defaults to general-purpose; "
                      "confirm that's intended rather than an oversight")

    # DECISION the exam names explicitly: skills are on-demand, CLAUDE.md is
    # always-loaded. A skill with no description is invisible to Claude's
    # own auto-invocation - it can only ever be run explicitly by a human.
    if not fm.get("description"):
        issues.append("no description - Claude cannot auto-invoke this skill; "
                      "it becomes command-only regardless of intent")

    return fm, issues


if __name__ == "__main__":
    for skill_dir in (EXAMPLES / "claude_skills").iterdir():
        skill_md = skill_dir / "SKILL.md.example"
        if not skill_md.exists():
            continue
        fm, issues = validate_skill(skill_md)
        print(f"=== {skill_dir.name} ===")
        print("frontmatter:", fm)
        print("issues:", issues if issues else "none")
        print()

    print("=== Skill vs CLAUDE.md: same content, wrong mechanism ===")
    print("If this were in CLAUDE.md: loaded into EVERY session's context, whether")
    print("or not deep research is ever needed - that's the always-loaded cost.")
    print("As a skill: zero cost until 'research the X module' or /deep-research")
    print("actually triggers it, and it runs in an isolated fork so its own file")
    print("reads never bloat the main conversation either.")
