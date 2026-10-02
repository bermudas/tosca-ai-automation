# Reuse scan: find existing objects before building

Existing test cases, modules and reusable blocks are the best templates you have. They already carry the team's conventions, working locators, block wiring and test data patterns. Run this scan **before** exploring or building anything, and end with an explicit decision.

## 1. What to look for

| Look for | Why |
|----------|-----|
| **Similar test cases** (same app, transaction or flow; same folder) | Template for structure, step order, buffers, test configuration, naming. Their steps also tell you which modules the team uses for each screen (§1b) |
| **Modules for the screens/pages in the scenario** | Reuse them as they are. Scanned modules carry self-healing data and proven locators. |
| **Reusable blocks / TestStepBlocks** (login, precondition, navigation, postcondition) | Wire them in instead of rebuilding |
| **Test data** (Cloud data sets, Commander TestSheets / TCPs) | Parameterize the same way |
| **Recent runs of similar cases** | Tell you which modules actually work today (a module in a red run may be stale) |

## 1b. Finding modules for a screen when the names don't match

The user describes the functionality ("submit a pick-up order"); modules are named after pages ("Shop | Review order | Summary"). Search in this order and stop when a screen is covered:

1. **Through similar test cases.** A case for the same area lists every module it uses. Read its steps (Commander: step → `Module`; Cloud: `cases steps <id> --json` → `moduleReference.id`) and collect the modules per screen. This is the fastest route and gives you the team's own step shapes for free.
2. **By page identity, not by name.** A module's root parameters say which page it drives: Html `Title` / `Url`, SAP `Transaction` / `ProgramName` / `ScreenNumber`, API `Resource`. Search those values with URL path segments, page titles, T-codes.
   - TCShell / TCAPI: `=>SUBPARTS:XModule[Name=i?"order"]`, and by locator `=>SUBPARTS[TechnicalId=?"orders"]` ([commander-object-model.md](commander-object-model.md) §14).
   - Commander MCP: walk `Modules/<App>/…` and read the module's parameters with `get_attributes`.
   - Cloud: `inventory search "<keyword>" --type Module --json`, then `modules get --json <id>` and check the root `Title` / `Url` and the attribute names.
3. **By keyword variants.** Try: the application name and acronym, the page title, the URL path, the transaction code, the business object (Order, Customer, Invoice), UI labels the user mentioned, and the team's naming pattern from `.agents/project.md`. Module folders usually mirror the application (`Modules/<App>/<Area>/`).
4. **Known modules in project memory.** `.agents/apps/<app>.md` lists pages, their modules and quirks from earlier work.
5. **Shared pieces.** Login, navigation, cookie banner, spinner, popups and the Precondition / Postcondition blocks almost always exist already: look in the Library / shared folders before anything else.
6. **Standard modules** for browser, waits, buffers, files, DB: never rebuild those (Commander Standard subset; Cloud `/builder/packages`).

For every screen in the scenario, record the result: **module found (id, folder)**, **partially covered** (which controls are missing), or **no module**. Only the last two go to live exploration, and the explorer gets the existing modules so it verifies them instead of rediscovering them.

### Can I trust the module I found?

| Check | How | If it fails |
|---|---|---|
| Is it a scan, not a hand-made stub? | Scanned modules carry a screenshot attachment and `SelfHealingData` steering params; their attributes have full TechnicalIds | A stub with 1–2 attributes and no locators: treat as "no module" |
| Is it current? | Modified date vs the app's last release; the module appears in a **recent green run** of a similar case | Verify its locators live before reuse (explorer) |
| Is it approved? | Folder stage (`Approved` > `Ready for Review` > `In Work`), WorkState | Another user's `In Work` object: ask before building on it |
| Does it cover my controls? | Compare the attribute list with the controls the scenario touches | Partially covered: reuse it and ask whether to extend it (rescan / add attributes), don't create a duplicate module for the same page |
| Who else uses it? | Commander: `=>SUBPARTS:Module[Name=="…"]=>AllReferences=>SUPERPART:TestCase` or the module's `TestSteps` back-link; Cloud: search cases in the same folder and read their steps | Shared module: change it only after checking every user |

## 2. How: per platform

### Commander, open (Commander MCP)

The Commander MCP has **no search**: TQL is not supported through MCP. Walk the tree instead:

