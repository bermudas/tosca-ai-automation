---
name: toscacloud-cli
description: "Tosca Cloud automation through the direct REST CLI `tools/toscacloud-cli/tosca_cli.py` (MBT / Inventory / Playlist APIs), plus deep reference for the Cloud test-case JSON model: Html (web) and SapEngine (SAP GUI) modules, TechnicalId/RelativeId locators, reusable blocks with ULID parameter wiring, 4-folder case layout, standard modules, TSU import/export, no-defect-masking and write-confirmation rules. Use when the official toscactl/tn/Tosca Cloud MCP path cannot do the job (hits a gap, a limit or an error), or whenever you need the JSON-level model of Cloud test cases and modules. Also a design reference for Tosca Commander (Server) modules/steps, whose concepts are similar."
license: MIT
compatibility: "Python 3.10+. Packages: tools/toscacloud-cli/requirements.txt. Credentials in tools/toscacloud-cli/.env (TOSCA_TENANT_URL, TOSCA_SPACE_ID, TOSCA_TOKEN_URL, TOSCA_CLIENT_ID, TOSCA_CLIENT_SECRET); token cached next to the script. Run from the repo root: python tools/toscacloud-cli/tosca_cli.py <command>"
argument-hint: "Describe the TOSCA task (e.g. 'create a test case for login flow', 'run smoke playlist and show failures', 'move all Web test cases into the Regression folder')"
metadata:
  author: bermudas
  version: "1.0"
  repository: https://github.com/bermudas/toscacloud_cli
---

## Where this fits

This is the **fallback runtime** for Tosca Cloud. Official Tricentis tooling comes first. See the `tosca-platform-guide` skill for the full routing:

1. **toscactl** (official CLI, `tosca-cloud` + journey skills) → 2. **tn** for toscactl gaps → 3. **Tosca Cloud MCP** (`ToscaCloudMcpServer`, e.g. personal-agent runs) → 4. **this CLI** when the above can't do it (missing command, limit, 403/404, or when you need raw MBT JSON control over modules, steps, blocks and ULIDs).

The **reference material** below (JSON model, locators, blocks, best practices, no-defect-masking) applies whichever runtime executes the change.

Setup (one-time):

```bash
python3 -m venv tools/toscacloud-cli/.venv
source tools/toscacloud-cli/.venv/bin/activate
pip install -r tools/toscacloud-cli/requirements.txt
cp tools/toscacloud-cli/.env.example tools/toscacloud-cli/.env   # then fill in; never commit
```

## When to use this skill

Use this skill for any task involving the Tricentis TOSCA Cloud REST API or the `tosca_cli.py` CLI:

- **Test cases** — create, update, clone, patch work state, export/import TSU
- **Modules** — create or update Html (web) or SAP GUI modules with locator attributes
- **Reusable blocks** — extend parameters, wire block references into test cases
- **Inventory** — search, move, organize into folders
- **Playlists** — list, run, check results
- **Web automation** (Html engine) — use Playwright to discover element locators, build modules, assemble 4-folder test cases
- **SAP GUI automation** (SapEngine) — create screen modules with `RelativeId` locators, wire the Precondition block
- **PDF verification** (Pdf engine) — verify saved/printed PDF content via `PdfDocument` modules (see [pdf-modules.md](references/pdf-modules.md))
- **Any TOSCA Cloud REST API operation** not listed above

## Core principle — always discover before acting

The MBT API has no general list endpoint; use Inventory for user-created artifacts and `/packages` for built-in modules:

1. `inventory search "<name>" --type TestCase` — find test case IDs
2. `inventory search "<name>" --type Module` — find **user-created** module IDs (built-in Standard modules do not appear here)
3. `cases get <id> --json` + `cases steps <id> --json` — ground truth for step composition, module IDs, attribute refs, config params
4. **Standard modules** (engine-bundled — OpenUrl, CloseBrowser, Wait, Execute JavaScript, HTTP, DB, file, email, T-code, etc.) do NOT appear in `inventory search`. Discover via `GET /_mbt/api/v2/builder/packages`. **Before** building a custom wrapper for any common capability, check there first — see [standard-modules.md](references/standard-modules.md).
5. Use the discovered JSON as the template when creating or patching similar cases.

## Workflow discipline — one artifact at a time

Work sequentially, not in batches. Each build cycle is a complete loop:

1. **Discover** — `inventory search` → read an existing similar artifact (`cases steps --json` / `modules get --json`) as ground truth.
2. **Explore** — use Playwright MCP (web) or read similar existing modules (SAP) to confirm element identity **before** writing JSON. Never commit a module whose locator matches >1 element — verify via `browser_evaluate` that the count is exactly 1.
3. **Build** — module → test case → placement, using fresh ULIDs where required (`businessParameter.id`, block-ref `parameters[].id` — but `parameterLayerId` is copied verbatim from the block, see ULID generation section). **Before finalizing identification choices, action modes, or folder structure**, reconcile against [best-practices.md](references/best-practices.md) (condensed from the 10 official Tricentis Best Practices KBs) — it is the "whether/why" reference that complements the mechanical how-to guides.
4. **Run** — personal agent via MCP for iterative debug, shared agent via CLI for CI/scheduled runs.
5. **Inspect** — on failure, read the exact TBox message via `GetFailedTestSteps` (MCP) or `playlists logs` (CLI). Classify the failure (see next section) before changing anything.
6. **Fix** — minimum-diff change: patch the offending module/step, not the whole case. **Probe, don't guess** (see below).

### Debugging discipline — probe, don't guess

Measured on a real session: guessing cost ~6 runs at ~2 min each; the first probe named the cause in **1**.

- **If the failure message does not name the cause, install a probe instead of a fix.** A TOSCA failure message reports where execution stopped, which on an SPA is routinely several steps *downstream* of the defect (a silently-cleared login field surfaces as `Could not find Link 'Sign Out'`; a silently-empty cart surfaces as `Could not find Button 'CHECKOUT'`). One guess is allowed; after it fails, probe.
- **Use an assert-success probe, not an always-failing one.** A `Verify JavaScript Result` step whose *expected* value is the success signature is silent when healthy and prints `Expected … / Actual …` (returned by `GetFailedTestSteps`) when not — and it does not abort the run. An always-failing probe aborts everything after it. Keep the good ones permanently as guards.
- **Pull the recording before theorising about UI state.** `Recording.mp4` and `TestSteps.json` come from the same attachments endpoint as `logs.txt`. A frame answers "was the field empty / the button disabled / did the page navigate" instantly; inferring it costs runs. Use `scripts/tosca_run_artifacts.py frames <playlistId>` — it aligns log timestamps to video offsets automatically.
- **One variable per run.** Two simultaneous edits destroy attribution — you learn neither which fixed it nor whether either did.
- **Never add a wait without a wait-shaped failure.** A disabled button and a not-yet-rendered element produce the same `Could not find …`. Prove the state is correct before blaming timing; otherwise you bake in a permanent unjustified static wait.
- **A passing guard narrows the search, it does not clear the step.** If `Verify quantity is 4` passes but the cart is empty, the value was right and the defect is elsewhere in that step group — often an async effect that was never awaited.
- **Inherited masking is a defect to restore first.** If a test you pick up already substitutes `Verify JavaScript Result` DOM clicks or injected values for real GUI steps, restore the GUI steps *before* debugging anything else. Those workarounds hide the real failure and destroy the coverage the test exists for — the same reasoning as the no-defect-masking rule above, applied to work you did not write.
7. **Confirm the write landed** — GET the artifact and check that the **`version` bumped** and the specific field you edited actually changed. A `✓ patched` / `204 No Content` from the API is **not** proof the delta was applied: MBT silently accepts unsupported JSON Patch ops (e.g. `remove` on an array element, deep JSON pointer paths like `/testCaseItems/1/items/2/testStepValues/0/value`, `move`) and returns 204 with zero changes. Inventory v3 PATCH has its own PascalCase/`{"operations":[…]}` wrapper — a request in MBT shape is accepted but ignored. Never report a change as done, never run the test, and never claim a fix based on the CLI's own "success" message alone. If PATCH did nothing, fall back to full PUT (`cases update` / `modules update`; for blocks `blocks add-param` / `blocks set-value-range`, which PUT the whole block internally).
8. **Validate** — re-run and confirm the step that previously failed now passes. Don't move on until green (or the failure is a documented application defect).
9. **Report** — IDs (entityId / moduleId / playlistId), folder placement, any remaining gaps.

