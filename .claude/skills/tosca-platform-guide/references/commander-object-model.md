# Tosca Commander object model and design rules

How Commander (on-prem / Server) objects are built and how Tricentis recommends designing them. This file covers the **Commander side**. The Cloud JSON model is in `toscacloud-cli` (SKILL.md, `references/web-automation.md`, `sap-automation.md`, `blocks.md`, `standard-modules.md`, `best-practices.md`), and the object mapping between the platforms is in [commander-vs-cloud.md](commander-vs-cloud.md). Where a rule already lives in those files, this file links to it and doesn't repeat it.

## 1. How to use this file

- **Read a real object before you write one.** Property names, enum values and the tasks available differ between Commander versions and workspace setups. On an open Commander, run `get_object_info` + `get_attributes` (`commander-mcp`) on a similar existing object. Headless, use TCShell/TCAPI (`cli-api-commander`). Offline, read a `.tsu` export with `tosca-tsu`, which also has the **ActionMode numeric codes**. Don't guess codes.
- **Tables here are for orientation.** They tell you what to look for and which rule applies. They don't replace the object's own attribute list.
- Anything marked *(inferred)* comes from observation or deduction, not from the docs. Verify it before relying on it.
- Applies to every section: **no defect masking** (`toscacloud-cli` SKILL.md → "No-defect-masking rule"), **reuse scan first** ([reuse-scan.md](reuse-scan.md)), **re-read after writing**, then `save_workspace` (+ `check_in_all` in multi-user workspaces).

## 2. Repository structure and naming

The KB four-eyes layout (Component folders, `In Work → Ready for Review → Approved`, one folder per user) is in `toscacloud-cli` → `best-practices.md` §1. The docs add these section layouts:

| Section | Recommended hierarchy |
|---------|-----------------------|
| Modules | Application (name + acronym) → area / functionality → part / process |
| TestCases | Mirror Requirements / TestCase-Design if you use them. Otherwise: application → business process → sub-process |
| Execution | (application, if several) → `Smoke` / `Regression` / `Archive` ExecutionLists |

Naming patterns:

| Object | Pattern | Example |
|--------|---------|---------|
| Module | `<App or abbreviation> \| <general section> \| <what it covers>` | `WebShop \| Checkout \| Payment details` |
| ModuleAttribute | Plain business label of the control | `Card number`, `Pay now` |
| TestCase | `<App> - <purpose>` (unique within the project) | `WebShop - Pay by credit card` |
| TestStep | `<verb> <object> [<context>]`, saying what this step does here, not repeating the module name | `Enter card details`, `Verify order confirmation` |
| ExecutionList | `<App> \| <workflow> \| <sub-workflow>` | `WebShop \| Checkout \| Payment` |
| Business parameter | No dots (a dot is read as a path separator) | `CardNumber` |

Rules:
- Use short, readable folder names whose categories don't overlap. Don't leave empty folders.
- Rename scanned modules and attributes **during the scan**. Captions are often too generic (duplicates) or too specific (contain an order number).

Source: [Project folders](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/project_folders.htm), [Module names](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/modules_names.htm), [TestCase names](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/testcases_names.htm), [ExecutionLists](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/execution_executionlists.htm), [Reusable TestStepBlocks](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/reusable_teststepblocks.htm)

## 3. Modules

### 3.1 Objects

| Object | What it is |
|--------|------------|
| `XModule` | One screen, page or section, or one non-UI interface (file, XML, API). Holds the configuration and identification params of the root. |
| `XModuleAttribute` | One control (field, button, table, row, cell…). Can nest (child attributes, e.g. table → row → cell), and can be turned into a reference to another XModule. |
| `ApiModule` | Created by API Scan. Holds transport, payload and authentication for one message (§3.6). |
| Generalization / specialization | A specialization XModule inherits the attributes of its generalization, follows its changes, and can add attributes of its own. |
| Classic `Module` | Legacy (non-TBox) type. Don't mix Classic and TBox in one test case (`best-practices.md` §4.5). |

### 3.2 XModule properties

| Property | Values / meaning |
|----------|------------------|
| `BusinessType` | Root type for the technology, e.g. `HtmlDocument`, `XmlDocument` |
| `InterfaceType` | `GUI` or `NonGUI` |
| `IsTBoxModule` | `True` = TBox (XModule), `False` = Classic |
| `IsAbstract` | `True` = the module can't be used in test cases (e.g. a generalization) |
| `ImplementationType` | Steering technology (HTML, JAVA, SAP…) |
| `AutomationFramework` | e.g. TBox, Generic |
| `SynchronizationPolicy` | `CannotBeExecuted`, `CustomizableDefaultIsOn` |
| `Version` | Tosca version that scanned it |
| Common to all objects | `UniqueId`, `NodePath`, `Revision`, `CreatedAt/By`, `ModifiedAt/By`, `OwningGroupName`, `ViewingGroupName`, `HasMissingReferences`, `IsCheckedOutByMe` |

### 3.3 XModuleAttribute properties

| Property | Values / meaning |
|----------|------------------|
| `BusinessType` | Technology-neutral control type (e.g. `EditBox`, `Button`, `Table`, `Row`, `Cell`, `ControlGroup`) |
| `InterfaceType` | `GUI`, `NonGUI`, `Implicit` |
| `Cardinality` | `0-1`, `1`, `0-N`, `1-N`: how often the attribute may appear in **one** TestStep. Use `0-N` when a step needs it twice. |
| `DefaultActionMode` | ActionMode pre-filled on new TestStepValues (e.g. Input for fields, Select for containers *(inferred from exports)*) |
| `DefaultDataType` | DataType pre-filled (String, Numeric, Date, Boolean, Password…) |
| `DefaultValue` | Value copied into new TestStepValues |
| `ValueRange` | Semicolon list shown as a drop-down. Special entries: `<DATE>`, `<TIME>`, `<FILEPATH>`, `<DIRECTORY>` |
| `IdentifyingContext` | JSON with identification info (self-healing) |
| `Description`, `SpecialIcon` | Documentation / icon |

Custom properties (Project → Properties Definition) take `Visible`, `DefaultValue`, `ValueRange`, `ValueType`, `SuppressCopy`. Names use letters, digits and `_`, and start with a letter or digit.

