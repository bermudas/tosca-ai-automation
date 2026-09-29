# .tsu evidence: how the patterns look inside real exports

The **build recipes** derived from these samples are in `tosca-platform-guide` → `references/test-patterns.md` (both platforms). This file keeps what's specific to reading `.tsu` files: entity-level details, blob contents and the observed enum values with their counts. Read it together with the object model in `../SKILL.md`.

Evidence base: 14 public **Commander** exports (GUID surrogates; see "Sources"). No Cloud (ULID) export was in the set. Values in this file are neutral placeholders, not copies.

`tsu_inspect.py tree` notation: `STEP 'name' -> module 'M'` is an `XTestStep` whose `Module` assoc points at `M`. Indented `- Attr = 'value' [Mode]` lines are `XTestStepValue`s (`ModuleAttribute` → the `XModuleAttribute` named `Attr`, `[Mode]` = decoded `ActionMode`). Deeper indentation = `SubValues`. `name=` is `ExplicitName`, `.Prop` is `ActionProperty`.

## Entity details per pattern

### API modules (test-patterns P5)

- **`ApiModule`** (not `XModule`), `InterfaceType=0`. Module `XParam`s (ParamType 8): `Engine=API`, `Executor=ApiExecutor`. An empty `ApiParameter` entity usually sits in `Properties` as well.
- The **`TCProperties` blob** (gzip XML, UTF-16 in Commander) holds the HTTP metadata: `IsRequest`, `CorrelationId` (the same GUID on request and response, which pairs them), `Method`, `Resource`, `Version`, `Schema`, `InactiveNodes=Remove`, `ListSupport=Dynamic`. Responses also carry `StatusCode` (`200 OK`), `ResponseTime` and `Direction=In`. `tsu_inspect.py modules` prints these as `api: {...}`.
- **`ExplicitConnection` / `Headers`** are plain base64, but in every sample (Tosca 14–15 era) they decode to **.NET BinaryFormatter** (`AAEAAAD/////…`) lists of `KeyValuePair<string,string>`, **not** JSON. Visible strings include `Name=<explicit>`, `TransportType=Http`, `Endpoint=<url>`. `Payload` is base64 UTF-8 (the JSON body, or the captured response body on the response module). Response `Headers` can contain captured cookies, so treat them as sensitive.
- **Request attributes** carry `DefaultActionMode=515` (Insert). Response container nodes (JSON objects/arrays) default to `1`, leaves to `69` (Verify).
- **Attribute locators**: `XParam` ParamType 5 `PathType` ∈ {`JsonPath`, `Header`, `Resource`, `UrlParam`, `Endpoint`} plus `Path` (for example `records[*].Id`, `Authorization[0]`, `name;Query;0`). ParamType 8 `ExplicitName=True` allows renamed attributes.
- **API Scan folder exports** (no test cases) hold hundreds of `ApiModule`s plus `ApiMessage` (`Direction` 0/1, `MediaType`, `MessageName` = OpenAPI path such as `paths['/api/x'].post.parameters[0].schema`) and `ApiSchema` (`Content` blob, `SchemaType` 0/1, `HashCode`), attached to folders via `ExtendableObject`. These are scan-time definitions, not executable steps.

### Constraint / list items (P4)

- **519 = Constraint** on child values of a list item; one sample keeps a disabled copy of the same step with `69` (Verify) instead. 519 is also the `DefaultActionMode` on the standard *TestData – Find & provide* modules.
- **517 = Select** on `{NULL}` containers; `ActionProperty=Index` with `Last` picks a position.
- **`1`** appears only on `{NULL}` container values (JSON objects, DB `Open Connection` / `Result Table`) that group children. Official name unproven; read it as "navigate into / no action".
- `ActionProperty=Count` with **`Operator=6`** (probably ≥, inferred); plain Verifies carry `Operator=1`.

### Set Buffer and expressions (P3)

- `TBox Set Buffer`: module XParams (type 8) `Engine=Framework`, `SpecialExecutionTask=SetBuffer`; single attribute `<Buffername>` with `Parameter=True`, `ExplicitName=True`. The buffer name is the value's `ExplicitName`.
- `TBox Partial Buffer`: `Buffer`, `Value`, `Start`, `End` (`Start`/`End` DataType 2).
- Tokens seen: `{B[x]}` (74 values, case-insensitive; `{b[x]}` occurs), `{CP[x]}`, `{NULL}`, `{DATE}`, `{DATETIME}`, `{CALC}`, `{REGEX}`, `{RANDOMREGEX}`, `{RANDOMTEXT}`, `{XB}`, `{EXPORTTOCSV[file]}`, `{Click}`, wildcards `*`. **Not seen:** `{PL[]}`, `{XL[]}`, `{RND[]}`, `{TDS[]}`, `{MATH[]}`.

