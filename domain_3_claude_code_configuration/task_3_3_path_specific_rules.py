"""Task 3.3 - Path-specific rules for conditional convention loading.

.claude/rules/*.md files without a paths: frontmatter field load
unconditionally, same priority as CLAUDE.md. WITH a paths: field (a YAML
list of glob patterns), a rule loads only when Claude reads a file matching
one of those patterns - which_rules_apply() below is that matching logic,
run against this repo's own example rules in examples/claude_rules/.

WHY GLOB RULES BEAT A SUBDIRECTORY CLAUDE.md for this case: this repo's test
files - if it had any - would sit next to the code they test (Button.test.tsx
beside Button.tsx), scattered across every directory, not concentrated in one
tests/ folder. A directory-level CLAUDE.md can only ever cover ONE directory
tree; testing.md.example's **/*.test.tsx pattern covers every test file
project-wide regardless of where it lives, in one file.

Uses pathlib.PurePath.full_match() (Python 3.13+), which supports ** the same
way the docs' own glob table describes - confirmed against all four of the
exam's named examples (terraform/**/*, **/*.test.tsx, and both directions of
"does this file match" / "does this file NOT match") before relying on it.

Run: python -m domain_3_claude_code_configuration.task_3_3_path_specific_rules
"""

from pathlib import Path, PurePath

import yaml

RULES_DIR = Path(__file__).parent / "examples" / "claude_rules"


def load_rules(rules_dir):
    rules = []
    for path in sorted(rules_dir.glob("*.md.example")):
        text = path.read_text()
        parts = text.split("---", 2)
        frontmatter = yaml.safe_load(parts[1]) if len(parts) >= 3 and parts[1].strip() else {}
        rules.append({"file": path.name, "paths": (frontmatter or {}).get("paths")})
    return rules


def which_rules_apply(changed_file, rules):
    """A rule with no 'paths' field is unconditional - it always applies.
    A rule WITH 'paths' applies only if the changed file matches at least
    one of its glob patterns."""
    changed = PurePath(changed_file)
    applicable = []
    for rule in rules:
        if rule["paths"] is None:
            applicable.append(rule["file"])  # unconditional
            continue
        if any(changed.full_match(pattern) for pattern in rule["paths"]):
            applicable.append(rule["file"])
    return applicable


if __name__ == "__main__":
    rules = load_rules(RULES_DIR)
    print("Loaded rules:")
    for r in rules:
        print(" ", r)

    test_files = [
        "terraform/modules/vpc/main.tf",
        "src/components/Button.test.tsx",
        "src/components/Button.tsx",       # NOT a test file - should get nothing
        "docs/README.md",                   # matches neither rule
    ]

    print("\nWhich rules load for each changed file:")
    for f in test_files:
        applicable = which_rules_apply(f, rules)
        print(f"  {f:45s} -> {applicable or 'none'}")
