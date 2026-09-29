# UAT document sources

The runbook (`../COMPASS-CMP-UAT-Runbook-and-Test-Cases.docx`) and the tracker
(`../COMPASS-CMP-UAT-Test-Cases.xlsx`) are generated from the files here. Edit
these, never the Word or Excel file.

| File | Holds |
|---|---|
| `runbook.js` | Part A of the Word document: build under test, accounts, glossary, scope, what is new, coordinator setup, known limits, run order |
| `build_reg.py`, `gen_prj.py`, `gen_con.py`, `build_rgt.py`, `build_ovs.py` | The test cases for each area, written out to `REG.json`, `PRJ.json`, `CON.json`, `RGT.json`, `OVS.json` |
| `ACC.json` | The access cases, kept as data directly |
| `build_docx.js` | Renders the Word document from `runbook.js` and the `*.json` cases |
| `build_xlsx.py` | Renders the Excel tracker from the same cases (Summary, Test Cases, Test Steps, Defect Log, Accounts) |

## Rebuild

```bash
cd docs/uat/source
npm install                                   # once: the docx package
python3 build_reg.py && python3 gen_prj.py && python3 gen_con.py \
  && python3 build_rgt.py && python3 build_ovs.py   # refresh the *.json cases
node build_docx.js ../COMPASS-CMP-UAT-Runbook-and-Test-Cases.docx
python3 build_xlsx.py ../COMPASS-CMP-UAT-Test-Cases.xlsx   # needs openpyxl
```

The workbook's formulas are recalculated by Excel when it opens it.

When the build under test changes, set `BUILD` in `runbook.js` and the
"Build under test" line in `build_xlsx.py` to the new commit, and update the
case count in [the docs map](../../README.md).
