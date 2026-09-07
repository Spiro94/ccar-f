# Domain 3 - Claude Code Configuration & Workflows (20%)

Checked against the official *Claude Certified Architect - Foundations Exam
Guide*, Task Statements 3.1-3.6.

Different character from Domains 1-2: this domain is mostly Claude Code
*configuration artifacts* (CLAUDE.md, rules, commands, skills), not
Python/API code. That creates a real safety question the other domains
didn't: CLAUDE.md, `.claude/rules/`, `.claude/commands/`, and
`.claude/skills/` are all paths Claude Code scans automatically. Writing real
ones at the real locations would silently change how Claude Code behaves in
*this* repo for every future session - including this one. So every example
below lives under `examples/`, one directory away from where Claude Code
would actually find it, following the same `example.mcp.json` pattern from
Domain 2.

| File | Task | Covers |
|---|---|---|
| `task_3_1_claude_md_hierarchy.py` | 3.1 | Load order (user/project/local), `@import` resolution, diagnosing the "teammate isn't getting instructions" failure |
| `task_3_2_slash_commands_and_skills.py` | 3.2 | `SKILL.md` frontmatter validation (`context: fork`, `allowed-tools`, `argument-hint`), skills vs CLAUDE.md |
| `task_3_3_path_specific_rules.py` | 3.3 | `.claude/rules/` glob-pattern scoping, verified against the exam's own two named patterns |
| `task_3_4_plan_mode_vs_direct.py` | 3.4 | Plan-mode decision rule, live Explore subagent for a discovery phase |
| `task_3_5_iterative_refinement.py` | 3.5 | Concrete examples vs vague prose (live comparison), TDD iteration loop, interview pattern, batch-vs-sequential |
| `task_3_6_cicd_integration.py` | 3.6 | `-p`, `--output-format json`, `--json-schema`, session-isolated review, all run against the real `claude` CLI |

## What's under `examples/`

```
examples/
  claude_md/         # hierarchy + @import demo (task_3_1)
  claude_rules/       # terraform.md.example, testing.md.example - the exam's own two named glob patterns
  claude_commands/    # review.md.example - matches the exam's own /review sample question
  claude_skills/      # deep-research/SKILL.md.example - context: fork, agent: Explore
  ci/                 # pr-review.yml.example - NOT under .github/workflows/, on purpose
```

## Two things found while verifying live, not just written and assumed correct

**A YAML footgun in `SKILL.md` frontmatter.** `argument-hint: [topic]` parses
as a one-item YAML *list*, not the literal string `"[topic]"` the docs show -
unquoted square brackets are YAML flow-sequence syntax. `task_3_2`'s
validator catches this (tested against a deliberately broken example before
trusting it), and the real `deep-research/SKILL.md.example` was fixed to
`argument-hint: "[topic]"` after the first version tripped over its own bug.

**3.5's core claim is empirical, and it held up.** "Concrete examples reduce
inconsistency" isn't asserted - `compare_vague_vs_examples()` runs both
prompts against the same held-out input and prints what actually came back.
Live run: vague prose produced `"Maria del Carmen Lopez-Garcia"` (no comma,
first-name-first); the example-augmented prompt produced `"Lopez-Garcia,
Maria del Carmen"` (correct Last-name-first format, matching the demonstrated
pattern). Same model, same input, genuinely different structure.
