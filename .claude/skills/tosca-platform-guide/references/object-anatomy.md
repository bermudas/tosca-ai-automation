# What a Tosca module and test case look like

Read this before you automate a scenario. It shows one complete **module**, one complete **test case** and one **reusable block** the way real projects build them, with every part explained, and how each part is stored on Tosca Server (Commander) and on Tosca Cloud. The shapes are generalized from real exported workspaces of both platforms (`tosca-tsu` → `references/tsu-evidence.md`); names and values are placeholders.

Same model on both platforms: Cloud stores the Commander objects as JSON. Only the field spelling and the IDs differ.

Next steps after this file: step shapes per situation → [test-patterns.md](test-patterns.md); exact calls per runtime → [build-guide.md](build-guide.md); full property tables → [commander-object-model.md](commander-object-model.md) (Commander), `toscacloud-cli` → `references/web-automation.md`, `sap-automation.md` (Cloud JSON).

## 1. The three layers

```
Module            WHAT can be steered: one page / screen / API message, with its controls (attributes) and how to find them
  ↑ used by
Test step         ONE use of a module: which attributes to touch, with which value and action
  ↑ grouped in
Test case         the scenario: folders of steps, block calls, control flow, plus configuration and recovery
```

A test case never contains locators. A module never contains test data. Everything a step does goes through a module attribute.

## 2. A module, complete

A module describes one page or one logical section of it.

```
MODULE 'Shop | Order History | Orders table'            ← name: App | Area | What
  BusinessType = HtmlDocument, InterfaceType = GUI
  parameters
    Engine = Html                    [Configuration]    ← mandatory on the module and on every attribute
    Title  = 'Shop - Orders*'        [TechnicalId]      ← identifies the PAGE (browser tab); wildcarded, never the exact title (`*` only when the case guarantees one app tab); add Url = 'https://host*' if titles clash
    ControlFramework = None          [Steering]
  attributes (tree)
    'Page title'            GenericGUI   Tag=H1                                            [TechnicalId]
    'Search orders'         TextBox      Tag=INPUT, attributes_data-test-id=orders.search  [TechnicalId]
                                         FireEvent=change                                  [Steering]
    'Export'                Button       Tag=BUTTON, attributes_data-test-id=orders.export [TechnicalId]
    'Loading spinner'       Container    Tag=DIV, ClassName=spinner*                       [TechnicalId]
    'Orders table'          Table        Tag=TABLE, Id=orders                              [TechnicalId]
                                         HeaderRow=1, DecisiveColumns=*                    [Steering]
      '<Row>'               Row          (placeholder: the step names the row)
        '<Cell>'            Cell         (placeholder: the step names the column)
```

| Part | Meaning | Commander | Cloud JSON |
|---|---|---|---|
| Module | One page/screen/message | `XModule` (`Name`, `BusinessType`, `InterfaceType`) | module root: `name`, `businessType`, `interfaceType: "Gui"`, `metadata.engine` |
| Module parameters | Identify the page and configure the engine | `XParam`s on the module | root `parameters[]` with `type` |
| Attribute | One control (or container of controls) | `XModuleAttribute` (`Name`, `BusinessType`, `DefaultActionMode`, `DefaultDataType`, `Cardinality`, `ValueRange`) | `attributes[]`: `name`, `businessType`, `defaultActionMode`, `defaultDataType`, `cardinality`, `valueRange` |
| Child attributes | Controls inside a container / table | nested `XModuleAttribute`s | nested `attributes[]` |
| Parameter kind | see below | `XParam.ParamType` | `parameters[].type` |

Three kinds of parameters, on the module and on each attribute:

| Kind | Answers | Typical entries |
|---|---|---|
| **TechnicalId** (identification) | How do I find it, uniquely? | Html: `Tag`, `Id`, `Name`, `InnerText`, `Title`, `ClassName`, `HREF`, any HTML attribute as `attributes_<name>`. SAP: `RelativeId`. API: `Path` + `PathType` |
| **Steering** | How do I drive it? | `FireEvent`, `WaitBefore`/`WaitAfter`, `HeaderRow`, `DecisiveColumns`, `IgnoreInvisibleHtmlElements`, `UserSimulation` |
| **Configuration** | Which engine, how to search? | `Engine`, `BusinessAssociation`, `ConstraintIndex` (n-th match), `ExplicitName` |

What makes a module good:

