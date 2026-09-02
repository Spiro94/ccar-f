# Domain 2 - Tool Design & MCP Integration (18%)

Checked against the official *Claude Certified Architect - Foundations Exam
Guide*, Task Statements 2.1-2.5.

| File | Task | Covers |
|---|---|---|
| `task_2_1_tool_interface_design.py` | 2.1 | Description quality as the primary tool-selection signal; ambiguous vs differentiated descriptions; splitting a generic tool into purpose-specific ones |
| `task_2_2_structured_error_responses.py` | 2.2 | MCP `isError`, `errorCategory` (transient/validation/permission/business), `isRetryable`, valid-empty-result vs access-failure |
| `task_2_3_tool_distribution_and_choice.py` | 2.3 | `tool_choice` (`auto`/`any`/forced), scoped tool access, too-many-tools degradation |
| `task_2_4_mcp_server_integration.py` | 2.4 | `.mcp.json` project vs user scoping, env var expansion, a real standalone MCP server with a resource |
| `task_2_5_builtin_tools.py` | 2.5 | Grep vs Glob vs Read/Write/Edit selection, incremental codebase exploration, the Edit-fails fallback |

## Two surfaces again

2.1 and 2.3 are on the **Claude API** (`anthropic`) - `tool_choice` and tool
descriptions are Messages API concepts, testable with a couple of `tools=[]`
lists and no SDK involved.

2.2, 2.4 and 2.5 are on the **Claude Agent SDK** - `isError`/MCP servers/
built-in tools only exist at that layer.

## What 2.4 actually stands up

The Agent SDK's in-process `create_sdk_mcp_server` (used for 2.2's error-
taxonomy demo) does **not** expose the MCP protocol's `resources/list`
capability - only tool-result content blocks of `type: "resource"`, which is
a different thing (a label on one tool's output, not a browsable catalog).
The exam's "MCP resources as content catalogs" skill needs a real, standalone
MCP server, so 2.4 uses the `mcp` package directly (stdio transport) rather
than the Agent SDK's simplified wrapper - the one task in this domain that
isn't just `ClaudeAgentOptions` and a prompt.

Discovering and reading that resource is its own separate skill, not
automatic: it goes through three built-in tools - `ListMcpResourcesTool`,
`ReadMcpResourceTool`, `ReadMcpResourceDirTool` - which must be in
`allowed_tools` like any other tool. On a first pass with an implicit prompt
and no mention of these tools by name, Haiku never reached for them even
with them allowed - it defaulted to guessing a tool argument instead. Only
naming them explicitly (letting `ToolSearch` load their deferred schemas)
got them used. Worth knowing going in: a capability being technically
available doesn't mean a model reliably discovers it unprompted.

`example.mcp.json` is deliberately **not** named `.mcp.json` - a real file by
that name at a project root auto-loads the moment someone runs Claude Code
there, and this repo shouldn't silently start trying to launch a demo MCP
server for anyone who opens a session in it.

## A gate that looked real and wasn't

2.5's Edit-fallback demo needs live `Write`/`Edit` access, scoped to one
throwaway file. The first version enforced that with a `can_use_tool`
callback - and the SDK raised `CanUseToolShadowedWarning` at runtime:
listing `"Write"`/`"Edit"` in `allowed_tools` auto-approves the whole tool
**before** `can_use_tool` is ever consulted, so the callback silently never
ran. The demo still behaved correctly that run, purely because the model
happened to write the right file - the gate itself was decorative. Fixed by
switching to a `PreToolUse` hook instead, which fires regardless of
`allowed_tools`, and re-verified the hook actually denies an off-target path
before trusting it. (Domain 1's `task_1_5_agent_sdk_hooks.py` already used
`hooks={"PreToolUse": [...]}` rather than `can_use_tool`, so it was never
exposed to this - checked, not assumed.) General lesson either way: a
permission mechanism only counts as a gate once you've watched it refuse
something.
