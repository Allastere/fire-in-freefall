"""Optional Edge verification of the four-page editorial app; no paid Gemini calls."""

import os
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

OUTPUT = Path(__file__).resolve().parents[1] / "design_reference" / "verification-v2"
OUTPUT.mkdir(exist_ok=True)
BASE = os.getenv("FLAME_TEST_URL", "http://127.0.0.1:8766")


def ready(page):
    expect(page.locator(".ff-footer")).to_be_attached(timeout=60000)
    expect(page.get_by_test_id("stException")).to_have_count(0)
    page.wait_for_function("document.querySelectorAll('[data-testid=stSkeleton]').length === 0")
    page.wait_for_function("!Array.from(document.querySelectorAll('[data-testid=stStatusWidget]')).some(e=>e.textContent.toLowerCase().includes('running'))")


with sync_playwright() as p:
    browser = p.chromium.launch(channel="msedge", headless=True)
    page = browser.new_page(viewport={"width": 1600, "height": 1100}, device_scale_factor=1)
    page.goto(BASE)
    ready(page)
    page.locator(".js-plotly-plot").first.wait_for(timeout=30000)
    assert page.get_by_test_id("stSidebar").count() == 0
    assert page.locator(".stApp").evaluate("e=>getComputedStyle(e).backgroundColor") == "rgb(237, 236, 230)"
    page.screenshot(path=str(OUTPUT / "01-overview.png"))
    print("Overview / new light theme / no sidebar: OK", flush=True)
    for title, heading, name in [("Explorer", "The experimental archive.", "02-explorer"),
                                  ("Ranking", "Research relevance.", "03-ranking"),
                                  ("SI Insights", "Material evidence.", "04-insights")]:
        page.locator(".st-key-editorial_nav").get_by_role("link", name=title, exact=True).click()
        expect(page.get_by_role("heading", name=heading, exact=False)).to_be_visible(timeout=60000)
        ready(page)
        page.mouse.move(1400, 100)
        page.screenshot(path=str(OUTPUT / f"{name}.png"))
        print(title + ": OK", flush=True)
    page.get_by_role("button", name="Run assessment", exact=True).wait_for(timeout=60000)
    page.get_by_text("Use a recorded experiment or mission environment", exact=True).click()
    field = page.locator(".st-key-editorial_reference").get_by_role("combobox")
    field.focus()
    field.press("ArrowDown")
    field.press("Enter")
    expect(field).to_have_value("PSI-25:B1")
    page.get_by_role("button", name="Load recorded conditions", exact=True).click()
    expect(page.get_by_role("spinbutton", name="Oxygen concentration (%)", exact=True)).to_have_value("22.2000")
    expect(page.get_by_role("spinbutton", name="Gravity (g)", exact=True)).to_have_value("0.0000")
    expect(page.get_by_role("checkbox", name="Include Gemini scientific synthesis", exact=True)).not_to_be_checked()
    page.get_by_role("button", name="Run assessment", exact=True).click()
    expect(page.locator(".ff-conclusion")).to_be_visible(timeout=60000)
    expect(page.get_by_test_id("stMetricValue").first).to_contain_text("0.44")
    expect(page.get_by_text("SI-generated research proposal", exact=False)).to_have_count(0)
    page.get_by_text("Scientific assessment / PMMA", exact=False).scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT / "05-b1-observed.png"))
    page.get_by_text("Configure material and environment", exact=True).click()
    page.get_by_role("spinbutton", name="Gravity (g)", exact=True).fill("0.166")
    page.get_by_role("spinbutton", name="Gravity (g)", exact=True).press("Enter")
    expect(page.get_by_text("Conditions have changed.", exact=False)).to_be_visible()
    expect(page.locator(".ff-conclusion")).to_have_count(0)
    page.get_by_role("button", name="Run assessment", exact=True).click()
    expect(page.locator(".ff-conclusion")).to_contain_text("Related experimental records", timeout=60000)
    page.screenshot(path=str(OUTPUT / "06-related-evidence.png"))
    page.set_viewport_size({"width": 900, "height": 1000})
    page.screenshot(path=str(OUTPUT / "07-narrow.png"))
    print("B1 observed / conditions preserved / changed inputs invalidate result / related evidence: OK", flush=True)
    browser.close()
