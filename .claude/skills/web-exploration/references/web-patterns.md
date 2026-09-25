# Web (Html engine) patterns from live exploration

App-independent patterns proven in live exploration of real sites. Each has a trigger, the pattern, and how to check it. Tosca JSON mechanics: `toscacloud-cli` → `web-automation.md`.

## Consent / cookie banner: always conditional
- **Trigger:** OneTrust / Cookiebot style banner on first visit.
- **Pattern:** Precondition step *If* `Accept` button `Visible == True` → `{CLICK}`. Prefer the vendor's stable id (OneTrust: `BUTTON` + `Id=onetrust-accept-btn-handler`).
- **Why:** it's shown on a clean profile but absent after cookies are set, so an unconditional click fails on reused agents.
- **Check:** clear cookies and storage, reload, and confirm the banner reappears. Verified: 2026-09-25.

## Duplicate navigation labels (desktop + hamburger + menu title)
- **Trigger:** `InnerText=<label>` matches more than 1 element.
- **Pattern:** add the discriminating **ClassName** of the desktop bar (e.g. `top-navigation__item-link`) instead of HREF or index.
- **Check:** `document.querySelectorAll('a.<class>')` filtered by text → exactly 1 visible. Verified: 2026-09-25.

## Mega-menu items hidden until hover
- **Trigger:** submenu link exists in the DOM but has zero size or a hidden parent; Tosca says *Could not find Link*.
- **Pattern:** top item `{MOUSEOVER}` → submenu item `{CLICK}` in the same step folder. Keep the user's hover path; don't replace it with OpenUrl.
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
- **Pattern:** explore with a visible browser, as Tosca agents do. Don't try to bypass the protection. If the agent also gets challenged, ask the app owners to allow-list the test agents.
