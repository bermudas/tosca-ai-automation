# .tsu evidence: how the patterns look inside real exports

The **build recipes** derived from these samples are in `tosca-platform-guide` → `references/test-patterns.md` (both platforms). This file keeps what's specific to reading `.tsu` files: entity-level details, blob contents and the observed enum values with their counts. Read it together with the object model in `../SKILL.md`.

Evidence base: **18 exports**: 14 public Commander exports (see "Sources") plus 4 private ones (3 Commander, 1 **Cloud**, the first Cloud sample). The object graph and association map built from all 18 is in [tsu-schema.md](tsu-schema.md). Values in this file are neutral placeholders, not copies; nothing from the private exports is quoted.

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
- Tokens seen: `{B[x]}` (74 values, case-insensitive; `{b[x]}` occurs), `{CP[x]}`, `{NULL}`, `{DATE}`, `{DATETIME}`, `{CALC}`, `{REGEX}`, `{RANDOMREGEX}`, `{RANDOMTEXT}`, `{XB}`, `{EXPORTTOCSV[file]}`, `{Click}`, wildcards `*`. The private exports add `{PL[x]}` (81), `{XL[x]}` (165, templates), `{SENDKEYS}`, `{STRINGREPLACE}`, `{TRIM}`, `{RND}`, `{KEYPRESS}`/`{KEYDOWN}`/`{KEYUP}`, `{TEXTINPUT}`, `{DOUBLECLICK}`, `{CLEAR}`. **Not seen anywhere:** `{TDS[]}`, `{MATH[]}`.

### Business parameters (P11)

Not in any public export, but present in all 4 private ones (18 blocks with a `ParameterLayer`, 77 `Parameter`s, 536 `ParameterReference`s over 114 calls).

```
ReuseableTestStepBlock 'Login'
  ParameterLayer 'Business Parameters' → Parameter URL, Parameter User, Parameter Password
  STEP 'Open' -> OpenUrl             Url      = '{PL[URL]}'       [Input]
  STEP 'Log in' -> Login Page        User     = '{PL[User]}'      [Input]
                                     Password = '{PL[Password]}'  [Input]
TestCase …
  CALL 'Login'   ParameterLayerReference 'Business Parameters'
                   ParameterReference(URL)      = '{CP[URL]}'
                   ParameterReference(User)     = '{CP[UserName]}'
                   ParameterReference(Password) = '{CP[UserPassword]}'
```

- `{PL[x]}` is used as the **whole value** in Input (48) and Insert (27) values, and embedded inside Verify strings (5).
- Call-site values: `{CP[x]}` for environment and credentials (the most common), `{B[x]}` for buffers from earlier steps, literals, and `{XL[Sheet.Attr]}` in templates.
- A call only stores references for the parameters it sets; `Parameter.ValueSelectionGroup` was empty in all samples.

### If control flow (P7)

- `TestCaseControlFlowItem` `StatementType`: 1 = If (24), **2 = loop** with Condition + Loop folders and `MaximumRepetitions` 20 or 5 (3). Folder `StatementType`: 0 = Condition, 1 = Then / Loop, 2 = Else (13). Do loops weren't seen.
- Folder names are free text ("Else do nothing", "First try / Second try"). Trust `StatementType`, not the name. Using If/Else as a retry ("First try" / "Second try") shows up once; it's a smell, not a pattern to copy.
- `TestStepFolder` names are free-form. In 12 of 12 sample files with test cases, steps and block calls hang directly off `TestCase.Items`; only one sample used `TestStepFolder`s at all.

### DB Expert and TDS (P6, P8)

- DB Expert module: `XModule BusinessType=DatabaseConnection`. `Connection string` has `DefaultDataType=4` (password-type), so real connection strings may appear encrypted. Tables use placeholder attributes `<Col>` / `<Cell>` / `<Row>`, targeted via `ExplicitName` (header text, `#n`, `$last` …).
- TDS connection settings (`TestDataEndpoint`, `TestDataRepository`) live in **`TCConfiguration.TestConfigurationParameters`** blobs.
- No `TestSheet` in the public samples. The private Cloud export has full TestCase-Design (14 TestSheets, 16 templates with instances); the object chain is in [tsu-schema.md](tsu-schema.md) §2.6.

### Pre/Postcondition blocks and recovery (P1)

