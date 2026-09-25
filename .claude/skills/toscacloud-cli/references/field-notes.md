# Field notes — Tosca Cloud operations knowledge

Operational knowledge carried over from the original `toscacloud_cli` Copilot agent (`.github/agents/tosca.agent.md`) and its CLAUDE.md / copilot-instructions, where it was not already covered by `SKILL.md` or the other references. Corrections that the skill made since then take precedence (e.g. `parameterLayerId` is copied from the block, `Id` **is** a valid Html TechnicalId, standard-module attribute GUIDs are re-discovered per tenant).

Paths are relative to the repo root: CLI = `tools/toscacloud-cli/tosca_cli.py`, credentials = `tools/toscacloud-cli/.env`.

## Operating constraints and tenant context

- **Tenant**: read from `tools/toscacloud-cli/.env` → `TOSCA_TENANT_URL`
- **Space ID**: read from `tools/toscacloud-cli/.env` → `TOSCA_SPACE_ID`
- **CLI**: `python tools/toscacloud-cli/tosca_cli.py <command>` (run from the repo root)
- **Config**: already set in `tools/toscacloud-cli/.env` — never prompt for credentials


- DO NOT fabricate entity IDs — always discover them via `inventory search` first
- DO NOT skip the discovery step when creating new test cases — check for existing modules to reuse
- DO NOT modify config settings — credentials are already configured
- DO NOT create modules with `--iface` other than `Gui` or `NonGui`
- ONLY use `--force` / `-y` flags when the user has explicitly confirmed a destructive operation
- DO NOT guess at folder IDs — always resolve them via `inventory folder-tree` or `inventory search "" --type folder`

The CLI's service-account only needs the `Tricentis_Cloud_API` clientId — do **not** swap in `E2G_Agents`, `Tosca_Server`, or `Tricentis_Hosted_E2G_Agents` when chasing 403s. Those are engine-internal identities and grant a different scope set (no delete, no private-agent dispatch, no log attachments); substituting them will not unlock the permission — it will just burn time. When the CLI gets a 403, the fix is either a Portal-UI action by the logged-in user, or a tenant-admin role grant on the existing Cloud-API role (see "Personal-agent runs need MCP" and the `cases delete` caveat in the Critical caveats table of `SKILL.md`).

Scratch JSON/Python files for TOSCA CLI work go under `.claude/tmp/` (gitignored), **not** `/tmp/`. Playwright MCP is sandboxed to the project root and cannot read `/tmp/`, and `/tmp/` is wiped across macOS reboots so your reproduction trail disappears. Use `.claude/tmp/<YYYY-MM-DD>-<intent>.json` (e.g. `.claude/tmp/2026-04-24-site-menu-v6.json`) and delete when the task lands.

The skill's examples use `.claude/tmp/` accordingly.

## Preserve the user's flow and don't change the journey

- **Preserve the user's flow, don't re-dispatch on environment hiccups.** When the user reports an environment failure (`"screen locked"`, `"VPN dropped"`, `"mcp glitched, reloaded"`), re-dispatch the **existing** playlist — do NOT re-edit test artifacts. The last known-good version in MBT is still valid, and the previous run may still be executing on the agent. When a step fails, fix the step — don't replace a hover→submenu→click user journey with a direct `OpenUrl` shortcut. The test documents the journey; shortcuts destroy the coverage. Only propose a flow change after ≥ 3 distinct root-cause fixes have failed, and ask first.
> **Resolved rule:** an **MCP reload/glitch** → do **not** re-dispatch; the previous run is still executing, so re-issue the last read-side MCP call. A **screen lock / VPN drop** that killed the run → re-dispatch the **unchanged** playlist. In neither case re-edit the test artifacts.

## Output format / report contents


After completing a task, always report:
- What was done (action taken)
- The entity ID(s) of created/modified artifacts (so the user can find them in the portal)
- The folder path / ancestor chain if placement was involved
- Any follow-up steps if manual portal action is needed



Whenever you encounter a **new API behavior**, **CLI bug**, **missing command**, or **useful pattern** not already covered in this skill, you must fix it immediately — do not just work around it and move on.

### When to trigger self-improvement

| Trigger | Action required |
|---------|----------------|
| CLI command fails or produces wrong output | Fix `tosca_cli.py` (patch the `ToscaClient` method or the Typer command), then re-run |
| New API behavior discovered (undocumented endpoint, required field, quirk) | Add a row to **Critical Caveats** in the skill (SKILL.md / references); add the endpoint to **Undocumented APIs** if applicable |
| New workflow pattern needed (e.g. a new type of gap-fill, a new clone variant) | Add a branch to the **Decision Tree** |
| New CLI command needed that would save future work | Implement it in `tosca_cli.py` (ToscaClient method + Typer command), add to **Key CLI Commands**, update `README.md` |
| Existing documentation is wrong or misleading | Correct it in the skill (SKILL.md / references) and in `README.md` |

