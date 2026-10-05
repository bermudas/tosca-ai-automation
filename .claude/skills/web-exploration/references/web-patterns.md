# Web (Html engine) patterns from live exploration

App-independent patterns proven in live exploration of real sites. Each has a trigger, the pattern, and how to check it. Tosca JSON mechanics: `toscacloud-cli` → `web-automation.md`.

These are Html-engine behaviors, so they apply to **Commander and Cloud** alike. Entries dated 2026-09-25…10-02 were verified in Commander runs, the "Engine traps" table in Cloud runs; on Cloud treat them as strong hypotheses until a Cloud run confirms. Sites and Tosca evolve: when a pattern stops working or you find a better one, update the entry with the new evidence. Platform-specific mechanics (how to write the If, the fixed-wait module, persistence) differ: Commander → `tosca-platform-guide` → `commander-field-notes.md`, Cloud → `toscacloud-cli` → `web-automation.md`.

## Consent / cookie banner: always conditional
- **Trigger:** OneTrust / Cookiebot style banner on first visit.
- **Pattern:** Precondition *If*: Condition = Verify step on the `Accept` button `Exists == True` → Then `X` (or `Exists == False` → Else `X`). The Verify sits **inside** the If's Condition folder; a Buffer step before the If doesn't work. Prefer the vendor's stable id (OneTrust: `BUTTON` + `Id=onetrust-accept-btn-handler`). If the team has a shared "open browser" block, it often handles the banner already.
- **Why:** it's shown on a clean profile but absent after cookies are set, so an unconditional click fails on reused agents.
- **Check:** clear cookies and storage, reload, and confirm the banner reappears. Verified: 2026-09-25.

## Duplicate navigation labels (desktop + hamburger + menu title)
- **Trigger:** `InnerText=<label>` matches more than 1 element.
- **Pattern:** add the discriminating **ClassName** of the desktop bar instead of HREF or index, as the **full** class string (`top-navigation__item-link *js-op`, see below).
- **Check:** `document.querySelectorAll('a.<class>')` filtered by text → exactly 1 visible. Verified: 2026-09-25.

## Mega-menu items hidden until hover
- **Trigger:** submenu link exists in the DOM but has zero size or a hidden parent; Tosca says *Could not find Link*.
- **Pattern:** step 1 hover the top item (`{MOUSEOVER}`) → step 2 click the submenu item with `X`. Keep the user's hover path; don't replace it with OpenUrl.
- **Don't:** add a separate hover step on the submenu item (the flyout can collapse between steps → *Could not find*), or chain `{MOUSEOVER};{CLICK}` in one value (after the click navigates: `ObjectDisposedException … Object name: 'Link'`; `FireEvent=True` doesn't help). Verified: 2026-10-02.
- **Same link in several flyouts:** identical text / class / href can exist in more than one mega-menu column, all hidden until their own parent is hovered. Hovering the right parent is what scopes the click; record which parent in the inventory.
- **Check:** after hover, the target's `getBoundingClientRect().width > 0`. Verified: 2026-09-25.

## Relative href vs HREF TechnicalId
- **Trigger:** `getAttribute('href')` is relative (`/services`).
- **Pattern:** Tosca compares the absolute URL, so use `https://host/services` or, better, omit HREF when Tag + InnerText + ClassName is already unique.

## Headings with line breaks
- **Trigger:** `innerText` contains `\n` (styled multi-line headings).
- **Pattern:** InnerText wildcard (`Quality*Engineering`), or verify a cleaner element (breadcrumb, title).
- **Check:** compare `el.innerText` with the visible text. Verified: 2026-09-25.

## Responsive breakpoint
- **Trigger:** different DOM at small widths (hamburger instead of the top bar).
- **Pattern:** explore and run **maximized** (≥ 1280 px wide). Note the breakpoint in `apps/<app>.md`.

## Bot protection on headless browsers
- **Trigger:** "Just a moment…" / Cloudflare challenge during exploration.
- **Pattern:** explore with a visible browser, as Tosca agents do. A visible Playwright MCP browser usually gets past the interstitial after a ~6 s wait (`browser_wait_for(time: 6)`); give the Tosca run the same settle time after `OpenUrl` (observed: 3 s was not enough, 6 s was). Don't try to bypass the protection. If the agent also gets challenged, ask the app owners to allow-list the test agents.

## ClassName is the full class string
- **Trigger:** you picked one class token from DevTools (`nav-link`) and the element has several (`nav-link nav-link- active`, `top-navigation__item-link js-op`).
- **Pattern:** Tosca's Html `ClassName` compares the whole `class` attribute. Store the full string, wildcard tokens that change (`nav-link*`, `base-class *js-op`, `*tab-item*` for a tab whose active state adds a token), or leave ClassName out when Tag + InnerText is already unique.
- **Check:** `el.getAttribute('class')` for the exact string; count matches of the wildcard pattern. Verified: 2026-10-02.

