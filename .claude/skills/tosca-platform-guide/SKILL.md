---
name: tosca-platform-guide
description: >-
  Entry point for any Tricentis Tosca task in this repo: decides whether the target is
  Tosca Commander (on-prem / Server, desktop workspace) or Tosca Cloud (SaaS tenant) and
  routes to the right runtime and skill (Commander MCP, Commander CLI/TCShell/TCAPI,
  toscactl, tn, Tosca Cloud MCP, tosca_cli.py), and maps concepts between Commander and
  Cloud (modules, test steps, reusable blocks, execution lists vs playlists) so knowledge
  from one platform can be reused on the other. Use first when a Tosca request doesn't
  name the platform or the tool, or when a runtime is blocked and you need the next option.
---

# Tosca platform guide

## 1. Which platform?

| Signal | Platform |
|--------|----------|
| Tosca Commander desktop app, `.tws` workspace, TCShell, TCAPI, surrogate IDs, node paths, "Server", multi-user repository, checkout / check-in | **Commander** |
| `*.my.tricentis.com` tenant, space/workspace UUID, playlists, Inventory, entityId, Local Runner / personal agent, toscactl, tn | **Cloud** |
| Unclear | Ask **once**: "Commander (desktop workspace) or Tosca Cloud (tenant)?" |

## 2. Runtime routing

Prefer the official Tricentis runtime; escalate only when it's blocked (missing capability, limit, error, or not installed), and say which tier you used and why.

### Commander (on-prem / Server)

| Tier | Runtime | Skill | Use when |
|------|---------|-------|----------|
| 1 | **Commander MCP** (`tosca-commander`, `http://127.0.0.1:46248/mcp`) | `commander-mcp` | Commander 26.1+ is **open** with the workspace. Authoring, tasks, execution, DI. |
| 2 | **TCShell headless** | `cli-api-commander` | Commander closed, CI/batch, or MCP not available. |
| 3 | **TCAPI** (PowerShell / dotnet script) | `cli-api-commander` → `tcapi.md`; authoring recipes in [references/commander-authoring-apis.md](references/commander-authoring-apis.md) | Programmatic access TCShell can't express: creating and editing test cases, steps and values when MCP isn't available (Commander < 26.1, closed, CI). Needs Commander installed on this machine. |
| 3 | **Tosca REST API** (Tosca Server / Commander REST webservice) | [references/commander-authoring-apis.md](references/commander-authoring-apis.md) | Remote access to a Tosca Server repository without a local Commander, or when TCAPI can't run here. |
| 4 | **Remote Control** (GUI-attended) | `cli-api-commander` → `remote-control.md` | Last resort, only with the user's consent. |

Path detection: `tools/tosca-commander-cli/scripts/Get-CommanderAutomationPaths.ps1` (or `.py`).

### Cloud (SaaS)

| Tier | Runtime | Skill | Use when |
|------|---------|-------|----------|
| 1 | **toscactl** | `tosca-cloud` + journey skills (`tosca-find`, `tosca-run`, `tosca-analyzing-*`, `tosca-authoring-*`, …) | Default for everything it supports. |
| 2 | **tn** | `tosca-cloud` → `runtime-routing.md` | toscactl gaps: Builder authoring and remediation, DI, mobile, loop. |
| 3 | **Tosca Cloud MCP** (`ToscaCloudMcpServer`) | `tosca-cloud` → `when-to-use-mcp.md`, `toscacloud-cli` → Local Runner loop | Personal Local Runner runs, step-level failure trees. |
| 4 | **`tosca_cli.py`** (direct REST) | `toscacloud-cli` | Tiers 1–3 are blocked, or you need raw MBT JSON control (modules, steps, blocks, ULIDs, TSU, Inventory moves). |

Checks: `python3 tools/tosca-cloud-cli/verify_toscactl.py`, `python3 tools/tosca-cloud-cli/Get-TnCloudPaths.py`.

## 3. Reuse scan first (both platforms)

Before exploring or building, look for **existing test cases, modules, reusable blocks and test data** that match the scenario, on the target platform and, if it's configured and allowed, on the other one (Commander ↔ Cloud share engines, locators and test-design concepts, though their APIs differ). Finish with a decision: **reuse as is / replicate / extend / new**. How to search each platform, including the fact that Commander MCP has no search (walk the tree) while TCShell/TCAPI has TQL: [references/reuse-scan.md](references/reuse-scan.md).

## 4. Then explore only what's missing or unverified

Walk the scenario live for screens with no module yet, or whose locators come from the other platform or a stale run:

- Web → `web-exploration` (Playwright MCP; `browser-verify` for deep DOM/JS checks)
- SAP GUI → `sap-gui-exploration` (SAP GUI MCP; server options in its references)

The explorer's element inventory (TechnicalIds / RelativeIds, window identity, steps, verification points) goes to the builder for either platform.

## 5. Rules that apply everywhere

- **Discover before acting**: find a similar existing test case or module and use it as the template.
- **One artifact at a time**: build → run → inspect → fix → re-run, then move to the next one.
- **No defect masking**: never delete or weaken a Verify, disable a step, or wrap it in an If to turn a run green. A real product bug should stay red. Full rule: `toscacloud-cli` SKILL.md.
- **Confirm writes landed**: re-read the object after every mutation (Commander `get_attributes`; Cloud GET + `version` bump).
- **Persist**: Commander `save_workspace` (+ `check_in_all` in multi-user workspaces); Cloud writes are immediate.
- **Preserve the user's flow**: don't replace their navigation path with a shortcut.
- **Ask before irreversible actions**: deletes, force overwrites, saving or posting in SAP.

## 6. Commander ↔ Cloud concept map

Cloud's test model is essentially Commander's TBox model (XModules / XTestSteps) serialized as JSON, so design knowledge transfers in both directions. Details and caveats: [references/commander-vs-cloud.md](references/commander-vs-cloud.md).

## 7. Building tests: patterns and object model (both platforms)

Before you build or fix a test case, module or block, on either platform and with any runtime tier:

1. **Pick a pattern** from [references/test-patterns.md](references/test-patterns.md): test case skeleton with recovery, buffer chaining, test-data preparation, row selection by Constraint, API request/response, DB check, optional-element If, data-driven options, module parameter kinds, execution grouping. Each pattern shows the Commander and the Cloud way to write it.
2. **Get the object details right.** Commander: [references/commander-object-model.md](references/commander-object-model.md) (object trees, module/attribute properties, ActionModes, dynamic expressions, TBox standard modules, TQL, official design rules with doc links). Cloud: `toscacloud-cli` references.
3. **Use the tier you're on.** Commander without MCP (Tosca Server, older versions, CI): TCAPI or REST recipes in [references/commander-authoring-apis.md](references/commander-authoring-apis.md).

Raw evidence from real `.tsu` exports (entity detail, enum codes and counts): `tosca-tsu` → `references/tsu-evidence.md`.