- **One page or one section**, named `App | Area | What`, roughly up to 20 controls, attributes in the order a user meets them. Shared parts (header, spinner, cookie banner) get their own small module with a wildcard `Title`.
- **Each attribute matches exactly one element.** Combine `Tag` with one or two stable anchors. Stability order: test-ID attribute (`attributes_data-test-id`) or `Id` → `Name` / `Title` → `InnerText` → `ClassName` → index. Generated classes (`ng-star-inserted`, hashes), `style_*` and positions are the last resort.
- **TechnicalId values can be dynamic**: wildcards (`Shop - Orders*`), `{REGEX["a|b"]}` for variants, and buffers (`ConstraintIndex = {B[RowNo]}`) so a step chooses the element at run time.
- **Tables** expose `<Row>` / `<Col>` / `<Cell>` placeholders instead of one attribute per cell. If the page isn't a real table, scanned modules model rows as nested containers with `ConstraintIndex`; mark index-based locators as fragile.
- **Attribute defaults** carry intent: `DefaultActionMode` Input for controls, Select for containers, Verify for read-only texts; `DefaultDataType` Password for secrets; `ValueRange` for the allowed values (`X`, `{CLICK}`, `True;False`).
- **Every Html control attribute also carries `Engine = Html` and `BusinessAssociation = Descendants` as Configuration params** (not shown per attribute above; table placeholders use `Rows` / `Columns` / `Cells`). Same on Commander and Cloud. Scans add them; hand-built attributes need them explicitly ([commander-field-notes.md](commander-field-notes.md) §3).
- `ClassName` is the element's full class string with wildcards for dynamic tokens, never a single token picked from a visual read.
- Module attributes come from a scan (XScan / Cloud scanner) or from the explorer's verified inventory. Never invent a locator.

## 3. A test case, complete

```
TEST CASE 'Customer manager submits a pick-up order'
  test configuration parameters (own or inherited)      URL, Browser, UserName, UserPassword(Password type)

  FOLDER 'Precondition'
    CALL BLOCK 'Shop | Login'                           Url={CP[URL]}  User={CP[UserName]}  Password={CP[UserPassword]}
    STEP 'Prepare test data' → TBox Set Buffer
        <Buffername> name='ProductName' = 'Wall paint'          [Input]
        <Buffername> name='Quantity'    = '2'                   [Input]

  FOLDER 'Process'
    CALL BLOCK 'Shop | Add product to cart'             ProductName={B[ProductName]}  Quantity={B[Quantity]}
    FOLDER 'Checkout'
      STEP 'Proceed to checkout' → Shop | Cart
          Proceed to checkout = X                               [Input]
      STEP 'Wait for review page' → Shop | Review order
          Header.Visible = True                                 [WaitOn]
      STEP 'Submit order' → Shop | Review order
          Pick-up option = X                                    [Input]
          Submit         = X                                    [Input]
      STEP 'Wait until spinner is gone' → Shop | Loading spinner
          Spinner.Exists = False                                [WaitOn]

  FOLDER 'Verification'
    STEP 'Order confirmed' → Shop | Order success
        Confirmation.InnerText = 'Thank you for your order*'    [Verify]
        Order number           = OrderNo                        [Buffer]     ← value = buffer NAME
    STEP 'Order is in history' → Shop | Order History | Orders table
        Orders table = {NULL}                                   (container)
          <Row> = {NULL}                                        (container)
            <Cell> name='Order number' = {B[OrderNo]}           [Constraint] ← pick the row
            <Cell> name='Status'       = 'Submitted'            [Verify]     ← check it

  FOLDER 'Postcondition'
    CALL BLOCK 'Shop | Logout and close browser'

  RECOVERY / CLEANUP SCENARIO     close browser (so an aborted run leaves no session behind)
```

| Part | Meaning | Commander | Cloud JSON |
|---|---|---|---|
| Test case | The scenario | `TestCase` (`Name`, `TestCaseWorkState`) | root: `name`, `workState`, `testCaseItems[]` |
| TCPs | Environment and credentials, read as `{CP[x]}` | Test Configuration Parameters on the case or an ancestor folder | `testConfigurationParameters[]` (Password entries have no `value`) |
| Folder | Phase or sub-flow; nests freely | `TestStepFolder` | `{"$type": "TestStepFolderV2", "name", "items[]"}` |
| Step | One use of one module | `XTestStep` → `Module` | `{"$type": "TestStepV2", "name", "moduleReference", "testStepValues[]"}` |
| Value | One attribute: value + action | `XTestStepValue` → `ModuleAttribute`; `Value`, `ActionMode`, `ActionProperty`, `Operator`, `DataType`, `ExplicitName` | `testStepValues[]`: `value`, `actionMode`, `actionProperty`, `operator`, `dataType`, `explicitName`, `moduleAttributeReference` |
| Nested value | Value on a child attribute | `SubValues` | `subValues[]` |
| Block call | Reuse with arguments | `TestStepFolderReference` + parameter references | `{"$type": "TestStepFolderReferenceV2", "reusableTestStepBlockId", "parameterLayerId", "parameters[]"}` |
| If / loop | Branching | `TestCaseControlFlowItem` with Condition / Then / Else / Loop folders | `{"$type": "ControlFlowItemV2", "statementTypeV2", "condition", "conditionPassed"}` |
| Recovery / cleanup | Runs on failure / at the end | Recovery scenario collection on a folder | `recoveryScenarioCollection` on the case |

