# PDF Verification Modules (Pdf engine) — Module Anatomy & Step Wiring

One scanned Pdf module per PDF **layout** (never parameterized across layouts). Used for end-of-flow checks: SAP print preview → save as PDF → verify contents.

## Module root anatomy

```json
{
  "id": "<uuid>", "name": "<Document Type In English>", "description": "", "version": 0,
  "businessType": "PdfDocument", "interfaceType": "NonGui",
  "attributes": [<Target PDF>, <PDF Password>, <Page containers>, <optional anchors>],
  "tcProperties": [],
  "parameters": [
    {"id": "<ULID>", "name": "Engine", "value": "Pdf", "type": "Configuration"},
    {"id": "<ULID>", "name": "DocumentLanguage", "value": "English", "type": "Transition"}
  ],
  "attachments": [{"id": "<ULID>", "name": "<original sample>.pdf", "blobId": "<space-uuid>_<ULID>"}],
  "metadata": {"isRescanEnabled": true, "engine": "Pdf"}
}
```

- Root `parameters` is exactly Engine=Pdf + DocumentLanguage (stays `"English"` even for Russian documents). No ProgramName/Transaction/ScreenNumber — the target document is supplied at runtime via the `Target PDF` attribute.
- **The attachment cannot be authored offline**: `blobId` = `<space blob-container uuid>_<ULID>` where the ULID is batch-generated with the attachment id. Scan the sample PDF once via the Portal UI, then edit/add attributes via the API.

## Fixed scaffold: Target PDF + PDF Password (always attributes[0] and [1])

```json
{"id": "<ULID>", "name": "Target PDF", "description": "", "businessType": "Document", "defaultValue": "", "defaultActionMode": "Input", "defaultDataType": "String", "defaultOperator": "Equals", "isVisible": true, "isRecursive": false, "specialIcon": "", "cardinality": "ZeroToOne", "interfaceType": "NonGui",
 "parameters": [
   {"id": "<ULID>", "name": "Engine", "value": "Pdf", "type": "Configuration"},
   {"id": "<ULID>", "name": "BusinessAssociation", "value": "", "type": "Configuration"},
   {"id": "<ULID>", "name": "Parameter", "value": "True", "type": "Configuration"}
 ],
 "attributes": [], "attachments": [], "metadata": {"businessType": "Document", "isUsedAsIdentification": false}}
```

`PDF Password` is identical except `"defaultDataType": "Password"` — include it even when the PDF has no password (fixed scanner scaffold). `Parameter="True"` marks these as business parameters the test step fills; `BusinessAssociation` is `""` on them (root-level) and `"Children"` on everything in the containment hierarchy.

## Locator archetype 1 — Page container + absolute text boxes (default)

```json
{"id": "<ULID>", "name": "Page <n>", "businessType": "PdfPage", "defaultActionMode": "Select", "defaultDataType": "String", "defaultOperator": "Equals", "isVisible": false, "isRecursive": false, "specialIcon": "Container", "cardinality": "ZeroToOne", "interfaceType": "NonGui", "description": "", "defaultValue": "",
 "parameters": [
   {"id": "<ULID>", "name": "BusinessAssociation", "value": "Children", "type": "Configuration"},
   {"id": "<ULID>", "name": "Engine", "value": "Pdf", "type": "Configuration"},
   {"id": "<ULID>", "name": "Page", "value": "<1-based page nr>", "type": "TechnicalId"}
 ],
 "attributes": [<verify fields>], "attachments": [], "metadata": {"businessType": "Container", "isUsedAsIdentification": true}}
```

`Page` is the ONLY TechnicalId in the whole Pdf grammar. Verify fields nest inside the page's `attributes`:

```json
{"id": "<ULID>", "name": "<Business Field Name>", "businessType": "PdfTextArea", "defaultActionMode": "Verify", "defaultDataType": "String", "defaultOperator": "Equals", "valueRange": ["<scan-time literal>"], "isVisible": true, "isRecursive": false, "specialIcon": "TextBox", "cardinality": "ZeroToOne", "interfaceType": "NonGui", "description": "", "defaultValue": "",
 "parameters": [
   {"id": "<ULID>", "name": "BusinessAssociation", "value": "Children", "type": "Configuration"},
   {"id": "<ULID>", "name": "Engine", "value": "Pdf", "type": "Configuration"},
   {"id": "<ULID>", "name": "Height", "value": "0.25", "type": "Transition"},
   {"id": "<ULID>", "name": "Width", "value": "<decimal>", "type": "Transition"},
   {"id": "<ULID>", "name": "X", "value": "<decimal>", "type": "Transition"},
   {"id": "<ULID>", "name": "Y", "value": "<decimal>", "type": "Transition"},
   {"id": "<ULID>", "name": "ForceOcr", "value": "False", "type": "Steering"}
 ],
 "attributes": [], "attachments": [], "metadata": {"businessType": "TextBox", "isUsedAsIdentification": false, "valueRange": ["<same literal>"]}}
```

- Bounding box in decimal inches, page-absolute when nested under a Page; `0.25` is the usual scanned line Height but not universal (e.g. `0.14672828` observed) — treat all four box values as scan-derived data, never invent them.
- `valueRange` holds the literal captured at scan time and is duplicated verbatim in `metadata.valueRange` — informational only; supply the real expected value from the test step (buffers/`{CP[...]}`) rather than relying on module-baked literals, which are environment data and brittle.

## Locator archetype 2 — text anchor + relative child (for values whose position floats)

Anchors sit at **module root**, as siblings of the Page containers — never nested inside a Page.

```json
{"id": "<ULID>", "name": "<AnchorNameInEnglish>", "businessType": "PdfTextArea", "defaultActionMode": "Select", "isVisible": false, "specialIcon": "TextBox", "cardinality": "ZeroToOne", "interfaceType": "NonGui", "defaultDataType": "String", "defaultOperator": "Equals", "description": "", "defaultValue": "", "isRecursive": false,
 "parameters": [
   {"id": "<ULID>", "name": "TextContent", "value": "<exact on-page text, non-Latin allowed>", "type": "Transition"},
   {"id": "<ULID>", "name": "Engine", "value": "Pdf", "type": "Configuration"},
   {"id": "<ULID>", "name": "AlgorithmicAssociation", "value": "Anchors", "type": "Configuration"}
 ],
 "attributes": [<ONE verify PdfTextArea child: BusinessAssociation=Children, X/Y/Width/Height RELATIVE to the anchor's box (same-line Y is ~0 or slightly negative), NO ForceOcr>],
 "attachments": [], "metadata": {"businessType": "TextBox", "isUsedAsIdentification": true}}
```

`AlgorithmicAssociation=Anchors` **replaces** BusinessAssociation on the anchor node. Anchor `name` = English translation of TextContent ("Total" for "Итого", "per day" for "за день"). In the test step, each anchor is wired exactly like a Page container: a top-level `Select` entry (no `value` key) whose verify child goes in `subValues`.

## Parameter type taxonomy (Pdf)

Configuration = wiring (Engine, BusinessAssociation, AlgorithmicAssociation, Parameter) · TechnicalId = `Page` only · Transition = scan-derived locator data (X, Y, Width, Height, TextContent, DocumentLanguage) · Steering = `ForceOcr` only. **Parameter array order is nondeterministic — always match by name, never by index.** `metadata.businessType` is the remapped display type (PdfPage → `Container`, PdfTextArea → `TextBox`, Document → `Document`) — never copy the attribute's own businessType into metadata. `isUsedAsIdentification` is `true` exactly on locator nodes (Page containers, anchors), `false` on leaves and business parameters.

## Step wiring (moduleReference metadata.engine = "Pdf", scanned module — no packageReference)

