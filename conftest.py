"""
Root conftest.py — shared fixtures and hooks for all test modules.

Run modes
---------
All tests:
    pytest -v

By module:
    pytest -v -m departments
    pytest -v -m login

Specific test cases:
    pytest -v -k "TC_DIC_002"
    pytest -v -k "TC_DIC_002 or TC_DIC_020"
"""
import os
import re
import sys
import time
from urllib.parse import urlsplit, urlunsplit

import yaml
import pytest
import allure
from playwright.sync_api import sync_playwright, Page, expect

ROOT = os.path.dirname(__file__)
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "utils"))
sys.path.insert(0, os.path.join(ROOT, "tools"))

CONFIG_PATH    = os.path.join(ROOT, "config", "config.yaml")
TEST_DATA_PATH = os.path.join(ROOT, "config", "test_data.yaml")

with open(CONFIG_PATH) as f:
    _CFG = yaml.safe_load(f)
with open(TEST_DATA_PATH) as f:
    _TEST_DATA = yaml.safe_load(f)

EXCEL_PATH     = _CFG["reporting"]["excel_path"]
SCREENSHOT_DIR = _CFG["reporting"]["screenshot_dir"]
SCREENSHOT_ON  = _CFG["reporting"]["screenshot_on_failure"]
VIDEO_ON       = _CFG["reporting"].get("video_on_failure", False)

# ── URL helpers ───────────────────────────────────────────────────────────────

def _normalize_base_url(base_url: str, app_path: str = "") -> str:
    if not base_url:
        return ""
    parsed = urlsplit(base_url.strip())
    base_path = (parsed.path or "").rstrip("/")
    app = (app_path or "").strip()
    if app and app not in ("/", ""):
        app_path_norm = "/" + app.strip("/")
        if not base_path:
            base_path = app_path_norm
        elif not base_path.lower().endswith(app_path_norm.lower()):
            base_path = f"{base_path}{app_path_norm}"
    return urlunsplit((parsed.scheme, parsed.netloc, base_path or "", parsed.query, parsed.fragment))


def _candidate_login_urls(base_url: str, app_path: str = "", login_path: str = "") -> list:
    if not base_url:
        return []
    domain = base_url.rstrip("/")
    app    = (app_path or "").strip().strip("/")
    login  = (login_path or "login").strip().strip("/")
    roots  = [domain]
    if app:
        roots.append(f"{domain}/{app}")
    for suffix in ["/PuffinUI", "/puffinui", "/Puffin", "/puffin", "/App", "/app", "/UI", "/ui"]:
        roots.append(f"{domain}{suffix}")

    seen, urls = set(), []
    for root in roots:
        for path in [login, "login", "Login", "signin", "SignIn"]:
            url = f"{root}/{path}"
            if url not in seen:
                seen.add(url)
                urls.append(url)
        if root not in seen:
            seen.add(root)
            urls.append(root)
    return urls


# ── Login page detection ──────────────────────────────────────────────────────

_USER_KEYS = ["user", "email", "login", "member", "username"]
_PASS_KEYS = ["pass", "pwd", "password"]


def _input_tokens(page: Page) -> list:
    tokens = []
    try:
        inputs = page.locator("input")
        for i in range(min(inputs.count(), 30)):
            el = inputs.nth(i)
            token = " ".join(filter(None, [
                el.get_attribute("name") or "",
                el.get_attribute("id") or "",
                el.get_attribute("placeholder") or "",
                el.get_attribute("type") or "",
                el.get_attribute("autocomplete") or "",
                el.get_attribute("aria-label") or "",
            ])).lower()
            tokens.append(token)
    except Exception:
        pass
    return tokens


def _looks_like_login_page(page: Page) -> bool:
    try:
        tokens = _input_tokens(page)
        if len(tokens) < 2:
            return False
        has_user = any(any(k in t for k in _USER_KEYS) for t in tokens)
        has_pass = any(any(k in t for k in _PASS_KEYS) for t in tokens)
        return has_user and has_pass
    except Exception:
        return False


