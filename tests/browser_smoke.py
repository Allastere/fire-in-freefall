"""Optional browser verification of the question-first workspace; no paid API calls."""
import os
from pathlib import Path
from playwright.sync_api import expect,sync_playwright

BASE=os.getenv('FLAME_TEST_URL','http://127.0.0.1:8768')
OUTPUT=Path(__file__).resolve().parents[1]/'design_reference'/'verification-intelligence'
OUTPUT.mkdir(exist_ok=True)
def ready(page):
    expect(page.locator('.ff-footer')).to_be_attached(timeout=60000)
    expect(page.get_by_test_id('stException')).to_have_count(0)
    page.wait_for_function("document.querySelectorAll('[data-testid=stSkeleton]').length === 0")
    page.wait_for_function("!Array.from(document.querySelectorAll('[data-testid=stStatusWidget]')).some(e=>e.textContent.toLowerCase().includes('running'))")
with sync_playwright() as p:
    browser=p.chromium.launch(channel='msedge',headless=True)
    page=browser.new_page(viewport={'width':1440,'height':1100})
    page.goto(BASE);ready(page)
    page.screenshot(path=str(OUTPUT/'01-overview.png'))
    for title in ['Explorer','Ranking','SI Insights']:
        page.locator('.st-key-editorial_nav').get_by_role('link',name=title,exact=True).click()
        ready(page)
        page.screenshot(path=str(OUTPUT/(title.lower().replace(' ','-')+'.png')))
    page.get_by_text('Include source-cited Gemini interpretation',exact=True).click()
    page.get_by_text('DETECTION',exact=True).click()
    page.get_by_role('button',name='Analyze scientific question',exact=True).click()
    expect(page.locator('.ff-conclusion')).to_be_visible(timeout=60000)
    ready(page)
    expect(page.locator('.js-plotly-plot').first).to_be_attached(timeout=30000)
    page.locator('.ff-conclusion').scroll_into_view_if_needed()
    page.screenshot(path=str(OUTPUT/'detection-answer.png'),full_page=True)
    page.set_viewport_size({'width':600,'height':950})
    page.screenshot(path=str(OUTPUT/'narrow.png'),full_page=True)
    print('Four pages, three-pillar workspace, detection answer/chart and narrow layout: OK')
    browser.close()
