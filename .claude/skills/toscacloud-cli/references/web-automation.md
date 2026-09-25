# Web Automation (Html Engine) — Detailed Guide

## Discovery workflow with Playwright

```
1. browser_navigate <url>
2. browser_snapshot                — get accessibility tree
3. browser_evaluate 'document.querySelectorAll("a[href='/path']").length'
   → must return 1; if > 1, find a discriminating ClassName
4. browser_evaluate 'JSON.stringify(Array.from(document.querySelectorAll("a[href='/path']")).map(function(el){return {cls:el.className}}))'
   → pick the class unique to the target element (e.g. top-navigation__item-link)
5. browser_click ref=<refId>       — navigate forward
6. Repeat for each step in the user journey
```

**Always verify element uniqueness before writing the module.** Many sites render nav links in both a mobile hamburger menu and a desktop nav bar. TOSCA will fail at runtime, not at save time, if a locator matches more than one element.

> **`InnerText` is exact-match in TOSCA's Html engine.** A link that wraps additional text nodes (e.g. an `<a>` containing both a caption and a nested heading) has `innerText` equal to the concatenation of all descendant text — not just the visible caption. A short `InnerText="<caption>"` will not match. Drop `InnerText` from the TechnicalIds and use `Tag` + `HREF` + `ClassName` (or a unique `Title` attribute) instead — or keep `InnerText` with a `*` wildcard pattern: wildcards are supported in TechnicalId values (e.g. `InnerText=*@*.*` matches any logged-in e-mail address).
>
> **Parent `visibility:hidden` propagates.** A mega-menu closed by default has its items rendered but hidden via parent `visibility:hidden` / `opacity:0`. TOSCA's default `IgnoreInvisibleHtmlElements=True` filters these out — your module-level selector finds the document but attribute lookup reports `"Could not find Link ..."`. Two fixes: (1) open the parent (click the menu trigger, then add a Wait + the hover/click step); (2) add `IgnoreInvisibleHtmlElements=False` as a Steering module parameter.
>
> **The Html scanner is viewport-scoped, not document-scoped.** A `Verify` on an `<h2>`, `<div>`, or any element below the fold fails with `Could not find …` even when the element exists in the DOM. Diagnostic — run before changing the selector:
>
> ```javascript
> // in browser_evaluate, on the live page at the same viewport size as the agent (maximized ≈ 900–1080)
> var sel = 'h2.stripe_title';
> var vh  = window.innerHeight;
> Array.from(document.querySelectorAll(sel)).map(function(el, i) {
>   var r = el.getBoundingClientRect();
>   return i + ': y=' + Math.round(r.y) + ' visible=' + (r.y >= 0 && r.y < vh);
> }).join('\n');
> ```
>
> If every match has `visible=false`, the element is below the fold — that is the failure, not the locator. `ScrollToFindElement=True` steering does **not** reliably reach far-below-the-fold content. Fixes in order of preference:
>
> 1. Prepend a `Send Keys (Keyboard)` step with `value: "{SENDKEYS[{PAGEDOWN}]}"` on a page-level element. Repeat until the target's `getBoundingClientRect().y` falls inside the viewport.
> 2. Navigate directly to a fragment anchor when the page supports one: an `OpenUrl` to `…/page#section-id` skips the scroll question entirely.
> 3. Pivot to `Verify JavaScript Result`: CDP `Runtime.evaluate` is document-scoped, so `return document.querySelectorAll('h2.stripe_title').length.toString()` returns the true count regardless of scroll position. See `standard-modules.md` for the module skeleton — remember to use **single quotes** inside the JS value (a `"` at the value root silently breaks the step).
>
> This is a distinct root cause from "scanner blind to body content" (observer-disabled case in `standard-modules.md`): viewport scoping applies even when the Tricentis Automation Extension is fully attached and the observer is healthy. Always check viewport first — cheapest diagnostic.

## Module structure — full root envelope

A Gui Html module root has **no `$type` discriminator**. The complete field set (all fields present in every scanned and hand-built module):

```json
{
  "id": "<uuid>",
  "name": "<AppName> | <PageName>",
  "description": "",
  "version": 0,
  "businessType": "HtmlDocument",
  "interfaceType": "Gui",
  "attributes": [ /* attribute objects — see attribute anatomy */ ],
  "tcProperties": [],
  "parameters": [
    {"id": "<ulid>", "name": "Engine", "value": "Html", "type": "Configuration"},
    {"id": "<ulid>", "name": "IgnoreInvisibleHtmlElements", "value": "True", "type": "Steering"},
    {"id": "<ulid>", "name": "ControlFramework", "value": "None", "type": "Steering"},
    {"id": "<ulid>", "name": "AllowedAriaControls", "value": "<see module-level identifiers table>", "type": "Steering"},
    {"id": "<ulid>", "name": "EnableSlotContentHandling", "value": "False", "type": "Steering"},
    {"id": "<ulid>", "name": "Title", "value": "<page title, * wildcard allowed>", "type": "TechnicalId"}
  ],
  "attachments": [],
  "metadata": {"isRescanEnabled": true, "engine": "Html", "controlFramework": "None"}
}
```

- **Every parameter entry — root and attribute level — carries its own fresh ULID `id`.** Mint one per entry; never reuse.
- **Root `metadata` mirrors the engine config**: `{"isRescanEnabled": true, "engine": "Html", "controlFramework": "None"}` for Html; SapEngine modules use `{"isRescanEnabled": true, "engine": "SapEngine"}` and omit `controlFramework`.
- Parameter **order is insignificant** (scanned siblings differ in ordering).
- `version` is server-managed — strip from PUT bodies (the CLI does this).
- `tcProperties` is always `[]`; scanned modules carry one root attachment `{"id": "<ulid>", "name": "Screenshot.png", "blobId": "<tenant-uuid>_<ulid>"}` — hand-built modules just use `"attachments": []`. Attribute-level `attachments` arrays are always empty.
- Prefer a **wildcard `Title`** (`"<AppName>*"`) for modules whose elements appear on more than one page (headers, nav): an exact Title only matches the one page whose title is exactly that string.
- `SelfHealingData` Steering blobs (root and per-attribute) are scanner by-products — **optional, not required for a working module**; hand-built modules omit them entirely.

