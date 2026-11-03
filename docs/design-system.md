# CSV Check design system

Version 0.1. A small, framework-free design system for the CSV Check MVP.

## Design direction

Use a light background, white surfaces, dark readable text and one blue action
color. The interface helps users upload a CSV, understand the results and open
previous reports. French is used in the UI; implementation identifiers and
documentation are in English. Fonts are provided by the operating system.

## Foundations

### Colors

| CSS token | Value | Purpose |
| --- | --- | --- |
| `--cc-bg` | `#F6F8FB` | Page background |
| `--cc-surface` | `#FFFFFF` | Cards and controls |
| `--cc-text` | `#182230` | Main text |
| `--cc-muted` | `#596579` | Supporting text |
| `--cc-border` | `#E4E7EC` | Decorative card boundaries |
| `--cc-control-border` | `#7C879A` | Input and secondary button boundaries |
| `--cc-primary` | `#1D4ED8` | Primary actions, links and focus outlines |
| `--cc-primary-hover` | `#1E40AF` | Hover on primary buttons |
| `--cc-primary-soft` | `#EFF6FF` | Supporting blue surfaces |
| `--cc-success` / `--cc-success-soft` | `#166534` / `#ECFDF3` | Successful operations |
| `--cc-warning` / `--cc-warning-soft` | `#92400E` / `#FFFAEB` | Findings that need review |
| `--cc-danger` / `--cc-danger-soft` | `#B42318` / `#FEF3F2` | Blocking upload or parsing errors |

### Typography and layout

- Font: system UI sans-serif. Use monospace only for column names and technical values.
- Main heading: responsive 32–44 px. Section: 24 px. Component: 18 px.
- Body: 16 px with 1.6 line height. Labels: 14 px. Metadata: 12 px.
- Weights: 400 for body text, 600–700 for hierarchy.
- Spacing tokens: 4, 8, 12, 16, 24, 32 and 48 px.
- Corner radii: 8 px for controls, 12 px for cards, 16 px for larger surfaces.
- Control height: at least 44 px.
- Under 700 px: navigation scrolls horizontally, columns stack, statistics stack.
- Dense tables scroll inside their own container rather than widening the page.

## Component inventory

| Component | Classes | States or variants |
| --- | --- | --- |
| Button | `cc-btn`, `cc-btn--primary`, `cc-btn--secondary`, `cc-btn--quiet` | Default, hover, keyboard focus, disabled, loading |
| Input | `cc-input`, `cc-label`, `cc-help`, `cc-error` | Default, focus, invalid, read-only |
| Select | `cc-select` | Comma or semicolon |
| File input | `cc-dropzone` | Idle, hover, keyboard focus, drag-over, selected file, invalid |
| Badge | `cc-badge` with `--neutral`, `--info`, `--success`, `--warning`, `--danger` | Status with text |
| Message | `cc-alert` with `--info`, `--success`, `--warning`, `--danger` | Message and next action |
| Card | `cc-card`, `cc-card__head`, `cc-card__body` | Content and report containers |
| Statistic | `cc-stat`, `cc-stat__label`, `cc-stat__value`, `cc-stat__hint` | Row, duplicate and empty-cell counts |
| Detail table | `cc-table-scroll`, `cc-table` | Accessible headers and scroll region |
| Empty state | `cc-empty` | First-use explanation and upload link |

## Status rules

- A report being saved is a successful operation even if it contains findings.
- Empty cells and duplicate rows are **points to review**, not necessarily errors.
- Red means the operation could not complete: invalid format, size or encoding,
  malformed CSV, or a failed request.
- Do not use "no issues" to mean that the data is fully correct: this MVP only
  checks empty cells and exact duplicate rows.
- Show labels and icons as well as color.
- Counts must map directly to `row_count`, `duplicate_count`, `empty_cell_count`.
- The example page uses the project's three-row contacts sample: one empty cell
  on CSV line 3 and a duplicate on line 4. Its values are illustrative, not live.

## Accessibility and interaction

- Keep semantic buttons, input labels, a single h1 and ordered heading levels.
- Keyboard focus is visible. The hidden native file input remains focusable.
- Dynamic upload feedback uses a status region; invalid controls reference their
  explanatory message. Unexpected real errors should be announced as alerts.
- Input boundaries and focus indicators remain visible on the page surface.
- Table headings have a `scope`; the table has a caption and a focusable scroll region.
- Animations respect `prefers-reduced-motion`.
- Avoid essential meaning conveyed only by icons, color or hover.

## File inventory

| File | Purpose |
| --- | --- |
| `app/static/css/design-system.css` | Reusable tokens, layouts and component styles |
| `app/static/js/design-system.js` | Local interactions for the reference page only |
| `app/templates/design-system.html` | Component reference using the shared CSS |
| `app/routers/design_system.py` | FastAPI route at `/design-system` |
| `docs/design-system-preview.html` | Self-contained offline copy for visual review |
| `docs/design-system.md` | Design decisions, component usage and integration |

The reference page performs **no API calls**. Its upload component only validates
the filename and size for demonstration; UTF-8 and content validation belong to
the existing API. The loading button simulates a request and never writes a report.

## Integrate into the existing FastAPI project

1. Extract the archive at the repository root. It adds the files above and does
   not contain a replacement `main.py` or deployment configuration.
2. Add these imports to `app/main.py`:

   ```python
   from pathlib import Path
   from fastapi.staticfiles import StaticFiles
   from app.routers import design_system
   ```

3. After the existing `app = FastAPI(...)` statement, add:

   ```python
   APP_DIR = Path(__file__).resolve().parent
   app.mount(
       "/static",
       StaticFiles(directory=APP_DIR / "static"),
       name="static",
   )
   app.include_router(design_system.router)
   ```

   Keep the existing router registrations and home route. If `/static` is already
   mounted, reuse that mount rather than registering it again.
4. Run the usual development command:

   ```bash
   .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Open `/design-system` on the forwarded port. Check `/health` and `/docs` still
   respond. Test the demo loader, file picker, reset, invalid extension and a
   narrow browser window. You can open `docs/design-system-preview.html` directly
   on your computer to review the same page offline.
6. Commit and push from your Codespace:

   ```bash
   git add app/main.py app/routers/design_system.py app/static/css/design-system.css app/static/js/design-system.js app/templates/design-system.html docs/design-system.md docs/design-system-preview.html
   git diff --cached
   git commit -m "feat: add CSV Check design system and component reference"
   git push
   ```

7. After Render's automatic deployment succeeds, open `/design-system` on the
   deployed API URL. This step publishes the component reference. The functional
   upload/history screens can then reuse the same classes.

## Using the components in the future UI

```html
<link rel="stylesheet" href="/static/css/design-system.css">

<button class="cc-btn cc-btn--primary" type="submit">Analyser le fichier</button>

<span class="cc-badge cc-badge--warning">Points à vérifier</span>

<div class="cc-card cc-card__body">
  <h2>Résultat de l’analyse</h2>
</div>
```

For real requests, use the existing `POST /analyses` route with multipart `file`
and the selected `delimiter` query parameter. Keep demonstration JavaScript on
the reference page only; the real screen will manage fetch, loading, API errors
and report rendering separately.
