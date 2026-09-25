---
name: tosca-project-memory
description: >-
  Builds and maintains the shared project memory in .agents/ for Tosca automation.
  (1) Onboarding: capture where and how the user automates (Commander/Server or Cloud,
  instance/workspace/tenant, folders, agents, conventions, testing approach). (2) Learning
  from existing assets: read-only mining of test cases, modules and reusable blocks that
  people already built, to extract the team's conventions and patterns (and anti-patterns).
  (3) Capturing expert know-how the user shares (Tosca design patterns, hints, rules).
  Use on first contact with a project (no .agents/project.md), when the user describes their
  setup or shares Tosca patterns ("remember that…", "we always…"), or when asked to learn,
  analyze or harvest conventions from an existing workspace or tenant.
argument-hint: "[onboard | learn <folder/area> | remember <pattern or hint>]"
---

# Tosca project memory

Memory lives in `.agents/` (conventions: `.agents/README.md`). This skill describes how to **fill** it. Everything written gets a **source label** so later agents know how much to trust it:

| Label | Meaning | Precedence |
|-------|---------|------------|
| `Source: user` (+ name/role if given, e.g. "certified Tosca engineer") | Stated by the user, a decision | 1: follow it, even over skill defaults, unless it would mask defects or leak secrets (then say so) |
| `Source: observed n/N` | Mined from existing assets: n of N sampled assets follow it | 2: default convention for new work |
| `Source: verified <date>` | Proven live (exploration, a run) | 2: can go stale; re-verify |
| `Source: inferred` | Your own reasoning, not yet confirmed | 3: propose, don't impose |

If a new entry conflicts with an existing one or with a skill rule, **don't silently overwrite**: show both and ask the user which one wins, then record the decision (`Source: user`).

## Workflow 1: Onboard (first contact, or the user describes the setup)

Trigger: `.agents/project.md` doesn't exist, or the user gives setup information.

1. **Capture whatever the user already said** into `.agents/project.md` (create it from `project.example.md`). Don't ask again for things they already told you.
2. **Discover what the tools can tell you** instead of asking: Commander `get_workspace_info` (workspace, multi-user) / `Get-CommanderAutomationPaths`; Cloud `verify_toscactl.py` (tenant, workspace), `toscactl` workspaces, agents. Record the results as `Source: verified`.
3. **Ask only for what's still missing and matters now**, in **one** short batch (at most ~5 questions), for example:
   - Commander or Cloud (or both)? Which workspace / tenant + space?
   - Where do new test cases, modules and reusable blocks go?
   - Which agent or ExecutionList/playlist for debug runs, and which for CI?
   - Naming conventions, or "learn them from existing cases"?
   - Anything about how you want testing approached (risk focus, data strategy, what not to automate)?
4. Offer **Workflow 2** if the workspace or tenant already has assets ("Shall I learn your conventions from the existing test cases in `<folder>`?").
5. Summarize what you stored.

## Workflow 2: Learn from existing assets (read-only)

Goal: make new work look like the team's existing work, and spot recurring problems.

1. **Scope**: the folder(s) the user names, or the most relevant area for the task. Sample about **10–30** representative test cases (recent, different authors and areas) plus the modules and blocks they use. Never modify anything.
2. **Read**, per platform:
   - Commander (open): tree walk with `get_object_info` (paged), then `get_attributes` in small batches (`commander-mcp` → `explain-test-case.md`). Headless: TQL via TCShell/TCAPI (`cli-api-commander`).
   - Cloud: `tosca-find` / `toscactl`; JSON via `tosca_cli.py cases steps <id> --json`, `modules get --json`, `blocks get --json`.
   - Offline: a `.tsu` export via the `tosca-tsu` skill (`summary`, `tree`, `modules`).
3. **Extract** and count (n/N):

   | Dimension | What to look for |
   |-----------|------------------|
   | Structure | Folder layout inside cases (Precondition / Process / Verification / Postcondition?), folder tree for cases/modules/blocks |
   | Naming | Test cases, modules (`App \| Page \| Area`?), steps, blocks, buffers |
   | Reuse | Which reusable blocks exist and how often they're used (login, open app, SAP logon, cleanup); business-parameter style |
   | Modules | Grouping per page/screen, scanned vs hand-made, locator styles (Id / Name / InnerText / ClassName / RelativeId), self-healing on or off |
   | Steering | Verify style (property + operator), buffers and dynamic expressions, WaitOn vs static Wait, If/loops, recovery/cleanup scenarios |
   | Data | TCPs (Browser, URL, credentials), TestSheets / data sets, hard-coded values |
   | Execution | ExecutionLists / playlists, agents, recurring failures in recent runs (`tosca-analyzing-execution-history`) |
   | **Anti-patterns** | Static waits, disabled steps without a reason, duplicated modules for the same page, unconditional popup handling, weakened Verifies, credentials in values |

4. **Write**:
   - Project conventions → `.agents/project.md` → *Conventions* (`Source: observed n/N`, with 1–2 example asset names/paths).
   - App-specific facts → `.agents/apps/<app>.md`.
   - Generic, reusable patterns (not tied to this project) → `.agents/patterns/<topic>.md`.
   - Anti-patterns → a *Known issues* list in `project.md`. **Report them; don't fix them** unless the user asks.
5. **Report**: 5–10 key conventions, the notable anti-patterns, and what you'll do by default from now on. Ask the user to confirm or correct. Their answers become `Source: user`.

## Workflow 3: Capture expert know-how

Trigger: the user shares hints or rules ("remember…", "we always…", "a good pattern for X is…", "never do Y in Tosca").

1. **Capture it faithfully**: their wording, the context it applies to (platform, engine, app type) and the reason if given. Label it `Source: user`, plus their role if they gave it (e.g. certified Tosca engineer).
2. **Classify and file it**:
   - Project- or team-specific rule (naming, folder policy, "ask before new modules") → `.agents/project.md` → *Conventions* / *User preferences*
   - App-specific → `.agents/apps/<app>.md`
   - Generic Tosca design pattern (useful in any project) → `.agents/patterns/tosca-design.md` (create it from `tosca-design.example.md` if missing), or a topic file such as `patterns/web.md` / `patterns/sap.md`. All of `.agents/` is gitignored and stays private. If the pattern is generic enough to benefit every project, **offer** to also propose it for the toolkit's skills (e.g. `web-exploration/references/web-patterns.md`, `toscacloud-cli/references/best-practices.md`), without any project or customer details.
3. **Check it against the skills.** If it contradicts a skill rule (e.g. the no-defect-masking rule, the TechnicalId priority, the ULID rules), point out the difference, ask which applies, and record the outcome. If the expert's pattern is better and generic, propose updating the skill as well (e.g. `toscacloud-cli/references/best-practices.md`).
4. **Apply it immediately** in the current task where relevant, and confirm briefly: "Noted in `.agents/patterns/tosca-design.md`: …".

## Pattern entry format

```markdown
## <Short name>
- **When:** <trigger / context: platform, engine, app type>
- **Do:** <the pattern, concrete (step layout, action mode, locator, block)>
- **Why:** <reason / failure it prevents>
- **Source:** user (certified Tosca engineer) | observed 12/15 (e.g. `/TestCases/Orders/VA01 Create`) | verified 2026-09-25
```

Keep entries short, update instead of duplicating, and never store secrets or customer data in files that are committed.
