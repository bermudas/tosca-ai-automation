# .tsu object graph: classes, associations and what you can learn from them

Map of the entity graph inside a subset, built from **18 real exports** (17 Commander, 1 Cloud; 56 classes, ~50,000 entities). Everything below is observed, with counts, unless marked *(inferred)*. Same schema on both platforms (`../SKILL.md` → "Commander vs Cloud exports"). Entity-level detail per pattern and enum counts: [tsu-evidence.md](tsu-evidence.md).

## 1. Ground rules of the graph

- Every entity has `ObjectClass`, `Surrogate`, `Attributes` (all strings) and `Assocs` (name → list of surrogates). Every association is stored on **both ends** under two different names (table §3). Following either end gives the same edge.
- An `Assocs` list can point **outside the export** (e.g. a module attribute whose referenced module wasn't exported). Check that the target exists before you dereference it.
- **Order:** `Items` / `TestStepValues` / `Attributes` lists are in tree order as Commander shows them *(inferred: matches the step order in every sample checked; the `Path` attribute is always empty)*.
- **Audit links** (`CreatedByUser`, `ModifiedByUser`, `LockedBy`) appear only when `TCUser` entities are exported (full-workspace exports). Ignore them for test logic.
- **`DerivedFrom`** is the copy/instantiation lineage: an object created from a template points to its source (§2.6). 973 entities carry it, all in the Cloud export with template instances.

## 2. The graph by layer

Arrows show the association name as stored on the left-hand class; `[n]` is the number of edges observed.

### 2.1 Containers

```
TCProject ─Items→ TCComponentFolder ─Items→ TCFolder ─Items→ TCFolder …
                                               └─Items→ TestCase | XModule | ApiModule | TestStepLibrary | TestSheet
                                                        | TestCaseTemplateInstance | ExecutionList | TCConfiguration
                                                        | OwnedRecoveryScenarioCollection | ReportDefinition
```

- A folder's type is shown by `TCFolder.Items`. Container attributes: `ContentPolicy` (a string such as `+-+-----------` that restricts which object types the folder allows *(inferred)*), `TestConfigurationParameters` blob (TCPs, inherited downward), `ConfigurationLinks` → `TCConfigurationLink` → `TCConfiguration` (shared TCP sets).
- Walk `ParentFolder` up to rebuild a node path. `tsu_inspect.py` does this, including `Library` and `OwnedScenarioCollection` hops.

### 2.2 Test case → steps → values (the core)

```
TestCase ─Items→ TestStepFolder ─Items→ TestStepFolder …                 [215 / 65]
   │                  └─Items→ XTestStep | TestStepFolderReference | TestCaseControlFlowItem   [630 / 185 / 11]
   └─Items→ XTestStep | TestStepFolderReference (directly, no folder)   [106 / 20]

XTestStep ─Module→ XModule | ApiModule                  exactly 1 [894]
XTestStep ─TestStepValues→ XTestStepValue               0..N [1,838]
XTestStepValue ─ModuleAttribute→ XModuleAttribute       exactly 1 [2,780]
XTestStepValue ─SubValues→ XTestStepValue               nested values for child attributes [942]
```

- A step value always targets exactly one module attribute. **Nested values mirror the attribute tree**: a value's `SubValues` target the child attributes (`XModuleAttribute.Attributes`) of its own attribute. A container value usually has `Value={NULL}` and ActionMode `1` or Select.
- Steps and block calls can sit directly in a test case (106 steps and 20 calls do); folders (`TestStepFolder`) nest freely.
- Step attributes: `Condition` (instantiation condition, §2.6), `Repetition`, `DisabledDescription` (non-empty = disabled), `Pausable`, `BreakInstantiation`.
- Value attributes: `Value`, `ActionMode`, `ActionProperty`, `Operator`, `DataType`, `ExplicitName` (the concrete target of a placeholder attribute such as `<Row>`, `<Cell>` or `<Buffername>`), `Condition`, `DisabledDescription`.
- **Only values the author touched are stored**. A step on a 20-attribute module may carry 3 values (29 steps have none, 601 have one).

### 2.3 Modules

```
XModule ─Attributes→ XModuleAttribute ─Attributes→ XModuleAttribute …    (tree) [1,476 / 1,468]
XModule | XModuleAttribute | ApiModule ─Properties→ XParam                [1,087 / 10,881 / 146]
XModule ─AttachedFiles→ OwnedFile ─EmbeddedContent→ FileContent          (scan screenshot) [123]
XModule ─Specializations→ XModule  /  ─Generalization→                   (module inheritance) [20]
XModuleAttribute ─ReferencedModule→ XModule                               (attribute that embeds another module) [38]
XModuleAttribute ─UIChildren→ XModuleAttribute                            (visual nesting ≠ logical tree) [9]
XModule ─TestSteps→ XTestStep;  XModuleAttribute ─TestStepValues→ XTestStepValue   (usage back-links)
```

- `XParam.ParamType` says what a parameter does: 5 identification, 8 configuration, 2 steering, plus 4/6/7 (tsu-evidence enum table). `Visible=0` hides a parameter from the UI (1,373 of 12,114).
- **Module inheritance**: an `IsAbstract=1` module (10 seen) is a generalization, and concrete modules point to it with `Generalization` *(its semantics are not documented in the docs we read)*.
- **Module reference attributes**: `ReferencedModule` lets an attribute reuse a whole module (for example a shared header), which shows up as `XModule.ReferencingAttributes` on the target.
- **Usage back-links**: `XModule.TestSteps` and `XModuleAttribute.TestStepValues` answer "who uses this module / attribute" without a search. That's the fastest impact analysis.
- `OwnedFile` is almost always the XScan screenshot (`Screenshot.png`). It makes up most of the file size.

### 2.4 Reuse: libraries, blocks, business parameters

```
TestStepLibrary ─ReusableItems→ ReuseableTestStepBlock ─Items→ XTestStep | TestStepFolder | TestStepFolderReference | TestCaseControlFlowItem
ReuseableTestStepBlock ─ParameterLayer→ ParameterLayer('Business Parameters') ─Parameters→ Parameter{Name, Description, ValueSelectionGroup}
TestStepFolderReference ─ReusedItem→ ReuseableTestStepBlock                        [221]
TestStepFolderReference ─ParameterLayerReference→ ParameterLayerReference ─ParameterLayer→ (the block's layer)
ParameterLayerReference ─AllParameterReferences→ ParameterReference{Value} ─Parameter→ Parameter   [536]
```

- **Declaration vs call**: the block declares `Parameter`s once. Every call (`TestStepFolderReference`) gets its own `ParameterLayerReference` with one `ParameterReference` per parameter it sets, holding the `Value`.
- Inside the block, steps read the parameter as `{PL[Name]}`, usually as the whole value (Input 48, Insert 27 in the samples) and sometimes embedded in a Verify string (5).
- Call-site values seen: literals, `{CP[x]}` (environment and credentials), `{B[x]}` (a buffer from an earlier step), and in templates `{XL[Sheet.Attr]}` (§2.6).
- Blocks call other blocks (a `TestStepFolderReference` inside a block, 13 times) and contain control flow (14).
- `ReuseableTestStepBlock.UsedBy` lists every call site. Use it for impact analysis before you change a block.

### 2.5 Control flow

```
TestCaseControlFlowItem{StatementType, MaximumRepetitions} ─ControlFlowFolders→ TestCaseControlFlowFolder{StatementType} ─Items→ steps / folders / references / nested control flow
```

| Item `StatementType` | Folders (folder `StatementType`) | Seen |
|---|---|---|
| 1 = If | 0 Condition, 1 Then, optional 2 Else | 24 |
| 2 = loop (While shape: Condition before Loop) | 0 Condition, 1 Loop; `MaximumRepetitions` 20 / 5 | 3 |

- **Folder names are free text** ("Else do nothing", "First try"). Use the folder's `StatementType` for its meaning, not its name.
- Do loops (3 per FORMAT_GUIDE) weren't seen.

### 2.6 TestCase-Design and template instantiation (seen in the Cloud export)

```
TestSheet ─Items→ TDAttribute ─Items→ TDAttribute …                     (the data tree)
TDAttribute ─Instances→ TDInstances ─Items→ TDInstance                   (the attribute's possible values = instances)
TestSheet  ─Instances→ TDInstances ─Items→ TDInstance                    (the test-case rows)
TDInstance(row) ─Values→ TDInstanceValue ─Element→ TDAttribute
                                          └ValueInstance→ TDInstance    (which instance of that attribute this row picks)

TestCase(template) ─TemplateDetail→ TestCaseTemplateDetail ─SchemaDefinition→ TestSheet
TestCaseTemplateDetail ─Instances→ TestCaseTemplateInstance ─DataSourceDefinition→ TestSheet
TestCaseTemplateInstance ─Items→ TestCase(instance) ─DerivedFrom→ TDInstance(row)
instance steps / values / references ─DerivedFrom→ the template's counterpart
```

- A row's value is **not a string**. `TDInstanceValue.Value` was empty in every case; the row points (`ValueInstance`) to one of the attribute's instances, and that instance's `Name` is the value. `BusinessRelevant` marks attributes that are test data rather than structure.
- **Template → instance**: the template's values hold `{XL[Sheet.Path.Attr]}`. The instance copies them with the XL **resolved to the literal** (136 step values, 192 block-parameter values), and copies every other value unchanged (258 + 23). The instance TestCase is named after its row (`Name` = TDInstance name, `DerivedFromName` = the same) and sits under the `TestCaseTemplateInstance`.
- **Conditions** such as `'<Sheet attribute path>' == "<instance>"` sit on the **template's** folders, steps and block calls, not on the instances. Instantiation drops branches whose condition is false, so an instance only contains the steps its row selected.
- To answer "which data produced this test case?", follow instance → `DerivedFrom` → TDInstance → `Values` → `ValueInstance.Name` per `Element`.

### 2.7 Recovery, execution, configuration, reports

```
TCFolder ─Items→ OwnedRecoveryScenarioCollection ─Scenarios→ RecoveryScenario{ScenarioType, RetryLevel} ─Items→ XTestStep
TCFolder ─Items→ ExecutionList ─Items→ ExecutionEntry ─TestCase→ TestCase;  ExecutionList ─ExecutionLogs / ActualExecutionLog→ ExecutionLog
TCFolder | TCComponentFolder | TCProject ─ConfigurationLinks→ TCConfigurationLink ─UsedConfiguration→ TCConfiguration
TCFolder ─Items→ ReportDefinition → DataSetDefinition (TQL) / DesignerDefinition / DefinitionFile
```

`RecoveryScenario.ScenarioType`: 1 on the two scenarios named "CleanUp Scenario", 0 on the one named "Recovery Scenario" (so 0 = Recovery, 1 = CleanUp *(inferred from names)*).

API Scan exports add `ApiMessage`, `ApiSchema` and `ApiParameter`, hung off folders through `Properties` / `ExtendableObject`. Legacy (pre-XModule) modules use `Module` → `ModuleAttribute` → `ObjectControlSimple` → `ObjectMap`.

## 3. Association pairs (both ends)

The most useful pairs; the name on each side is what you read in that class's `Assocs`.

| Class.assoc | ↔ | Class.assoc |
|---|---|---|
| `TCFolder.Items` | ↔ | `<child>.ParentFolder` (TCFolder, TestCase, XModule, ApiModule, TestStepLibrary, TestSheet, TestCaseTemplateInstance, ExecutionList, TCConfiguration, OwnedRecoveryScenarioCollection) |
| `TCProject.Items` | ↔ | `TCFolder.Project` / `TCComponentFolder.Project` |
| `TestCase.Items` | ↔ | `TestStepFolder.TestCase`, `XTestStep.TestCase`, `TestStepFolderReference.TestCase` |
| `TestStepFolder.Items` | ↔ | `XTestStep.ParentFolder`, `TestStepFolderReference.ParentFolder`, `TestStepFolder.ParentFolder`, `TestCaseControlFlowItem.ParentFolder` |
| `ReuseableTestStepBlock.Items` | ↔ | same `ParentFolder` names as above |
| `XTestStep.TestStepValues` | ↔ | `XTestStepValue.TestStep` |
| `XTestStepValue.SubValues` | ↔ | `XTestStepValue.ParentValue` |
| `XTestStep.Module` | ↔ | `XModule.TestSteps` / `ApiModule.TestSteps` |
| `XTestStepValue.ModuleAttribute` | ↔ | `XModuleAttribute.TestStepValues` |
| `XModule.Attributes` | ↔ | `XModuleAttribute.Module` (also `ApiModule.Attributes`) |
| `XModuleAttribute.Attributes` | ↔ | `XModuleAttribute.ParentAttribute` |
| `XModuleAttribute.UIChildren` | ↔ | `XModuleAttribute.UIParent` |
| `XModule/XModuleAttribute/ApiModule.Properties` | ↔ | `XParam.ExtendableObject` |
| `XModule.Specializations` | ↔ | `XModule.Generalization` |
| `XModule.ReferencingAttributes` | ↔ | `XModuleAttribute.ReferencedModule` |
| `XModule.AttachedFiles` | ↔ | `OwnedFile.AttachedTo`; `OwnedFile.EmbeddedContent` ↔ `FileContent.File` |
| `TestStepLibrary.ReusableItems` | ↔ | `ReuseableTestStepBlock.Library` |
| `ReuseableTestStepBlock.UsedBy` | ↔ | `TestStepFolderReference.ReusedItem` |
| `ReuseableTestStepBlock.ParameterLayer` | ↔ | `ParameterLayer.ReuseableTestStepBlock` |
| `ParameterLayer.Parameters` | ↔ | `Parameter.ParameterLayer` |
| `ParameterLayer.ParameterLayerReferences` | ↔ | `ParameterLayerReference.ParameterLayer` |
| `TestStepFolderReference.ParameterLayerReference` | ↔ | `ParameterLayerReference.TestStepFolderReference` |
| `ParameterLayerReference.AllParameterReferences` | ↔ | `ParameterReference.ParameterLayerReference` |
| `Parameter.ParameterReferences` | ↔ | `ParameterReference.Parameter` |
| `TestCaseControlFlowItem.ControlFlowFolders` | ↔ | `TestCaseControlFlowFolder.ParentControlFlowItem` |
| `TestCaseControlFlowFolder.Items` | ↔ | `<child>.ParentFolder` |
| `TestSheet.Items` | ↔ | `TDAttribute.TestSheet`; `TDAttribute.Items` ↔ `TDAttribute.ParentItem` |
| `TestSheet.Instances` / `TDAttribute.Instances` | ↔ | `TDInstances.DefiningItem` / `TDInstances.DefiningElement` |
| `TDInstances.Items` | ↔ | `TDInstance.Instances` |
| `TDInstance.Values` | ↔ | `TDInstanceValue.Instance`; `TDInstance.UsedInValues` ↔ `TDInstanceValue.ValueInstance`; `TDAttribute.Values` ↔ `TDInstanceValue.Element` |
| `TestCase.TemplateDetail` | ↔ | `TestCaseTemplateDetail.TestCase` |
| `TestCaseTemplateDetail.Instances` | ↔ | `TestCaseTemplateInstance.TemplateDetail` |
| `TestCaseTemplateInstance.Items` | ↔ | `TestCase.ParentFolder` |
| `OwnedRecoveryScenarioCollection.Scenarios` | ↔ | `RecoveryScenario.OwnedScenarioCollection`; `RecoveryScenario.Items` ↔ `XTestStep.ParentFolder` |
| `ExecutionList.Items` | ↔ | `ExecutionEntry.ExecutionList`; `TestCase.ExecutionEntries` ↔ `ExecutionEntry.TestCase` |
| `TCConfigurationLink.UsedConfiguration` | ↔ | `TCConfiguration.UsedBy`; `<folder>.ConfigurationLinks` ↔ `TCConfigurationLink.ConfiguredItem` |

`DerivedFrom` is one-directional: there is no back-link on the source.

## 4. Questions a .tsu answers, and how

| Question | Traversal |
|---|---|
| What does test case X do, in order? | `tsu_inspect.py tree X` (TestCase → Items → … → values, blocks inlined with `--expand`) |
| Which test cases / blocks use module M or attribute A? | `XModule.TestSteps` / `XModuleAttribute.TestStepValues` → up via `TestStep` / `ParentFolder` to the TestCase or block |
| Which call sites does changing block B affect, with which arguments? | `ReuseableTestStepBlock.UsedBy` → each `TestStepFolderReference` → `ParameterLayerReference.AllParameterReferences` (`Parameter.Name` = `Value`) |
| How is a control located? | `XModuleAttribute.Properties` → `XParam` with `ParamType=5` (plus the module's own type-5 params for the window/page), self-healing alternatives in `SelfHealingData` |
| Which buffers flow between steps? | values with ActionMode 165 (Value = buffer name) or `{XB[..]}` → later values containing `{B[name]}` |
| Which environment settings does a test depend on? | every `{CP[x]}` in values and parameter references, and the TCP blobs up the `ParentFolder` chain |
| Which data row produced this instantiated test case? | TestCase `DerivedFrom` → TDInstance → Values (§2.6) |
| What's unused (within the exported scope)? | `XModule.TestSteps` empty, `ReuseableTestStepBlock.UsedBy` empty. Only conclusive for a full-workspace export; in a partial subset, users may simply not be included |
| Is this subset from Commander or Cloud? | surrogate format (GUID vs 26-char ULID), blob encoding (`../SKILL.md`) |

## 5. What a .tsu does NOT tell you

- Values of **encrypted** fields (Password DataType; a GUID plus base64).
- The **module attributes the author didn't use** in a step (they're on the module, not on the step).
- Execution results. `ExecutionLog`s export without results in the samples.
- Anything outside the subset: referenced objects that weren't included show up as dangling surrogates.

Sources: the 14 public exports listed in [tsu-evidence.md](tsu-evidence.md), plus 4 private exports on the maintainer's machine (3 Commander, 1 Cloud). Only structure and counts were taken from those; no names or values.
