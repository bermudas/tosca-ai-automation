# SAP GUI Automation (SapEngine) — Detailed Guide

## SAP engine vs Html engine

| Property | Html engine | SAP engine |
|----------|------------|------------|
| Module `businessType` | `HtmlDocument` | `Window` |
| `interfaceType` | `Gui` | `Gui` |
| Attribute Engine param | `Html` | `SapEngine` |
| TechnicalId locator | `Tag`, `InnerText`, `HREF`, `ClassName` | `RelativeId` |
| Window/screen binding | `Url` / `Title` TechnicalIds | Root quartet: `Engine`/`Transaction`/`ProgramName`/`ScreenNumber` |
| Browser config param | `Browser: Chrome/Edge/Firefox` | **None** |
| Session startup | `OpenUrl` standard module | Precondition reusable block |
| Session teardown | `CloseBrowser` standard module | Postcondition reusable block (`ccd86083…`) |

## Standard SAP framework modules (not in Inventory)

These are engine-provided. Use their IDs directly — never search `inventory` for them.

| Step | Module ID | Attribute | Attr ref ID | Notes |
|------|-----------|-----------|-------------|-------|
| `Close SAP Logon` | `1b9ae625-f924-4837-89b4-63da94bbd701` | `Path` | `39e342b2-958e-f3b9-4561-e4b466384784` | Value: `taskkill` |
| same | same | `Arguments` | `39e342b2-958e-8357-d519-dc29dbb4d77f` | `actionMode: "Select"`; see `subValues` |
| same | same | `Argument` (subValue) | `39e342b2-958e-b1d9-61c7-6718ae8be275` | `/f`, `/im`, `saplogon.exe` |
| `SAP Logon` | `3c3b1139-48a5-4ad0-a33c-72b3cbbc30f7` | `SapLogonPath` | `39e342b2-961b-0690-437e-9ff959a98288` | Path to `saplogon.exe` |
| same | same | `SapConnection` | `39e342b2-961b-3ba0-e24a-644888d69eeb` | Connection name in Logon Pad |
| `SAP Login` | `24437bbe-dcd2-441c-bdd4-37537c0bde99` | `Client` | `39e342b2-961b-4340-b56e-50e7fd7f1bab` | Client number |
| same | same | `User` | `39e342b2-961b-d3b0-29f7-fae93ac1f0e3` | Use `{CP[Username]}` |
| same | same | `Password` | `39e342b2-961b-4754-ea0c-ebc747c29cd0` | `dataType: "Password"` |
| same | same | `Enter` | `39e342b2-961b-ef6e-24bf-07d5c81dc707` | Value `"X"` to click |
| `T-code` | `35fcfe84-c373-4b53-869b-604af40a689e` | `Transaction code` | `39e342b2-961b-de12-c278-888795c3d7dc` | Value `"/n<TCODE>"` — see Run-transaction convention below |
| same | same | `Buttons` | `39e342b2-961b-bff2-cf38-9a91cd40a637` | Value `"Enter"` to confirm |
| `Wait` | `80b7982e-0e10-4bc0-bdf3-6bc04503fd63` | `Duration` | `39e342b2-958e-ba1f-bb58-702e193d6016` | ms; `dataType: Numeric` |
| `StatusBar` (verify message / capture doc nr) | `aca7c8ee-b916-4978-b658-95a26bd02722` | `Message` | `39e4abe9-685a-f2b0-777b-3f8c21d181f2` | businessType `StatusBar`, valueRange `["{Click}", "{Doubleclick}"]`, module `isRescanEnabled: false`. Verify value with embedded `{XB[Buf]}` extracts the SAP document number: `"Standard PO created under the number {XB[PurchaseOrder]}"` |
| `SubToolBar` (application toolbar menu) | `d82fd0e7-fd5f-40e7-a4d7-d3ab87086683` | `SubToolBar` | `39e342b2-961b-b9af-9ac8-e38e5e5ea37c` | businessType `Menu`, module `isRescanEnabled: false`. Value = wildcard button label: `"Save*"`, `"Post*"`, `"Execute*"`, `"Print Report*"`, `"Microsoft Excel*"` |

### packageReference on standard-module steps

Steps that use Sap Standard modules must carry `"packageReference": {"id": "Sap", "type": "Standard"}` on **both** the step's `moduleReference` AND every `moduleAttributeReference`:

```json
"moduleReference": {"id": "35fcfe84-c373-4b53-869b-604af40a689e", "packageReference": {"id": "Sap", "type": "Standard"}, "metadata": {"isRescanEnabled": true, "engine": "SapEngine"}},
"testStepValues": [{"name": "Transaction code", "value": "/n<TCODE>", "actionMode": "Input", "dataType": "String", "actionProperty": "", "operator": "Equals", "moduleAttributeReference": {"id": "39e342b2-961b-de12-c278-888795c3d7dc", "moduleId": "35fcfe84-c373-4b53-869b-604af40a689e", "packageReference": {"id": "Sap", "type": "Standard"}, "metadata": {"businessType": "TextBox", "isUsedAsIdentification": false, "valueRange": ["{Click}", "{Doubleclick}", "{Rightclick}"]}}, "subValues": [], "id": "<fresh-ULID>", "disabled": false}]
```

How to tell standard from scanned in existing JSON: standard attributes have UUID-format ids (Sap-package ones share `39e…` prefixes; other packages differ — e.g. BasicWindowOperations attrs include `3a12cc32-…`) and carry `packageReference` on every reference; scanned (user) module attributes have tenant-minted 26-char ULID ids and NO `packageReference`. Windows-dialog/screenshot/send-keys steps use `{"id": "BasicWindowOperations", "type": "Standard"}` with `metadata.engine: "Framework"`.

## Precondition reusable block (always the first testCaseItem)

Block ID: `b0e929fa-1038-4246-9ab7-b4878f41d66e`

Handles: `taskkill saplogon.exe` → Wait 5s → SAP Logon → SAP Login.

**Never inline these steps** — always reference this block.

### Business parameter IDs

| Param | ULID |
|-------|------|
| `SapLogonPath` | `01KHJSJ4D4AY1BG2KDK4BAK1TD` |
| `SapConnection` | `01KHJSJ6H4EVTFQVGTKSVGA05G` |
| `Client` | `01KHJSJ8TFB32TV3W42JFMYCFN` |
| `User` | `01KHJSJB7H6QNQER4WK6P5NS8N` |
| `Password` | `01KHJSJDM36KRJHSBV5PRN8035` |

### testCaseItem[0] template (as observed in all production SAP cases)

```json
{
  "$type": "TestStepFolderReferenceV2",
  "reusableTestStepBlockId": "b0e929fa-1038-4246-9ab7-b4878f41d66e",
  "parameterLayerId": "01KHJSJ1DTC8N6ZYF59BJ6DQ8P",
  "parameters": [
    {"id": "<fresh-unique-id>", "name": "SapLogonPath",  "value": "C:\\Program Files (x86)\\SAP\\FrontEnd\\SAPgui\\saplogon.exe", "referencedParameterId": "01KHJSJ4D4AY1BG2KDK4BAK1TD", "parameters": []},
    {"id": "<fresh-unique-id>", "name": "SapConnection", "value": "<connection name from Logon Pad>", "referencedParameterId": "01KHJSJ6H4EVTFQVGTKSVGA05G", "parameters": []},
    {"id": "<fresh-unique-id>", "name": "Client",        "value": "<client nr>",     "referencedParameterId": "01KHJSJ8TFB32TV3W42JFMYCFN", "parameters": []},
    {"id": "<fresh-unique-id>", "name": "User",          "value": "{CP[Username]}",  "referencedParameterId": "01KHJSJB7H6QNQER4WK6P5NS8N", "parameters": []},
    {"id": "<fresh-unique-id>", "name": "Password",      "value": "{CP[Password]}",  "referencedParameterId": "01KHJSJDM36KRJHSBV5PRN8035", "parameters": []}
  ],
  "id": "<fresh-ULID>",
  "name": "Precondition_Reference",
  "disabled": false
}
```

