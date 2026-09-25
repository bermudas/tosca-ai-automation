---
name: sap-gui-exploration
description: >-
  Explores an SAP GUI for Windows scenario live through an SAP GUI MCP server and
  turns what it sees into Tosca-ready SapEngine module data: transaction, ABAP program,
  screen number, control scripting IDs mapped to Tosca RelativeId, control types and
  step sequence. Use before building or fixing Tosca SAP tests (Commander or Cloud),
  when asked to "walk through" an SAP transaction, or when the user asks which SAP GUI
  MCP to use or how to set one up. Does NOT build the Tosca artifacts itself (hand the
  inventory to commander-mcp / toscacloud-cli / tosca-cloud).
---

# SAP GUI exploration for Tosca

Walk the scenario in a real SAP GUI session and record every screen and control you touch, **before** writing any Tosca module or test step. Tosca SapEngine binds on the same SAP GUI Scripting IDs these MCP servers expose, so what you capture here maps almost 1:1 to Tosca.

## Prerequisites (check, don't assume)

- **Windows** machine with SAP GUI for Windows 7.40+ and SAP Logon running. None of these servers work on macOS/Linux; if the MCP server fails to start, say so and stop.
- **SAP GUI Scripting enabled**, on the server (`sapgui/user_scripting = TRUE`, RZ11) and in the client (SAP Logon → Options → Accessibility & Scripting → Scripting).
- The user is **already logged in**. Attach to the existing session. Never ask for, type or store an SAP password in chat.
- Know the target system/client. Treat production systems as **read-only** unless the user explicitly says otherwise.

## Which MCP server

The configured server is **`sap-gui`** = [kts982/mcp-sap-gui](https://github.com/kts982/mcp-sap-gui), launched with `uvx mcp-sap-gui[screenshots] --profile operator`. It's in the templates `.mcp.json.example` / `.vscode/mcp.json.example`; the user's active `.mcp.json` / `.vscode/mcp.json` may not include it (Windows only). If it's missing, or the user wants another server, read [references/mcp-server-options.md](references/mcp-server-options.md), present the options, **let the user choose**, then add it to their active MCP configs.

## Exploration loop (kts982 tool names; adapt for other servers)

1. **Attach**: `sap_list_connections` → `sap_connect_existing` (never `sap_connect` with credentials).
2. **Start the transaction**: `sap_execute_transaction("<TCODE>")`.
3. **Per screen**, before acting:
   - `sap_get_screen_info` → record **transaction, program, screen number, title**. This is the Tosca window identity (module "quartet").
   - `sap_get_screen_elements` → record the IDs, types and labels of every control the scenario touches.
   - `sap_screenshot` (optionally `save_path=`) for the evidence trail.
4. **Act** the way the user would: `sap_set_field`, `sap_press_button`, `sap_select_combobox_entry`, `sap_select_checkbox`, `sap_select_tab`, `sap_send_key("Enter"|"F8"|…)`, and for tables and trees `sap_read_table`, `sap_select_table_row`, `sap_read_tree`, `sap_expand_tree_node`.
5. **Popups** get their own window identity: `sap_get_popup_window` + `sap_get_screen_info`. Record them as separate screens.
6. **Verification points**: read the result (`sap_read_field`, `sap_read_table`, status bar message) and record the expected value.
7. **Never save/post** (`F11`, Save, Post) without explicit user approval. The server asks for confirmation anyway; don't try to bypass it.
8. Stop when the scenario ends, go back with `F3`/`F12` and leave the session where the user had it.

## Output: the screen/control inventory

Hand this to the builder. One table per screen:

```markdown
### Screen 2 — VA01 Create Sales Order: Overview
Transaction: VA01 | Program: SAPMV45A | Screen: 4001 | Title: "Create Standard Order: Overview"

| # | Label | Scripting ID (from MCP) | Type | Tosca RelativeId | Action / value | Verify? |
|---|-------|-------------------------|------|------------------|----------------|---------|
| 1 | Sold-To Party | wnd[0]/usr/subSUBSCREEN_HEADER:SAPMV45A:4021/subPART-SUB:SAPMV45A:4701/ctxtKUAGV-KUNNR | GuiCTextField | /usr/subSUBSCREEN_HEADER:SAPMV45A:4021/subPART-SUB:SAPMV45A:4701/ctxtKUAGV-KUNNR | Input `1000` | — |
| 2 | Continue | wnd[0]/tbar[0]/btn[0] | GuiButton | "/tbar[0]/btn[0]" | Click | — |
```

### Mapping scripting IDs → Tosca

| MCP gives | Tosca SapEngine (Cloud & Commander) |
|-----------|-------------------------------------|
| `wnd[0]/usr/ctxtRMMG1-MATNR` | `RelativeId` = `/usr/ctxtRMMG1-MATNR`. **Drop the `wnd[n]` / session prefix**; the path is window-relative. |
| any path containing `[n]` (e.g. `wnd[0]/tbar[0]/btn[0]`) | Cloud JSON: value wrapped in embedded quotes, `"\"/tbar[0]/btn[0]\""` |
| transaction / program / screen number | Window module identity: `Transaction`, `ProgramName`, `ScreenNumber` (Cloud root "quartet"; Commander SAP module TechnicalIds) |
| popup on a system program (`SAPMSDYP`, `SAPLSPO2`, …) | separate Window module; keeps the invoking T-code; add a `Caption` for generic popups |
| control type `GuiCTextField` / `GuiTextField` / `GuiButton` / `GuiComboBox` / `GuiCheckBox` / `GuiRadioButton` / `GuiTab` / `GuiTableControl` / `GuiShell` (ALV/tree) | attribute businessType TextBox / Button / ComboBox / CheckBox / RadioButton / TabControl / Table / TableTree |

Full grammar, table/tree archetypes and module JSON: `toscacloud-cli` skill → [sap-automation.md](../toscacloud-cli/references/sap-automation.md). For Commander, check an existing module first (`commander-mcp`: inspect a similar SAP module; its TechnicalIds use the same RelativeId path grammar), then build the same way.

## Rules

- **Never guess** program/screen numbers or IDs. Read them from the live screen. Tosca only fails at runtime.
- Record the **user's real path** (menus, tabs, popups). Don't shortcut it with a direct T-code jump the user didn't take.
- Note dynamic values (document numbers, dates) as **buffers** to capture, not hard-coded values.
- If a control only exists in some screen variants (subscreen `00*` variations), record all observed variants.