- Standard-module identity lives in module XParams (type 8): `Engine=Framework`, `SpecialExecutionTask=OpenUrl|SetBuffer|…`. Folder paths `Modules/Standard modules/TBox Automation Tools/...` and `/TBox XEngines/...`.
- Repeating child attributes (`Argument`, `Cardinality 0-N`) sit under a `{NULL}` **Select** container, one `SubValue` per occurrence.
- Block calls (`TestStepFolderReference`) had **no `ParameterLayerReference`** in any sample, so business parameters weren't observed.
- `TCFolder` → `OwnedRecoveryScenarioCollection` → `RecoveryScenario` (`ScenarioType=1`, `RetryLevel=0` here, which differs from FORMAT_GUIDE) → `XTestStep`s with `ParentFolder` = the scenario.

### Waits (WaitOn, 101)

Seen 118 times in 2 private exports, never in the public ones: `ActionProperty` `Exists` (74), `Visible` (38), `InnerText` (6), always with `True` or an expected text. That's the dynamic-wait idiom: wait for the element or text instead of `TBox Wait`.

### Locators and self-healing in current XScan exports (P9)

- XScan exposes **any HTML attribute** as an identification parameter named `attributes_<attr>` (e.g. `attributes_data-test-id`, `attributes_class`, `attributes_href`, framework attributes such as `attributes_ng-reflect-…`), and CSS values as `style_<property>`. `OuterHtml` / `InnerHtml` also appear. Prefer a stable `attributes_data-test-id` over `ClassName` when it exists.
- `SelfHealingData` (ParamType 2, on almost every Html attribute: 1,368 in the private exports) is .NET-typed JSON: `TcSelfHealingData` → `HealingParameters.$values[]` of `TcSelfHealingProperty {Name, Surrogate, ParamType, Value, Weight}`. It holds weighted alternative locator properties used when the primary TechnicalIds stop matching. Read it; never hand-edit it.
- ParamType **7** = `XPath` (28), **6** = `innerText` (lower-case, 4), **4** = extra properties (`Visible`, `Focused`, `Url`, `DefaultName`). Configuration params seen in addition: `ConstraintIndex`, `IdentifyingContext` (Cloud).
- UIA engine modules (`Engine=UIA`) appear for Windows dialogs next to Html modules.

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

## Observed enum values (18 files)