### If control flow (P7)

- `TestCaseControlFlowItem` `StatementType=1` (If), `MaximumRepetitions` empty. Folders: `TestCaseControlFlowFolder` `Condition` (StatementType 0), `Then` (1). Else (2 per FORMAT_GUIDE) and While/Do loops were not seen.
- `TestStepFolder` names are free-form. In 12 of 12 sample files with test cases, steps and block calls hang directly off `TestCase.Items`; only one sample used `TestStepFolder`s at all.

### DB Expert and TDS (P6, P8)

- DB Expert module: `XModule BusinessType=DatabaseConnection`. `Connection string` has `DefaultDataType=4` (password-type), so real connection strings may appear encrypted. Tables use placeholder attributes `<Col>` / `<Cell>` / `<Row>`, targeted via `ExplicitName` (header text, `#n`, `$last` …).
- TDS connection settings (`TestDataEndpoint`, `TestDataRepository`) live in **`TCConfiguration.TestConfigurationParameters`** blobs.
- No `TestSheet` / TestCase-Design entities appeared in any sample.

### Pre/Postcondition blocks and recovery (P1)

- Standard-module identity lives in module XParams (type 8): `Engine=Framework`, `SpecialExecutionTask=OpenUrl|SetBuffer|…`. Folder paths `Modules/Standard modules/TBox Automation Tools/...` and `/TBox XEngines/...`.
- Repeating child attributes (`Argument`, `Cardinality 0-N`) sit under a `{NULL}` **Select** container, one `SubValue` per occurrence.
- Block calls (`TestStepFolderReference`) had **no `ParameterLayerReference`** in any sample, so business parameters weren't observed.
- `TCFolder` → `OwnedRecoveryScenarioCollection` → `RecoveryScenario` (`ScenarioType=1`, `RetryLevel=0` here, which differs from FORMAT_GUIDE) → `XTestStep`s with `ParentFolder` = the scenario.

### Modules: Html and Vision AI (P9)

```
XModule 'Orders View'                     BusinessType=HtmlDocument  InterfaceType=1
  XParam Engine=Html (8)   Title='App - Orders View' (5)   ControlFramework=None (2)
  - 'Search'        TextBox  Tag=INPUT (5) Type=search (5) Visible=True (4) FireEvent=change (2) BusinessAssociation=Descendants (8)
  - 'orders_table'  Table    Id=orders_table (5) Tag=TABLE (5) DecisiveColumns=* (2) HeaderRow=1 (2)
      - '<Row>'  Row     ExplicitName='$1;$<n>;$last;$header;…' (8)  BusinessAssociation=Rows (8)
        - '<Cell>' Cell  ExplicitName='$1;…;ID;Plan Name;…' (8)       BusinessAssociation=Cells (8)

XModule 'Orders View (Vision AI)'         BusinessType=Window  InterfaceType=1
  XParam Engine='Vision AI' (8)  Caption='App - Orders View - Google Chrome' (7)
  - 'Search:'  VisionAIControl  ControlType=Input (5)  Label='Search:' (5)
```

(number) = `XParam.ParamType`. Salesforce-scanned modules add `SalesforceScannerId` (2), `ApiKey`/`Container` (4) and `TCObjectProperty` entities.

### Execution lists, TCPs, legacy classes (P10)

- `TCFolder` → `ExecutionList` (`TCProperties{TestType=…}`, `IsMandate`, `IncludeForAccumulation`) → `Items` → `ExecutionEntry{Repetitions}` (`TestCase` assoc) plus an empty `ExecutionLog`.
- TCPs appear as `TestConfigurationParameters` blobs on `TCProject`, `TCFolder`, `TCConfiguration` and `TestCase`. Configurations can contain **plaintext client secrets and passwords**: never paste them.
- Full-workspace exports also contain `TCUser` (`EncryptedPassword`), `TCUserGroup`, `ReportDefinition` / `DataSetDefinition` (TQL `Constraint`), and legacy classic modules: `Module` → `ModuleAttribute` → `ObjectControlSimple`, `ObjectMap` → `ObjectMapParams{Label=KeyWord}`.

## Observed enum values (14 files; "n / f" = occurrences / files)

