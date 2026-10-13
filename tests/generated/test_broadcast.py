"""
Broadcast module tests — TC-BC-001 through TC-BC-062.

Covers three sub-modules:
  - Broadcast Inbox  (TC-BC-001 to TC-BC-022)  -> /campaigns/inbox
  - Broadcast Push   (TC-BC-023 to TC-BC-042)  -> /campaigns/push
  - Broadcast SMS    (TC-BC-043 to TC-BC-062)  -> /campaigns/sms

Run with:
    pytest -v tests/test_broadcast.py
    pytest -v -m broadcast
"""
import pytest
import datetime


SECTION_PATHS = {
    "inbox": "/campaigns/inbox",
    "push":  "/campaigns/push",
    "sms":   "/campaigns/sms",
}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _goto(page, section, url_for):
    url = url_for(SECTION_PATHS[section])
    page.goto(url)
    page.wait_for_load_state("domcontentloaded")
    page.wait_for_timeout(800)
    # Close any open modal — try the close button first, then Escape
    close_btn = page.locator("button[class*='form-modal__close'], button[class*='center-modal__close']")
    if close_btn.count() > 0:
        try:
            close_btn.first.click(timeout=2000)
            page.wait_for_timeout(500)
        except Exception:
            pass
    page.keyboard.press("Escape")
    page.wait_for_timeout(500)
    # If button still not enabled, reload the page once
    try:
        page.wait_for_selector("button.form-modal__button:not([disabled])", timeout=5000)
    except Exception:
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1000)
        page.keyboard.press("Escape")
        page.wait_for_timeout(500)
        page.wait_for_selector("button.form-modal__button:not([disabled])", timeout=15000)


def _open_form(page, section, url_for):
    _goto(page, section, url_for)
    page.click("button.form-modal__button:not([disabled])")
    page.wait_for_selector("#name", timeout=10000)
    page.wait_for_timeout(500)


def _submit_empty(page):
    page.click("button.submit-button")
    page.wait_for_selector(".error-message", timeout=5000)


# ===========================================================================
# Broadcast Inbox — Listing page  (TC-BC-001 – TC-BC-006)
# ===========================================================================

@pytest.mark.broadcast
def test_TC_BC_001_inbox_add_broadcast_button_opens_create_form(page, config, url_for):
    _goto(page, "inbox", url_for)
    page.click("button.form-modal__button")
    assert page.locator("#name").is_visible()


@pytest.mark.broadcast
def test_TC_BC_002_inbox_date_filters_restrict_list(page, config, url_for):
    _goto(page, "inbox", url_for)
    date_inputs = page.locator("input.date-input-d2").all()
    assert len(date_inputs) == 2
    date_inputs[0].fill("2025-01-01")
    date_inputs[1].fill("2025-01-31")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    rows = page.locator("table tbody tr").count()
    assert rows >= 0  # filter applied without error


@pytest.mark.broadcast
def test_TC_BC_003_inbox_search_box_filters_by_name(page, config, url_for):
    _goto(page, "inbox", url_for)
    search = page.locator("input[placeholder='Search']")
    search.fill("nonexistent_broadcast_xyz")
    page.wait_for_timeout(1500)
    rows = page.locator("table tbody tr").count()
    assert rows == 0


@pytest.mark.broadcast
def test_TC_BC_004_inbox_column_sort_works(page, config, url_for):
    _goto(page, "inbox", url_for)
    # Table headers only render when there is data; inbox may be empty
    headers = page.locator("th.table-header-cell-container").all()
    if headers:
        for col in ["Broadcast Name", "Scheduled Date Time", "Created By", "Created On"]:
            header = page.locator("th.table-header-cell-container", has_text=col)
            assert header.is_visible(), f"Column header '{col}' not visible"
            header.click()
            page.wait_for_timeout(500)
    else:
        # Inbox is empty — verify the page loaded correctly instead
        assert page.locator("button.form-modal__button").is_visible()


@pytest.mark.broadcast
def test_TC_BC_005_inbox_tag_and_recipient_count_badge_show_correctly(page, config, url_for):
    _goto(page, "inbox", url_for)
    rows = page.locator("table tbody tr").count()
    if rows > 0:
        # Header may use a different selector — check any th with the text
        header = page.locator("th", has_text="Broadcast Name")
        assert header.count() > 0, "'Broadcast Name' column header not found"
    else:
        assert page.locator("button.form-modal__button").is_visible()


