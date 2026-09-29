# Tosca test-design patterns (Commander and Cloud)

Proven step shapes to apply when you **build or fix** a test. Each pattern gives the platform-neutral shape first, then how to write it on Commander and on Cloud. The shapes come from real exported workspaces (`tosca-tsu` → `references/tsu-evidence.md`, which has the raw entity detail and enum counts) and from the official rules in [commander-object-model.md](commander-object-model.md) and `toscacloud-cli` → `best-practices.md`.

How to use:

1. Pick the pattern that matches the scenario step, **after** the reuse scan ([reuse-scan.md](reuse-scan.md)). An existing test case or block in the user's workspace beats a pattern from here, because it carries their conventions.
2. Build it with the mechanics of the runtime tier you're actually on. The shapes are written in object/attribute terms (step → module, value → attribute, ActionMode, ExplicitName…), which every tier exposes under the same names:
   - Commander open with MCP (26.1+): tasks and attributes, `commander-mcp` → `author-automated-test-case.md`.
   - Commander/Tosca Server without MCP (older version, Commander closed, CI, remote server): **TCAPI** (the .NET DLLs) or the **Tosca REST API**, see [commander-authoring-apis.md](commander-authoring-apis.md); TCShell for batch tasks (`cli-api-commander`).
   - Cloud: JSON (`toscacloud-cli`: `web-automation.md`, `sap-automation.md`, `blocks.md`, `standard-modules.md`) or the official `tosca-authoring-automated-testcase` path.
3. Standard-module names below are the Commander *Standard subset* names. On Cloud, find the equivalent in the engine packages (`/builder/packages`, `standard-modules.md`). Never hard-code a module or attribute ID you haven't read on the target.

Notation used in the shapes:

```
STEP 'name' -> Module                      one test step on that module
    - Attribute = 'value'  [ActionMode]    one step value
      - Child   = 'value'  [ActionMode]    nested value (child attribute)
    name='x'                               ExplicitName (Commander) / explicitName (Cloud)
    .Prop                                  ActionProperty (Visible, Exists, Count, Index, RowNumber…)
CALL 'Block'                               reusable block reference
```

Platform field names at a glance: Commander `ActionMode` / `ActionProperty` / `Operator` / `ExplicitName` / `DataType` on XTestStepValue; Cloud `actionMode` / `actionProperty` / `operator` / `explicitName` / `dataType` on `testStepValues[]`. Numeric codes appear only in `.tsu` exports (`tosca-tsu`).

---

## P1. Test case skeleton: Precondition → Process → Verification → Postcondition, with a recovery scenario

Use for every UI test case.

```
TestCase 'Create order - standard customer'
  Precondition   CALL 'Open app'        (start browser / program with {CP[URL]}, wait for window)
  Process        business steps only
  Verification   the checks that prove the outcome (+ evidence screenshot if the team takes one)
  Postcondition  CALL 'Close app'       (close browser / kill process, short settle wait)
  Recovery / CleanUp scenario: the same teardown, so an aborted run still cleans up
```

- **Commander:** folders are `TestStepFolder`s. Opening and closing usually live in a Library block (`TBox Start Program` with `Path={CP[CHROME_PATH]}` and repeated `Argument` children under a `{NULL}` Select container; `TBox Window Operation` `Operation=Wait On Open`; teardown via Html `CloseBrowser` or `TBox Close Program`). Recovery/CleanUp scenarios sit in a folder's recovery scenario collection. Details: [commander-object-model.md](commander-object-model.md) §4, §7, §10.
- **Cloud:** `TestStepFolderV2` ×4, `OpenUrl` / `CloseBrowser` standard modules, `recoveryScenarioCollection` on the case: `toscacloud-cli` → `web-automation.md` "4-folder test case structure", "Recovery / CleanUp scenario".
- Many real Commander workspaces put steps straight under the test case with no folders. **Follow the team's convention** when the reuse scan shows one (record it in `.agents/project.md`); otherwise use the four folders.
- Environment values (URL, browser path, artifact folder) are **test configuration parameters** read with `{CP[x]}`, defined on the project / folder / configuration, not typed into steps.

## P2. Buffer → reuse chaining (UI ↔ API ↔ DB)

Use whenever a value produced in one step (generated ID, token, order number) is needed later.

```
STEP 'Create response' -> Create Order (response)
    - id           = 'OrderId'                 [Buffer]     value = buffer NAME
STEP 'Status bar'   -> Main Window
    - StatusBar    = 'Order {XB[OrderNo]} saved' [Verify]   verify literal text AND capture the variable part
STEP 'Open order'   -> OpenUrl
    - Url          = '{CP[URL]}/orders/{B[OrderId]}/view' [Input]
```

- `[Buffer]` takes the **buffer name** as its value, not the content. Read it with `{B[name]}`.
- `{XB[name]}` only works inside a **Verify** value. Use it when the value sits inside surrounding text.
- Buffers are scoped to the executing test case and cross reusable-block boundaries. They don't carry over to the next test case, so test cases stay self-contained.
- Cloud: in a row `explicitName`, a buffer needs a `$` prefix: `${B[RowNum]}` (`toscacloud-cli` SKILL.md caveats).

