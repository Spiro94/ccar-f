# CCAR-F study repo

Working code for the five domains of the Claude Certified Architect -
Foundations exam. One directory per domain, one file per task statement.

| Domain | Weight | Directory |
|---|---|---|
| 1. Agentic Architecture & Orchestration | 27% | `domain_1_agentic_architecture/` |
| 2. Claude Code Configuration & Workflows | - | `domain_2_claude_code_configuration/` |
| 3. Prompt Engineering & Structured Output | - | `domain_3_prompt_engineering/` |
| 4. Tool Design & MCP Integration | - | `domain_4_tool_design_mcp/` |
| 5. Context Management & Reliability | - | `domain_5_context_management/` |

`shared/` holds the pieces every domain reuses: the Anthropic client and the
calculator / stub-search tool definitions with their executors.

## Running

Files import from `shared/`, so run them as modules from the repo root:

```bash
python -m domain_1_agentic_architecture.task_1_1_agentic_loop
```

## Setup

```bash
pip install -r requirements.txt
```

`ANTHROPIC_API_KEY` goes in `.env`. Tasks that use the Claude Agent SDK also
need the Claude Code CLI available on PATH - the SDK drives it as a subprocess.
