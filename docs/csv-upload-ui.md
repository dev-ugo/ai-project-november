# CSV upload interface

Functional HTML/CSS/JavaScript UI for the existing CSV Check API. It reuses the
design system already installed in the project. No additional Python or frontend
dependency is required.

## Included files

| File | Purpose |
| --- | --- |
| `app/templates/index.html` | Functional upload and report screen |
| `app/static/css/app.css` | Page layout using the design system tokens |
| `app/static/js/app.js` | File selection, upload, error states and report rendering |
| `app/static/examples/contacts.csv` | Downloadable test CSV: 3 rows, 1 duplicate, 1 empty cell |
| `docs/csv-upload-ui.md` | Integration and verification instructions |

The existing design-system CSS and reference page are not replaced. The archive
does not replace `main.py`, the API router, database code or Render settings.

## Requirements

- The previous design system is installed at `/static/css/design-system.css`.
- Static files are mounted at `/static` in `app/main.py`.
- The existing `POST /analyses` endpoint is registered and saves reports.
- Frontend and API are served from the same origin, including the forwarded
  Codespaces URL and the Render URL. No separate frontend service is needed.

## Integrate

1. Extract `csv-check-upload-ui.zip` at the root of the existing repository.
2. In `app/main.py`, import `HTMLResponse`:

   ```python
   from fastapi.responses import HTMLResponse
   ```

3. Replace the existing root route, including its decorator, with this code.
   Use the existing `APP_DIR = Path(__file__).resolve().parent` from the design
   system setup:

   ```python
   @app.get("/", response_class=HTMLResponse, include_in_schema=False)
   def home() -> HTMLResponse:
       """Display the CSV upload and analysis interface."""
       page = APP_DIR / "templates" / "index.html"
       return HTMLResponse(page.read_text(encoding="utf-8"))
   ```

   Keep one handler for `/`: replace the old handler that redirected to `/docs`.
   Remove its `RedirectResponse` import if nothing else uses it. Preserve the
   existing health, analysis and design-system routes and static mount.
4. Run the usual development command:

   ```bash
   .venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
   ```

5. Open the root URL of the forwarded port, without `/docs`. Download the example
   from the UI, then select it and click **Analyser le CSV**.

## API contract

The request is a multipart form with a `file` field, sent to:

```text
POST /analyses?delimiter=%2C
POST /analyses?delimiter=%3B
```

The browser supplies the multipart boundary; JavaScript does not set a
`Content-Type` header manually. The successful response is expected to be:

```json
{
  "id": 1,
  "filename": "contacts.csv",
  "created_at": "2026-11-03T10:00:00+00:00",
  "row_count": 3,
  "duplicate_count": 1,
  "empty_cell_count": 1,
  "anomalies": [
    {"type": "empty_cell", "row": 3, "column": "email"},
    {"type": "duplicate_row", "row": 4}
  ]
}
```

IDs, dates and values in this example are illustrative. The UI displays the actual
values returned by the backend; it does not generate or simulate reports.

## Behavior

- Picker and drag-and-drop both send the selected file. Only one file is accepted.
- Files must have a `.csv` extension, a filename of at most 255 characters,
  nonzero size and size no greater than 1 MiB.
- The user explicitly chooses comma or semicolon. UTF-8, CSV syntax, header and
  row validation are performed by the existing API.
- The primary button is enabled only after a valid selection.
- During the request, file controls and reset are disabled; duplicate submissions
  are prevented. The controls are re-enabled after success or error.
- Changing file or delimiter hides the previous result to avoid mixing reports.
- API validation errors are translated into French. Network, timeout and
  malformed-response errors do not display a successful report.
- The request times out after 90 seconds. No automatic retry is performed. A
  timeout cannot prove that the server did not already save the report.
- At most the first 200 findings are rendered to keep large reports responsive.
  All counts and the saved backend report remain complete.
- Header-only files have an explicit neutral state. A file with no detected
  issues is described only in terms of the two implemented checks.
- Filenames and column names are inserted with `textContent`, never interpolated
  into HTML. Server data cannot create markup in the report.
- Dynamic statuses are announced, inputs have labels, the report receives focus
  after success, and scrolling respects reduced-motion preferences.
- Saving is handled entirely by the existing backend transaction. This step does
  not add history retrieval: reloading the page clears the displayed result, but
  keeps the report in PostgreSQL.

## Verify in Codespaces and on Render

1. `/` loads the upload page; `/docs`, `/health` and `/design-system` still work.
2. Download and upload the example: a saved report ID/date, 3 rows, 1 duplicate,
   1 empty cell; anomalies refer to CSV lines 3 and 4.
3. Upload a valid CSV with no empty cells or duplicates: show zero findings.
4. Upload a header-only file: show no data rows, not a blanket success claim.
5. Select a `.pdf`, a zero-byte file or a CSV over 1 MiB: block submission with
   a readable message.
6. Use a semicolon CSV and select **Point-virgule**: its columns are parsed correctly.
7. Submit a malformed CSV or non-UTF-8 file: show the API error and allow retry.
8. Use reset/new analysis after a result; select the same file again; verify that
   the previous result is cleared and the new file is sent correctly.
9. Check the layout at approximately 390 px: cards stack and the results table
   scrolls inside its own container.

## Commit

Implementation verification performed before delivery:

- FastAPI route/static-file checks and real multipart requests to an isolated
  API using the existing backend contract, with readback from an SQLite test DB.
- In-memory DOM tests with mocked requests for selection, multipart encoding,
  separator, loading, duplicate-submit prevention, errors, reset, large reports
  and safe rendering of filenames/column names. These do not upload files.
- Desktop and approximately 390 px browser layout checks.
- The browser test environment denied file-upload permission, so an actual
  browser file-picker upload and the connection to the user's Render instance
  still need to be verified using the steps above.

```bash
git add app/main.py app/templates/index.html app/static/css/app.css app/static/js/app.js app/static/examples/contacts.csv docs/csv-upload-ui.md
git diff --cached
git commit -m "feat: add CSV upload interface and display saved reports"
git push
```

After Render's automatic deployment succeeds, test the root page and a real
upload on the hosted URL. PostgreSQL on Render is independent of the development
database in Codespaces.
