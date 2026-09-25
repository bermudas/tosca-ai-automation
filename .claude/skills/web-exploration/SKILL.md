---
name: web-exploration
description: >-
  Explores a web application scenario live with the Playwright MCP (plus browser-verify
  for deep DOM/JS checks) and produces a Tosca-ready page/element inventory: page Url/Title
  identity, unique TechnicalIds (Id, Name, Title, InnerText, HREF, ClassName, Tag),
  uniqueness proof, action sequence and verification points. Use before building or fixing
  Tosca Html-engine tests (Commander or Cloud), or when asked to walk through a web
  scenario. Does NOT build the Tosca artifacts itself.
---

# Web exploration for Tosca (Html engine)

Walk the scenario in a real browser and record each page and element you touch, **before** writing any Tosca module or step. Tosca's Html engine (Commander and Cloud) identifies controls with the same DOM properties you inspect here.

Tools: **Playwright MCP** (`playwright` server) for navigation and snapshots. **browser-verify** skill (CDP) when you need JS in page context, computed styles, cookies or network detail.

## Exploration loop

1. `browser_navigate <url>`. Resize to the size the Tosca agent will use (maximized, about 1920×1080). The Html scanner is viewport-scoped.
2. `browser_snapshot`: the accessibility tree gives you candidate elements and refs.
3. For each element the scenario touches, pick TechnicalIds in this priority order and **prove uniqueness**:
   1. `Tag` + `Id` (form fields)
   2. `Tag` + unique `Title`
   3. `Tag: INPUT` + `Name`
   4. `Tag` + `InnerText` (exact, case-sensitive, full textContent; `*` wildcard allowed)
   5. `Tag` + `HREF` (absolute) + `ClassName`
   6. `Tag` + `ClassName` (semantic names only, never hashed `css-abc123`)

   ```js
   // browser_evaluate — must return 1
   document.querySelectorAll('<css for chosen properties>').length
   ```
   Also check that the element is visible in the viewport (`getBoundingClientRect().y` within `innerHeight`) and not under a `visibility:hidden` parent.
4. Act like the user would (`browser_click`, `browser_type`, `browser_select_option`, hover for menus). Keep the user's real path: no direct URL jumps they didn't make.
5. At each verification point, record the property and the expected value (`Visible`, `InnerText`, value).
6. Note dynamic data (order numbers, dates) to **buffer**, and anything that needs waits (SPA loads, spinners).

## Output: page/element inventory

```markdown
### Page 1 — Login
Url: https://shop.example.com/login* | Title: Login – Example Shop

| # | Element | TechnicalIds | Unique? | Action / value | Verify |
|---|---------|--------------|---------|----------------|--------|
| 1 | Email | Tag=INPUT, Id=Email | 1 ✓ | Input `{CP[User]}` | — |
| 2 | Log in | Tag=BUTTON, InnerText=Log in | 1 ✓ | Click | — |
| 3 | Account link | Tag=A, InnerText=*@*.* | 1 ✓ | — | Visible=True |
```

Known traps and proven patterns (consent banners, duplicate nav labels, hover-only menus, relative href, line-broken headings, breakpoints, bot protection): [references/web-patterns.md](references/web-patterns.md).

Hand the inventory to the builder (`commander-mcp` for Commander; `tosca-authoring-automated-testcase` / `toscacloud-cli` for Cloud). Module JSON details, action modes, the 4-folder case layout and debugging for the Html engine: `toscacloud-cli` → [web-automation.md](../toscacloud-cli/references/web-automation.md) and [best-practices.md](../toscacloud-cli/references/best-practices.md). The TechnicalId concepts are the same in Commander XModules.
