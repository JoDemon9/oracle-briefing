#!/usr/bin/env python3
"""Render the actual portal and exercise unavailable editions and storage failures."""
import argparse
import functools
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass

def run(screenshots=None):
    server = ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    records = json.loads((ROOT/'docs/data/editions.json').read_text())
    published = [x for x in records if x['status']=='published']
    order = {'morning':0, 'midday':1, 'evening':2}
    latest = max(published, key=lambda x:(x['date'], order[x['type']]))
    checks = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            # Existing portal styling uses Tailwind and Google Fonts. Block every other external request.
            def route(request):
                url = request.request.url
                if url.startswith(base) or urlparse(url).hostname in {'cdn.tailwindcss.com','fonts.googleapis.com','fonts.gstatic.com'}:
                    request.continue_()
                else:
                    request.abort()
            context.route('**/*', route)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error:errors.append(str(error)))
            for width in [320,375,390,1440]:
                page.set_viewport_size({'width':width,'height':900})
                page.goto(base+'/index.html', wait_until='networkidle')
                page.wait_for_function('document.querySelector("[data-published-editions]").textContent.includes("Δημοσιευμένη")')
                assert page.evaluate('getComputedStyle(document.querySelector(".max-w-7xl")).maxWidth')!='none', 'Portal styles did not load'
                if screenshots and width in [320,375,1440]:
                    screenshots.mkdir(parents=True, exist_ok=True)
                    page.screenshot(path=str(screenshots/f'{width}-portal.png'), full_page=True)
                if not page.evaluate('document.documentElement.scrollWidth<=innerWidth+1'):
                    print(page.evaluate('JSON.stringify([...document.querySelectorAll("*")].filter(e=>e.getBoundingClientRect().right>innerWidth+1 && !e.closest(".ticker-wrap,.overflow-x-auto,#wireDrawerModal")).slice(0,25).map(e=>({tag:e.tagName,cls:e.className,right:e.getBoundingClientRect().right,text:e.textContent.slice(0,100)})))'))
                    raise AssertionError(f'Portal overflow at {width}px')
                assert page.locator('[data-published-editions] a').count()==3
                assert page.locator('[data-latest-briefing]').first.get_attribute('href').endswith(latest['url'])
                assert latest['date'] in page.locator('[data-latest-edition-label]').inner_text()
                for button in page.locator('button:visible').all():
                    assert button.bounding_box()['height']>=43
                assert not errors, errors
                checks.append(f'{width}px portal, published links, labels and touch targets passed')
            page.locator('#themeToggle').focus()
            page.keyboard.press('Enter')
            assert page.locator('html').get_attribute('class')=='dark'
            checks.append('Portal keyboard theme control passed')
            limited = [dict(x, status='draft') if x['date']==latest['date'] and x['type']=='evening' else x for x in records]
            page.route('**/data/editions.json', lambda r:r.fulfill(json=limited[::-1]))
            page.reload(wait_until='networkidle')
            assert page.locator('[data-published-editions] a').count()==2
            assert 'Βραδινή · Δεν έχει δημοσιευτεί' in page.locator('[data-published-editions]').inner_text()
            assert 'Μεσημεριανή' in page.locator('[data-latest-edition-label]').inner_text()
            checks.append('Missing evening, draft exclusion and unsorted registry passed')
            page.unroute('**/data/editions.json')
            page.route('**/data/editions.json', lambda r:r.fulfill(status=404,body='missing'))
            page.reload(wait_until='networkidle')
            assert 'δεν φορτώθηκε' in page.locator('[data-published-editions]').inner_text()
            checks.append('Missing portal registry shows a usable error state')
            page.unroute('**/data/editions.json')
            page.add_init_script('Object.defineProperty(window,"localStorage",{get(){throw new Error("blocked")}})')
            errors.clear()
            page.reload(wait_until='networkidle')
            page.locator('#themeToggle').click()
            assert page.locator('html').get_attribute('class')=='dark'
            assert not errors, errors
            checks.append('Portal theme works when browser storage is blocked')
            hostile = [{'title':'<img src=x onerror="window.__wireInjected=true">', 'link':'https://example.com/news', 'snippet':'<script>window.__wireInjected=true</script>', 'source':'RSS', 'time_str':'12/10 12:48 · Κύπρος'}]
            page.route('**/live-wire.json', lambda r:r.fulfill(json=hostile))
            page.route('**/wire-health.json', lambda r:r.fulfill(json={'last_success_at':'2000-01-01T00:00:00Z','status':'ok'}))
            page.reload(wait_until='networkidle')
            page.wait_for_function('document.getElementById("wireHealth").textContent.includes("καθυστερημένη")')
            page.wait_for_function('document.getElementById("liveWireTicker").textContent.includes("<img")')
            assert page.locator('#liveWireTicker img').count()==0
            assert not page.evaluate('Boolean(window.__wireInjected)')
            checks.append('RSS markup stays plain text and stale collection is labelled honestly')
            browser.close()
    finally:
        server.shutdown()
        server.server_close()
    print('\n'.join(checks))
    print(f'{len(checks)} portal browser checks passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--screenshots',type=Path)
    run(parser.parse_args().screenshots)