Don't batch: don't build 5 cases and then run them together. Build one, run it, fix it, then start the next.

## Test-data hygiene — reset shared server-side state

Web tests that mutate **account-scoped server state** (shopping cart, saved profile, drafts) are not repeatable by default. Two failure modes, both seen on AOS 2026-07-22:

- **A failed run poisons the next one.** A run that added items but died before checkout leaves them behind; the next run's assertion reads `Expected "2" / Actual "6"`.
- **Your own exploration poisons the run.** Browsing the live app while logged in **as the test account** writes to the same server-side state. Explore logged out, or with a different account, or clean up afterwards.

**Put the reset in its own folder after Login, not in the flow under test.** It is test-*data* setup: the journey being tested keeps every one of its assertions, so this is not defect masking — the distinction is that you are establishing preconditions, not weakening a check. Navigate with the **app's own controls** (header links) rather than `OpenUrl`, and finish with an assertion that the state really is clean, so a failed reset fails at the reset rather than corrupting a later step.

## Before you call it an application defect

An app defect is a legitimate finding, but the bar is evidence, not elimination. Require **all** of:

1. **Every automation-side cause is ruled out** — locator resolves, value verified present, correct route, no stale document. Most "app defects" this session were mine (`UserSimulation`, a no-op `OpenUrl`).
2. **A recording A/B**, ideally within a single run: the same action working at one point and doing nothing at another, on an identical-looking page. That is far stronger than a log line.
3. **The app's own confirmation is absent** — a control that normally produces visible feedback (a mini-cart panel, a badge increment) produces none.