## P3. Test data kitchen: prepare values with Set Buffer and expressions

Use to compute dates, unique names and derived strings **before** the business steps, instead of hard-coding them.

```
STEP 'Prepare data' -> TBox Set Buffer
    - <Buffername> = '50'                                   [Input] name='Age'
    - <Buffername> = '{DATE[][-{B[Age]}y][MM/dd/yyyy]}'      [Input] name='DOB'
    - <Buffername> = '{RANDOMTEXT[8]}@example.test'          [Input] name='Email'
    - <Buffername> = '{DATETIME[][][s]}'                     [Input] name='Stamp'
    - <Buffername> = '{REGEX["(?<No>\d*)\s(?<Street>.*$)"]}' [Verify] name='Address'   → buffers No, Street
    - <Buffername> = '{XB[Zip]}-*'                            [Verify] name='Zip'       → keeps part before '-'
```

- **Commander:** `TBox Set Buffer` has one placeholder attribute `<Buffername>`. The buffer name goes in **ExplicitName**, the content in Value. `TBox Partial Buffer` cuts by position. A Verify with a named-group `{REGEX}` creates one buffer per group.
- **Cloud:** use the Buffer operations standard module (`web-automation.md` "Buffer write step"). `{CALC}` and `{SCRIPT}` aren't available on Cloud; use `{MATH}` and the string operations instead (`toscacloud-cli` SKILL.md "Dynamic expressions"; Cloud column of [commander-object-model.md](commander-object-model.md) §6).
- Prefer generated unique data (`{RANDOMTEXT}`, a timestamp) for records the test creates, so reruns don't collide.

## P4. Pick one row / list item by content (Constraint), then act on it

Use for tables, grids, JSON arrays and SAP tables whenever the row position isn't fixed. **Don't** loop over rows.

```
STEP 'Find order row' -> Orders View
    - Orders table   = '{NULL}'          [Select]
      - <Row>        = '{NULL}'          [Select]      (no fixed row name)
        - <Cell> name='Customer' = 'ACME'   [Constraint]  pick the row where Customer = ACME
        - <Cell> name='Status'   = 'Open'   [Verify]      check a sibling in that same row
        - <Cell> name='ID'       = 'RowId'  [Buffer]      or capture it

STEP 'List response' -> Query Response  (API)
    - totalSize.Count = '1'     [Verify]    count check
    - records         = '{NULL}' [Select]
      - item          = '{NULL}' [Select]   .Index = 'Last' for position, or:
        - Status      = 'Open'    [Constraint]
        - Id          = 'PickedId' [Buffer]
```

- Combine constraints until **exactly one** row matches. `#n` picks the n-th match; `ResultCount` tells you how many matched.
- Fixed positions use row/column selectors in the name: `$1`, `$last`, `$header`, `#2`, or a header text for columns.
- Changing Constraint to Verify turns "find the row where…" into "every row must…". Pick deliberately.
- Cloud SAP table shape and the row-anchored verify: `toscacloud-cli` → `sap-automation.md` (Constraint idiom). Web: `web-automation.md` action modes.

## P5. API test: request/response pair, token block, chained IDs

Use for REST/SOAP steps, API-driven test data setup, and hybrid tests where an API call creates data the UI then checks.

```
Block 'Get auth token'
  STEP 'Token request'  -> GetToken (request)     client_id = '{CP[Client_ID]}'  [Insert] …
  STEP 'Token response' -> GetToken (response)    access_token = 'Token'         [Buffer]

TestCase 'Create record via API'
  CALL 'Get auth token'
  STEP 'Create request'  -> Create (request)
      - Endpoint      = '{CP[API_Endpoint]}/Record' [Insert]
      - Authorization = 'Bearer {B[Token]}'         [Insert]
      - Name          = '{B[LastName]}'             [Insert]
  STEP 'Create response' -> Create (response)
      - StatusCode = '201 Created' [Verify]
      - id         = 'NewId'       [Buffer]
  STEP 'Get request'  -> GetById (request)     RecordId = '{B[NewId]}' [Insert]  (Resource part)
  STEP 'Get response' -> GetById (response)    Id = '{B[NewId]}'       [Verify]
```

- Request values use **Insert**; response values use Verify / Buffer. Request and response are separate modules scanned as a pair (API Scan).
- Put authentication in one block and call it first in every API test.
- Secrets (client secret, passwords) come from TCPs or encrypted values, never literals.
- Commander: API modules come from API Scan (`create_api_module` in `commander-mcp`); [commander-object-model.md](commander-object-model.md) §3.6. Cloud: API messages / API execution; check the reuse scan for existing API modules before scanning.

## P6. Database check of what the test created

Use to prove a UI or API action actually persisted (end-to-end check).

