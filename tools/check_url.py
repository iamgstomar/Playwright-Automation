"""
Simple diagnostic script: reads config/config.yaml and checks the app base URL
and the login URL. Prints HTTP status codes and a short snippet of the body.

Usage:
    python tools/check_url.py

This helps verify whether the `base_url`, `app_path` and `login_path` in
`config/config.yaml` point at a reachable resource and if the login page exists.
"""
import os
import sys
import yaml
import requests
from urllib.parse import urljoin

ROOT = os.path.dirname(os.path.dirname(__file__))
CONFIG_PATH = os.path.join(ROOT, 'config', 'config.yaml')


def build_urls(cfg):
    base = cfg['environment']['base_url'].rstrip('/')
    app_path = cfg['environment'].get('app_path', '').strip('/')
    login_path = cfg['environment'].get('login_path', '').lstrip('/')

    if app_path:
        base_with_app = f"{base}/{app_path}"
    else:
        base_with_app = base

    # Build canonical login URL
    if login_path:
        login_url = f"{base_with_app}/{login_path}"
    else:
        login_url = base_with_app

    # Also provide alternatives to try
    alternatives = [
        base,  # domain only
        base + '/',
        base_with_app,
        base_with_app + '/',
        login_url,
        urljoin(base, login_path),  # try joining directly
        urljoin(base_with_app + '/', login_path),
    ]

    # Deduplicate while keeping order
    seen = set()
    result = []
    for u in alternatives:
        if u not in seen:
            seen.add(u)
            result.append(u)
    return result


def load_config(path):
    if not os.path.exists(path):
        print(f"ERROR: config not found at {path}")
        sys.exit(2)
    with open(path, 'r') as f:
        return yaml.safe_load(f)


def fetch(url, timeout=10):
    try:
        r = requests.get(url, timeout=timeout, verify=True)
        return (r.status_code, r.headers.get('Content-Type', ''), r.text[:1000])
    except requests.exceptions.RequestException as e:
        return (None, None, f"ERROR: {e}")


if __name__ == '__main__':
    cfg = load_config(CONFIG_PATH)
    urls = build_urls(cfg)

    print(f"Testing URLs derived from {CONFIG_PATH}")
    for u in urls:
        print('\n-->', u)
        status, ctype, snippet = fetch(u)
        if status is None:
            print(snippet)
        else:
            print(f"Status: {status}  Content-Type: {ctype}")
            if snippet:
                snippet = snippet.replace('\n', ' ')[:500]
                print("Body snippet:", snippet)

    print('\nDone. If all relevant URLs return 404, check server or app path settings.')
