from playwright.sync_api import sync_playwright
import yaml

cfg = yaml.safe_load(open(r'D:\Documents\Learning\MyApps\KUAutomation\config\config.yaml', encoding='utf-8'))
base = cfg['environment']['base_url'].rstrip('/')
app = cfg['environment'].get('app_path', '').strip('/')
login_url = f"{base}/{app}/login" if app else f"{base}/login"
print('LOGIN_URL', login_url)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    page = browser.new_page(ignore_https_errors=True)
    page.goto(login_url, wait_until='domcontentloaded', timeout=30000)
    print('PAGE_URL', page.url)
    print('TITLE', page.title())
    print('INPUT_COUNT', page.locator('input').count())
    for i in range(page.locator('input').count()):
        el = page.locator('input').nth(i)
        print('INPUT', i, {
            'name': el.get_attribute('name'),
            'id': el.get_attribute('id'),
            'type': el.get_attribute('type'),
            'placeholder': el.get_attribute('placeholder'),
            'role': el.get_attribute('role'),
            'value': el.get_attribute('value')
        })
    for i in range(page.locator('button').count()):
        b = page.locator('button').nth(i)
        print('BUTTON', i, 'text=', repr(b.inner_text()[:200]), 'visible=', b.is_visible())
    page.fill("input[name='username']", cfg['credentials']['username'])
    page.fill("input[name='password']", cfg['credentials']['password'])
    btn = page.locator("button:has-text('Login'), button[type='submit'], [type='submit']").first
    print('BTN_TEXT', btn.inner_text())
    print('BTN_VISIBLE', btn.is_visible())
    btn.click(force=True)
    page.wait_for_timeout(8000)
    print('AFTER_LOGIN_URL', page.url)
    print('AFTER_LOGIN_TITLE', page.title())
    print('AFTER_LOGIN_BODY_SNIP', page.locator('body').inner_text()[:2000])
    browser.close()