### 3.4 Parameter kinds (on XModule and XModuleAttribute)

| Kind | Purpose | Examples |
|------|---------|----------|
| Configuration | Engine selection and search algorithm | `Engine` (mandatory: `Html`, `SapEngine`, `Xml`, `File`, `Framework`…), `BusinessAssociation`, `TechnicalAssociation`, `AlgorithmicAssociation`, `ConstraintIndex`, `AvoidSnapper`, `Transition` |
| TechnicalId | Technology-specific locator properties | Html: `Tag`, `Id`, `Name`, `ClassName`, `InnerText`, `Title`, `Type`, `Href`, `style_*`. Module root: `Title`, `Url`. SAP: `RelativeId`, window by transaction / program / screen |
| BusinessId | Technology-neutral identifiers | label of a button, text of a TextBox |
| ReflectedId | Properties read through reflection (Java / .NET) | |
| Steering | Runtime behaviour, inherited by child attributes *(inferred, `toscacloud-cli` observes the same on Cloud)* | `WaitBefore`, `WaitAfter`, `SendKeysDelay`, Html: `IgnoreInvisibleHtmlElements`, `DisableGetElementById`, `FireEvent`, `AllowedAriaControls` / `IgnoreAriaControls`, `EnableSlotContentHandling`, `HeaderTable`. SAP: `SAPLogonPath`, `SAPConnection`, `IdentifyColumnsByName` |
| Transition | Alternative locators | `XPath`, `CssSelector` |

`.tsu` exports store the kind as `XParam.ParamType` (codes in `tosca-tsu`). Cloud stores it as `parameterType` / `type` (`toscacloud-cli` → `web-automation.md` "Attribute anatomy"). Per-engine locator detail: web → `web-automation.md` + `web-exploration`, SAP → `sap-automation.md` + `sap-gui-exploration`.

### 3.5 Identification and design rules

**Identification order**: by **property** → by **index** (same control several times on a screen) → by **anchor** (non-web only) → by **image** (last resort). Every identifier must be:
- **Unique**: combine properties, or go through a parent with a unique ID. Identify embedded pop-ups through their top-level container.
- **Stable**: replace dynamic parts with a `*` wildcard, scan and run with the same user permissions, and for image identification keep the same resolution and colour depth. Check parent/child assumptions with XScan's highlight.
- The Html priority list and the traps (duplicate mobile/desktop DOM, invisible clones, InnerText exact-match) are in `toscacloud-cli` SKILL.md → "TechnicalId priority" and `best-practices.md` §4. They're the same engine on Commander.
- Html `ClassName` compares the **full** `class` attribute, not one token: store the whole string and wildcard dynamic tokens (`base-class *js-op`). `HREF` compares the absolute URL.
- Every Html control attribute carries `Engine = Html` and `BusinessAssociation = Descendants` as **Configuration** params (scans add them; table children use `Rows` / `Columns` / `Cells`). A hand-authored attribute without them, or with them as TechnicalIds, fails with `Sequence contains more than one element`. A hand-authored `XModule` also needs `InterfaceType = GUI` + `BusinessType = HtmlDocument` (defaults `NonGUI` / empty → `No Transition Config defined`). Details and the tag → BusinessType table: [commander-field-notes.md](commander-field-notes.md) §3.

**Module design**:
| Rule | Why |
|------|-----|
| At most **~20 controls** per module. Split by **screen area**, not by workflow | Keeps it usable, and one control lives in exactly one module |
| No 1–2-attribute modules | Hard to find, costly to maintain |
| **Attribute order = execution order.** Tosca runs a step's values top to bottom in module order, so reorder attributes (drag-and-drop) to match the user flow | e.g. tick "Remember me" before clicking "Log in" |
| Don't duplicate a module to get another order | Double maintenance. In a TestStep, use "Allow reorder" instead |
| Never delete a used module and build a new one | Breaks every reference. **Rescan** it, adjust a property (e.g. add a wildcard), or replace it through module versioning, then delete the old one |
| Groups of links / buttons / radios → `ControlGroup` attribute | They appear as a drop-down in values (`best-practices.md` §4.11) |