```json
{"$type": "TestStepV2", "reorderAllowed": false, "id": "<ULID>", "name": "Verify <Document>", "disabled": false,
 "moduleReference": {"id": "<pdf-module-uuid>", "metadata": {"isRescanEnabled": true, "engine": "Pdf"}},
 "testStepValues": [
   {"id": "<ULID>", "name": "Target PDF", "value": "{B[FileName]}", "actionMode": "Input", "dataType": "String", "actionProperty": "", "operator": "Equals", "moduleAttributeReference": {"id": "<TargetPDF-attr-ULID>", "moduleId": "<pdf-module-uuid>", "metadata": {"businessType": "Document", "isUsedAsIdentification": false}}, "subValues": [], "disabled": false},
   {"id": "<ULID>", "name": "Page 1", "actionMode": "Select", "dataType": "String", "actionProperty": "", "operator": "Equals", "moduleAttributeReference": {"id": "<Page-attr-ULID>", "moduleId": "<pdf-module-uuid>", "metadata": {"businessType": "Container", "isUsedAsIdentification": true}},
    "subValues": [
      {"id": "<ULID>", "name": "<Field>", "value": "{B[<Buf>]}", "actionMode": "Verify", "dataType": "String", "actionProperty": "", "operator": "Equals", "moduleAttributeReference": {"id": "<field-attr-ULID>", "moduleId": "<pdf-module-uuid>", "metadata": {"businessType": "TextBox", "isUsedAsIdentification": false, "valueRange": ["<literal>"]}}, "subValues": [], "disabled": false}
    ], "disabled": false}
 ]}
```

Note the Select entry has **no `value` key**. Expected values are typically buffers (`{B[CashReceipt_Amount]}`) or config params (`{CP[Username]}` against the Creator field).

## The SAP print-to-PDF-then-verify loop

1. SapEngine scanned popup module (e.g. `FBCJ | Cash Journal | Print Receipt pop up Window`): a root-level **Button** attribute `"Print Preview (F8)"`, Input value `"X"` (its valueRange shows `{Click}`; the working sample uses `"X"`).
2. UIA scanned dialog module: click `Save` (`"{Click}"` or `"X"`). UIA modules are scanned per Windows dialog — `metadata.engine: "UIA"`, no packageReference.
3. Optional retry `If`: condition = Verify `Save` `Visible` `"True"` → Then = click Save again.
4. UIA Save-dialog step with THREE values in order: `File name:` Input = composed path `"C:\\...\\<Doc> - {B[DocNum]} - {DATE[][][dd.MM.yyyy]}.pdf"` → `Save` Input `"X"` → `File name:` AGAIN with `actionMode: "Buffer"`, value `"FileName"` (**capture-after-write** is the preferred idiom — re-read the field you just typed into rather than buffering the composed string).
5. UIA: click `Close`.
6. Verification folder: the Pdf step above with `Target PDF = {B[FileName]}`.

BasicWindowOperations Standard modules seen in the same flows (packageReference `{"id": "BasicWindowOperations", "type": "Standard"}`, `metadata.engine: "Framework"`, `isRescanEnabled: false`): Take Screenshot `303256b7-59d7-4775-8fe5-198a30fd582b` (Environment/Storage Location Type/Directory/Filename/Select Screen), window ops `97567cef-0a33-488a-9cda-732d3b6658fe` (Caption + Operation e.g. `"Verify Window Exists"`), send keys `035c7ead-b699-4786-bf28-9fe7e308c64b` (Caption + Keys, dataType `RawString`, e.g. `"^{F4}"`), dialog buttons `00dbd714-20d6-4913-add8-b6b576930056` (Caption + Button), Save As `a5b947d8-5b99-4bb3-9fa8-0e5c1c5e9600` (Caption + FilePath). Confirm per tenant via `GET /_mbt/api/v2/builder/packages`.
