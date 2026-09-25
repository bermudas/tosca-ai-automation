# .agents: shared project memory

Plain Markdown that **both Claude Code and Copilot** read and maintain. It's versioned and reviewable, and it's shared with the team through git. It replaces tool-private memory for anything the team should know.

| Path | Holds | Git |
|------|-------|-----|
| `README.md` | These conventions | committed (template) |
| `project.example.md` | Template for `project.md` | committed (template) |
| `patterns/tosca-design.example.md` | Template / format for `patterns/tosca-design.md` | committed (template) |
| `project.md` | **This project's setup**: platform(s), tenant/workspace, folders, agents, environments, naming conventions, user preferences | ignored |
| `apps/<app>.md` | **Application know-how**: pages/screens, stable locators, quirks, sample scenarios, test data sources, known defects | ignored |
| `patterns/*.md` | **Reusable patterns** learned in this project or shared by experts (`tosca-design.md`, `web.md`, `sap.md`, …) | ignored |

> **Everything created here is gitignored** (`.agents/` in `.gitignore`); only the templates above are tracked. Project data, tenant details and customer-specific knowledge never leave your machine by accident. In a **private** project repo, remove the `.agents/` line from `.gitignore` if the team should share the memory. To publish a new template, use `git add -f`.
>
> Generic web/SAP knowledge that ships with the toolkit lives in the skills (e.g. `web-exploration/references/web-patterns.md`), not here.

## How it gets filled

Skill **`tosca-project-memory`**: **onboard** (the user's setup: platform, instance, folders, agents, testing approach), **learn** (mine existing test cases/modules/blocks built by people for conventions and anti-patterns, read-only) and **remember** (expert hints and Tosca design patterns the user shares). Each entry carries a source label: `user` > `observed n/N` / `verified <date>` > `inferred`.

## When agents read

At the start of every Tosca task: `project.md` (if it exists), then `apps/<app>.md` for the application in scope, then the `patterns/` that fit (web / SAP / Commander / Cloud). Treat what's there as **hints to verify**, not facts. Apps and tenants change.

## When agents write

After a task, **only** for things that were verified and will save time next time:

- **Setup the user told you** (tenant, workspace, folder for new tests, preferred agent/playlist, naming rules) → `project.md`
- **App facts proven live** (a locator that works, a trap, a popup that appears only sometimes, a known product defect with its ticket) → `apps/<app>.md`
- **Patterns that worked on more than one app, or are clearly generic** → `patterns/<topic>.md`
- **Knowledge about Tosca itself** (a new API quirk, CLI behavior, engine rule) doesn't go here. Propose adding it to the relevant skill instead (e.g. `toscacloud-cli/references/field-notes.md`) so every project benefits.

## Rules

1. **Never store secrets**: no passwords, tokens, client secrets, personal data. Reference where they live (`toscactl login`, `.env`) instead.
2. **Short and factual**: bullets and tables, one topic per file, and a `Verified: YYYY-MM-DD` line on facts that can go stale.
3. **Update, don't append duplicates.** Fix or delete entries that turned out wrong.
4. **Say what you changed** in your final report (`Updated .agents/apps/shop.example.com.md: cookie banner is conditional`).
5. Ask the user before writing anything that reflects a **decision** (conventions, preferences) rather than an observation.