def _detect_login_url(page: Page, config) -> str:
    env = config["environment"]
    explicit = (env.get("login_url") or "").strip()
    if explicit.startswith("http"):
        return explicit

    base      = env.get("base_url", "")
    app       = env.get("app_path", "")
    login_path = env.get("login_path", "/login")
    timeout   = int(config.get("browser", {}).get("timeout", 15000))

    for url in _candidate_login_urls(base, app, login_path):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=timeout)
            page.wait_for_load_state("networkidle", timeout=min(timeout, 8000))
        except Exception:
            continue
        if _looks_like_login_page(page):
            return page.url

    return _normalize_base_url(base, app)


# ── Field finder ──────────────────────────────────────────────────────────────

def _find_field(page: Page, keys: list):
    """
    Find an input field dynamically by checking every possible attribute
    (name, id, placeholder, autocomplete, aria-label, type) against a list
    of keyword hints. Falls back to positional index for password fields.
    """
    inputs = page.locator("input:visible")
    count  = inputs.count()

    # Pass 1 — attribute keyword match
    for i in range(count):
        el = inputs.nth(i)
        attrs = " ".join(filter(None, [
            el.get_attribute("name") or "",
            el.get_attribute("id") or "",
            el.get_attribute("placeholder") or "",
            el.get_attribute("autocomplete") or "",
            el.get_attribute("aria-label") or "",
            el.get_attribute("type") or "",
            el.get_attribute("data-testid") or "",
            el.get_attribute("class") or "",
        ])).lower()
        if any(k in attrs for k in keys):
            return el

    # Pass 2 — type attribute only (catches type="password" / type="email")
    for i in range(count):
        el = inputs.nth(i)
        t  = (el.get_attribute("type") or "").lower()
        if keys == _PASS_KEYS and t == "password":
            return el
        if keys == _USER_KEYS and t in ("text", "email"):
            return el

    # Pass 3 — positional fallback (first visible non-hidden input = username,
    #           second = password)
    visible = [inputs.nth(i) for i in range(count)
               if (inputs.nth(i).get_attribute("type") or "").lower() != "hidden"]
    if keys == _USER_KEYS and visible:
        return visible[0]
    if keys == _PASS_KEYS and len(visible) >= 2:
        return visible[1]

    return None


# ── Field filler (React/Vue/Angular safe) ─────────────────────────────────────

def _fill_field(page: Page, el, value: str) -> None:
    """
    Fill a field in a way that fires all JS framework events:
    focus → select-all → type char-by-char → blur.
    Falls back to JS value injection + dispatchEvent if typing fails.
    """
    try:
        el.scroll_into_view_if_needed()
        el.click()
        el.select_text()
    except Exception:
        pass

    try:
        el.fill("")          # clear first
        el.type(value, delay=40)
        # Verify the value actually landed
        actual = el.input_value()
        if actual == value:
            return
    except Exception:
        pass

    # JS fallback — sets value and fires React synthetic + native events
    page.evaluate(
        """([el, val]) => {
            const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
                window.HTMLInputElement.prototype, 'value').set;
            nativeInputValueSetter.call(el, val);
            ['input', 'change', 'blur'].forEach(evt =>
                el.dispatchEvent(new Event(evt, { bubbles: true }))
            );
        }""",
        [el.element_handle(), value],
    )


# ── Submit helper ─────────────────────────────────────────────────────────────

def _submit_login(page: Page, password_field, timeout: int) -> None:
    """
    Try every possible way to submit the login form, in order of preference.
    """
    submit_selectors = [
        "button[type='submit']",
        "input[type='submit']",
        "button:has-text('Login')",
        "button:has-text('Log In')",
        "button:has-text('Sign in')",
        "button:has-text('Sign In')",
        "button:has-text('Submit')",
        "button:has-text('Continue')",
        "[role='button']:has-text('Login')",
        "[role='button']:has-text('Sign in')",
    ]

    for sel in submit_selectors:
        try:
            btn = page.locator(sel).first
            if btn.count() > 0 and btn.is_visible(timeout=2000):
                # Wait for it to be enabled (React may keep it disabled until fields are valid)
                try:
                    expect(btn).to_be_enabled(timeout=5000)
                except Exception:
                    pass
                btn.click()
                return
        except Exception:
            continue

    # Fallback 1 — press Enter on the password field
    if password_field is not None:
        try:
            password_field.press("Enter")
            return
        except Exception:
            pass

    # Fallback 2 — submit the form via JS
    try:
        page.evaluate(
            "() => { const f = document.querySelector('form'); "
            "if (f) f.requestSubmit ? f.requestSubmit() : f.submit(); }"
        )
    except Exception:
        pass