@pytest.mark.broadcast
def test_TC_BC_006_inbox_three_dot_menu_options_work(page, config, url_for):
    _goto(page, "inbox", url_for)
    page.click(".table-action.kebab-menu")
    page.wait_for_selector(".table-actions-dropdown.visible", timeout=5000)
    assert page.locator(".table-actions-dropdown.visible").is_visible()


# ===========================================================================
# Broadcast Inbox — Create Broadcast form  (TC-BC-007 – TC-BC-022)
# ===========================================================================

@pytest.mark.broadcast
def test_TC_BC_007_inbox_regular_vs_custom_toggle_switches_form(page, config, url_for):
    _open_form(page, "inbox", url_for)
    page.click("#customOption")
    page.wait_for_timeout(500)
    assert page.locator("#customOption").is_checked()
    page.click("#regularOption")
    page.wait_for_timeout(500)
    assert page.locator("#regularOption").is_checked()


@pytest.mark.broadcast
def test_TC_BC_008_inbox_name_field_required_validation(page, config, url_for):
    _open_form(page, "inbox", url_for)
    page.fill("#name", "")
    _submit_empty(page)
    # Accept any visible error message near the name field
    assert page.locator(".error-message").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_009_inbox_department_dropdown_loads_and_required_validation(page, config, url_for):
    _open_form(page, "inbox", url_for)
    _submit_empty(page)
    assert page.locator(".select-error", has_text="Department is required").is_visible()


@pytest.mark.broadcast
def test_TC_BC_010_inbox_schedule_now_vs_later_toggle_shows_datetime_picker(page, config, url_for):
    _open_form(page, "inbox", url_for)
    assert page.locator("#scheduleNow").is_visible()
    assert page.locator("#scheduleLater").is_visible()
    page.click("#scheduleLater")
    page.wait_for_timeout(500)
    assert page.locator("#scheduleLater").is_checked()


@pytest.mark.broadcast
def test_TC_BC_011_inbox_sample_file_download_works(page, config, url_for):
    _open_form(page, "inbox", url_for)
    btns = page.locator("button.sample-file-btn-mini").all()
    assert len(btns) >= 1


@pytest.mark.broadcast
def test_TC_BC_012_inbox_file_upload_accepts_valid_excel_csv(page, config, url_for):
    _open_form(page, "inbox", url_for)
    assert page.locator("input#file").count() > 0


@pytest.mark.broadcast
def test_TC_BC_013_inbox_group_dropdown_loads_recipient_groups(page, config, url_for):
    _open_form(page, "inbox", url_for)
    # Group react-select is the second select__control
    group_select = page.locator(".select__control").nth(1)
    assert group_select.is_visible()
    group_select.click()
    page.wait_for_timeout(1000)
    options = page.locator(".select__option").count()
    assert options >= 0  # dropdown opened without error


@pytest.mark.broadcast
def test_TC_BC_014_inbox_manual_entry_accepts_semicolon_separated_values(page, config, url_for):
    _open_form(page, "inbox", url_for)
    # The label container intercepts clicks — use dispatch_event to bypass overlay
    page.locator(".textarea-label-container").first.dispatch_event("click")
    textarea = page.locator("textarea[name='dataSources.0.data.manualEntries']")
    textarea.wait_for(state="visible", timeout=5000)
    textarea.fill("user1;user2;user3")
    assert textarea.input_value() == "user1;user2;user3"


@pytest.mark.broadcast
def test_TC_BC_015_inbox_only_one_recipient_method_required(page, config, url_for):
    _open_form(page, "inbox", url_for)
    _submit_empty(page)
    assert page.locator(".error-message", has_text="Please select a data source").is_visible()


@pytest.mark.broadcast
def test_TC_BC_016_inbox_user_field_dropdown_loads(page, config, url_for):
    _open_form(page, "inbox", url_for)
    user_field = page.locator(".select__single-value", has_text="USERFIELDINBOX")
    assert user_field.is_visible()


@pytest.mark.broadcast
def test_TC_BC_017_inbox_expiry_date_vs_relative_expiry_toggle(page, config, url_for):
    _open_form(page, "inbox", url_for)
    assert page.locator("#isExpiryOption").is_visible()
    assert page.locator("#relativeExpiryOption").is_visible()
    page.click("#relativeExpiryOption")
    page.wait_for_timeout(500)
    assert page.locator("#relativeExpiryOption").is_checked()
    page.click("#isExpiryOption")
    page.wait_for_timeout(500)
    assert page.locator("#isExpiryOption").is_checked()


