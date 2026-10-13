"""
Inspect the live departments page DOM and write results to a file.
Run: python tools/inspect_dept_page.py
"""
from playwright.sync_api import sync_playwright
import yaml, os

cfg      = yaml.safe_load(open(r'D:\Documents\Learning\MyApps\KUAutomation\config\config.yaml', encoding='utf-8'))
LOGIN    = cfg['environment']['login_url']
DEPT     = 'https://twowayserver.future-club.com/dictionary/department'
USER     = cfg['credentials']['username']
PASS     = cfg['credentials']['password']
OUT      = r'D:\Documents\Learning\MyApps\KUAutomation\screenshots\OLD\dept_dom.txt'

lines = []
def log(s): lines.append(str(s))

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False, slow_mo=100)
    ctx  = browser.new_context(ignore_https_errors=True)
    page = ctx.new_page()

    # ── login ──────────────────────────────────────────────────────────────
    page.goto(LOGIN, wait_until='domcontentloaded', timeout=30000)
    page.wait_for_timeout(3000)
    u = page.locator("input[name='username']").first
    u.click()
    page.evaluate("""([el, val]) => {
        const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        s.call(el, val);
        ['input','change'].forEach(e => el.dispatchEvent(new Event(e, {bubbles:true})));
    }""", [u.element_handle(), USER])
    pw = page.locator("input[name='password']").first
    pw.click()
    page.evaluate("""([el, val]) => {
        const s = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
        s.call(el, val);
        ['input','change'].forEach(e => el.dispatchEvent(new Event(e, {bubbles:true})));
    }""", [pw.element_handle(), PASS])
    page.wait_for_timeout(800)
    page.locator("button[type='submit']").click()
    try:
        page.wait_for_url(lambda url: '/login' not in url.lower(), timeout=20000)
    except Exception:
        pass
    page.wait_for_load_state('networkidle', timeout=15000)
    log(f'AFTER_LOGIN: {page.url}')

    if '/login' in page.url.lower():
        log('LOGIN FAILED')
        open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
        browser.close()
        exit()

    # ── navigate to departments ────────────────────────────────────────────
    page.goto(DEPT, wait_until='domcontentloaded', timeout=30000)
    page.wait_for_load_state('networkidle', timeout=15000)
    page.wait_for_timeout(2000)
    log(f'DEPT_URL: {page.url}')

    # ── buttons ───────────────────────────────────────────────────────────
    btns = page.locator('button')
    log(f'\n=== BUTTONS ({btns.count()}) ===')
    for i in range(min(btns.count(), 50)):
        b = btns.nth(i)
        log(f'  [{i}] text={repr(b.inner_text()[:80])} '
            f'cy={repr(b.get_attribute("data-cy") or "")} '
            f'testid={repr(b.get_attribute("data-testid") or "")} '
            f'aria={repr(b.get_attribute("aria-label") or "")} '
            f'title={repr(b.get_attribute("title") or "")} '
            f'class={repr((b.get_attribute("class") or "")[:80])}')

    # ── inputs ────────────────────────────────────────────────────────────
    inputs = page.locator('input')
    log(f'\n=== INPUTS ({inputs.count()}) ===')
    for i in range(min(inputs.count(), 30)):
        el = inputs.nth(i)
        log(f'  [{i}] name={repr(el.get_attribute("name") or "")} '
            f'id={repr(el.get_attribute("id") or "")} '
            f'type={repr(el.get_attribute("type") or "")} '
            f'placeholder={repr(el.get_attribute("placeholder") or "")} '
            f'cy={repr(el.get_attribute("data-cy") or "")} '
            f'testid={repr(el.get_attribute("data-testid") or "")} '
            f'class={repr((el.get_attribute("class") or "")[:80])}')

    # ── selects ───────────────────────────────────────────────────────────
    selects = page.locator('select')
    log(f'\n=== SELECTS ({selects.count()}) ===')
    for i in range(min(selects.count(), 10)):
        el = selects.nth(i)
        opts = el.locator('option').all_inner_texts()
        log(f'  [{i}] name={repr(el.get_attribute("name") or "")} '
            f'class={repr((el.get_attribute("class") or "")[:60])} '
            f'options={opts[:10]}')

    # ── table headers ─────────────────────────────────────────────────────
    ths = page.locator('th, [role="columnheader"]')
    log(f'\n=== HEADERS ({ths.count()}) ===')
    for i in range(min(ths.count(), 20)):
        el = ths.nth(i)
        log(f'  [{i}] text={repr(el.inner_text()[:60])} '
            f'class={repr((el.get_attribute("class") or "")[:80])}')

    # ── all [data-cy] elements ────────────────────────────────────────────
    cy_els = page.locator('[data-cy]')
    log(f'\n=== DATA-CY ELEMENTS ({cy_els.count()}) ===')
    for i in range(min(cy_els.count(), 40)):
        el = cy_els.nth(i)
        log(f'  [{i}] tag={el.evaluate("e=>e.tagName")} '
            f'cy={repr(el.get_attribute("data-cy"))} '
            f'text={repr(el.inner_text()[:60])}')

    # ── all [data-testid] elements ────────────────────────────────────────
    tid_els = page.locator('[data-testid]')
    log(f'\n=== DATA-TESTID ELEMENTS ({tid_els.count()}) ===')
    for i in range(min(tid_els.count(), 40)):
        el = tid_els.nth(i)
        log(f'  [{i}] tag={el.evaluate("e=>e.tagName")} '
            f'testid={repr(el.get_attribute("data-testid"))} '
            f'text={repr(el.inner_text()[:60])}')

    # ── validation error inspection ───────────────────────────────────────
    # Open form, type 2 chars in Value field, submit, capture error DOM
    try:
        close_btn = page.locator("button[aria-label='Close modal']").first
        if close_btn.count() > 0 and close_btn.is_visible(timeout=1000):
            close_btn.click()
            page.wait_for_timeout(400)
    except Exception:
        pass
    page.locator("button[data-cy='open-modal-button']").click()
    page.locator("input[name='departmentValue']").wait_for(timeout=8000)
    page.locator("input[name='departmentValue']").fill("li")
    page.locator("button.button_form-submit_main").click()
    page.wait_for_timeout(800)
    log(f'\n=== VALIDATION ERROR DOM (after submitting 2-char value) ===')
    # dump all elements that contain the error text
    all_els = page.locator("*").all()
    for el in all_els:
        try:
            txt = el.inner_text(timeout=200).strip()
            if "minimum" in txt.lower() or "length" in txt.lower() or "3 char" in txt.lower():
                log(f'  tag={el.evaluate("e=>e.tagName")} '
                    f'class={repr((el.get_attribute("class") or "")[:80])} '
                    f'text={repr(txt[:100])}')
        except Exception:
            pass

    # ── language switcher — close modal first, then inspect header area ───
    # close modal if open
    try:
        close_btn = page.locator("button[aria-label='Close modal']").first
        if close_btn.count() > 0 and close_btn.is_visible(timeout=1000):
            close_btn.click()
            page.wait_for_timeout(500)
    except Exception:
        pass

    log(f'\n=== LANGUAGE SWITCHER CANDIDATES ===')
    lang_selectors = [
        "[class*='lang']", "[class*='language']", "[class*='locale']",
        "[aria-label*='language' i]", "[aria-label*='lang' i]",
        "[data-cy*='lang']", "[data-testid*='lang']",
        "button:has-text('EN')", "button:has-text('AR')",
        "[class*='switch']", "[class*='toggle']",
        "header button", "nav button", ".navbar button", ".header button",
    ]
    found_lang = set()
    for sel in lang_selectors:
        try:
            els = page.locator(sel)
            for i in range(min(els.count(), 5)):
                el = els.nth(i)
                uid = el.evaluate("e => e.outerHTML")[:120]
                if uid not in found_lang:
                    found_lang.add(uid)
                    log(f'  sel={repr(sel)} tag={el.evaluate("e=>e.tagName")} '
                        f'text={repr(el.inner_text()[:60])} '
                        f'class={repr((el.get_attribute("class") or "")[:80])} '
                        f'aria={repr(el.get_attribute("aria-label") or "")} '
                        f'cy={repr(el.get_attribute("data-cy") or "")} '
                        f'visible={el.is_visible()}')
        except Exception as e:
            log(f'  sel={repr(sel)} ERROR: {e}')

    # also dump full header/navbar HTML for manual inspection
    log(f'\n=== HEADER/NAV HTML ===')
    for nav_sel in ['header', 'nav', '.navbar', '.app-header', '.top-bar', '[class*="header"]', '[class*="navbar"]']:
        try:
            el = page.locator(nav_sel).first
            if el.count() > 0:
                html = el.evaluate("e => e.outerHTML")[:2000]
                log(f'  [{nav_sel}]: {html}')
        except Exception:
            pass

    browser.close()

open(OUT, 'w', encoding='utf-8').write('\n'.join(lines))
print(f'Written to {OUT}')
