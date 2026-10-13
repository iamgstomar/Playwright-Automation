"""
Rebuilds the Summary sheet dynamically from whatever sheets exist in the workbook.
- Detects Status column per sheet by reading header row 3
- Counts actual data rows (rows with a value in column 1, starting row 4)
- Adds/removes modules automatically when sheets are added or removed
Run anytime:  python tools/fix_summary.py
"""
import openpyxl
from openpyxl.utils import get_column_letter
import os
import sys
import time

RETRY_DELAY = 3
WRITE_RETRIES = 5

import yaml

_CFG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "config.yaml")
with open(_CFG_PATH) as f:
    _CFG = yaml.safe_load(f)

EXCEL_PATH = _CFG["reporting"]["excel_path"]
HEADER_ROW = 3
DATA_START  = 4


def _status_col_letter(ws):
    """Find the Status column letter by scanning header row 3."""
    for cell in ws[HEADER_ROW]:
        if cell.value and str(cell.value).strip().lower() == "status":
            return get_column_letter(cell.column)
    return None


def _safe_name(title):
    return f"'{title}'" if (" " in title or "-" in title) else title


def fix():
    wb = openpyxl.load_workbook(EXCEL_PATH)
    summary = wb["Summary"]

    # Collect all sheets except Summary, in workbook tab order
    module_sheets = [wb[s] for s in wb.sheetnames if s != "Summary"]

    # Clear old data rows
    for row in summary.iter_rows(min_row=DATA_START, max_row=summary.max_row):
        for cell in row:
            cell.value = None

    written = []
    for i, ws in enumerate(module_sheets, start=DATA_START):
        status_col = _status_col_letter(ws)
        if not status_col:
            print(f"  SKIP {ws.title} — no Status column found")
            continue

        safe      = _safe_name(ws.title)
        # Use open-ended range so formulas cover any future rows added to the sheet
        tc_rng    = f"{safe}!A{DATA_START}:A10000"
        st_rng    = f"{safe}!{status_col}{DATA_START}:{status_col}10000"

        summary.cell(row=i, column=1).value = ws.title
        summary.cell(row=i, column=2).value = f"=COUNTA({tc_rng})"
        summary.cell(row=i, column=3).value = f'=COUNTIF({st_rng},"Pass")'
        summary.cell(row=i, column=4).value = f'=COUNTIF({st_rng},"Fail")'
        summary.cell(row=i, column=5).value = f'=COUNTIF({st_rng},"Blocked")'
        summary.cell(row=i, column=6).value = f'=COUNTIF({st_rng},"Not Executed")'
        summary.cell(row=i, column=7).value = f"=IFERROR(C{i}/B{i},0)"
        written.append(ws.title)

    # TOTAL row
    last_data_row = DATA_START + len(written) - 1
    total_row     = last_data_row + 1
    summary.cell(row=total_row, column=1).value = "TOTAL"
    for col in range(2, 8):
        col_letter = get_column_letter(col)
        summary.cell(row=total_row, column=col).value = (
            f"=SUM({col_letter}{DATA_START}:{col_letter}{last_data_row})"
        )

    for attempt in range(1, WRITE_RETRIES + 1):
        try:
            wb.save(EXCEL_PATH)
            break
        except PermissionError:
            if attempt == WRITE_RETRIES:
                print(
                    f"ERROR: Cannot save {EXCEL_PATH}\n"
                    f"File is locked by SharePoint/OneDrive or open in Excel.\n"
                    f"Close it and re-run."
                )
                return
            print(f"  File locked, retrying in {RETRY_DELAY}s (attempt {attempt}/{WRITE_RETRIES})...")
            time.sleep(RETRY_DELAY)
    print(f"Summary rebuilt — {len(written)} modules, TOTAL at row {total_row}")
    for name in written:
        print(f"  {name}")


if __name__ == "__main__":
    fix()
