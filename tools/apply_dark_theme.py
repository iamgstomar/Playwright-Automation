"""
apply_dark_theme.py
-------------------
Injects a dark theme into allure-report/index.html.
Run AFTER allure generate, BEFORE allure open.

    python tools/apply_dark_theme.py
"""
import os, re

ROOT       = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INDEX_HTML = os.path.join(ROOT, "allure-report", "index.html")

# Surgical dark theme — does NOT override Allure's own status/severity colors
DARK_CSS = """<style id="dark-theme-override">
  /* ── Base ── */
  html, body { background: #0d0d0d !important; color: #d4d4d4 !important; }

  /* ── Sidebar ── */
  .side-nav { background: #161616 !important; border-right: 1px solid #2a2a2a !important; }
  .side-nav__item > a,
  .side-nav__item > span { color: #a0a0a0 !important; }
  .side-nav__item.active > a,
  .side-nav__item.active > span { color: #ffffff !important; background: #1f1f1f !important; }
  .side-nav__item > a:hover { color: #ffffff !important; background: #1a1a1a !important; }
  .side-nav__collapse { color: #666 !important; border-top: 1px solid #2a2a2a !important; }

  /* ── App header / toolbar ── */
  .app__header { background: #161616 !important; border-bottom: 1px solid #2a2a2a !important; }
  .app__header .app__title { color: #ffffff !important; }

  /* ── All widget / card containers ── */
  .widget,
  .widget__body,
  .card,
  .card__body { background: #161616 !important; border: 1px solid #2a2a2a !important; }

  /* ── Widget titles ── */
  .widget__title { color: #ffffff !important; border-bottom: 1px solid #2a2a2a !important; }
  .widget__title .widget__title-text { color: #ffffff !important; }
  .widget__title .widget__title-counter { color: #888 !important; }

  /* ── "Nothing to show" empty states ── */
  .widget__empty-message,
  .empty-message { color: #555 !important; }

  /* ── Summary numbers (big 69 on overview) ── */
  .summary__total { color: #ffffff !important; }
  .summary__total-label { color: #888 !important; }

  /* ── Trend / chart containers ── */
  .trend { background: #161616 !important; }
  .highcharts-background { fill: #161616 !important; }
  .highcharts-plot-background { fill: #161616 !important; }
  .highcharts-title text,
  .highcharts-axis-labels text,
  .highcharts-legend-item text { fill: #d4d4d4 !important; color: #d4d4d4 !important; }
  .highcharts-grid-line { stroke: #2a2a2a !important; }
  .highcharts-axis-line { stroke: #444 !important; }

  /* ── Environment table ── */
  .environment-table { background: #161616 !important; }
  .environment-table__row { border-bottom: 1px solid #2a2a2a !important; }
  .environment-table__key { color: #a0a0a0 !important; }
  .environment-table__value { color: #ffffff !important; }

  /* ── Generic tables (Suites, Behaviors, etc.) ── */
  .table { background: #161616 !important; }
  .table__head { background: #1e1e1e !important; border-bottom: 1px solid #333 !important; }
  .table__head .table__cell { color: #a0a0a0 !important; }
  .table__row { border-bottom: 1px solid #222 !important; }
  .table__row:hover { background: #1e1e1e !important; }
  .table__cell { color: #d4d4d4 !important; }

  /* ── Test name links ── */
  .test-result__title,
  .test-result__title a { color: #7eb8f7 !important; }
  .test-result__title a:hover { color: #aad4ff !important; }

  /* ── Test detail pane ── */
  .pane,
  .pane__body,
  .split-pane { background: #111 !important; }
  .test-result { background: #161616 !important; }
  .test-result__overview { background: #161616 !important; }
  .test-result__description { color: #c0c0c0 !important; }

  /* ── Steps ── */
  .step { background: #1a1a1a !important; border-left: 2px solid #333 !important; }
  .step__title { color: #d4d4d4 !important; }
  .step__title:hover { background: #222 !important; }

  /* ── Tags / labels (non-status) ── */
  .label { background: #252525 !important; color: #a0a0a0 !important; }

  /* ── Severity labels — keep Allure's own colors, just fix background ── */
  .label_severity_blocker  { background: #3a1a1a !important; }
  .label_severity_critical { background: #3a1a1a !important; }
  .label_severity_normal   { background: #1a2a3a !important; }
  .label_severity_minor    { background: #1e1e1e !important; }
  .label_severity_trivial  { background: #1e1e1e !important; }

  /* ── Status colors — keep Allure's own text colors, fix backgrounds ── */
  .label_status_passed  { background: #0d2b0d !important; }
  .label_status_failed  { background: #2b0d0d !important; }
  .label_status_broken  { background: #2b1e0d !important; }
  .label_status_skipped { background: #1e1e1e !important; }
  .label_status_unknown { background: #1e1e1e !important; }

  /* ── Progress bars — keep green for passed ── */
  .progress-bar__chunk_status_passed  { background: #4caf50 !important; }
  .progress-bar__chunk_status_failed  { background: #f44336 !important; }
  .label_status_broken  { background: #ff9800 !important; }
  .progress-bar__chunk_status_skipped { background: #607d8b !important; }

  /* ── Inputs / search ── */
  input, select, textarea {
    background: #1e1e1e !important;
    color: #d4d4d4 !important;
    border: 1px solid #333 !important;
  }
  input::placeholder { color: #555 !important; }

  /* ── Scrollbar ── */
  ::-webkit-scrollbar { width: 6px; height: 6px; }
  ::-webkit-scrollbar-track { background: #0d0d0d; }
  ::-webkit-scrollbar-thumb { background: #333; border-radius: 3px; }
  ::-webkit-scrollbar-thumb:hover { background: #555; }

  /* ── Tooltip ── */
  .tooltip { background: #222 !important; color: #d4d4d4 !important; border: 1px solid #444 !important; }

  /* ── Dropdown / popup ── */
  .dropdown__menu,
  .popup { background: #1e1e1e !important; border: 1px solid #333 !important; }
  .dropdown__item:hover { background: #252525 !important; }
  .dropdown__item { color: #d4d4d4 !important; }
</style>"""

def apply():
    if not os.path.exists(INDEX_HTML):
        print(f"  ERROR: {INDEX_HTML} not found — run allure generate first")
        return

    with open(INDEX_HTML, "r", encoding="utf-8") as f:
        html = f.read()

    # remove any previously injected block
    html = re.sub(r'\s*<style id="dark-theme-override">.*?</style>', "", html, flags=re.DOTALL)

    # inject just before </head>
    html = html.replace("</head>", f"\n    {DARK_CSS}\n</head>", 1)

    with open(INDEX_HTML, "w", encoding="utf-8") as f:
        f.write(html)

    print("  Dark theme applied to allure-report/index.html")

if __name__ == "__main__":
    apply()
