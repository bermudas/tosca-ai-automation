# Tosca test automation workspace

Skills, agents and MCP servers for automating **Tricentis Tosca Commander** (on-prem / Server) and **Tosca Cloud** with Claude Code and GitHub Copilot (VS Code). All skills and agents live once, in `.claude/`, and both tools read them from there.

**Start with the `tosca-platform-guide` skill**: it picks the platform, the runtime tier and the skill, and maps Commander ↔ Cloud concepts.

## Agents (`.claude/agents/`)

| Agent | Use for |
|-------|---------|
| `tosca-automation-engineer` | End-to-end: explore → build → run → diagnose → fix → report, on Commander or Cloud |
| `tosca-scenario-explorer` | Live scenario walk-through (Playwright / SAP GUI MCP) → Tosca-ready element inventory; changes nothing in Tosca |

## Skills (`.claude/skills/`)

| Area | Skills |
|------|--------|
| Routing & concepts | `tosca-platform-guide` |
| Project memory | `tosca-project-memory` (onboard the user's setup, learn conventions from existing assets, capture expert patterns into `.agents/`) |
| Exploration | `web-exploration` (Playwright MCP), `browser-verify` (CDP deep checks), `sap-gui-exploration` (SAP GUI MCP + server options) |
| Commander, open (MCP) | `commander-mcp` |
| Commander, headless (TCShell / TCAPI / Remote Control) | `cli-api-commander` |
| Cloud, official (toscactl default, tn for gaps) | `tosca-cloud`, `tosca-cloud-basics`, `tosca-cloud-connect`, `toscactl-reference`, journeys: `tosca-analyzing-execution-results`, `tosca-analyzing-execution-history`, `tosca-remediating-from-results`, `tosca-authoring-automated-testcase`, `tosca-authoring-manual-testcase`, `tosca-explaining-testcase`; commands: `tosca-find`, `tosca-run`, `tosca-status`, `tosca-execution`, `tosca-agents`, `tosca-datasets`, `tosca-import-dataset`, `tosca-export-dataset`, `tosca-create-playlist`, `tosca-delete-playlist`, `tosca-create-workspace`, `tosca-delete-workspace`, `tosca-login`, `tosca-setup` |
| Cloud, fallback + JSON model reference | `toscacloud-cli` (`tools/toscacloud-cli/tosca_cli.py`) |
| Subset files (.tsu), both platforms, read-only | `tosca-tsu` (`scripts/tsu_inspect.py`: summary, step trees, modules/locators, diff) |
| Maintenance | `update-upstream-skills`: pull updates from Tricentis/mcp-skills and bermudas/toscacloud_cli with a 3-way merge (`upstream.json`, `scripts/sync_upstream.py`) |

## MCP servers

Templates: `.mcp.json.example` (Claude) and `.vscode/mcp.json.example` (Copilot). The active `.mcp.json` / `.vscode/mcp.json` are **personal and gitignored**: copy the examples and keep only the servers that work on this machine. If a server a task needs isn't configured, tell the user which entry to add from the example; don't edit the example files for personal settings.

| Server | What | Notes |
|--------|------|-------|
| `tosca-commander` | Commander in-process MCP, `http://127.0.0.1:46248/mcp` | Needs Commander 26.1+ open with a workspace. Change the port if yours differs. |
| `playwright` | Web exploration | `npx @playwright/mcp@latest` |
| `sap-gui` | SAP GUI exploration ([kts982/mcp-sap-gui](https://github.com/kts982/mcp-sap-gui)) | Windows + SAP GUI scripting only; `uvx`. Alternatives: `sap-gui-exploration/references/mcp-server-options.md`. |
| `ToscaCloudMcpServer` | Tosca Cloud MCP via `mcp-remote` (user OAuth) | **Placeholder.** Set `<YourTenant>`/`<WorkspaceId>` in your active configs, then remove it from `disabledMcpjsonServers` in `.claude/settings.json`. |

## Routing, in short

**Commander**: Commander open → `commander-mcp`. Closed, CI or batch → `cli-api-commander` (TCShell → TCAPI → Remote Control last). Helper scripts: `tools/tosca-commander-cli/scripts/` (e.g. `Get-CommanderAutomationPaths.ps1` / `python3 tools/tosca-commander-cli/scripts/Get-CommanderAutomationPaths.py`; Remote Control client `tools/tosca-commander-cli/scripts/lib/TcShellRemoteControl.ps1`). Batch mode: always `save` before exit. Data Integrity only via MCP.

**Cloud**: official first. **toscactl** (default) → **tn** (gaps: Builder, DI, mobile, loop) → **Tosca Cloud MCP** (personal Local Runner runs, failed-step trees) → **`tosca_cli.py`** (fallback: raw MBT JSON, blocks/ULIDs, TSU, Inventory moves). Checks: `python3 tools/tosca-cloud-cli/verify_toscactl.py`, `python3 tools/tosca-cloud-cli/Get-TnCloudPaths.py`. Say which tier you used and why you escalated.

## Project memory (`.agents/`)

Shared, tool-neutral memory in plain Markdown. Conventions: `.agents/README.md`.

- **Read at task start**: `.agents/project.md` (setup: platform, tenant/workspace, folders, agents, naming, preferences), `.agents/apps/<app>.md` for the app in scope, and the fitting `.agents/patterns/*.md`. Treat them as hints and re-verify anything that can go stale.
- **Write after the task**, verified facts only: setup the user gave you → `project.md`; app locators, quirks and known defects → `apps/<app>.md`; generic proven patterns → `patterns/`. Tosca-product knowledge goes into the skills instead. **Never store secrets.** Mention what you updated in your report.
- Filling it: `tosca-project-memory` skill. **Onboard** on first contact (no `project.md`), **learn** conventions from existing test cases/modules (read-only, counted n/N), **remember** expert hints the user shares. Label every entry: `Source: user | observed n/N | verified <date> | inferred`. User-stated rules win; conflicts go to the user.

## Guardrails (all platforms)

1. **Reuse scan before you build.** Find similar test cases, modules, blocks and test data (and, if allowed, on the other platform: Commander ↔ Cloud share engines, locators and test design). Decide: reuse / replicate / extend / new. Never make up IDs. See `tosca-platform-guide` → `reuse-scan.md`.
2. **Explore live only what's missing or unverified**, and prove every locator is unique.
3. **One artifact at a time**: build → run → fix → re-run.
4. **Confirm writes landed** by re-reading. Commander: `save_workspace` (+ `check_in_all` in multi-user workspaces) after mutations.
5. **No defect masking**: never weaken or remove a Verify to make a run green.
6. **Preserve the user's flow**: no navigation shortcuts.
7. **Secrets**: never echo or commit them. Credentials stay in the tools' own config (`toscactl login`, `tools/toscacloud-cli/.env`, SAP GUI session).
8. **Confirm before irreversible actions**: deletes, force overwrites, SAP save/post, check-in.
9. Scratch files go in `.claude/tmp/` (gitignored).
10. Don't commit new or experimental agent/skill definitions without the user's confirmation.

## Sources

- Commander MCP + CLI packs, Cloud CLI pack: [Tricentis/mcp-skills](https://github.com/Tricentis/mcp-skills) (`Tosca/Commander/MCP`, `Tosca/Commander/CLI`, `Tosca/Cloud/CLI`), Apache-2.0.
- `toscacloud-cli`, `browser-verify`, `tosca_cli.py`: [bermudas/toscacloud_cli](https://github.com/bermudas/toscacloud_cli).
- SAP GUI MCP catalog: [marianfoo/sap-ai-mcp-servers](https://github.com/marianfoo/sap-ai-mcp-servers).
