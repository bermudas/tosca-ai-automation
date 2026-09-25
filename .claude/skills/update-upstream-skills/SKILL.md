---
name: update-upstream-skills
description: >-
  Updates the vendored skills and helper tools in this repo from their upstream sources
  (Tricentis/mcp-skills: Commander MCP, Commander CLI, Cloud CLI packs; bermudas/toscacloud_cli:
  toscacloud-cli, browser-verify, tosca_cli.py) with a 3-way merge that keeps local adaptations.
  Use when asked to "update/sync/refresh the Tricentis skills", "pull upstream changes", "check
  for skill updates", or to add a new upstream source. Also reviews upstream changes to files we
  merge by hand (AGENTS.md fragments, rules, the original Copilot agent).
argument-hint: "[check|apply] [--source tricentis-mcp-skills|bermudas-toscacloud-cli]"
---

# Update vendored skills from upstream

Configuration lives in `upstream.json` (sources, file mappings, path-rewrite rules, watch list). The last synced commit per source is in `upstream.lock.json`. The engine is `scripts/sync_upstream.py` (needs `git` and Python 3). Upstream clones are cached in `.cache/upstream/` (gitignored).

How the merge works: **base** = upstream at the locked commit, **ours** = the file in this repo, **theirs** = upstream now. The rewrite rules (our path/link adaptations) are applied to base and theirs first. Upstream improvements flow in, local edits survive, and only real clashes become `<<<<<<<` conflicts.

## Procedure

1. **Check** (no writes):
   ```bash
   python3 scripts/sync_upstream.py check
   ```
   Summarize for the user: new commits (subjects), changed / added / removed vendored files, watched files that changed, and other upstream changes (e.g. a new pack). If everything is up to date, say so and stop.

2. **Safety net.** If the repo is a git repo, make sure the working tree is clean (`git status`) so the update can be reviewed as a diff and reverted. If it isn't a git repo, suggest `git init && git add -A && git commit -m baseline` first, and ask before continuing.

3. **Apply**:
   ```bash
   python3 scripts/sync_upstream.py apply            # or --source <name>, --ref <tag/commit>
   ```
   This updates `upstream.lock.json`. Exit code 1 means conflicts.

4. **Resolve conflicts** (`grep -rn '^<<<<<<< ' .claude tools .github`). For each hunk:
   - **Take upstream content** for Tricentis/bermudas knowledge: commands, tool names, workflows, API behavior.
   - **Keep our adaptations**: repo paths (`tools/...`, `.claude/...`), the skill rename `tosca-automation` → `toscacloud-cli` (the `name:` must match the folder), the fallback-tier sections, the "Where this fits" section, corrected facts.
   - If upstream now covers something we patched, drop our patch. If upstream contradicts one of our deliberate corrections (see `toscacloud-cli/references/field-notes.md` header), keep ours and mention it to the user.
   - Remove every marker.

5. **New upstream paths or files not covered by a rewrite rule** (e.g. a new helper script referenced as `python3 new_script.py`): add a mapping and/or rewrite rule to `upstream.json`, and copy the file to `tools/...`. Then re-run `apply`: it's idempotent.

6. **Watched files** (listed under "watched files changed"): read the upstream diff (the command is printed) and hand-merge anything relevant into our own files:
   - `*AGENTS.md.fragment`, `copilot-instructions.md.fragment` → `AGENTS.md` / `.github/copilot-instructions.md`
   - `rules/*.md`, `README.md`, `START-HERE.md` → `AGENTS.md` routing or `tosca-platform-guide`
   - bermudas `.github/agents/tosca.agent.md`, `CLAUDE.md`, copilot-instructions → `toscacloud-cli` SKILL.md / `references/field-notes.md` (only knowledge that's actually new) or `tools/toscacloud-cli/DEVELOPING.md` (CLI-dev notes)
   - `.mcp.json` / `.vscode/mcp.json` → our templates `.mcp.json.example` and `.vscode/mcp.json.example` (never the personal active configs)

   - `bermudas-toscatsu` is **watch-only**: our `tosca-tsu` skill is an adaptation, not a copy. When `parse_tsu.py` changes, look for format discoveries (new ObjectClasses, confirmed ActionMode codes, blob encodings, Cloud specifics) and port them by hand into `tosca-tsu/SKILL.md` and `scripts/tsu_inspect.py`. Skip the Playwright-conversion changes.

7. **New or removed skills**: a skill folder added upstream appears automatically. Add it to the skills table in `AGENTS.md` (and to agent `skills:` lists if relevant). If a skill was removed upstream and deleted here, remove its mentions.

8. **Validate**:
   ```bash
   python3 scripts/sync_upstream.py validate
   ```
   It must print `validate: OK` (skill names match folders, agents reference existing skills, every skill is listed in AGENTS.md, no broken relative links, no conflict markers, JSON configs parse). Also smoke-test the helpers: `python3 tools/tosca-cloud-cli/verify_toscactl.py`, `python3 tools/tosca-commander-cli/scripts/Get-CommanderAutomationPaths.py`, `python3 -m py_compile tools/toscacloud-cli/tosca_cli.py`.

9. **Report**: source → old..new commit, what changed (short list), conflicts and how you resolved them, hand-merged watch items, new or removed skills, validation result. Don't commit unless the user asks.

## Adding a new upstream source

Add an entry under `sources` in `upstream.json` (`repo`, `ref`, `map`, optional `rewrite`, `watch`, `watch_new_dirs`), copy the files once by hand, adapting paths, and record the commit in `upstream.lock.json`. Then check that the rewrite rules reproduce the repo files: for unedited files, `apply` against the same commit must report nothing changed.
