# CCAR-F study repo

Working code for the five domains of the Claude Certified Architect -
Foundations exam. One directory per domain, one file per task statement.

Domain order and weights are from the official *Claude Certified Architect -
Foundations Exam Guide*.

| Domain | Weight | Directory |
|---|---|---|
| 1. Agentic Architecture & Orchestration | 27% | `domain_1_agentic_architecture/` |
| 2. Tool Design & MCP Integration | 18% | `domain_2_tool_design_mcp/` |
| 3. Claude Code Configuration & Workflows | 20% | `domain_3_claude_code_configuration/` |
| 4. Prompt Engineering & Structured Output | 20% | `domain_4_prompt_engineering/` |
| 5. Context Management & Reliability | 15% | `domain_5_context_management/` |

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
