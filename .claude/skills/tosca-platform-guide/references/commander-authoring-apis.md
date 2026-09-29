# Commander authoring without MCP: TCAPI and the Tosca REST API

How to **create and edit** Commander objects (folders, test cases, XTestSteps, values, block references, If/While, ExecutionLists, TCPs) when the in-process Commander MCP isn't available: Commander < 26.1, Commander closed, CI, or a server-side job. Object shapes and design rules: [commander-object-model.md](commander-object-model.md). Step shapes: [test-patterns.md](test-patterns.md). Runtime detection, hosts and the search-only examples: `cli-api-commander` → `tcapi.md`, `workspace-checkout.md`, `path-selection.md`.

Evidence labels used below: **[doc]** = the member is listed in the official TCAPI reference (DevCorner, read on 2025.1; the `TCAPI` class also checked on 2024.1 and 2026.1); **[code]** = seen in public client code; **[inferred]** = deduced from the other two, not confirmed; **(unverified)** = check it against the docs for your version or a real workspace before you rely on it.

## 1. Which API?

| Situation | Use | Why |
|-----------|-----|-----|
| Commander 26.1+ open with the workspace | **Commander MCP** (`commander-mcp`) | In-process, no second lock, has Data Integrity |
| Commander installed on this machine, workspace closed (or a separate clone), any version 24.1+ | **TCAPI** via PowerShell / dotnet script | Typed object model: every create/edit below is a documented method or property |
| Only a Tosca Server is reachable (no Commander on the agent machine), or a remote/CI job | **Tosca REST API** (`/rest/toscacommander`) | HTTP, remote. Solid for read, TQL search, checkout/check-in, update, run. Authoring is only partly verified (§3) |
| Batch script, simple creates (`Create TestCase`, `DropMarked` modules onto a case), CI | **TCShell** (`cli-api-commander` → `reference/tasks.md`, `commands.md`) | No code, but values/ActionModes need `set` per object |
| Trigger a run and fetch results only | **Execution API** (Tosca Server, `/automationobjectservice/api`) | Runs only, no authoring (§3.5) |

TCAPI vs REST:

| | TCAPI | REST API |
|--|-------|----------|
| Needs | Commander installed + license on the agent machine, file/DB access to the workspace, the matching .NET host (`tcapi.md`) | Tosca Server with `Tricentis.Tosca.RestApiService` running, a workspace folder on the server, credentials |
| Lock | Opens its own workspace lock. Fails if Commander (or REST) has the same `.tws` open | The service opens the workspace through TCAPI on the server (it consumes a TCAPI license there), so the same lock rule applies server-side |
| Authoring coverage | Full typed API (§2) | Tasks via URL; attribute writes and object creation bodies unverified |
| Best for | Building/refactoring test cases in bulk | Remote read/search, checkout, check-in, UpdateAll, triggering tasks |