1. `get_workspace_info` → then `get_object_info(<top folder>, include_parent_and_children=true)`, paging with `offset` (`commander-mcp` → `inspect-workspace.md`).
2. Walk the likely folders first: `Modules` (by application / transaction), `TestCases` (by area), the Library / TestCase-Design folders holding reusable blocks. Use the folder names the user gives you. Don't crawl the whole workspace blindly on big projects.
3. For each candidate: `get_attributes` (in small batches) to read steps, values, action modes and module references (`explain-test-case.md`).

### Commander, closed or headless (TCShell / TCAPI)

TQL search **is** available here (`cli-api-commander` → `tcapi.md`, `workspace-checkout.md`):

```powershell
$project.Search('=>SUBPARTS:TestCase[Name=~"(?i)order"]')
$project.Search('=>SUBPARTS:XModule[Name=~"(?i)VA01"]')
```

Full TQL syntax (operators, `->`, SUPERPART, set operations, more examples): [commander-object-model.md](commander-object-model.md) §14.

A single-user workspace that Commander has open is locked for headless access. Use the MCP tree walk then, or ask the user to close Commander.

### Cloud

1. **toscactl** (official): `tosca-find` / `tosca-cloud-basics` to search by name, artifact type and folder.
2. **tosca_cli.py** (JSON ground truth): `inventory search "<kw>" --type TestCase|Module --json`, `inventory search "" --type TestCase --folder-id <id>` for a whole folder, then `cases steps <id> --json` and `modules get --json <id>`. Built-in standard modules come from `/builder/packages`, not Inventory (`toscacloud-cli` → `standard-modules.md`).
3. **Tosca Cloud MCP**: `SearchArtifacts`, `AnalyzeTestCaseItems`, `GetModulesSummary` (read-only).

## 3. Cross-platform reference (Commander ↔ Cloud)

If the target platform has nothing similar, **and the other platform is configured and the user allows it**, look there too. Teams migrating between Commander and Cloud often have the same flows on both sides.

- Same **engines** and the same **locator vocabulary**: Html TechnicalIds (`Tag`, `Id`, `Name`, `InnerText`, `HREF`, `ClassName`, `Title`), SapEngine `RelativeId` plus window identity (transaction / program / screen). A locator proven on one platform is a very strong candidate on the other.
- Same **test-design vocabulary**: folders, action modes (Input / Verify / Buffer / WaitOn …), value expressions (`{CLICK}`, `{B[..]}`, `{CP[..]}`), reusable blocks with business parameters.
- **Different mechanics**: Commander = objects plus tasks and attributes (MCP / TCShell / TCAPI). Cloud = JSON documents over REST with ULIDs. **Translate, don't copy**: read the source, then rebuild with the target platform's own tools. Use `commander-vs-cloud.md` for the object mapping.
- Treat locators taken from the other platform as **hypotheses**. Re-verify them live (`web-exploration` / `sap-gui-exploration`) before relying on them: the application version or environment may differ.
- **Offline reference via subsets**: a `.tsu` export from either platform can be read with the `tosca-tsu` skill (same schema on both sides) to inspect or diff test cases and module locators without API access.
- **Bulk moves**: both sides deal in Tosca subsets (`.tsu`; Cloud: `tosca_cli.py` TSU export/import). Moving content by subset may work, depending on versions. Try it with a single test case first and inspect the result before moving more. Otherwise, rebuild by translating.

## 4. Decide, and say so

End the scan with a short reuse inventory and one decision per scenario:

```markdown
Reuse scan — "Create sales order VA01" (Commander)
- Similar cases: /TestCases/SD/Orders/VA01 Standard order (3 steps short of the scenario)
- Modules: VA01 Initial Screen ✓, VA01 Overview ✓, Save popup ✗ (missing)
- Blocks: SAP Logon (Library) ✓
- Cross-platform: Cloud case "VA01 – Standard order" has a Save-popup module (SAPLSPO2/101) → locator hypothesis
Decision: REPLICATE + EXTEND — copy the existing case, add the Save-popup module (explore to confirm), reuse the logon block.
```

| Decision | When |
|----------|------|
| **Reuse as is** | An existing case already covers the scenario. Run it, don't duplicate it. |
| **Replicate** | A similar case exists and only the data or small variations differ: copy it and change values (Commander: copy/`execute_drop_task`; Cloud: `cases clone`, or build from its JSON with fresh item IDs). |
| **Extend** | Most modules or blocks exist. Build the case from them and explore or scan only the missing screens. |
| **New** | Nothing relevant exists on either platform. Explore fully, then build. |

Only after this does exploration start, and then only for what's **missing or unverified**.