### How to apply changes

1. **Fix `tosca_cli.py` first** — add the ToscaClient method and/or Typer command, validate with `python tools/toscacloud-cli/tosca_cli.py <cmd> --help` and a live test call.
2. **Update `README.md`** — add/fix the relevant command section and (if applicable) the Undocumented APIs table.
3. **Update this file** — add the new pattern to Critical Caveats, Decision Tree, or Quick Reference as appropriate.
4. **Never leave a discovered bug unfixed** — if the workaround was a separate `.py` script, move that logic into a proper CLI command.

### Scope rules
- Only change what is directly related to the new discovery — do not refactor unrelated code.
- New CLI commands must follow the existing style: Typer app + ToscaClient method, `--json` flag, Rich output.
- New ToscaClient methods must include a docstring with the HTTP verb, endpoint path, and return type.

## Decision tree: detailed gap-fill and assemble-from-parts procedures

```
User wants to EXTEND COVERAGE (gap filling)?
  → inventory search in the folder to find existing cases (inventory get <folderId> --include-ancestors)
  → cases steps <id> --json on ALL existing cases to identify the pattern (materials, values, steps)
  → identify the gap (e.g. 3 Materials exists → 4 Materials is missing)
  → check if the reuseable blocks need new parameters first:
      blocks get <blockId> --json → see current businessParameters
      blocks add-param <blockId> --name <newParam> → get the new param's ULID
      blocks set-value-range <blockId> <enumParam> --values '1,2,3,4'  (extend count enums)
  → build the new case body using the existing case JSON as a template
  → ensure each TestStepFolderReferenceV2 has the block's own parameterLayerId (copied verbatim) + fresh ULIDs for the ref id and parameters[].id
  → cases update <newId> --json-file new_case.json
  → inventory move testCase <newId> --folder-id <folderId>
```

```
User wants to ASSEMBLE a new case from parts of existing cases?
  → inventory search "" --type TestCase --folder-id <folderId> to enumerate candidates
  → cases steps <id> --json on ALL relevant cases to extract step folders and block refs
  → identify which folders/blocks to reuse from which cases (mix and match)
  → deep-copy each block ref: keep the block's parameterLayerId, fresh ULIDs for the ref id + parameters[].id
  → deep-copy each step folder recursively with fresh item IDs
  → build the new testCaseItems list combining pieces from multiple source cases
  → cases create → cases update <newId> --json-file assembled.json
  → inventory move testCase <newId> --folder-id <folderId>
```
> **Correction (applied above):** do **not** mint a fresh `parameterLayerId`. Copy the block's own `parameterLayerId` verbatim, and leave the key out for parameterless references. Fresh ULIDs go only on the reference `id` and each `parameters[].id` (see `blocks.md`).

## Additional CLI flags

```bash
python tools/toscacloud-cli/tosca_cli.py playlists run <id> --wait [--param-overrides '[...]']
python tools/toscacloud-cli/tosca_cli.py playlists logs <execId> -e --quiet      # input is already an executionId; suppress stdout
```

## Additional critical caveats

| `folderKey` in Inventory v3 PATCH | Read-only — always use `inventory move` to change folder placement |

| `inventory folder-tree` without `--folder-ids` was broken | Fixed: body must be a bare JSON array (not `{}`); the `post()` `body or {}` default was swapped to `{} if body is None else body`. Without args returns `[]` — pass `--folder-ids` with parent IDs to get children. |

| TSU export IDs | Must be `entityId` values (UUIDs), not human-readable names |

| `--json` flag placement | Always place `--json` **before** positional arguments: `cases get --json <id>` ✓, `cases get <id> --json` ✓, but `cases get -- <id> --json` ✗ — the `--` end-of-options separator causes Typer to treat `--json` as a positional arg, silently falling back to Rich display output. |

| `HREF` TechnicalId must be absolute URL | TOSCA resolves the `href` DOM property (absolute URL) when matching the `HREF` TechnicalId — it does NOT use `getAttribute('href')` (relative). If an `<a>` has `href="/services"`, the TOSCA parameter must be `HREF: https://www.example.com/services`. Using `/services` (relative) causes a mismatch and the element is never found. Best practice: omit `HREF` entirely when `Tag + InnerText + ClassName` already uniquely identifies the element. |