Notes:
- `parameterLayerId` is the **block's** layer id — copy `01KHJSJ1DTC8N6ZYF59BJ6DQ8P` verbatim (identical in every production case referencing this block); do NOT mint a fresh one. When a referenced block has no parameters (e.g. the Postcondition block `ccd86083-5b30-4897-b8df-4963c6e151b7`), the reference carries no `parameterLayerId` at all — the rule is "mirror the block", not "always present".
- Every parameter entry carries `name` (byte-for-byte from the block's parameter name) and a nested empty `parameters: []`.
- Parameter-entry `id`s just need to be fresh and unique — production cases contain both UUIDs and ULIDs; a fresh ULID is fine.
- Reference naming convention: `<Block name>_Reference` with the block name copied byte-for-byte — e.g. `Precondition_Reference`, `Postcondition_Reference`, and `AS01 - Register fixed asset master record _Reference` (the trailing space before `_Reference` is preserved from the block name).

## Test case configuration (no Browser param)

```json
"testConfigurationParameters": [
  {"name": "Username", "value": "your_user", "dataType": "String"},
  {"name": "Password", "dataType": "Password", "password": {"id": "<encryptedId>"}}
]
```

## Case root skeleton — Precondition / transaction chapters / Postcondition

Production SAP cases always sandwich the flow between the logon and teardown blocks:

```
testCaseItems:
[0]    TestStepFolderReferenceV2 "Precondition_Reference"   → SAP-logon block  b0e929fa-1038-4246-9ab7-b4878f41d66e
[1..n] one chapter per SAP transaction, named "<TCODE> - <business intent>", realized as EITHER:
         • TestStepFolderV2 (inline chapter)
             ├── TestStepFolderV2 "Process"        (actions; FIRST step is always "Run transaction <TCODE>")
             └── TestStepFolderV2 "Verification"   (optional; assertions, {XB[...]} document-number captures, PDF checks)
         • TestStepFolderReferenceV2 "<TCODE> - <business intent>_Reference" → per-transaction reusable block
           (with parameterLayerId + parameters when the block declares business parameters)
[last] TestStepFolderReferenceV2 "Postcondition_Reference"  → Postcondition teardown block ccd86083-5b30-4897-b8df-4963c6e151b7
```

The Postcondition block (`ccd86083…`, named "Postcondition") is session teardown, not a GUI logoff: `Close SAP Logon` (taskkill saplogon.exe) → Wait 5 s. It takes no parameters.

Template-family variant (data-driven matrices): a single root folder `"Process"` holds one block reference per transaction in business-flow order (VA01 → VL01N → VL02N → VF01 → VA03), plus a root folder `"Verification"` with one inline TestStepV2. Folder nesting never exceeds chapter → Process/Verification → steps. A single-transaction case is simply the same skeleton with n = 1 chapter.

### Postcondition reference — minimal parameterless form

```json
{"$type": "TestStepFolderReferenceV2", "reusableTestStepBlockId": "ccd86083-5b30-4897-b8df-4963c6e151b7", "parameters": [], "id": "<fresh-ULID>", "name": "Postcondition_Reference", "disabled": false}
```

Note: when `parameters` is `[]` the `parameterLayerId` key is **absent** — never send it empty.

### "Run transaction" step convention

T-code standard module `35fcfe84-c373-4b53-869b-604af40a689e`: `Transaction code` = `"/n<TCODE>"` (the `/n` prefix aborts any pending transaction; namespaced codes work: `"/n/CBY/INCOME_FOS"`), `Buttons` = `"Enter"`. Step name: `"Run transaction <TCODE>"` (no `/n` in the name; namespaced codes keep their own leading slash: `"Run transaction /CBY/INCOME_FOS"`).

### Step naming conventions

Short imperatives (`"Click Save"`, `"Fill in initial data"`); buffer-writing steps prefixed `"---> BUFFER: <BufName>"` or suffixed `"(BUFFER)"` when the capture rides on a Verify (`"Verify that Purchase Order created (BUFFER)"`); If-items named `"If <situation>"` (e.g. `"If Header collapsed"`, `"If initial pop up is shown"`).

## Module-level screen identification — the root parameter quartet (REQUIRED)

Every SapEngine **screen module** (`businessType: "Window"` — initial screens, overview screens, popups) identifies its window via four root-level `parameters`, all `"type": "Configuration"`, each with its own fresh ULID `id`. There is **no RelativeId at module level** — the window binds on Transaction + ProgramName + ScreenNumber (plus an optional Caption, below). This quartet is the SapEngine analogue of the Html module's `Url`/`Title` TechnicalIds. Array order is not significant — match by name.

```json
"parameters": [
  {"id": "<ulid>", "name": "Engine",       "value": "SapEngine",        "type": "Configuration"},
  {"id": "<ulid>", "name": "Transaction",  "value": "<TCODE>",          "type": "Configuration"},
  {"id": "<ulid>", "name": "ProgramName",  "value": "<ABAP program>",   "type": "Configuration"},
  {"id": "<ulid>", "name": "ScreenNumber", "value": "<dynpro number>",  "type": "Configuration"}
]
```

Rules distilled from expert artifacts:
- **ProgramName/ScreenNumber must be read from the actual screen** (SAP GUI: System → Status, or F1 → Technical Info), never guessed — e.g. AW01N's program is literally `AW01N`, not `SAPL...`. Observed shapes: module pools `SAPM...`/`SAPL...` (`SAPMFCJ0`, `SAPLMEGUI`), plain reports (`RMMR1MDI`, `RFBILA00`, `RABEST_ALV01`), custom-namespace programs (`/CBY/FOS_INCOME_N`), system programs (`SAPMSSY0`, `SAPMSDYP`, `SAPLSPO2`). Selection screens are usually `1000`; ALV fullscreen `500` (`SAPLSLVC_FULLSCREEN`); ABAP list output `SAPMSSY0`/`120`. ScreenNumber is an unpadded string (`"1"`, `"50"`, `"14"`, `"120"`).
- Production examples: `VF03 | Display Invoice` → `Transaction=VF03, ProgramName=SAPMV60A, ScreenNumber=104`; `FBCJ | Cash Journal | Tabs` → `SAPMFCJ0` / `100`; namespaced T-codes work verbatim (`/CBY/INCOME_FOS` → `ProgramName=/CBY/FOS_INCOME_N, ScreenNumber=1000`); `ME21N | Save Document pop up` → `SAPLSPO2` / `101`.
- **Every popup / follow-on screen is its own Window module with its own quartet.** System-program **popups** keep `Transaction = <invoking T-code>` even though their ProgramName is a system program (Information popup → `SAPMSDYP`/`10`; standard save prompt → `SAPLSPO2`/`101`; message list → `SAPMSSY0`/`120`). But a **drill-down that is really another transaction** carries the *target* T-code, not the invoking one: the Display Document view opened from AW01N binds as `Transaction=FB03`, `SAPMF05L`/`750` — identical to the standalone FB03 module. Read the current transaction off the actual screen (System → Status); don't assume it's the T-code you typed.
- A `Transaction` wildcard is legal for shared initial screens: `"VA0*"` matches VA01/VA02/VA03 on the shared `SAPMV45A`/`101` dynpro.
- **Generic popups can add a fifth parameter** — when the program/screen pair is a shared generic popup (e.g. `SAPMSDYP`/`10`, used for many information dialogs), the quartet alone is ambiguous. Add a caption entry alongside it: `{"id": "<ULID>", "name": "Caption", "value": "Information*", "type": "BusinessId"}` (trailing `*` wildcard on the window caption). This is the only place the `BusinessId` parameter type appears.
- Root `metadata` must be `{"isRescanEnabled": true, "engine": "SapEngine"}` — `metadata.engine` always duplicates the root `Engine` parameter's value.
- **Exception — control-node helper modules have no quartet.** SapEngine control-helper modules such as `TableTreeNode` (`businessType: "TreeNode"`) carry instead: `Engine=SapEngine` (`Configuration`), `BusinessAssociation=Nodes` (`Configuration`), and `ExplicitName=True` (`Steering`). Only screen/window modules get the quartet.
- **The Engine parameter lives in BOTH places** — once at module root (part of the quartet) and once inside every attribute's `parameters[]`; attributes repeat `Engine=SapEngine` at every nesting depth. Attribute-level `parameters[]` are unchanged by the root quartet: each attribute still carries its own `Engine=SapEngine` + `RelativeId` (`TechnicalId`), plus `BusinessAssociation=Descendants` where applicable — the root quartet does not replace them.

## Full module + attribute anatomy (authoring checklist)

**Module root** — exact key set (identical across every expert-authored artifact), nothing more:

```json
{
  "id": "<uuid4-lowercase>",
  "name": "<TCODE> | <Screen Title>[ | <Subscreen / popup name>[ pop up]]",
  "description": "",
  "version": 0,
  "businessType": "Window",
  "interfaceType": "Gui",
  "attributes": [ "<attributes>" ],
  "tcProperties": [],
  "parameters": [
    {"id": "<ulid>", "name": "Engine",       "value": "SapEngine", "type": "Configuration"},
    {"id": "<ulid>", "name": "Transaction",  "value": "ME21N",     "type": "Configuration"},
    {"id": "<ulid>", "name": "ProgramName",  "value": "SAPLMEGUI", "type": "Configuration"},
    {"id": "<ulid>", "name": "ScreenNumber", "value": "14",        "type": "Configuration"}
  ],
  "attachments": [{"id": "<ulid>", "name": "Screenshot.png", "blobId": "<tenant-uuid>_<ulid>"}],
  "metadata": {"isRescanEnabled": true, "engine": "SapEngine"}
}
```

- `description` is always `""`; `tcProperties` always `[]`. `version` is a server-managed counter — write `0` when authoring.
- Root `parameters` is the `Engine`/`Transaction`/`ProgramName`/`ScreenNumber` quartet on virtually every `Window` module; some popup modules add a fifth `Caption` parameter. (Rescan also produces rare standalone `businessType: "TreeNode"` sub-modules whose root parameters are `BusinessAssociation`/`Engine`/`ExplicitName` with no attachment — don't use those as templates.)
- Scanner-produced `Window` modules carry exactly one root attachment (`Screenshot.png`; `blobId` = constant tenant UUID + `_` + fresh ULID). When authoring via API you may omit the attachment, but never put attachments on attributes — attribute-level `attachments` are always `[]` at every depth.

**ID conventions**: module root `id` (and any `referencedModule.id`) is a lowercase UUIDv4. Every attribute `id`, parameter `id`, and attachment `id` at every depth is a 26-char Crockford-base32 ULID — generate a fresh one per element (the CLI's `_generate_ulid()`).

**Attribute scaffold** — leaf-control shape (TextBox/Button/CheckBox/RadioButton/ComboBox/TabControl/Table):

```json
{
  "id": "<ulid>",
  "name": "<exact on-screen label, verbatim incl. punctuation/hotkey e.g. \"Cont. (Enter)\", \"Display <-> Change (Ctrl+F1)\">",
  "description": "",
  "businessType": "<archetype>",
  "defaultValue": "",
  "defaultActionMode": "<Input|Select|Verify — see mapping below>",
  "defaultDataType": "String",
  "defaultOperator": "Equals",
  "valueRange": [ "<per-archetype — see mapping below>" ],
  "isVisible": true,
  "isRecursive": false,
  "specialIcon": "",
  "cardinality": "ZeroToOne",
  "interfaceType": "Gui",
  "parameters": [
    {"id": "<ulid>", "name": "BusinessAssociation", "value": "Descendants", "type": "Configuration"},
    {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"},
    {"id": "<ulid>", "name": "RelativeId", "value": "<path>", "type": "TechnicalId"}
  ],
  "attributes": [],
  "attachments": [],
  "metadata": {"businessType": "<same as archetype>", "isUsedAsIdentification": false, "valueRange": [ "<byte-identical copy>" ]}
}
```

**Field-presence variations** (the scaffold above is NOT literally universal):
- **Row / Column / Cell / TableTreeNodeCell** have NO `valueRange`; instead they carry `"isExplicitNameAllowed": true` + `"explicitNameRange": [...]` (inserted between `specialIcon` and `cardinality`), and their `parameters` are `BusinessAssociation` (`Rows` / `Columns` / `Cells`) + `Engine` + `ExplicitName` — **no `RelativeId`**. The `ExplicitName` parameter value is the `explicitNameRange` entries joined with `;`. Row range is the selector set `$1;$<n>;$last;$header;$firstEmptyRow;$lastContentRow`; Column range is `$1;$<n>;$last` + the literal column captions. A `<Cell>` under `<Row>` gets the column-caption range; a `<Cell>` under `<Col>` gets the row-selector range.
- **Table** keeps the standard triple but adds Steering parameters: `IgnoreInvisibleTableContent=True`, `DecisiveColumns=*`, `HeaderRow=1` (type `"Steering"`); plain-table variants may also carry `HeaderLineCount`, `ContentLineCount`, `TableStartLine`.
- **TreeNode / TableTree** have neither `valueRange` nor `explicitNameRange`. TreeNode parameters: `BusinessAssociation=Nodes` + `Engine` + `ExplicitName`; TableTree: standard `Descendants`/`Engine`/`RelativeId` triple.
- **ControlGroup** has no `valueRange`, no `interfaceType`, and `parameters: []` — the child Button attributes carry the locators.
- **TrafficLight** has no `interfaceType` and no `RelativeId` (parameters: `BusinessAssociation=Descendants` + `Engine` only).

**metadata echo rule**: every attribute's `metadata` restates `businessType` + `isUsedAsIdentification: false`, plus a **byte-identical copy** of `valueRange` (when the attribute has one) or `isExplicitNameAllowed: true` + a copy of `explicitNameRange` (explicit-name nodes). Ranges are always written twice — keep both copies in sync. Two businessType-rename exceptions: **ControlGroup** echoes `"businessType": "ButtonGroup"` and **TableTreeNodeCell** echoes `"businessType": "Cell"`; everything else echoes the same value.

**Fixed per-businessType defaults** (pure function of businessType across all expert artifacts):

| businessType | defaultActionMode | range field / contents | cardinality | specialIcon |
|---|---|---|---|---|
| TextBox | Input | valueRange `["{Click}", "{Doubleclick}", "{Rightclick}"]` | ZeroToOne | `""` |
| Button | Input | valueRange `["{Click}"]` | ZeroToOne | `""` |
| CheckBox | Input | valueRange `["True", "False"]` | ZeroToOne | `""` |
| RadioButton | Input | valueRange `["{Click}"]` | ZeroToOne | `""` |
| ComboBox | Input | valueRange = literal dropdown option texts | ZeroToOne | `"ComboBox"` |
| TabControl | Input | valueRange = literal tab captions | ZeroToOne | `""` |
| Table | Select | valueRange `["{TableCompare}"]` | ZeroToOne | `""` |
| Row / Column | Select | explicitNameRange (no valueRange) | ZeroToN | `""` |
| Cell | Verify | explicitNameRange (no valueRange) | ZeroToN | `""` |
| TableTreeNodeCell | Verify | explicitNameRange (may be absent) | ZeroToN | `"Cell"` |
| TableTree | Input | none | ZeroToOne | `""` |
| TreeNode | Select | none | ZeroToOne | `""` |
| ControlGroup | Input | none | ZeroToOne | `"ButtonGroup"` |
| TrafficLight | Select | valueRange `["Green", "Yellow", "Red"]` | ZeroToOne | `""` |

Always: `defaultDataType="String"`, `defaultOperator="Equals"`, `defaultValue=""`, `isVisible=true`, `isRecursive=false`, `description=""`, and `interfaceType="Gui"` — `interfaceType` is ABSENT only on ControlGroup and TrafficLight. Parameter array order is never significant. Read-only display fields (totals, net value — e.g. `/usr/txtF_TOTAL_RECEIPTS`) are still authored as plain TextBox with the standard click valueRange — no Verify-flavored archetype exists at module level; verification intent lives in the test case's actionMode.

**valueRange dual semantics**: curly-brace action tokens for action controls (`{Click}`, `{TableCompare}`) vs literal selectable values for state controls (tab captions, dropdown texts, `True`/`False`, `Green`/`Yellow`/`Red`).

## RelativeId locator grammar (complete)

SAP modules do NOT use `Tag`, `InnerText`, `HREF`, or `ClassName` as TechnicalId — only `RelativeId`.

Paths are window-relative (never contain `wnd[0]` or a session prefix), `/`-separated, starting at `/usr` (user area), `/tbar[n]` (toolbar), or a shell path for ALV/tree controls (`/shellcont/shell`, `/usr/shell/…`). **Path-bearing attributes never inherit from their parent** — a nested attribute's RelativeId repeats the full path from the window root (a child under `/usr/tabsTABSTRIP_TABBL1` stores `/usr/tabsTABSTRIP_TABBL1/tabpUCOM1/…`, not a relative suffix). The only attributes without a RelativeId are structural children of a `Table` attribute (`<Row>`/`<Col>`/`<Cell>`) — those carry no `parameters[]` path at all.

| Segment / prefix | Meaning | Verbatim example |
|---|---|---|
| `/usr/` | screen user area root | — |
| `ctxt<STRUCT>-<FIELD>` | text field **with F4 value help** (SAP GuiCTextField) | `/usr/ctxtANLA-BUKRS` |
| `txt<STRUCT>-<FIELD>` | text field **without value help** (GuiTextField) — still an Input field in every observed module, not display-only | `/usr/txtRM08M-DIFFERENZ` |
| `btn<NAME>` | dynpro pushbutton | `/usr/btnSPOP-VAROPTION1` |
| `chk<STRUCT>-<FIELD>` | checkbox (observed only deep-nested, never directly under `/usr`) | `…/ssubHEADER_SCREEN:SAPLFDCB:0010/chkINVFO-XMWST` |
| `rad<FIELD>` | radio button | `/usr/radP_BEFOR` |
| `cmb<STRUCT>-<FIELD>` | combo box (`businessType: ComboBox`, actionMode Input) | `/usr/cmbRV60A-FKART` |
| `tabs<ID>` | tab strip container | `/usr/tabsF_TABSTRIP` |
| `tabp<ID>` | tab page (also `tabpT\\01` backslash-escaped ordinals) | `tabpTABHDT8`, `tabpT\\01` |
| `sub<AREA>:<PROGRAM>:<DYNPRO>` | subscreen area (colon-delimited) | `subSUB0:SAPLMEGUI:0030` |
| `ssub<AREA>:<PROGRAM>:<DYNPRO>` | tabstrip subscreen (incl. `%`-names) | `ssub%_SUBSCREEN_TABBL1:RFBILA00:0001` |
| `tbl<PROGRAM><TC_NAME>` | classic table control — program + TC name concatenated, no separator | `tblSAPLMEGUITC_1211`, `tblSAPMFCJ0FTCJ_E_POSTINGS` |
| `cntl<ID>/shellcont/shell` | ALV grid / custom control shell | `/usr/cntlGRID1/shellcont/shell` |
| `/tbar[0]/btn[n]` | system toolbar button (btn[0] = Continue/Enter) | `"/tbar[0]/btn[0]"` |
| `/tbar[1]/btn[n]` | application toolbar button | `"/tbar[1]/btn[7]"` |
| `/usr` (bare) | whole user area — used as the `Table` attribute for ABAP list-report output (AR01, F.01 message list) | `/usr` |

Field leaf names are SAP DDIC style `<STRUCT>-<FIELD>` in caps (`VBAK-AUART`, `INVFO-BLDAT`) or report select-option/parameter names on selection screens — `-LOW`/`-HIGH` suffixes (`SO_BUKRS-LOW`, `V-MONATE-HIGH`) and `P_*` parameters (`P_BUKRS`).

**Bracket-quoting rule (CRITICAL)**: iff the path contains a bracketed index `[n]`, the JSON string value is wrapped in **literal embedded double quotes**:

```json
{"name": "RelativeId", "value": "\"/tbar[0]/btn[0]\"", "type": "TechnicalId"}
{"name": "RelativeId", "value": "\"/usr/shell/shellcont[1]/shell[1]\"", "type": "TechnicalId"}
```

Index-free paths stay bare (`/usr/ctxtANLA-ANLKL`, `/shellcont/shell`). Colons, `%`, and `tabpT\\01` escapes do NOT trigger quoting. Reproduce the embedded quotes exactly or the locator breaks.

**Dynpro wildcard**: a `*` may absorb screen-variant digits inside a subscreen segment: `subSUB0:SAPLMEGUI:00*` (ME21N's SUB0 renders as 0020/0030 depending on state; the same module also uses literal `subSUB0:SAPLMEGUI:0020` alongside the wildcard form). Deep chains are normal: `/usr/subSUB0:SAPLMEGUI:00*/subSUB2:SAPLMEVIEWS:1100/subSUB2:SAPLMEVIEWS:1200/subSUB1:SAPLMEGUI:1211/tblSAPLMEGUITC_1211`. Two grids inside one custom control are disambiguated by shellcont index: `.../cntlIDC_GRID_PLAN/shellcont/shell/shellcont[0]/shell` vs `.../shellcont[1]/shell` (whole value quoted, per the bracket rule).

## Finding RelativeId values

- Copy from a similar existing module: `modules get <existingModuleId> --json`
- SAP GUI field: press `F1` → Technical Information → "Screen field" (e.g. `ANLA-ANLKL`). Prefix with `/usr/ctxt` for text fields.
- From existing test case steps: `cases steps <existingCaseId> --json` → `moduleAttributeReference.metadata`

## ComboBox / CheckBox / RadioButton archetypes

All three use the standard attribute scaffold and the Engine + BusinessAssociation=Descendants + RelativeId parameter triple; only these fields differ:

**ComboBox** — `businessType: "ComboBox"`, `specialIcon: "ComboBox"` (Button/TextBox/CheckBox/RadioButton leaves all have `specialIcon: ""`; the only other SapEngine archetype observed with a non-empty specialIcon is `TableTreeNodeCell` → `"Cell"`), RelativeId prefix `cmb`:

```json
{
  "businessType": "ComboBox", "defaultActionMode": "Input", "specialIcon": "ComboBox",
  "valueRange": ["<option text 1>", "<option text 2>", "..."],
  "parameters": [ ..., {"id": "<ulid>", "name": "RelativeId", "value": "/usr/<containers>/cmb<STRUCT>-<FIELD>", "type": "TechnicalId"} ],
  "metadata": {"businessType": "ComboBox", "isUsedAsIdentification": false, "valueRange": ["<same options>"]}
}
```

`valueRange` enumerates the **human-readable dropdown option texts verbatim** (not keys) — e.g. `"Standard PO"`, `"Goods Receipt"`. Preserve duplicates and any trailing single-space entry `" "` (the blank option) exactly as scanned. Steering the control = Input of the option text.

**CheckBox** — `businessType: "CheckBox"`, `specialIcon: ""`, `valueRange: ["True", "False"]` exactly, RelativeId prefix `chk`:

```json
{
  "businessType": "CheckBox", "defaultActionMode": "Input", "specialIcon": "",
  "valueRange": ["True", "False"],
  "parameters": [ ..., {"id": "<ulid>", "name": "RelativeId", "value": "/usr/<containers>/chk<STRUCT>-<FIELD>", "type": "TechnicalId"} ],
  "metadata": {"businessType": "CheckBox", "isUsedAsIdentification": false, "valueRange": ["True", "False"]}
}
```

**RadioButton** — `businessType: "RadioButton"`, `specialIcon: ""`, `valueRange: ["{Click}"]` (same as Button), RelativeId prefix `rad`:

```json
{
  "businessType": "RadioButton", "defaultActionMode": "Input", "specialIcon": "",
  "valueRange": ["{Click}"],
  "parameters": [ ..., {"id": "<ulid>", "name": "RelativeId", "value": "<path>/rad<FIELDNAME>", "type": "TechnicalId"} ],
  "metadata": {"businessType": "RadioButton", "isUsedAsIdentification": false, "valueRange": ["{Click}"]}
}
```

## TabControl attribute (tab strip)

`businessType: "TabControl"`, **`defaultActionMode: "Input"`** — a tab is switched by *inputting its caption* as the step value (expert case: step "Navigate to Cash receipts tab" = `actionMode: "Input"`, value `Cash receipts`). `valueRange` lists the literal tab captions verbatim; `metadata.valueRange` duplicates the list. When the Tabs row appears in a step only as the container/anchor for child values (not to switch tabs), expert cases use `actionMode: "Select"` — sometimes with an empty value (`"Fill in Business transactions and Amount"`), sometimes carrying the tab caption (`"Get Number of rows with content"` = `Select` + `Cash receipts`); both anchor forms occur in the same production case. What never occurs: switching a tab via `Select` — switching is always `Input` + caption.

```json
{
  "id": "<ulid>",
  "name": "Tabs",
  "description": "",
  "businessType": "TabControl",
  "defaultValue": "",
  "defaultActionMode": "Input",
  "defaultDataType": "String",
  "defaultOperator": "Equals",
  "valueRange": ["<Tab caption 1>", "<Tab caption 2>"],
  "isVisible": true, "isRecursive": false, "specialIcon": "",
  "cardinality": "ZeroToOne", "interfaceType": "Gui",
  "parameters": [
    {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"},
    {"id": "<ulid>", "name": "BusinessAssociation", "value": "Descendants", "type": "Configuration"},
    {"id": "<ulid>", "name": "RelativeId", "value": "/usr/tabs<TABSTRIP_ID>", "type": "TechnicalId"}
  ],
  "attributes": [ /* tab-page controls — see nesting rule below */ ],
  "attachments": [],
  "metadata": {"businessType": "TabControl", "isUsedAsIdentification": false, "valueRange": ["<Tab caption 1>", "<Tab caption 2>"]}
}
```

The tab strip's own `RelativeId` may itself sit under a `sub…/ssub…` chain, e.g. `/usr/subTABSTRIP:SAPLATAB:0100/tabsTABSTRIP100` (AS01) — copy whatever the screen scan gives you, not just `/usr/tabs…`.

**Nesting rule — children keep FULL paths.** Controls on tab pages may be nested in the TabControl's `attributes` array, but each child's `RelativeId` is always the complete path from `/usr`, repeating the `tabs<ID>/tabp<ID>/ssub<AREA>:<PROGRAM>:<DYNPRO>` chain — paths are never relative to the parent attribute:

```
/usr/tabsF_TABSTRIP/tabpTAB1/ssubF_SUBSCREEN:SAPMFCJ0:0110/tblSAPMFCJ0FTCJ_E_POSTINGS
```

Nesting encodes visual containment for humans only; steering resolution stays absolute. Both authoring styles appear in expert data and both work: (a) children nested under a TabControl attribute, or (b) flat attributes at module root whose RelativeId simply runs through `tabs.../tabp.../ssub...` with no TabControl attribute at all. The `tabp<ID>` segment in the child path is what selects the page, not the nesting.

## ControlGroup — locator-less logical grouping (NOT for toolbars)

Toolbar buttons are ordinary top-level `Button` attributes with a **quoted indexed RelativeId** — the JSON string value carries literal double quotes around the path: `"RelativeId": "\"/tbar[0]/btn[0]\""`. Any RelativeId containing `[index]` brackets is quoted this way; plain `/usr/btn…` ids are not. In the expert corpus, every `/tbar` button (14/14) is a plain Button — none live inside a ControlGroup.

`ControlGroup` is purely a **logical grouping node** for related on-screen `/usr` buttons (a period-selector row, per-tab print buttons):

```json
{
  "id": "<ulid>",
  "name": "<group label>",
  "description": "",
  "businessType": "ControlGroup",
  "defaultValue": "",
  "defaultActionMode": "Input",
  "defaultDataType": "String",
  "defaultOperator": "Equals",
  "isVisible": true,
  "isRecursive": false,
  "specialIcon": "ButtonGroup",
  "cardinality": "ZeroToOne",
  "parameters": [],
  "attributes": [ <full Button attributes with complete Engine/BusinessAssociation/RelativeId triples and FULL paths> ],
  "attachments": [],
  "metadata": {"businessType": "ButtonGroup", "isUsedAsIdentification": false}
}
```

Defining quirks (all deliberate, copy exactly):
- `parameters` is **empty** — no Engine, no RelativeId, no BusinessAssociation. The group has no locator.
- `specialIcon: "ButtonGroup"` and `metadata.businessType: "ButtonGroup"` — metadata businessType deliberately DIFFERS from the attribute's `businessType: "ControlGroup"`.
- No `valueRange` and no `interfaceType` field — in the expert corpus, ControlGroup and TrafficLight are the only attribute types without `interfaceType`; every other attribute carries `interfaceType: "Gui"`.
- Children are ordinary fully-located Buttons — each repeats the whole path from `/usr` (e.g. `/usr/tabsF_TABSTRIP/tabpTAB1/ssubF_SUBSCREEN:SAPMFCJ0:0110/btnFB_PRINT_RECEIPT_0110`) and the full parameter triple; nothing is inherited from the group.

## Table archetype — {TableCompare} + Steering trio + `<Row>`/`<Col>`/`<Cell>` triad

Covers classic table controls (`tbl...`), ALV grids (`cntl.../shellcont/shell`), and ABAP list output (bare `/usr`). The parent Table carries all steering; Row/Col/Cell descendants have **no RelativeId and no Steering** — they address purely via `BusinessAssociation` + `ExplicitName`.

```json
{
  "id": "<ulid>", "name": "<Context> Table", "description": "",
  "businessType": "Table", "defaultValue": "",
  "defaultActionMode": "Select", "defaultDataType": "String", "defaultOperator": "Equals",
  "valueRange": ["{TableCompare}"],
  "isVisible": true, "isRecursive": false, "specialIcon": "", "cardinality": "ZeroToOne", "interfaceType": "Gui",
  "parameters": [
    {"id": "<ulid>", "name": "BusinessAssociation", "value": "Descendants", "type": "Configuration"},
    {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"},
    {"id": "<ulid>", "name": "RelativeId", "value": "<full path>/tbl<PROGRAM><TC_NAME>  |  /usr/cntlGRID1/shellcont/shell  |  /usr", "type": "TechnicalId"},
    {"id": "<ulid>", "name": "HeaderRow", "value": "1", "type": "Steering"},
    {"id": "<ulid>", "name": "IgnoreInvisibleTableContent", "value": "True", "type": "Steering"},
    {"id": "<ulid>", "name": "DecisiveColumns", "value": "*", "type": "Steering"}
  ],
  "attributes": [ <Row child>, <Col child> ],
  "attachments": [],
  "metadata": {"businessType": "Table", "isUsedAsIdentification": false, "valueRange": ["{TableCompare}"]}
}
```

Exactly two children, named literally `<Row>` and `<Col>` (angle brackets included), each with one `<Cell>` child. **Transposed addressing**: the Cell under `<Row>` is addressed by column caption; the Cell under `<Col>` by row selector — giving `Table > Row($n) > Cell(ColName)` and `Table > Col(ColName) > Cell($n)`.

```json
{
  "id": "<ulid>", "name": "<Row>", "description": "", "businessType": "Row",
  "defaultValue": "", "defaultActionMode": "Select", "defaultDataType": "String", "defaultOperator": "Equals",
  "isExplicitNameAllowed": true,
  "explicitNameRange": ["$1", "$<n>", "$last", "$header", "$firstEmptyRow", "$lastContentRow"],
  "isVisible": true, "isRecursive": false, "specialIcon": "", "cardinality": "ZeroToN", "interfaceType": "Gui",
  "parameters": [
    {"id": "<ulid>", "name": "ExplicitName", "value": "$1;$<n>;$last;$header;$firstEmptyRow;$lastContentRow", "type": "Configuration"},
    {"id": "<ulid>", "name": "BusinessAssociation", "value": "Rows", "type": "Configuration"},
    {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"}
  ],
  "attributes": [{
    "id": "<ulid>", "name": "<Cell>", "description": "", "businessType": "Cell",
    "defaultValue": "", "defaultActionMode": "Verify", "defaultDataType": "String", "defaultOperator": "Equals",
    "isExplicitNameAllowed": true,
    "explicitNameRange": ["$1", "$<n>", "$last", "<Col caption 1>", "<Col caption 2>"],
    "isVisible": true, "isRecursive": false, "specialIcon": "", "cardinality": "ZeroToN", "interfaceType": "Gui",
    "parameters": [
      {"id": "<ulid>", "name": "ExplicitName", "value": "$1;$<n>;$last;<Col caption 1>;<Col caption 2>", "type": "Configuration"},
      {"id": "<ulid>", "name": "BusinessAssociation", "value": "Cells", "type": "Configuration"},
      {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"}
    ],
    "attributes": [], "attachments": [],
    "metadata": {"businessType": "Cell", "isUsedAsIdentification": false, "isExplicitNameAllowed": true, "explicitNameRange": ["$1", "$<n>", "$last", "<Col caption 1>", "<Col caption 2>"]}
  }],
  "attachments": [],
  "metadata": {"businessType": "Row", "isUsedAsIdentification": false, "isExplicitNameAllowed": true, "explicitNameRange": ["$1", "$<n>", "$last", "$header", "$firstEmptyRow", "$lastContentRow"]}
}
```

`<Col>` mirrors this with `businessType: "Column"`, `BusinessAssociation: "Columns"`, `explicitNameRange = ["$1", "$<n>", "$last", <actual column header captions in on-screen order>]`, and its `<Cell>` carrying the row-selector list. Every scanned table module includes both the `<Row>` and `<Col>` subtrees.

Rules:
- `ExplicitName` parameter value = `explicitNameRange` array joined with `;` (no spaces) — dual encoding, keep byte-in-sync.
- Column caption lists are captured **per grid, verbatim** — including abbreviations, punctuation, and duplicates (`"Item"` may appear 4x). Never dedupe or normalize.
- Row selector vocabulary is fixed: `$1`, `$<n>`, `$last`, `$header`, `$firstEmptyRow`, `$lastContentRow`.
- ALV grids get the identical Steering trio and Row/Col/Cell subtree as classic table controls — only the RelativeId differs.
- `BusinessAssociation` inside a table is structural: `Rows` / `Columns` / `Cells` (not `Descendants`). Tree controls use `Nodes` — but note a TreeNode's `ExplicitName` parameter is a **Steering** param with value `"True"` (a flag), NOT a Configuration token list like table children.
- At step time you never add attributes per row — you repeat the SAME `<Row>`/`<Cell>` attribute in `subValues[]` with different `explicitName` values (see the step-side table-addressing section).
- Only the classic dynpro control uses a `tbl` segment, and it is often nested deep inside container paths (`/usr/tabs…/ssub…/tbl…`) — the control name after the program is whatever the ABAP screen defines (`TCTRL_UEB_FAKT`, `TC_LIPS_OVER`, `TC_MR1M`, `FTCJ_E_POSTINGS`, …), not always `TCTRL_*`. Concrete examples: `/usr/tblSAPMV60ATCTRL_UEB_FAKT`, `/usr/tabs…/ssub…/tblSAPMV50ATC_LIPS_OVER`.

**ABAP list-report variant** (ProgramName `SAPMSSY0`, ScreenNumber `120`): RelativeId is bare `/usr` and three extra Steering params are added: `{"name": "TableStartLine", "value": "<first data line, e.g. 6>", "type": "Steering"}`, `{"name": "HeaderLineCount", "value": "0", "type": "Steering"}`, `{"name": "ContentLineCount", "value": "<row count>", "type": "Steering"}` (line numbers as strings). HeaderRow stays `"1"`; column captions come from the printed report header.

## TableTree archetype — ALV trees (AW01N Asset Explorer, VA03 Document Flow)

SAP ALV tree controls are modeled as a `TableTree` attribute in the transaction's Window module **plus a separate, self-referential `TreeNode` module**. Two parts, created in this order: (1) the standalone `TableTreeNode` module, (2) the `TableTree` attribute that references it.

### Part 1 — the TableTree attribute (in the Window module)

`businessType: "TableTree"`, `defaultActionMode: "Input"`, **no valueRange**, `cardinality: "ZeroToOne"`. The RelativeId is a shell path with bracket indices; bracketed shell paths are always wrapped in literal quotes inside the JSON string (corpus-invariant: every bracketed RelativeId is quoted, no unbracketed one is): `"\"/usr/shell/shellcont[1]/shell[1]\""` or `"\"/shellcont/shell/shellcont[0]/shell\""`. Exactly two children:

```json
{
  "id": "<ulid>", "name": "<tree name>", "businessType": "TableTree",
  "defaultActionMode": "Input", "defaultDataType": "String", "defaultOperator": "Equals",
  "isVisible": true, "isRecursive": false, "cardinality": "ZeroToOne", "interfaceType": "Gui",
  "parameters": [
    {"id": "<ulid>", "name": "RelativeId", "value": "\"/usr/shell/shellcont[1]/shell[1]\"", "type": "TechnicalId"},
    {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"},
    {"id": "<ulid>", "name": "BusinessAssociation", "value": "Descendants", "type": "Configuration"}
  ],
  "attributes": [
    {
      "id": "<ulid>", "name": "<Cell>", "businessType": "TableTreeNodeCell",
      "defaultActionMode": "Verify", "defaultDataType": "String", "defaultOperator": "Equals",
      "isExplicitNameAllowed": true, "isVisible": true, "isRecursive": false,
      "specialIcon": "Cell", "cardinality": "ZeroToN", "interfaceType": "Gui",
      "explicitNameRange": ["$1", "$<n>", "$last", "<TreeCol 1>", "<TreeCol 2>"],
      "parameters": [
        {"id": "<ulid>", "name": "ExplicitName", "value": "$1;$<n>;$last;<TreeCol 1>;<TreeCol 2>", "type": "Configuration"},
        {"id": "<ulid>", "name": "BusinessAssociation", "value": "Cells", "type": "Configuration"},
        {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"}
      ],
      "attributes": [], "attachments": [],
      "metadata": {"businessType": "Cell", "isUsedAsIdentification": false, "isExplicitNameAllowed": true,
                   "explicitNameRange": ["$1", "$<n>", "$last", "<TreeCol 1>", "<TreeCol 2>"]}
    },
    {
      "id": "<ulid>", "name": "TableTreeNode", "businessType": "TreeNode",
      "defaultActionMode": "Select", "defaultDataType": "String", "defaultOperator": "Equals",
      "isExplicitNameAllowed": true, "isVisible": true, "isRecursive": false,
      "specialIcon": "", "cardinality": "ZeroToOne", "interfaceType": "Gui",
      "parameters": [
        {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"},
        {"id": "<ulid>", "name": "ExplicitName", "value": "True", "type": "Steering"},
        {"id": "<ulid>", "name": "BusinessAssociation", "value": "Nodes", "type": "Configuration"}
      ],
      "attributes": [], "attachments": [],
      "referencedModule": {"id": "<uuid of the standalone TableTreeNode module>",
                           "metadata": {"isRescanEnabled": true, "engine": "SapEngine"}},
      "metadata": {"businessType": "TreeNode", "isUsedAsIdentification": false, "isExplicitNameAllowed": true}
    }
  ],
  "attachments": [],
  "metadata": {"businessType": "TableTree", "isUsedAsIdentification": false}
}
```

### Part 2 — the standalone TableTreeNode module (self-referential)

The tree node's structure lives in a **separate standalone module** referenced via `referencedModule` (a UUID) — the only cross-module reference pattern in SAP module authoring — and that module **references itself**: its own inner `TableTreeNode` attribute's `referencedModule.id` is the module's own UUID. This recursion is what models arbitrary tree depth. Create the module, then ensure the self-reference points at its own id, then point the Window module's TreeNode child (Part 1) at it.

```json
{
  "id": "<moduleUuid>", "name": "TableTreeNode", "description": "",
  "businessType": "TreeNode", "interfaceType": "Gui",
  "parameters": [
    {"id": "<ulid>", "name": "ExplicitName", "value": "True", "type": "Steering"},
    {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"},
    {"id": "<ulid>", "name": "BusinessAssociation", "value": "Nodes", "type": "Configuration"}
  ],
  "attributes": [
    {
      "id": "<ulid>", "name": "<Cell>", "businessType": "TableTreeNodeCell",
      "defaultActionMode": "Verify", "defaultDataType": "String", "defaultOperator": "Equals",
      "isExplicitNameAllowed": true, "isVisible": true, "isRecursive": false,
      "specialIcon": "Cell", "cardinality": "ZeroToN", "interfaceType": "Gui",
      "parameters": [
        {"id": "<ulid>", "name": "BusinessAssociation", "value": "Cells", "type": "Configuration"},
        {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"},
        {"id": "<ulid>", "name": "ExplicitName", "value": "True", "type": "Steering"}
      ],
      "attributes": [], "attachments": [],
      "metadata": {"businessType": "Cell", "isUsedAsIdentification": false, "isExplicitNameAllowed": true}
    },
    {
      "id": "<ulid>", "name": "TableTreeNode", "businessType": "TreeNode",
      "defaultActionMode": "Select", "defaultDataType": "String", "defaultOperator": "Equals",
      "isExplicitNameAllowed": true, "isVisible": true, "isRecursive": false,
      "specialIcon": "", "cardinality": "ZeroToOne", "interfaceType": "Gui",
      "parameters": [
        {"id": "<ulid>", "name": "Engine", "value": "SapEngine", "type": "Configuration"},
        {"id": "<ulid>", "name": "ExplicitName", "value": "True", "type": "Steering"},
        {"id": "<ulid>", "name": "BusinessAssociation", "value": "Nodes", "type": "Configuration"}
      ],
      "attributes": [], "attachments": [],
      "referencedModule": {"id": "<moduleUuid — the SAME id as this module: self-reference>",
                           "metadata": {"isRescanEnabled": true, "engine": "SapEngine"}},
      "metadata": {"businessType": "TreeNode", "isUsedAsIdentification": false, "isExplicitNameAllowed": true}
    }
  ],
  "tcProperties": [], "attachments": [],
  "metadata": {"isRescanEnabled": true, "engine": "SapEngine"}
}
```

Quirks to reproduce exactly:
- `TableTreeNodeCell` is the only attribute businessType carrying `specialIcon: "Cell"`, and its `metadata.businessType` says `"Cell"` (NOT `TableTreeNodeCell`) — a deliberate mismatch, present in every sample.
- `ExplicitName` has two distinct forms in this archetype: the `;`-joined name-list `Configuration` form on the top-level `<Cell>` (paired with an `explicitNameRange` listing `$1`, `$<n>`, `$last` plus the tree's real column headers), and the boolean flag form `"True"` with `type: "Steering"` (on every TreeNode, and on the `<Cell>` inside the standalone module, which has **no** `explicitNameRange`). One field sample (VA03) additionally carries a duplicate `ExplicitName: "True"` with `type: "Configuration"` on the TreeNode — an editing artifact; the canonical form is the three parameters shown.
- The standalone `TableTreeNode` module is the exception to the screen-module root-parameter quartet — it carries module-level `ExplicitName`/`Engine`/`BusinessAssociation` parameters instead (no Transaction/ProgramName/ScreenNumber) and has no `RelativeId` anywhere (identification comes from the parent TableTree's shell path).
- `BusinessAssociation: "Nodes"` extends the observed SAP vocabulary: `Descendants`, `Children`, `Rows`, `Columns`, `Cells`, `Nodes`.

## UIA modules — native OS dialogs in a SAP flow

The moment a SAP flow crosses into a native Windows dialog (browser File Download bar, Download complete, Save As), the popup gets its **own Window module on Engine=UIA** — never merged into the SAP screen module. Module skeleton and attribute scaffold are identical to SapEngine modules; only identification changes.

**Module root parameters** — exactly 3 (no Transaction/ProgramName/ScreenNumber), and root `metadata.engine` is `"UIA"`. Order within `parameters[]` is not significant (real artifacts vary):

```json
"parameters": [
  {"id": "<ulid>", "name": "Engine", "value": "UIA", "type": "Configuration"},
  {"id": "<ulid>", "name": "Name", "value": "<dialog title, e.g. Save As>", "type": "Transition"},
  {"id": "<ulid>", "name": "SelfHealingData", "value": "<escaped TcSelfHealingData JSON>", "type": "Steering"}
],
"metadata": {"isRescanEnabled": true, "engine": "UIA"}
```

Among SapEngine and UIA modules, `type: "Transition"` appears ONLY on this UIA window-level `Name` (window-title match) — SapEngine modules never use it. (Other engines do use Transition for other params: Pdf modules carry `DocumentLanguage` as Transition, and Html attributes can carry `XPath` as Transition — don't treat the type as UIA-exclusive tenant-wide.) The window-level SelfHealingData blob always includes `ClassName="#32770"`, `ControlTypeName="ControlType.Window"`, `FrameworkId="Win32"`, an empty-value `AutomationId`, `Orientation="OrientationType_None"`, and the title under `Name` twice (once ParamType 5, once ParamType 7) — all Weight 1.0 at window level.

**UIA attribute parameters** — 5 entries (AutomationId + Name as a TechnicalId pair):

```json
{
  "id": "<ulid>", "name": "<caption>", "businessType": "<Button|TextBox>",
  "defaultActionMode": "Input", "defaultDataType": "String", "defaultOperator": "Equals",
  "valueRange": ["{Click}"],
  "cardinality": "ZeroToOne", "interfaceType": "Gui",
  "parameters": [
    {"id": "<ulid>", "name": "BusinessAssociation", "value": "Descendants", "type": "Configuration"},
    {"id": "<ulid>", "name": "Engine", "value": "UIA", "type": "Configuration"},
    {"id": "<ulid>", "name": "AutomationId", "value": "<win32 control id>", "type": "TechnicalId"},
    {"id": "<ulid>", "name": "Name", "value": "<caption>", "type": "TechnicalId"},
    {"id": "<ulid>", "name": "SelfHealingData", "value": "<escaped blob>", "type": "Steering"}
  ],
  "metadata": {"businessType": "<same>", "isUsedAsIdentification": false, "valueRange": ["{Click}"]}
}
```

- AutomationId values are usually Win32 dialog control ids: `"1"` = default/OK/Save, `"2"` = Cancel (IDCANCEL), `"1001"` = classic file-dialog edit field, 4-digit custom ids for browser buttons. They can also be plain strings — the File Download bar's Close button has `AutomationId="Close"`.
- TextBox variant: `valueRange ["{Click}", "{Doubleclick}", "{Rightclick}"]`, SelfHealingData additionally carries `IsPasswordField=False` (ParamType 4), `ClassName "Edit"`, `ControlType.Edit`.
- SelfHealingData value is a JSON-escaped .NET-serialized string: `{"$id":"1","$type":"Tricentis.TCCore.BusinessObjects.Modules.SelfHealing.TcSelfHealingData, BusinessObjects","HealingParameters":{"$id":"2","$type":"System.Collections.Generic.List`1[[Tricentis.TCCore.BusinessObjects.Modules.SelfHealing.TcSelfHealingProperty, BusinessObjects]], System.Private.CoreLib","$values":[...]}}` where **every** `$values` entry carries its own `"$id"` and `"$type":"Tricentis.TCCore.BusinessObjects.Modules.SelfHealing.TcSelfHealingProperty, BusinessObjects"` plus `"Name":"<prop>","Surrogate":"<fresh uuid>","ParamType":<5|7|4>,"Value":"<v>","Weight":<w>`. Weights are heuristic, not fixed: identifying props (AutomationId, Name) are usually 1.0 but Name has been observed at 0.5; generic props (ClassName, FrameworkId, ControlTypeName, Orientation) are usually fractional (0.5, 0.33333, 0.16667, 0.07692, ...) but appear at 1.0 on some attributes. When building by hand, copy the weight pattern from a scanned sibling attribute rather than inventing one. SapEngine attributes never carry SelfHealingData.
- Module naming continues the flow path: `FBCJ | Cash Journal | Print Receipt | Save As pop up`. Test cases chain SapEngine and UIA modules transparently — same skeleton, same scaffold.

## TestStepV2 / testStepValue anatomy (canonical, as authored by experts)

```json
{
  "$type": "TestStepV2",
  "testStepValues": [<value entries>],
  "moduleReference": {"id": "<module-uuid>", "metadata": {"isRescanEnabled": true, "engine": "SapEngine"}},
  "reorderAllowed": false,
  "id": "<fresh-ULID>", "name": "<imperative step name>", "disabled": false
}
```

`reorderAllowed: false` appears on every TestStepV2 (never on folders). Canonical value entry:

```json
{
  "id": "<fresh-ULID>", "name": "<module attribute name>",
  "value": "<v>",                       // OMIT the whole key (absent, not null) on pure-navigation Select entries
  "explicitName": "<token>",            // only on <Row>/<Cell>-style children
  "actionMode": "Input|Verify|Buffer|Select|Constraint",
  "dataType": "String",                 // "Numeric" for {MATH}-fed buffers, "RawString" for send-keys (e.g. "^{F4}"), "Password" for password fields
  "actionProperty": "",                 // "Visible"|"Exists" for presence checks, "RowNumber" to buffer a row index
  "operator": "Equals",                 // the only operator observed; wildcards via {XB[...]} or * in value
  "moduleAttributeReference": {"id": "<attr id from module>", "moduleId": "<module-uuid>", "metadata": {"businessType": "<from module>", "isUsedAsIdentification": false, "valueRange": ["<copied verbatim from module>"]}},
  "subValues": [], "disabled": false
}
```

**metadata is echoed verbatim** from the module attribute into every usage — `businessType`, `isUsedAsIdentification`, plus whichever of `valueRange` or `isExplicitNameAllowed`+`explicitNameRange` the module attribute defines (Row/Cell attributes carry `explicitNameRange`, Table carries `valueRange: ["{TableCompare}"]`). Copy it from `modules get --json`, don't invent it.

## Hierarchical table addressing via nested subValues

Drill-down = nesting in `subValues`, each container level `actionMode: "Select"`:

```
Tabs (Select) → Table (Select, valueRange ["{TableCompare}"]) → <Row> (Select, explicitName) → <Cell> (leaf action, explicitName = column header) → optional embedded control (e.g. TrafficLight Verify "Green")
```

Rules:
- **Select `value` key**: a Select that performs a real selection carries a `value` — e.g. the Tabs container gets `value: "<tab name>"` in the first step that must switch to that tab. Pure-navigation Selects (Table containers, Rows addressed by explicitName, Tabs in later steps drilling through the already-active tab) OMIT the `value` key entirely — absent, not `null`.
- ALL `<Row>` instances in a step share ONE `moduleAttributeReference.id` (the module's single `<Row>` attribute) and are distinguished purely by `explicitName`. Same for `<Cell>` instances (explicitName = literal column header). Each subValue entry still gets its own fresh ULID `id`. Observed row tokens: `"$1"`, `"$2"`, `"$3"`, `"$lastContentRow"`, and a buffered index `"${B[RowNum]}"` — note the `$` prefix required by the buffered-index form. The module's full row grammar (`explicitNameRange`) is `$1`, `$<n>`, `$last`, `$header`, `$firstEmptyRow`, `$lastContentRow`.
- The **leaf** carries the real action: `Input` a value or `"{DOUBLECLICK}"`, `Verify` an expected value, `Buffer` a capture, `Constraint` an anchor. Row-level `Input` value `"{SELECT}"` selects the row.
- **Row-anchored verify (Constraint idiom)**: inside a `<Row>` WITHOUT explicitName, one `<Cell>` gets `actionMode: "Constraint"` with the key value (e.g. `"{B[Asset]}"`) to locate the row; sibling `<Cell>`s get `actionMode: "Verify"`.
- **Row-index capture**: `<Row>` with `explicitName: "$lastContentRow"`, `actionMode: "Buffer"`, `actionProperty: "RowNumber"`, `value: "<BufName>"` — later steps address the row as `explicitName: "${B[<BufName>]}"`.
- To scale a table verification with data, duplicate the `<Row>` subValue per data row (`"$1"`, `"$2"`, `"$3"`) — no loops; expected totals are pre-computed literals in SAP display format (comma decimals: `"25,34"`, `"50,68"`, `"76,02"`).

## SAP GUI value conventions (observed across all production SAP cases)

| Target (`businessType`) | actionMode | value |
|---|---|---|
| Button (screen / popup) | Input | `"X"` (preferred, 26x) or `"{Click}"` (8x) — both used in passing cases against valueRange `["{Click}"]` |
| ButtonGroup (standard toolbar `Buttons` attr, or module-local groups) | Input | button name: `"Enter"`, `"Back"`, `"Save"`, `"Today"` |
| Menu (standard `SubToolBar` attr) | Input | wildcard label: `"Save*"`, `"Post*"`, `"Execute*"`, `"Print Report*"`, `"Microsoft Excel*"` |
| TextBox, commit with keyboard | Input | append `{ENTER}`: `"BY01{ENTER}"`, `"{B[PurchaseOrder]}{ENTER}"`, `"{DATE[][][yyyy]}{ENTER}"` |
| Date field | Input | `"{DATE[][][dd.MM.yyyy]}"` (today, SAP display format) |
| Table `<Cell>` | Input | `"{DOUBLECLICK}"` to drill in, or literal text to type |
| Table `<Row>` | Input | `"{SELECT}"` selects the row |
| TabControl | Input | tab name (navigates); `Select` + tab name is used only when the tab is the context parent of nested Table subValues |
| CheckBox | Input | `"True"` / `"False"` (its valueRange — `{Click}` is NOT in it; only `"True"` observed) |
| RadioButton | Input | `"{Click}"` (its entire valueRange — `True`/`False` are NOT accepted) |
| ComboBox | Input | visible item text — always a member of the attribute's `valueRange` |

dataType deviations from `"String"` (only two observed in SAP cases): `"Numeric"` for values feeding `{MATH[...]}` (e.g. a Balance is buffered with `dataType: "Numeric"`, then re-entered as `"{MATH[Abs({B[Balance]})]}{ENTER}"`), and `"RawString"` for send-keys values like `"^{F4}"`. Expected literals in Verify steps use SAP display formats: comma decimals (`"0,00"`, `"25,34"`) and raw icon codes for message-type cells (`"@5B\\QInformation@"` as written in the JSON file — the runtime string has a single backslash). Thousands-dot format (`"1.000,00"`) appears only in a Pdf-engine report-verification module, not in SAP GUI steps.

## ControlFlowItemV2 — full observed shape

```json
{
  "$type": "ControlFlowItemV2",
  "statementTypeV2": "If",
  "condition": {
    "items": [
      {"$type": "TestStepV2",
       "testStepValues": [{"id": "<ULID>", "name": "<FieldName>", "value": "True", "actionMode": "Verify", "dataType": "String", "actionProperty": "Exists", "operator": "Equals", "moduleAttributeReference": {"id": "<attr-id>", "moduleId": "<module-uuid>", "metadata": {"businessType": "<bt>", "isUsedAsIdentification": false}}, "subValues": [], "disabled": false}],
       "moduleReference": {"id": "<module-uuid>", "metadata": {"isRescanEnabled": true, "engine": "SapEngine"}},
       "reorderAllowed": false, "id": "<ULID>", "name": "<check name>", "disabled": false}
    ],
    "id": "<fresh-ULID>", "name": "Condition", "disabled": false
  },
  "conditionPassed": {
    "items": [<handler TestStepV2 steps>],
    "id": "<fresh-ULID>", "name": "Then", "disabled": false
  },
  "id": "<fresh-ULID>", "name": "If <situation>", "disabled": false
}
```

Rules observed across all production cases:
- `condition` and `conditionPassed` are containers **with their own `id`, `name`, `disabled`** — named literally `"Condition"` and `"Then"`.
- There is **no else branch** — no `conditionFailed` key is ever present.
- The condition step is a plain Verify presence check: `actionProperty: "Visible"` or `"Exists"`, value `"True"` — or **inverted** value `"False"` to detect an absent/collapsed state (e.g. "If Header collapsed" → Tabs Exists = False → Then: click Expand).
- Idioms: optional-popup handler ("If initial pop up is shown" → fill fields), retry ("If Pop up is still visible" → click Save again), UI-state normalization.

## Module naming convention

`TCODE | Screen Name` — e.g.:
- `FBCJ | Cash Journal: Initial Data pop up`
- `AS01 | Create Asset | Initial screen`
- `ME21N | Create Purchase Order`
- `MIGO | Goods Receipt Purchase Order`

UIA popup modules continue the flow path: `FBCJ | Cash Journal | Print Receipt | Save As pop up`.

## Creation workflow

```bash
# 1. Check for existing screen modules
python tools/toscacloud-cli/tosca_cli.py inventory search "<TCODE>" --type Module --json

# 2. Create module if missing
python tools/toscacloud-cli/tosca_cli.py modules create --name "<TCODE> | <ScreenName>" --iface Gui --json
# Write module body JSON (businessType: Window, root parameter quartet
# Engine/Transaction/ProgramName/ScreenNumber, SapEngine attributes with RelativeId)
python tools/toscacloud-cli/tosca_cli.py modules update <moduleId> --json-file .claude/tmp/module.json
python tools/toscacloud-cli/tosca_cli.py modules get <moduleId> --json   # verify

# 3. Create test case
python tools/toscacloud-cli/tosca_cli.py cases create --name "<description>" --state Planned --json
# Write case body:
#   - testConfigurationParameters: Username + Password (no Browser)
#   - testCaseItems[0]: Precondition block b0e929fa with 5 param values
#     (parameterLayerId = 01KHJSJ1DTC8N6ZYF59BJ6DQ8P, copied verbatim)
#   - testCaseItems[1..n]: chapter folders "<TCODE> - <intent>" with Process/Verification
#   - testCaseItems[last]: Postcondition block ccd86083 (parameterless, no parameterLayerId)
python tools/toscacloud-cli/tosca_cli.py cases update <caseId> --json-file .claude/tmp/case.json
python tools/toscacloud-cli/tosca_cli.py cases steps <caseId>
python tools/toscacloud-cli/tosca_cli.py inventory move testCase <caseId> --folder-id <folderId>
```