## Same text repeated in a panel body
- **Trigger:** a tab title / card title also appears verbatim in the content below it.
- **Pattern:** text alone isn't unique; add the title's ClassName (full string). Verified: 2026-09-28.

## Present but collapsed: Exists, not Visible
- **Trigger:** an element (search / filter box, accordion content) is in the DOM but an ancestor has `display:none`, `offsetParent == null` or a zero-size box, even if it looked fine in an exploration pass.
- **Pattern:** verify `Exists == True` (structural presence); `Visible` will fail and a longer wait won't help. Only use `Visible` for elements you saw rendered.
- **Check:** `getComputedStyle`, `el.offsetParent`, `getBoundingClientRect()` before choosing the property. Verified: 2026-10-02.

## Settle after navigation
- **Trigger:** any click that loads a new page, and the first search right after `OpenUrl`.
- **Pattern:** a settle step before the next search or verify (shared wait-for-page block, a WaitOn on the new page, or a short fixed wait: `TBox Wait` on Commander, the `Wait` standard module on Cloud). Without it the engine throws transient `busy tab` / `Pipe is broken` / `Invalid buffer length` errors rather than "not found". Verified on 2 sites: 2026-09-25.

## Dynamic counts and texts
- **Trigger:** "Showing N results", dates, counters.
- **Pattern:** verify presence / visibility of the container or a wildcard (`Showing * results`), never the current number.

## Engine traps (Html engine, seen on Cloud; apply to Commander until proven otherwise)

Verified on Tosca Cloud runs against an AngularJS shop (2026-07), from `toscacloud-cli`. Same engine as Commander.

| Symptom | Cause | Fix |
|---|---|---|
| `OpenUrl` `[Succeeded]` but nothing reloaded | Target URL is hash-identical to the current one (`https://host/#/` while at `#/`): no document load at all | Change more than the hash (`https://host/?reload=1#/`), then prove it with the freshness probe (`test-patterns.md` P13) |
| Steps right after `OpenUrl` act on the old page and "succeed" | `OpenUrl` only issues the navigation (≈0.04 s duration is the tell) | Follow it with a WaitOn / freshness guard; for a route change prefer the app's own link (an SPA transition WaitOn can sync on) |
| Logged out after a reload although cookies survive | The SPA kept its session in memory | Re-authenticate after any reload; clone the working login steps rather than writing a second variant |
| SPA input `[Succeeded]` but the field keeps its default value; ~50 % flaky | `UserSimulation=True` steering types at whatever has focus, not at the resolved element | Remove `UserSimulation`, keep `FireEvent=change`; guard the input with a Verify (P13). A longer settle does **not** fix it |
| `Found multiple controls for Link '…'` on an `Id` that is unique in the DOM | Module not tab-scoped: with `Title="*"` (or an SPA that has one title on every route) attributes resolve against every open tab of the app | Module-level `Url=https://host*` TechnicalId (+ the real `Title`), and keep the leftover-tab cleanup in Precondition. Check this **before** touching the selector |
| Leftover-tab cleanup `If` hard-fails when no tab is open | A GUI Verify as the condition can't evaluate false when the document doesn't exist | Condition = `Verify JavaScript Result` probe (`UseActiveTab=False`, `Title=*<App>*`, JS `return 'present'`, Result `present`); Then = `CloseBrowser Title="*<App>*"` |
| `Tag=BUTTON` + `Name=…` → `Could not find Button` | `Name` resolved on `INPUT` but not on `BUTTON` in the same run | Use `Id` or `InnerText` for buttons |
| `Could not find Container '…'` on an `H2` whose InnerText is byte-exact | Seen on Cloud with the heading modelled as `Container`; a nested `SPAN` resolved at once. **Conflicting evidence:** on Commander `H1` / `H2` attributes with `BusinessType=GenericGUI` + InnerText verified green on two sites | Try `GenericGUI` for headings first; if it still fails, target the nested / adjacent `SPAN` or `DIV`. Record which worked |
| `Expression … could not be parsed … Token is not valid in this context: {` in a JavaScript step | Any `{` in the value is parsed as a Tosca expression | Brace-free JS: expression-bodied arrows, ternaries, `String.fromCharCode(10)` for newlines |
| Below-the-fold element `Could not find` although it's in the DOM | Hypothesis only (viewport scoping), never independently reproduced; the one case was a heading (row above) | Check the tag first; then scroll (`{PAGEDOWN}`) or verify via `Verify JavaScript Result` |