Sources: [TCAPI reference 2025.1](https://documentation.tricentis.com/devcorner/2025.1/tcapi/webindex.html), [Tosca REST API Service settings (Tosca Connect page)](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_connect/connect.htm), [Tosca Server features](https://docs.tricentis.com/tosca-2025.1/en-us/content/tosca_server/tosca_server_features.htm)

## 2. TCAPI authoring recipes (PowerShell)

Run a recipe with the repo helpers so host selection, `Add-Type`, save and close are handled: `tools/tosca-commander-cli/scripts/Invoke-TcApi.ps1 -Workspace <tws> -User $env:TOSCA_USER -Password $env:TOSCA_PASSWORD -ScriptPath .claude/tmp/build.ps1` (it saves after the script unless `-NoSave`, then closes). Inside the script, the session helpers from `lib/TcApiSession.ps1` are loaded (`Get-TcApiProject`, `Search-TcApi`, `Save-TcApiWorkspace`). Run `Invoke-TcApi.ps1 -DetectOnly` first. Put scratch scripts in `.claude/tmp/`.

### 2.1 Class and member map (all [doc] unless marked)

| Need | Class → member | Returns |
|------|----------------|---------|
| Start / stop | `TCAPI.CreateInstance()` (also `(TCAPILicenseMode)`), `OpenWorkspace(twsPath, loginName, loginPassword, logLevel)`, `CloseWorkspace()`, `TCAPI.CloseInstance()` | `TCAPI`, `TCWorkspace` |
| Server repository (TSR) | `ToscaServerLogin(personalAccessToken)` or `ToscaServerLogin(clientId, clientSecret)`; `CreateNewWorkspaceFromServerRepository(workspaceDirPath, projectName, branchName)` (3rd param is `snapshotName` in 2026.1) | `TCAPIManagedUserData`, `TCWorkspace` |
| Workspace | `GetProject()`, `GetTCObject(objectId)`, `Search(startObject, TQL)`, `Save()`, `CheckInAll(checkInComment)`, `UpdateAll()`, `RevertAll()`, `IsSingleUser` | |
| Any object (`TCObject`) | `Search(tqlString)`, `GetAttributeValue(attrName)`, `SetAttibuteValue(attrName, attrValue)` (Tricentis spelling, one "r"), `GetPropertyValue`/`SetPropertyValue`, `ExecuteTask(name[, TCTaskParams])`, `ExecuteDropTask(name, dropObject, copy)`, `IsTaskApplicable(task)`, `ChangesAllowed`, `UniqueId`, `NodePath`, `Delete(...)`, `Move(obj)`, `Reorder(obj, InsertAfter)`, `EnsureUniqueName()` | |
| Checkout (`OwnedItem`: folders, test cases, lists, libraries) | `Checkout()`, `CheckoutTree()`, `Checkin(Comment)`, `CheckinTree(Comment)`, `RevokeCheckout(...)`, `CheckOutState`, `IsCheckedOutByMe`, `LockedBy` | |
| Folders (`TCFolder`) | `CreateFolder()`, `CreateTestCase()`, `CreateExecutionList([objToDrop])`, `CreateTestStepLibrary()`, `CreateTestCaseAndTestStepFromModule(objToDrop)`, `CreateXModule()`, `Items` | new object |
| Test case (`TestCase`) | `CreateFolder()` → `TestStepFolder`, `CreateXTestStepFromXModule(objToDrop)` → `XTestStep`, `CreateTestStepFolderReference(objToDrop)` → `TestStepFolderReference`, `CreateIFStatement()` / `CreateWHILEStatement()` / `CreateDOStatement()` → `TestCaseControlFlowItem`, `CreateRecoveryScenarioCollection()`, `CreateManualXTestStep()`, `ConvertToTemplate()`, `CreateTemplateInstance`, `TestCaseWorkState`, `Items` | |
| `TestStepFolder`, `TestCaseControlFlowFolder`, `ReuseableTestStepBlock` | same create set as TestCase (`CreateFolder`, `CreateXTestStepFromXModule`, `CreateTestStepFolderReference`, `CreateIFStatement`…), plus `Condition`, `Repetition` (strings), `Disable(reason)` / `Enable()` | |
| XTestStep | `TestStepValues`, `TestStepValuesInRightOrder`, `Module`, `CreateXTestStepValue(objToDrop)`, `CreateXTestStepValueTree()`, `APICreateValuesFromDefaultForXTestStep()`, `Condition`, `Repetition`, `Disabled` | |
| XTestStepValue | `Value`, `ActionMode` (`XTestStepActionMode`), `DataType` (`ModuleAttributeDataType`), `Operator` (`Operator`), `ActionProperty`, `Name` (get/set), `ModuleAttribute`, `SubValues`, `Condition`, `CreateXTestStepValue(objToDrop)`, `CreatePLReference(objToDrop)` | |
| Control flow | `TestCaseControlFlowItem.Condition` / `ConditionPassedFolder` (Then) / `ConditionFailedFolder`, `CreateELSEStatement()` → `TestCaseControlFlowFolder`, `MaximumRepetitions`, `StatementType` | |
| Blocks | `TestStepLibrary.CreateReusableTestStepBlock()`, `CreateReusableTestStepBlockAndReferenceIt(objsToDrop)`; `ReuseableTestStepBlock.CreateBusinessParameterContainer()` → `ParameterLayer.CreateParameter()` → `Parameter` (`Name`, `ValueRange`); `TestStepFolderReference.ReusedItem`, `ParameterLayerReference`, `CreateParameterLayerReference()`; `ParameterLayerReference.AllParameterReferences`, `CreateParameterReference(objToDrop)`; `ParameterReference.Value` | |
| Execution | `ExecutionList.CreateExecutionEntry(objToDrop)` → `ExecutionEntry` (`Repetitions`, `TestCase`), `ExecutionList.CreateFolder()`, `ExecutionList.Run()` | |
| TCPs | static `TestConfigurationHelper.SetTestConfigurationParameterValue(objectWithConfiguration, paramName, paramValue)`, `RenameTestConfigurationParameter(...)`, `ResetTestConfigurationParameterToDefaultValue(...)`; `TCFolder` and `TestCase` implement `IObjectWithConfiguration` | |

Enums [doc]: `XTestStepActionMode` = `Input, Insert, Verify, Buffer, WaitOn, Select, Constraint, Exclude, Delete, Modify, Output, …` (plus `DEPRECATED_*` members: don't use). `Operator` = `None, Equals, NotEquals, Greater, GreaterOrEqual, Smaller, LessOrEqual`. `ModuleAttributeDataType` = `String, Numeric, Date, Boolean, Password, Secret, RawString`. `TestCaseWorkState` = `PLANNED, IN_WORK, COMPLETED`. The enums live in `Tricentis.TCAPIObjects.Objects`. PowerShell also converts a plain string (`'Verify'`) to the enum on assignment.

Task methods have overloads with string or `MsgBoxResult_*` arguments that answer the dialogs the GUI would show (e.g. `Delete(ContinueOnWarning, DeleteSelectedObject)`). Prefer the parameterless overload where one exists. The accepted string values ("Yes"/"OK"…) aren't documented on the pages read (unverified).

### 2.2 Open, check out, find the inputs

```powershell
# build.ps1 — run via Invoke-TcApi.ps1 (workspace already open, helpers loaded)
$project = Get-TcApiProject
$ws      = Get-TcApiActiveWorkspace
$folder  = (Search-TcApi -Start $project -Tql '=>SUBPARTS:TCFolder[Name=="Orders"]')[0]
$module  = (Search-TcApi -Start $project -Tql '=>SUBPARTS:XModule[Name=="Order form"]')[0]
$block   = (Search-TcApi -Start $project -Tql '=>SUBPARTS:ReuseableTestStepBlock[Name=="Open app"]')[0]  # TQL type name [inferred]
if (-not $folder -or -not $module) { throw 'Reuse scan target missing: report, do not invent' }

if (-not $ws.IsSingleUser) {                       # multi-user: check out before any write
    if (-not $folder.ChangesAllowed) { [void]$folder.CheckoutTree() }
    if (-not $folder.ChangesAllowed) { throw "Checked out by $($folder.LockedBy): stop and report" }
}
```

Opening directly (outside the helper): `$api.OpenWorkspace($tws, $env:TOSCA_USER, $env:TOSCA_PASSWORD, 0)`. The docs (2024.1–2026.1) show four parameters; this repo's helper and public code ([Boehringer-Ingelheim/toscaci `WorkspaceSession.cs`](https://github.com/Boehringer-Ingelheim/toscaci), Apache-2.0) call it with three. Use whichever overload your version binds. The meaning of `logLevel` values is undocumented (unverified). TSR workspace: `ToscaServerLogin($env:TOSCA_PAT)` then `CreateNewWorkspaceFromServerRepository($dir, $project, $branch)`; the required call order is (unverified).

### 2.3 Test case skeleton, steps and values (P1, P2, P4, P5)

```powershell
$tc = $folder.CreateTestCase();  $tc.Name = 'Create order - standard customer'; $tc.EnsureUniqueName()
$pre  = $tc.CreateFolder(); $pre.Name  = 'Precondition'
$proc = $tc.CreateFolder(); $proc.Name = 'Process'
$ver  = $tc.CreateFolder(); $ver.Name  = 'Verification'
$post = $tc.CreateFolder(); $post.Name = 'Postcondition'

[void]$pre.CreateTestStepFolderReference($block)          # CALL 'Open app' (§2.4)

$step = $proc.CreateXTestStepFromXModule($module); $step.Name = 'Enter order'
function Get-Val($s, $attr) { $s.TestStepValues | Where-Object { $_.ModuleAttribute.Name -eq $attr } | Select-Object -First 1 }

$v = Get-Val $step 'Customer'
if (-not $v) { $attr = $module.Search('=>SUBPARTS:XModuleAttribute[Name=="Customer"]')[0]  # [inferred] TQL
               $v = $step.CreateXTestStepValue($attr) }
$v.Value = 'ACME'; $v.ActionMode = 'Input'

$v = Get-Val $step 'Order number'; $v.Value = 'OrderNo'; $v.ActionMode = 'Buffer'          # P2: value = buffer NAME
$v = Get-Val $step 'Save';         $v.Value = '{CLICK}'; $v.ActionMode = 'Input'

$chk = $ver.CreateXTestStepFromXModule($module); $chk.Name = 'Status saved'
$v = Get-Val $chk 'Status'; $v.ActionMode = 'Verify'; $v.Operator = 'Equals'; $v.Value = 'Saved'
$v = Get-Val $chk 'Save';   $v.ActionMode = 'Verify'; $v.ActionProperty = 'Visible'; $v.DataType = 'Boolean'; $v.Value = 'True'
```

- Whether `CreateXTestStepFromXModule` pre-creates a value per module attribute, and in which order, is (unverified): read `TestStepValues` back and create missing ones with `CreateXTestStepValue(<XModuleAttribute>)`. For API modules, `APICreateValuesFromDefaultForXTestStep()` fills request/response values (P5: request values `Insert`, response `Verify`/`Buffer`).
- Setting `ActionMode` or `DataType` resets `Operator` (object model §4.1), so set the operator **last**.
- Nested values (table row/cell, P4): walk `SubValues`, or create children with `$parent.CreateXTestStepValue($childAttr)`. The dynamic name (`$1`, `#2`, `Customer`, buffer names on `TBox Set Buffer`'s `<Buffername>`, P3) is the value's **ExplicitName**. TCAPI exposes a settable `Name` on XTestStepValue; whether that is the ExplicitName or you need `SetAttibuteValue('ExplicitName', …)` is (unverified): set it, then compare with a value created in the GUI.
- Generic fallback for any attribute the typed API doesn't expose: `$obj.GetAttributeValue('X')` / `$obj.SetAttibuteValue('X', 'v')`. Read `GetAllPropertyNames()` / an existing object first; never guess names.
- Step switches: `$step.Condition = '…'` (TestCase-Design condition), `$step.Repetition = '3'`, `$step.Disable('reason')`. `$tc.TestCaseWorkState = 'IN_WORK'` until it runs green, then `COMPLETED`.

### 2.4 Reusable block reference with business parameters (P1, P5)

```powershell
$ref = $pre.CreateTestStepFolderReference($block)
$plr = $ref.ParameterLayerReference; if (-not $plr) { $plr = $ref.CreateParameterLayerReference() }
foreach ($pr in $plr.AllParameterReferences) {
    switch ($pr.Name) { 'URL' { $pr.Value = '{CP[URL]}' } 'User' { $pr.Value = '{CP[AppUser]}' } }
}
```

Whether parameter references appear automatically when the block has a parameter container is (unverified): if `AllParameterReferences` is empty, create them with `$plr.CreateParameterReference($parameter)` using the block's `ParameterLayer.Parameters`. New block from existing steps: `$library.CreateReusableTestStepBlockAndReferenceIt(@($folderOrSteps))`; parameters: `$blk.CreateBusinessParameterContainer().CreateParameter()` then set `Name`, and use `{PL[Name]}` in step values. Only for steps reused in several cases (object model §8). Check `UsedBy` before you change a block.

### 2.5 If with a Verify condition (P7), loops

```powershell
$if = $proc.CreateIFStatement()
$c  = $if.Condition.CreateXTestStepFromXModule($bannerModule)
$v  = Get-Val $c 'Accept'; $v.ActionMode = 'Verify'; $v.ActionProperty = 'Visible'; $v.Value = 'True'
$t  = $if.ConditionPassedFolder.CreateXTestStepFromXModule($bannerModule)
$v  = Get-Val $t 'Accept'; $v.Value = '{CLICK}'; $v.ActionMode = 'Input'
# optional: $else = $if.CreateELSEStatement()
```

`CreateWHILEStatement()` / `CreateDOStatement()` give the same item type; set `MaximumRepetitions`. Which folder is the loop body for While/Do (`ConditionPassedFolder` is the guess) is (unverified). Never move a business Verify into a Condition (defect masking, object model §9).

### 2.6 ExecutionList (P10) and TCPs (P1, P8)

```powershell
$elFolder = (Search-TcApi -Start $project -Tql '=>SUBPARTS:TCFolder[Name=="Smoke"]')[0]   # an ExecutionLists folder
$el = $elFolder.CreateExecutionList(); $el.Name = 'Orders - smoke'
$entry = $el.CreateExecutionEntry($tc)             # or $elFolder.CreateExecutionList($tcFolder)

[Tricentis.TCAPIObjects.Objects.TestConfigurationHelper]::SetTestConfigurationParameterValue($folder, 'URL', 'https://test.example')
```

Whether `SetTestConfigurationParameterValue` **creates** a TCP that doesn't exist yet or only sets an existing one is (unverified): read it back with `$folder.GetPropertyValue(...)` or TQL `EVALCP("URL")`. Put TCPs as high as possible; secrets only as Password-type TCPs, never in plain strings. Running: `$el.Run()` needs a license-capable agent session; unattended runs belong on DEX / the Execution API.

### 2.7 Save, check in, close

```powershell
Save-TcApiWorkspace                                          # $ws.Save()
if (-not $ws.IsSingleUser) { $ws.CheckInAll('Agent: create order smoke test') }   # ask the user first (guardrail 8)
# Invoke-TcApi.ps1 saves and calls Close-TcApiWorkspace (CloseWorkspace + CloseInstance) on exit
```

Sources: [TCAPI class](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic14.html), [TCWorkspace](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic6952.html), [TCObject](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic5774.html), [TCFolder](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic5494.html), [TestCase](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic7483.html), [TestStepFolder](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic8686.html), [XTestStep](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic10205.html), [XTestStepValue](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic10255.html), [TestCaseControlFlowItem](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic7688.html), [TestStepFolderReference](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic8733.html), [TestStepLibrary](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic8768.html), [ReuseableTestStepBlock](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic4958.html), [ExecutionList](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic1595.html), [TestConfigurationHelper](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic8056.html), [XTestStepActionMode](https://documentation.tricentis.com/devcorner/2025.1/tcapi/topic10392.html). Topic numbers differ per version: use `VersionProfile.DocBaseUrl` from path detection and navigate by class name. Older releases (e.g. [16.0 TCWorkspace](https://documentation.tricentis.com/devcorner/1600/tcapi/topic6781.html)) already have `Save`, `Search`, `CheckInAll`, `UpdateAll`.

## 3. Tosca REST API recipes

### 3.1 Hosting and auth

- Installed and configured with **Tosca Server** as Windows service `Tricentis.Tosca.RestApiService`. Settings: `appsettings.json` in `C:\Program Files (x86)\TRICENTIS\Tosca Server\RestApiService` (since 2024.1; earlier `TCAPIRestServiceStandalone.exe.config`). Key settings: `WorkspaceBasePath` (folder holding the workspaces; the `{workspace}` in URLs is a workspace under it), `APIInstanceCachingTime` (default 60 s), `LogExceptions`, `ExceptionLogPath`. Since 2024.1 **running tests through the REST API is off by default** (`DisableExecutionTasks`). [doc]
- Base URL: `https://<server>:<port>/rest/toscacommander` through the Tosca Server gateway [code: Boehringer-Ingelheim/tosca-service, centreon-plugins]. Some installs expose `/tcrest/toscacommander` [code: xebialabs xlr-tosca-plugin, MIT]. Port depends on the installation. WCF-hosted versions serve an operations list at `<base>/help` (seen on a public install, unverified per version).
- Use a **dedicated clone** of the workspace for the service, not one a person works in: the service holds a TCAPI lock on it [third-party docs: OpsHub].
- Auth headers [code]: client credentials → `Authorization: Basic base64(clientId:clientSecret)` plus `authMode: clientCredentials` (Boehringer, Apache-2.0); plain `Authorization: Basic base64(user:password)` (Centreon); PAT → `AuthMode: pat` + the token in `Authorization` (konopski wrapper, unverified). Basic user/password reportedly doesn't work against a Tosca Server Repository (OpsHub, unverified). Windows authentication (unverified).
- Credentials come from env vars (`TOSCA_CLIENT_ID`, `TOSCA_CLIENT_SECRET`, `TOSCA_PAT`); never literals in scripts or `.agents/`.

```powershell
$base = "$env:TOSCA_REST_BASE/rest/toscacommander"; $wsn = [uri]::EscapeDataString($env:TOSCA_REST_WORKSPACE)
$pair = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes("$($env:TOSCA_CLIENT_ID):$($env:TOSCA_CLIENT_SECRET)"))
$h = @{ Authorization = "Basic $pair"; authMode = 'clientCredentials'; Accept = 'application/json' }
function Tosca($path, $method = 'GET', $body) { Invoke-RestMethod -Method $method -Uri "$base/$wsn/$path" -Headers $h -Body $body -ContentType 'application/json' }
```

### 3.2 Endpoints with evidence

| Operation | Call | Evidence |
|-----------|------|----------|
| List workspaces | `GET <base>/GetWorkspaces` | help-page listing + konopski (unverified) |
| Read object | `GET <base>/{ws}/object/{UniqueId}` → `{ TypeName, Attributes:[{Name, Value}], … }` | code (Centreon, Boehringer) |
| Follow an association | `GET <base>/{ws}/object/{id}/association/{AssocName}` → array of objects with `UniqueId` | code (Centreon) |
| TQL search | `GET <base>/{ws}/object/{startId or project}/task/Search?tqlString=<url-encoded TQL>` → array | code (Boehringer, starts at `project`) |
| Check out | `GET <base>/{ws}/object/{id}/task/CheckOut` · `…/task/CheckOutTree` | code (Boehringer) |
| Check in all / update / revert | `GET <base>/{ws}/task/CheckInAll?checkInComment=…` · `…/task/UpdateAll` · `…/task/RevertAll` | code (Boehringer); UpdateAll also in Tricentis KB0014845 |
| Drop task | `GET <base>/{ws}/object/{targetId}/task/AssignOwner?objToDrop={id}` | code (Boehringer) |
| Run a TestEvent | `GET <base>/{ws}/object/{eventId}/task/ExecuteNow` (needs execution tasks enabled) | code (xlr plugin), KB0014845 |
| Attach a file / delete object | `PUT <base>/{ws}/object/{id}?name={file}` (raw bytes) · `DELETE <base>/{ws}/object/{id}` | code (Boehringer) |
| Report download | `GET <base>/{ws}/resource?source=report&UniqueId={id}&reportname={r}&filename={f}` | [doc] 2024.1 changes (docs show it without `{ws}`; client code includes it) |
| Create object | `POST <base>/{ws}/object` · also listed: `GET {ws}/object` | help-page listing only; body format (unverified) |

Pattern [inferred]: `…/task/<Name>` invokes the TCAPI task method of that name on the object, and query parameters carry the method's parameters: `objToDrop`, `checkInComment` and `tqlString` are exactly the TCAPI parameter names (§2.1), and Tricentis states the service works through TCAPI. Case seems tolerated (`CheckOut` vs TCAPI `Checkout`).

### 3.3 Authoring through tasks (all unverified)

If the pattern holds, the TCAPI create methods map to URLs like these. Try them on a scratch folder first and re-read after each call:

```bash
# unverified: plausible calls built from the TCAPI task names; confirm on your server version
H=(-H "Authorization: Basic $(printf '%s:%s' "$TOSCA_CLIENT_ID" "$TOSCA_CLIENT_SECRET" | base64)" -H 'authMode: clientCredentials')
B="$TOSCA_REST_BASE/rest/toscacommander/$TOSCA_REST_WORKSPACE"
curl -s "${H[@]}" "$B/object/$FOLDER_ID/task/CheckOutTree"
curl -s "${H[@]}" "$B/object/$FOLDER_ID/task/CreateTestCase"                          # returns the new object?
curl -s "${H[@]}" "$B/object/$TC_ID/task/CreateXTestStepFromXModule?objToDrop=$MODULE_ID"
curl -s "${H[@]}" "$B/object/$TC_ID/task/CreateTestStepFolderReference?objToDrop=$BLOCK_ID"
curl -s "${H[@]}" "$B/object/$ELFOLDER_ID/task/CreateExecutionList"
curl -s "${H[@]}" "$B/object/$EL_ID/task/CreateExecutionEntry?objToDrop=$TC_ID"
curl -s "${H[@]}" "$B/task/CheckInAll?checkInComment=agent%20build"
```

Setting `Name`, `Value`, `ActionMode`, `Operator`, `DataType` over REST has no verified call: the likely candidate is `PUT <base>/{ws}/object/{id}` with a JSON body mirroring the GET shape (`{"Attributes":[{"Name":"Value","Value":"ACME"}]}`) (unverified; the only confirmed PUT is the file upload). Until confirmed on the target server, **do the value editing with TCAPI or TCShell** (`set Value "…"` after `JumpToNode`) and use REST for search, checkout, check-in and verification reads.

### 3.4 Verify over REST

After every write, `GET …/object/{id}` and compare `Attributes` (`Name`, `ActionMode`, `Value`…), and list children with `…/association/Items` or `…/association/TestStepValues` (association names from TCAPI, unverified over REST). The multi-user state is in the `CheckOutState` attribute (`CheckedIn`, `CheckedOut`…), as Boehringer's client reads it before checking out.

### 3.5 Execution API (runs only)

`https://<server>:<port>/automationobjectservice/api`: `POST /Execution/Enqueue`, `GET /Execution/{id}/Status`, `GET /Execution/{id}/Results` (JUnit), `GET /Execution/{id}/Results/Summary`. Headers `X-Tricentis: OK` and, on HTTPS, `Authorization: Bearer <token>` from `/tua/connect/token` (client credentials). No authoring. [doc]

Sources: [Tosca REST API Service settings](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_connect/connect.htm), [Changes and deprecations 2024.1](https://docs.tricentis.com/tosca-2024.1/en-us/content/upgrade/upgrade_changes.htm), [Server configuration files](https://docs.tricentis.com/tosca-2025.1/en-us/content/upgrade/upgrade_server_configuration_files.htm), [Execution API](https://docs.tricentis.com/tosca-2025.1/en-us/content/continuous_integration/execution_api_integration.htm), [Boehringer-Ingelheim/tosca-service `ToscaRestAPIHandler.java`](https://github.com/Boehringer-Ingelheim/tosca-service) (Apache-2.0), [centreon-plugins `apps/tosca/restapi`](https://github.com/centreon/centreon-plugins) (Apache-2.0), [xebialabs-community/xlr-tosca-plugin](https://github.com/xebialabs-community/xlr-tosca-plugin) (MIT), [OpsHub Tosca connector](https://docs.opshub.com/v7.225/connectors/tricentis-tosca), [konopski/tosca-commander-api](https://github.com/konopski/tosca-commander-api) (WTFPL; its paths omit `/object/` and don't match the other clients, so treat it as unverified).

## 4. Verification, multi-user rules, secrets

- **Re-read every write** (guardrail 4). TCAPI: after `Save()`, re-query with `Search`/`GetTCObject($tc.UniqueId)` and print the tree (`Items` → `TestStepValues` → `Value`/`ActionMode`/`Operator`). Better: validate by exporting and reading the subset offline (`ExportSubset` → `tosca-tsu` step tree). Then run once in a ScratchBook/ExecutionList and fix, one artifact at a time.
- **Multi-user**: `IsSingleUser == $false` → check out (`CheckoutTree` on the smallest folder that covers the change) before creating anything in it; if `ChangesAllowed` stays false, another user holds it: stop and report `LockedBy`, never revoke someone else's checkout. Run `UpdateAll()` before building on a stale workspace. `CheckInAll` / check-in only after the user confirms (guardrail 8). Library checkouts lock the block for everyone: keep them short.
- **Locks**: TCAPI, TCShell, REST and Commander can't share one `.tws`. Close Commander or use a separate clone (`workspace-checkout.md`).
- **Deletes** (`Delete(...)`, `DELETE /object/{id}`) need explicit user confirmation.
- **Secrets**: workspace login and server credentials from env vars (`TOSCA_USER`, `TOSCA_PASSWORD`, `TOSCA_PAT`, `TOSCA_CLIENT_ID`/`_SECRET`) or Windows auth; never echo them, never write them into scripts, `.agents/`, TCP String values or commit history. `Invoke-TcApi.ps1` passes the password via `$env:TOSCA_PASSWORD` to the child host.

## 5. Unknowns (check before relying on them)

1. `OpenWorkspace` 3- vs 4-parameter binding per version, and valid `logLevel` values. (unverified)
2. TSR flow: order of `ToscaServerLogin` → `CreateNewWorkspaceFromServerRepository` → `OpenWorkspace`; `branchName` vs `snapshotName` per version. (unverified)
3. Whether `CreateXTestStepFromXModule` pre-creates all XTestStepValues. (unverified)
4. ExplicitName on XTestStepValue: `Name` property vs `SetAttibuteValue('ExplicitName', …)`. (unverified)
5. Automatic business-parameter references on `CreateTestStepFolderReference`. (unverified)
6. While/Do loop-body folder (`ConditionPassedFolder`?). (unverified)
7. `SetTestConfigurationParameterValue` creating vs only setting a TCP. (unverified)
8. String answers accepted by task overloads (`"Yes"`, `"OK"`…). (unverified)
9. TQL type filter `ReuseableTestStepBlock` / `XModuleAttribute` (class names exist in TCAPI; TQL use inferred). (unverified)
10. REST: create-object body, attribute-update body, `/association/<name>` names, whether every TCAPI task (e.g. `CreateTestCase`) is callable via `…/task/<Name>` and what it returns, `GetWorkspaces`, PAT and Windows auth, default ports, `/rest` vs `/tcrest`. (unverified)
11. REST availability and behaviour before Tosca Server 2024.1 (config file and execution defaults changed then). (unverified)

Found an answer to one of these on a real workspace? Update this file (Tosca product fact) and note the version you verified against.
