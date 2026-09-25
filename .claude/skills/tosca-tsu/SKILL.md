---
name: tosca-tsu
description: >-
  Reads and explains Tosca subset files (.tsu) exported from Tosca Commander or Tosca Cloud,
  read-only: decodes the gzip+JSON entity graph, prints test-case step trees, reusable-block
  calls with parameters, modules with their locators (TechnicalIds / RelativeId), test
  configuration parameters, tells Commander exports from Cloud exports, and diffs two exports.
  Use when the user gives you a .tsu file, asks what is inside a subset, wants to reuse or
  compare tests across Commander and Cloud offline, or before importing a subset. Does NOT
  create or modify .tsu files.
---

# Tosca subset (.tsu) inspection

A `.tsu` is the same format on both platforms: a **gzip stream of UTF-8 JSON** holding a flat list of entities. One reader handles Commander and Cloud exports, so a `.tsu` is the easiest offline way to see an object model from either side, e.g. during a cross-platform reuse scan (`tosca-platform-guide` → `reuse-scan.md`).

**Read-only.** Never hand-write or patch a `.tsu` for import. Import through the platform: Commander's import, or Cloud via `tosca_cli.py cases import-tsu` / `toscactl` / `tn`. See "Writing" below for why.

## Tool

```bash
S=.claude/skills/tosca-tsu/scripts/tsu_inspect.py
python3 $S export.tsu summary              # origin guess (Commander/Cloud), class counts, test cases / blocks / modules with folder paths
python3 $S export.tsu tree ["name part"]   # step tree per TestCase / reusable block (add --expand to inline blocks)
python3 $S export.tsu modules              # modules -> attribute tree -> locator params (Tag, Id, InnerText, RelativeId, …)
python3 $S export.tsu entity <surrogate>   # one raw entity, nested H4sI blobs decoded
python3 $S export.tsu dump out.json        # pretty JSON with screenshots stripped (diffable, greppable)
```

Diff the same test between two exports (surrogates always differ between platforms, hence `--no-ids`):

```bash
diff <(python3 $S commander.tsu tree "Login" --no-ids) <(python3 $S cloud.tsu tree "Login" --no-ids)
```

Stdlib only; screenshots (`FileContent.Data`) are skipped by every command except `entity`. Exports can be tens of MB, so prefer `summary` / `tree NAME` over dumping everything into the context.

## Format in brief

```json
{"Entities": [
  {"ObjectClass": "XTestStepValue", "Surrogate": "…",
   "Attributes": {"Value": "Contact Us", "ActionMode": "69", "ActionProperty": "InnerText", "Operator": "1", …},
   "Assocs": {"TestStep": ["…"], "ModuleAttribute": ["…"], "SubValues": [], …}}
]}
```

- Every entity has exactly `ObjectClass`, `Surrogate` (its ID), `Attributes` (**all values are strings**: `"0"`, `"1"`, `"37"`) and `Assocs` (lists of surrogates).
- Associations are **bidirectional** (`XTestStep.Module` ↔ `XModule.TestSteps`), and an export contains everything its objects reference.
- Nested blobs: attributes starting with `H4sI` are base64(gzip(XML)): `TestCase.TestConfigurationParameters`, `XModule.TCProperties`. Commander blobs are **UTF-16**, Cloud blobs UTF-8 with BOM. `XParam SelfHealingData` is .NET-typed JSON in a string. `FileContent.Data` is base64 PNG, which makes up most of the file size.

## Object model