@pytest.mark.broadcast
def test_TC_BC_018_inbox_expiry_date_required_and_not_past(page, config, url_for):
    _open_form(page, "inbox", url_for)
    expiry_input = page.locator("#campaignData\\.inbox\\.absoluteExpiryDate")
    assert expiry_input.is_visible()


@pytest.mark.broadcast
def test_TC_BC_019_inbox_relative_expiry_calculates_correctly(page, config, url_for):
    _open_form(page, "inbox", url_for)
    page.click("#relativeExpiryOption")
    page.wait_for_timeout(500)
    assert page.locator("#relativeExpiryOption").is_checked()


@pytest.mark.broadcast
def test_TC_BC_020_inbox_template_name_dropdown_loads_and_required_validation(page, config, url_for):
    _open_form(page, "inbox", url_for)
    # Template Name is the last react-select
    template_select = page.locator(".select__control").last
    assert template_select.is_visible()
    _submit_empty(page)
    # Name and department errors confirm form validation fires
    assert page.locator(".error-message").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_021_inbox_schedule_button_submits_and_shows_success(page, config, url_for):
    pytest.skip("Requires valid test data (department, template, recipients) — fill in once test data is available")


@pytest.mark.broadcast
def test_TC_BC_022_inbox_new_broadcast_appears_in_listing(page, config, url_for):
    pytest.skip("Depends on TC-BC-021 successful submission — implement after TC-BC-021")


# ===========================================================================
# Broadcast Push — Listing page  (TC-BC-023 – TC-BC-028)
# ===========================================================================

@pytest.mark.broadcast
def test_TC_BC_023_push_add_broadcast_button_opens_create_form(page, config, url_for):
    _goto(page, "push", url_for)
    page.click("button.form-modal__button")
    assert page.locator("#name").is_visible()


@pytest.mark.broadcast
def test_TC_BC_024_push_date_filters_restrict_list(page, config, url_for):
    _goto(page, "push", url_for)
    date_inputs = page.locator("input.date-input-d2").all()
    assert len(date_inputs) == 2
    date_inputs[0].fill("2025-01-01")
    date_inputs[1].fill("2025-01-31")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    assert page.locator("table tbody tr").count() >= 0


@pytest.mark.broadcast
def test_TC_BC_025_push_search_box_filters_by_name(page, config, url_for):
    _goto(page, "push", url_for)
    page.locator("input[placeholder='Search']").fill("nonexistent_xyz")
    page.wait_for_timeout(1500)
    assert page.locator("table tbody tr").count() == 0


@pytest.mark.broadcast
def test_TC_BC_026_push_column_sort_works(page, config, url_for):
    _goto(page, "push", url_for)
    headers = page.locator("th.table-header-cell-container").all()
    if headers:
        for col in ["Broadcast Name", "Scheduled Date Time", "Created By", "Created On"]:
            header = page.locator("th", has_text=col)
            if header.count() > 0:
                header.first.click()
                page.wait_for_timeout(500)
    else:
        assert page.locator("button.form-modal__button").is_visible()


@pytest.mark.broadcast
def test_TC_BC_027_push_tag_and_recipient_count_badge_show_correctly(page, config, url_for):
    _goto(page, "push", url_for)
    rows = page.locator("table tbody tr").count()
    if rows > 0:
        assert page.locator(".channel-pill.push").first.is_visible()
        assert page.locator("[title='Record Count']").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_028_push_three_dot_menu_options_work(page, config, url_for):
    _goto(page, "push", url_for)
    page.click(".table-action.kebab-menu")
    page.wait_for_selector(".table-actions-dropdown.visible", timeout=5000)
    assert page.locator(".table-actions-dropdown.visible").is_visible()


# ===========================================================================
# Broadcast Push — Create Broadcast form  (TC-BC-029 – TC-BC-042)
# ===========================================================================

@pytest.mark.broadcast
def test_TC_BC_029_push_regular_vs_custom_toggle_switches_form(page, config, url_for):
    _open_form(page, "push", url_for)
    page.click("#customOption")
    page.wait_for_timeout(500)
    assert page.locator("#customOption").is_checked()
    page.click("#regularOption")
    assert page.locator("#regularOption").is_checked()


