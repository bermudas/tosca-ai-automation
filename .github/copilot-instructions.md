# Copilot instructions

Follow **`AGENTS.md`** at the repo root. It indexes the agents, skills, MCP servers, routing and guardrails. Skills and agents are in `.claude/skills/` and `.claude/agents/`; VS Code loads both folders natively. File-scoped rules: `.github/instructions/*.instructions.md`.

Copilot-specific notes:

- **Agents**: pick `tosca-automation-engineer` or `tosca-scenario-explorer` in the Chat agent picker.
- **Direct tool mode**: Copilot calls MCP tools one at a time. For Commander, turn plans into numbered steps with one tool per step (`commander-mcp` → `direct-tool-mode.md`).
- **MCP start-up race**: if the first request after a VS Code reload returns `canceled` with `mcpServersStarting`, the Tosca Cloud MCP OAuth handshake is still running. Retry once, and don't re-dispatch playlists or re-edit tests.
- **Terminal**: Commander TCShell/TCAPI helpers are Windows/PowerShell. `tosca_cli.py`, `toscactl` and the Python detectors are cross-platform.