| ObjectClass | Key attributes | Key Assocs |
|-------------|----------------|------------|
| `TCProject`, `TCFolder`, `TCComponentFolder`, `TestStepLibrary` | Name | `Items`, `ParentFolder` (walk up for the path) |
| `TestCase` | Name, Description, TestCaseWorkState, TestConfigurationParameters (blob) | `Items` → folders, `ParentFolder` |
| `TestStepFolder` | Name (Precondition / Process / Verification / Postcondition …), Condition | `Items` |
| `XTestStep` | Name, Condition, Repetition, DisabledDescription (non-empty = disabled) | `Module` → `XModule`, `TestStepValues` |
| `XTestStepValue` | Value, ActionMode, ActionProperty, Operator, ExplicitName, DataType | `ModuleAttribute`, `SubValues` / `ParentValue` (recursive) |
| `XModule` / `ApiModule` | Name, BusinessType, InterfaceType, TCProperties (blob) | `Properties` → `XParam`, `Attributes`, `TestSteps` |
| `XModuleAttribute` | Name, BusinessType, Cardinality, DefaultActionMode | `Properties` → `XParam`, `Attributes` / `ParentAttribute` (child elements) |
| `XParam` | Name, Value, ParamType (**5** = TechnicalId/locator, **8** = configuration) | `ExtendableObject` (owner) |
| `ReuseableTestStepBlock` | Name | `Items`; `ParameterLayer` → `Parameter` |
| `TestStepFolderReference` (block call) | – | `ReusedItem` → block; `ParameterLayerReference` → `AllParameterReferences` → `ParameterReference{Value}` → `Parameter` |
| `TestCaseControlFlowItem` (If / loops) | StatementType | `ControlFlowFolders` → `TestCaseControlFlowFolder` named Condition / Then / Else / Loop |
| Cloud extras seen | `TestSheet`, `TDAttribute`, `TDInstance(Value)`, `TestCaseTemplateDetail/Instance`, `RecoveryScenario` | |

There's no separate `UniqueId`; `Surrogate` is the identity. ExecutionLists and TCPs as standalone entities haven't been seen in samples yet (TCPs appear only as the blob).

### ActionMode codes (bit flags)

| Code | Meaning | Confidence |
|------|---------|------------|
| 37 | Input | confirmed |
| 69 | Verify | confirmed |
| 101 | WaitOn | confirmed |
| 165 | Buffer | confirmed |
| 517 | Select (default on containers) | inferred |
| 515 | Insert (API params/headers) | inferred |
| 1 | navigation-only, on `{NULL}` container values with children | inferred |

Treat the inferred ones as hypotheses; check them against TCAPI or a known object before relying on them. Value tokens are the usual Tosca syntax: `{CLICK}`, `{NULL}`, `{B[x]}`, `{PL[x]}` (block parameter), `{CP[x]}` (config param), `{XL[x]}`. Encrypted values (a GUID plus base64) can't be decrypted outside the source workspace.

## Commander vs Cloud exports

| | Commander | Cloud |
|---|-----------|-------|
| Surrogate | Tosca sequential GUID `3a1af892-05e1-…` | 26-char **ULID** `01KY32WM…` |
| Revision / CheckOutState | real repository values | always `"0"` |
| Nested blob encoding | UTF-16 XML | UTF-8-BOM XML |
| SelfHealingData `$type` | `Tricentis.TCAddIns.XDefinitions.Modules…` | `Tricentis.TCCore.BusinessObjects.Modules.SelfHealing…` |

Otherwise it's the **same schema**: same class names, attributes and assocs. That's the file-level evidence behind `tosca-platform-guide` → `commander-vs-cloud.md`.

## Mapping to the Cloud JSON model

| .tsu | Cloud REST JSON (`toscacloud-cli`) |
|------|-----------------------------------|
| `XTestStep` + `XTestStepValue` | `TestStepV2` + `testStepValues[]` (`actionMode` names instead of codes) |
| `XParam` ParamType 5 (Tag, Id, InnerText, RelativeId…) | attribute `parameters[]` with `type: TechnicalId` |
| `XParam` ParamType 8 (Engine…) | `type: Configuration` params |
| `TestStepFolderReference` + ParameterReferences | `TestStepFolderReferenceV2` + `parameters[]` with `referencedParameterId` |
| `TestCaseControlFlowItem` | `ControlFlowItemV2` |

## Writing (.tsu generation): out of scope

Writing is just `gzip(json)`, but a file Tosca accepts on import needs consistent bidirectional associations, platform-correct IDs (GUIDs for Commander, ULIDs for Cloud), internal blobs (`TCProperties`) and re-encrypted secrets. Known attempts (bermudas/ToscaTSU `gen_tsu.py`) only graft onto a real exported skeleton, don't maintain back-links, and have no confirmed successful import. If the user explicitly wants to experiment: start from a real export, change as little as possible, keep both directions of every association, and import only into a **throwaway** workspace or space. Say clearly that it's unsupported.

## Privacy

Exports contain customer URLs, test data, screenshots and sometimes encrypted credentials. Don't paste large raw dumps into chat or commit `.tsu` files or dumps to this repo. Summarize instead.

Source of the approach: [bermudas/ToscaTSU](https://github.com/bermudas/ToscaTSU) (MIT); its Playwright conversion parts aren't included here.