| Field | Value | Meaning (evidence) | n / f |
|-------|-------|--------------------|-------|
| `XTestStepValue.ActionMode` | 37 | Input: TBox params, text entry, `X`/`{Click}` | 290 / 11 |
| | 69 | Verify: response fields, `.Visible`, `.Exists`, regex/wildcard checks | 112 / 9 |
| | 515 | Insert: every API request value; `DefaultActionMode` of request attrs | 46 / 3 |
| | 165 | Buffer: Value = buffer name | 41 / 4 |
| | 517 | Select: `{NULL}` containers, list `Index` | 26 / 8 |
| | 1 | container pass-through on `{NULL}` (default for JSON/DB containers) | 16 / 7 |
| | 519 | Constraint: list-item filter; default on TDS *Find & provide* attrs | 4 / 2 (+1 as default) |
| | 101 | WaitOn | not seen here |
| `XModuleAttribute.DefaultActionMode` | 0 | unset (TBox XML/JSON example modules) | 338 / 3 |
| `XTestStepValue.Operator` | 0 | none/plain (Input, Buffer, Insert) | 355 / 12 |
| | 1 | equals (all plain Verifies, `{NULL}` containers) | 177 / 11 |
| | 6 | comparison with `.Count` (probably ≥; inferred) | 3 / 2 |
| `XTestStepValue.DataType` / `DefaultDataType` | 0 | String | 497 / 12 |
| | 2 | Numeric (Duration, Start/End, totalSize) | 22 / 5 |
| | 3 | **Boolean** (`True` values: Close connection, success, done) | 13 / 5 |
| | 4 | **Password** / encrypted (Password, Connection string) | 3 / 1 |
| `XParam.ParamType` | 8 | configuration (Engine, SpecialExecutionTask, BusinessAssociation, ExplicitName, Parameter) | 3125 / 14 |
| | 5 | technical ID / locator (Tag, Id, InnerText, Title, RelativeId, API Path/PathType) | 1071 / 9 |
| | 2 | steering (FireEvent, DecisiveColumns, HeaderRow, UserSimulation, UseWildcards…) | 148 / 7 |
| | 4 | extra identification/info (Visible, Caption, ApiKey, Container, Adapter, DefaultName) | 87 / 4 |
| | 7 | window Caption (Vision AI), ContextMenu (SAP) | 10 / 3 |
| | 6 | ActionCommand (SAP) | 4 / 1 |
| `TestCaseControlFlowItem.StatementType` | 1 | If | 2 / 2 (same block) |
| `TestCaseControlFlowFolder.StatementType` | 0 / 1 | Condition / Then | 2 / 2 |
| `XModuleAttribute.Cardinality` | `0-1`, `1`, `0-N`/`0-n`, `1-N`/`1-n`, `0-3` | case varies | |
| `XModuleAttribute.InterfaceType` | 2147483647 / 1 | generic / GUI | 1521 / 99 |
| `XModule.InterfaceType` | 0 / 1 | non-GUI (TBox, API, DB) / GUI | 284 / 62 |
| `TestCase.TestCaseWorkState` | 0 / 2 | | 27 / 20 |
| `RecoveryScenario` | ScenarioType=1, RetryLevel=0 | | 1 / 1 |

XModule `BusinessType` values seen: `Window`, `HtmlDocument`, `JsonDocument`, `XmlDocument`, `DatabaseConnection`, `ExcelEngine`, `TextStreamManipulator`, `MenuItem`, `String`. Attribute `BusinessType` values seen: `Button`, `TextBox`, `Link`, `Label`, `Table`/`Row`/`Column`/`Cell`, `JsonObject`/`JsonArray`/`JsonValue`, `XmlElement`/`XmlAttribute`, `VisionAIControl`, `SapGuiStatusbar`, `TreeNode`, `MenuItem`, `RadioButton`, `GenericGUI`.

The ActionMode bit pattern fits the codes (1 base; 4 on every read/select mode; 32 Input; 64 Verify; 128 Buffer; 512 container/API family, with 2 marking Insert/Constraint), but that's an observation, not documentation.

## Sources

- [fillegar/tosca-subsets](https://github.com/fillegar/tosca-subsets): 12 subsets (API/SFDC, DB Expert, TDS, REGEX/date helpers, Vision AI, TBox). No license, so only reduced sketches appear here.
- [Boehringer-Ingelheim/toscaci](https://github.com/Boehringer-Ingelheim/toscaci) `e2e/src/tosca/subsets.tsu` (Apache-2.0): full sample workspace with execution lists, recovery scenario, Pre/Postcondition blocks and the standard-module library.
- [zondor/awesome-subsets](https://github.com/zondor/awesome-subsets): Salesforce Html modules. No license.
- [bjorn-ali-goransson/Tosca-TSU-Format](https://github.com/bjorn-ali-goransson/Tosca-TSU-Format) `FORMAT_GUIDE.md`: format reference used for cross-checking. No license; contradictions are noted in SKILL.md.
- [raviacn95/tosca-playwright-migration](https://github.com/raviacn95/tosca-playwright-migration) (MIT): TBox module semantics. Its ActionMode map (69 = WaitOn, 101 = Constraint, 519 = Insert) contradicts the evidence above.
