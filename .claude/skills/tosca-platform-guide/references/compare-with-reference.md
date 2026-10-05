# When a build doesn't work: compare it with a working reference, then remember

You can create modules and test cases yourself, on both platforms, with any runtime in [build-guide.md](build-guide.md). You don't need a scan for every module. But when something you built doesn't behave, don't iterate blindly on guesses. Put your object next to one that works, diff them field by field, fix the difference, and record what you learned so the next build doesn't repeat it.

## 1. When to switch to comparison

Switch after **one** failed fix attempt whose cause you can't name, or immediately on any of these:

| Symptom | Usually means |
|---|---|
| `XModules and XModuleAttributes have to provide the configuration param "Engine"` | A configuration parameter is missing on the module or on an attribute |
| Control not found / "Found multiple controls" although the locator is right in the browser | Module root doesn't identify the page (`Title` / `Url`), or steering params differ from the scanned module (`IgnoreInvisibleHtmlElements`, `AllowedAriaControls`, `BusinessAssociation`) |
| Step runs but does nothing; value silently ignored | Wrong ActionMode / DataType / `ExplicitName`, value key missing, the attribute reference points to another module, or a PATCH was dropped (Cloud) |
| API accepts the write (200/204) but the object looks different when read back | Server rewrote or dropped fields; a required `metadata` echo or `id` was missing |
| Block call does nothing with its parameters | Wrong `parameterLayerId` / parameter wiring, or parameter names not byte-identical |
| It works in the UI when a colleague builds it, not when you do | The UI fills defaults you didn't: that's the diff to find |
| `Sequence contains more than one element` with unique locators; `No Transition Config defined` | Hand-built Commander module: Configuration params missing or typed as TechnicalId, or `InterfaceType` / `BusinessType` left at defaults ([commander-field-notes.md](commander-field-notes.md) §1, §3) |
| Locator unique in the browser, 0 matches at run time | `ClassName` holds one token instead of the full class string |

## 2. Pick a reference

In order of preference:

1. **A scanned module for the same page / screen**, or a **green test case** that uses it (reuse scan, [reuse-scan.md](reuse-scan.md) §1b). Same engine, same tenant / workspace, recently run.
2. **Any working module of the same engine and businessType** in the workspace (another page's `HtmlDocument`, another SAP screen). The envelope is what you're comparing, not the locators.
3. **A standard module and a case that uses it**, for standard-module steps.
4. **Ask the user for one**, in one sentence: "Could you scan this page (XScan / Cloud scanner) once, or export one working case with its modules as a `.tsu`? I'll compare mine against it." A manual scan is the ground truth for what the engine expects. Say which page and why.
5. **The shapes in this repo** ([object-anatomy.md](object-anatomy.md), `toscacloud-cli` → `web-automation.md` / `sap-automation.md`, `tosca-tsu` → `tsu-evidence.md`) when nothing on the target can be used. They're generalized, so prefer a real object when you can get one.

## 3. Read both the same way, then diff

Use the same tool for both objects so the output lines up.

| Runtime | Read | Diff |
|---|---|---|
| Cloud (`tosca_cli.py`) | `modules get --json <mine>` / `<ref>`; `cases get --json` + `cases steps --json` | `diff <(jq -S . mine.json) <(jq -S . ref.json)`; for step trees strip ids first (`jq 'del(.. \| .id?)'`) |
| Commander MCP | `get_object_info(include_parent_and_children=true)` then `get_attributes` on the module, each attribute and its parameters, for both | Compare the attribute lists side by side in `.claude/tmp/` |
| TCShell / TCAPI | `GetAttributeValue` / `print` on both; or **Export Subset** both to `.tsu` | `tsu_inspect.py a.tsu modules` vs `b.tsu modules`; `diff <(tsu_inspect tree "A" --no-ids) <(tsu_inspect tree "B" --no-ids)` |
| Any | A `.tsu` from the user | `tosca-tsu` skill, `entity <surrogate>` for the raw parameter list |

Then go through this list and note every difference, present-vs-absent first, values second:

**Module**
- Root: `Engine`; page identity (`Title`, `Url` / transaction, program, screen) and its **type** (TechnicalId vs Configuration); steering params (`ControlFramework`, `IgnoreInvisibleHtmlElements`, `AllowedAriaControls`, `EnableSlotContentHandling`); `businessType` / `interfaceType`; `metadata.engine` (Cloud).
- Each attribute: `Engine` + `BusinessAssociation` present; `businessType`; `defaultActionMode` / `defaultDataType` / `cardinality` / `valueRange`; TechnicalIds (which ones, `Tag` present, wildcards); steering (`FireEvent`); Cloud `metadata` echo (`businessType`, `isUsedAsIdentification`, `valueRange` copy); every parameter has an `id`.
- Tree: do the reference's controls sit under containers / `<Row>` `<Cell>` placeholders while yours are flat (or the reverse)?

**Test case**
- Step: `moduleReference` flavor (standard package vs scanned), `metadata.engine`; one module per step.
- Value: all keys present (`value`, `actionMode`, `actionProperty`, `operator`, `dataType`, `explicitName`, `subValues`, `disabled`); `moduleAttributeReference.id` belongs to **that** module; nested values follow the attribute tree; `ExplicitName` on placeholders; buffer values hold a name.
- Block call: `reusableTestStepBlockId`, `parameterLayerId` identical to the block's, `referencedParameterId` per parameter, names byte-identical.
- Case: `id` in the PUT body, no `version`; TCPs present where `{CP[..]}` is read; folder / `$type` discriminators.

Fix **only** the differences, one group at a time, re-read, re-run. If the diff is empty and it still fails, the problem isn't the object: look at the agent / browser / environment (`tosca-analyzing-execution-results` → `failure-taxonomy.md`).

## 4. Remember what the diff taught you

Every comparison that fixed something produces one of two kinds of knowledge. Record it before you report, with `Verified: <date>` and the source label from `.agents/README.md`.

| What you learned | Where it goes | Form |
|---|---|---|
| **Tosca behaves like this** (a required field, a default the UI fills, an API quirk, an engine rule). Same on every project | The skill, so everyone benefits: Cloud → `toscacloud-cli` SKILL.md caveats / `field-notes.md` (its self-improvement protocol); Commander → [commander-object-model.md](commander-object-model.md), [commander-authoring-apis.md](commander-authoring-apis.md); a `?` or `(u)` cell in [build-guide.md](build-guide.md) that you have now verified → replace it with the fact | One row or bullet: symptom → cause → fix, plus the version / tenant it was seen on |
| **This project does it like this** (which module to copy from, how this app's pages are modelled, a quirk of this tenant or workspace) | `.agents/apps/<app>.md` → **Reference objects**: ids / paths of a known-good module and case per page, and what to copy from them. Conventions → `.agents/project.md`. Generic recipes proven here → `.agents/patterns/` | Short bullets; never secrets |
| **A failed attempt and its fix** | `.agents/apps/<app>.md` or `patterns/`: "Tried X → failed with Y → fixed by Z" | One line, so the next run skips the detour |

Rules: update existing entries instead of adding duplicates; delete what turned out wrong; ask the user before recording a decision or preference they didn't state; say in your report what you recorded. The reference objects you found (§2) are worth recording even when nothing failed: they're the fastest start for the next scenario on the same app.