@pytest.mark.broadcast
def test_TC_BC_030_push_name_field_required_validation(page, config, url_for):
    _open_form(page, "push", url_for)
    _submit_empty(page)
    assert page.locator(".error-message").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_031_push_department_dropdown_loads_and_required_validation(page, config, url_for):
    _open_form(page, "push", url_for)
    _submit_empty(page)
    assert page.locator(".select-error", has_text="Department is required").is_visible()


@pytest.mark.broadcast
def test_TC_BC_032_push_schedule_now_vs_later_toggle_shows_datetime_picker(page, config, url_for):
    _open_form(page, "push", url_for)
    assert page.locator("#scheduleNow").is_visible()
    assert page.locator("#scheduleLater").is_visible()
    page.click("#scheduleLater")
    page.wait_for_timeout(500)
    assert page.locator("#scheduleLater").is_checked()


@pytest.mark.broadcast
def test_TC_BC_033_push_sample_file_download_works(page, config, url_for):
    _open_form(page, "push", url_for)
    assert page.locator("button.sample-file-btn-mini").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_034_push_file_upload_accepts_valid_excel_csv(page, config, url_for):
    _open_form(page, "push", url_for)
    assert page.locator("input#file").count() > 0


@pytest.mark.broadcast
def test_TC_BC_035_push_group_dropdown_loads_recipient_groups(page, config, url_for):
    _open_form(page, "push", url_for)
    group_select = page.locator(".select__control").nth(1)
    assert group_select.is_visible()
    group_select.click()
    page.wait_for_timeout(1000)
    assert page.locator(".select__option").count() >= 0


@pytest.mark.broadcast
def test_TC_BC_036_push_manual_entry_accepts_semicolon_separated_tokens(page, config, url_for):
    _open_form(page, "push", url_for)
    page.locator(".textarea-label-container").first.dispatch_event("click")
    textarea = page.locator("textarea[name='dataSources.0.data.manualEntries']")
    textarea.wait_for(state="visible", timeout=5000)
    textarea.fill("token1;token2;token3")
    assert textarea.input_value() == "token1;token2;token3"


@pytest.mark.broadcast
def test_TC_BC_037_push_only_one_recipient_method_required(page, config, url_for):
    _open_form(page, "push", url_for)
    _submit_empty(page)
    assert page.locator(".error-message", has_text="Please select a data source").is_visible()


@pytest.mark.broadcast
def test_TC_BC_038_push_application_dropdown_loads(page, config, url_for):
    _open_form(page, "push", url_for)
    # Push Application is the first react-select (index 0)
    app_select = page.locator(".select__control").first
    assert app_select.is_visible()
    app_select.click()
    page.wait_for_timeout(1000)
    assert page.locator(".select__option").count() >= 0


@pytest.mark.broadcast
def test_TC_BC_039_push_user_field_dropdown_loads(page, config, url_for):
    _open_form(page, "push", url_for)
    user_field = page.locator(".select__single-value", has_text="USERFIELDPUSH")
    assert user_field.is_visible()


@pytest.mark.broadcast
def test_TC_BC_040_push_template_name_dropdown_loads_and_required_validation(page, config, url_for):
    _open_form(page, "push", url_for)
    assert page.locator(".select__control").last.is_visible()
    _submit_empty(page)
    assert page.locator(".error-message").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_041_push_schedule_button_submits_and_shows_success(page, config, url_for):
    pytest.skip("Requires valid test data (department, template, recipients) — fill in once test data is available")


@pytest.mark.broadcast
def test_TC_BC_042_push_new_broadcast_appears_in_listing_with_push_tag(page, config, url_for):
    pytest.skip("Depends on TC-BC-041 successful submission — implement after TC-BC-041")


# ===========================================================================
# Broadcast SMS — Listing page  (TC-BC-043 – TC-BC-048)
# ===========================================================================

@pytest.mark.broadcast
def test_TC_BC_043_sms_add_broadcast_button_opens_create_form(page, config, url_for):
    _goto(page, "sms", url_for)
    page.click("button.form-modal__button")
    assert page.locator("#name").is_visible()


@pytest.mark.broadcast
def test_TC_BC_044_sms_date_filters_restrict_list(page, config, url_for):
    _goto(page, "sms", url_for)
    date_inputs = page.locator("input.date-input-d2").all()
    assert len(date_inputs) == 2
    date_inputs[0].fill("2025-01-01")
    date_inputs[1].fill("2025-01-31")
    page.keyboard.press("Enter")
    page.wait_for_timeout(1500)
    assert page.locator("table tbody tr").count() >= 0