# ── Session guard — re-login if session expired ──────────────────────────────

def ensure_logged_in(pg: Page, config) -> None:
    """Call after every page.goto() — silently re-logs in if the session expired."""
    if "/login" in pg.url.lower() and _looks_like_login_page(pg):
        print("\n  [SESSION] Expired — re-logging in...")
        _do_login(pg, config)


# ── Core login flow ───────────────────────────────────────────────────────────

def _do_login(pg: Page, config) -> None:
    """
    Fully dynamic login:
      1. Navigate to the login page (auto-detected).
      2. Wait for the SPA to render the real form.
      3. Find username + password fields by any attribute.
      4. Fill them in a framework-safe way.
      5. Submit via the most reliable method available.
      6. Wait for the URL to leave /login.
      7. Raise a clear error if login still failed.
    """
    timeout = int(config["browser"]["timeout"])
    dbg_dir = os.path.join(SCREENSHOT_DIR, "debug")
    os.makedirs(dbg_dir, exist_ok=True)

    # ── 1. Navigate ──────────────────────────────────────────────────────────
    login_url = _detect_login_url(pg, config)
    pg.goto(login_url, wait_until="domcontentloaded", timeout=timeout)

    # ── 2. Wait for the real form (SPA shell → actual inputs) ────────────────
    try:
        pg.wait_for_function(
            """() => {
                const inputs = [...document.querySelectorAll('input:not([type="hidden"])')];
                const tokens = inputs.map(el =>
                    (el.name + ' ' + el.id + ' ' + el.placeholder +
                     ' ' + el.type + ' ' + (el.getAttribute('autocomplete') || '')).toLowerCase()
                );
                const hasUser = tokens.some(t =>
                    ['user','email','login','member','username'].some(k => t.includes(k)));
                const hasPass = tokens.some(t =>
                    ['pass','pwd','password'].some(k => t.includes(k)));
                return hasUser && hasPass;
            }""",
            timeout=timeout,
        )
    except Exception:
        # If the wait times out, try anyway — maybe the form is already there
        pass

    pg.wait_for_load_state("networkidle", timeout=min(timeout, 10000))
    pg.screenshot(path=os.path.join(dbg_dir, "1_login_page.png"), full_page=True)
    print(f"\n  [LOGIN] URL      : {pg.url}")
    print(f"  [LOGIN] Title    : {pg.title()}")
    print(f"  [LOGIN] Inputs   : {_input_tokens(pg)}")

    # ── 3. Find fields ───────────────────────────────────────────────────────
    username_field = _find_field(pg, _USER_KEYS)
    password_field = _find_field(pg, _PASS_KEYS)

    if username_field is None:
        pg.screenshot(path=os.path.join(dbg_dir, "error_no_username.png"), full_page=True)
        raise RuntimeError("Could not locate username field on login page")
    if password_field is None:
        pg.screenshot(path=os.path.join(dbg_dir, "error_no_password.png"), full_page=True)
        raise RuntimeError("Could not locate password field on login page")

    # ── 4. Fill fields ───────────────────────────────────────────────────────
    _fill_field(pg, username_field, config["credentials"]["username"])
    print(f"  [LOGIN] Username filled")
    _fill_field(pg, password_field, config["credentials"]["password"])
    print(f"  [LOGIN] Password filled")

    pg.screenshot(path=os.path.join(dbg_dir, "2_after_fill.png"), full_page=True)

    # Brief pause so the framework can process onChange and enable the submit button
    pg.wait_for_timeout(600)

    # ── 5. Submit ────────────────────────────────────────────────────────────
    _submit_login(pg, password_field, timeout)
    print(f"  [LOGIN] Submit triggered")

    # ── 6. Wait for redirect away from /login ────────────────────────────────
    try:
        pg.wait_for_url(
            lambda url: "/login" not in url.lower(),
            timeout=timeout,
        )
    except Exception:
        # URL didn't change — check if there's an error message on the page
        pass

    pg.wait_for_load_state("networkidle", timeout=min(timeout, 10000))
    pg.screenshot(path=os.path.join(dbg_dir, "3_after_login.png"), full_page=True)
    print(f"  [LOGIN] After-login URL: {pg.url}")

    # ── 7. Verify success ────────────────────────────────────────────────────
    if "/login" in pg.url.lower() and _looks_like_login_page(pg):
        # Try to capture any error message the app shows
        error_msg = ""
        for sel in [
            ".error", ".alert", ".alert-danger", "[class*='error']",
            "[class*='alert']", "[role='alert']", ".notification",
            "[class*='message']", "[class*='invalid']",
        ]:
            try:
                el = pg.locator(sel).first
                if el.count() > 0 and el.is_visible(timeout=1000):
                    error_msg = el.inner_text().strip()
                    break
            except Exception:
                pass
        detail = f" — App says: '{error_msg}'" if error_msg else ""
        raise RuntimeError(
            f"Login failed: still on login page at {pg.url}{detail}"
        )


