# Build guide: creating and fixing test cases and modules (Commander and Cloud)

Use this file when you **build or fix** a Tosca test case, block or module, on Commander (on-prem / Server) or on Cloud, with whatever runtime you have. It tells you which call does what on each runtime, and which rules make the result correct. What a finished module, test case and block look like: [object-anatomy.md](object-anatomy.md). Step shapes are in [test-patterns.md](test-patterns.md) (P1–P12). Object detail is in [commander-object-model.md](commander-object-model.md) and in `toscacloud-cli` → `references/web-automation.md`, `sap-automation.md` and `blocks.md`. How to find existing objects: [reuse-scan.md](reuse-scan.md).

Cell legend used in this file: `—` means the runtime can't do it. `?` means nothing in the repo documents it, so check it on a scratch object before you rely on it. `(u)` means the repo names the call but marks it unverified.

## 1. How to use

1. **Reuse scan** ([reuse-scan.md](reuse-scan.md)). End it with a decision: reuse / replicate / extend / new. Never invent IDs.
2. **Pick the patterns** for each scenario step ([test-patterns.md](test-patterns.md)). If the team already has a case or block that does the same thing, follow it instead (`.agents/project.md`).
3. **Write a build plan** before the first write. State the **tier** you're on and why (for example: "Commander closed → TCAPI"; "toscactl can't author steps → `tosca_cli.py`").

   | # | Object | Pattern | Runtime call (§3) | Verify (§5) |
   |---|--------|---------|-------------------|-------------|
   | 1 | Module `App \| Login` | P9 | reuse `<id>` | `modules get --json` / `get_attributes` |
   | 2 | TestCase `App - Log in` | P1 | `create_test_case` / `cases create` + `cases update` | re-read the tree |

4. **Build one artifact → re-read it → run it → fix it → re-run it.** Only then start the next artifact (§4 G-process).
5. **Persist** (Commander `save`, then check-in after the user confirms). Report the IDs, where each object was placed, the tier you used, and any gaps.

## 2. Object model for builders

