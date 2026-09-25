# Reusable Test Step Blocks — Deep Dive

## What blocks are

Blocks (`reuseableTestStepBlocks`) are reusable step sequences with a typed parameter interface. They are the primary way to build **data-driven test matrices** in TOSCA Cloud — one block defines the steps, many test cases supply different parameter values.

## Block endpoint (note the Tricentis typo: `reuseable`)

```
GET/PUT/PATCH/DELETE /{spaceId}/_mbt/api/v2/builder/reuseableTestStepBlocks/{id}
```

## How blocks connect to test cases

```
ReuseableTestStepBlock
  └── businessParameters[]
        ├── { id: "ULID", name: "Material1",         valueRange: [] }
        ├── { id: "ULID", name: "Material2",         valueRange: [] }
        └── { id: "ULID", name: "NumberOfMaterials", valueRange: ["1","2","3"] }

TestCaseV2.testCaseItems[]
  └── TestStepFolderReferenceV2
        ├── reusableTestStepBlockId: "b0e929fa-..."   ← the block's UUID
        ├── parameterLayerId: "<the BLOCK's own layer ULID>"  ← copied verbatim from the block; omit entirely when parameters is []
        └── parameters[]
              ├── { id: "<fresh-ULID>", name: "Material1", referencedParameterId: "<block-param-id>", value: "YSD_HAWA230" }
              └── { id: "<fresh-ULID>", name: "NumberOfMaterials", referencedParameterId: "<count-param-id>", value: "3" }
```

**Key rule**: every `referencedParameterId` must match an `id` in the block's `businessParameters[]`. Use `blocks get <blockId> --json` to get those IDs.

## parameterLayerId — belongs to the block, not the reference

`parameterLayerId` identifies the **block's parameter layer**. In production artifacts it is IDENTICAL across every case that references the same block (SAP-logon Precondition block `b0e929fa`: `01KHJSJ1DTC8N6ZYF59BJ6DQ8P` in all 6 cases that use it; the VA01 sales block: one shared ULID across all three `1/2/3 Materials` cases). Verified across 26 block references in 11 production cases — zero exceptions. Rules:

1. **Referencing a block already referenced elsewhere with parameters** → COPY the `parameterLayerId` verbatim from the block itself (`blocks get --json <blockId>` → root-level `parameterLayerId`) or from any existing reference (`cases get --json <otherCaseId>`). Do not mint a new one.
2. **First-ever parameterized reference to a block** → mint one fresh ULID; all later references reuse it.
3. **No parameter overrides** (`"parameters": []`) → **omit the `parameterLayerId` key entirely** (observed on every Postcondition reference — the key is dropped, not nulled/empty; a parameterless block has no root `parameterLayerId` either).
4. Per-reference fresh IDs are only: the reference's own `id` and each `parameters[].id`.

A parameterized reference with a missing or wrong `parameterLayerId` has all its parameter values silently ignored.

## Parameter entry shape — name is copied byte-for-byte

Each entry carries a `name` field that must match the block's parameter name **byte-for-byte, including whitespace defects** (a real production block param is named `" DocumentPath"` with a leading space, and every referencing case repeats it exactly):

```json
{"id": "<fresh-ULID>", "name": "<ParamName verbatim from block>", "value": "<literal or {CP[...]}/{B[...]}/{DATE...} expression>", "referencedParameterId": "<block businessParameter id, copied verbatim>", "parameters": []}
```

## parameters[] is a partial override, not a mirror

Only pass entries for parameters you actually set. Numbered parameter families scale with data: a 1-material case passes only `Material1`/`Material1Quantity` plus `NumberOfMaterials="1"`; the 3-material case adds the `Material2`/`Material3` families. Entries for unused family members are simply absent — the block's other `businessParameters` keep their defaults. Each family member has its own distinct `referencedParameterId` in the block — never reuse one id for two entries.

## CLI commands

```bash
python tools/toscacloud-cli/tosca_cli.py blocks get <blockId>                              # show block + businessParameters table
python tools/toscacloud-cli/tosca_cli.py blocks add-param <blockId> --name <name>          # add param, prints new ULID
python tools/toscacloud-cli/tosca_cli.py blocks add-param <blockId> --name <name> --value-range '1,2,3'
python tools/toscacloud-cli/tosca_cli.py blocks set-value-range <blockId> <paramName> --values '1,2,3,4'
python tools/toscacloud-cli/tosca_cli.py blocks delete <blockId> --force
```

## Workflow: extend a block for a new data row (e.g. add 4th Material)

```bash
# 1. Inspect the block
python tools/toscacloud-cli/tosca_cli.py blocks get <blockId> --json

# 2. Add the new parameter — CLI generates a ULID and prints it
python tools/toscacloud-cli/tosca_cli.py blocks add-param <blockId> --name Material4
# Output: New parameter Id: 01KKKF297AAQB3K3WQSMQE2WPQ  ← save this

# 3. Extend a count/enum parameter's valueRange if needed
python tools/toscacloud-cli/tosca_cli.py blocks set-value-range <blockId> NumberOfMaterials --values '1,2,3,4'

# 4. Build the new test case JSON (clone existing case body, change values)
#    - parameterLayerId: copy VERBATIM from the block / the existing case's reference
#    - Fresh id (ULID) for each parameter entry and the reference's own id
#    - referencedParameterId = the block param ULID from step 2
#    - name on each entry = the block param's name, byte-for-byte

# 5. PUT the case
python tools/toscacloud-cli/tosca_cli.py cases update <caseId> --json-file updated_case.json
```

## TestStepFolderReferenceV2 template

```json
{
  "$type": "TestStepFolderReferenceV2",
  "reusableTestStepBlockId": "<blockId>",
  "parameterLayerId": "<the block's own parameterLayerId, copied verbatim — omit when parameters is []>",
  "parameters": [
    { "id": "<fresh-ULID>", "name": "<ParamName1 verbatim>", "referencedParameterId": "<block-param-id-1>", "value": "value1", "parameters": [] },
    { "id": "<fresh-ULID>", "name": "<ParamName2 verbatim>", "referencedParameterId": "<block-param-id-2>", "value": "value2", "parameters": [] }
  ],
  "id": "<fresh-ULID>",
  "name": "BlockName",
  "disabled": false
}
```

## ULID rules

Generate a **fresh** ULID for each:
- The reference's own `id`
- Each parameter `id` inside that reference's `parameters[]`
- Each new `businessParameter.id` when adding a param to a block

**Copy verbatim** (never fresh): `parameterLayerId` (the block's own layer ID — see section above) and every `referencedParameterId`. Never reuse the *fresh* IDs across different cases or parameter slots — the server may silently ignore duplicates.

## Common pitfalls

| Situation | What to do |
|-----------|-----------|
| `parameterLayerId` missing or wrong on a **parameterized** reference | All parameter values silently ignored — copy the block's own `parameterLayerId` verbatim (`blocks get --json <blockId>`). On parameterless references the key must be **absent**, not empty |
| `referencedParameterId` wrong | Use `blocks get <blockId> --json` to get exact param IDs from `businessParameters[].id` |
| Block PUT rejects `version` field | The CLI strips it automatically — never include it manually |
| Block PUT rejects entry without `id` | Every `businessParameters` entry needs a ULID `id` — use `blocks add-param` which generates one |
| Block ID not found via `inventory search` | Block IDs come from test cases, not inventory: `cases get --json <caseId>` → `testCaseItems[].reusableTestStepBlockId` where `$type == "TestStepFolderReferenceV2"` |
