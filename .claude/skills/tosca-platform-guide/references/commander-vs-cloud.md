# Tosca Commander ↔ Tosca Cloud concept map

Tosca Cloud's test model is essentially Commander's TBox model (XModules, XTestSteps, reusable blocks, TechnicalIds, action modes) stored as JSON behind REST APIs. Use this map to reuse knowledge from one platform on the other: the **Cloud references in `toscacloud-cli`** (web-automation, sap-automation, blocks, standard-modules, best-practices) are the most detailed material in this repo and mostly apply to Commander too.

Rows marked ≈ are close analogues, not identical. Verify against a real object on the target platform before relying on them (Commander: `get_attributes`; Cloud: `cases get --json` / `modules get --json`).

## Objects

| Concept | Commander (on-prem / Server) | Cloud | Notes |
|---------|------------------------------|-------|-------|
| Container / scope | Workspace (`.tws`), project root, component folders | Tenant → space/workspace → Inventory folders | Commander multi-user: checkout / check-in. |
| Object identity | Surrogate ID, node path (`/TestCases/...`) | Inventory `entityId`, MBT id, ULIDs for items/params | Cloud: use Inventory `entityId` for MBT calls. |
| UI module | **XModule** with XModuleAttributes (scanned) | **Module** (`businessType` Window/…) with attributes | Same parameter kinds: TechnicalId / Configuration / Steering. |
| Engine selection | `Engine` configuration param (Html, SapEngine, …) | Root `Engine` param + `metadata.engine` | Same engine names. |
| Web locators | TechnicalIds: Tag, Id, Name, Title, InnerText, HREF, ClassName | Same | Same priority rules (`web-exploration`). |
| SAP locators | `RelativeId`; window by transaction / program / screen | `RelativeId`; root quartet Engine/Transaction/ProgramName/ScreenNumber | Same path grammar (`sap-automation.md`). |
| Test case | TestCase → TestStepFolder → **XTestStep** → **XTestStepValue** | TestCase → `testCaseItems`: `TestStepFolderV2` → `TestStepV2` → `testStepValues` | 1:1 structure. |
| Action modes | Input, Insert, Verify, Buffer, WaitOn, Select, Constraint, Exclude | `actionMode` with the same names | Plus `actionProperty` / operator on Verify. |
| Value expressions | `{CLICK}`, `{SENDKEYS[..]}`, `{B[buf]}`, `{CP[param]}`, `{DATE}`, … | Same syntax | |
| Reusable steps | Library → **Reuseable TestStepBlock** + Business Parameters; referenced in test cases | **Reusable blocks** (`blocks` API, artifact type `sharedAction`) + `businessParameters`; referenced via `TestStepFolderReferenceV2` + `parameterLayerId` | Cloud needs ULID wiring (`blocks.md`). |
| Control flow | If / Then / Else, loops (While / Do) statements | `ControlFlowItemV2` (If / loops) | |
| Test configuration | Test Configuration Parameters (TCPs), inherited down the folder tree | `testConfigurationParameters` on the case | e.g. `Browser`, credentials. |
| Recovery / cleanup | Recovery Scenarios, CleanUp Scenarios | `recoveryScenarioCollection` | |
| Standard modules | Standard subset (TBox Automation Tools: OpenUrl, Wait, Buffer, Execute JavaScript, T-code, …) | Engine-bundled Standard **packages** (well-known GUIDs, `/builder/packages`) | Don't rebuild what Standard modules already do. |
| API tests | API modules (`create_api_module`) | API messages (`apiMessage`), API execution | |
| Test data | TestSheets / TCD, TemplateInstances, Test Data Service (TDS) | ≈ Data sets (TDM, `tosca-datasets`) | Cloud has no TemplateInstance equivalent. Use data sets + parameters. |
| Manual tests | ManualXTestStep (+ values for expected results) | Manual test cases (`tosca-authoring-manual-testcase`) | |
| Execution grouping | **ExecutionList** → ExecutionEntries | **Playlist** → items | |
| Execution result | ExecutionLog → ExecutionTestCaseLog → ExecutionXTestStepLog | Run → failed test steps (`GetFailedTestSteps`, `toscactl` execution views) | |
| Execution agents | Local / Distributed Execution (DEX) agents | Team agents, personal Local Runner | |
| Execution trigger | `execute_test_suite` (+ `execute_test_suite_status`) / TCShell | `toscactl` run / `RunPlaylist` (MCP) / `playlists run` (CLI) | Commander: one execution at a time. |
| Data Integrity | DI tools in `commander-mcp` (DB Expert, row-by-row, lineage) | DI via `tn` (`di-orchestration.md`) | |
| Exchange format | Tosca subset `.tsu` export/import | TSU export/import (`toscacloud-cli`: `cases export-tsu` / `import-tsu`) | **Same schema** (gzip JSON entity graph; Commander GUID vs Cloud ULID surrogates). Inspect with the `tosca-tsu` skill. Check versions before importing across platforms. |
| Persistence | In-memory until `save_workspace`; `check_in_all` for multi-user | Immediate REST writes with a `version` field; confirm via GET | |