# ── Logout helper ─────────────────────────────────────────────────────────────

def _logout_if_possible(page: Page, config) -> None:
    if page is None:
        return
    timeout = int(config.get("browser", {}).get("timeout", 15000))
    for sel in [
        "a:has-text('Logout')", "button:has-text('Logout')",
        "a:has-text('Log out')", "button:has-text('Log out')",
        "a:has-text('Sign Out')", "button:has-text('Sign Out')",
        "[aria-label*='logout' i]", "[title*='logout' i]",
    ]:
        try:
            el = page.locator(sel).first
            if el.count() > 0 and el.is_visible(timeout=2000):
                el.click()
                page.wait_for_load_state("networkidle", timeout=timeout)
                return
        except Exception:
            pass
    base = _normalize_base_url(
        config["environment"]["base_url"],
        config["environment"].get("app_path", ""),
    )
    for path in ["logout", "signout", "sign-out"]:
        try:
            page.goto(f"{base.rstrip('/')}/{path}", wait_until="domcontentloaded", timeout=timeout)
            return
        except Exception:
            pass


# ── TC ID / module helpers ────────────────────────────────────────────────────

_TC_PATTERN = re.compile(r"test_(TC_[A-Za-z]+_\d+)", re.IGNORECASE)

_MODULE_MAP = {
    "TC_LOG": "Login",
    "TC_BC":  "Broadcast",
    "TC_DIC": "Departments",
    "TC_CM":  "Credit_Management",
    "TC_CR":  "CreditReports",
    "TC_UM":  "User_Management",
    "TC_RPT": "Reports",
    "TC_HDR": "Home_Header",
    "TC_GEN": "General_CrossCutting",
}


def _tc_id_from_name(name: str):
    m = _TC_PATTERN.search(name)
    if not m:
        return None
    return m.group(1).upper().replace("_", "-", 2)


def _module_folder(tc_id: str) -> str:
    if not tc_id:
        return "Unknown"
    parts  = tc_id.split("-")
    prefix = "_".join(parts[:2])
    return _MODULE_MAP.get(prefix, prefix)


def _screenshot_path(tc_id: str, module: str) -> str:
    folder = os.path.join(SCREENSHOT_DIR, module)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{tc_id}_{module}.png")


# ── Session start ─────────────────────────────────────────────────────────────

def pytest_sessionstart(session):
    try:
        import fix_summary
        fix_summary.fix()
    except PermissionError:
        print("\nWARNING: QA_Test_Cases.xlsx is open — close it to update Summary.\n")
    except Exception as e:
        print(f"\nWARNING: Summary auto-update failed: {e}\n")


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture(scope="session")
def config():
    return _CFG


@pytest.fixture(scope="session")
def test_data():
    """Centralised test data from config/test_data.yaml."""
    return _TEST_DATA


