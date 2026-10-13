from playwright.sync_api import sync_playwright
import yaml

cfg = yaml.safe_load(open(r'D:\Documents\Learning\MyApps\KUAutomation\config\config.yaml', encoding='utf-8'))
base = cfg['environment']['base_url'].rstrip('/')
app = cfg['environment'].get('app_path', '').strip('/')
login_url = f"{base}/{app}/login" if app else f"{base}/login"
print('LOGIN_URL', login_url)

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page(ignore_https_errors=True)
    page.goto(login_url, wait_until='domcontentloaded', timeout=30000)
    print('PAGE_URL', page.url)
    print('TITLE', page.title())
    print('BODY', page.locator('body').inner_text()[:2000])
    inputs = page.locator('input')
    print('INPUT_COUNT', inputs.count())
    for i in range(min(inputs.count(), 10)):
        el = inputs.nth(i)
        print('INPUT', i, {
            'name': el.get_attribute('name'),
            'id': el.get_attribute('id'),
            'type': el.get_attribute('type'),
            'placeholder': el.get_attribute('placeholder'),
            'aria-label': el.get_attribute('aria-label'),
        })
    buttons = page.locator('button')
    print('BUTTON_COUNT', buttons.count())
    for i in range(min(buttons.count(), 20)):
        b = buttons.nth(i)
        print('BUTTON', i, repr(b.inner_text()[:120]))
    try:
        username = cfg['credentials']['username']
        password = cfg['credentials']['password']
        page.fill("input[name='username']", username)
        page.fill("input[name='password']", password)
        page.click("button[type='submit']")
        page.wait_for_load_state('networkidle', timeout=30000)
        print('AFTER_LOGIN_URL', page.url)
        print('AFTER_LOGIN_TITLE', page.title())
        print('AFTER_LOGIN_BODY', page.locator('body').inner_text()[:2000])
    except Exception as e:
        print('LOGIN_ERROR', type(e).__name__, e)
        print('ERROR_BODY', page.locator('body').inner_text()[:2000])
    browser.close()
