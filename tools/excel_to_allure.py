"""
excel_to_allure.py  —  QA_Test_Cases.xlsx  →  Allure result JSONs
Usage:
    python tools/excel_to_allure.py                     # Departments only
    python tools/excel_to_allure.py --sheet Login
    python tools/excel_to_allure.py --all               # every sheet
    python tools/excel_to_allure.py --all --label "Sprint 3"
"""
import os, json, uuid, argparse, datetime, openpyxl

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_PATH = os.path.join(ROOT, "QA_Test_Cases.xlsx")
OUT_DIR    = os.path.join(ROOT, "allure-results")
HEADER_ROW = 3
DATA_START = 4
MAX_TREND  = 10   # keep last N builds in trend

SHEET_META = {
    "Departments":          {"epic": "Puffin Broadcast Platform", "feature": "Dictionaries — Departments"},
    "SMS Broadcast":        {"epic": "Puffin Broadcast Platform", "feature": "Broadcast — SMS"},
    "Push Broadcast":       {"epic": "Puffin Broadcast Platform", "feature": "Broadcast — Push"},
    "Inbox Broadcast":      {"epic": "Puffin Broadcast Platform", "feature": "Broadcast — Inbox"},
    "MessageTemplate":      {"epic": "Puffin Broadcast Platform", "feature": "Message Templates"},
    "User Management":      {"epic": "Puffin Broadcast Platform", "feature": "User Management"},
    "CreditReports":        {"epic": "Puffin Broadcast Platform", "feature": "Credit Reports"},
    "Reports":              {"epic": "Puffin Broadcast Platform", "feature": "Reports"},
    "Credit Management":    {"epic": "Puffin Broadcast Platform", "feature": "Credit Management"},
    "Home-Header":          {"epic": "Puffin Broadcast Platform", "feature": "Home — Header"},
    "Login":                {"epic": "Puffin Broadcast Platform", "feature": "Login"},
    "General-CrossCutting": {"epic": "Puffin Broadcast Platform", "feature": "General / Cross-Cutting"},
}

STATUS_MAP = {
    "pass": "passed", "fail": "failed", "failed": "failed",
    "blocked": "broken", "not executed": "skipped",
    "skip": "skipped", "skipped": "skipped",
}

STORY_MAP = {
    "Departments": [
        (9,  "Add Department Form"),
        (57, "Search and Filter"),
        (64, "Table and UI Behaviour"),
        (67, "Security"),
    ],
    "Login": [
        (5,  "Valid Login"),
        (10, "Invalid Login"),
        (99, "Session & Security"),
    ],
}

def _story(tc_id: str, sheet: str) -> str:
    try:
        n = int(tc_id.split("-")[-1])
    except Exception:
        return "General"
    for limit, name in STORY_MAP.get(sheet, []):
        if n <= limit:
            return name
    return "General"

def _severity(tc_id: str) -> str:
    try:
        n = int(tc_id.split("-")[-1])
        if n <= 9:  return "critical"
        if n <= 30: return "normal"
        return "minor"
    except Exception:
        return "normal"

def _ts_ms(val) -> int:
    if val is None:
        return int(datetime.datetime.now().timestamp() * 1000)
    if isinstance(val, datetime.datetime):
        return int(val.timestamp() * 1000)
    try:
        return int(datetime.datetime.strptime(str(val).strip(), "%Y-%m-%d %H:%M").timestamp() * 1000)
    except Exception:
        return int(datetime.datetime.now().timestamp() * 1000)

def _col(headers, fragment):
    for i, h in enumerate(headers):
        if h and fragment.lower() in str(h).lower():
            return i
    return None

# ── Process one sheet ────────────────────────────────────────────────────────