```
STEP 'Verify in DB' -> DB Expert module (standard)
    - Open Connection   = '{NULL}'  (container)
      - Connection name   = 'AppDb'          [Input]
      - Connection string = '{CP[DB_Conn]}'  [Input]     password-type: keep it in a TCP
    - SQL Statement     = 'SELECT … WHERE Id = ''{B[NewId]}''' [Input]
    - Result Table      = '{NULL}'  (container)
      - <Col> name='Status' = '{NULL}' [Select]
        - <Cell> name='#2'  = 'Open'   [Verify]      #2 = first data row
    - Close connection  = 'True'   [Input]
```

- Put the buffered key from P2 into the SQL; verify columns by header name.
- `{EXPORTTOCSV[file]}` on the result table dumps the query result to a file (for example to load TDS, P8).
- Cloud: the Database standard package (`standard-modules.md`). Discover its attribute tree before building.

## P7. Optional element: If with a Verify condition (the only accepted If)

Use only for things that **may or may not** appear: cookie or consent banners, "session expired" pop-ups, leftover browser tabs before cleanup.

```
If
  Condition   STEP 'Banner shown?' -> Cookie Banner   Accept.Visible = 'True' [Verify]
  Then        STEP 'Accept'        -> Cookie Banner   Accept = '{CLICK}'      [Input]
```

- A failing condition Verify only selects the branch; it doesn't fail the test. A wildcard Verify (`*-*`) is the "contains" idiom.
- **Never** wrap a business Verify in an If to get past a failure: that's defect masking (`toscacloud-cli` SKILL.md). Loops: prefer `Repetition` or Constraint (P4) over While/Do.
- Commander: `TestCaseControlFlowItem` with Condition / Then / Else folders ([commander-object-model.md](commander-object-model.md) §9). Cloud: `ControlFlowItemV2` (`web-automation.md` "Conditional steps", VJS probe variant for tab cleanup). On Cloud, narrow the module-level `Title`/`Url` first, or the condition hard-fails instead of evaluating false.

## P8. Data-driven: TCPs, TestSheets / templates, TDS

Choose by where the data comes from:

| Need | Use |
|------|-----|
| Environment values shared by many tests (URL, browser, endpoint) | Test configuration parameters, `{CP[x]}`, set high in the tree |
| Same flow over many data combinations | Commander: TestCase-Design TestSheet + template + instances ([commander-object-model.md](commander-object-model.md) §11). Cloud: data sets + parameters (no template instances; `commander-vs-cloud.md`) |
| Data created during or between runs (orders to pay, users to reuse) | TDS / TDM, with a `Status` column so consumed rows aren't reused (`best-practices.md`) |

```
STEP 'Import to TDS' -> TestData - Import items (standard)
    - Existing or new TDS type = 'OrdersToPay' [Input]
    - Import format = 'CSV' [Input];  Filename = '{CP[csvFile]}' [Input]
```

TDS connection settings belong in the configuration's TCPs, not in the test case. Consuming modules (*Find & provide*) filter rows by Constraint.

## P9. Module design: locators vs steering vs configuration

Use when you create or fix a module.

| Parameter kind | Holds | Examples |
|----------------|-------|----------|
| Identification (TechnicalId) | How to find the control uniquely | Html `Tag`, `Id`, `Name`, `InnerText`, `Title`, `ClassName`, `HREF`; SAP `RelativeId`; API `Path` + `PathType` (JsonPath, Header, Resource, UrlParam, Endpoint) |
| Steering | Runtime behaviour | `FireEvent`, `DecisiveColumns`, `HeaderRow`, `IgnoreInvisibleTableContent`, `UserSimulation`, `WaitBefore`/`WaitAfter` |
| Configuration | Engine and search setup | `Engine` (Html, SapEngine, API, Framework, Vision AI…), `BusinessAssociation`, `ExplicitName`, `SpecialExecutionTask` |

- The module root identifies the window/page (Html `Title`/`Url`, SAP transaction/program/screen); attributes identify controls within it.
- Tables get placeholder children `<Row>`, `<Col>`, `<Cell>` whose real target comes from ExplicitName in the step (P4).
- The same screen can have two modules (XScan Html + Vision AI); a test may use each where it's strongest.
- Design rules (size, attribute order, naming, uniqueness proof): [commander-object-model.md](commander-object-model.md) §3.5, `web-automation.md` / `sap-automation.md`, `web-exploration`, `sap-gui-exploration`.

## P10. Execution grouping

- Commander: ExecutionList → ExecutionEntries (one per test case, `Repetitions`), grouped as Smoke / Regression / Archive. CI can pick lists by a custom property such as `TestType`. §13 of [commander-object-model.md](commander-object-model.md).
- Cloud: playlists (`tosca-create-playlist`, `tosca-run`).

---

Found a pattern that worked on this project but isn't generic? Record it in `.agents/patterns/` (`tosca-project-memory`). Found a Tosca product fact that is wrong or missing here? Fix this file.
