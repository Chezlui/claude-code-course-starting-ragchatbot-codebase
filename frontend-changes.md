# Frontend Changes

## Dark/Light Theme Toggle

### Files Modified

- `frontend/index.html`
- `frontend/style.css`
- `frontend/script.js`

---

### `frontend/index.html`

Added a `<button class="theme-toggle" id="themeToggle">` element directly inside `<body>`, before `.container`. It contains two inline SVGs:

- `.icon-moon` — shown in dark mode (default); clicking switches to light mode
- `.icon-sun` — shown in light mode; clicking switches back to dark mode

Attributes: `aria-label="Toggle theme"` and `title` for accessibility and tooltip support.

---

### `frontend/style.css`

#### 1. CSS Custom Property expansion

Added new theme-aware variables to `:root` (with light-mode overrides in `[data-theme="light"]`):

| Variable | Dark value | Light value | Used by |
|---|---|---|---|
| `--source-link-color` | `#93c5fd` | `#1d4ed8` | source badge text |
| `--source-link-hover-color` | `#ffffff` | `#0f172a` | source badge hover text |
| `--code-bg` | `rgba(0,0,0,0.25)` | `rgba(0,0,0,0.06)` | `<code>` / `<pre>` backgrounds |
| `--error-color` | `#f87171` | `#dc2626` | error message text |
| `--error-bg` | `rgba(239,68,68,0.1)` | `rgba(239,68,68,0.08)` | error message background |
| `--error-border` | `rgba(239,68,68,0.2)` | `rgba(239,68,68,0.25)` | error message border |
| `--success-color` | `#4ade80` | `#16a34a` | success message text |
| `--success-bg` | `rgba(34,197,94,0.1)` | `rgba(34,197,94,0.08)` | success message background |
| `--success-border` | `rgba(34,197,94,0.2)` | `rgba(34,197,94,0.25)` | success message border |
| `--transition-theme` | shared shorthand | — | reused across surface elements |

#### 2. Hardcoded colors replaced with variables

Previously, several elements had literal color values that would look wrong in light mode:
- `.sources-content a/span` — `color: #93c5fd` → `color: var(--source-link-color)`
- `.sources-content a:hover` — `color: #fff` → `color: var(--source-link-hover-color)`
- `.message-content code/pre` — `rgba(0,0,0,0.2)` → `var(--code-bg)`
- `.error-message` — all three color properties use error variables
- `.success-message` — all three color properties use success variables

#### 3. Smooth transitions added to surface elements

`transition: var(--transition-theme)` (covers `background-color`, `color`, `border-color`, `box-shadow` at 0.3s ease) added to:
- `body`
- `.sidebar`
- `.message-content`
- `.chat-input-container`
- `#chatInput` (merged with existing `all 0.2s ease`)
- `.stat-item`
- `.suggested-item` (merged with existing `all 0.2s ease`)
- `.error-message`
- `.success-message`
- `.message-content code` and `pre`

#### 4. Toggle button styles (`.theme-toggle`)

Fixed-position circular button (40×40 px) in the top-right corner:
- Uses `var(--surface)`, `var(--border-color)`, `var(--text-secondary)` so it adapts to both themes automatically
- Hover: scales up, highlights in primary blue, adds blue glow
- Focus: `box-shadow: 0 0 0 3px var(--focus-ring)` for keyboard accessibility
- Active: slight scale-down for tactile feedback
- `transition` covers background, border, color, transform, and box-shadow

#### 5. Icon visibility

`.icon-moon` is shown by default (dark mode); `.icon-sun` is hidden.  
`[data-theme="light"]` reverses these, swapping to the sun icon without any JavaScript needed.

---

### `frontend/script.js`

1. **`initTheme()`** — Called on `DOMContentLoaded`. Reads `localStorage.getItem('theme')` and applies `data-theme="light"` to `<html>` if the user previously selected light mode, persisting preference across page reloads.

2. **`toggleTheme()`** — Checks `document.documentElement`'s `data-theme` attribute. Removes it (→ dark mode) or sets it to `"light"`, then writes the new value to `localStorage`.

3. **Event listener** — Wired in `setupEventListeners()` via `document.getElementById('themeToggle').addEventListener('click', toggleTheme)`.
