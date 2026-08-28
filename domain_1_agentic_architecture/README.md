# Domain 1 - Agentic Architecture & Orchestration (27%)

| File | Task | Covers |
|---|---|---|
| `task_1_1_agentic_loop.py` | 1.1 | Loop lifecycle, `stop_reason`, model-driven vs decision tree, loop anti-patterns |
| `task_1_2_multi_agent_orchestration.py` | 1.2 | Hub-and-spoke, parallel spawning, narrow decomposition risk, iterative refinement |
| `task_1_3_subagent_definitions.py` | 1.3 | `AgentDefinition`, tool restrictions, context isolation |
| `task_1_4_workflow_enforcement.py` | 1.4 | Programmatic prerequisites, escalation handoff package |
| `task_1_5_agent_sdk_hooks.py` | 1.5 | `PreToolUse` blocking, `PostToolUse` normalisation |
| `task_1_6_task_decomposition.py` | 1.6 | Prompt chaining vs dynamic decomposition, per-file + cross-file pass |
| `task_1_7_session_management.py` | 1.7 | `resume`, `fork_session`, fresh-session-plus-summary trade-off |

## Two SDKs, two surfaces

Tasks 1.1 and 1.4 use the **Claude API** (`anthropic`) - you own the loop, so
the loop control and the enforcement gate are visible in the code.

Tasks 1.2, 1.3, 1.5, 1.6 and 1.7 use the **Claude Agent SDK**
(`claude-agent-sdk`), a different package that supplies the harness. Subagents,
`AgentDefinition`, hooks and sessions only exist there.

## Terminology drift worth knowing

The exam objectives call the subagent-spawning mechanism the **Task tool** and
say `allowedTools` must include `"Task"`. Claude Code renamed it to **Agent** in
v2.1.63. Current SDKs emit `"Agent"` in `tool_use` blocks while `"Task"` still
appears in the `system:init` tool list and in `permission_denials[].tool_name`.
The files here allow both names and check for both when detecting delegation.
