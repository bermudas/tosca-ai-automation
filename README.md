# tosca-ai-automation

AI agent skills, agents and MCP configuration for **Tricentis Tosca** test automation with **Claude Code** and **GitHub Copilot (VS Code)**, covering **Tosca Commander** (on-prem / Server) and **Tosca Cloud**.

Skills and agents live once, in `.claude/`. Claude Code and VS Code Copilot both read them from there. `AGENTS.md` is the shared index that both tools load.

## What's inside

| | |
|---|---|
| **Agents** | `tosca-automation-engineer` (reuse scan → explore → build → run → diagnose → fix → report), `tosca-scenario-explorer` (live walk-through that produces a Tosca-ready element inventory) |
| **Commander** | `commander-mcp` (Commander open, in-process MCP), `cli-api-commander` (TCShell / TCAPI / Remote Control) |
| **Cloud** | Tricentis `toscactl`/`tn` skills (`tosca-cloud`, `tosca-find`, `tosca-run`, analysis, authoring, remediation, …) plus `toscacloud-cli` (REST CLI fallback and a deep JSON-model reference) |
| **Exploration** | `web-exploration` (Playwright MCP), `browser-verify` (CDP), `sap-gui-exploration` (SAP GUI MCP; server options documented) |
| **Cross-platform** | `tosca-platform-guide` (routing, reuse scan, Commander ↔ Cloud concept map), `tosca-tsu` (read .tsu subsets from either platform) |
| **Maintenance** | `update-upstream-skills` (3-way merge sync from upstream sources) |
| **MCP servers** | `tosca-commander`, `playwright`, `sap-gui`, `ToscaCloudMcpServer` (placeholder) in `.mcp.json.example` (Claude) and `.vscode/mcp.json.example` (Copilot) |

## Getting started

1. Clone the repo, then create your personal MCP configs (gitignored) from the examples and **keep only the servers that work on your machine**. For example, drop `sap-gui` unless you're on Windows with SAP GUI, and drop `ToscaCloudMcpServer` until you have your tenant URL:
   ```bash
   cp .mcp.json.example .mcp.json                 # Claude Code
   cp .vscode/mcp.json.example .vscode/mcp.json   # VS Code Copilot
   ```
   Open the folder in **Claude Code** or **VS Code with Copilot** (Agent mode).
2. One-time setup, only for what you use:

   | Target | Setup |
   |--------|-------|
   | Commander | Commander 26.1+ open with your workspace (MCP on `127.0.0.1:46248`; change the port in both MCP files if yours differs) |
   | Cloud (official) | Install `toscactl` → `toscactl login --url <tenant>.my.tricentis.com` → `python3 tools/tosca-cloud-cli/verify_toscactl.py` |
   | Cloud (fallback CLI) | See `tools/toscacloud-cli/README.md`: venv plus `tools/toscacloud-cli/.env` (never committed) |
   | Cloud MCP / personal agent | Replace `<YourTenant>` / `<WorkspaceId>` in your `.mcp.json` and `.vscode/mcp.json`, then remove `ToscaCloudMcpServer` from `disabledMcpjsonServers` in `.claude/settings.json` |
   | Web exploration | Node.js (Playwright MCP runs via `npx`) |
   | SAP exploration | Windows, SAP GUI with scripting enabled, [`uv`](https://docs.astral.sh/uv/); log in to SAP first |

3. Ask in plain language. Simple requests ("find login test cases", "why did last night's run fail?") need no agent. For end-to-end work, pick an agent (Copilot: agent picker; Claude Code: name it in the prompt):

   > *Cloud. Automate login → add to cart → checkout on https://shop.example.com, verify the confirmation, put it in Regression/Web and run it on my personal agent.* (use **tosca-automation-engineer**)

   Name the platform, the application (URL, or SAP system and transaction), the scenario steps with expected results and data, and where the test belongs.

## Guardrails built in

Reuse existing tests and modules before building (also across Commander ↔ Cloud). Explore live only what's missing, and prove every locator unique. Build one artifact at a time. Confirm every write landed. **Never mask a defect** to get a green run. Keep the user's navigation flow. Ask before irreversible actions. Never echo or commit secrets.

## Project memory

Agents keep shared know-how in [`.agents/`](.agents/README.md): project setup (`project.md`, from `project.example.md`), per-application knowledge (`apps/`) and reusable patterns (`patterns/`). Plain Markdown, read and updated by both Claude and Copilot. Only the templates are committed; everything agents or users create in `.agents/` is gitignored so project data stays private. In a private project repo you can un-ignore it to share with the team.

## Keeping upstream content current

Vendored content is pinned in `upstream.lock.json`. Ask your assistant to *"update the Tricentis skills"*, or run:

```bash
python3 scripts/sync_upstream.py check      # what changed upstream
python3 scripts/sync_upstream.py apply      # 3-way merge that keeps local adaptations
python3 scripts/sync_upstream.py validate   # consistency checks
```

## Credits and license

MIT © 2026 Alexander Bychinskiy, except third-party components: Tricentis/mcp-skills content is Apache-2.0. See [NOTICE](NOTICE). Not affiliated with or endorsed by Tricentis.