How to read a value line: **`Attribute.Property = value [ActionMode]`**.

| ActionMode | The value is | Example |
|---|---|---|
| Input | What to type or do: text, `True`, `X` (click; `{CLICK}` only when mouse emulation is needed) | `Submit = X` |
| Verify | The expected content (`.Property` picks what to compare) | `Status.InnerText = 'Submitted'` |
| WaitOn | The state to wait for | `Spinner.Exists = False` |
| Buffer | The **name** of the buffer to fill | `Order number = OrderNo` |
| Constraint | The content that selects this row / item | `<Cell> 'Order number' = {B[OrderNo]}` |
| Select | Nothing or a path; opens a container / picks a node | `Orders table = {NULL}` |
| Insert | API request content | `Authorization = 'Bearer {B[Token]}'` |

Rules that hold in every well-built case:

1. **A step uses exactly one module; a value targets exactly one attribute of that module.** Nested values follow the module's attribute tree: to reach a cell you go table → row → cell.
2. **Only the attributes you need get a value.** A step on a 20-attribute module may have two values. Related actions on one page go into one step (fill user + password + click).
3. **`ExplicitName` names the concrete target of a placeholder attribute**: the column or row of `<Cell>` / `<Row>`, the buffer of `<Buffername>`.
4. **Data flows through buffers and parameters, not literals**: environment and credentials `{CP[x]}`; values produced during the run `[Buffer]` → `{B[x]}`; block arguments `{PL[x]}` inside the block; sheet data `{XL[x]}` in templates only.
5. **Every action that makes the app work is followed by a WaitOn** on something that proves it finished (next page's header, spinner gone). Static `TBox Wait` steps are a smell.
6. **Each test case is self-contained**: it logs in, creates or finds its own data, and cleans up.
7. **Verifications are explicit steps** in a place a reader can find (a Verification folder, or right after the action in the team's convention). Never weaken one to get a green run.

## 4. A reusable block, complete

```
LIBRARY 'Shop libraries'
  BLOCK 'Shop | Login'            business parameters: Url, User, Password
    CALL BLOCK 'Common | Close and open browser'      Url={PL[Url]}
    STEP 'Wait for page' → Shop | Loading spinner     Spinner.Exists = False [WaitOn]
    IF  Condition  STEP → Shop | Cookie banner        Accept.Visible = True  [Verify]
        Then       STEP → Shop | Cookie banner        Accept = X             [Input]
    STEP 'Log in' → Shop | Login page
        User     = {PL[User]}       [Input]
        Password = {PL[Password]}   [Input]
        Log in   = X                [Input]
    STEP 'Logged in' → Shop | Top bar                 Account menu.Visible = True [WaitOn]
```

| Part | Commander | Cloud JSON |
|---|---|---|
| Block | `ReuseableTestStepBlock` in a `TestStepLibrary` | reusable block (`blocks` API) |
| Parameters | "Business Parameters" layer → `Parameter`s | `businessParameters[]`, `parameterLayerId` |
| Argument at the call | `ParameterReference.Value` | `parameters[].value` + `referencedParameterId` |

Blocks hold the steps; callers hold the data. A block may call other blocks and contain the If for optional popups. Create a block when the sequence is reused; name it `App | What it does`.

## 5. Check your result against this list

- [ ] Module: `Engine` on the module and every attribute; page identity (`Title`/`Url`, or SAP transaction/program/screen) on the module; every attribute proven unique on the live page.
- [ ] Every step points to an existing module, every value to an attribute of that same module; nested values follow the attribute tree.
- [ ] ActionMode fits the intent; Verify / WaitOn carry the right property (`Visible`, `Exists`, `InnerText`…); Buffer values hold a buffer name.
- [ ] No literal URLs, users, passwords or environment values in steps; secrets are Password-type TCPs.
- [ ] Every `{B[x]}` was written earlier in the same case; every `{PL[x]}` is a parameter of the enclosing block; every `{CP[x]}` exists on the case or above it.
- [ ] Waits are WaitOn; optional elements are wrapped in an If; loops have a repetition cap.
- [ ] Block calls pass every parameter the block needs.
- [ ] The case starts from a clean state and leaves one (Postcondition + recovery).

## 6. Look at a real one before you build

The user's own objects beat this file. Read one similar test case and the module it uses on the target, and copy its conventions:

| Runtime | Test case | Module |
|---|---|---|
| Commander MCP | `get_object_info` (children) + `get_attributes` | same, on the module and its attributes |
| TCShell / TCAPI / REST | TQL search, then attribute reads ([commander-authoring-apis.md](commander-authoring-apis.md)) | same |
| Cloud | `tosca_cli.py cases get --json <id>` / `cases steps <id> --json` | `tosca_cli.py modules get --json <id>` |
| A `.tsu` export | `tsu_inspect.py <file> tree "<name>"` | `tsu_inspect.py <file> modules` |
