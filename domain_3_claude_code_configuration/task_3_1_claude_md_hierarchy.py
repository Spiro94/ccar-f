"""Task 3.1 - CLAUDE.md hierarchy, scoping, and @import.

Not something to demonstrate by running the Agent SDK against a live prompt -
CLAUDE.md loading is a startup-time filesystem mechanism, not something you
call. So this file IS the mechanism: a small resolver that walks the same
load order the docs specify, and a diagnostic that reproduces the exam's own
named failure - "a new team member not receiving instructions because
they're in user-level rather than project-level configuration."

LOAD ORDER (from the official docs, confirmed, not assumed):
  1. Managed policy CLAUDE.md (org-wide, out of scope here - no per-user file)
  2. User-level: ~/.claude/CLAUDE.md - personal, NEVER shared via version
     control, regardless of how correct or well-written it is
  3. Project-level, root to cwd: CLAUDE.md / .claude/CLAUDE.md at every
     directory from the filesystem root down to the working directory,
     ROOT FIRST - so instructions closer to where you launched Claude are
     read LAST (and so, informally, tend to win in a conflict)
  4. CLAUDE.local.md alongside each CLAUDE.md, appended right after it

This file operates on domain_3_claude_code_configuration/examples/claude_md/
- example files, not the real hierarchy Claude Code would load for THIS
repo. Nothing here is auto-loaded; it is walked deliberately, by this script,
on request.

Run: python -m domain_3_claude_code_configuration.task_3_1_claude_md_hierarchy
"""

import re
from pathlib import Path

EXAMPLES = Path(__file__).parent / "examples" / "claude_md"

IMPORT_RE = re.compile(r"(?<!`)@([^\s`]+)")


def find_imports(text):
    """@path syntax, skipping fenced/inline code spans (the docs specify
    import parsing skips those) - approximated here by skipping any @ that
    is immediately preceded by a backtick."""
    return IMPORT_RE.findall(text)


def resolve_imports(file_path, depth=0, max_depth=4, seen=None):
    """Recursively expand @imports, capped at the documented 4-hop depth.
    Relative paths resolve against the IMPORTING file's directory, not the
    caller's cwd - a common mistake this function deliberately avoids."""
    seen = seen if seen is not None else set()
    file_path = file_path.resolve()
    if file_path in seen or depth > max_depth:
        return []
    seen.add(file_path)

    if not file_path.exists():
        return [(file_path, None)]  # broken import - surfaced, not swallowed

    text = file_path.read_text()
    results = [(file_path, text)]
    for ref in find_imports(text):
        imported = (file_path.parent / ref).resolve()
        results.extend(resolve_imports(imported, depth + 1, max_depth, seen))
    return results


def diagnose_new_teammate(instruction_snippet, user_level_file, project_level_file):
    """The exam's own scenario: a teammate isn't getting instructions because
    they landed in ~/.claude/CLAUDE.md instead of the project file. Since
    user-level content is real text on THIS machine, no other teammate's
    session ever sees it - that is the entire diagnosis, deterministically
    checkable without asking anyone to describe their symptoms."""
    in_user_file = user_level_file.exists() and instruction_snippet in user_level_file.read_text()
    in_project_file = project_level_file.exists() and instruction_snippet in project_level_file.read_text()

    if in_user_file and not in_project_file:
        return (
            f"MISCONFIGURED: '{instruction_snippet}' is in {user_level_file} "
            f"(user-level - only you). Move it to {project_level_file} "
            f"(project-level - shared via version control) so teammates get it."
        )
    if in_project_file:
        return f"OK: '{instruction_snippet}' is in {project_level_file} - shared with the team."
    return f"NOT FOUND: '{instruction_snippet}' is in neither file."


if __name__ == "__main__":
    root = EXAMPLES / "root_CLAUDE.md.example"
    print("=== Resolving root_CLAUDE.md.example and its @imports ===")
    for path, text in resolve_imports(root):
        status = "MISSING" if text is None else f"{len(text)} chars"
        print(f"  {path.relative_to(EXAMPLES.parent.parent)}  [{status}]")

    print("\n=== Diagnosing the exam's own scenario ===")
    # Simulated: the "git workflow" rule only exists in a personal file, never
    # committed - a plausible real mistake, not staged to look dramatic.
    fake_user_level = EXAMPLES / "docs" / "git-instructions.md.example"  # stands in for ~/.claude/CLAUDE.md
    fake_project_level = EXAMPLES / "root_CLAUDE.md.example"
    print(diagnose_new_teammate("Squash-merge PRs", fake_user_level, fake_project_level))