| Field | Value | Meaning (evidence) | n |
|-------|-------|--------------------|---|
| `XTestStepValue.ActionMode` | 37 | Input: TBox params, text entry, `X`/`{Click}` | 1,304 |
| | 69 | Verify: response fields, `.Visible`, `.Exists`, regex/wildcard checks | 645 |
| | 1 | container pass-through on `{NULL}` (default for JSON/DB containers) | 350 |
| | 517 | Select: `{NULL}` containers, list `Index` | 169 |
| | 101 | **WaitOn** (`Exists` / `Visible` / `InnerText`), 2 files | 118 |
| | 515 | Insert: every API request value; `DefaultActionMode` of request attrs | 110 |
| | 165 | Buffer: Value = buffer name | 80 |
| | 519 | Constraint: list-item filter; default on TDS *Find & provide* attrs | 4 (+1 as default) |
| `XModuleAttribute.DefaultActionMode` | 0 | unset (TBox XML/JSON example modules) | 338 |
| `XTestStepValue.Operator` | 0 | none/plain (Input, Buffer, Insert) | 1,683 |
| | 1 | equals (all plain Verifies, `{NULL}` containers) | 1,093 |
| | 2 | once, on a Verify `.Exists`. `NotEquals` if the TCAPI enum order (None, Equals, NotEquals, Greater, GreaterOrEqual, Smaller, LessOrEqual) maps to 0–6 *(inferred)* | 1 |
| | 6 | with `.Count`. By that enum order it's `LessOrEqual`; earlier notes guessed ≥. Unresolved: check on a real object | 3 |
| `DataType` / `DefaultDataType` | 0 | String | 2,691 |
| | 2 | Numeric (Duration, Start/End, totalSize) | 68 |
| | 3 | **Boolean** (`True` values: Close connection, success, done) | 13 |
| | 4 | **Password** / encrypted (Password, Connection string) | 6 |
| | 6 | on a `Keys` value (`{ENTER}`). `RawString` if the TCAPI `ModuleAttributeDataType` order (String, Date, Numeric, Boolean, Password, Secret, RawString) maps to 0–6, which fits 2/3/4 above *(inferred)* | 2 |
| `XParam.ParamType` | 8 | configuration (Engine, SpecialExecutionTask, BusinessAssociation, ExplicitName, Parameter, ConstraintIndex) | 6,363 |
| | 5 | technical ID / locator (Tag, Id, InnerText, Title, `attributes_*`, `style_*`, RelativeId, API Path/PathType) | 3,750 |
| | 2 | steering (SelfHealingData, FireEvent, DecisiveColumns, HeaderRow, UserSimulation, WaitBefore/After…) | 1,807 |
| | 4 | extra properties (Visible, Focused, Url, Caption, ApiKey, DefaultName) | 92 |
| | 7 | XPath; window Caption (Vision AI); ContextMenu (SAP) | 90 |
| | 6 | innerText (Html), ActionCommand (SAP) | 12 |
| `TestCaseControlFlowItem.StatementType` | 1 / 2 | If / loop (Condition + Loop, `MaximumRepetitions`) | 24 / 3 |
| `TestCaseControlFlowFolder.StatementType` | 0 / 1 / 2 | Condition / Then or Loop / Else | 27 / 27 / 13 |
| `XModuleAttribute.Cardinality` | `0-1`, `1`, `0-N`/`0-n`, `1-N`/`1-n`, `0-3` | case varies | |
| `XModuleAttribute.InterfaceType` | 2147483647 / 1 | generic / GUI | 1,779 / 1,419 |
| `XModule.InterfaceType` | 0 / 1 | non-GUI (TBox, API, DB) / GUI | 308 / 132 |
| `XModule.IsAbstract` | 1 | generalization module (with `Specializations`) | 10 |
| `TestCase.TestCaseWorkState` | 0 / 2 | | 44 / 60 |
| `RecoveryScenario.ScenarioType` | 0 / 1 | Recovery / CleanUp *(by name)*, `RetryLevel=0` | 1 / 2 |
| `TDAttribute.BusinessRelevant` | 1 / 0 | test data / structure | 260 / 14 |

XModule `BusinessType` values seen: `Window`, `HtmlDocument`, `JsonDocument`, `XmlDocument`, `DatabaseConnection`, `ExcelEngine`, `TextStreamManipulator`, `MenuItem`, `String`. Attribute `BusinessType` values seen: `Button`, `TextBox`, `Link`, `Label`, `Table`/`Row`/`Column`/`Cell`, `JsonObject`/`JsonArray`/`JsonValue`, `XmlElement`/`XmlAttribute`, `VisionAIControl`, `SapGuiStatusbar`, `TreeNode`, `MenuItem`, `RadioButton`, `GenericGUI`.

The ActionMode bit pattern fits the codes (1 base; 4 on every read/select mode; 32 Input; 64 Verify; 128 Buffer; 512 container/API family, with 2 marking Insert/Constraint), but that's an observation, not documentation.

## Sources

- [fillegar/tosca-subsets](https://github.com/fillegar/tosca-subsets): 12 subsets (API/SFDC, DB Expert, TDS, REGEX/date helpers, Vision AI, TBox). No license, so only reduced sketches appear here.
- [Boehringer-Ingelheim/toscaci](https://github.com/Boehringer-Ingelheim/toscaci) `e2e/src/tosca/subsets.tsu` (Apache-2.0): full sample workspace with execution lists, recovery scenario, Pre/Postcondition blocks and the standard-module library.
- [zondor/awesome-subsets](https://github.com/zondor/awesome-subsets): Salesforce Html modules. No license.
- [bjorn-ali-goransson/Tosca-TSU-Format](https://github.com/bjorn-ali-goransson/Tosca-TSU-Format) `FORMAT_GUIDE.md`: format reference used for cross-checking. No license; contradictions are noted in SKILL.md.
- 4 private exports on the maintainer's machine (3 Commander web projects, 1 Cloud export with TestCase-Design). Only structure and counts were used.
- [raviacn95/tosca-playwright-migration](https://github.com/raviacn95/tosca-playwright-migration) (MIT): TBox module semantics. Its ActionMode map (69 = WaitOn, 101 = Constraint, 519 = Insert) contradicts the evidence above.
