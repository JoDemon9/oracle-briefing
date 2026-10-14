"""Exercise the actual central newspaper and simulated next publications."""
import argparse
import functools
import hashlib
import json
import threading
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://jodemon9.github.io/Claude-Briefing/'
class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass

def run(screenshots=None):
    if screenshots:screenshots.mkdir(parents=True,exist_ok=True)
    descriptor=json.loads((ROOT/'docs/data/day-latest.json').read_text(encoding='utf-8'))
    original=(ROOT/'docs/data/day-snapshot.html').read_text(encoding='utf-8')
    registry=json.loads((ROOT/'docs/data/editions.json').read_text(encoding='utf-8'))
    available_slots={e['type'] for e in registry if e['date']==descriptor['day_id'] and e['status']=='published'}
    state={'descriptor':descriptor,'html':original,'fail':False,'asset_fail':False,'asset_hash':False,'html_fail':False}
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            context=browser.new_context(reduced_motion='reduce')
            def route(r):
                url=r.request.url
                if url.startswith(base) or url.startswith('data:'):r.continue_()
                elif url.startswith(SOURCE+'data/day-latest.json'):
                    r.fulfill(status=404,body='missing') if state['fail'] else r.fulfill(json=state['descriptor'])
                elif url.startswith(SOURCE+'today.html'):
                    r.fulfill(status=503,body='missing') if state['html_fail'] else r.fulfill(content_type='text/html',body=state['html'])
                elif url.startswith(SOURCE+'assets/'):
                    relative=urlsplit(url).path.removeprefix('/Claude-Briefing/')
                    path=ROOT/'docs/assets/latest-snapshot'/descriptor['version']/relative
                    r.fulfill(status=503,body='missing') if state['asset_fail'] else r.fulfill(body='invalid asset') if state['asset_hash'] else r.fulfill(path=str(path)) if path.is_file() else r.abort()
                else:r.abort()
            context.route('**/*',route)
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            for width in [320,375,390,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                page.goto(base+'/',wait_until='networkidle')
                assert page.url==base+'/'
                assert not page.locator('iframe').count()
                assert page.locator('meta[name="oracle-day-id"]').get_attribute('content')==descriptor['day_id']
                assert page.locator('#cyprus .newscard').count()>0 and page.locator('#world .newscard').count()>0
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                photo=page.locator('.hero .lead-overview img').first
                assert photo.bounding_box()['height']<=201
                assert page.locator('.hero .story-content > h2').bounding_box()['y']<photo.bounding_box()['y']
                assert page.locator('.hero .story-more').count()==0
                assert not page.locator('.hero .card-context').is_visible()
                page.locator('.hero .lead-analysis>summary').click()
                assert page.locator('.hero .card-context').is_visible()
                assert len(page.locator('.hero .card-context').inner_text().split())>=110
                assert page.locator('.hero .read-link').get_attribute('href').startswith(SOURCE+'articles/')
                for img in page.locator('[data-editorial-image] img').all():
                    parent=img.locator('xpath=ancestor::details[1]')
                    if parent.count():parent.evaluate('(x)=>x.open=true')
                    img.scroll_into_view_if_needed();img.evaluate('(x)=>x.decode()')
                    assert img.evaluate('(x)=>x.naturalWidth>0&&x.naturalHeight>0')
                page.locator('details').evaluate_all('(nodes)=>nodes.forEach(x=>x.open=false)')
                assert page.locator('.edition-desk [aria-current]').count()==0
                assert page.locator('.edition-desk a').count()==len(available_slots)
                assert page.locator('.core-quotes>.quote-card:visible').count()<=6
                assert page.locator('.market-movers>.market-note:visible').count()<=3
                assert page.locator('#markets table.quotes').count()==0
                for card in page.locator('.core-quotes>.quote-card').all():
                    assert card.locator('time').is_visible() and card.locator('.quote-status').is_visible()
                if screenshots and width in [375,1440]:
                    page.locator('#markets').screenshot(path=str(screenshots/f'{width}-compact-markets.png'))
                summary=page.locator('.all-quotes>summary');summary.focus();page.keyboard.press('Enter')
                assert summary.evaluate('(x)=>x.parentElement.open')
                for node in page.locator('#markets>details').all():node.evaluate('(x)=>x.open=true')
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                if screenshots and width in [375,1440]:
                    page.locator('.tech-quotes').screenshot(path=str(screenshots/f'{width}-expanded-tech-watch.png'))
                rate_summary=page.locator('.rate-disclosure>summary')
                rate_summary.focus();page.keyboard.press('Enter')
                assert rate_summary.evaluate('(x)=>x.parentElement.open')
                for card in page.locator('.rate-card').all():
                    assert card.locator('time').is_visible()
                    assert card.locator('.quote-status').is_visible()
                for panel in page.locator('.edition-panel').all():
                    panel.locator('.sources-disclosure>summary').focus();page.keyboard.press('Enter')
                    assert panel.locator('.source-item').first.is_visible()
                    for times in panel.locator('.source-times').all():
                        assert times.is_visible() and 'Ανάκτηση' in times.inner_text()
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                if screenshots and width in [375,1440]:
                    page.locator('.rate-summary').screenshot(path=str(screenshots/f'{width}-expanded-rates.png'))
                    page.locator('.panel-weather').screenshot(path=str(screenshots/f'{width}-expanded-weather-sources.png'))
                checks.append(f'{width}px: keyboard rate and panel disclosures preserve visible reference times without overflow')
                page.locator('details').evaluate_all('(nodes)=>nodes.forEach(x=>x.open=false)')
                assert not page.locator('.hero-grid > .analysis-grid').count()
                expected_columns=3 if width>=1100 else 1
                for grid in page.locator('#cyprus .g3,#world .g3').all():
                    assert grid.evaluate('(x)=>getComputedStyle(x).gridTemplateColumns.split(" ").length')==expected_columns
                if width>=1100:
                    hero=page.locator('.hero').bounding_box()
                    assert hero['height']<620,hero
                    gap=page.locator('.hero .read-link').bounding_box()['y']-page.locator('.hero .abstract').bounding_box()['y']-page.locator('.hero .abstract').bounding_box()['height']
                    assert gap<150,('Unused lead space',gap)
                assert page.locator('#changes .update-card').count()>0
                assert page.locator('#changes .update-card h3').count()>0
                for panel in page.locator('.edition-panel').all():
                    assert panel.locator('details.sources-disclosure').count()==1
                assert page.locator('.calendar-list .calendar-event').count()>0
                checks.append(f'{width}px: article columns, compact lead actions, update cards and consistent panels passed')
                assert len(page.locator('#cyprus .newscard .story-content').first.inner_text().split())>45
                reader=page.locator('.hero .read-link').first
                reader.focus()
                assert reader.evaluate('(x)=>document.activeElement===x')
                assert urlsplit(reader.get_attribute('href')).path.endswith('/lead.html')
                assert page.url==base+'/'
                reader.evaluate('(x)=>x.blur()')
                if screenshots and width in [375,1440]:
                    screenshots.mkdir(parents=True,exist_ok=True)
                    page.evaluate('scrollTo(0,0)')
                    page.screenshot(path=str(screenshots/f'{width}-central-briefing.png'))
                    page.locator('.navs a[href="#cyprus"]').click()
                    page.screenshot(path=str(screenshots/f'{width}-large-news-cards.png'))
                if screenshots and width in [375,1440]:
                    style='.stickybar,.back-top,.skip-link{visibility:hidden!important}'
                    for selector,label in [('#changes','updates'),('.panel-tech','technology'),('.panel-weather','weather'),('.panel-calendar','calendar')]:
                        if page.locator(selector).count():page.locator(selector).first.screenshot(path=str(screenshots/f'{width}-{label}.png'),style=style)
                    page.locator('[data-theme-toggle]').click()
                    assert page.locator('html').get_attribute('data-theme')=='dark'
                    page.evaluate('scrollTo(0,0)')
                    page.screenshot(path=str(screenshots/f'{width}-dark-central.png'))
                    for selector,label in [('#changes','updates'),('.panel-weather','weather'),('.panel-calendar','calendar')]:
                        if page.locator(selector).count():page.locator(selector).first.screenshot(path=str(screenshots/f'{width}-dark-{label}.png'),style=style)
                    page.locator('[data-theme-toggle]').click()
                checks.append(f'{width}px: complete central briefing, compact lead, substantial previews, decoded photographs and separate reader')
            updated=BeautifulSoup(original,'html.parser')
            updated.find('meta',attrs={'name':'oracle-day-id'})['content']='2099-01-01'
            updated.find('meta',attrs={'name':'oracle-day-updated-at'})['content']='2099-01-01T19:30:00+02:00'
            updated.select_one('.hero .story-content > h2').string='Δοκιμαστική νεότερη δημοσιευμένη έκδοση'
            state['html']=str(updated)
            state['descriptor']=dict(descriptor,day_id='2099-01-01',updated_at='2099-01-01T19:30:00+02:00',html_sha256=hashlib.sha256(state['html'].encode()).hexdigest())
            page.goto(base+'/',wait_until='networkidle')
            page.wait_for_function('document.querySelector("meta[name=oracle-day-id]").content==="2099-01-01"')
            assert page.url==base+'/' and not page.locator('iframe').count()
            assert 'Δοκιμαστική' in page.locator('.hero .story-content > h2').inner_text()
            page.locator('[data-theme-toggle]').click();assert page.locator('html').get_attribute('data-theme')=='dark'
            checks.append('Next published edition replaces the whole page at the same address; controls still work')
            # Corrections to the same published edition also replace stale content.
            corrected=BeautifulSoup(original,'html.parser');corrected.select_one('.hero .story-content > h2').string='Δοκιμαστική διόρθωση της ίδιας έκδοσης'
            state['html']=str(corrected)
            state['descriptor']=dict(descriptor,html_sha256=hashlib.sha256(state['html'].encode()).hexdigest())
            page.goto(base+'/',wait_until='networkidle')
            page.wait_for_function('document.querySelector(".hero .story-content > h2").textContent.includes("Δοκιμαστική διόρθωση")')
            checks.append('A correction to the same edition refreshes its complete content')
            state['html']=original
            state['descriptor']=dict(descriptor,version='f'*64)
            page.goto(base+'/',wait_until='networkidle')
            page.wait_for_function('document.querySelector("link[rel=stylesheet]").href.startsWith("https://jodemon9.github.io/Claude-Briefing/")')
            checks.append('A styles-only update refreshes the central view even when article HTML is unchanged')
            for case in ['missing','hash','draft','html-fetch','asset-fetch','asset-hash','wrong-identity','older-day']:
                state['fail']=case=='missing'
                state['html']=original
                state['descriptor']=dict(descriptor,html_sha256='0'*64)
                if case=='draft':state['descriptor']['status']='draft'
                if case in ['html-fetch','asset-fetch','asset-hash','wrong-identity','older-day']:
                    state['descriptor']=dict(descriptor,version='f'*64)
                state['html_fail']=case=='html-fetch'
                state['asset_fail']=case=='asset-fetch'
                state['asset_hash']=case=='asset-hash'
                if case=='wrong-identity':state['descriptor']['day_id']='2099-01-02'
                if case=='older-day':state['descriptor']['day_id']='2000-01-01'
                page.goto(base+'/',wait_until='networkidle')
                page.wait_for_selector('#latest-status')
                assert page.locator('meta[name="oracle-day-id"]').get_attribute('content')==descriptor['day_id']
                assert page.locator('#cyprus .newscard').count()>0
                checks.append(case+': complete dated snapshot remains available')
            state.update(descriptor=descriptor,html=original,fail=False,html_fail=False,asset_fail=False,asset_hash=False)
            page.add_init_script('Object.defineProperty(window,"localStorage",{get(){throw Error("blocked")}})')
            page.goto(base+'/',wait_until='networkidle')
            page.locator('[data-theme-toggle]').click()
            assert page.locator('html').get_attribute('data-theme')=='dark'
            assert not errors,errors
            checks.append('Blocked browser storage preserves central reading and theme controls')
            nojs=browser.new_context(java_script_enabled=False,viewport={'width':375,'height':900})
            nojs.route('**/*',route)
            plain=nojs.new_page();plain.goto(base+'/',wait_until='networkidle')
            assert plain.locator('#cyprus .newscard').count()>0
            plain.locator('.all-quotes>summary').focus();plain.keyboard.press('Enter')
            assert plain.locator('.all-quotes').get_attribute('open') is not None
            plain.locator('.rate-disclosure>summary').focus();plain.keyboard.press('Enter')
            assert plain.locator('.rate-card time').first.is_visible()
            plain.locator('.panel-weather .sources-disclosure>summary').focus();plain.keyboard.press('Enter')
            assert plain.locator('.panel-weather .source-times').first.is_visible()
            assert not plain.evaluate('document.documentElement.scrollWidth>innerWidth+1')
            checks.append('JavaScript disabled: complete local newspaper and native market expansion work')
            browser.close()
    finally:server.shutdown();server.server_close()
    print('\n'.join(checks));print(f'{len(checks)} central browser checks passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);run(parser.parse_args().screenshots)