**The root-level `parameters` array must contain `Engine: Html`.** Without it, TOSCA throws `XModules and XModuleAttributes have to provide the configuration param "Engine"` at runtime. Scanned modules have it automatically; manually created ones do not.

### Module-level identifiers (TechnicalId on the module root, not on an attribute)

These determine *which HtmlDocument* (i.e. browser tab) the module binds to at runtime. On a shared-Chrome agent (user's personal browser with many tabs), the defaults are too loose.

| Param | Type | Good value | Why |
|-------|------|-----------|-----|
| `Engine` | Configuration | `Html` | Required — see above |
| `Title` | TechnicalId | `*<AppName>*` (glob) | Restricts document match by tab title |
| `Url` | TechnicalId | `https://<host>*` | **Add this** to disambiguate when multiple tabs share a title pattern — this alone stops the _"More than one matching tab"_ error without needing a `CloseBrowser` first |
| `ControlFramework` | Steering | `None` | Default for vanilla HTML |
| `AllowedAriaControls` | Steering | `button; checkbox; combobox; link; listbox; menuitem; menuitemcheckbox; menuitemradio; menu; menubar; option; radio; cell; gridcell; columnheader; rowheader; row; grid; table; tablist; tab; textbox; treegrid; treeitem; tree` | Scanner-default literal (semicolon-space separated, identical in all scanned modules) — copy it verbatim into hand-built modules; an empty or truncated value causes erratic element resolution for ARIA menus/grids/tables |
| `EnableSlotContentHandling` | Steering | `False` | `True` triggers shadow-DOM traversal that many ordinary pages don't need |
| `IgnoreInvisibleHtmlElements` | Steering | `True` | Skip off-screen duplicates of the same element |

Scanned modules also carry a `SelfHealingData` steering param with hints about the page at scan time (Title + URL). **When reusing a scanned module for a different flow, drop the `SelfHealingData` entry** — the module still works via TechnicalIds, and stale self-healing hints can interfere with document matching on the new flow.

## businessType by element — archetype reference

Verified against scanned-artifact ground truth (Demo Web Shop Login + Top Menu modules). Rows marked **(unverified)** have no scanned sample — re-scan and copy the real JSON rather than trusting the recipe.

| Element | `businessType` | `defaultActionMode` | `valueRange` | Locator recipe |
|---------|---------------|---------------------|--------------|----------------|
| `<a>` | `Link` | `Input` | `["{Click}", "{Rightclick}"]` | `Tag=A` + `InnerText=<exact link text>` (wildcards OK, e.g. `*@*.*`); optionally `ClassName` |
| `<input type=text/email>` | `TextBox` | `Input` | `["{Click}", "{Doubleclick}", "{Rightclick}"]` | `Tag=INPUT` + `Id=<dom-id>` + Steering `FireEvent=change` |
| `<input type=password>` | `TextBox`, **`defaultDataType: "Password"`** | `Input` | same as TextBox | same as TextBox |
| `<input type=checkbox>` | **`CheckBox`** (capital B) | `Input` | **`["True", "False"]`** — state values, NOT click actions | `Tag=INPUT` + `Id=<dom-id>` + Steering `FireEvent=change` |
| `<input type=submit/button>` | `Button` | `Input` | `["{Click}"]` | `Tag=INPUT` + **`Value=<caption>`** (the `value` attr IS the caption; `InnerText` is empty on input-type buttons) |
| `<button>` | `Button` | `Input` | `["{Click}"]` | `Tag=BUTTON` + `InnerText=<caption>` **(unverified — no `<button>`-tag scan in ground truth; the verified Button sample is the input-type row above)** |
| `<select>` | **`ComboBox`** (capital B — the only casing observed in scanned artifacts; never `Combobox`) | `Input` | scanned ComboBoxes carry the **option list** as `valueRange` (e.g. `["Invoice", "Credit Memo", …]`), not `["{Select}"]` **(no Html `<select>` in ground truth — scan the element and copy what comes back)** | `Tag=SELECT` + `Id`/`Name` **(unverified)** |
| verify-only text (`<span>`/`<div>`/heading) | `Container` | **`Select`** | **omit the `valueRange` key entirely** | static text: `Tag` + `InnerText=<full message>`; dynamic text: `Tag` + `ClassName=<css class>` (e.g. `field-validation-error`) |
| element with no stable anchor | `GenericGUI` | **`Select`** | omit `valueRange` | `Tag=<TAG>` + `XPath` — **last resort**: the `XPath` parameter has `type: "Transition"` (not TechnicalId) and its value is an absolute 1-indexed path wrapped in embedded literal quotes: `"\"/html[1]/body[1]/<...>/li[1]\""`. Maximally brittle — prefer ClassName |
| page root | `HtmlDocument` | — | — (module-level only) | `Title` (+ `Url`) TechnicalId on the module root |

**Rules that fall out of the table:**
- `defaultActionMode` encodes intent: `Input` for anything clickable/typable, `Select` for passive assertion anchors (Container, GenericGUI), `Verify` for repeating data cells. `defaultOperator` is `"Equals"` and `defaultValue` is `""` everywhere.
- Verify-only archetypes (Container, GenericGUI) have **no `valueRange` field at all** — do not emit an empty array.
- **`FireEvent=change` Steering** (`{"name": "FireEvent", "value": "change", "type": "Steering"}`) goes on every form input (TextBox, CheckBox) to fire the JS `change` event after typing — required by client-side validation frameworks. Never on Buttons or Links.
- `defaultDataType` is `"String"` everywhere except password fields (`"Password"`).
- Scanned input archetypes duplicate `valueRange` under `metadata.valueRange` — when cloning a scanned attribute keep both copies in sync.

> **Container nesting is NOT a DOM scope.** Nesting a Button inside a Container in the module tree affects only Steering-param inheritance — at runtime TBox resolves `moduleAttributeReference.id` globally against the document. If two matching buttons exist in different page regions you get *"Found multiple controls for Button '…'"* regardless of the parent Container. To discriminate sibling elements, embed the ancestor's class/ID in the child's own selector (e.g. `ClassName: "region-header lang-switch"` combining both), or pivot to `Verify JavaScript Result` with a scoped `document.querySelector('.region-header button.lang-switch')`.

## Attribute anatomy — the common envelope

The "Module structure" skeleton above is abbreviated. Ground-truth scanned Html modules carry this exact key set on **every** attribute — a from-scratch PUT/create should include all of them:

```json
{
  "id": "<fresh-ulid>",
  "name": "<verbatim UI label incl. ':' '?' '(0)' — or a semantic name for assert targets>",
  "description": "",
  "businessType": "<Link|TextBox|CheckBox|Button|Container|GenericGUI>",
  "defaultValue": "",
  "defaultActionMode": "<Input for actionable controls | Select for verify-only Container/GenericGUI>",
  "defaultDataType": "<String — but Password for password inputs>",
  "defaultOperator": "Equals",
  "valueRange": ["<actions or state values — OMIT the key entirely for Container/GenericGUI>"],
  "isVisible": true,
  "isRecursive": false,
  "specialIcon": "",
  "cardinality": "ZeroToOne",
  "interfaceType": "Gui",
  "parameters": [
    {"id": "<ulid>", "name": "BusinessAssociation", "value": "Descendants", "type": "Configuration"},
    {"id": "<ulid>", "name": "Engine", "value": "Html", "type": "Configuration"},
    {"id": "<ulid>", "name": "Tag", "value": "<UPPERCASE-TAG>", "type": "TechnicalId"},
    {"id": "<ulid>", "name": "<Id|InnerText|Value|ClassName>", "value": "<anchor>", "type": "TechnicalId"}
  ],
  "attributes": [],
  "attachments": [],
  "metadata": {
    "businessType": "<same archetype>",
    "isUsedAsIdentification": false,
    "valueRange": ["<exact copy of attribute.valueRange — omit when the attribute has none>"]
  }
}
```

Rules:
- **Every Html attribute carries exactly two Configuration parameters** — `BusinessAssociation: "Descendants"` and `Engine: "Html"`. Their position in the `parameters` array does **not** matter (scanned modules interleave them freely with TechnicalId/Steering entries) — but both must be present; a missing `Engine` raises `XModules and XModuleAttributes have to provide the configuration param "Engine"` at runtime.
- **`metadata` mirrors the attribute**: repeat `businessType`, set `"isUsedAsIdentification": false` (the value in every observed scanned Html page attribute), and duplicate `valueRange` verbatim when (and only when) the attribute has one.
- **Every parameter carries its own fresh ULID `id`** — scanned modules always have them; don't emit id-less parameter entries.
- Typical locator recipe: `Tag` (uppercase HTML tag: `A`, `INPUT`, `SPAN`, `LI`, …) plus one or two semantic anchors (`Id` | `InnerText` | `Value` | `ClassName`), all ANDed together at resolution time.
- `defaultActionMode`/`defaultDataType` observed pairings: interactive controls (Link, TextBox, CheckBox, Button) use `Input`; verify-only Container/GenericGUI use `Select`. `defaultDataType` is `String` everywhere except password inputs, which use `Password`.
- `cardinality` is `"ZeroToOne"` for singleton elements; `"ZeroToN"` for repeating cells (also required when the same attribute is used twice in one TestStep — KB4 #13).
- IDs: scanned module root `id` is a lowercase server-assigned **UUID**; every attribute id, parameter id, and attachment id is a fresh 26-char Crockford **ULID** (`01…`). Never reuse IDs between elements.
- Scanned TextBox/CheckBox attributes often carry a `FireEvent: "change"` Steering param — keep it when the page's validation reacts to change events; always drop `SelfHealingData` when hand-authoring (see module-level identifiers section).
- Child nesting (`attributes` inside an attribute) is unused in flat page modules — leave `[]` (and remember nesting does NOT scope DOM matching anyway — see the Container-nesting warning above).

## Value expression reference

All values in a TestStepValue are **UPPERCASE commands wrapped in braces**. Source of truth: Tosca Cloud [References docs](https://docs.tricentis.com/tosca-cloud/en-us/content/references/values_overview.htm).

### Action modes (TestStepValue `actionMode`)

| Mode | Use |
|------|-----|
| `Input` | Write a value into the control |
| `Insert` | Insert a value into an API module control |
| `Verify` | Assert — compare expected vs actual; pair with `actionProperty` (`Visible`, `InnerText`, etc.) and `operator` |
| `Buffer` | Capture the control's value into the buffer named by `value` |
| `Output` | Capture a specific control property (`Value`, `InnerText`, `Enabled`, `Exists`, `Visible`) into a buffer |
| `WaitOn` | Poll the control until it reaches the specified state |
| `Select` | Choose a specific child control (e.g. a menu item, tab, row) — required for hover-revealed submenus if your tooling exposes it that way |
| `Constraint` | Narrow the parent scope — e.g. pick the right table row by a column value |
| `Exclude` | Remove specific rows/columns from a table operation |

### Click / mouse values (on Link, Button, CheckBox, etc.)

| Value | Action |
|-------|--------|
| `{CLICK}` | Left click |
| `{DOUBLECLICK}` | Double click |
| `{RIGHTCLICK}` | Right click |
| `{ALTCLICK}` / `{CTRLCLICK}` / `{SHIFTCLICK}` | Modified click (plus `L`/`R` variants e.g. `{LALTCLICK}`) |
| `{LONGCLICK}` | ~2-second press |
| `{MOUSEOVER}` | **Real mouse move over element** — fires CSS `:hover` |
| `{DRAG}` / `{DROP}` | Drag-and-drop pair |
| `X` | JS-click (no mouse event) |
| `{CLICK[OffsetH][OffsetV]}` | Click at pixel/percent offset from top-left of the control |
| `{MOUSE[<action>][Jump\|Smooth\|HorizontalFirst\|VerticalFirst][OffsetH][OffsetV]}` | Advanced: full control over move method + offset |

> `{Hover}` is **not** valid — TOSCA errors with _"No suitable value found for command Hover"_. Use `{MOUSEOVER}`. Synthetic JS events don't fire the CSS `:hover` pseudo-class; `{MOUSEOVER}` emits a real mouse move that does.

Example Link `valueRange` that includes hover:
```json
"valueRange": ["{CLICK}", "{RIGHTCLICK}", "{MOUSEOVER}"]
```

#### Mega-menu hover routing — direct `{MOUSEOVER}` paths can accidentally switch panels

Plain `{MOUSEOVER}` moves the cursor in a **straight line** (default `Jump`/`Smooth`) from its current position to the target's center. On mega-menus where top-level triggers (About / Products / Research / Careers / …) each open their own panel on hover, a straight diagonal line from one top-level trigger to a deep submenu link **crosses other top-level triggers** and swaps the open panel mid-flight — the intended target is no longer visible when the subsequent `{CLICK}` fires, and TBox reports `Link '…' is not steerable. The reason could be that the control is not visible` after a ~10 s timeout.

Two fixes, in order of preference:

1. **Single-step L-path via the advanced `{MOUSE[…]}` form.** Replace the `{MOUSEOVER}` value on the target Link with `{MOUSE[MOUSEOVER][HorizontalFirst]}` (or `[VerticalFirst]` depending on layout). The move goes horizontal-then-vertical (or vice versa) in a single step, keeping the cursor inside the expanded panel's safe rectangle. Requires the Link's `valueRange` to include the exact string.

2. **Explicit waypoint attribute.** If the target element is deep enough that even `HorizontalFirst` crosses a sibling trigger, add a **waypoint Link attribute** to the module — an element on the same-y-row as the top-level trigger, safely inside the opened submenu column — and insert a `MOUSEOVER <waypoint>` step between the panel-opening hover and the target hover:

   ```
   1. Click <hamburger Menu>
   2. MOUSEOVER <top-level trigger>            ← opens submenu
   3. WaitOn <target visible>
   4. MOUSEOVER <waypoint>                     ← horizontal move inside safe row
   5. MOUSEOVER <target>                       ← vertical move inside submenu column
   6. Click <target>
   ```

   To pick a good waypoint, call `document.querySelectorAll('<trigger-submenu> > li:nth-child(1) > a')` or inspect via Playwright `browser_evaluate` — you want a link whose `getBoundingClientRect().top/bottom` **overlap the top-level trigger's y-range** (same row), so the path from trigger → waypoint is horizontal only. Then the path from waypoint → target is vertical only (both are in the same submenu column). This L-shaped path never crosses another top-level trigger.

Validated against Novartis — see case `Novartis — verify Therapeutic Areas sections` in the Sandbox space. Direct `{MOUSEOVER}` from `About` to `Therapeutic areas` crossed `Products` / `Patients` and closed the About panel; adding a `Board of Directors` waypoint (same y-row as `About`, top of the About submenu column) made the flow deterministic.

### Keyboard commands (on TextBox / any focusable)

Single key: `{ENTER}` `{RETURN}` `{TAB}` `{ESC}` `{ESCAPE}` `{BACKSPACE}` `{DEL}` `{HOME}` `{END}` `{LEFT}` `{RIGHT}` `{UP}` `{DOWN}` `{INSERT}` `{CLEAR}` `{F1}`–`{F24}` — and modifiers `{SHIFT}` `{CTRL}` `{ALT}` (plus `L`/`R` variants), plus `{CAPSLOCK}` `{NUMLOCK}` `{SCROLLLOCK}` `{PRINT}` `{BREAK}` `{LWIN}` `{RWIN}` `{APPS}`.

Advanced:
- `{SENDKEYS["<Microsoft SendKeys string>"]}` — Windows SendKeys-style sequence
- `{KEYPRESS[<VK code>]}` — single virtual-key press (no `VK_` prefix)
- `{KEYDOWN[<code>]}` / `{KEYUP[<code>]}` — hold / release a key
- `{TEXTINPUT["<unicode text>"]}` — raw unicode input (bypasses keymap)

### Dynamic expressions (in any `value` field)

| Expression | Purpose |
|------------|---------|
| `{CP[ParamName]}` | Reference a test-configuration parameter (e.g. `{CP[Username]}`) |
| `{B[bufferName]}` | Reference a buffered value — **case-sensitive, test-case-scoped** (cannot cross test-case boundaries) |
| `{MATH[<expr>]}` | Arithmetic: `+ - * / %`, comparisons, logical, bitwise; functions `Abs Ceiling Floor Max Min Pow Round Sign Sqrt Truncate` (e.g. `{MATH[2*(2+5)]}` → `14`) |
| `{BASE64}`, `{STRINGLENGTH}`, `{STRINGTOLOWER}`, `{STRINGTOUPPER}`, `{TRIM}`, `{STRINGREPLACE}`, `{STRINGSEARCH}`, `{NUMBEROFOCCURRENCES}` | String ops; some accept `[IGNORECASE]` / `[REPLACEFIRST]` / `[FINDFIRST]` |

Other value-expression families documented but rarely needed for basic web cases: scroll operations, regex capture, random values, date/time, number formats, intervals, resource expressions, user simulation, key-vault secrets. See Tosca's [value expressions overview](https://docs.tricentis.com/tosca-cloud/en-us/content/references/values_overview.htm).

## Standard framework module IDs

| Step | Module ID | Attribute | Attr ref ID | Notes |
|------|-----------|-----------|-------------|-------|
| `OpenUrl` | `9f8d14b3-7651-4add-bcfe-341a996662cc` | `Url` | `39e342b2-960b-2251-d1b9-5b340c12fa19` | Navigate |
| same | same | `UseActiveTab` | `39ef3b0d-1ee2-a137-d5d3-976be1b8c766` | Always `"False"` |
| same | same | `ForcePageSwitch` | `deaad6b0-32d2-4c60-a682-40e30540e3d9` | Always `"True"` |
| `CloseBrowser` | `3019e887-48ca-4a7e-8759-79e7762c6152` | `Title` | `39e342b2-958e-3e2f-7c85-29871c23f1dc` | Value = title glob; `"*"` = any |
| `Wait` | `80b7982e-0e10-4bc0-bdf3-6bc04503fd63` | `Duration` | `39e342b2-958e-ba1f-bb58-702e193d6016` | ms; `dataType: Numeric` |
| `Buffer` | `8415c10d-ab41-44a7-949a-602f4dddd2d2` | `<Buffername>` | `39e342b2-958e-0a6b-cbfd-5fdd372ca255` | Package `BufferOperations`, engine `Framework`; buffer name goes in `explicitName`, literal in `value` (`actionMode: Input`, `dataType: String`) |

## 4-folder test case structure

```
Precondition   — CloseBrowser Title="*"  ← ALWAYS FIRST: clears leftover browser sessions
               — OpenUrl (Url + UseActiveTab=False + ForcePageSwitch=True)
Process        — User actions (click links, fill inputs, click buttons)
Verification   — Verify steps (actionMode: Verify + actionProperty)
Teardown       — CloseBrowser + optional Wait
```

> **Why CloseBrowser first?** A leftover browser tab from a previous run causes _"More than one matching tab"_. Starting with `CloseBrowser Title="*"` (wildcard) guarantees a clean slate — **on grid agents and workstations that run a dedicated Chrome profile**. On workstation agents that reuse the user's personal Chrome, `Title="*"` would close the user's own tabs — narrow it to `Title="*<AppName>*"` and wrap in a `ControlFlowItemV2 If` that first verifies a known app element is visible.
>
> **Leftover-tab cleanup, idiomatic form** — when running on personal Chrome, prepend to Precondition:
> ```
> If  condition = Verify <always-visible app element> Visible=True
>     then       = CloseBrowser Title="*<AppName>*"
> ```
> The condition Verify has to be checkable cheaply with no user action (e.g. the site's Menu button, logo link, or any element that's in the page chrome). If the Verify returns false (no leftover tab) the If skips and OpenUrl proceeds. If Verify returns true, CloseBrowser runs first. Without this, the very first step after OpenUrl fails with `"More than one matching tab was found"` on the second and later runs of the day.

> **When CloseBrowser fails with `UnestablishedConnectionException`** — the agent has no running Chrome at all (typical on a fresh grid agent). `CloseBrowser` tries to handshake with the extension, hits a 10 s timeout, and aborts. In that case remove the cleanup step entirely — `OpenUrl` will launch Chrome itself.

> **`"The Browser could not be found"` at the first interactive step** — the Tricentis Chrome extension is not installed/enabled in the Chrome instance the agent is driving. OpenUrl opens the tab, but subsequent steps have no bridge. Fix on the agent (install the extension in the profile, or configure a dedicated profile). **No test-case change resolves this.**

### Test case root envelope

A GET of a test case returns exactly these root fields — there is **no `tags` field**, and `description` is conventionally `""`:

```json
{
  "id": "<caseId — also required in the PUT body>",
  "name": "<Scenario>",
  "description": "",
  "workState": "<Planned|InWork|Completed>",
  "testConfigurationParameters": [
    {"name": "Browser", "value": "<Chrome|Edge|Firefox>", "dataType": "String"}
  ],
  "parameterSetIds": [],
  "testCaseItems": [
    {"$type": "TestStepFolderV2", "items": [ /* CloseBrowser cleanup, OpenUrl */ ], "id": "<ulid>", "name": "Precondition", "disabled": false},
    {"$type": "TestStepFolderV2", "items": [ /* user actions */ ], "id": "<ulid>", "name": "Process", "disabled": false},
    {"$type": "TestStepFolderV2", "items": [ /* Verify steps only */ ], "id": "<ulid>", "name": "Verification", "disabled": false},
    {"$type": "TestStepFolderV2", "items": [ /* CloseBrowser + optional Wait */ ], "id": "<ulid>", "name": "Postcondition", "disabled": false}
  ],
  "recoveryScenarioCollection": { /* optional — only on cases with a recovery/CleanUp scenario; when cloning, copy verbatim or omit entirely */ }
}
```

- GET also returns a `version` field — it is server-managed; **omit it from PUT** (the CLI's `cases update` strips it automatically). Mature suite cases sit at `workState: "Completed"`; drafts at `"Planned"`.
- `testConfigurationParameters` may also carry credential params alongside `Browser` — e.g. `{"name": "Username", "value": "…", "dataType": "String"}` and `{"name": "Password", "dataType": "Password", "password": {"id": "<encrypted-id>"}}` (Password entries have **no `value` key**). Steps reference them via `{CP[Username]}` / `{CP[Password]}`.
- Production suites name the fourth folder `Postcondition` (this maps 1-1 to the `Teardown` naming used elsewhere in this skill). Cases assembled from reusable blocks name the referenced folders `Precondition_Reference` / `Postcondition_Reference`.
- Negative-variant naming convention: `"<Scenario> - <exact expected UI error text>"` (e.g. `Unsuccessful login - Please enter a valid email address.`) — the case name literally contains the string asserted in Verification, making it a self-documenting oracle.

## Recovery / CleanUp scenario (`recoveryScenarioCollection`)

Production cases duplicate the Postcondition teardown pair (CloseBrowser + Wait) into a case-level `recoveryScenarioCollection` so an aborted/failed run still closes the browser before the next case starts. It is a sibling of `testCaseItems` on the case root:

```json
"recoveryScenarioCollection": {
  "id": "<uuid — unique per case>",
  "name": "*** Recovery Scenarios ***",
  "scenarios": [{
    "name": "CleanUp Scenario",
    "id": "<ulid>",
    "type": "CleanUp",
    "retryLevel": "TestCase",
    "items": [
      { /* CloseBrowser TestStepV2 — moduleReference 3019e887-48ca-4a7e-8759-79e7762c6152, value Title = "<AppName>*" (trailing * wildcard), actionMode Input */ },
      { /* Wait TestStepV2 — moduleReference 80b7982e-0e10-4bc0-bdf3-6bc04503fd63, value Duration = "3000", dataType Numeric, name "Wait: 3 sec" */ }
    ],
    "disabled": false
  }]
}
```

- The scenario `items` are ordinary `TestStepV2` objects — copy the Postcondition CloseBrowser/Wait steps verbatim.
- `type: "CleanUp"`, `retryLevel: "TestCase"` is the standard shape; the collection name is conventionally the literal `"*** Recovery Scenarios ***"`.
- Item ULIDs inside the scenario do not need to be globally unique across cases (the server tolerates verbatim reuse when cloning), but mint fresh ones anyway to stay consistent with the fresh-ID rule.

## TestStepV2 anatomy — the general step and value shape

Every step, standard or scanned, has this shape:

```json
{
  "$type": "TestStepV2",
  "testStepValues": [ /* one entry per attribute touched */ ],
  "moduleReference": { /* flavor A or B below */ },
  "reorderAllowed": false,
  "id": "<fresh-ulid — UUID also accepted>",
  "name": "<verb-first action phrase, e.g. 'Click Log in', or bare module name for standard steps>",
  "disabled": false
}
```

**Two moduleReference flavors** — pick by module origin:

```json
// Flavor A — Standard module (OpenUrl, CloseBrowser, Wait, Buffer, …)
// packageReference.id is the package name: Html, Timing, BufferOperations, …
// engine is "Framework" for these four; Verify JavaScript Result is Standard but tenant-specific (Html on the validated tenant) — always copy engine from the fetched module
{"id": "<module-uuid>", "packageReference": {"id": "<Html|Timing|BufferOperations>", "type": "Standard"}, "metadata": {"isRescanEnabled": false, "engine": "Framework"}}
// Flavor B — scanned/hand-built app page module: NO packageReference
{"id": "<module-uuid>", "metadata": {"isRescanEnabled": true, "engine": "Html", "controlFramework": "None"}}
```

**Every Html-engine testStepValue has this fixed 10-key shape** (`operator` is `Equals` and `subValues` is `[]` in every Html-engine entry; `actionProperty` is `""` for every Input). Two documented exceptions: `dataType: "Password"` values add an 11th key `"password": {"id": "<encrypted-id>"}` and set `value: ""` (see Password fields below); SAP table Row/Cell steps nest populated `subValues` with `actionMode: "Select"` — see `sap-automation.md`, never copy this template for those.

```json
{
  "id": "<fresh-ulid per step — never reuse across steps>",
  "name": "<module attribute display name>",
  "value": "<literal | X | True/False | expected text>",
  "actionMode": "<Input|Verify>",
  "dataType": "<String|Numeric|Password>",
  "actionProperty": "<'' | InnerText | Visible>",
  "operator": "Equals",
  "moduleAttributeReference": {
    "id": "<attribute id from the module — ULID for scanned attrs, UUID for Standard attrs>",
    "moduleId": "<same as the step's moduleReference.id>",
    "metadata": {"businessType": "<Link|TextBox|Button|Container|GenericGUI>", "isUsedAsIdentification": false}
  },
  "subValues": [],
  "disabled": false
}
```

- Standard-module values also repeat `packageReference` inside `moduleAttributeReference`; scanned values instead set `metadata.businessType` and mirror the attribute's `valueRange` when it has one (TextBox/Link/Button attrs carry `valueRange`; Container/GenericGUI don't).
- **Multiple related actions go in ONE step as multiple testStepValues** (e.g. Email + Password + Log-in click as three values of a single "Fill in login and password, click Log in" step; two related assertions as two values of one "Verify message" step).
- **One page module feeds many steps across phases** — repeat the full `moduleReference` per step and pick the attribute subset; the `moduleAttributeReference.id`s are the stable contract shared by every case using that module, while every `testStepValue.id` and step `id` is fresh per case.
- Folder shape: `{"$type": "TestStepFolderV2", "items": [<steps>], "id": "<ulid>", "name": "<phase>", "disabled": false}` — production cases carry no `description` on folders or steps (the observed key set is exactly the one shown above); don't emit the key when authoring from scratch. If you need to annotate a known defect per the no-defect-masking rule, use the test case `description` or a tracker link in the step `name`.

## OpenUrl step template (all 3 params required)

```json
{
  "$type": "TestStepV2",
  "name": "OpenUrl – https://example.com",
  "moduleReference": {
    "id": "9f8d14b3-7651-4add-bcfe-341a996662cc",
    "packageReference": {"id": "Html", "type": "Standard"},
    "metadata": {"isRescanEnabled": false, "engine": "Framework"}
  },
  "testStepValues": [
    {
      "name": "Url", "value": "https://example.com",
      "actionMode": "Input", "dataType": "String", "operator": "Equals",
      "moduleAttributeReference": {
        "id": "39e342b2-960b-2251-d1b9-5b340c12fa19",
        "moduleId": "9f8d14b3-7651-4add-bcfe-341a996662cc",
        "packageReference": {"id": "Html", "type": "Standard"}
      }
    },
    {
      "name": "UseActiveTab", "value": "False",
      "actionMode": "Input", "dataType": "String", "operator": "Equals",
      "moduleAttributeReference": {
        "id": "39ef3b0d-1ee2-a137-d5d3-976be1b8c766",
        "moduleId": "9f8d14b3-7651-4add-bcfe-341a996662cc",
        "packageReference": {"id": "Html", "type": "Standard"},
        "metadata": {"valueRange": ["True", "False"]}
      }
    },
    {
      "name": "ForcePageSwitch", "value": "True",
      "actionMode": "Input", "dataType": "String", "operator": "Equals",
      "moduleAttributeReference": {
        "id": "deaad6b0-32d2-4c60-a682-40e30540e3d9",
        "moduleId": "9f8d14b3-7651-4add-bcfe-341a996662cc",
        "packageReference": {"id": "Html", "type": "Standard"},
        "metadata": {"valueRange": ["True", "False"]}
      }
    }
  ]
}
```

## Buffer write step (BufferOperations Standard module)

To store a literal into a named buffer, use the `Buffer` Standard module — **not** `actionMode: "Buffer"` (that mode captures a control's value; writing a literal is a plain `Input` on the `<Buffername>` attribute, renamed via `explicitName`):

```json
{
  "$type": "TestStepV2",
  "name": "--->  BUFFER: <bufferName>",
  "moduleReference": {
    "id": "8415c10d-ab41-44a7-949a-602f4dddd2d2",
    "packageReference": {"id": "BufferOperations", "type": "Standard"},
    "metadata": {"isRescanEnabled": false, "engine": "Framework"}
  },
  "testStepValues": [{
    "id": "<fresh-ulid>",
    "name": "<Buffername>",
    "explicitName": "<bufferName>",
    "value": "<content to buffer>",
    "actionMode": "Input",
    "dataType": "String",
    "actionProperty": "",
    "operator": "Equals",
    "moduleAttributeReference": {
      "id": "39e342b2-958e-0a6b-cbfd-5fdd372ca255",
      "moduleId": "8415c10d-ab41-44a7-949a-602f4dddd2d2",
      "packageReference": {"id": "BufferOperations", "type": "Standard"},
      "metadata": {"businessType": "", "isUsedAsIdentification": false, "isExplicitNameAllowed": true}
    },
    "subValues": [],
    "disabled": false
  }],
  "reorderAllowed": false,
  "id": "<fresh-ulid>",
  "disabled": false
}
```

- `explicitName` is the buffer's name (read back later with `{B[<bufferName>]}` — case-sensitive, test-case-scoped); `value` is the buffered content; the attribute keeps its placeholder display name `<Buffername>`.
- Step naming convention from production suites: `--->  BUFFER: <name>` (arrow prefix, double space).
- A Buffer step with `"testStepValues": []` is a legal runtime no-op shell — don't clone it around; either populate it or delete it.

## Verify steps

```json
{
  "name": "Error message",
  "value": "Please enter a valid email address.",
  "actionMode": "Verify",
  "actionProperty": "InnerText",
  "operator": "Equals",
  "dataType": "String"
}
```

| `actionProperty` | Checks |
|-----------------|--------|
| `"Visible"` | Element is visible; value `"True"` |
| `"InnerText"` | Exact inner text matches value |
| `""` (empty) | Plain interaction, no assertion |

## Login / outcome verification patterns

Three production-validated shapes for the Verification folder:

1. **Success = existence of a session-scoped element**, not absence of an error. Verify `Visible=True` on an element that only exists when logged in — e.g. a header "User" Link whose `InnerText` TechnicalId is the wildcard `*@*.*` (matches any logged-in e-mail, deliberately dynamic):

   ```json
   {"name": "<User link attr>", "value": "True", "actionMode": "Verify", "actionProperty": "Visible", "dataType": "String", "operator": "Equals", ...}
   ```

2. **Failure = exact error text via Container attributes.** Model TWO distinct verify targets on the page module and pick per scenario:
   - **Summary banner** (server-side validation): `Container` located by `Tag=SPAN` + `InnerText=<full message>` — assert with `actionMode: Verify`, `actionProperty: InnerText`, `value` = the exact expected text.
   - **Field-level validation message** (client-side, text varies): `Container` located by `Tag=SPAN` + `ClassName=field-validation-error` — the class is stable while the text changes, so the expected text lives only in the test step's `value`.
   Invalid-format scenarios assert the field-level Container; wrong-credentials / no-account scenarios assert the summary banner (optionally plus a `GenericGUI` "Reason" line as a second value).

3. **Pack related assertions as multiple testStepValues in ONE Verify step** (e.g. `Verify message` = summary Container + Reason in a single `TestStepV2`), keeping the Verification folder one-step-per-outcome.

Name the steps declaratively: `Verify that login is successful`, `Verify message`.

## Test case config params

```json
"testConfigurationParameters": [
  {"name": "Browser", "value": "Chrome", "dataType": "String"}
]
```

Supported: `Chrome`, `Edge`, `Firefox`.

## Password fields

Two halves — module attribute and test step value:

**Module attribute**: an ordinary `TextBox` archetype but with `"defaultDataType": "Password"` — the only non-String `defaultDataType` observed in production modules (also appears on `Document`-type "PDF Password" attributes). Locators as usual (`Tag=INPUT` + `Id` + `FireEvent=change`).

**Test step value**: the secret is never inline — `value` stays `""` and a sibling `password` object carries a server-issued vault token:

```json
{
  "id": "<ULID>",
  "name": "Password:", "value": "",
  "password": {"id": "<22-char base64url token>"},
  "actionMode": "Input", "dataType": "Password", "actionProperty": "", "operator": "Equals",
  "moduleAttributeReference": {"id": "<attrId>", "moduleId": "<moduleUuid>", "metadata": {"businessType": "TextBox", "isUsedAsIdentification": false, "valueRange": ["{Click}", "{Doubleclick}", "{Rightclick}"]}},
  "subValues": [], "disabled": false
}
```

- **`password.id` tokens are stored server-side per test case** — four cases targeting the same Password attribute each carry a different token. You cannot mint one client-side; set the secret via the Portal UI (or clone a case that already has one and re-enter the secret), then read the token back with `cases get --json` before assembling a PUT body.
- **The `{CP[Password]}` route is equally vaulted, not a plaintext alternative.** A Password-typed test configuration parameter carries its own per-case vault token and has **no `value` key at all**:

```json
"testConfigurationParameters": [
  {"name": "Password", "dataType": "Password", "password": {"id": "<22-char base64url token>"}},
  {"name": "Username", "value": "ABYCH", "dataType": "String"}
]
```

  Block parameters then reference it with `{"name": "Password", "value": "{CP[Password]}", "referencedParameterId": "<block businessParameter ULID>"}`. This is the majority pattern in production cases (6 of 10 sampled) — prefer it when the secret is fed into a reusable block rather than a direct module step. The same Portal-UI-first rule applies: the config-param token is also server-issued and per-case.

## Conditional steps — `ControlFlowItemV2` for optional elements

Wrap a step in an `If` block when the element may or may not be present (cookie banners, leftover tabs, optional popups). **Works reliably only when the module-level selector can cleanly miss** — i.e. add a tight `Url=https://host.tld*` to the module so the document match returns a clean no-match instead of hard-failing.

```json
{
  "$type": "ControlFlowItemV2",
  "statementTypeV2": "If",
  "id": "<ULID>",
  "name": "If cookie banner shown",
  "disabled": false,
  "condition": {
    "id": "<ULID>",
    "name": "Condition",
    "disabled": false,
    "items": [
      {
        "$type": "TestStepV2",
        "id": "<ULID>",
        "name": "Accept Cookies visible?",
        "moduleReference": { "id": "<pageModuleId>", "metadata": {...} },
        "testStepValues": [{
          "id": "<ULID>",
          "name": "Accept Cookies",
          "value": "True",
          "actionMode": "Verify",
          "actionProperty": "Visible",
          "dataType": "String",
          "operator": "Equals",
          "moduleAttributeReference": { "id": "<attrId>", "moduleId": "<pageModuleId>", "metadata": {...} },
          "subValues": [],
          "disabled": false
        }]
      }
    ]
  },
  "conditionPassed": {
    "id": "<ULID>",
    "name": "Then",
    "disabled": false,
    "items": [ /* the original Click step */ ]
  }
}
```

Top-level keys: `$type`, `statementTypeV2` (`"If"`), `condition` (inline folder), `conditionPassed` (inline folder), `id`, `name`, `disabled`. No `conditionFailed` — just omit and nothing runs on the false branch.

Typical uses that have been verified in production:
- Cookie banner (OneTrust `#onetrust-accept-btn-handler`) — condition: Verify `Accept Cookies` Visible=True
- Leftover browser tab cleanup — condition: Verify a known nav element Visible=True; then: `CloseBrowser Title="*<AppName>*"`

### VJS probe — robust conditional CloseBrowser without a scanned module

When you need to conditionally close the browser but don't have (or don't want to depend on) a scanned Html module for the page, use a **VJS probe** as the `ControlFlowItemV2 If` condition instead of an Html-module Verify:

```json
{
  "$type": "ControlFlowItemV2",
  "statementTypeV2": "If",
  "name": "If <AppName> tab open – close it",
  "condition": {
    "items": [{
      "$type": "TestStepV2",
      "name": "Probe – <AppName> tab open?",
      "moduleReference": { "id": "<VJS-module-GUID>", "packageReference": {"id": "Html", "type": "Standard"}, "metadata": {"engine": "<tenant-engine-value>"} },
      "testStepValues": [
        { "name": "UseActiveTab", "value": "False", "actionMode": "Input", "dataType": "String" },
        { "name": "Title", "value": "*<AppName>*", "actionMode": "Input", "dataType": "String" },
        { "name": "JavaScript", "value": "return 'present'", "actionMode": "Input", "dataType": "String" },
        { "name": "Result", "value": "present", "actionMode": "Verify", "dataType": "String", "operator": "Equals" }
      ]
    }]
  },
  "conditionPassed": {
    "items": [/* CloseBrowser step */]
  }
}
```

**Why this works:** VJS with `UseActiveTab=False + Title=*<pattern>*` silently returns `""` (empty string) when no matching tab exists, instead of throwing an error like a GUI Html module would. The Result `Verify "present"` then fails → the If condition evaluates false → CloseBrowser is skipped. When a matching tab IS open, the JS runs and returns `"present"` → Verify passes → CloseBrowser executes.

**Advantage over Html-module Verify condition:** no scanned module or page element is needed; works immediately after Teardown closes the browser; handles the "fresh agent, no browser running at all" case cleanly without `UnestablishedConnectionException`.

## Debugging a failed run

1. `playlists results <runId>` returns only `<failure />`. No step-level logs exist via the Playlists v2 API.
2. Logs are stored in Azure Blob and fetched by the Portal via `/{spaceId}/_e2g/api/executions/{executionId}/units/{unitId}/attachments`, which returns SAS-signed URLs like:
   ```
   https://e2gweuprod001resblobs.blob.core.windows.net/<tenant-slug>/<spaceId>/<executionId>/<unitId>/logs?sv=…&se=…&sr=b&sp=r&sig=…
   ```
   SAS TTL ≈ 30 min. The blob GET takes **no Authorization header** — the SAS is the entire auth. Also available on the same endpoint: `TBoxResults.tas`, `TestSteps.json`, `Recording.mp4`, `junit_result_*.xml`.
3. The `Tricentis_Cloud_API` client app this CLI uses **can** read that attachments endpoint for shared-agent runs (see SKILL.md and the E2G recipe in `field-notes.md`). An older note here said it was 403'd, which is outdated. Personal-agent runs are still invisible to the service token; use the MCP tools. If you do hit a 403:
   - Copy the SAS URL from the Portal DevTools Network tab and `curl` it.
   - Re-run locally on an E2G agent: the same log mirrors at `C:\Users\<user>\AppData\Local\Temp\E2G\<runUuid>\…`.
3. Common error mapping:

   | TBox message | Likely cause | Fix |
   |--------------|-------------|-----|
   | `UnestablishedConnectionException` at CloseBrowser | No Chrome running on agent | Remove the cleanup step, or wrap in `If` + narrow `Title` |
   | `The Browser could not be found` | Tricentis Chrome extension not attached | Install/enable extension in agent's Chrome profile — not a test fix |
   | `More than one matching tab was found` | Agent shares user's Chrome; multiple tabs match | Add `Url=https://<host>*` TechnicalId at module level |
   | `Could not find HtmlDocument … Title: <pattern>` | Module-level selector doesn't match | Tighten/fix `Title`; add `Url` for host-scoped match |
   | `Could not find Link '…'` | Element locator ambiguous or DOM changed | Re-check via Playwright `browser_evaluate` + uniqueness count |

## Creation workflow

```bash
# 1. Playwright: snapshot page, verify element uniqueness with browser_evaluate
# 2. Check for existing module
python tools/toscacloud-cli/tosca_cli.py inventory search "<AppName>" --type Module

# 3. Create module (if none exists)
python tools/toscacloud-cli/tosca_cli.py modules create --name "<AppName> | <PageName>" --iface Gui --json
# Write module JSON file with Engine param at root level + attribute params
python tools/toscacloud-cli/tosca_cli.py modules update <moduleId> --json-file .claude/tmp/module.json
python tools/toscacloud-cli/tosca_cli.py modules get <moduleId> --json   # verify

# 4. Create test case
python tools/toscacloud-cli/tosca_cli.py cases create --name "<description>" --state Planned --json
python tools/toscacloud-cli/tosca_cli.py cases update <caseId> --json-file .claude/tmp/case.json
python tools/toscacloud-cli/tosca_cli.py cases steps <caseId>
python tools/toscacloud-cli/tosca_cli.py inventory move testCase <caseId> --folder-id <folderId>
```
