# Domain 3 - Claude Code Configuration & Workflows (20%)

Checked against the official *Claude Certified Architect - Foundations Exam
Guide*, Task Statements 3.1-3.6.

Different character from Domains 1-2 in two ways. First: this domain is
mostly Claude Code *configuration artifacts* (CLAUDE.md, rules, commands,
skills), not Python/API code, so every example config file lives under
`examples/` - one directory off the real paths Claude Code scans
(`CLAUDE.md`, `.claude/rules/`, `.claude/commands/`, `.claude/skills/`,
`.github/workflows/`). Writing them at the real locations would silently
change how Claude Code behaves in *this* repo for every future session,
including this one.

Second: **task statements that describe a static schema or mechanism are
documentation with a diagram, not a Python script that parses one config
file and calls it code.** Only the pieces that exercise genuine live
behavior - a real subagent call, a real CLI subprocess, a live comparison of
two model responses - are `.py` files. Judged per task statement, not per
domain.

| Task | What it is | Where |
|---|---|---|
| 3.1 CLAUDE.md hierarchy | Docs + load-order diagram | [`docs/3-1-claude-md-hierarchy.md`](docs/3-1-claude-md-hierarchy.md) |
| 3.2 Slash commands & skills | Docs + frontmatter table + fork diagram | [`docs/3-2-skills-and-commands.md`](docs/3-2-skills-and-commands.md) |
| 3.3 Path-specific rules | Docs + glob-matching diagram | [`docs/3-3-path-specific-rules.md`](docs/3-3-path-specific-rules.md) |
| 3.4 Plan mode vs direct execution | Decision-tree diagram | [`docs/3-4-plan-mode-vs-direct.md`](docs/3-4-plan-mode-vs-direct.md) |
| 3.4 The Explore subagent | Live code - a real isolated-context discovery call | [`task_3_4_explore_subagent.py`](task_3_4_explore_subagent.py) |
| 3.5 Iterative refinement | Live code - concrete-examples comparison, TDD loop, interview pattern | [`task_3_5_iterative_refinement.py`](task_3_5_iterative_refinement.py) |
| 3.6 CI/CD integration | Live code - real subprocess calls to the installed `claude` CLI | [`task_3_6_cicd_integration.py`](task_3_6_cicd_integration.py) |

## What's under `examples/`

```
examples/
  claude_md/         # hierarchy + @import demo (docs/3-1)
  claude_rules/       # terraform.md.example, testing.md.example - the exam's own two named glob patterns (docs/3-3)
  claude_commands/    # review.md.example - matches the exam's own /review sample question (docs/3-2)
  claude_skills/      # deep-research/SKILL.md.example - context: fork, agent: Explore (docs/3-2)
  ci/                 # pr-review.yml.example - NOT under .github/workflows/, on purpose (task_3_6)
```

## Findings from actually running/parsing things, not just writing and assuming correct

**A YAML footgun in `SKILL.md` frontmatter.** `argument-hint: [topic]` parses
as a one-item YAML *list*, not the literal string `"[topic]"` the docs show -
unquoted square brackets are YAML flow-sequence syntax. Caught by parsing
this repo's own `deep-research/SKILL.md.example` with `yaml.safe_load` before
trusting it; fixed by quoting. Documented in
[`docs/3-2-skills-and-commands.md`](docs/3-2-skills-and-commands.md).

**3.5's core claim is empirical, and it held up.** "Concrete examples reduce
inconsistency" isn't asserted in `task_3_5_iterative_refinement.py` - it runs
both a vague-prose prompt and an example-augmented prompt against the same
held-out input and reports what actually came back. Live run: vague prose
produced `"Maria del Carmen Lopez-Garcia"` (no comma, first-name-first); the
example-augmented prompt produced `"Lopez-Garcia, Maria del Carmen"` (correct
Last-name-first format, matching the demonstrated pattern). Same model, same
input, genuinely different structure.