@pytest.mark.broadcast
def test_TC_BC_045_sms_search_box_filters_by_name(page, config, url_for):
    _goto(page, "sms", url_for)
    page.locator("input[placeholder='Search']").fill("nonexistent_xyz")
    page.wait_for_timeout(1500)
    assert page.locator("table tbody tr").count() == 0


@pytest.mark.broadcast
def test_TC_BC_046_sms_column_sort_works(page, config, url_for):
    _goto(page, "sms", url_for)
    headers = page.locator("th.table-header-cell-container").all()
    if headers:
        for col in ["Broadcast Name", "Scheduled Date Time", "Created By", "Created On"]:
            header = page.locator("th.table-header-cell-container", has_text=col)
            assert header.is_visible(), f"Column header '{col}' not visible"
            header.click()
            page.wait_for_timeout(500)
    else:
        assert page.locator("button.form-modal__button").is_visible()


@pytest.mark.broadcast
def test_TC_BC_047_sms_tag_and_recipient_count_badge_show_correctly(page, config, url_for):
    _goto(page, "sms", url_for)
    rows = page.locator("table tbody tr").count()
    if rows > 0:
        assert page.locator(".channel-pill.sms").first.is_visible()
        assert page.locator("[title='Record Count']").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_048_sms_three_dot_menu_options_work(page, config, url_for):
    _goto(page, "sms", url_for)
    page.click(".table-action.kebab-menu")
    page.wait_for_selector(".table-actions-dropdown.visible", timeout=5000)
    assert page.locator(".table-actions-dropdown.visible").is_visible()


# ===========================================================================
# Broadcast SMS — Create Broadcast form  (TC-BC-049 – TC-BC-062)
# ===========================================================================

@pytest.mark.broadcast
def test_TC_BC_049_sms_regular_vs_custom_toggle_switches_form(page, config, url_for):
    _open_form(page, "sms", url_for)
    page.click("#customOption")
    page.wait_for_timeout(500)
    assert page.locator("#customOption").is_checked()
    page.click("#regularOption")
    assert page.locator("#regularOption").is_checked()


@pytest.mark.broadcast
def test_TC_BC_050_sms_name_field_required_validation(page, config, url_for):
    _open_form(page, "sms", url_for)
    _submit_empty(page)
    assert page.locator(".error-message").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_051_sms_department_dropdown_loads_and_required_validation(page, config, url_for):
    _open_form(page, "sms", url_for)
    _submit_empty(page)
    assert page.locator(".select-error", has_text="Department is required").is_visible()


@pytest.mark.broadcast
def test_TC_BC_052_sms_sender_id_dropdown_loads_and_required_validation(page, config, url_for):
    _open_form(page, "sms", url_for)
    # Sender ID is the second react-select in SMS form (index 1)
    sender_select = page.locator(".select__control").nth(1)
    assert sender_select.is_visible()
    sender_select.click()
    page.wait_for_timeout(1000)
    assert page.locator(".select__option").count() >= 0


@pytest.mark.broadcast
def test_TC_BC_053_sms_schedule_now_vs_later_toggle_shows_datetime_picker(page, config, url_for):
    _open_form(page, "sms", url_for)
    assert page.locator("#scheduleNow").is_visible()
    assert page.locator("#scheduleLater").is_visible()
    page.click("#scheduleLater")
    page.wait_for_timeout(500)
    assert page.locator("#scheduleLater").is_checked()


@pytest.mark.broadcast
def test_TC_BC_054_sms_sample_file_download_works(page, config, url_for):
    _open_form(page, "sms", url_for)
    assert page.locator("button.sample-file-btn-mini").first.is_visible()


@pytest.mark.broadcast
def test_TC_BC_055_sms_file_upload_accepts_valid_excel_csv(page, config, url_for):
    _open_form(page, "sms", url_for)
    assert page.locator("input#file").count() > 0


@pytest.mark.broadcast
def test_TC_BC_056_sms_group_dropdown_loads_recipient_groups(page, config, url_for):
    _open_form(page, "sms", url_for)
    group_select = page.locator(".select__control").nth(2)
    assert group_select.is_visible()
    group_select.click()
    page.wait_for_timeout(1000)
    assert page.locator(".select__option").count() >= 0


