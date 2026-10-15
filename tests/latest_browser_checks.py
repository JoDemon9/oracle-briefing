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
                for bar in page.locator('.article-actions').all():
                    boxes=[c.bounding_box() for c in bar.locator(':scope > details > summary,:scope > .story-actions > a').all()]
                    assert max(b['y'] for b in boxes)-min(b['y'] for b in boxes)<2
                    assert all(b['height']>=44 for b in boxes)
                assert page.locator('figure figcaption,.photo-credit').count()==0
                assert page.locator('.image-credits-link').count()==1
                assert page.locator('#opportunities').count()==1
                assert '04/11/2026 · 18:00 Κύπρου' in page.locator('#opportunities').inner_text()
                photo=page.locator('.hero .lead-overview img').first
                assert photo.bounding_box()['height']<=(281 if width>=700 else 191)
                assert page.locator('.hero .lead-copy > h2').bounding_box()['y']<photo.bounding_box()['y'] if width<700 else photo.bounding_box()['width']>350
                assert page.locator('.hero .story-more').count()==0
                assert page.locator('.hero .lead-analysis').evaluate('(x)=>x.tagName==="DETAILS"')
                assert not page.locator('.hero .card-context').is_visible()
                depth=page.locator('.hero .lead-analysis>summary');depth.focus();page.keyboard.press('Enter')
                assert page.locator('.hero .card-context').is_visible()
                assert 0<len(page.locator('.hero .card-context').inner_text().split())<=180
                depth.click()
                # DEC-005 supports both a useful full reader and an original-source link.
                expected_reader=BeautifulSoup(original,'html.parser').select_one('.hero .read-link')
                actual_reader=page.locator('.hero .read-link').first
                assert actual_reader.get_attribute('href')==expected_reader['href']
                if 'original-report' in expected_reader.get('class',[]):
                    assert page.locator('.hero .original-report').get_attribute('href').startswith('https://')
                else:
                    assert urlsplit(actual_reader.get_attribute('href')).path.startswith('/Claude-Briefing/articles/')
                    assert page.locator('.hero .original-report').count()==0
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
                for panel in page.locator('.edition-panel:not(.opportunities)').all():
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
                    assert not page.locator('.hero .card-context').is_visible()
                    assert page.locator('.hero .article-actions').bounding_box()['height']<=55
                assert page.locator('#changes .update-card').count()>0
                assert page.locator('#changes .update-card h3').count()>0
                evidence=page.locator('#changes .update-sources>summary').first
                assert evidence.bounding_box()['height']<61
                evidence.focus();page.keyboard.press('Enter')
                assert page.locator('#changes .update-origin').first.is_visible()
                assert page.locator('#changes .update-source-links a').count()>1
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                evidence.click()
                for panel in page.locator('.edition-panel:not(.opportunities)').all():
                    assert panel.locator('details.sources-disclosure').count()==1
                assert page.locator('.calendar-list .calendar-event').count()>0
                checks.append(f'{width}px: article columns, compact lead actions, update cards and consistent panels passed')
                assert len(page.locator('#cyprus .newscard .story-content').first.inner_text().split())>45
                first=page.locator('#cyprus .newscard').first
                # DEC-005 exposes the complete 30-second findings instead of a
                # shorter headline-like abstract; retain a bounded initial card.
                assert first.bounding_box()['height']<1300
                assert not first.locator('.card-context').is_visible()
                first.locator('.card-analysis>summary').focus();page.keyboard.press('Enter')
                assert first.locator('.card-context').is_visible()
                assert 0<len(first.locator('.card-context').inner_text().split())<=180
                first.locator('.card-analysis>summary').click()
                assert first.locator('.article-meta').count()==1
                assert first.locator('.story-history').count()==0
                assert page.locator('.hero figcaption,.hero .photo-credit').count()==0
                assert page.locator('.image-credits-link').get_attribute('href')==SOURCE+'photo-credits.html'
                if width<700:
                    assert page.locator('.masthead').bounding_box()['height']<90
                    assert page.locator('.stickybar').bounding_box()['height']<65
                    assert page.locator('.hero .lead-copy > h2').evaluate('(x)=>x.getBoundingClientRect().y+scrollY')<650
                    menu=page.locator('.section-menu>summary');menu.focus();page.keyboard.press('Enter')
                    assert page.locator('.section-menu-list a').count()>=10
                    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                    page.keyboard.press('Escape');assert not page.locator('.section-menu').evaluate('(x)=>x.open')
                assert page.locator('.market-summary>li').count()<=3
                assert page.locator('.market-overview>.market-note').count()==0
                checks.append(f'{width}px: content-first header, native menu, compact cards, combined evidence and licensed photo disclosures passed')
                reader=page.locator('.hero .read-link').first
                reader.focus()
                assert reader.evaluate('(x)=>document.activeElement===x')
                assert urlsplit(reader.get_attribute('href')).path==urlsplit(BeautifulSoup(original,'html.parser').select_one('.hero .read-link')['href']).path
                assert page.url==base+'/'
                reader.evaluate('(x)=>x.blur()')
                if screenshots and width in [375,1440]:
                    screenshots.mkdir(parents=True,exist_ok=True)
                    page.evaluate('scrollTo(0,0)')
                    page.screenshot(path=str(screenshots/f'{width}-central-briefing.png'))

                    if width<1100:
                        page.locator('.section-menu>summary').click()
                        page.locator('.section-menu-list a[href="#cyprus"]').click()
                        assert not page.locator('.section-menu').evaluate('(x)=>x.open')
                    else:page.locator('.navs a[href="#cyprus"]').click()
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
            updated.select_one('.hero .lead-copy > h2').string='Δοκιμαστική νεότερη δημοσιευμένη έκδοση'
            state['html']=str(updated)
            state['descriptor']=dict(descriptor,day_id='2099-01-01',updated_at='2099-01-01T19:30:00+02:00',html_sha256=hashlib.sha256(state['html'].encode()).hexdigest())
            page.goto(base+'/',wait_until='networkidle')
            page.wait_for_function('document.querySelector("meta[name=oracle-day-id]").content==="2099-01-01"')
            assert page.url==base+'/' and not page.locator('iframe').count()
            assert 'Δοκιμαστική' in page.locator('.hero .lead-copy > h2').inner_text()
            page.locator('[data-theme-toggle]').click();assert page.locator('html').get_attribute('data-theme')=='dark'
            checks.append('Next published edition replaces the whole page at the same address; controls still work')
            # Corrections to the same published edition also replace stale content.
            corrected=BeautifulSoup(original,'html.parser');corrected.select_one('.hero .lead-copy > h2').string='Δοκιμαστική διόρθωση της ίδιας έκδοσης'
            state['html']=str(corrected)
            state['descriptor']=dict(descriptor,html_sha256=hashlib.sha256(state['html'].encode()).hexdigest())
            page.goto(base+'/',wait_until='networkidle')
            page.wait_for_function('document.querySelector(".hero .lead-copy > h2").textContent.includes("Δοκιμαστική διόρθωση")')
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
            plain.locator('.section-menu>summary').focus();plain.keyboard.press('Enter')
            assert plain.locator('.section-menu-list a[href="#cyprus"]').is_visible()
            plain.locator('.section-menu>summary').click()
            plain.locator('#cyprus .card-analysis>summary').first.focus();plain.keyboard.press('Enter')
            assert plain.locator('#cyprus .card-context').first.is_visible()
            assert plain.locator('figure figcaption,.photo-credit').count()==0
            assert plain.locator('.image-credits-link').get_attribute('href')==SOURCE+'photo-credits.html'
            plain.locator('.opportunity-watch>summary').focus();plain.keyboard.press('Enter')
            assert plain.locator('#opportunity-cy-new-entrepreneurship-2024-call2').is_visible()
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
