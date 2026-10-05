# Commander field notes: what real build-and-run sessions taught

Lessons from agent sessions with a Tosca SME on a multi-user Commander 26.1 workspace (Commander MCP, Html engine), September–October 2026. Each one cost at least one failed run. They're generalized here; nothing project-specific. The object shapes and official rules are in [commander-object-model.md](commander-object-model.md); this file is the practical layer on top: what the engine and the MCP actually do.

Labels: **verified** = reproduced and fixed in a real run; **user** = rule stated by the SME (house rule, not yet contradicted by a scan); *(u)* = plausible, not proven.

**These are lessons learned, not laws.** They're the best-known way as of the date and version above, and Tosca, the MCP and the apps keep evolving. Use them as the default and the first hypothesis when something fails, but:
- If you find a better way (a newer Commander / MCP version, a working reference object, the team's own convention, a Tricentis doc), **use it** and **update this file**: change or retract the entry, add what replaced it with the evidence (version, date, what you ran), and keep the old form only as a one-line "used to be" when it helps someone on an older version.
- If an entry doesn't match what you observe, trust the observation, re-verify once, then fix the entry. Don't work around a stale note in silence.
- A user-stated or project rule (`.agents/project.md`) beats an entry here for that project.
- Not negotiable, whatever you find: no defect masking, confirm before irreversible actions, never store secrets (`AGENTS.md` guardrails).

## 0. Platform scope: what applies where

All lessons were verified on **Commander** (multi-user workspace, Commander MCP). Cloud runs the **same Html engine**, so engine and locator behavior carries over, but the tooling, persistence and run model differ. Treat engine rows as strong hypotheses on Cloud until a Cloud run confirms them.

| Section | Commander MCP, multi-user | Commander single-user / TCShell / TCAPI | Cloud |
|---|---|---|---|
| §1 Engine error table | ✓ | ✓ (same engine) | Html-engine rows apply (same engine; Cloud docs independently report the `CloseBrowser` / `UnestablishedConnectionException` and "More than one matching tab" cases). Rows on run logs / unsaved workspace are Commander-only |
| §2 Session discipline (checkout, check-in clears the run log, `save_workspace`, surrogate-id runs) | ✓ | Saving yes (`save` / `Save()`); no checkout / check-in in single-user | **Doesn't apply.** No checkout, check-in or save: every successful PUT is a new `version`; confirm with GET + version bump (`toscacloud-cli`). Run logs come from `playlists logs` / Cloud MCP `GetFailedTestSteps` and aren't cleared by edits |
| §3 Hand-built module envelope | ✓ (`execute_task("Configuration Param")`, `InterfaceType` / `BusinessType` properties) | Same properties via TCAPI (u) | Same envelope in JSON (`Engine` + `BusinessAssociation` Configuration params per attribute, `interfaceType: "Gui"`, `businessType`): `toscacloud-cli` → `web-automation.md` "Attribute anatomy". Cloud has its own BusinessType table there; prefer it on Cloud |
| §4 Html locator rules | ✓ | ✓ | ✓ (same engine) |
| §5 Step shapes (`X`, hover then click, settle after navigation, If condition) | ✓ | ✓ | ✓, with Cloud's extra If rule: give the module a tight `Url=https://host*` so the condition can cleanly miss (`web-automation.md` "Conditional steps"). Cloud fixed wait = the `Wait` standard module |
| §6 Browser lifecycle | ✓ | ✓ | ✓. Cloud's idiom for the same problem: If (Verify an always-visible app element) → `CloseBrowser Title="*<App>*"`; never `Title="*"` on agents that share the user's personal Chrome |
| §7 Block references through the MCP | ✓ | TCAPI `CreateTestStepFolderReference` instead | **Doesn't apply.** Cloud block calls are JSON (`parameterLayerId` copied verbatim, `referencedParameterId`): `toscacloud-cli` → `blocks.md` |
| §8 Workflow | ✓ | ✓ | ✓ |

## 1. Engine error → cause → fix

Read the exact engine message first, then look here before you change anything.

| Engine message (or symptom) | Usual cause | Fix | |
|---|---|---|---|
| `Sequence contains more than one element` although Tag / ClassName / InnerText are each unique on the page | A hand-authored attribute lacks the **Configuration** params `BusinessAssociation = Descendants` and `Engine = Html`, or has them as **TechnicalId** params (no error at save, wrong at run time) | Add both as Configuration params on every control attribute (§3). Inside tables / trees `BusinessAssociation` is structural (`Rows`, `Columns`, `Cells`, `Nodes`): copy it from a scanned table | verified |
| `No Transition Config defined` | Hand-authored `XModule` keeps its defaults `InterfaceType = NonGUI`, `BusinessType` empty | Set `InterfaceType = GUI`, `BusinessType = HtmlDocument` on the module, `InterfaceType = GUI` + a real `BusinessType` on each attribute | verified |
| `Could not find Link` / `Could not find <control>` on a menu item | The item lives in a flyout / mega-menu that is hidden until its parent is hovered, or the flyout collapsed between steps | Hover the parent in the step before, then `X`-click the child (§5) | verified |
| Locator looks unique in the browser but matches 0 elements | `ClassName` holds one token of a multi-token `class`; Html `ClassName` compares the **whole** attribute string | Wildcard the full string (`nav-link*`, `top-navigation__item-link *js-op`) or drop ClassName when Tag + InnerText is unique (§4) | verified |
| Locator matches >1 element although a DOM query on the class looked unique | Same label exists in hidden copies (hamburger menu, other flyout columns, panel body) | Add the discriminating ClassName (full string), and scope by hovering the right parent first | verified |
| `Connection to the HtmlEngineExtensionHelper failed` / `Unestablished connection to browser` on `CloseBrowser` | `CloseBrowser` ran with no browser session open (e.g. as the first Precondition step). It's not a no-op | Don't start a case with `CloseBrowser`; use an idempotent force-close + open block, or start with `OpenUrl` (§6). It's **not** an environment problem: check the case shape before blaming the browser extension | verified |
| `More than one matching tab was found` on `OpenUrl` / the first search | Tabs left over from earlier validation runs | Clean up in Postcondition, or start from a force-close + open block (§6) | verified |
| `Cannot interact with busy tab. Connection to application under test lost.`, `Invalid buffer length`, `Pipe is broken` (often inside document-type detection such as `IsClassicSalesforcePage`) | The search raced a page transition: right after `OpenUrl`, or right after a click that navigates | Add a settle step between the navigating action and the next search: a shared "wait for page to load" block, a WaitOn on the new page, or a short `TBox Wait` (§5) | verified on 2 apps |
| `ObjectDisposedException` ("Trying to call method: Equals, Object name: 'Link'") | A compound value (`{MOUSEOVER};{CLICK}`) or `{CLICK}` on a link that navigates: post-action sync touches a disposed element. `FireEvent = True` doesn't help | Split hover and click into separate steps and click with `X` (§5) | verified |
| Verify `Visible == True` fails on an element that exists and "looked normal" while exploring | Collapsed by default (ancestor `display:none`, `offsetParent == null`, zero-size), e.g. a filter / search box | Verify `Exists == True` for structural presence; a longer wait won't fix it | verified |
| Exact `Title` on the module root → window / representation ambiguity, even with one tab | Over-specific page identity | Use a wildcard `Title`. `*` is safe only when the Precondition guarantees a single app tab (force-close block); otherwise `*App*` and/or `Url=https://host*`. On Cloud, `Title="*"` with leftover tabs gave `Found multiple controls` on a unique id (`web-patterns.md` "Engine traps") | verified |
| Run finished but no per-step log (Commander MCP) | Run triggered without the explicit surrogate id, or the log was cleared by a check-in / checkout | §2 | user + verified |
| Objects you built "disappeared" in the next session; ids from memory don't resolve (Commander) | `save_workspace` was never called before the session ended | §2. Re-verify every remembered id with `get_object_info` before reuse | observed |
| `No Transition Config defined` / `Sequence contains…` on Cloud | Same causes in JSON: missing `Engine` / `BusinessAssociation` Configuration params or a wrong `interfaceType` | `toscacloud-cli` → `web-automation.md` "Attribute anatomy" | (u) |

## 2. Commander MCP session discipline (multi-user workspaces)

- **Check out what you need up front** (modules, case, folders), then build, run and fix while everything stays checked out.
- **Don't check in inside the fix-and-run loop.** Check-in / checkout **clears the last execution's per-step log**, so you lose the evidence of what just failed. Capture the run result first. Leave the final `check_in_all` to the user unless they ask you to do it. (user)
- **`save_workspace` after every group of mutations.** Unsaved work in a checked-out folder doesn't survive the session. (observed)
- **Run with the explicit surrogate id**: `execute_test_suite(isValidationRun=true, testCaseId=<surrogate id>)`, then poll `execute_test_suite_status`. Other forms come back without per-step logs. (user)
- `create_test_case` checks in by itself in multi-user workspaces (see `build-guide.md` §6): for an iterative build, prefer creating the case once and adding steps with `execute_drop_task`, and tell the user before the call.

## 3. Hand-authoring a GUI module (no scan available)

A real XScan in the Commander UI is the default and the reference shape. Hand-authoring (from a verified exploration inventory) is for gaps and demos; flag such modules for a real scan. A hand-built module saves and checks in fine even when it can't work at run time, so compare it against a scanned one ([compare-with-reference.md](compare-with-reference.md)).

Shape that runs (confirmed by diffing a hand-built module against the same page after a live scan):

```
XModule  'App | Page'                 InterfaceType=GUI   BusinessType=HtmlDocument
  Engine = Html                       [Configuration]
  Title  = *                          [TechnicalId]   ← wildcard, not the exact page title (`*` only with a guaranteed single tab; else `*App*` / Url)
  XModuleAttribute 'Services'         InterfaceType=GUI   BusinessType=Link   ValueRange={Click}
    Tag = A                           [TechnicalId]
    ClassName = top-nav__link *js-op  [TechnicalId]   ← full class string, wildcarded
    InnerText = Services              [TechnicalId]
    BusinessAssociation = Descendants [Configuration] ← every control attribute (table children: Rows / Columns / Cells; tree: Nodes)
    Engine = Html                     [Configuration] ← on every attribute, too
```

- Add the Configuration params with `execute_task(taskName="Configuration Param")` on the attribute id (same mechanism as on the module), then set Name / Value. Not as TechnicalID Params (§1 row 1). (verified)
- If the element has a unique `id`, `test-id` or `data-test-id`, add it as its own TechnicalID Param (`Name` = the HTML attribute name, `Value` = its value) next to the structural ones. These are the most redesign-proof locators. (user)
- `BusinessType` by HTML tag / ARIA role, not a generic placeholder (user; confirm against a scan of the same app when you get one):

  | Tag (+ role) | BusinessType |
  |---|---|
  | `A` (no role / `role=link`), `BUTTON` with `role=link` | `Link` |
  | `BUTTON` (no role / `role=button`), `A` with `role=button` | `Button` |
  | any tag with `role="tab"` | `TabItem`, plus `SpecialIcon = ListItem` |
  | `DIV`, `SPAN` | `Container` |
  | `INPUT type=text` | `TextBox` |
  | `UL` | `ListBox` |
  | `TABLE` | `Table` |
  | `IMG` | `Image` |
  | `LABEL` | `Label` |
  | `H1`–`H4`, anything else | `GenericGUI` |

- Put the legal actions in `ValueRange` (`{Click}`, `{Click};{Rightclick}`).
- Add attributes to the existing module of the same page / section before you create a new module (one control lives in one module, [commander-object-model.md](commander-object-model.md) §3.5).

## 4. Html locator rules the engine enforces

- **`ClassName` = the whole `class` attribute**, not one token. Read `el.className` (or `getAttribute('class')`) during exploration and store the full string, wildcarding dynamic tokens (`*js-op`, `* active`). A tab whose active state adds a token needs `*base-class*`.
- **`HREF` compares the absolute URL.** Pages with relative `href` (`/services`) need the absolute form, or better, no HREF.
- **InnerText with line breaks** (`Quality\nEngineering`) needs a wildcard (`Quality*Engineering`).
- **Labels repeated in hidden copies** (responsive hamburger menu, other mega-menu columns, tab-panel body repeating the tab title): text alone is not unique; add ClassName and scope by the user's hover path.
- Prove uniqueness with a live count of 1 **and** check computed visibility (`getComputedStyle`, `offsetParent`, `getBoundingClientRect`) before choosing `Visible` vs `Exists` for a Verify.

## 5. Step shapes that survive synchronization

- **Clicks: `X`** (no mouse emulation) for links and buttons. `{CLICK}` is more prone to post-action sync problems, worst right before navigation. (user + verified)
- **Hover menus:** `Hover <parent>` (`{MOUSEOVER}`) → `X`-click the child as its own step. Don't add a separate hover on the child (the flyout can collapse between steps), and don't chain `{MOUSEOVER};{CLICK}` in one value (disposed-element error after navigation).
- **Navigation then verify:** after any action that loads a new page (and right after `OpenUrl`), put a settle step before the next search: prefer the team's shared "wait for page to load" block or a WaitOn on a control of the new page; a short `TBox Wait` (2–6 s) is the fallback. Sites behind a bot-protection interstitial need the longer end (observed ~6 s).
- **Optional element (cookie banner)**: the condition is a real **Verify step inside the If's `Condition` folder**. Drop the banner module onto `If/Condition`, add the button attribute, set `ActionMode = Verify`, `ActionProperty = Exists`, `Value = False`; put the accept click (`X`) in `Else` (or the mirror: `Exists == True` → click in `Then`). A Buffer step placed **before** the If, with an empty Condition, does not work. (verified)

## 6. Browser lifecycle across repeated runs

- A case that's run again and again during development must start from a clean browser without failing when there is nothing to close.
- Best: the team's shared **force-close + open** reusable block in Precondition (typically: close the browser process if it exists, start it with the URL as a business parameter, wait for load, accept the consent banner conditionally). It's idempotent, so the Postcondition doesn't need its own `CloseBrowser`. Look for one in the reuse scan before building anything.
- Without such a block: Precondition starts with `OpenUrl`; `CloseBrowser` (with a wildcard `Title`) only in Postcondition. Or, on both platforms, the conditional form: If (condition) → `CloseBrowser Title="*<App>*"`, so it only runs when there is something to close. Make the condition a `Verify JavaScript Result` probe (`return 'present'`): a GUI Verify hard-fails instead of evaluating false when no app tab exists (Cloud, `web-patterns.md` "Engine traps").
- `Title="*"` closes every browser window: fine on grid agents / dedicated profiles, not on agents that share the user's personal Chrome.
- Never a bare `CloseBrowser` as the first step (§1).

## 7. Reusable block references through the MCP

- Insert a block as a **live `TestStepFolderReference`**: `execute_drop_task(copy=true, sourceIds=[<reference or block id>], targetId=<Precondition folder>)`. Keep it a reference; don't resolve it into plain steps. (verified)
- **Business parameter values on a new reference can be virtual placeholders** that `set_attribute` can't write until someone types a value once in the Commander UI. Workaround that works: copy **an existing reference instance** whose parameter (e.g. `Url`) already has a value; the copy carries the materialized `ParameterReference`, and `set_attribute(<param id>, "Value", "<new value>")` works at once. Fallback: ask the user to type the value once in the UI. (verified)
- A reference instance and the master `ReuseableTestStepBlock` look alike by name. Check the type with `get_object_info` before you record an id as "the block"; the master usually lives in a TestStepLibrary of a utilities / common-libraries folder.

## 8. Workflow the SME insisted on

1. Walk the scenario live (Playwright MCP) and snapshot every page, **even when the app's locators are already documented**: sites change. Re-verify, don't trust memory.
2. Check existing modules for a fit (team sandbox, shared global modules, `.agents/apps/<app>.md`) and reuse matching attributes.
3. Only if nothing fits: add attributes to the module already scoped to that page / section, or create a new module.
4. Use the team's mandatory Precondition block if there is one (record it in `.agents/project.md`).
