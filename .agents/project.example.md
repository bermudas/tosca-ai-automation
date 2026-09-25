# Project setup

<!-- Copy to .agents/project.md (gitignored) and fill in, or let the agent do it (skill `tosca-project-memory`: onboard / learn / remember).
     Label entries with their source: user | observed n/N | verified <date> | inferred. No secrets. -->

## Platform
- Platform: Commander | Cloud | both
- Commander: workspace `<path>.tws`, single/multi-user, MCP port `46248`, Commander version `<26.1>`
- Cloud: tenant `<tenant>.my.tricentis.com`, workspace/space `<name>` (`<id>`), runtimes available: toscactl / tn / Cloud MCP / tosca_cli.py

## Where tests go
- New test cases: `<folder path>`
- Modules: `<folder path>` (group by application / page)
- Reusable blocks: `<library path>` (login, open browser, SAP logon, …)
- Playlists / ExecutionLists: `<name>` for smoke, `<name>` for regression

## Execution
- Debug runs: personal agent `<name>` / local Commander
- CI runs: agent / pool `<name>`
- Browser: Chrome, maximized

## Testing approach
- e.g. risk focus, what to automate first / never, data strategy, how to handle known defects (Source: user)

## Conventions
- Test case naming: `<App> – <Feature> – <Scenario>`
- Module naming: `<App> | <Page> | <Area>`
- Folder layout inside a case: Precondition / Process / Verification / Postcondition
- Test data: `<data set / TestSheet>`; credentials via `<TCP names>`

## Observed conventions (learned from existing assets)
- e.g. `Modules named App | Page | Area` (Source: observed 27/30, e.g. `/Modules/Shop/Login`)

## Known issues in existing assets
- e.g. static 5 s waits in 12/30 cases, not fixed (Source: observed)

## Applications under test
- `<app>` → `.agents/apps/<app>.md`

## User preferences
- e.g. "always run on personal agent before adding to playlist", "ask before creating new modules"