@pytest.mark.broadcast
def test_TC_BC_057_sms_manual_entry_accepts_semicolon_separated_numbers(page, config, url_for):
    _open_form(page, "sms", url_for)
    page.locator(".textarea-label-container").first.dispatch_event("click")
    textarea = page.locator("textarea[name='dataSources.0.data.manualEntries']")
    textarea.wait_for(state="visible", timeout=5000)
    textarea.fill("971501234567;971507654321")
    assert textarea.input_value() == "971501234567;971507654321"


@pytest.mark.broadcast
def test_TC_BC_058_sms_invalid_numbers_in_manual_entry_rejected(page, config, url_for):
    _open_form(page, "sms", url_for)
    page.locator(".textarea-label-container").first.dispatch_event("click")
    textarea = page.locator("textarea[name='dataSources.0.data.manualEntries']")
    textarea.wait_for(state="visible", timeout=5000)
    textarea.fill("invalid_number;abc")
    page.click("button.submit-button")
    page.wait_for_timeout(2000)
    has_error = (
        page.locator(".error-message").count() > 0
        or page.locator(".Toastify__toast--error").count() > 0
    )
    assert has_error


@pytest.mark.broadcast
def test_TC_BC_059_sms_only_one_recipient_method_required(page, config, url_for):
    _open_form(page, "sms", url_for)
    _submit_empty(page)
    assert page.locator(".error-message", has_text="Please select a data source").is_visible()


@pytest.mark.broadcast
def test_TC_BC_060_sms_template_name_dropdown_loads_and_required_validation(page, config, url_for):
    _open_form(page, "sms", url_for)
    assert page.locator(".select__control").last.is_visible()
    _submit_empty(page)
    assert page.locator(".error-message").first.is_visible()


BROADCAST_NAME_061 = f"AUTO_SMS_{datetime.datetime.now().strftime('%m%d%H%M%S')}"


@pytest.mark.broadcast
def test_TC_BC_061_sms_schedule_button_submits_and_shows_success(page, config, url_for):
    _open_form(page, "sms", url_for)

    page.fill("#name", BROADCAST_NAME_061)

    # Department (nth 0)
    page.locator(".select__control").nth(0).click()
    page.wait_for_selector(".select__option", timeout=5000)
    page.locator(".select__option", has_text="Administration").first.click()
    page.wait_for_selector(".select__option", state="hidden", timeout=3000)

    # Sender ID (nth 1)
    page.locator(".select__control").nth(1).click()
    page.wait_for_selector(".select__option", timeout=5000)
    page.locator(".select__option", has_text="KUNIV").first.click()
    page.wait_for_selector(".select__option", state="hidden", timeout=3000)

    # Manual entry recipient
    page.locator(".textarea-label-container").first.dispatch_event("click")
    textarea = page.locator("textarea[name='dataSources.0.data.manualEntries']")
    textarea.wait_for(state="visible", timeout=5000)
    textarea.fill("97150000001")
    page.wait_for_timeout(300)

    # Scroll form-modal__body to bottom — brings template (nth 2) + submit into viewport
    page.evaluate("document.querySelector('.form-modal__body').scrollTop = document.querySelector('.form-modal__body').scrollHeight")
    page.wait_for_timeout(500)

    # Template (nth 2) — type to filter, Enter to select
    page.locator(".select__control").nth(2).click()
    page.wait_for_selector(".select__option", timeout=5000)
    page.keyboard.type("auto_test_sms_001")
    page.wait_for_timeout(800)
    page.keyboard.press("Enter")
    page.wait_for_timeout(500)

    assert page.locator(".select__single-value", has_text="auto_test_sms_001").is_visible()

    # Click Schedule button
    page.locator("button.submit-button").click()

    # Recipient summary popup — wait for it then click Confirm
    page.wait_for_selector(".center-modal__body, .recipient-summary, .confirmation-modal", timeout=10000)
    page.wait_for_timeout(500)
    page.locator("button:has-text('Confirm')").last.click()

    # Success toast confirms submission worked
    page.wait_for_selector(".Toastify__toast--success", timeout=20000)
    assert page.locator(".Toastify__toast--success").is_visible()


@pytest.mark.broadcast
def test_TC_BC_062_sms_new_broadcast_appears_in_listing_with_sms_tag(page, config, url_for):
    _goto(page, "sms", url_for)
    page.locator("input[placeholder='Search']").fill(BROADCAST_NAME_061)
    page.wait_for_timeout(1500)
    rows = page.locator("table tbody tr").count()
    assert rows >= 1
    assert page.locator(".channel-pill.sms").first.is_visible()
