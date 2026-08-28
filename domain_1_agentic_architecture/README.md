# Domain 1 - Agentic Architecture & Orchestration (27%)

Checked against the official *Claude Certified Architect - Foundations Exam
Guide* (Task Statements 1.1-1.7), not just the objectives summary this domain
was originally built from. Where the two disagreed, the official guide won.

| File | Task | Covers |
|---|---|---|
| `task_1_1_agentic_loop.py` | 1.1 | Loop lifecycle, `stop_reason`, model-driven vs decision tree, loop anti-patterns |
| `task_1_2_multi_agent_orchestration.py` | 1.2 | Hub-and-spoke, dynamic subagent selection, partitioning to avoid duplication, narrow decomposition risk, iterative refinement |
| `task_1_3_subagent_definitions.py` | 1.3 | `AgentDefinition`, tool restrictions, context isolation |
| `task_1_3_1_synthesizer_subagent.py` | 1.3.1 | Passing one subagent's result to another via the coordinator, with structured claim/evidence/source metadata so attribution survives the handoff |
| `task_1_3_2_deterministic_handoff.py` | 1.3.2 | The same handoff made programmatic - Python, not a prompt instruction, builds the synthesizer's structured context |
| `task_1_4_workflow_enforcement.py` | 1.4 | Programmatic prerequisites, escalation handoff package (customer ID, root cause, refund amount, recommendation) |
| `task_1_4_1_multi_concern_decomposition.py` | 1.4.1 | Decomposing a multi-concern message into distinct items, one shared identity verification, one unified synthesized reply |
| `task_1_5_agent_sdk_hooks.py` | 1.5 | `PreToolUse` blocking, `PostToolUse` normalisation |
| `task_1_6_task_decomposition.py` | 1.6 | Prompt chaining vs dynamic decomposition (the exam's own "add tests to a legacy codebase" example), per-file + cross-file pass |
| `task_1_7_session_management.py` | 1.7 | `resume`, targeted re-analysis after a named file change, `fork_session`, fresh-session-plus-summary trade-off |

## Two SDKs, two surfaces

Tasks 1.1, 1.4 and 1.4.1 use the **Claude API** (`anthropic`) - you own the
loop, so the loop control and the enforcement gate are visible in the code.

Tasks 1.2, 1.3, 1.3.1, 1.3.2, 1.5, 1.6 and 1.7 use the **Claude Agent SDK**
(`claude-agent-sdk`), a different package that supplies the harness. Subagents,
`AgentDefinition`, hooks and sessions only exist there.

## Numbering note

Task Statements in the official guide are 1.1 through 1.7 - there is no 1.3.1,
1.3.2 or 1.4.1 in the real exam blueprint. Those are this repo's own
subdivision, used when one task statement covers more than one distinct
scenario worth a separate runnable file (e.g. 1.3's model-driven context
passing vs. its deterministic alternative). Don't cite these decimal numbers
on the exam itself.

## Terminology drift worth knowing

- **Task tool vs Agent tool.** The exam guide calls the subagent-spawning
  mechanism the **Task tool** and says `allowedTools` must include `"Task"`.
  Claude Code renamed it to **Agent** in v2.1.63. Current SDKs emit `"Agent"`
  in `tool_use` blocks while `"Task"` still appears in the `system:init` tool
  list and in `permission_denials[].tool_name`. The files here allow both
  names and check for both when detecting delegation. Answer `"Task"` on the
  exam; expect `"Agent"` in the actual `tool_use` block.
- **Named session resumption.** The exam guide describes `--resume
  <session-name>` - a human-assigned name, via the CLI. The Python Agent SDK's
  `resume` field on `ClaudeAgentOptions` takes a session **ID** (the UUID off
  `ResultMessage.session_id`), not a name you chose. `task_1_7_session_management.py`
  uses the SDK's actual mechanism; treat "named" in the exam's phrasing as
  "identified," not literally string-named, when you're reading code instead
  of using the CLI.

## Source

`https://claudecertificationguide.com` (an unofficial third-party study site)
was useful for cross-checking structure, but the official exam guide is the
authority acted on here whenever the two disagreed - notably on where
`fork_session` belongs (official guide: Task 1.7, not 1.3, despite the
third-party site's page for its "1.3" naming it there too).