## Reading an object on one platform to rebuild it on the other

The same test reads differently on each side. Use this to translate a source object found in a cross-platform reuse scan (`reuse-scan.md` §3):

| You read on Cloud (JSON) | Look for / set on Commander (attributes, tasks) |
|--------------------------|--------------------------------------------------|
| `testCaseItems[]` tree (`TestStepFolderV2`, `TestStepV2`) | TestStepFolders / XTestSteps under the TestCase (`get_object_info` children) |
| `TestStepV2.module` / `moduleAttributeReference` | XTestStep's referenced XModule / XTestStepValue's XModuleAttribute |
| `testStepValues[].value`, `actionMode`, `actionProperty`, operator | XTestStepValue `Value`, `ActionMode`, `Operator`, `Condition` (`get_attributes`) |
| Module root params `Engine`, `Url`/`Title` or SAP `Transaction`/`ProgramName`/`ScreenNumber` | XModule configuration params / TechnicalIds of the same names |
| Attribute params `Tag`, `Id`, `InnerText`, `RelativeId`, … (`type: TechnicalId`) | XModuleAttribute TechnicalIds with the same names and values |
| `TestStepFolderReferenceV2` + `parameters[]` → block `businessParameters` | Reference to a Reuseable TestStepBlock + its Business Parameter values |
| `testConfigurationParameters` | Test Configuration Parameters (TCPs) on the case or an ancestor folder |

Commander → Cloud is the same table read from right to left. Build the Cloud JSON following `toscacloud-cli` (fresh ULIDs, the block's `parameterLayerId` copied verbatim). Attribute names and exact shapes can differ by Commander version: check them with `get_attributes` on a real object before writing.

## What transfers well

- **Locator strategy** (TechnicalId priority, uniqueness proof, viewport and visibility traps): identical engines.
- **SAP window identity and RelativeId grammar**: identical.
- **Test design**: 4-folder layout (Precondition / Process / Verification / Postcondition), buffers, reusable blocks with business parameters, no-defect-masking: identical practice.
- **Failure taxonomy** (`tosca-analyzing-execution-results` → failure-taxonomy.md): the engine error messages are the same.

## What doesn't

- **Mechanics**: Commander uses tasks and attributes on live objects (MCP `execute_task`, `set_attribute`) or TCShell commands. Cloud uses JSON documents over REST, with ULIDs and PATCH/PUT quirks. Don't port JSON shapes to Commander, or Commander task names to Cloud.
- **Transactions and locking**: Commander checkout/check-in and a single UI thread. Cloud has none of that, but writes can be silently ignored, so always GET after writing.
- **Scanning**: Commander has XScan in the desktop. Cloud modules are authored as JSON or scanned by the Cloud scanner. In both cases, validate locators live first (explorer skills).
