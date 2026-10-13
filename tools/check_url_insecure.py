import os
import sys
import yaml
import requests

ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(ROOT, 'config', 'config.yaml')

if not os.path.exists(CONFIG_PATH):
    print('config not found')
    sys.exit(2)

with open(CONFIG_PATH) as f:
    cfg = yaml.safe_load(f)

base = cfg['environment']['base_url'].rstrip('/')
app = cfg['environment'].get('app_path','').strip('/')
if app:
    base_with_app = f"{base}/{app}"
else:
    base_with_app = base

common_paths = [
    '',
    '/',
    '/login',
    '/Login',
    '/account/login',
    '/Account/Login',
    '/login.aspx',
    '/index',
    '/home',
]

tried = []
for p in common_paths:
    if p.startswith('/'):
        ppath = p
    else:
        ppath = '/' + p if p else ''
    candidates = [
        base + ppath,
        base + '/' + app + ppath if app else base + ppath,
        base_with_app + ppath,
    ]
    for u in candidates:
        if u in tried:
            continue
        tried.append(u)
        try:
            r = requests.get(u, verify=False, timeout=10)
            status = r.status_code
            print(f"{u} -> {status}  len={len(r.text)}")
        except Exception as e:
            print(f"{u} -> ERROR: {e}")

print('Done')
