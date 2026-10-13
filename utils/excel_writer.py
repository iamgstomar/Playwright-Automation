"""
Writes automated test results back into QA_Test_Cases.xlsx.

Key facts about the real workbook:
  - Header row is row 3 on every sheet
  - Data starts at row 4
  - Status, Actual Result, Tested By, Date Tested columns are auto-detected
    from the header row (column positions differ between sheets)
  - TC-BC-XXX IDs appear in THREE sheets (Inbox Broadcast, Push Broadcast,
    SMS Broadcast) — the sheet is chosen by the TC ID numeric range:
      001-022  -> Inbox Broadcast
      023-042  -> Push Broadcast  (stored as TC-BC-01..20 in Excel)
      043-062  -> SMS Broadcast   (stored as TC-BC-01..20 in Excel)
  - TC-DIC-XXX IDs appear in TWO sheets (Departments, MessageTemplate):
      001-025  -> Departments
      012-029  -> MessageTemplate  (overlap — Departments takes priority for 012-025)
"""
import datetime
import time
import os
import openpyxl

WRITE_RETRIES = 5
RETRY_DELAY   = 3  # seconds between retries when file is locked

FILE_NAME = "QA_Test_Cases.xlsx"

# OneDrive/SharePoint folder name patterns to prefer (in priority order)
_ONEDRIVE_PATTERNS = [
    "OneDrive - ",
    "OneDrive",
    "SharePoint",
]


def resolve_excel_path(config_path: str) -> str:
    """
    Return config_path as-is if it exists (absolute path from config.yaml).
    Falls back to scanning OneDrive folders if the config path does not exist.
    """
    if os.path.isfile(config_path):
        return os.path.abspath(config_path)
    # Fallback: scan home for OneDrive/SharePoint copy
    home = os.path.expanduser("~")
    for entry in os.scandir(home):
        if not entry.is_dir():
            continue
        for pattern in _ONEDRIVE_PATTERNS:
            if pattern.lower() in entry.name.lower():
                candidate = os.path.join(entry.path, FILE_NAME)
                if os.path.isfile(candidate):
                    return candidate
    return os.path.abspath(config_path)

# Maps a TC ID prefix to the ordered list of sheets to search.
# First match wins — order matters for overlapping ranges.
SHEET_SEARCH_ORDER = {
    "TC-LOG": ["Login"],
    "TC-BC":  ["Inbox Broadcast", "Push Broadcast", "SMS Broadcast"],
    "TC-DIC": ["Departments", "MessageTemplate"],
    "TC-CM":  ["Credit Management"],
    "TC-CR":  ["CreditReports"],
    "TC-UM":  ["User Management"],
    "TC-RPT": ["Reports"],
    "TC-HDR": ["Home-Header"],
    "TC-GEN": ["General-CrossCutting"],
}

# Broadcast sheets store IDs without leading zeros (TC-BC-01 not TC-BC-001).
# This maps the full test-function ID to the Excel-stored ID for those sheets.
def _excel_id(sheet_title: str, tc_id: str) -> str:
    """Return the TC ID as it is stored in the given sheet."""
    if sheet_title in ("Push Broadcast", "SMS Broadcast"):
        # These sheets use TC-BC-01 format (no leading zero on single digit,
        # two-digit number). Convert TC-BC-043 -> TC-BC-04, TC-BC-023 -> TC-BC-01
        parts = tc_id.split("-")          # ['TC', 'BC', '043']
        num = int(parts[2])               # 43
        if sheet_title == "Push Broadcast":
            num = num - 22                # 023->1, 024->2 ... 042->20
        else:
            num = num - 42                # 043->1, 044->2 ... 062->20
        return f"TC-BC-{num:02d}"
    return tc_id


def _detect_columns(sheet, header_row=3):
    """Detect 1-based column indexes by scanning the header row."""
    candidates = {
        "tc_id":      ["test case id", "tc id"],
        "status":     ["status"],
        "actual":     ["actual result"],
        "tested_by":  ["tested by"],
        "date_tested":["date tested"],
        "remarks":    ["remarks"],
    }
    try:
        headers = [
            str(c.value).strip().lower() if c.value else ""
            for c in sheet[header_row]
        ]
    except Exception:
        headers = []

    result = {}
    for key, opts in candidates.items():
        for i, h in enumerate(headers, start=1):
            if any(opt in h for opt in opts):
                result[key] = i
                break

    return {
        "tc_id":       result.get("tc_id", 1),
        "status":      result.get("status", 7),
        "actual":      result.get("actual", 8),
        "tested_by":   result.get("tested_by", 9),
        "date_tested": result.get("date_tested", 10),
        "remarks":     result.get("remarks", 11),
    }


def _get_prefix(tc_id: str) -> str:
    """Extract prefix e.g. 'TC-LOG' from 'TC-LOG-006'."""
    parts = tc_id.split("-")
    return "-".join(parts[:2]) if len(parts) >= 2 else tc_id


def write_result(excel_path: str, tc_id: str, status: str,
                 actual_result: str = "", tested_by: str = "Automation Bot",
                 remarks: str = "") -> bool:
    """
    Write Pass/Fail/Blocked/Not Executed to the correct row and sheet.
    Returns True if the row was found and updated, False otherwise.
    """
    excel_path = resolve_excel_path(excel_path)
    wb = openpyxl.load_workbook(excel_path)
    prefix = _get_prefix(tc_id)
    sheets_to_search = SHEET_SEARCH_ORDER.get(prefix)

    # Fall back to searching all sheets if prefix not in map
    if not sheets_to_search:
        sheets_to_search = [s.title for s in wb.worksheets if s.title != "Summary"]

    for sheet_title in sheets_to_search:
        if sheet_title not in wb.sheetnames:
            continue
        ws = wb[sheet_title]
        cols = _detect_columns(ws)
        lookup_id = _excel_id(sheet_title, tc_id)

        for r in range(4, ws.max_row + 1):
            if ws.cell(row=r, column=cols["tc_id"]).value == lookup_id:
                ws.cell(row=r, column=cols["status"]).value = status
                ws.cell(row=r, column=cols["actual"]).value = actual_result
                ws.cell(row=r, column=cols["tested_by"]).value = tested_by
                ws.cell(row=r, column=cols["date_tested"]).value = \
                    datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                if remarks:
                    ws.cell(row=r, column=cols["remarks"]).value = remarks
                _save_with_retry(wb, excel_path)
                return True

    return False


def _save_with_retry(wb, excel_path: str):
    """Retry save to handle SharePoint/OneDrive file lock."""
    for attempt in range(1, WRITE_RETRIES + 1):
        try:
            wb.save(excel_path)
            return
        except PermissionError:
            if attempt == WRITE_RETRIES:
                raise PermissionError(
                    f"Cannot write to {excel_path} — file is locked by SharePoint/OneDrive.\n"
                    f"Close the file in Excel/browser and ensure OneDrive has finished syncing."
                )
            print(f"  [excel_writer] File locked, retrying in {RETRY_DELAY}s "
                  f"(attempt {attempt}/{WRITE_RETRIES})...")
            time.sleep(RETRY_DELAY)
