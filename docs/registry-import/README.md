# Registry import: processors and data sources from Excel

An administrator can fill the processor and data-source registers from an Excel
workbook (`.xlsx`) instead of one form at a time. In the console it is the
**Import from Excel** button on the Processors and Data sources pages, shown to
the administrator only.

## Files here

| File | What it is |
| --- | --- |
| `processors-template.xlsx` | Empty processors workbook: headings, dropdowns and a "How to fill" sheet |
| `processors-sample.xlsx` | The same, with five fictional processors |
| `data-sources-template.xlsx` | Empty data-sources workbook |
| `data-sources-sample.xlsx` | Six fictional data sources that name the sample processors |

All names, contract references and codes in the samples are made up. Import the
processors first: a data source names its processor, which must already be
registered and active.

The API serves the same workbooks, so these files are a convenience copy:
`GET /processors/import/template?sample=true` gives the current one.

## API (administrator only)

| Method and path | What it does |
| --- | --- |
| `GET /processors/import/template` | The workbook to fill in; `?sample=true` adds example rows |
| `POST /processors/import/check` | What the workbook would create, skip and refuse. Writes nothing |
| `POST /processors/import` | Creates every row, or none (201) |
| `GET /sources/import/template` | As above, for data sources |
| `POST /sources/import/check` | As above |
| `POST /sources/import` | As above |

The upload is `multipart/form-data` with one field, `file`, of type
`application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` (max 25 MB,
1,000 rows). Every other role gets 403.

Both `check` and `import` return the same report:

```json
{
  "kind": "processors",
  "applied": true,
  "total": 5, "created": 4, "skipped": 1, "errors": 0,
  "rows": [
    {"row": 2, "name": "Pune Gait Research Labs Pvt Ltd", "outcome": "created",
     "message": null, "problems": [], "uuid": "…"},
    {"row": 3, "name": "Test Processor Ltd", "outcome": "skipped",
     "message": "Already registered", "problems": [], "uuid": null}
  ]
}
```

`outcome` is `ready` (a check: would be created), `created`, `skipped` or
`error`. `row` is the spreadsheet's row number, with the headings as row 1.

## Rules

- **All or nothing.** If any row is in error, `POST …/import` creates nothing and
  answers 422 with `code: "import_rejected"` and the same report in the error
  body, so each problem can be shown against its row and column.
- **Re-uploading is safe.** A processor whose legal name is already registered
  (any case), or a source whose code is, is skipped, not created again and not
  overwritten. Edit a registered record with its form.
- **Same rules as the forms.** Required columns, lengths, the allowed values for
  type, role and exchange mode, a security date that is not in the future, a
  two-letter country code. Dates may be Excel dates or text such as
  `2026-09-15` or `15/09/2026`; In-house takes Yes/No.
- **Processors by name.** A source's Processor column takes the legal name or
  the contract reference. Unknown, ambiguous (use the contract reference) or
  suspended is an error. Blank means a source the organisation runs itself.
- **Audited.** Each row is created through the registry service, so it writes
  the same `processor.created` / `source.created` audit entry as the form.
- **Only .xlsx.** Formulas are read as their saved values, never evaluated;
  `.xls` and CSV are refused.
