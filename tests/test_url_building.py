from conftest import _normalize_base_url


def test_base_url_accepts_any_path_after_domain():
    assert _normalize_base_url("https://example.com", "/PuffinUI") == "https://example.com/PuffinUI"
    assert _normalize_base_url("https://example.com/PuffinUI", "") == "https://example.com/PuffinUI"
    assert _normalize_base_url("https://example.com/custom-app", "/portal") == "https://example.com/custom-app/portal"
    assert _normalize_base_url("https://example.com/tenant-a", "/PuffinUI") == "https://example.com/tenant-a/PuffinUI"
    assert _normalize_base_url("https://example.com/tenant-a/PuffinUI", "/PuffinUI") == "https://example.com/tenant-a/PuffinUI"


def test_base_url_keeps_existing_app_path_without_duplicate_slash():
    assert _normalize_base_url("https://example.com/portal", "/portal") == "https://example.com/portal"
    assert _normalize_base_url("https://example.com/portal/", "/portal") == "https://example.com/portal"
    assert _normalize_base_url("https://example.com", "/") == "https://example.com"
    assert _normalize_base_url("https://example.com/any/tenant", "/") == "https://example.com/any/tenant"
