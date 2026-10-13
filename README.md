# QA Automation — Puffin Broadcast Platform

Automated tests that read their pass/fail criteria from your existing
`QA_Test_Cases.xlsx` and write the results straight back into it.

## 1. Where to fill in the environment details

Open **`config/config.yaml`** — this is the ONLY file you need to edit to get started:

```yaml
environment:
  base_url: "http://<YOUR-TEST-IP-OR-DOMAIN>:<PORT>"   # <-- put your test server here
  login_path: "/login"

credentials:
  username: "<TEST_USERNAME>"    # <-- your QA test account
  password: "<TEST_PASSWORD>"
  ad_test_username: "<AD_TEST_USERNAME>"

browser:
  headless: false   # keep this false at first so you can WATCH the browser run
```

Once your test environment is up, replace the `<...>` placeholders and save.

## 2. One-time setup

```bash
cd qa_automation
python3 -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install               # downloads the browser binaries
```

## 3. Run the tests

```bash
pytest -v                        # run everything
pytest -v tests/test_login.py    # run just one module's tests
pytest -v -k "credits"           # run tests matching a keyword
```

With `headless: false`, a real Chrome window will pop up and you'll watch it
click through the app — good for building confidence before automating fully.

## 4. Where results go

After each test run, results are written automatically back into
`QA_Test_Cases.xlsx`:
- **Status** column → Pass / Fail / Blocked
- **Actual Result** column → what happened (or the error message)
- **Tested By** → "Automation Bot"
- **Date Tested** → timestamp of the run

Open the Excel file afterward — the **Summary** sheet will recalculate
automatically and show your live Pass/Fail counts per module.

## 5. Naming convention (important)

Test function names must follow this pattern so results map to the right
Excel row:

```python
def test_TC_LOG_006_valid_login_redirects_to_dashboard():
    ...
```

`TC_LOG_006` → maps to Test Case ID `TC-LOG-006` in the Login sheet.
Just copy the Test Case ID from Excel, swap dashes for underscores, and
prefix with `test_`.

## 6. Adding / removing / editing test cases

This is the main point of the whole setup:

- **Add a feature to test** → add a row to the relevant sheet in
  `QA_Test_Cases.xlsx` (or ask me and I'll regenerate it), THEN write a
  matching `test_TC_XXX_###_...` function in the right `tests/test_*.py`
  file.
- **Remove a feature** → delete its row from Excel, and delete/skip the
  matching test function.
- **Modify expected behavior** → edit the "Expected Result" column in Excel,
  and update the `assert` in the matching test function to match.

The Excel sheet stays the single source of truth for *what* should be
tested; the `tests/` folder is *how* it gets tested.

## 7. Folder structure

```
qa_automation/
├── config/
│   └── config.yaml          <- fill in URL + credentials here
├── tests/
│   ├── conftest.py           <- shared login/browser setup + auto-writes results
│   └── test_login.py         <- example module (copy this pattern for others)
├── utils/
│   └── excel_writer.py       <- writes Pass/Fail back into the Excel file
├── requirements.txt
└── README.md
```

## 8. Expired / self-signed HTTPS certificate

If your test site's SSL certificate is expired or self-signed (the kind that
only "works" in incognito because your regular Chrome profile has cached a
security exception/HSTS policy), Playwright is already configured to ignore
certificate errors entirely (`ignore_https_errors=True` in `conftest.py` and
`test_login.py`). You don't need incognito mode or any browser flags — the
automated browser will connect regardless of the certificate warning.

## 9. Next modules to script

Once Login is working end-to-end, copy `test_login.py` as a template for:
- `test_credits.py` — Manage Push/SMS Credits (Add/Remove, balance math)
- `test_broadcast.py` — Broadcast Inbox/Push/SMS create + schedule flows
- `test_users_roles.py` — AD user validation + role permission checks
- `test_reports.py` — filters, export, empty states

I can write the actual test bodies for each once real selectors (element
IDs/classes from your app) are available — either send me the HTML/DOM, or
once the environment is live I can inspect it directly via a connected
browser tool.
