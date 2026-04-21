# Frontend Changes

## Code Quality Tooling

### New files added

| File | Purpose |
|------|---------|
| `frontend/package.json` | npm package manifest with Prettier and ESLint as dev dependencies |
| `frontend/.prettierrc` | Prettier configuration (4-space indent, single quotes, 100-char print width) |
| `frontend/.eslintrc.json` | ESLint configuration for browser JS (ES2021, `eslint:recommended` + custom rules) |
| `scripts/check-frontend.sh` | Shell script to run all frontend quality checks from the project root |

### Modified files

| File | Changes |
|------|---------|
| `frontend/script.js` | Reformatted to match Prettier config: consistent single quotes, explicit `curly` braces on all conditionals, trailing commas on multiline expressions, blank line cleanup, and removal of stale comments |

---

### How to use

**Install dev dependencies (first time only):**
```bash
cd frontend && npm install
```

**Check formatting and lint from the project root:**
```bash
./scripts/check-frontend.sh
```

**Auto-fix formatting and lint issues:**
```bash
./scripts/check-frontend.sh --fix
```

**Run individual checks from inside `frontend/`:**
```bash
npm run format:check   # Prettier dry-run
npm run format         # Apply Prettier formatting
npm run lint           # ESLint report
npm run lint:fix       # ESLint auto-fix
npm run check          # format:check + lint together
```

---

### Prettier configuration (`frontend/.prettierrc`)

```json
{
  "printWidth": 100,
  "tabWidth": 4,
  "singleQuote": true,
  "trailingComma": "es5",
  "semi": true,
  "arrowParens": "always",
  "endOfLine": "lf"
}
```

### ESLint rules (`frontend/.eslintrc.json`)

- Environment: `browser` + ES2021
- Extends `eslint:recommended`
- `no-var` — enforces `const`/`let`
- `prefer-const` — flags `let` that could be `const`
- `eqeqeq` — requires `===` over `==`
- `curly` — requires braces on all control flow
- `semi` — requires semicolons
- `no-trailing-spaces` — flags trailing whitespace
- `marked` declared as a read-only global (loaded via CDN)