| Object | Commander (class → key fields) | Cloud JSON (`$type` / field) | Required relationships |
|--------|--------------------------------|------------------------------|------------------------|
| Folder | `TCFolder` (`Items`, `ContentPolicy`, TCPs) | Inventory folder (`entityId`); placement via `inventory move` | Folder type limits what it can contain. On Cloud, creating a case doesn't place it in a folder: always move it |
| Test case | `TestCase` (`TestCaseWorkState` PLANNED / IN_WORK / COMPLETED) | case root: `id`, `name`, `workState` (Planned / InWork / Completed), `testCaseItems[]`, `testConfigurationParameters[]`, `recoveryScenarioCollection` | PUT body needs `id` and must not contain `version`. Cloud MBT id = Inventory `entityId` |
| Step folder | `TestStepFolder` (`Condition`, `Repetition`) | `TestStepFolderV2` {`items[]`, `id`, `name`, `disabled`} | Folders nest. Steps may also sit directly under the case (the tsu evidence shows this) |
| Test step | `XTestStep` → **`Module`** (exactly 1); `Condition`, `Repetition`, disabled flag | `TestStepV2` → **`moduleReference`** {`id`, `packageReference`? (Standard only), `metadata.engine`}; `reorderAllowed`, `testStepValues[]` | One step uses exactly one module |
| Step value | `XTestStepValue` → **`ModuleAttribute`** (exactly 1); `Value`, `ActionMode`, `ActionProperty`, `Operator`, `DataType`, `ExplicitName`, `Condition`; children in `SubValues` | `testStepValues[]` entry: `value`, `actionMode`, `actionProperty`, `operator`, `dataType`, `explicitName`, `moduleAttributeReference` {`id`, `moduleId`, `metadata` copied from the attribute}; children in `subValues[]` | A value targets one attribute **of the step's own module**. A child value targets a **child attribute of its parent value's attribute**. Store only the values you need |
| Placeholder value | `<Row>` / `<Col>` / `<Cell>` / `<Buffername>` attribute + `ExplicitName` | same attribute + `explicitName`. A buffer in a row name needs the `$` prefix: `${B[RowNum]}` | Every `<Row>` in a step shares one attribute id and differs only by `explicitName` |
| Reusable block | `TestStepLibrary` → `ReuseableTestStepBlock` → `ParameterLayer` ("Business Parameters") → `Parameter{Name}` | `reuseableTestStepBlocks/{id}`: `businessParameters[]` {ULID `id`, `name`, `valueRange`}, root `parameterLayerId` | One library per folder. Parameter names contain no dots. Inside the block, use `{PL[Name]}` |
| Block call | `TestStepFolderReference` → `ReusedItem`; `ParameterLayerReference` → `ParameterReference{Value}` → `Parameter` | `TestStepFolderReferenceV2` {`reusableTestStepBlockId`, `parameterLayerId` (the block's, copied verbatim; omit it when `parameters` is empty), `parameters[]` {fresh `id`, `name` byte-for-byte, `referencedParameterId`, `value`, `parameters: []`}} | Set only the parameters this call needs. On Cloud, a wrong `parameterLayerId` means every value is silently ignored |
| If / loop | `TestCaseControlFlowItem` {`StatementType` 1=If, 2=loop; `MaximumRepetitions`} → `TestCaseControlFlowFolder` (0 Condition, 1 Then/Loop, 2 Else) | `ControlFlowItemV2` {`statementTypeV2: "If"`, `condition` {items}, `conditionPassed` {items}}. No `conditionFailed` has been observed. Loop JSON: ? | Tools read the folder **type**, not its name (the name is free text). Loops always get `MaximumRepetitions` |
| Recovery / CleanUp | `OwnedRecoveryScenarioCollection` → `RecoveryScenario{ScenarioType 0 = Recovery, 1 = CleanUp (inferred), RetryLevel}` → steps | `recoveryScenarioCollection` {`name: "*** Recovery Scenarios ***"`, `scenarios[]` {`type: "CleanUp"`, `retryLevel`, `items[]`}} | These fire only in ExecutionList / playlist runs, not in the ScratchBook |
| TCP | TCP on the project / folder / case / ExecutionList; read with `{CP[x]}` | `testConfigurationParameters[]` {`name`, `value`, `dataType`}. A Password entry has `password.id` and no `value` | Define TCPs as high in the tree as you can. Secrets use the Password type only |
| Module | `XModule` (`Engine` Configuration param; root TechnicalIds `Title` / `Url`, SAP transaction / program / screen) → `XModuleAttribute` tree → `XParam` (TechnicalId / Steering / Configuration) | module root: `businessType`, `interfaceType`, `parameters[]` (`Engine` **required**), `attributes[]` (each with `Engine` + `BusinessAssociation` Configuration params), `metadata` | Root identifies the page / window. An attribute identifies one control. Module-level `Url` / `Title` must be `TechnicalId`, not `Configuration` |
| API module | `ApiModule` (API Scan; `create_api_module`) | API message (`tosca_builder_*ApiMessage`) | Request values use Insert. Response values use Verify / Buffer |
| TestSheet / template | `TestSheet` → `TDAttribute` / `TDInstance`; template `TestCase` + `TestCaseTemplateDetail` → `TemplateInstance` | Same classes appear in a Cloud `.tsu`. **No Cloud authoring tooling in this repo** | `{XL[..]}` is valid only in templates. Edit the template, never the generated instances |
| Execution grouping | `ExecutionList` → `ExecutionEntry` → `TestCase` | Playlist → items `InputTestCaseV1` {`sourceId`} / `InputFolderV1` | Put only COMPLETED cases into ExecutionLists |

Invariants to check on every write:

- Nested values mirror the attribute tree. A container value usually has `{NULL}` (Commander) or no `value` key (Cloud pure-navigation Select).
- Each module attribute runs top to bottom in module order within one step. Use `0-N` / `ZeroToN` cardinality to use the same attribute twice.
- `{PL[..]}` only inside a block, as the whole value (Input / Insert) or embedded in a Verify string. `{XL[..]}` only in templates. `{XB[..]}` only inside a Verify value.
- `[Buffer]` takes the buffer **name** as its value. Buffers live for one test case and cross block boundaries.
- Cloud IDs: root `id` is a UUID. Every attribute, parameter, value and item `id` is a fresh ULID. Copy `parameterLayerId` and `referencedParameterId` verbatim.

## 3. Build matrix

### 3.1 Commander (on-prem / Server)

| Operation | Commander MCP (26.1+, Commander open) | TCShell (headless) | TCAPI (PowerShell / .csx) | Tosca REST (`/rest/toscacommander/{ws}`) |
|-----------|----------------------------------------|--------------------|---------------------------|------------------------------------------|
| Find / reuse candidate | Tree walk: `get_object_info(include_parent_and_children=true, offset)` + `get_attributes`. **No TQL** | `JumpTo "<TQL>"`, `For "<TQL>" CallOnEach \| TaskOnEach \| MarkAll` (`Search` is interactive only) | `$project.Search('<TQL>')` / `Search-TcApi` | `GET …/object/{start}/task/Search?tqlString=` |
| Check out before a write (multi-user) | `list_available_tasks` → `execute_task` `Checkout` (`Checkout Tree` last) | `task "Checkout"` / `checkouttree` | `CheckoutTree()`; check `ChangesAllowed`, `LockedBy` | `…/object/{id}/task/CheckOut` / `CheckOutTree` |
| Create folder | Intermediate folders are created by `create_test_case(folderPath)`; otherwise `execute_task` with a create task from `list_available_tasks` | `task "Create Folder"` + `set Name "…"` | `TCFolder.CreateFolder()` | ? (`…/task/CreateFolder` fits the task pattern, not tested) |
| Create test case | `create_test_case(folderPath, name, steps?, requirements?)`: saves (single-user) or **checks in** (multi-user) on success | `task "Create TestCase"` + `set Name` | `TCFolder.CreateTestCase()`; `EnsureUniqueName()` | `…/object/{folder}/task/CreateTestCase` (u) |
| Step folder (P1) | ? (`execute_task`, name from `list_available_tasks`) | `task "Create Folder"` (on a TestCase: ?) | `TestCase.CreateFolder()` | ? |
| Add step from module | At creation: `create_test_case` `steps=[{moduleId, action, values}]`. Later: `execute_drop_task(target=testCase, sources=[module])` | `Mark` module(s) → `JumpToNode` case → `DropMarked` | `CreateXTestStepFromXModule(module)` (whether values are pre-created: u) | `…/task/CreateXTestStepFromXModule?objToDrop={module}` (u) |
| Add value for an attribute | `execute_drop_task(target=step, sources=[attribute])` | ? | `step.CreateXTestStepValue(attr)`; `APICreateValuesFromDefaultForXTestStep()` for API | ? |
| Set Value / ActionMode / DataType / Operator | `set_attribute(identifier, Value \| ActionMode \| DataType \| Operator \| Condition, value)`. Set Operator **last** (changing ActionMode resets it) | `JumpToNode <value>` → `set Value "…"`, `set ActionMode "…"` | `$v.Value`, `$v.ActionMode = 'Verify'`, `$v.DataType`, `$v.Operator` (last) | ? (`PUT …/object/{id}` body unverified: edit with TCAPI / TCShell instead) |
| ActionProperty | ? (`set_attribute` if `get_attributes` lists it as writable) | ? (`set ActionProperty`) | `$v.ActionProperty = 'Visible'` | ? |
| Nested value / ExplicitName (P3, P4) | ? (child drop and a writable `ExplicitName` are both undocumented) | ? | `$parent.CreateXTestStepValue($childAttr)`, walk `SubValues`; ExplicitName = `Name` or `SetAttibuteValue('ExplicitName', …)` (u) | ? |
| Buffer (P2, P3) | Value: `set_attribute` `ActionMode=Buffer`, `Value=<name>`. Read it with `{B[name]}` | as "Set Value" | as "Set Value"; `TBox Set Buffer` `<Buffername>` + ExplicitName | ? |
| Block call + parameter values (P11) | ? (not documented; `execute_drop_task` block → folder has not been tested) | ? | `CreateTestStepFolderReference(block)` → `ParameterLayerReference` / `CreateParameterLayerReference()` → `AllParameterReferences[].Value` (whether references are created automatically: u) | `…/task/CreateTestStepFolderReference?objToDrop={block}` (u); parameter values ? |
| Create block + parameters | ? (GUI action "Create Reuseable TestStepBlock": check `list_available_tasks`) | ? | `TestStepLibrary.CreateReusableTestStepBlock()` / `CreateReusableTestStepBlockAndReferenceIt(objs)`; `CreateBusinessParameterContainer().CreateParameter()` | ? |
| If / While / Do (P7) | `execute_task` IF / WHILE / DO on the test case (names from `list_available_tasks`) | ? | `CreateIFStatement()` → `Condition`, `ConditionPassedFolder`, `CreateELSEStatement()`; `CreateWHILEStatement()` / `CreateDOStatement()` + `MaximumRepetitions` (loop-body folder: u) | ? |
| Recovery / CleanUp (P1) | ? | ? | `TestCase.CreateRecoveryScenarioCollection()`; scenario creation ? | ? |
| TCP (P1, P8) | ? | ? | `TestConfigurationHelper.SetTestConfigurationParameterValue(obj, name, value)` (whether it creates a new TCP: u) | ? |
| Module | UI: **don't scan**, report the gap (XScan in the UI only). API: `create_api_module(name, path)` | `task "Create XModule"` (empty; XScan in the UI) | `TCFolder.CreateXModule()`; attribute creation ? | ? |
| ExecutionList + entry (P10) | ? (`execute_task` / `execute_drop_task` case → list, not documented) | `task "Create ExecutionList"`; add entry ? | `CreateExecutionList([objToDrop])`, `ExecutionList.CreateExecutionEntry(tc)` | `…/task/CreateExecutionList`, `…/task/CreateExecutionEntry?objToDrop=` (u) |
| Run | `execute_test_suite(identifier)` (+ `isValidationRun=true` = ScratchBook) → poll `execute_test_suite_status(jobId)`. One run at a time | `task "Run"` on the ExecutionList / entry | `ExecutionList.Run()` | `…/object/{eventId}/task/ExecuteNow` (execution tasks are off by default); Execution API `POST /Execution/Enqueue` |
| Read back | `get_object_info` (tree) + `get_attributes` (small batches); `set_attribute` returns the read-back value | `print`, `get <attr>` | `GetTCObject(id)`, `Items` → `TestStepValues` → `Value` / `ActionMode`; `GetAttributeValue`; Export Subset → `tosca-tsu` | `GET …/object/{id}`, `…/association/{Items \| TestStepValues}` (association names: u) |
| Persist | `save_workspace`; `check_in_all` (after the user confirms) | `save` (**required** in batch mode); `checkinall` | `Save()` / `Save-TcApiWorkspace`; `CheckInAll(comment)` | `…/task/CheckInAll?checkInComment=`; save ? |

Sources: `commander-mcp` → `reference/tools-catalog.md`, `reference/workflows/author-automated-test-case.md`, `create-test-case.md`, `add-step-to-existing-test-case.md`, `execute-task.md`, `workspace-orchestration.md`. `cli-api-commander` → `reference/tasks.md`, `reference/commands.md`, `reference/workflows/*.md`. TCAPI and REST: [commander-authoring-apis.md](commander-authoring-apis.md) §2–§3.

### 3.2 Cloud

| Operation | Tosca Cloud MCP (`ToscaCloudMcpServer`) | toscactl (tier 1) | tn (`/tosca` tools, tier 2) | Cloud REST: `tosca_cli.py` / JSON (tier 4) |
|-----------|------------------------------------------|-------------------|-----------------------------|--------------------------------------------|
| Find / reuse candidate | `SearchArtifacts`, `GetModulesSummary`, `AnalyzeTestCaseItems` | `assets find --type TestCase\|Module\|SharedAction\|Folder\|TestCaseTemplate --name` | `tosca_inventory_search`, `tosca_inventory_advancedSearch`, `tosca_builder_getModulesSummary` | `inventory search "<kw>" --type TestCase\|Module\|folder [--folder-id]`, `cases steps --json`, `modules get --json`. Standard modules: `GET /_mbt/api/v2/builder/packages` |
| Create folder | ? | — | `tosca_inventory_createFolder` | `inventory create-folder --name [--parent-id]` |
| Create test case | `ScaffoldTestCase` (scaffold only; don't use it to copy a case) | — | `tosca_builder_scaffoldTestCase(name, description?, testSteps[{name, moduleName?}])` | `cases create --name --state Planned` → `cases update <id> --json-file` (full PUT); `cases clone`; `cases scaffold-web <id> --url` |
| Place in folder | ? | — | `tosca_inventory_move` | `inventory move testCase <id> --folder-id <folder>` |
| Step folders (P1) | ? | — | ? (scaffold creates steps; folder layout ?) | `testCaseItems[]` of `TestStepFolderV2` |
| Add step from module | At scaffold time only | — | At scaffold time only (**no append tool**; first name match wins for `moduleName`) | `TestStepV2` in `cases update`; `cases insert-step <case> <folder> --json-file step.json [--after\|--before\|--at-start]` |
| Set value / actionMode / operator / actionProperty | — | — | — (no step-update tool in the catalog) | Edit `testStepValues[]`, then `cases update`; `cases set-step-value <case> <folder> <step> <attr> --to "…"`. `cases patch` only for shallow paths (deep paths are silently ignored) |
| Nested / placeholder (P3, P4) | — | — | — | `subValues[]` + `explicitName` (`$1`, `$lastContentRow`, `${B[RowNum]}`, column header); container `actionMode: "Select"` with no `value` key |
| Buffer (P2, P3) | — | — | — | Capture: `actionMode: "Buffer"`, `value` = name. Literal: BufferOperations module `8415c10d-…`, `<Buffername>` + `explicitName`, `Input`. Embedded text: `{XB[..]}` in Verify |
| Block call + parameter values (P11) | ? | — | ? | `TestStepFolderReferenceV2` via `cases update`. Block ids come from existing cases (`testCaseItems[].reusableTestStepBlockId`) |
| Create block / add parameters | ? | — | ? | New block: ? (no command). Extend: `blocks add-param <id> --name`, `blocks set-value-range`; read `blocks get --json`. No `blocks update` command exists (§6) |
| If (P7) / loop | — | — | — | `ControlFlowItemV2` `statementTypeV2: "If"`, `condition`, `conditionPassed`. Else / While JSON: ? |
| Recovery / CleanUp (P1) | — | — | — | `recoveryScenarioCollection` in `cases update` (copy the Postcondition teardown) |
| TCP (P1, P8) | — | Only per-run overrides: `playlists run start --param K=V` | ? | `testConfigurationParameters[]` in `cases update`. Password tokens are issued by the **Portal only** |
| Module | — (no scanning) | — | — (API messages: `tosca_builder_createApiMessage` / `updateApiMessage`) | `modules create --name --iface Gui` → `modules update --json-file`; `modules add-attr-param <id> <attr> <param> --to`; `modules set-param`. UI scans: Cloud scanner / Portal |
| TestSheet / template | ? | find only (`--type TestCaseTemplate`) | ? | ? (TSU round-trip only: `cases export-tsu` / `import-tsu`) |
| Playlist + case (P10) | ? (`DeletePlaylistById` only) | `playlists create <name> --test-case <id>…` | `tosca_playlist_add` | `playlists create --name`, `playlists attach-case <pl> <case>` (`InputTestCaseV1`) |
| Run | `RunPlaylist(playlistId, runOnAPersonalAgent=true)` (personal Local Runner) | `playlists run start <id> --wait [--private] [--report junit --report-path]` | `tosca_playlist_run` | `playlists run <id> --wait` (shared agents only; personal agents return 403) |
| Read results | `GetRecentRuns({nameFilter})` → `GetFailedTestSteps({runIds:[executionId]})`; `GetRecentPlaylistRunLogs` | `playlists run view <run>`, `executions attachments --type test-steps\|logs\|junit` | `tosca_playlist_getRecentRuns`, `tosca_playlist_getFailedTestSteps` | `playlists results`, `playlists logs <runId> [--save]` |
| Read back artifact | `AnalyzeTestCaseItems` ? | `assets find` (proves it exists, nothing more) | `tosca_inventory_search` (exists) | `cases get --json` (`version` bumped) + `cases steps --json`; `modules get --json`; `blocks get --json` |
| Persist | immediate | immediate | immediate | immediate: confirm with a GET |

Sources: `tosca-cloud` → `runtime-routing.md`, `builder-orchestration.md`, `reference/tools-catalog.md`, `reference/workflows/*.md`; `toscactl-reference/SKILL.md`; `tosca-authoring-automated-testcase` (SKILL + references); `toscacloud-cli` SKILL.md ("Key CLI commands", caveats), `references/web-automation.md`, `sap-automation.md`, `blocks.md`, `field-notes.md` (MCP vs CLI split). `cases set-step-value`, `cases insert-step`, `cases scaffold-web`, `modules add-attr-param` / `set-param` and `playlists create` / `attach-case` exist in `tools/toscacloud-cli/tosca_cli.py --help` but aren't described in the skill docs yet.

### 3.3 Minimal build sequences per tier

Each sequence builds one case. Plug in the patterns from your build plan. Commander MCP (`commander-mcp` → `author-automated-test-case.md`, `add-step-to-existing-test-case.md`):

```text
get_workspace_info                                   # mode: single / multi-user
get_object_info(<Modules folder>, include_parent_and_children=true)   # resolve module + attribute ids
create_test_case(folderPath="TestCases/<Area>", name, steps=[{moduleId, action, values}])
get_object_info(<new case>, include_parent_and_children=true)        # verify tree
execute_drop_task(target=<caseOrFolder>, sources=[<moduleId>])        # append a step later
execute_drop_task(target=<stepId>, sources=[<attributeId>])           # add a value to it
set_attribute(<valueId>, "ActionMode", "Verify"); set_attribute(<valueId>, "Value", "…")
execute_task(<IF task from list_available_tasks>, objectIds=[<case>]) # only for P7
execute_test_suite(<case>, isValidationRun=true) → execute_test_suite_status(jobId)
save_workspace                                        # check_in_all only after the user confirms
```

TCShell (`cli-api-commander` → `reference/workflows/create-test-case.md`, `reference/commands.md` §3.2):

```text
JumpToNode "/TestCases/<Area>"
task "Create TestCase"
set Name "<App> - <purpose>"
JumpToNode "/Modules/<App>/<Page>"
Mark
JumpToNode "/TestCases/<Area>/<App> - <purpose>"
DropMarked                                            # one XTestStep per marked module
print
save                                                  # batch mode closes WITHOUT saving otherwise
```

TCAPI: run a script through `tools/tosca-commander-cli/scripts/Invoke-TcApi.ps1 -Workspace <tws> -ScriptPath .claude/tmp/build.ps1` (run `-DetectOnly` first). Copy the full P1 / P2 / P4 / P7 / P10 recipes from [commander-authoring-apis.md](commander-authoring-apis.md) §2.2–§2.7.

Cloud, `tosca_cli.py` (`toscacloud-cli` → `references/web-automation.md` "Creation workflow"). Scratch JSON goes in `.claude/tmp/`:

```bash
python tools/toscacloud-cli/tosca_cli.py inventory search "<App>" --type Module --json   # reuse first
python tools/toscacloud-cli/tosca_cli.py cases steps --json <similarCaseId>              # template JSON
python tools/toscacloud-cli/tosca_cli.py cases create --name "<Scenario>" --state Planned --json
python tools/toscacloud-cli/tosca_cli.py cases update <caseId> --json-file .claude/tmp/case.json   # body has "id", no "version"
python tools/toscacloud-cli/tosca_cli.py cases get --json <caseId>                       # version bumped? tree as planned?
python tools/toscacloud-cli/tosca_cli.py inventory move testCase <caseId> --folder-id <folderId>
python tools/toscacloud-cli/tosca_cli.py playlists create --name "<Scenario> — debug" --json
python tools/toscacloud-cli/tosca_cli.py playlists attach-case <playlistId> <caseId>
# run: MCP RunPlaylist(playlistId, runOnAPersonalAgent=true)  or  playlists run <playlistId> --wait
```

The minimum shape of one Cloud step value. The full 10-key shape and the `metadata` echo rules are in `web-automation.md` "TestStepV2 anatomy":

```json
{"id": "<ulid>", "name": "<attr name>", "value": "True", "actionMode": "Verify", "dataType": "String",
 "actionProperty": "Visible", "operator": "Equals",
 "moduleAttributeReference": {"id": "<attrId>", "moduleId": "<moduleId>", "metadata": {"businessType": "<bt>", "isUsedAsIdentification": false}},
 "subValues": [], "disabled": false}
```

Cloud, official path (`tosca-authoring-automated-testcase`): run `toscactl assets find --type module --name "<partial>" --json --silent` → the user picks the modules → `tn --loop "Activate /tosca. Create automated test '<name>' reusing modules from folders <folders>. Report module gaps. loop_complete when done."` → `toscactl assets find --type testCase --name "<name>" --json --silent`. Values, blocks and control flow then need tier 4.

## 4. Build rules / quality gates

Check these before the first run, and again before you report.

**Structure**
- [ ] G1. The case follows the team convention from the reuse scan. Otherwise use P1: Precondition → Process → Verification → Postcondition, plus a CleanUp scenario ([test-patterns.md](test-patterns.md) P1; [commander-object-model.md](commander-object-model.md) §4.2, §10).
- [ ] G2. The case is self-contained, ends in the state it started from, and has ≥1 business Verify. Verify after each significant step (object model §4.2).
- [ ] G3. Names follow the naming patterns: `<App> - <purpose>`, verb-first step names, `App | Area | Page` module names (object model §2).

**Modules and locators**
- [ ] G4. Every locator is unique (proved live with a count of 1) and stable. Prefer `Id` / a test-ID attribute (`attributes_data-test-id`) over `ClassName` / `InnerText`. Never use `style_*`, `OuterHtml` or `attributes_ng-reflect-*` as the primary identifier (P9; `toscacloud-cli` SKILL.md "TechnicalId priority"; `web-exploration`, `sap-gui-exploration`).
- [ ] G5. The module root has `Engine`. On Cloud, every Html attribute also has `Engine` + `BusinessAssociation`, and root `Url` / `Title` are `TechnicalId` (`web-automation.md` "Module structure", "Attribute anatomy").
- [ ] G6. A module covers one screen area with ≤~20 controls, and attribute order matches the flow. Never delete a used module and rebuild it: rescan it or fix it (object model §3.5).
- [ ] G7. Reuse Standard modules / packages before you build a wrapper (object model §7; `standard-modules.md`).

**Values and data**
- [ ] G8. Use WaitOn on `Exists` / `Visible` / `InnerText`, not `TBox Wait` / `Timing.Wait`. A static wait is only for teardown settling or the documented SPA bootstrap (P12; `field-notes.md`).
- [ ] G9. Each buffer is named, set once, and read later with `{B[..]}`. Nothing buffered goes unused (P2, P3).
- [ ] G10. Environment values and credentials come from TCPs (`{CP[..]}`). No literal secrets. Passwords are Password-type only (P1, P5; `web-automation.md` "Password fields").
- [ ] G11. Records the test creates get generated unique data (`{RANDOMTEXT}`, a timestamp) (P3).
- [ ] G12. Use Constraint to pick a row, not a loop (P4).
- [ ] G13. Use `X` for clicks. `{CLICK}` / `{SENDKEYS}` only when the direct form fails. No `{SCRIPT}` / `{XP}` on Cloud (object model §6).

**Reuse**
- [ ] G14. Create a block only for steps reused across several cases, and give it business parameters. Within one case, use `Repetition` instead (P11; object model §8).
- [ ] G15. Use `{PL[..]}` as the whole value inside blocks. Before you rename a parameter or change a block, check every call site (`UsedBy`) (P11; `tosca-tsu` → `tsu-schema.md` §4).
- [ ] G16. Cloud block call: `parameterLayerId` copied verbatim (absent when there are no parameters), a real `referencedParameterId`, and parameter names copied byte-for-byte (`blocks.md`).

**Control flow and integrity**
- [ ] G17. Use If only for optional elements (banners, pop-ups, leftover tabs), with a Verify condition. Never use it as a retry, and never around a business Verify (P7).
- [ ] G18. Every While / Do has `MaximumRepetitions` (5–20) (P7; object model §9).
- [ ] G19. **No defect masking**: never remove, weaken, disable or If-wrap a Verify to get green. No recovery that dismisses the error under test (`toscacloud-cli` SKILL.md "No-defect-masking rule").
- [ ] G20. Don't edit template instances: change the template or the TestSheet and reinstantiate (P8; object model §11).
- [ ] G21. Preserve the user's navigation flow. No shortcut URLs or T-codes they didn't use (`field-notes.md`).

**Process**
- [ ] G22. One artifact at a time: build → re-read (§5) → run → fix → re-run.
- [ ] G23. Re-read after **every** write. A `✓`, a 204 or `{}` is not proof.
- [ ] G24. Commander: `save` after each group of mutations. Check in only after the user confirms. Note that MCP `create_test_case` checks in by itself in multi-user workspaces (§6).
- [ ] G25. Deletes, force overwrites and SAP save / post need explicit user confirmation.

## 5. Verification per runtime

| Runtime | Read back | Compare | Validate by running |
|---------|-----------|---------|---------------------|
| Commander MCP | `get_object_info(<case>, include_parent_and_children=true)`, then `get_attributes` on steps / values in small batches | Tree order, module per step, `Value` / `ActionMode` / `Operator` / `DataType` per value. `set_attribute` returns `old_value` + read-back | `execute_test_suite(isValidationRun=true)` → `execute_test_suite_status` until `IsRunning=false`. Recovery runs only in an ExecutionList |
| TCShell | `JumpToNode <path>` → `print` / `get <attr>` | Name, path, attributes after each `set` | `task "Run"` on an ExecutionList, then `save` |
| TCAPI | After `Save()`: `GetTCObject($tc.UniqueId)` / `Search`, print `Items` → `TestStepValues` → `Value` / `ActionMode` / `Operator`. Offline: Export Subset → `tosca-tsu` tree | The build plan against the printed tree. Compare ExplicitName with a value created in the GUI | ScratchBook / `ExecutionList.Run()` |
| Tosca REST | `GET …/object/{id}` (`Attributes`), `…/association/Items` | Attributes against the plan; `CheckOutState` | Execution API `Enqueue` → `Status` → `Results` |
| toscactl | `assets find --type TestCase --name` | Existence and folder only | `playlists run start --wait --assert-success`; `executions attachments --type test-steps` |
| tn / Cloud MCP | `tosca_inventory_search` / `SearchArtifacts` | Existence only (no step tree via Builder tools) | Personal agent: `RunPlaylist(runOnAPersonalAgent=true)` → `GetRecentRuns({nameFilter: exact name})` → `GetFailedTestSteps` (Local Runner preflight: `toscacloud-cli` SKILL.md "Iterative test-development loop") |
| `tosca_cli.py` | `cases get --json` + `cases steps --json`; `modules get --json`; `blocks get --json` | **`version` bumped** and the edited field changed. For a PATCH, calibrate first with a `/description` round-trip | `playlists run <id> --wait` → `playlists logs <runId>` (shared agent) |

## 6. Runtime gaps and escalation

| Runtime | Can't do (authoring) | Next tier |
|---------|----------------------|-----------|
| Commander MCP | No search / TQL. No UI scanning. Block calls, block creation, recovery, TCPs, ExecutionLists and nested values aren't documented. `create_test_case` takes steps **only at creation** and checks in by itself in multi-user workspaces | Undocumented operation: try it via `list_available_tasks` on a scratch object, or close Commander → TCAPI. Search: walk the tree, or TCShell / TCAPI with Commander closed |
| TCShell | No typed nested values, block wiring, control flow or TCPs. Tasks don't prompt for names, so `set Name` after each create. Can't open a workspace Commander has locked | TCAPI. Commander open: MCP, or Remote Control with consent |
| TCAPI | Needs Commander installed plus a license, and an unlocked `.tws`. Several members are unverified ([commander-authoring-apis.md](commander-authoring-apis.md) §5). No UI scanning | REST for remote read / checkout. Scan in the Commander UI |
| Tosca REST | Attribute writes and create bodies are unverified. Execution tasks are off by default since 2024.1 | Values via TCAPI / TCShell. Runs via the Execution API |
| toscactl | No authoring: find, playlists, runs, datasets only | tn |
| tn / Cloud MCP | Scaffold only: no step append, no value edit, no blocks, no control flow, no recovery, no TCPs. `ScaffoldTestCase` drops bindings when used as a copy. No deletes except playlists / API messages | `tosca_cli.py` (tier 4) for every JSON-level edit. Personal-agent runs stay on MCP |
| `tosca_cli.py` | Can't create a new block or a While loop (not documented). No `blocks update` command. No Password tokens (Portal). No deletes with the service role (403). Personal agents return 403. No TestSheet / template authoring | Portal UI (block creation, secrets, deletes, templates), then continue by JSON. Runs on MCP |
| Cloud templates / TestSheets | Objects exist, but no authoring tooling in this repo | Ask the user. Fall back to data sets + block parameters (P8) |

When you escalate, say which tier you used and why ("Cloud MCP has no append-step tool → `cases insert-step`").