def process_sheet(ws, sheet_name: str, out_dir: str) -> dict:
    meta    = SHEET_META.get(sheet_name, {"epic": "Puffin Broadcast Platform", "feature": sheet_name})
    epic    = meta["epic"]
    feature = meta["feature"]

    headers  = [c.value for c in ws[HEADER_ROW]]
    idx_id   = _col(headers, "test case id") or _col(headers, "id")
    idx_scen = _col(headers, "scenario")
    idx_exp  = _col(headers, "expected")
    idx_stat = _col(headers, "status")
    idx_act  = _col(headers, "actual")
    idx_by   = _col(headers, "tested by")
    idx_date = _col(headers, "date")

    counts = {"passed": 0, "failed": 0, "broken": 0, "skipped": 0, "total": 0}

    for row in ws.iter_rows(min_row=DATA_START, values_only=True):
        tc_id = row[idx_id] if idx_id is not None else None
        if not tc_id or not str(tc_id).strip().upper().startswith("TC"):
            continue

        tc_id      = str(tc_id).strip()
        scenario   = str(row[idx_scen]).strip()  if idx_scen is not None and row[idx_scen]  else tc_id
        expected   = str(row[idx_exp]).strip()   if idx_exp  is not None and row[idx_exp]   else ""
        status_raw = str(row[idx_stat]).strip().lower() if idx_stat is not None and row[idx_stat] else "not executed"
        actual     = str(row[idx_act]).strip()   if idx_act  is not None and row[idx_act]   else ""
        tested_by  = str(row[idx_by]).strip()    if idx_by   is not None and row[idx_by]    else "Automation Bot"
        date_val   = row[idx_date]               if idx_date is not None                    else None

        status   = STATUS_MAP.get(status_raw, "skipped")
        ts_stop  = _ts_ms(date_val)
        ts_start = ts_stop - 2000

        result = {
            "uuid":       str(uuid.uuid4()),
            "historyId":  tc_id,
            "testCaseId": tc_id,
            "fullName":   f"{feature} > {tc_id}",
            "name":       f"{tc_id}: {scenario}",
            "status":     status,
            "start":      ts_start,
            "stop":       ts_stop,
            "labels": [
                {"name": "epic",     "value": epic},
                {"name": "feature",  "value": feature},
                {"name": "story",    "value": _story(tc_id, sheet_name)},
                {"name": "severity", "value": _severity(tc_id)},
                {"name": "testType", "value": "automated"},
                {"name": "tag",      "value": sheet_name},
                {"name": "tag",      "value": tc_id},
                {"name": "owner",    "value": tested_by},
            ],
            "description": f"**Expected Result:**\n{expected}" if expected else "",
            "steps": [], "attachments": [], "parameters": [], "links": [],
        }

        if status in ("failed", "broken"):
            result["statusDetails"] = {"message": actual or "Test failed", "trace": ""}
        elif status == "skipped":
            result["statusDetails"] = {"message": actual or "Not executed", "trace": ""}

        with open(os.path.join(out_dir, f"{result['uuid']}-result.json"), "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)

        counts[status] = counts.get(status, 0) + 1
        counts["total"] += 1

    return counts

# ── History / Trend (accumulates across runs) ────────────────────────────────

def write_history(out_dir: str, all_counts: dict, label: str):
    hist_dir = os.path.join(out_dir, "history")
    os.makedirs(hist_dir, exist_ok=True)

    total   = sum(c.get("total",   0) for c in all_counts.values())
    passed  = sum(c.get("passed",  0) for c in all_counts.values())
    failed  = sum(c.get("failed",  0) for c in all_counts.values())
    broken  = sum(c.get("broken",  0) for c in all_counts.values())
    skipped = sum(c.get("skipped", 0) for c in all_counts.values())

    trend_path = os.path.join(hist_dir, "history-trend.json")

    # load existing trend so we ACCUMULATE runs
    existing = []
    if os.path.exists(trend_path):
        try:
            with open(trend_path, encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = []

    # next buildOrder = max existing + 1
    next_order = max((e.get("buildOrder", 0) for e in existing), default=0) + 1

    new_entry = {
        "buildOrder": next_order,
        "reportName": label or datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "reportUrl":  ".",
        "data": {
            "total":   total,
            "passed":  passed,
            "failed":  failed,
            "broken":  broken,
            "skipped": skipped,
            "unknown": 0,
        }
    }

    # keep last MAX_TREND entries (oldest first so chart reads left→right)
    trend = (existing + [new_entry])[-MAX_TREND:]

    with open(trend_path, "w", encoding="utf-8") as f:
        json.dump(trend, f, indent=2)

    # history.json — per-test pass/fail history (empty is fine, Allure fills it)
    hist_path = os.path.join(hist_dir, "history.json")
    if not os.path.exists(hist_path):
        with open(hist_path, "w", encoding="utf-8") as f:
            json.dump({}, f)

    return next_order

# ── Executor ─────────────────────────────────────────────────────────────────

def write_executor(out_dir: str, build_order: int, label: str):
    executor = {
        "name":       "Automation Bot",
        "type":       "local",
        "buildName":  label or datetime.datetime.now().strftime("Build %Y-%m-%d %H:%M"),
        "buildOrder": build_order,
        "reportName": "Puffin QA Report",
        "reportUrl":  ".",
    }
    with open(os.path.join(out_dir, "executor.json"), "w", encoding="utf-8") as f:
        json.dump(executor, f, indent=2)

# ── Environment ───────────────────────────────────────────────────────────────

def write_environment(out_dir: str, sheets: list):
    import yaml
    base_url = "N/A"
    browser  = "Chromium"
    try:
        with open(os.path.join(ROOT, "config", "config.yaml"), encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        base_url = cfg["environment"].get("base_url", "N/A")
        browser  = cfg.get("browser", {}).get("type", "chromium").capitalize()
    except Exception:
        pass

    lines = [
        "Application=Puffin Broadcast Platform",
        f"Base_URL={base_url}",
        f"Browser={browser}",
        f"Modules_Tested={', '.join(sheets)}",
        f"Report_Generated={datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "Results_Source=QA_Test_Cases.xlsx",
    ]
    with open(os.path.join(out_dir, "environment.properties"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# ── Categories ────────────────────────────────────────────────────────────────

def write_categories(out_dir: str):
    cats = [
        {"name": "Failed Tests",          "matchedStatuses": ["failed"]},
        {"name": "Blocked / Broken",       "matchedStatuses": ["broken"]},
        {"name": "Skipped / Not Executed", "matchedStatuses": ["skipped"]},
    ]
    with open(os.path.join(out_dir, "categories.json"), "w", encoding="utf-8") as f:
        json.dump(cats, f, indent=2)

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sheet",  default="Departments", help="Single sheet name")
    parser.add_argument("--all",    action="store_true",   help="All sheets")
    parser.add_argument("--label",  default="",            help="Build label shown in Trend (e.g. 'Sprint 3')")
    args = parser.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    # remove old result files only — keep history dir intact
    for fname in os.listdir(OUT_DIR):
        if fname.endswith("-result.json"):
            os.remove(os.path.join(OUT_DIR, fname))

    wb = openpyxl.load_workbook(EXCEL_PATH)
    sheets = [s for s in wb.sheetnames if s != "Summary"] if args.all else [args.sheet]

    processed, all_counts = [], {}
    for name in sheets:
        if name not in wb.sheetnames:
            print(f"  WARNING: '{name}' not found — skipping")
            continue
        counts = process_sheet(wb[name], name, OUT_DIR)
        all_counts[name] = counts
        processed.append(name)
        p, f, b, s = counts["passed"], counts["failed"], counts["broken"], counts["skipped"]
        print(f"  [{name}]  total={counts['total']}  pass={p}  fail={f}  blocked={b}  skip={s}")

    label      = args.label or (", ".join(processed) + " — " + datetime.datetime.now().strftime("%Y-%m-%d"))
    build_order = write_history(OUT_DIR, all_counts, label)
    write_executor(OUT_DIR, build_order, label)
    write_environment(OUT_DIR, processed)
    write_categories(OUT_DIR)

    print(f"\n  Build #{build_order} written to: {OUT_DIR}")
    print(f"  Next steps:")
    print(f'    allure\\allure-2.30.0\\bin\\allure.bat generate allure-results --clean -o allure-report')
    print(f'    python tools/apply_dark_theme.py')
    print(f'    allure\\allure-2.30.0\\bin\\allure.bat open allure-report --port 5050')

if __name__ == "__main__":
    main()