| Add a `Wait` step after OpenUrl in Precondition for SPAs | Single-page apps (React, Angular, etc.) don't finish rendering immediately after navigation. Without an explicit `Wait` (3000–5000 ms) after `OpenUrl`, TOSCA will fail to find the first interactive element — humans will always add this manually. Include a `Timing.Wait Duration=5000` step at the end of the Precondition folder for any SPA target. |
> **Scope:** this is only for the Precondition bootstrap of SPAs. Everywhere else follow `best-practices.md`: avoid static waits and prefer `WaitOn` on the element you need next. Better still, use a `WaitOn` on the first interactive element instead of the fixed 5 s.

## E2G logs: endpoints and attachment details

3-step recipe these commands wrap (`Tricentis_Cloud_API` works as-is — no extra role needed):
1. `GET /{spaceId}/_playlists/api/v2/playlistRuns/{runId}` → read `executionId`.
2. `GET /{spaceId}/_e2g/api/executions/{executionId}` → run doc with `items[]` (one `UnitV1` per test case, each with `id`, `name`, `state`, `assignedAgentId`).
3. `GET /{spaceId}/_e2g/api/executions/{executionId}/units/{unitId}/attachments` → SAS-signed Azure Blob URLs: `logs.txt`, `JUnit.xml`, `TBoxResults.tas`, `TestSteps.json`, `Recording.mp4` (only when recorded). SAS TTL ≈ 30 min; the blob GET needs **no Authorization header** — the signature is the entire auth.

| E2G attachment names | `list_unit_attachments` returns records with `name` ∈ {`logs`, `JUnit`, `TBoxResults`, `TestSteps`, `Recording`} and a separate `fileExtension` (`txt`/`xml`/`tas`/`json`/`mp4`). `Recording` is only present when `playlist.uploadRecordingsOnSuccess` triggered a capture. |

| SAS-signed blob GET must NOT include Authorization | The `contentDownloadUri` is a fully signed Azure Blob URL — adding `Authorization: Bearer …` causes Azure to 403 because the SAS signature *is* the auth. The CLI's `download_blob()` strips headers; if you call the URL by hand from `playlists attachments --json`, just `curl` the URL plain. SAS TTL ≈ 30 min; re-list attachments to refresh. |

## Personal agents: identity, dispatch and preflight details

| Personal/private agents are invisible to the CLI's service token | `Tricentis_Cloud_API` (`client_credentials`) only sees agents with `"private": false` in `_e2g/api/agents`. A personal Local Runner registered to the developer's Okta identity returns **403 "Unauthorized access to agent"** on direct GET, and any `playlists run`/`testDebugging/runs` POST will sit `Queued` forever because no shared agent claims it. Pinning `AgentIdentifier=<personalAgentName>` does NOT help — dispatch is owner-scoped, not name-scoped. |

| Local Runner preflight (else runs hang or fail oddly) | (a) Install Tosca Local Runner / Cloud Agent on the developer machine — registers the personal agent; (b) install + enable the Tricentis Automation Extension in the Chrome and/or Edge profile the agent will drive; (c) keep the target browser window MAXIMIZED before triggering the run. Minimized / shrunken browsers cause `coordinate out of bounds`, `element not in view`, or silent click misses. Re-launch the Local Runner if the agent disappears from `_e2g/api/agents` (only visible to MCP/user identity). |

The fastest debug loop for a brand-new test case is to bind it to the user's **own machine as a personal agent** and re-run via MCP after each fix. This is the path the Portal's "Run on personal agent" button uses.
- **MCP** (`ToscaCloudMcpServer`) is wired in `.vscode/mcp.json` via `mcp-remote` with PKCE OAuth. First connection opens a browser, the developer logs in to Okta as themselves, and the refresh token is cached. From then on every MCP call carries the **developer's user identity**, so it can list, dispatch to, and read runs from the developer's personal agent.

## Polling personal-agent results via MCP: tool semantics


The CLI's `playlists status/logs` returns **403** on personal-agent runs — `Tricentis_Cloud_API` can't see them. Use MCP:

1. **Authoritative pass/fail for a specific playlist** — `mcp__ToscaCloudMcpServer__GetRecentPlaylistRunLogs(playlistId)`. Returns a succeeded-and-failed-log pair; `["No succeeded runs found."]` means the latest run for that playlist did **not** pass.
2. **Find an executionId for your run** — `mcp__ToscaCloudMcpServer__GetRecentRuns({nameFilter: "<exact playlist name>"})`. The `nameFilter` must be the **exact** playlist name including any em-dash (`—`, `\u2014`) / en-dash; partial substring doesn't match. Returns executionIds for runs of that playlist.
3. **Inspect failures** — `mcp__ToscaCloudMcpServer__GetFailedTestSteps({runIds: ["<executionId>"]})`. Requires the **executionId**, not the `playlistRun.id` returned by `RunPlaylist` — passing the latter errors with `"Run with the specified ID doesn't exist."`
4. **Do not** trust `GetRecentRuns({stateFilter})` without `nameFilter` — it returns ~10 executionIds sorted alphabetically by UUID (not by time) and you can't tell which is yours. Always filter by name.

  - `GetRecentRuns({nameFilter: "<exact playlist name>"})` — returns executionIds only for matching playlist. The `nameFilter` must be **exact** including em-dash/en-dash characters (`—` is `\u2014`); partial substring matches return `[]`.

## MCP tooling: capability split, naming, first-turn cancellation

- **First-turn MCP-boot cancellation after VS Code reload.** If your first request in a fresh Chat window comes back with `result.errorDetails = {"code":"canceled"}` and `response = [{"kind":"mcpServersStarting"}]`, the TOSCA MCP server is still completing its PKCE/OAuth handshake. **Retry the request once** — do not re-dispatch playlists or re-author test cases; the prior request never executed. The handshake takes 3-8 s and is async; Copilot races it on the first turn.

- **MCP vs CLI — capability split.** MCP write tools are **scaffolding-only**. Do not use `ScaffoldTestCase` when the user asks to `copy`/`clone`/`duplicate` a test case — it drops attribute bindings, `ControlFlowItemV2` nodes, and parameter values. Correct split:
  - **MCP (read/dispatch/inspect)**: `SearchArtifacts`, `AnalyzeTestCaseItems`, `GetModulesSummary`, `RunPlaylist`, `GetRecentRuns`, `GetRecentPlaylistRunLogs`, `GetFailedTestSteps`, `ListSimulatorAgents`, `Delete*ById`.
  - **CLI (writes with full fidelity)**: `cases clone`, `cases update --json-file`, `modules update --json-file`, `blocks update`, `cases patch`, `inventory move`, TSU export/import.
  - **CLI (writes with care — confirm-GET required)**: `cases patch`, `inventory patch` — silent-no-op on unsupported ops.

- **MCP tool naming convention.** Tools are `mcp__ToscaCloudMcpServer__<MethodName>` — **double underscore**, PascalCase server name, PascalCase method. Do not write `mcp_toscacloudmcp_*` in user-facing text or tool invocations — that's a Copilot-autocomplete mistake and will not resolve.

## Undocumented APIs implemented by the CLI


These are implemented in the CLI and work on the live tenant:

- **Inventory v1 folder ops**: create-folder, rename-folder, delete-folder, folder-ancestors, folder-tree
- **MBT TSU**: export-tsu (→ binary blob), import-tsu (multipart upload)

## Reusing scanned modules instead of creating new ones


- If a test case for the same app already exists, **always** check `cases steps <existingCaseId> --json` first — TOSCA Studio may have already scanned the page and created a `HtmlDocument` module with all attributes. Reuse that module's `id` and attribute `id` values verbatim.
- Only create a new module when no existing scanned copy exists.
- The difference: scanned modules have self-healing data (`SelfHealingData` steering parameter with a JSON blob) — manually created ones don't. Both work, but scanned modules are more resilient to minor DOM changes.

## SAP Precondition block internals: `{PL[...]}` references and sample values

**Internal steps (in order):**
1. `ProcessOperations` — `taskkill /f /im saplogon.exe` (kills any existing SAP session)
2. `Timing.Wait` — 5000 ms
3. `SAP Logon` — opens SAP Logon Pad, selects the connection
4. `SAP Login` — fills Client / User / Password via `{PL[...]}` references, clicks Enter

Sample values from agent L756-758 (tenant-specific; the skill uses placeholders and the `Program Files (x86)` path)
```json
    { "id": "<fresh-ULID>", "referencedParameterId": "01KHJSJ4D4AY1BG2KDK4BAK1TD", "value": "C:\\Program Files\\SAP\\FrontEnd\\SAPgui\\saplogon.exe" },
    { "id": "<fresh-ULID>", "referencedParameterId": "01KHJSJ6H4EVTFQVGTKSVGA05G", "value": "E93" },
    { "id": "<fresh-ULID>", "referencedParameterId": "01KHJSJ8TFB32TV3W42JFMYCFN", "value": "100" },
```

---
