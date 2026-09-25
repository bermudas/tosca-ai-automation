# SAP GUI MCP server options

All options drive **SAP GUI for Windows** through the SAP GUI Scripting COM API (or UI Automation), so they only run on **Windows** with SAP GUI installed and scripting enabled. Source catalog: [marianfoo/sap-ai-mcp-servers → SAP GUI Automation](https://github.com/marianfoo/sap-ai-mcp-servers#sap-gui-automation).

**The user decides which server to use.** Present this table, recommend one based on their constraints, then add the chosen entry to the user's **active** configs: `.mcp.json` (Claude Code, key `mcpServers`) and/or `.vscode/mcp.json` (Copilot, key `servers`, each entry with `"type": "stdio"`). Both are personal and gitignored; update the `.example` templates only when changing the repo's recommended default. Remove or rename `sap-gui` if replacing it, and update the `sap-gui-exploration` skill's tool names if they differ.

| Server | Install / launch | Tools | Strengths | Watch out |
|--------|------------------|-------|-----------|-----------|
| **[kts982/mcp-sap-gui](https://github.com/kts982/mcp-sap-gui)** (configured as `sap-gui`) | `uvx mcp-sap-gui[screenshots]` from PyPI, no clone | ~50 Scripting-API tools: screen info/elements, fields, tables, ALV, trees, popups, screenshots, workflow guides | Returns scripting IDs directly (maps to Tosca RelativeId). Safety features: `--profile exploration\|operator\|full`, `--read-only`, transaction allow-lists, policy presets, confirmation before Save, audit log. Never takes passwords. | Needs `uv`. Profile `exploration` is read-only (can't run transactions); use `operator` to walk scenarios. |
| **[bermudas/SAP-MCP](https://github.com/bermudas/SAP-MCP)** | `git clone` → `python -m venv .venv` → `pip install -e .` → `python -m sap_gui_mcp` | 18: UIA tools (`sap_get_ui_tree`, `sap_click_by_property`, `sap_get_snapshot`…) + Scripting tools (`sap_script_get_all_fields`, `sap_script_set_field`, `sap_script_start_transaction`, table cells, vkeys) | Combines UI Automation (works on SAP Logon pad / non-scripting windows) with Scripting IDs. Ships Copilot agents ("SAP tester", "SAP TOSCA Vision Script") that emit Tosca-ready element tables. | Local clone + venv. `.env` holds SAP credentials for its login flow: keep it out of git. |
| **[mario-andreschak/mcp-sap-gui](https://github.com/mario-andreschak/mcp-sap-gui)** | clone → `python -m pip install .` → `.env` with `SAP_SESSION_ID=/app/con[0]/ses[0]` → `python -m sap_gui_server.server` | Transaction launch/end, **coordinate** click/move/type, screenshots | Most popular. Pinned to one explicit session; supports SSO. | Mostly pixel/coordinate-driven, which gives you fewer scripting IDs for Tosca. Best when vision-based exploration is acceptable. |
| **[Hochfrequenz/sapgui.mcp](https://github.com/Hochfrequenz/sapgui.mcp)** | Windows release `.exe` (`"command": "C:/path/to/sapgui_mcp_windows_<version>.exe"`, `env: {"BACKEND_TYPE": "desktop"}`) or from source (uv) | Scripting API + **SAP Web GUI** backend | One server for desktop SAP GUI and SAP GUI for HTML. | Web GUI tests in Tosca use the Html engine, not SapEngine. Explore Web GUI with Playwright too. |
| **[jduncan8142/sap_gui_mcp](https://github.com/jduncan8142/sap_gui_mcp)** | `pip install -e .` from clone (uv supported) | Scripting API via FastMCP, screenshots | Small and simple. | Low activity (1 star, last update 2025-12). |
| **[toni-ramchandani/sapient-mcp](https://github.com/toni-ramchandani/sapient-mcp)** | clone → `pip install -e .` → `python -m sapient_mcp` (env `SAPIENT_MCP_SAPLOGON_PATH`, `SAPIENT_MCP_CAPS=screenshot,codegen,advanced`) | RoboSAPiens (Robot Framework) based, label-driven, codegen | Label-based addressing, Robot Framework code generation. | **No license file.** Check with the user/legal before using. Label-based locators need translating to RelativeIds. |

## Config snippets

Claude Code (`.mcp.json` → `mcpServers`):

```json
"sap-gui": { "type": "stdio", "command": "uvx", "args": ["mcp-sap-gui[screenshots]", "--profile", "operator"] }
```

```json
"sap-gui-bermudas": {
  "type": "stdio",
  "command": "C:\\path\\to\\SAP-MCP\\.venv\\Scripts\\python.exe",
  "args": ["-m", "sap_gui_mcp"],
  "env": { "SAP_LOGON_PATH": "C:\\Program Files (x86)\\SAP\\FrontEnd\\SAPgui\\saplogon.exe" }
}
```

```json
"sap-gui-mario": {
  "type": "stdio",
  "command": "C:\\path\\to\\mcp-sap-gui\\.venv\\Scripts\\python.exe",
  "args": ["-m", "sap_gui_server.server"],
  "cwd": "C:\\path\\to\\mcp-sap-gui"
}
```

```json
"sap-desktop": { "type": "stdio", "command": "C:/path/to/sapgui_mcp_windows_<version>.exe", "env": { "BACKEND_TYPE": "desktop" } }
```

```json
"sapient": {
  "type": "stdio",
  "command": "python",
  "args": ["-m", "sapient_mcp", "--caps", "screenshot,codegen,advanced"],
  "env": { "SAPIENT_MCP_SAPLOGON_PATH": "C:\\Program Files (x86)\\SAP\\FrontEnd\\SAPgui\\saplogon.exe" }
}
```

VS Code (`.vscode/mcp.json` → `servers`): same objects. Keep `"type": "stdio"`.

After adding a server to `.mcp.json`, also add its name to `enabledMcpjsonServers` in `.claude/settings.json` if it should start without an approval prompt.

## Choosing, in short

- Want Tosca RelativeIds with the least setup → **kts982** (default).
- Already use the SAP tester / Vision Script agents, or need UIA for non-scripting windows → **bermudas/SAP-MCP**.
- SAP GUI for HTML as well as desktop → **Hochfrequenz** (and Playwright for the Html side).
- Scripting can't be enabled at all → only coordinate/vision options (**mario-andreschak**) remain, but Tosca SapEngine itself needs scripting, so raise this with the user first.