@pytest.fixture(scope="session")
def browser(config):
    browser_name  = (config.get("browser", {}).get("type") or "chromium").lower()
    headless      = bool(config.get("browser", {}).get("headless", False))
    slow_mo       = int(config.get("browser", {}).get("slow_mo", 0))
    launch_kwargs = {"headless": headless, "slow_mo": slow_mo}

    if browser_name == "chrome":
        launch_kwargs["channel"] = "chrome"
    elif browser_name == "msedge":
        launch_kwargs["channel"] = "msedge"

    p = sync_playwright().start()
    try:
        b = getattr(p, browser_name if browser_name not in ("chrome", "msedge") else "chromium").launch(**launch_kwargs)
        yield b
    finally:
        try:
            b.close()
        except Exception:
            pass
        try:
            p.stop()
        except Exception:
            pass


@pytest.fixture(scope="session")
def base_url(config):
    raw = (config["environment"].get("base_url") or "").strip()
    return _normalize_base_url(raw, config["environment"].get("app_path", ""))


@pytest.fixture(scope="session")
def url_for(base_url):
    def _url_for(path: str) -> str:
        return f"{base_url.rstrip('/')}/{path.lstrip('/')}" if path else base_url
    return _url_for


@pytest.fixture(scope="module")
def page(browser, config):
    """Authenticated page — logs in once per module, reused across all tests in that module."""
    record_video = VIDEO_ON
    ctx_kwargs   = {"ignore_https_errors": True}
    if record_video:
        video_dir = os.path.join(ROOT, "videos")
        os.makedirs(video_dir, exist_ok=True)
        ctx_kwargs["record_video_dir"]  = video_dir
        ctx_kwargs["record_video_size"] = {"width": 1280, "height": 720}

    ctx = browser.new_context(**ctx_kwargs)
    pg  = ctx.new_page()
    pg.set_default_timeout(config["browser"]["timeout"])

    _do_login(pg, config)

    time.sleep(2)
    try:
        yield pg
    finally:
        try:
            _logout_if_possible(pg, config)
        except Exception:
            pass
        try:
            pg.close()
        except Exception:
            pass
        try:
            ctx.close()
        except Exception:
            pass


# ── Screenshot on failure + Excel write ──────────────────────────────────────

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report  = outcome.get_result()

    if report.when != "call":
        return

    tc_id  = _tc_id_from_name(item.name)
    module = _module_folder(tc_id) if tc_id else "Unknown"
    failed = report.failed
    actual = str(call.excinfo.value)[:300] if call.excinfo else ""
    status = "Fail" if failed else "Pass"

    pg = item.funcargs.get("page") or item.funcargs.get("auth_page")

    # ── Screenshot on failure → attach to Allure ─────────────────────────────
    if failed and pg:
        try:
            shot_path = _screenshot_path(tc_id or item.name, module)
            pg.screenshot(path=shot_path, full_page=True)
            if SCREENSHOT_ON:
                with open(shot_path, "rb") as f:
                    allure.attach(
                        f.read(),
                        name=f"{tc_id or item.name} — failure screenshot",
                        attachment_type=allure.attachment_type.PNG,
                    )
        except Exception:
            pass

    # ── Video on failure → attach to Allure ──────────────────────────────────
    if failed and VIDEO_ON and pg:
        try:
            video_path = pg.video.path() if pg.video else None
            if video_path and os.path.exists(video_path):
                with open(video_path, "rb") as f:
                    allure.attach(
                        f.read(),
                        name=f"{tc_id or item.name} — failure video",
                        attachment_type=allure.attachment_type.WEBM,
                    )
        except Exception:
            pass

    # ── Excel write ───────────────────────────────────────────────────────────
    if tc_id and EXCEL_PATH:
        try:
            from excel_writer import write_result
            if not write_result(EXCEL_PATH, tc_id, status, actual):
                print(f"\n  WARNING: {tc_id} not found in Excel")
        except PermissionError:
            print(f"\n  WARNING: Excel locked — could not write result for {tc_id}")
        except Exception as e:
            print(f"\n  WARNING: Excel write failed for {tc_id}: {e}")
