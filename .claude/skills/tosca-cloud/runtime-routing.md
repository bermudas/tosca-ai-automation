# Runtime routing — toscactl vs tn

**Default:** use **`toscactl`**. Use **`tn`** only for workflows marked **`[tn]`** in journey skills or listed as tn-only in the decision table below.

## Decision table

| User intent | Runtime | Skill / doc |
|-------------|---------|---------------|
| Connect tenant | **toscactl** | `tosca-cloud-connect`, `tosca-setup` |
| Search assets / playlists | **toscactl** | `tosca-find`, `tosca-cloud-basics` |
| Run playlist, view history, diagnose latest run | **toscactl** | `tosca-run`, `tosca-status`, `tosca-execution`, analyze journey skills |
| Execution history / trends | **toscactl** | `tosca-analyzing-execution-history` |
| Agents, TDM datasets, CI run flags | **toscactl** | `tosca-agents`, `tosca-datasets` |
| Explain test case (step tree) | **toscactl** metadata → **tn** Builder read | `tosca-explaining-testcase` |
| Author manual / automated test case | **toscactl** module search → **tn** scaffold | author journey skills |
| Remediate (mutations) | **tn**; verify re-run **toscactl** | `tosca-remediating-from-results` |
| DI, mobile, simulation, API execution | **tn** | `di-orchestration.md`, mobile, simulation workflows |
| Autonomous multi-step / robot | **tn** | `tn-invocation.md`, loop/robot workflows |

## Prerequisites by runtime

| Runtime | Setup |
|---------|--------|
| **toscactl** | `toscactl login`; `python3 tools/tosca-cloud-cli/verify_toscactl.py` |
| **tn** (gaps) | `python3 tools/tosca-cloud-cli/configure_tn_connection.py`; `tn --setup`; `echo "/tosca then list workspaces" \| tn` |

## Per-step tagging in journey skills

Journey skills mark steps with **`[toscactl]`** or **`[tn]`**. Follow the tag — do not substitute runtimes.

## Exit criteria

When **toscactl** supports a workflow previously routed to **tn**, update the skill step to `[toscactl]` only and remove the tn fallback for that step.

## Fallback tiers (this repository)

Official Tricentis runtimes always go first. When they hit a gap, a limit or an error, escalate in this order and say which tier you used:

| Tier | Runtime | Typical reasons to use it |
|------|---------|---------------------------|
| 1 | **toscactl** | Default for everything it supports |
| 2 | **tn** | toscactl gaps listed above (Builder authoring/remediation, DI, mobile, loop) |
| 3 | **Tosca Cloud MCP** (`ToscaCloudMcpServer`, template in `.mcp.json.example`) | Runs on a **personal Local Runner agent** (`RunPlaylist(runOnAPersonalAgent=true)`), `GetFailedTestSteps`, `GetRecentPlaylistRunLogs` |
| 4 | **`tools/toscacloud-cli/tosca_cli.py`** (skill `toscacloud-cli`) | toscactl/tn/MCP can't do it or aren't installed: raw MBT JSON edits of modules/steps/blocks, ULID parameter wiring, TSU import/export, Inventory v3 moves, identity/app secrets |

Whichever runtime executes the change, follow the `toscacloud-cli` skill's **no-defect-masking**, **confirm-the-write-landed** and **TechnicalId** rules. They describe the Cloud data model, not just that CLI.