Recurring archetype worth checking first: **an SPA action that dies after a completed transaction** (AOS's ADD TO CART no-ops after an order until the page is reloaded). If you work around it, mirror what a real user must do, and record the defect in the test case `description` so the workaround carries its justification and is not later "cleaned up" as unexplained.

## No-defect-masking rule

When a run fails, classify BEFORE changing anything:

| Failure type | Typical signal | Permitted action |
|---|---|---|
| **Infrastructure** | `Could not find Link ...`, `More than one matching tab`, stale `SelfHealingData`, extension not attached, timing | Fix the TechnicalId, tighten module-level `Url`/`Title`, add a `Wait`, fix the agent environment. Re-run. |
| **Application defect — isolated** | One `Verify` step fails; the rest of the flow still executes meaningfully | Keep the `Verify` step. Note the defect in the step `description` or a tracker link; raise the bug. **Do not** delete or weaken the assertion. |
| **Application defect — blocks flow** | The product bug prevents the core path (popup never opens, login rejected on valid creds) | Let the test fail. A red run is the correct regression signal for a real bug. |

**Forbidden — regardless of reasoning:**
- Removing a `Verify` step to make the run green.
- Changing `actionMode: Verify` + `actionProperty: "Visible"`/`"InnerText"` to a weaker form (dropping `actionProperty` so the step just interacts).
- Deleting an attribute from a module so a failing lookup stops happening.
- Setting `disabled: true` on a step that catches a genuine product bug.
- Wrapping a failing `Verify` in `ControlFlowItemV2 If` so the test silently skips the bug.
- The **re-scoping trap**: concluding "this assertion belongs in a different test case" and removing it from the current one. If a step belonged in this case when it was written, it belongs there now.

The only legitimate way to keep a run green while a known product bug exists is to raise the bug and either leave the test failing or set `disabled: true` with a description linking to the tracker. Masking a defect creates false confidence and defeats the regression suite.

## TechnicalId priority (Html engine)

When picking locator parameters for a new Html module attribute, prefer higher-rank options first. Stability beats cleverness — avoid framework-generated class names and long absolute XPaths.

1. **`Tag: INPUT` + `Id`** — first-choice locator for form fields (text/password inputs, checkboxes). Use the DOM `id` attribute verbatim: `{"name": "Id", "value": "<dom-id>", "type": "TechnicalId"}`. Validated in production scanner-generated modules: Email/Password/RememberMe are bound by `Id` + `Tag` as their only TechnicalIds (scanner self-healing weights `Id` at 1.0) and are steered with `actionMode: Input` in Completed test cases. (Earlier guidance here claimed `Id` is silently ignored by the Html engine — that was wrong; this ranking matches `references/best-practices.md`, which ranks `id` first.)
2. **`Tag` + unique `Title`** — stable, locale-independent. Use when the target has a meaningful `title=""`.
3. **`Tag: INPUT` + `Name`** — fallback for form fields that have no DOM `id`.
4. **`Tag` + `InnerText`** — clickable buttons/links with short, unique, stable, locale-appropriate text. Remember `InnerText` matches the full `textContent` exactly, including nested children and literal `\r\n` line breaks (`"Shopping cart\r\n(0)"`), and is case-sensitive (so it differs from CSS `text-transform: uppercase` rendering). `*` wildcards are allowed anywhere in the value — `InnerText: "*@*.*"` matches any logged-in e-mail address.
5. **`Tag: INPUT` + `Value`** — for `<input type="submit|button">` buttons the HTML `value` attribute IS the visible caption; `InnerText` is empty on these elements. Use `{"name": "Value", "value": "<caption>", "type": "TechnicalId"}`.
6. **`Tag` + `HREF` + `ClassName`** — nav links. `HREF` must be absolute; `ClassName` discriminates between duplicated mobile/desktop/dropdown copies of the same link.
7. **`Tag` + `ClassName`** — for dynamic-text verify targets (e.g. `ClassName: "field-validation-error"` + `Tag: SPAN`) and as a last-resort anchor. Prefer semantic BEM-style class names; avoid framework-generated hashes like `css-xyz123`.

After picking a candidate, run a uniqueness check via Playwright MCP:

```javascript
document.querySelectorAll('<your css>').length   // MUST be 1
```

If >1, add another discriminator before saving the module. TOSCA will NOT warn you at save time — the ambiguity only surfaces at runtime as `Could not find Link '...'` or `More than one matching ...`.

## Pre-run quality gates

Before triggering a run, confirm these **mechanical** checks here, and walk through the **conformance** checklist in [best-practices.md](references/best-practices.md) (naming, TestCase structure, identification priority, forbidden `{CLICK}`/`{SENDKEYS}` patterns, etc.):

- [ ] Module has root-level `Engine: Html` (or `SapEngine`) configuration parameter.
- [ ] Every parameterized `TestStepFolderReferenceV2` carries the block's own `parameterLayerId` (copy it from `blocks get --json <blockId>` → root `parameterLayerId`; identical across all references to that block). References to parameterless blocks omit the key and use `"parameters": []`.
- [ ] Every parameter value entry has `referencedParameterId` pointing to a real `businessParameter.id` on the block.
- [ ] `version` field stripped from PUT bodies (the CLI does this automatically).
- [ ] Each attribute locator matches exactly one element on the live page (Playwright MCP uniqueness check).
- [ ] **No `UserSimulation` Steering param on any form-input attribute** unless proven necessary against the live page. It types at whatever holds focus, so when focus is elsewhere the step reports `[Succeeded]` and the field keeps its **prior/default** value. Check with `modules get --json <id>` — search every `attributes[].parameters[]` for `"name": "UserSimulation"`. The steering that actually sets a value on an SPA input is `FireEvent=change`.
- [ ] Every `Input` into an SPA form field is followed by a `Verify` of the value on the same attribute. A field that was never written is the most expensive failure mode to diagnose — without the guard it surfaces several steps downstream as an unrelated `Could not find …`. Do **not** add a new settle here on suspicion: on AOS the coin-flip was `UserSimulation`, not a hydration race.
- [ ] Any mid-test `OpenUrl` reload is (a) not hash-identical to the current URL — otherwise it is a silent no-op — and (b) followed by a document-freshness guard, since `OpenUrl` returns before the page has loaded. Re-authenticate afterwards if the app keeps its session in memory.
- [ ] Precondition starts with `OpenUrl` (all 3 params: `Url`, `UseActiveTab=False`, `ForcePageSwitch=True`) and a `Wait` step for SPAs.
- [ ] Leftover-tab handling: on workstation agents that share the user's Chrome, cleanup is wrapped in `ControlFlowItemV2 If` with a narrow `Title="*<AppName>*"` — never an unconditional `CloseBrowser Title="*"`.
- [ ] Local Runner preflight done (extension enabled in target browser, browser maximized) for personal-agent runs.
- [ ] Conformance walkthrough completed — see [best-practices.md](references/best-practices.md) "Agent checklist" section.

## Declarative execution

Act, don't ask. Once the user has approved a task ("build a test for flow X"), execute the full discover → build → place → run → inspect loop without asking for permission between steps. State what you are doing, not what you propose to do.

- ✗ "Shall I create the module first or the test case?"
- ✓ "Creating the module now." (then does it)

Only pause for explicit confirmation on irreversible actions: `delete-folder`, `delete-block`, `--force`, overwriting a test case whose current version you haven't inspected.

## Decision tree

| Goal | First action |
|------|-------------|
| Extend coverage / gap fill | `inventory search` in the folder → `cases steps --json` on ALL existing cases to find the pattern |
| Create new test case | `inventory search` for similar cases first → clone or assemble from template |
| Find something | `inventory search "<keywords>" [--type TestCase\|Module\|folder]` |
| Run tests on grid/team agent | CLI: `playlists list` → `playlists run <id> --wait` |
| Run on developer's local machine (iterative debug) | MCP: `RunPlaylist(playlistId, runOnAPersonalAgent=true)` — see Iterative loop section below |
| Move / organize | `inventory move <type> <entityId> --folder-id <folderEntityId>` |
| Export / import | `cases export-tsu --ids "id1,id2" --output file.tsu` / `cases import-tsu --file file.tsu` |
| Create Web test case | Use Playwright to snapshot the page → discover element locators → create module → create case → see [Web Automation guide](references/web-automation.md) |
| Create SAP GUI test case | `inventory search "<TCODE>" --type Module` → create/reuse modules → assemble case → see [SAP GUI guide](references/sap-automation.md) |
| Verify a printed/saved PDF (receipts, reports) | Scan the sample PDF once in the Portal → extend the `PdfDocument` module via API → wire `Target PDF = {B[FileName]}` + Page/anchor `Select` entries with `Verify` subValues → see [PDF guide](references/pdf-modules.md) |
| Run JavaScript in the page / read cookie / scroll / CSS query a hydrated SPA / scanner is blind to body content | Use the `Verify JavaScript Result` or `Execute JavaScript` **Standard** module (GUIDs + attribute IDs + ready-to-paste JSON in [standard-modules.md](references/standard-modules.md)). Do NOT reach for `{SCRIPT[...]}` dynamic value — it is not a registered command on Tosca Cloud. Do NOT try to import the Standard subset — it's already on the agent, reachable by GUID |
| Any functionality the platform probably ships (HTTP, DB query, file, email, clipboard, timing, T-code…) | First `GET /_mbt/api/v2/builder/packages` → find the module → get attribute IDs via `packages/{packageId}/modules/{moduleId}` → hard-code the GUIDs in your generated test step. Writing a custom wrapper is almost always wrong |

## Key CLI commands

```bash
# Discovery
python tools/toscacloud-cli/tosca_cli.py inventory search "<name>" [--type TestCase|Module|folder] [--include-ancestors]
python tools/toscacloud-cli/tosca_cli.py inventory search "" --type TestCase --folder-id <entityId>
python tools/toscacloud-cli/tosca_cli.py inventory get TestCase <entityId> --include-ancestors

# Test cases
python tools/toscacloud-cli/tosca_cli.py cases get <caseId> --json          # full metadata
python tools/toscacloud-cli/tosca_cli.py cases steps <caseId> --json        # full step tree (use this first)
python tools/toscacloud-cli/tosca_cli.py cases create --name "..." --state Planned
python tools/toscacloud-cli/tosca_cli.py cases update <caseId> --json-file case.json   # full PUT
python tools/toscacloud-cli/tosca_cli.py cases clone <caseId> --name "..."
# Shortcuts (GET → mutate → full PUT in one command; top-level folders only)
python tools/toscacloud-cli/tosca_cli.py cases scaffold-web <caseId> --url https://… [--title "…"]   # 4 folders: OpenUrl / (empty Process) / optional title Verify / CloseBrowser
python tools/toscacloud-cli/tosca_cli.py cases insert-step <caseId> <Folder> --json-file step.json [--after NAME|--before NAME|--at-start]   # one TestStepV2; missing ids filled
python tools/toscacloud-cli/tosca_cli.py cases set-step-value <caseId> <Folder> <Step> <Attr> --to "…" [--js]   # one testStepValue.value; --*-index N when names repeat
python tools/toscacloud-cli/tosca_cli.py cases export-tsu --ids "id1,id2" [--module-ids "m1"] [--block-ids "b1"] --output file.tsu
python tools/toscacloud-cli/tosca_cli.py cases import-tsu --file file.tsu

# Modules
python tools/toscacloud-cli/tosca_cli.py modules get <moduleId> [--json]
python tools/toscacloud-cli/tosca_cli.py modules create --name "..." --iface Gui
python tools/toscacloud-cli/tosca_cli.py modules update <moduleId> --json-file body.json
python tools/toscacloud-cli/tosca_cli.py modules add-attr-param <moduleId> <Attr> <Param> --to "…" [--type TechnicalId|Steering|Configuration]   # upsert an attribute parameter, keeps its id
python tools/toscacloud-cli/tosca_cli.py modules set-param <moduleId> <Param> --to "…" [--type …]   # upsert a module-level parameter (Title, Url, Engine, steering flags)

# Reusable blocks
python tools/toscacloud-cli/tosca_cli.py blocks get <blockId>
python tools/toscacloud-cli/tosca_cli.py blocks add-param <blockId> --name <name> [--value-range '1,2,3']
python tools/toscacloud-cli/tosca_cli.py blocks set-value-range <blockId> <paramName> --values '1,2,3,4'
python tools/toscacloud-cli/tosca_cli.py blocks delete <blockId> --force

# Test case patch (partial update)
python tools/toscacloud-cli/tosca_cli.py cases patch <caseId> --operations '[{"op":"replace","path":"/workState","value":"Completed"}]'

# Playlists
python tools/toscacloud-cli/tosca_cli.py playlists create --name "…" [--run-mode parallel|sequential|sequentialOnSameAgent]
python tools/toscacloud-cli/tosca_cli.py playlists attach-case <playlistId> <caseId> [-p key=value …]   # appends an InputTestCaseV1 item (+ per-item parameters)
python tools/toscacloud-cli/tosca_cli.py playlists list
python tools/toscacloud-cli/tosca_cli.py playlists list-runs
python tools/toscacloud-cli/tosca_cli.py playlists run <id> --wait
python tools/toscacloud-cli/tosca_cli.py playlists results <runId>
python tools/toscacloud-cli/tosca_cli.py playlists logs <runId>                    # per-unit agent logs (E2G, full TBox transcript)
python tools/toscacloud-cli/tosca_cli.py playlists logs <runId> --save ./logs      # save logs.txt + JUnit.xml + TBoxResults.tas + TestSteps.json
python tools/toscacloud-cli/tosca_cli.py playlists attachments <runId>             # SAS URLs per unit (no download)

# Folders
python tools/toscacloud-cli/tosca_cli.py inventory move testCase <entityId> --folder-id <folderEntityId>
python tools/toscacloud-cli/tosca_cli.py inventory create-folder --name "..." [--parent-id "..."]
python tools/toscacloud-cli/tosca_cli.py inventory rename-folder <folderId> --name "..."
python tools/toscacloud-cli/tosca_cli.py inventory delete-folder <folderId> [--delete-children] --force
python tools/toscacloud-cli/tosca_cli.py inventory folder-ancestors <folderId>
python tools/toscacloud-cli/tosca_cli.py inventory folder-tree --folder-ids "<parentFolderId>"
```

## Critical caveats

| Situation | What to do |
|-----------|-----------|
| `--json` flag placement | Place before positional args: `cases get --json <id>` ✓ |
| Block IDs ≠ Module entity IDs | Get block IDs from `cases get --json <caseId>` → `testCaseItems[].reusableTestStepBlockId` where `$type == "TestStepFolderReferenceV2"` |
| `parameterLayerId` | It is the **block's** parameter layer, defined on the block itself — `blocks get --json <blockId>` returns a root-level `parameterLayerId`, and every `TestStepFolderReferenceV2` to that block must carry that exact value verbatim (it is identical across all cases referencing the same block; never mint a fresh ULID per reference). If the block has no `businessParameters`, the block has no `parameterLayerId` and the reference must **omit the key entirely** alongside `"parameters": []`. A parameterized reference with a missing or wrong `parameterLayerId` has all its parameter values silently ignored. Verified across all 26 block references in 11 production cases. |
| Entity ID truncation in table | Always use `--json` to get full IDs before passing to commands |
| Html module root `Engine` param | Manually created Html modules must have `{"name":"Engine","value":"Html","type":"Configuration"}` in the root-level `parameters` array. Without it: _XModules and XModuleAttributes have to provide the configuration param "Engine"_ |
| Duplicate page elements | Modern pages render the same nav link in mobile + desktop. `Tag+InnerText+HREF` alone matches all copies. Use `browser_evaluate` to count matches; add `ClassName` to discriminate. |
| `OpenUrl` to a **hash-identical** URL is a silent no-op | Navigating to `https://host/#/` while the browser is already at `#/` performs **no document load at all**. TOSCA reports `[Succeeded]`, there is no warning, and nothing happens — so a "reload" step can appear in the log for runs where no reload ever occurred. This invalidated two separate diagnoses before it was detected. To force a real load, change more than the hash: `https://host/?reload=1#/`. Verify it landed (row below) rather than assuming. |
| `OpenUrl` returns **before** the page has loaded | It only *issues* the navigation — `[DURATION: 00:00:00.039]` for a full page load is the tell. Any step placed after it can run against the **old** document, and clicks on the outgoing page report `[Succeeded]` while doing nothing. Never treat `OpenUrl` as synchronous; follow it with a freshness guard (next row), and prefer the app's own in-page navigation (a header link) when you just need a route change — those are ordinary SPA transitions that `WaitOn` can synchronise on. |
| Proving a reload actually happened | `Verify JavaScript Result` with `return (Date.now() - performance.timeOrigin < 20000 ? 'fresh' : 'stale-' + Math.round(Date.now() - performance.timeOrigin));` — `performance.timeOrigin` is set per document load, so this is the document's **age in ms**. Expected `fresh`. When wrong it prints the real age (`stale-40135` = a 40 s old document that never reloaded), which converts "how long should I wait?" guesswork into a fact. Brace-free JS, per the `{`-parser trap. |
| A real reload drops an SPA's **in-memory session** | After a genuine document load the app may be logged out even though cookies survive — on AOS the cart still worked as a guest but checkout could not reach the payment step. Any reload-based workaround must re-authenticate afterwards. Clone the working Login steps (fresh ULIDs) rather than authoring a second variant, so both logins keep the same guards. |
| Leftover browser tab | Do **not** open Precondition with an unconditional `CloseBrowser Title="*"`. On a workstation agent sharing the developer's Chrome it closes the user's own tabs, and on any agent with no Chrome running yet it hard-fails (`UnestablishedConnectionException`, ~10 s timeout) — which tempts you to delete the cleanup entirely, and then tabs accumulate across failed runs until element lookups resolve against more than one document (`Found multiple controls for Link '…'` on an id that is provably unique in the DOM). Scope it instead: module-level `Url=https://<host>*` on **every** module, plus a `ControlFlowItemV2 If` whose condition is a VJS probe, wrapping `CloseBrowser Title="*<AppName>*"`. Unconditional `Title="*"` is acceptable only on a dedicated-profile grid agent that already has Chrome running. |
| MBT PATCH ops | Lowercase: `replace`, `add`, `remove`. Response is 204 No Content — always GET the artifact afterwards and confirm `version` bumped and the target field actually changed. Unsupported ops (deep JSON-pointer paths into nested step trees, `remove` on array elements, `move`) are **silently ignored**: CLI still prints `✓ patched`, server still returns 204, but the body is unchanged. When the confirm-GET shows no diff, fall back to `cases update` / `modules update` (full PUT), or the `cases set-step-value` / `cases insert-step` / `modules add-attr-param` shortcuts, which do the GET → mutate → PUT round-trip for you. Blocks: `blocks add-param` / `blocks set-value-range` (there is no `blocks update` command). |
| Inventory v3 PATCH body | Wrapper: `{"operations": [{"op": "Replace", ...}]}` — PascalCase op. Same confirm-GET rule: an MBT-shape body (bare array, lowercase op) is accepted and 204'd but applies no changes. |
| Confirm writes before claiming success | Never trust the CLI's own `✓` line, an HTTP 204, or a `{}` response body as proof that your edit persisted. Always follow a write with a GET and assert the delta (usually: `version` field bumped). MBT PATCH has two silent-no-op cases (unsupported ops, deep paths); `modules update` returns `{}` on success too. One trivial probe — `{"op":"replace","path":"/description","value":"…"}` round-trip — is enough to calibrate whether the endpoint is accepting your shape before you batch real edits. |
| Inventory search filter | Despite swagger, only lowercase works: `contains`, `and` |
| SAP standard modules | Not in inventory. The `Sap` package ships 19 modules — `SAP Logon`, `SAP Login`, `SAP Toolbar` (the "T-code" module `35fcfe84`), `SAP Statusbar` (`aca7c8ee` — verify + `{XB[…]}` doc-number capture), `SAP SubToolBar` (`d82fd0e7` — tooltip-glob button clicks like `"Save*"`), `SAP Menu`, `SAP TreeView`, `SAP Emulated Table Tree`, `SAP Message Toast`, `SAP WaitForBusyIndicator`, … — use IDs directly from the [SAP guide](references/sap-automation.md) or re-discover via `GET /_mbt/api/v2/builder/packages` |
| TSU export field | `reusableTestStepBlockIds` (no double-e) |
| `version` in PUT body | Omit — rejected by case, block, **and** module PUT endpoints. CLI's `update_case`/`update_block`/`update_module` strip it automatically |
| MBT test case ID = Inventory `entityId` | `cases get`/`steps`/`update` accept only the Inventory `entityId`. Playlist item `id` and inventory `attributes.surrogate` both 404. Resolve via `inventory search … --type TestCase --json` → `id.entityId` |
| Failed playlist run with `<failure />` only | Playlists v2 has no step-level log endpoint, but E2G does. Use `playlists logs <runId>` — it walks `/_e2g/api/executions/{executionId}` units → `/units/{unitId}/attachments` → SAS-signed Azure Blob downloads (logs.txt, JUnit.xml, TBoxResults.tas, TestSteps.json, Recording.mp4). Works under `Tricentis_Cloud_API`. The endpoint keys on `PlaylistRunV1.executionId`, **not** the playlist run's `id` — the CLI resolves this via `playlists status` automatically; pass `--execution-id / -e` to skip the lookup. SAS TTL ≈ 30 min; the blob GET must NOT carry an Authorization header. |
| Personal-agent runs need MCP, not CLI | `Tricentis_Cloud_API` (CLI service token) cannot dispatch to or read a developer's personal Local Runner — `_e2g/api/agents/<personalAgentName>` returns 403, and `playlists status <runId>` on a private run returns 403. Use `mcp__ToscaCloudMcpServer__RunPlaylist(playlistId, runOnAPersonalAgent=true)` to trigger and `GetRecentRuns` + `GetFailedTestSteps` to inspect — MCP carries the developer's user identity (PKCE OAuth via `mcp-remote` configured in `.vscode/mcp.json`). |
| `cases delete` / `modules delete` / `blocks delete` → 403 | The `Tricentis_Cloud_API` client-credentials role has create/read/update/patch on MBT artifacts but **no delete privilege** on this tenant. Symptom: `DELETE /_mbt/api/v2/builder/testCases/{id}` returns 403 regardless of query-string tweaks (`?force=true`, `?permanent=true`), and all bulk variants (`testCases/bulkDelete`, `testCases/delete`, `DELETE /testCases` with body) are 405 — no such route. Inventory-side DELETE routes (`_inventory/api/v3/artifacts/testCase/{id}`, v1 equivalents) are 404/405. The MCP tool set carries the user's identity but doesn't expose a delete-test-case / delete-module / delete-block tool — only `DeletePlaylistById`. **Workarounds**: (a) delete via the Portal UI (the logged-in user's browser token has delete); (b) ask tenant admin to grant the Cloud-API role `testCases:delete` / `modules:delete` / `reuseableTestStepBlocks:delete`. Always run `inventory search` + playlist-reference scan before delete either way — dangling `sourceId` references in playlists are a harder cleanup than keeping a stale "(Copy)" case around. |
| Local Runner preflight | Before triggering on a personal agent: install Tosca Local Runner / Cloud Agent on the developer's machine; install + enable Tricentis Automation Extension in Chrome and/or Edge; keep the target browser **maximized** (minimized windows cause coordinate-out-of-bounds and silent click misses). |
| Html "More than one matching tab" | Agent shares the user's Chrome profile, and any run that aborts before Teardown leaves its tab open — tabs accumulate across runs and lookups then resolve against more than one document (symptom: `Found multiple controls …` on a unique id). Apply **both** fixes: (1) give every module a module-level `Url=https://<host>*` **plus the page's real `Title`** — an SPA serves the same document title on every route (AOS serves `" Advantage Shopping"` everywhere), so `Title` alone cannot separate two tabs of the same app and `Title="*"` scopes to nothing; (2) prepend a `ControlFlowItemV2 If` to Precondition whose condition is a **`Verify JavaScript Result` probe** (`UseActiveTab=False`, `Title=*<AppName>*`, `JavaScript` = `return 'present'`, `Result` Verify `present`), then = `CloseBrowser Title="*<AppName>*"`. Do **not** use a GUI `Verify … Visible=True` as the If condition — with no matching document it hard-fails instead of evaluating false, which is exactly the no-leftover-tab branch the `If` exists to handle; the VJS probe returns `""` there and the If cleanly skips. |
| Click operation values | Uppercase in braces: `{CLICK}`, `{DOUBLECLICK}`, `{RIGHTCLICK}`, `{ALTCLICK}`, `{CTRLCLICK}`, `{SHIFTCLICK}`, `{LONGCLICK}`, `{MOUSEOVER}`, `{DRAG}`, `{DROP}`. For hover use `{MOUSEOVER}` — **not** `{Hover}` (fails with _"No suitable value found for command Hover"_). Add `{MOUSEOVER}` to the Link's `valueRange`. Synthetic JS events don't fire CSS `:hover`; TOSCA's `{MOUSEOVER}` emits a real mouse move |
| `{Click}` reports Succeeded but browser doesn't navigate | Drupal / SPA mega-menu links sometimes log `[Succeeded] Click '…'` while the tab URL never changes — the next module's `Url=` scope then can't find the tab. Per Tricentis best-practices KB5 #12, replace `value: "{Click}"` with `value: "X"` (direct click — invokes the DOM click handler without mouse emulation). Do **not** try `{LEFTCLICK}` — not a registered Html-engine keyword, throws `[Exception]` with ~0.07 s duration. |
| Below-the-fold element: `Could not find …` though it is in the DOM (viewport scoping) | **Check the tag first** — for `H1`–`H6` see the heading-tag row; headings never resolve at any scroll position, and the only reproduction this viewport theory was ever built on is an `<h2>`. For non-heading tags viewport scoping is **plausible but never independently reproduced** — treat it as a hypothesis to test, not a known mechanism. A `Verify` on a below-the-fold `<div>`/`<span>` fails with `Could not find …` even though `browser_evaluate('document.querySelectorAll(sel).length')` ≥ 1. `ScrollToFindElement=True` steering does **not** reliably help. Fixes in order of preference: (1) prepend a `{SENDKEYS["{PAGEDOWN}"]}` / `{PAGEDOWN}` on the page body, or an `OpenUrl` to a fragment anchor, to bring the element into the viewport; (2) pivot to `Verify JavaScript Result` — CDP `Runtime.evaluate` sees the whole DOM regardless of scroll position. This is a different root cause from the "scanner observer disabled" case in `standard-modules.md`; check viewport first (`browser_evaluate('document.querySelector(sel).getBoundingClientRect().y')` vs `window.innerHeight`) before assuming the observer pipeline is broken. |
| Attaching cases to a playlist | The items list discriminator is `$type: "InputTestCaseV1"` (field: `sourceId`, **not** `id`). Folders use `InputFolderV1`. Using `TestCaseV1` / `TestCase` returns *"InputItemV1 $type must be either InputFolderV1 or InputTestCaseV1"*. |
| Module-level `Url` / `Title` must be `parameterType: "TechnicalId"` | Not `"Configuration"`. If set as `Configuration` the Html engine silently ignores them for tab scoping — symptom is persistent *"More than one matching tab was found"* regardless of how precise the pattern is. Verify with `modules get --json <id>` → `parameters[].parameterType`. Fix in-place via `modules update` with corrected type. |
| `UseActiveTab = True` alone rejected | Some tenants fail a `Verify JavaScript Result` step with `UseActiveTab=True` and no other criteria — raising *"Specify at least one of the Search Criteria."*. Always accompany with `Title=*<AppName>*` or `Url=https://<host>*`, or switch to `UseActiveTab=False` + Title/Url. The reliably working shape: `UseActiveTab=False` + `Title=*<AppName>*`. |
| `Found multiple controls for <Control> '<Name>'` on a provably unique DOM `Id` | **Check tab scoping before touching the selector.** The message names the *element*, not the tab, so it reads like a locator bug — but without a module-level `Url` (or with `Title="*"`) attributes resolve against **every** matching document, so two open tabs of the same app make a globally unique `id` match twice. SPAs make this the default failure: a single-title SPA serves the identical `document.title` on every route, so `Title` can never discriminate — you need `Url=https://<host>*`. Two checks, in order: (1) `modules get --json <moduleId>` → a host-scoped `Url` TechnicalId exists and `Title` is not `*`; (2) the Precondition still has its leftover-tab cleanup — with cleanup removed, every failed run leaves another tab behind and the ambiguity compounds each debug iteration. Only once the module is tab-scoped is the container-nesting cause (row below) worth investigating. Validated on AOS 2026-07-22: `Found multiple controls for Link 'User Menu' (Tag: A, Id: menuUserLink)` while `document.querySelectorAll('#menuUserLink').length === 1`; fixed by scoping alone, with no change to the attribute's selector. |
| Container nesting does NOT scope attribute matching | Nesting a Button attribute inside a Container attribute in the module tree affects only Steering-param inheritance — it does **not** scope DOM resolution. `moduleAttributeReference.id=<Button>` resolves globally against the document; if two matching buttons exist in different page regions, you still get *"Found multiple controls for Button '<Name>'"*. To discriminate: embed the discriminating ancestor class in the child's own selector (`ClassName` combining both), or switch to `Verify JavaScript Result` with a scoped `document.querySelector('.region-header button.lang-switch')`. |
| `GetRecentRuns` returns ~10 executionIds sorted alphabetically by UUID | A newly dispatched run whose UUID sorts late is **invisible** regardless of wait time. **Solution: dispatch debug runs from a dedicated, uniquely-named playlist** — `nameFilter` scopes to the playlist name, so a playlist with one run returns exactly one executionId. See "Getting the executionId of a personal-agent run" below. **When the user says "mcp glitched/reloaded"**: do **not** re-dispatch the playlist — the previous run is still executing. Re-issue the last read-side MCP call once and continue. |
| Personal-agent runs are invisible to the CLI **by permission, not by paging** | `GET /_playlists/api/v2/playlistRuns` under the service token returns only runs with `"private": false` — a personal-agent run is absent from the list entirely, so no `top`/`skip` paging trick reaches it, and `playlists status/logs <runId>` on it returns 403. Only the MCP tools (developer's Okta identity) can see it. |
| Keyboard command values | All uppercase-braced: `{ENTER}` `{TAB}` `{ESC}` `{F1}`..`{F24}` `{UP}` `{DOWN}` `{LEFT}` `{RIGHT}` `{BACKSPACE}` `{DEL}` `{HOME}` `{END}` `{SHIFT}` `{CTRL}` `{ALT}`. Advanced: `{SENDKEYS["..."]}`, `{KEYPRESS[code]}`, `{KEYDOWN/KEYUP[code]}`, `{TEXTINPUT["..."]}`. Ref: [keyboard_operations](https://docs.tricentis.com/tosca-cloud/en-us/content/references/keyboard_operations.htm) |
| Action mode cheat-sheet | `Input` write; `Insert` (API modules); `Verify` + `actionProperty` assert; `Buffer`/`Output` capture into `{B[name]}`; `WaitOn` dynamic wait; `Select` pick a specific child; `Constraint`/`Exclude` narrow tables. Ref: [action_types](https://docs.tricentis.com/tosca-cloud/en-us/content/references/action_types.htm) |
| Dynamic expressions | `{CP[Param]}` config param; `{B[Var]}` buffer (case-sensitive, **test-case-scoped** — does NOT cross cases, but DOES cross reusable-block boundaries within one case); `{MATH[...]}` arithmetic with `Abs/Ceiling/Floor/Max/Min/Pow/Round/Sign/Sqrt/Truncate`; string ops `{STRINGLENGTH}` `{STRINGTOLOWER}` `{STRINGTOUPPER}` `{TRIM}` `{STRINGREPLACE}` `{STRINGSEARCH}` `{BASE64}` `{NUMBEROFOCCURRENCES}` |
| `{XB[Buffer]}` wildcard-extract | Valid **inside a Verify value only** (`actionMode: "Verify"`, `actionProperty: ""`): matches the dynamic part of the actual text AND writes it to a buffer in one step — `"Standard PO created under the number {XB[PurchaseOrder]}"` on a StatusBar attribute verifies the literal prefix and captures the document number. Read downstream with `{B[PurchaseOrder]}` (often `"{B[…]}{ENTER}"` to type-and-commit). Read+write can mix in one string: `"Delivery {B[Delivery]} saved, material document {XB[MaterialDoc]} created"`. Buffers written inside a reusable block are readable by later case-level steps and later blocks — buffer scope is the executing test case, crossing block boundaries. `{XB}` is the mechanism for values **embedded in surrounding literal text** (status-bar messages); to capture a whole field's content, use a plain `actionMode: "Buffer"` step instead (buffer name in `value`, `actionProperty: ""`). |
| Date/time expressions | `{DATE[][][dd.MM.yyyy]}` = today formatted (first two bracket groups are offset/unit — leave empty for "now"); also `{DATE[][][yyyy]}`; `{DATETIME}` for timestamps in file names. `{DATE[][][dd.MM.yyyy]}` is the standard value for SAP date fields. |
| Buffer inside a Row `explicitName` | Requires the `$` prefix: `"explicitName": "${B[RowNum]}"` — plain `{B[…]}` works only in `value` fields. Capture the index first with a `<Row>` subValue: `actionMode: "Buffer"`, `actionProperty: "RowNumber"`, `explicitName: "$lastContentRow"`, and the buffer name in `value` (e.g. `"value": "RowNum"`). Other `$` row selectors: `$1`, `$<n>`, `$last`, `$header`, `$firstEmptyRow`. |
| `actionProperty` values | `""` plain action (or, with `actionMode: "Buffer"`, capture full field content); `"Visible"` presence check (observed with value `"True"`); `"Exists"` with `"True"` or `"False"` (`Exists`+`"False"` detects absent/collapsed state — the If-condition idiom inside `ControlFlowItemV2`); `"InnerText"` (Html); `"RowNumber"` (Buffer a table row's index). |
| `InnerText` exact-match | TOSCA's `InnerText` TechnicalId matches the full element `innerText` exactly, including text of nested children. A card link wrapping an `<h2>` will have `innerText="<caption>\n<heading>"` and will not match a short caption. Drop `InnerText`; use Tag + HREF + ClassName or a `Title` attribute. Wildcards **are** supported in the value (`InnerText: "*phrase*"`, `"*@*.*"`) |
| **SPA input reports `[Succeeded]` but nothing was typed — check `UserSimulation` before blaming hydration** | The step passes and the field still holds its **prior/default** value: `Actual "1"` on a quantity input whose default is `1`; `Actual "sec-sender-a ng-scope invalid\|0\|0"` on a login form whose two fields are both length 0. Cause is a `UserSimulation=True` Steering param — it emits real keystrokes **at whatever currently holds focus**, not into the element TOSCA resolved, so when focus is elsewhere the field is never touched. It is **not** a scanner default: you only have it if you added it, and the usual reason for adding it ("this AngularJS field needs real keystrokes") is wrong. **Fix: remove `UserSimulation`, keep `FireEvent=change`** — TOSCA then sets the value on the resolved element and fires the event; confirm on the live page first that a native setter + `input` event updates the framework model. **Read the guard's `Actual` before theorising**: untouched default = never typed (this row); `""` = cleared but not filled; an appended value (`"41"` where you typed `4` into a field holding `1`) = the app appends instead of replacing. Establish on the live page which of those the app does, and the `Actual` then identifies the cause on its own. **Guard every `Input` into an SPA form field with a `Verify` of the same value** — without it every symptom is downstream and misleading: `Could not find Link 'Sign Out'` (login form empty), `Could not find Button 'CHECKOUT'` (cart never filled), cart badge `""` (ADD TO CART fired with an empty quantity), ~50 % flakiness depending on where focus landed. **A settle does not fix this** — a 2 s settle was in place throughout and the run stayed ~50 % flaky. Validated on AOS 2026-07-22. |
| Heading tags (`H1`–`H6`) don't resolve as controls | `Tag: H2` + `InnerText` returns `Could not find Container '…'` even when the element is visible, in-viewport, and its `innerText` is provably byte-exact (verified via a `Verify JavaScript Result` probe returning the literal text) — **exact and wildcard InnerText both fail**. The Html scanner does not expose heading elements. **Fix: target the nested/adjacent `SPAN` or `DIV` instead** — e.g. for `<div id="orderPaymentSuccess"><h2><span>Thank you…</span></h2></div>` use `Tag: SPAN` + `InnerText: "*Thank you…*"`, or `Tag: DIV` + `Id`. Validated on AOS 2026-07-22: identical locator failed on `H2`, passed immediately on `SPAN`. Note this is a **distinct** cause from the viewport-scoping row — check the tag first, it's the cheaper fix, and an `<h2>` is the only element that row's theory rests on. |
| `Name` TechnicalId works on `INPUT`, not on `BUTTON` | `Tag: INPUT` + `Name: quantity` resolves fine, but `Tag: BUTTON` + `Name: save_to_cart` fails with `Could not find Button '…'` on the same page in the same run. For buttons use `Id`, or `InnerText` (which is confirmed working on `BUTTON` — `Tag: BUTTON` + `InnerText: "BUY NOW"` resolves). |
| `{` anywhere in a JavaScript step value is fatal | Not just `"` at the value root — a `{` **anywhere** in an `Execute`/`Verify JavaScript Result` value raises `Expression provided in test step item "JavaScript" could not be parsed … Token is not valid in this context: {`. That rules out `for(){}`, `if(){}`, function bodies and object literals. **Write brace-free JS**: arrow functions with expression bodies (`arr.map(e=>e.id).join(',')`), ternaries instead of `if`, and `String.fromCharCode(10)` instead of a `\n` escape. |
| Smuggling diagnostics out of a personal-agent run | A `Verify` failure message includes the **actual** value, and `GetFailedTestSteps` returns that message — so a `Verify JavaScript Result` step whose expected value is the **success signature** is a free diagnostic: it passes silently when the app is healthy and prints the real page state when it isn't. Example: JS returns `btn.className+'|'+u.value.length+'|'+p.value.length`, expected `"sec-sender-a ng-scope|13|10"`. This is how the AOS login race was root-caused without any human log access. Prefer this over an always-failing probe, which aborts the run. |
| Parent `visibility:hidden` propagates | Closed mega-menus hide children via parent styling; TOSCA's default `IgnoreInvisibleHtmlElements=True` filters them out. Open the parent before looking up the child, or set `IgnoreInvisibleHtmlElements=False` as a Steering module param |
| Html "The Browser could not be found" | Tricentis Chrome extension not attached to the agent's Chrome. Fix on the agent (install/enable extension), **not** in the test case |
| `ControlFlowItemV2` for optional elements | Works cleanly when the module-level selector (`Title`/`Url`) can produce a clean no-match. Verify steps inside the condition evaluate `false` on hidden elements; they hard-fail when the document itself can't be found. Narrow the module-level selector before relying on `If` |
| Test case PUT requires `id` in body | The full PUT body must include `"id": "<caseId>"` — API rejects bodies without it |
| New case not in inventory immediately | After `cases create`, wait 3–10 s before searching — CLI retries automatically |
| Placing a case after create/clone | Always run `inventory move testCase <newId> --folder-id <folderId>` — creation alone doesn't place it |
| Finding a folder's entity ID | Use `inventory folder-tree --folder-ids "<parentId>"` or read the UUID from the portal URL |
| `inventory search --folder-id` | Filters client-side by matching the `folderKey` suffix — pass `--folder-ids` with parent IDs |
| `modules update` returns `{}` | A 200/204 with empty body is normal — verify with `modules get <id> --json` afterwards |
| Block params need `id` | Every `businessParameters` entry needs a ULID `id` — always use `blocks add-param` which generates one |
| `referencedParameterId` | Each parameter value entry must match a `businessParameter.id` from the block — get IDs via `blocks get <blockId> --json` |
| `{CP[ParamName]}` syntax | Reference test config params in step values: `{CP[Username]}`, `{CP[Password]}` |
| ProcessOperations `subValues` | The `Arguments` step uses `actionMode: "Select"` with each CLI arg as a separate item in `subValues[]` — multiple args in one `value` string won't work |
| Standard modules invisible in `inventory search` | Intentional. Discover via `GET /_mbt/api/v2/builder/packages` + `packages/{pkg}/modules/{moduleId}`. Top-level module GUIDs appear stable; attribute GUIDs are NOT confirmed stable — re-discover per tenant. See [standard-modules.md](references/standard-modules.md) |
| `{SCRIPT[...]}` / `{XP[...]}` dynamic-value expansion | Not registered on Tosca Cloud. To run JS from a test step, use the `Execute JavaScript` / `Verify JavaScript Result` Standard modules — see [standard-modules.md](references/standard-modules.md) |
| Html scanner blind to body content (not iframe / not shadow DOM / not CSS-hidden) | Module Steering flags won't fix it. Pivot to `Verify JavaScript Result` (CDP-based, bypasses the scanner). Full diagnostic playbook + anti-patterns in [standard-modules.md](references/standard-modules.md) |

## ULID generation

The CLI's `_generate_ulid()` creates Crockford base32 ULIDs. Generate a **fresh** ULID for:
- Each `businessParameter.id` added to a block
- Each parameter entry `id` in a test case's block reference (`parameters[].id`)
- Each block reference's own `id` (the `TestStepFolderReferenceV2.id`)

Do **NOT** generate a fresh ULID for `parameterLayerId` — it belongs to the block (copy it verbatim from `blocks get --json <blockId>` or any existing reference; mint it only once, the first time a block is ever parameterized). ID conventions observed in production artifacts: module/case/block root `id` = UUID; every attribute, parameter, and attachment `id` = 26-char Crockford ULID.

## Step JSON discriminator

Items use `$type`:
- `TestStepFolderV2` — inline folder, children in `items[]`
- `TestStepFolderReferenceV2` — block reference, ID in `reusableTestStepBlockId`
- `TestStepV2` — atomic step
- `ControlFlowItemV2` — If/Then conditional

## Iterative test-development loop (Local Runner + MCP)

Use this loop when developing a new test case end-to-end on the developer's own machine — fastest feedback because no shared queueing, and the developer can watch the browser drive itself.

**One-time prerequisites on the developer machine**
1. Install **Tosca Local Runner / Cloud Agent** — registers a *private* personal agent under the developer's Okta identity (visible only to MCP, not to the CLI service token).
2. Install + enable the **Tricentis Automation Extension** in Chrome and/or Edge.
3. Keep the target browser window **maximized** before each run (minimized → coordinate-out-of-bounds, missed clicks).

**The loop**
1. **Explore** the target site with Playwright MCP (`browser_navigate` → `browser_snapshot` → identify Tag/InnerText/HREF/ClassName; verify locator uniqueness with `browser_evaluate`).
2. **Build / update** modules and the test case via the CLI (service token is fine for build operations).
3. **Trigger** via MCP — NOT the CLI: `mcp__ToscaCloudMcpServer__RunPlaylist(playlistId, runOnAPersonalAgent=true)`. The CLI's service token is 403'd on personal agents.
4. **Wait** via MCP: `GetRecentRuns({nameFilter: "<debug playlist name>"})` — with a dedicated debug playlist (below) the single returned id **is** your executionId. **Poll every 5–10 s, not every 60–120 s.** Typical single-case runs finish in 15–40 s (a 46-step, two-purchase web flow ≈ 45–90 s); a 90 s sleep burns a full prompt-cache window (TTL ≈ 300 s). Never chain `sleep N && curl` in a retry loop — use the harness `run_in_background` + `Monitor` pattern.
5. **Inspect failures** via MCP: `mcp__ToscaCloudMcpServer__GetFailedTestSteps({runIds:[<executionId>]})` — returns the per-step failure tree with the engine's exact message + stack trace.
6. **Fix** the failing module/step/RTSB via the CLI, then back to step 3.

**Do not** pin `AgentIdentifier` on the playlist — `runOnAPersonalAgent: true` is the entire routing instruction, and the playlist stays generic for grid runs too.

### Getting the executionId of a personal-agent run (no human, no token hacking)

`GetFailedTestSteps({runIds:[…]})` needs the **executionId**, not the `playlistRun.id` that `RunPlaylist` returns — and there is no API that maps one to the other under the service token (personal runs are `private` and excluded from `playlistRuns` entirely; `playlists status/logs` → 403). `GetRecentRuns` is capped at ~10 ids sorted **ascending by UUID string**, so a new run whose UUID starts with a high hex digit is permanently invisible in a busy playlist.

**Fix — one dedicated debug playlist per session.** `nameFilter` scopes to the *playlist* name, so a playlist with a single run returns a single id:

```bash
# once per debug session — ASCII-only name (no em-dash: nameFilter must match byte-exact)
python tools/toscacloud-cli/tosca_cli.py playlists create --json -n "AOS Order Purchase debug 20260722a" -m sequential
python tools/toscacloud-cli/tosca_cli.py playlists attach-case <playlistId> <caseEntityId>
```

```
GetRecentRuns({nameFilter: "AOS Order Purchase debug 20260722a"})   -> []                    # baseline, before the run
RunPlaylist(<playlistId>, runOnAPersonalAgent=true)
GetRecentRuns({nameFilter: "AOS Order Purchase debug 20260722a"})   -> ["<executionId>"]      # exactly one
GetFailedTestSteps({runIds: ["<executionId>"]})                     -> per-step failure tree
```

Validated end-to-end on 2026-07-22. **Always take the `[]` baseline before dispatching** — it proves the id you read afterwards belongs to your run. Re-use the same debug playlist across iterations of one session (ids accumulate but stay far under the cap; the newest is the one absent from your previous poll); start a fresh one per session/day.

`GetFailedTestSteps` returns an empty `failedTestSteps` array for a passing run — that, not `GetRecentRunLogs`, is the reliable green signal. `GetRecentRunLogs(playlistId)` returns `["No succeeded runs found."]` and does **not** surface failed-run logs, so it cannot substitute.

For **shared/team-agent** runs none of this applies — the CLI sees them directly: `playlists logs <runId>` returns the full TBox transcript.

### Searching and deleting runs — a run lives in THREE stores

Deleting a run is not one call. The same run is represented three times, and **only the third is what the Portal's Runs page renders**:

| Surface | Holds | Effect of deleting |
|---|---|---|
| `/_playlists/api/v2/playlistRuns/{id}` | playlist-side record, **the only place `executionId` appears** | invisible in the UI; also destroys the `playlistRun → executionId` mapping |
| `/_e2g/api/executions/{id}` | the execution + its attachments (logs, `Recording.mp4`, TestSteps) | removes the artifacts, **not** the listing |
| **`/_playlists/api/v2/runInfo/{id}`** | **what the Portal Runs page renders** | **this is the one that clears the UI** |

**Order matters.** If you need executionIds (to fetch logs first), collect them *before* deleting `playlistRuns` — that delete removes the mapping and there is no other way back to it. To clear the UI, `runInfo` is sufficient and is what the Portal itself calls.

**Enumeration.** `GET /_playlists/api/v2/runInfo` silently returns only **10** items no matter what `total` says, and `?top=` is rejected (`Field 'top' is not supported`). Use the search POST — this is the Portal's own body shape:

```jsonc
POST /_playlists/api/v2/runInfo/search
{"filter":{"searchTerm":null,"items":[],"linkOperator":"or"},
 "sort":[{"field":"createdAt","direction":1}],
 "pageToken":null,"itemsPerPage":50,"includeFields":null,"excludeFields":null}
```
Page with the returned `pageToken`. Items carry `id`, `name` (the playlist name), `state`, `personal`, `createdAt`. `POST /_e2g/api/executions/search` with `{}` is the equivalent for the execution store (`GET` there is 405).

**Auth.** All three DELETEs and both searches require the **user** token (`~/.mcp-auth/`, see above). The service account is 403 on every one, and `tosca_cli.py playlists delete-run` therefore fails on personal runs — and even when it works it targets `playlistRuns`, the surface that does *not* change what you see.

**Verify on the surface the user sees.** A confirm-GET on the endpoint you just called returning 404 proves only that *that* store changed. After a cleanup, re-run the `runInfo` search and count what remains, then have the user refresh the Portal.

Keep succeeded runs when clearing failures — with `uploadRecordingsOnSuccess` enabled on the playlist they retain their recordings, which is the reference to diff a future failure against.

### Full agent log for a personal-agent run (the MCP user token)

`GetFailedTestSteps` returns only the failed leaves. For the **complete TBox transcript** — every `[Succeeded]`/`[Failed]` line, durations, expected-vs-actual — reuse the OAuth user token that `mcp-remote` caches on disk. It reaches every endpoint the service token is 403 on:

```python
key  = hashlib.md5(MCP_URL.encode()).hexdigest()          # MCP_URL exactly as in .mcp.json
tok  = json.load(open(glob.glob(os.path.expanduser(
           f'~/.mcp-auth/mcp-remote-*/{key}_tokens.json'))[0]))['access_token']
H    = {'Authorization': f'Bearer {tok}'}
run  = GET f'{B}/_playlists/api/v2/playlistRuns' params={'playlistId': pid, 'sort':'desc(createdAt)'} -> items[0]
eid  = GET f'{B}/_playlists/api/v2/playlistRuns/{run["id"]}' -> ['executionId']   # only place it appears
unit = GET f'{B}/_e2g/api/executions/{eid}' -> items[0]
att  = GET f'{B}/_e2g/api/executions/{eid}/units/{unit["id"]}/attachments'
text = GET att['logs']['contentDownloadUri']        # SAS is the auth — send NO Authorization header
```

**Use the bundled script — do not re-derive this:** [`scripts/tosca_run_artifacts.py`](scripts/tosca_run_artifacts.py)

```bash
python .claude/skills/toscacloud-cli/scripts/tosca_run_artifacts.py log    <playlistId>
python .claude/skills/toscacloud-cli/scripts/tosca_run_artifacts.py fetch  <playlistId>   # all attachments
python .claude/skills/toscacloud-cli/scripts/tosca_run_artifacts.py frames <playlistId> --step "ADD TO CART" --after 3
```

### Don't stop at logs.txt — the run also ships a screen recording

The same attachments endpoint serves **`Recording.mp4`**, `TestSteps.json`, `TBoxResults.tas` and `JUnit.xml`, not just `logs.txt`. The recording is the fastest way to answer "what was actually on screen", and the log cannot answer it: the log says `Could not find Button 'CHECKOUT'`, the recording shows *"Your shopping cart is empty"* — i.e. the real defect was six steps earlier.

`frames` automates the alignment: it parses the log for `Screen recorder: Recording` (video **t0**) and for every `[Succeeded]`/`[Failed]` step timestamp, then cuts PNGs at the matching video offsets and prints the step timeline. With no `--step`/`--at` it defaults to every failed step plus 2 s after. **Read the PNGs directly** — one frame routinely replaces several debug runs.

Requires ffmpeg; falls back to `pip install imageio-ffmpeg`'s bundled binary automatically. Not every agent/config records — if `Recording` is absent from the attachment map the script says so.

Gotchas: the list endpoint's sort syntax is strictly `desc(field)`/`asc(field)` (everything else 400s); supported filter fields are `playlistId, state, createdBy, sort, pageToken` only; list items do **not** carry `executionId`, so the single-run GET is mandatory. The cached token lives **3600 s and has no refresh_token** — when it expires, ask the user to run `/mcp reload`.

> **Do not retry the `offline_access` fix — it was tested and rejected (2026-07-22).** Adding `offline_access` to `--static-oauth-client-metadata` in `.mcp.json` looks like it should yield a refresh_token, and the Okta AS does advertise `offline_access` in `scopes_supported`. But the `MCPServer` client app is not *granted* that scope, so the authorize request fails with `No authorization code received` and the MCP server won't reconnect until you revert. Unlocking it requires an Okta admin to grant the scope to the app — not a config change. Two further traps if anyone re-tests: (1) `mcp-remote` keys its cache on `md5(server url)`, so with a still-valid token it silently reuses the cache and never sends the new scope — you must move `~/.mcp-auth/mcp-remote-*/<hash>_*` aside to force a handshake; (2) back up both `.mcp.json` and that cache first, because a failed flow leaves the MCP server disconnected.
>
> **For unattended/CI runs, use the shared team agent instead** — `tosca_cli.py playlists logs <runId>` works there under the service token with no user-token juggling at all. The user-token path is for interactive personal-agent debugging, where a 1-hour window is not a real constraint.

For shared/team-agent runs (CI, scheduled jobs, parameter-overridden runs), use the CLI's `playlists run` and `playlists logs` — those work fine under the service-account token.

## Detailed how-to guides

- Read [Web Automation (Html engine)](references/web-automation.md) when creating or updating Html engine modules, building web test cases, or using Playwright to discover element locators and class names.
- Read [SAP GUI Automation (SapEngine)](references/sap-automation.md) when creating or updating SAP GUI modules, assembling SAP test cases, or working with T-codes, RelativeId locators, or the Precondition reusable block.
- Read [Reusable Blocks](references/blocks.md) when working with reusable test step blocks — extending block parameters, wiring block references into test cases, or debugging `parameterLayerId` / `referencedParameterId` issues.
- Read [Standard Modules & Execute/Verify JavaScript](references/standard-modules.md) when you need to: run JavaScript in the browser, read cookies / storage / computed styles, work around a scanner that's blind to body content, or use any out-of-the-box platform module (HTTP, DB, file, email, clipboard, timing, T-code). Includes the `/packages` discovery endpoint recipe and the full Html-package GUID table.
- Read [PDF Verification Modules (Pdf engine)](references/pdf-modules.md) when verifying PDF content produced by the flow under test (SAP print-to-PDF receipts, reports) — module anatomy (`PdfDocument`/`NonGui`/`Engine: Pdf`), Page-container and text-anchor locator archetypes, and the SAP print-preview → UIA Save-As dialog → `{B[FileName]}` verify loop.
- Read `tosca-platform-guide` → `references/test-patterns.md` when planning a test case's step structure: proven shapes for both platforms (skeleton + recovery, buffer chaining, data preparation, Constraint row selection, API request/response, DB check, optional-element If, block with business parameters, WaitOn, data-driven options, module parameter kinds).
- Read [Best Practices (condensed KB summary)](references/best-practices.md) before finalizing module identification choices, TestCase structure, or TestStep action modes — it compresses the 10 official Tricentis Best Practices articles into a single checklist.
- Read [Field notes](references/field-notes.md) for operating constraints, gap-fill / assemble-from-parts procedures, E2G log recipe, personal-agent identity and dispatch, MCP polling semantics, the MCP-vs-CLI capability split, undocumented APIs, and the self-improvement protocol (fix the CLI + update the skill when you find new API behavior).