Source: [XModule properties](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/xmodules_properties.htm), [Module properties](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/modules_properties.htm), [Structure XModules](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/xmodules_xdefinitions.htm), [Specify properties](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/specifiying_properties.htm), [XBrowser controls](https://docs.tricentis.com/tosca-2026.1/en-us/content/engines_3.0/xbrowser/xbrowser_controls.htm), [SAP controls](https://docs.tricentis.com/tosca-2026.1/en-us/content/engines_3.0/sap/sap_controls.htm), [Identifiers](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/scan_identifiers.htm), [Module size](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/modules_size.htm), [Attribute order](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/modules_order_of_attributes.htm), [Update or delete](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/modules_update_or_delete.htm)

### 3.6 API modules (brief)

- Built by **API Scan**: scan a definition (OpenAPI 3.0, Swagger, WSDL, RAML, WADL, OData 4.0, JSON Schema, XSD), edit, validate, send, then **export to Commander**, which creates API modules and test cases. API Scan also exports OSV scenarios.
- An API module holds the transport, payload and authentication (Basic, OAuth 2.0, client certificate, Kerberos/SPNEGO, NTLM, Digest). Connections and environments live in the **API Connection Manager**.
- In steps: **Insert** creates request content (non-UI objects), **Verify** / **Buffer** read the response, **Constraint** on list-item elements picks the one item whose values match, and siblings of that item are then verified (§5).
- Commander MCP has `create_api_module` for API interactions missing from a test (`commander-mcp` → `author-automated-test-case.md`).

Source: [API Engine 3.0](https://docs.tricentis.com/tosca-2026.1/en-us/content/engines_3.0/api/api_engine.htm), [API Scan TestCases](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/api_scan_create_tc.htm), [API modules](https://docs.tricentis.com/tosca-2025.1/en-us/content/engines_3.0/api/api_modules_working.htm), [Constraint on lists](https://docs.tricentis.com/tosca-2026.1/en-us/content/engines_3.0/api/api_constrain_lists.htm)

## 4. Test cases

### 4.1 Object tree

```
TestCase                      (TestCaseWorkState, TCPs, Recovery Scenarios folder)
└─ TestStepFolder             (Name, Condition, Repetition)
   ├─ XTestStep               (→ XModule; Name, Condition, Repetition, disabled flag)
   │  └─ XTestStepValue       (→ XModuleAttribute; Value, ActionMode, DataType, Operator, ActionProperty, ExplicitName, Condition)
   │     └─ XTestStepValue …  (child attributes: row / cell / nested elements)
   ├─ TestStepFolderReference (→ Reuseable TestStepBlock + business parameter values, §8)
   └─ If / While / Do statement (§9)
```

| Field | Where | Notes |
|-------|-------|-------|
| `Value` | value | Literal, dynamic expression (§6), or `{NULL}` on a container that only navigates *(inferred from exports)* |
| `ActionMode` | value | §5. Changing ActionMode or DataType resets `Operator` to its default. |
| `DataType` | value | Use the right one for the check: Boolean for `Exists`, Numeric / Date for comparisons, Password for secrets |
| `Operator` / `ActionProperty` | value | Comparison and property for Verify / WaitOn / Buffer (§5.2) |
| `ExplicitName` | value | Names a dynamic child: table row / column (`$1`, `#3`, `$last`…), or an attribute with Cardinality `0-N` |
| `Condition` | folder / step / value | TestCase-Design condition, evaluated on instantiation (§11) |
| `Repetition` | folder / step | Repeat N times, or once per value of a buffered list *(inferred)*. Preferred over loops. |
| `TestCaseWorkState` | TestCase | `PLANNED` (counts 20 %), `IN_WORK` (50 %), `COMPLETED` (100 %) in requirement coverage |

Exact attribute names (`Condition`, `Repetition`, the disabled flag, WorkState) can differ by version, so `get_attributes` first. The `.tsu` class names and assocs are in `tosca-tsu` → "Object model".

### 4.2 Structure and content rules

- Top folders: **Precondition** (start app, log in, prepare data, set buffers) → **Process** (the actual test; sub-folders per application or business process in end-to-end cases) → **Postcondition** (log out, close app/browser, release data, clean files). This repo also uses a separate **Verification** folder (`best-practices.md` §5.1): keep it when the team does.
- Folder logs appear in results only when Project → Options → Advanced → "Create Logs for TestStepFolders" is on.
- **Self-contained**: the start and end state are the same, and no other test case has to run first.
- **Defined outcome**: at least one real Verify that proves the business result, not just that the steps ran.
- **Verify after each significant step**, not in one large step at the end. Failures are then easy to locate.
- No filler test cases of 1–2 transitional steps, and no folders holding a single step.

### 4.3 Waits

| Option | Use |
|--------|-----|
| Default sync | Tosca waits up to **10 s** for screens and controls (setting `Synchronization Timeout`) |
| **WaitOn** on the control (preferred) | Waits until a property reaches a value (e.g. progress bar `InnerText` = `100%`). Default up to **20 s** (setting `Synchronization Timeout during WaitOn`) |
| `WaitBefore` / `WaitAfter` steering param on the attribute | Static wait built into the module (ms). Better than TBox Wait because one change covers every test |
| `TBox Wait` (`Duration` ms) | Last resort. Hard-codes timing into each test case |

Source: [TestCase structure](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/testcases_structure.htm), [TestCase content](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/testcases_content.htm), [Verifications](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/testcases_verifications.htm), [Wait times](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/testcases_wait_times.htm), [Control properties](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/control_properties.htm), [Execution state calculation](https://docs.tricentis.com/tosca-2026.1/en-us/content/requirements/calculation_example_execution_state.htm)

## 5. ActionModes

Numeric codes (37 Input, 69 Verify, 101 WaitOn, 165 Buffer…) are in `tosca-tsu` → "ActionMode codes". Cloud uses the same names (`toscacloud-cli` → `web-automation.md` "Action modes").

| ActionMode | Does | Value holds | Notes |
|------------|------|-------------|-------|
| **Input** | Writes to the control: types, clicks, selects | Text, `X`, click / key tokens | Multi-line text with Shift+Enter in the value cell |
| **Insert** | Creates objects in non-UI interfaces (XML nodes, API request content) | Content | NonGUI modules |
| **Verify** | Compares a control value or property | Expected value, or `.<Property><Op><Value>` | Case-sensitive, supports regex (§6). Uses the control's default property when none is given |
| **Buffer** | Saves the value or a property into a buffer | Buffer name (`<property>-><buffer>` in tables) | Read later with `{B[name]}`. Array element: `{B[name][index]}` |
| XBuffer (via **Verify**) | Verifies a string and captures its dynamic part | `literal {XB[name]} literal` | Not a separate mode. It's a Verify value. Also allowed in TBox File Existence (2026.1) |
| **WaitOn** | Pauses until the property has the value | Expected value / property | Timeout = "Synchronization Timeout during WaitOn" |
| **Select** | Selects / navigates a uniquely named node (container, tree path with `->`, table) | Usually empty, or a path | Default on containers *(inferred)* |
| **Constraint** | Narrows the search in the parent to the element(s) matching this value: table row by cell, list item by field | Search value | Combine constraints until exactly one element matches; `#<n>` picks the n-th match. Table comparisons ignore spaces, tabs and line breaks |
| **Exclude** | Leaves a part out of a comparison | e.g. `{TableCompare}` on tables | |
| **Delete** / **Modify** | Remove / overwrite elements of a buffered array | Index `#n` / `#last` or a Constraint | Only through `TBox Array Operation` |

### 5.1 Tables

| Selector (ExplicitName / attribute name) | Meaning |
|------------------------------------------|---------|
| `<Row name>` / `<Column name>` | Header-defined name (wildcards allowed) |
| `$1`, `$<n>` | Position relative to the header |
| `#<n>` | Absolute position, ignoring the header |
| `$header`, `$last`, `$lastContentRow`, `$firstEmptyRow` | Special rows |
| Negative numbers | Columns / rows before the header |

Table properties: `RowCount`, `ColumnCount`, `RowNumber` / `RawRowNumber`, `ColumnNumber` / `RawColumnNumber`, `ResultCount` (matches of the constraint). **Row-by-content pattern**: Row `<any>` (or `*`) → Cell `Customer` = `ACME` with **Constraint** → Cell `Status` with **Verify** (or Buffer `RowNumber`). SAP tables also take `{SELECT}`, `{ADDSELECT}`, `{DESELECT}` with Input to select rows. Cloud-side row-buffer detail (`${B[RowNum]}`) is in `toscacloud-cli` SKILL.md → caveats.

### 5.2 Verify / WaitOn operators and properties

- Value syntax: `<Op><Value>` for the default property, or `.<Property><Op><Value>` for a named property. Operators: `==` `!=` `<` `>` `<=` `>=`. There's an input assistant (blue arrow in the Value cell).
- Business properties on all technologies: `Exists`, `Visible`, `Enabled`, `IsSteerable`, `ResultCount`. Technical properties depend on the engine (e.g. Html `Tag`, `InnerText`).
- The same property syntax works with **Verify, WaitOn, Select, Constraint**.
- Cloud stores property and operator as separate fields (`actionProperty`, operator). Commander shows them in the value and in `ActionProperty` / `Operator` *(inferred, confirmed in `.tsu` attributes)*.

Source: [ActionModes](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/action_modes.htm), [Control properties](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/control_properties.htm), [Table](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/type_table.htm), [Constraint on lists](https://docs.tricentis.com/tosca-2026.1/en-us/content/engines_3.0/api/api_constrain_lists.htm), [Buffer Operations](https://docs.tricentis.com/tosca-2025.1/en-us/content/standard_subset/automation_tools/buffer_operations.htm), [SAP controls](https://docs.tricentis.com/tosca-2026.1/en-us/content/engines_3.0/sap/sap_controls.htm)

## 6. Dynamic values

General form: `{COMMAND[p1][p2]…}`. Special characters are `{ } [ ] " *`. Escape them by wrapping in double quotes (or use the "Escape value" context action). Inside a regex, escape with `\`. `*` is a wildcard in values, table names and identification params (several are allowed: `*ri*n*s`).

Cloud column: ✓ = documented or used on Cloud in `toscacloud-cli`; ✗ = known not to work there; ? = not verified.

| Expression | Meaning | Cloud |
|------------|---------|-------|
| `X` | Click without mouse emulation (preferred for buttons and links) | ✓ |
| `{CLICK}` `{DOUBLECLICK}` `{RIGHTCLICK}` `{LONGCLICK}` `{MOUSEOVER}` `{DRAG}` `{DROP}` | Mouse emulation. Offsets: `{CLICK[h][v]}` (px or %). Also `{MOUSE[…]}`, `{JUMPTO[…]}` | ✓ (no `{LEFTCLICK}` anywhere) |
| `{ALTCLICK}` `{SHIFTCLICK}` `{CTRLCLICK}` (the click page also lists `{CONTROLCLICK}`), L/R variants | Click with a modifier | ✓ `{CTRLCLICK}` |
| `{ENTER}` `{TAB}` `{ESC}` `{F1}`…`{F24}` `{UP}` `{DEL}` `{HOME}` … | Single keys | ✓ |
| `{SENDKEYS["…"]}` | WinForms SendKeys (`+` Shift, `^` Ctrl, `%` Alt). Delay via `SendKeysDelay` (steering param beats TCP) | ✓ |
| `{KEYPRESS[code]}` `{KEYDOWN[code]}` `{KEYUP[code]}` | Virtual-key codes without the `VK_` prefix (e.g. `RETURN`) | ✓ |
| `{TEXTINPUT["…"]}` | Send Unicode text | ✓ |
| `{B[name]}` / `{B[name][i]}` | Read a buffer / an array element | ✓ |
| `{XB[name]}` | Capture inside a Verify value | ✓ |
| `{CP[name]}` | Test configuration parameter (§12) | ✓ |
| `{PL[name]}` | Business parameter inside a reusable block (§8) | ✓ |
| `{XL[Path.To.Attr]}` | TestSheet attribute in a template (§11) | ? (Cloud has templates, different mechanics) |
| `{S[<path>]}` | Value from the Settings dialog | ? |
| `{RES[name]}` / `{RES[name][encoding]}` | Named resource (e.g. a loaded XML). Can't be combined with other expressions | ? |
| `{DATE[base][offset][format]}`, `{TIME}`, `{DATETIME}`, `{DAY}` `{MONTH}` `{YEAR}`, `{MONTHFIRST}` `{MONTHLAST}` `{QUARTERFIRST}` … | Date/time. Offset units `d` `w`(workdays) `M` `y` `h` `H` `m` `s` `fff`, e.g. `+3M-1d`. .NET format strings. Prefixes `L` (locale), `N` (2-digit), `A` (3-letter) | ✓ |
| `{CALC[…]}` | Arithmetic evaluated **by Excel** (2010+ must be installed) | ? *(inferred: unlikely on Cloud agents)* |
| `{MATH[…]}` | NCalc arithmetic, no Excel needed. Adds `%`, comparisons, logic, bitwise, functions like `Round(x,n)` | ✓ |
| `{RND[len]}` / `{RND[lo][hi]}`, `{RNDDECIMAL[…]}`, `{RANDOMTEXT[n]}`, `{RANDOMREGEX["…"]}`, `{CTMSTMP}` | Random numbers, text, regex-shaped text, unique timestamp string | ✓ (Cloud docs) |
| `{STRINGLENGTH[t]}` `{STRINGTOLOWER[t]}` `{STRINGTOUPPER[t]}` `{TRIM[t][START\|…]}` `{STRINGREPLACE[t][pat][new][IGNORECASE]}` `{STRINGSEARCH[t][pat]}` `{NUMBEROFOCCURRENCES[t][pat]}` `{BASE64[t][ENCODE]}` | String operations | ✓ |
| `{REGEX["…"]}` | .NET regex match in Verify / WaitOn. A named group `(?<buf>…)` writes a buffer. A buffer can only be used **inside** the regex | ? |
| `{NULL}` | Navigation-only value on a container *(seen in exports, docs page not fetched)* | ✓ (in `.tsu`) |
| `{SCRIPT[…]}`, `{XP[…]}` | Script / XPath expansion | ✗ on Cloud (`toscacloud-cli` caveats). Commander: verify on your version |
| `{EMPTY}`, `{ENV[…]}`, `{NUMBER…}` | Not confirmed in the docs fetched for this file. Test on a real step before use | ? |

Other expression families in the docs, not detailed here: scroll operations, number formats, intervals, UserSimulation, Key Vault secrets. Keyboard / mouse emulation (`{CLICK}`, `{SENDKEYS}`) is discouraged: prefer `X` and direct input (`best-practices.md` §5.12).

Source: [Specify values](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/specifying_values.htm), [Click operations](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/click_operations.htm), [Keyboard commands](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/special_characters.htm), [Text expressions](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/text_expressions.htm), [Date and time](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/date_and_time_expressions.htm), [Calculations](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/calculations.htm), [Random values](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/random_values.htm), [Random values (Cloud)](https://docs.tricentis.com/tosca-cloud/en-us/content/references/values_random.htm), [String operations](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/string_operations.htm), [Regular expressions](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/regular_expressions.htm), [Resource expressions](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/resource_expressions.htm), [Buffers how-to](https://docs.tricentis.com/tosca-2023.1/en-us/content/articles/buffer_this.htm)

### 6.1 Buffer rules

- A buffer is a name/value pair kept **per workspace on the executing machine**. It isn't shared between users, and it doesn't reach DEX agents from another run. Treat its lifetime as **one test case** (`best-practices.md` §10.2).
- Ways to set one: ActionMode Buffer, `{XB[…]}` in a Verify, a regex named group, `TBox Set Buffer`, `TBox Partial Buffer`, `TBox Name To Buffer` (ExecutionList only). Buffer names can themselves contain expressions.
- View and delete them in the Buffer Viewer (Settings → Engine → Buffer), or with `TBox Delete Buffer` (empty or `*` = all, `Buff*` = pattern).
- Common failures: wrong bracket placement, stray spaces or line breaks inside the expression.

## 7. Standard modules (Standard subset)

Import the Standard subset once per workspace. It contains **TBox Automation Tools**, **Engines** modules (Html, SAP, Mobile, API…), **Test Data Management** modules, sample test cases, ExecutionLists, virtual folders and report templates. Use them instead of building your own. Cloud equivalents are engine-bundled packages (`toscacloud-cli` → `standard-modules.md`).

| Folder → Module | Purpose | Key attributes |
|-----------------|---------|----------------|
| Process → `TBox Start Program` | Launch an exe / app | `Path`, `Directory`, `Arguments`, `WaitforExit` (→ `StandardOutputFile`, `TimeoutForExit`, `ExitCode`), `Run as` (→ `Username`, `Password`) |
| Process → `TBox Close Program` | Close / wait / verify a process | `Id` / `Name` / `Main Window Title` (one required), `Command Line`, `Operation` (Close if Exist, Close, Wait on Close, Verify Program Exists) |
| Windows → `TBox Window Operation` | Act on a window | `Caption`, `Child Window Caption`, `Operation` (Bring To Front, Close, Maximize, Minimize, Move to Center, Normal, Resize (+Height/Width), Try Bring To Front, Verify Window Exists / Does Not Exist, Wait On Close / Open), `Window Index`, `Timeout` |
| Windows → `TBox Dialog` / `TBox Save As` | Standard dialogs | `Caption`, `Label`, `Button` / `FilePath`, confirmation popup fields |
| Windows → `TBox Send Keys`, `TBox Context Menu`, `TBox Clipboard`, `TBox Take Screenshot`, `TBox Scroll Window Operation` | Keys to a window, menu path `A->B`, clipboard input / verify / buffer / wait, screenshot, scrolling | `Caption`, `Keys` / `Menu` / `Value` / `Filename` … |
| Buffer → `TBox Set Buffer` | Write (Input) or check (Verify) buffers | one attribute per buffer name |
| Buffer → `TBox Partial Buffer`, `TBox Name To Buffer`, `TBox Delete Buffer` | Substring into a buffer, test case name into a buffer, delete | `Buffer`, `Value`, `Start`/`End`/`Last` |
| Buffer → `TBox Iterate Array`, `TBox Array Operation` | Loop over / change buffered arrays | `Array to Iterate`, `Target Buffer` (in a While condition). `Array`, `Content`, `Item` (`#n`, `#last`), `.Count==` |
| Expression Evaluation → `TBox Evaluation Tool` | Comparisons with a true/false result: conditions of If / While / Do | `Expression` (Verify). Strings in `'…'`, NCalc syntax, `AND` |
| File → `TBox File Existence`, `Read/Create File`, `Append File`, `Copy File`, `Move/Rename File`, `Delete File`, `File Compare`, `Image Compare`, `Zip File`, `Unzip File` | File I/O | `Directory`, `File`, `Text`, `Encoding`, `Overwrite` … |
| Folder, Numeric, Resource Handling, Test Scripts | Folder operations, decimal format conversion, delete resources, start test scripts | |
| Timing → `TBox Wait`, `TBox Start Timer`, `TBox Stop Timer` | Static wait (`Duration` ms, avoid it); timers with `ID`, `Maximal Duration` (both in the same test case) | |
| Engines → Html | `OpenUrl` (`Url`, `UseActiveTab`, `ForcePageSwitch`, `BrowserArguments`), `CloseBrowser` (`Title`; fails hard when no browser session is open, so never as the first step: [commander-field-notes.md](commander-field-notes.md) §6), `Execute JavaScript` / `Verify JavaScript Result` (search criteria `Title`/`Url`/`Window Index`/`UseActiveTab`, `JavaScript`, `Result`), `Steer Dialog Box`, `ClickOnScreen`, log monitoring, broken-link and accessibility checks, QR/barcode | Cloud JSON shapes in `web-automation.md` / `standard-modules.md` |
| Engines → SAP | SAP Logon (`SAPLogonPath`, `SAPConnection`, SSO bypass), SAP Login, SAP Toolbar (T-code), status bar … | Cloud package list in `sap-automation.md` |

Source: [Standard subset](https://docs.tricentis.com/tosca-2026.1/en-us/content/standard_subset/standard_subset_overview.htm), [TBox Automation Tools](https://docs.tricentis.com/tosca-2025.1/en-us/content/standard_subset/automation_tools/automation_tools_overview.htm), [Process Operations](https://docs.tricentis.com/tosca-2026.1/en-us/content/standard_subset/automation_tools/process_operations.htm), [Basic Windows Operations](https://docs.tricentis.com/tosca-2026.1/en-us/content/standard_subset/automation_tools/windows_operations.htm), [Buffer Operations](https://docs.tricentis.com/tosca-2025.1/en-us/content/standard_subset/automation_tools/buffer_operations.htm), [Expression Evaluation](https://docs.tricentis.com/tosca-2025.1/en-us/content/standard_subset/automation_tools/expression_evaluation.htm), [File Operations](https://docs.tricentis.com/tosca-2025.1/en-us/content/standard_subset/automation_tools/file_operations.htm), [Timing](https://docs.tricentis.com/tosca-2026.1/en-us/content/standard_subset/automation_tools/timing.htm), [HTML Modules](https://docs.tricentis.com/tosca-2026.1/en-us/content/standard_subset/engines_3.0/html.htm), [SAP controls](https://docs.tricentis.com/tosca-2026.1/en-us/content/engines_3.0/sap/sap_controls.htm)

## 8. Reuse: libraries, reusable blocks, business parameters

| Object | Facts |
|--------|-------|
| `TestStepLibrary` | Lives in a TestCases folder. **One per folder.** Created automatically in the parent folder when you create a block and no library exists |
| `ReuseableTestStepBlock` (Tosca's spelling) | Built by selecting steps / folders in a test case → "Create Reuseable TestStepBlock". Contains TestSteps, XTestSteps, folders, other block references |
| Business Parameter Container → Business Parameters | Created on the block. A step value uses a parameter as `{PL[<name>]}` (typed, or drag-and-drop). **No dots in names.** Renaming a parameter updates every link |
| `TestStepFolderReference` | The use of a block in a test case. It carries **business parameter references** with the values for this use. F11 "simple view" hides non-parameter content, and the ribbon's parameter button resolves `{PL}` to the actual values |
| Nested blocks | Pass data only through business parameter references, never through step values |

Rules:
- Create a block **only for steps you actually reuse** in several test cases (`best-practices.md` §1.5). To repeat steps within **one** test case, use `Repetition` on a folder or step instead.
- Keep a separate library per application or version: checking out a library locks it for everyone.
- Library changes propagate to every reference. Check who uses a block (TQL §14) before changing it.
- Buffers set inside a block are visible to later steps of the same test case (`toscacloud-cli` caveats, same engine).
- Cloud wiring (ULIDs, `parameterLayerId`): `toscacloud-cli` → `blocks.md`. Don't port it to Commander.

Source: [Reusable TestStepBlocks](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/reusable_teststepblocks.htm), [TestStepLibraries](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/teststep_libraries.htm), [Repetitions and reuse](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/testcases_repetitions_and_reuse.htm)

## 9. Control flow: If / While / Do

| Statement | Created with | Runs |
|-----------|-------------|------|
| **If** | Context menu or "Create Object" on a test case / folder. Creates `Condition` + `Then`. Add `Else` by hand | Then once if the condition holds, otherwise Else once |
| **While** | Creates `Condition` + `Loop` | Checks first. Repeats Loop while the condition holds (may run 0 times) |
| **Do** | Creates `Condition` + `Loop` | Runs Loop first, then checks. Repeats while the condition holds (runs at least once) |

- Order inside If: Condition → Then → (Else).
- The condition is a **step inside the `Condition` folder** (drop the module onto it, set a Verify value such as `.Exists == False`). A Buffer step placed before the If, with an empty Condition, does not drive the branch.
- Conditions are usually `TBox Evaluation Tool` Verify expressions (e.g. buffer `A` < 10), or any Verify step (e.g. `Exists == True`).
- While / Do have **`MaximumRepetitions`** (default **30**) against infinite loops.
- **Condition results don't count toward the test result.** A failing Verify inside a Condition is silent by design, so never move a real check into a Condition (**defect masking**, see `toscacloud-cli` SKILL.md).
- Prefer not to branch or loop (`best-practices.md` §5.7–5.8): use TestCase-Design conditions (§11), `Repetition`, or Constraint. Accepted uses: optional pop-ups / consent banners, cleanup preparation, iterating an array (`TBox Iterate Array` in a While condition).
- `.tsu`: `TestCaseControlFlowItem` + `TestCaseControlFlowFolder` (`tosca-tsu`). Cloud: `ControlFlowItemV2` (`web-automation.md` → "Conditional steps").

Source: [Conditional statements and loops](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/conditional_statements.htm), [Expression Evaluation](https://docs.tricentis.com/tosca-2025.1/en-us/content/standard_subset/automation_tools/expression_evaluation.htm)

## 10. Recovery and CleanUp scenarios

| Item | Facts |
|------|-------|
| Location | A `*** Recovery Scenarios ***` folder on a TestCase folder or a TestCase. It applies to that object and everything below it |
| Recovery Scenario | Corrective steps for an expected disturbance (modal dialog, cookie banner, UI delay). It succeeds when **all** its steps pass |
| `RetryLevel` (property) | `TestStepValue`: resume at the failed value. `TestStep`: resume at the failed step. `TestCase`: re-run the whole case. **Prefer TestStep**, because a TestCase restart repeats login/start against an app that is already open. NonGUI modules recover only at TestStep / TestCase level |
| Lookup order | Tosca looks on the closest level first and runs the applicable scenarios top to bottom. If none applies or none succeeds, it escalates to the next level up |
| CleanUp Scenario | Right-click the Recovery Scenarios folder → "Create CleanUp Scenario". Runs when Recovery fails, to reset the environment (e.g. kill the app) so the next case can start. Several run top to bottom |
| When they fire | Only in ExecutionList runs, not in the ScratchBook (`best-practices.md` §5.18–19) |

Rules: write narrow scenarios for specific, known problems. Don't use CleanUp to cover a weak design: expected behaviour (e.g. a duplicate-entry dialog) belongs in the normal flow. A recovery must never dismiss the very error a test is meant to catch (no defect masking). Cloud: `recoveryScenarioCollection` (`web-automation.md`).

Source: [Create a Recovery Scenario](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/recovery_create_scenario.htm), [Define a CleanUp Scenario](https://docs.tricentis.com/tosca-2026.1/en-us/content/tbox/recovery_cleanup.htm), [Error handling](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/testcases_error_handling.htm)

## 11. TestCase-Design and templates

### 11.1 TestCase-Design objects

| Object | Facts |
|--------|-------|
| `TestSheet` | Framework for one requirement / business theme. Name unique in its folder. Built **data-oriented** (Attributes) or **process-oriented** (Steps). Sheets with the same structure can be merged; a structure can be pasted from the clipboard |
| Attribute | A variable of the test (e.g. `Fuel type`), can nest (`Person.First Name`). Business relevance per attribute (`best-practices.md` §3.13) |
| Instance | A variant of an attribute. Created by hand, from a value, or by dragging a ModuleAttribute. **Character**: `Valid` (default, no error expected), `Invalid` (error expected), `StraightThrough` (the lowest-dependency happy path, needed for linear expansion). **Position**: `Inner` / `Boundary` (StraightThrough is always Inner) |
| `NULL` / `EMPTY` instance | Zero / empty string, one each per element. Enable them in Project → Options → TestCaseDesign |
| Class | Reusable data (e.g. customer records) that sheets reference. Edit the Class, not the reference. Duplicate instances can be merged |
| Instance rows | Generated by combinatorics. Rename them to business names (`best-practices.md` §3) |

### 11.2 Templates and instantiation

| Step | Facts |
|------|-------|
| Make a template | Test case → "Convert to Template" (reversible, with data loss). Templates get their own icon |
| Attach data | Drag a TestSheet / Class onto the template, or set `SchemaPath` to an Excel file (.xlsx / .xlsm, no comments). One TestSheet per template (`best-practices.md` §3.14) |
| Link values | `{XL[Level1.Level2.Attr]}` in step values (drag the attribute rather than typing). Relative form `{XL[.Attr]}`. "Check Template" validates the references and nested paths |
| Conditions | On template, folder, step, XTestStep or value: `Insurant.Person.Sex=="male"`, combined with `&&` / `\|\|`. Numeric: `ASINT(Age)<17`. Characters other than A-Z / 0-9 need `\` or apostrophes: `'Product.vehicle-insurance'=="X"` |
| `InstanceName` | Names the generated cases: fixed text (numbered) or `{XL[Instance.Name]}` plus prefix / suffix |
| Instantiate | Context menu "Create TemplateInstance" creates one TestCase per instance in a **TemplateInstance** folder. `DataSourcePath`, `InstantiationSelector` (subset) apply. Ctrl+R = "Reinstantiate" |
| Generated cases | Copy the template structure, ActionModes and WorkState. Hand edits set `ChangedManually` and are **lost on re-instantiation**, so edit the template only |

Cloud has the same TestCase-Design objects (a real Cloud export contains TestSheets, templates and template instances; see `tosca-tsu` → `tsu-schema.md` §2.6), but this repo has no Cloud tooling for authoring them yet ([commander-vs-cloud.md](commander-vs-cloud.md)). Copied template steps keep a link to their source (`DerivedFrom` in exports), and `{XL[]}` values are resolved to literals in the instances.

Source: [Instances](https://docs.tricentis.com/tosca-2026.1/en-us/content/testcase_design/instances.htm), [TestSheets](https://docs.tricentis.com/tosca-2026.1/en-us/content/testcase_design/testsheets.htm), [TestCase templates](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/testcase_templates.htm), [Combining templates with data sources](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/combining_templates.htm), [Assign test data](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/assigning_test_data.htm), [Creating TemplateInstances](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/instantiating_testcases.htm)

## 12. Test Configuration Parameters (TCPs)

- **Where**: the project root, ComponentFolders, TestCase-Design / Configurations / TestCases / ExecutionList folders, TestCases, ExecutionLists, ExecutionEntries, the ScratchBook. Edit them in the object's **Test configuration** tab (Ctrl+N, Ctrl+. creates one).
- **Inheritance**: children inherit. Override on a lower level; "Reset to default value" restores the parent's value. A **bold** name means it is defined here, regular means inherited.
- **Kinds**: built-in TCPs are read by Tosca itself (e.g. `Browser`, `SendKeysDelay`), so you don't reference them. Custom TCPs take `Name`, `Value`, `DataType` (String / Boolean / Password) and `ValueRange`, and are read with `{CP[Name]}` (e.g. `C:\{CP[Progpath]}\App`).
- **Configurations**: named bundles of TCPs in the Configurations section, assigned to ExecutionLists / TestCases by drag-and-drop (Mobile scans create them automatically).
- Put TCPs as **high** as possible. Keep per-case data in TestSheets, not TCPs (`best-practices.md` §1.6, §10.1). Never store real credentials in plain String TCPs: use the Password type or the team's vault.
- Query them with TQL `EVALCP("Browser")` (inherited) or `Browser == …` (defined on the object only).

Source: [Create TCPs](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/tcp_create_tcp.htm), [TCP examples](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/tcp_examples.htm), [TQL examples](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/tql_examples.htm)

## 13. ExecutionLists and Requirements

| Object | Facts |
|--------|-------|
| ExecutionList | Created by dropping a TestCase / folder onto ExecutionLists, or "Create ExecutionList". Gets an **ActualLog** (last results) straight away. Keeps its result history |
| ExecutionEntry | One per test case use. The same case can appear several times. The icon shows WorkState (PLANNED / IN_WORK / COMPLETED) |
| ExecutionEntry folder | Created when you drop a TestCase folder. **Linked** to the source folder so it stays in sync. Non-linked sub-folders are possible |
| Results | ExecutionLog → ExecutionTestCaseLog → step logs ([commander-vs-cloud.md](commander-vs-cloud.md)) |

- Group lists by test type and business workflow, mirror the TestCases tree, and put only COMPLETED cases in them (`best-practices.md` §6). Recovery / CleanUp and `TBox Name To Buffer` work only here.
- Run: Commander MCP `execute_test_suite` (+ `_status`), TCShell (`cli-api-commander`), or DEX TestEvents for unattended runs.
- **Requirements**: folders → RequirementSets → Requirements (functional / non-functional). Each has a `Weight` (default 1). `Relative Weight (%)` = weight / total in the set. Link TestCases (and TestSheets) to Requirements, and link ExecutionLists to the RequirementSet. Execution state = relative weight × results. Coverage counts WorkState as PLANNED 0.2 / IN_WORK 0.5 / COMPLETED 1.0. Updates are manual, or automatic with the project setting `AutoCalculateRequirements`. Keep at most 7 siblings per level (`best-practices.md` §2).

Source: [Create an ExecutionList](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/execution_lists_section.htm), [ExecutionLists best practice](https://docs.tricentis.com/tosca-2024.2/en-us/content/best_practices/execution_executionlists.htm), [Requirements](https://docs.tricentis.com/tosca-2023.2/en-us/content/requirements/requirements.htm), [Execution state calculation](https://docs.tricentis.com/tosca-2026.1/en-us/content/requirements/calculation_example_execution_state.htm)

## 14. TQL cheat sheet

**Availability**: Commander UI (TQL search, can be saved as a virtual folder), TCShell `Search "<tql>" <n>` / `JumpToNode`, TCAPI `$project.Search('<tql>')` (`cli-api-commander` → `tcapi.md`, `reference/commands.md`). **Not available through Commander MCP**: walk the tree there ([reuse-scan.md](reuse-scan.md)). Results depend on the starting object.

Grammar: `query ::= { arrowOperator [RETURN] searchExpression }` and `searchExpression ::= (assocName | aggregation) [":" Type] ["[" logicalExpression "]"]`. No spaces inside tokens.

| Token | Meaning |
|-------|---------|
| `->` / `=>` | One level down / all levels down |
| `SUBPARTS` / `SUPERPART` | Children / parents (aggregations). Also `SELF`, `PROJECT` |
| Associations | `Items`, `TestSteps`, `Module`, `AllReferences`, `ExecutionEntries`, `TestCase`, `LockedBy`, `TestedBy` … (any assoc name) |
| `:Type` | Filter by class: `TestCase`, `XModule`, `Module`, `TCFolder`, `TestStepValue`, `ExecutionEntry`, `OwnedItem`, `RequirementSet` … |
| `==` `!=` `=i=` `!i=` | Equal / not equal (case-insensitive with `i`) |
| `=?` `=i?` `!?` `!i?` | Contains / doesn't contain |
| `=~` `=i~` | .NET regex |
| `<` `>` `<=` `>=`, `AND` `OR` `NOT`, `+ - * :` | Relational, logical, arithmetic |
| `COUNT("assoc")`, `EVALCP("tcp")`, `OBJECTS("id")`, `TODAY(±d)` | Functions |
| `UNION(q,…)` `INTERSECTION(q,…)` `COMPLEMENT(all, subset)` `SORT(q,"cond")` `SUBSET(q,i,n)` | Set operations |
| `RETURN` | Return this level instead of the last one |
| `'<ANY>'` | Any property |

Recipes (run from the project root):

```text
=>SUBPARTS:TestCase[Name=~"(?i)checkout"]                           # cases by name
=>SUBPARTS:XModule[Name=?"Payment"]                                 # modules by name
=>SUBPARTS[TechnicalId=="ID=edit_price"]                            # objects by locator
=>SUBPARTS:Module[Name=="Vehicle data"]=>AllReferences=>SUPERPART:TestCase   # cases using a module
=>SUBPARTS:TestStepValue[Value=="Motorcycle"]=>SUPERPART:TestCase   # cases using a value
=>SUBPARTS:Module[COUNT("TestSteps")==0]                            # unused modules
=>COMPLEMENT(=>SUBPARTS:TestCase,=>RETURN SUBPARTS:TestCase->ExecutionEntries)  # cases in no ExecutionList
=>COMPLEMENT(=>SUBPARTS:TestCase,=>SUBPARTS:RequirementTestCaseLink->TestedBy)  # cases without requirement
=>SUBPARTS:TestCase[IsTemplate=i="true"]                            # templates
=>SUBPARTS:TestCase[EVALCP("Browser")=="Chrome"]                    # by inherited TCP
=>RETURN SUBPARTS:OwnedItem[CheckOutState=="CheckedOut"]->LockedBy[Name=="jdoe"]  # who holds checkouts
```

Blocks aren't in the docs' examples. Try `=>SUBPARTS:ReuseableTestStepBlock[Name=?"Login"]` *(inferred from the `.tsu` class name)*, and verify before relying on it.

Source: [TQL Search](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/tql_search.htm), [TQL grammar](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/tql_grammar.htm), [Operators and functions](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/tql_operators.htm), [Building queries](https://docs.tricentis.com/tosca-2025.1/en-us/content/tosca_commander/tql_creation.htm), [TQL examples](https://docs.tricentis.com/tosca-2026.1/en-us/content/tosca_commander/tql_examples.htm)

## 15. Commander ↔ Cloud callouts

| Topic | Commander | Cloud | See |
|-------|-----------|-------|-----|
| Editing | Tasks and attributes on live objects, then `save_workspace` | JSON over REST, GET after every write | [commander-vs-cloud.md](commander-vs-cloud.md) |
| Reusable block | Library → block → `{PL[]}`, names wired by the tool | `sharedAction` + ULID `parameterLayerId` wiring | `blocks.md` |
| Test data | TestSheets, Classes, templates, `{XL[]}` | Same TestCase-Design objects (seen in export) + data sets | §11 |
| Search | TQL (TCShell/TCAPI/UI), not through MCP | Inventory search / toscactl | [reuse-scan.md](reuse-scan.md) |
| Standard modules | Imported Standard subset (modules are visible in the tree) | Engine packages by GUID, not in Inventory | `standard-modules.md` |
| Dynamic values | Full list incl. `{CALC}` (Excel), `{S[]}`, `{RES[]}` | `{SCRIPT}` / `{XP}` not registered; `{MATH}` works | §6 |
| ActionMode storage | Numeric codes in `.tsu` | Names in JSON | `tosca-tsu` |
