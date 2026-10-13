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
    descriptor=json.loads((ROOT/'docs/data/latest.json').read_text(encoding='utf-8'))
    original=(ROOT/'docs/data/latest-snapshot.html').read_text(encoding='utf-8')
    state={'descriptor':descriptor,'html':original,'fail':False}
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(ROOT/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start()
    base=f'http://127.0.0.1:{server.server_port}'
    checks=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True)
            context=browser.new_context(reduced_motion='reduce')
            def route(r):
                url=r.request.url
                if url.startswith(base) or url.startswith('data:'):r.continue_()
                elif url.startswith(SOURCE+'data/latest.json'):
                    r.fulfill(status=404,body='missing') if state['fail'] else r.fulfill(json=state['descriptor'])
                elif url.startswith(SOURCE+'latest.html'):
                    r.fulfill(content_type='text/html',body=state['html'])
                elif url.startswith(SOURCE+'assets/'):
                    relative=urlsplit(url).path.removeprefix('/Claude-Briefing/')
                    path=ROOT/'docs/assets/latest-snapshot'/descriptor['version']/relative
                    r.fulfill(path=str(path)) if path.is_file() else r.abort()
                else:r.abort()
            context.route('**/*',route)
            page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
            for width in [320,375,390,1440]:
                page.set_viewport_size({'width':width,'height':1000})
                page.goto(base+'/',wait_until='networkidle')
                assert page.url==base+'/'
                assert not page.locator('iframe').count()
                assert page.locator('meta[name="oracle-edition-id"]').get_attribute('content')==descriptor['edition_id']
                assert page.locator('#cyprus .newscard').count()>0 and page.locator('#world .newscard').count()>0
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                photo=page.locator('.hero .lead-overview img').first
                assert photo.bounding_box()['height']<=201
                assert page.locator('.hero .story-content > h2').bounding_box()['y']<photo.bounding_box()['y']
                assert page.locator('.hero .story-more').count()==0
                assert page.locator('.hero .card-context').is_visible()
                assert len(page.locator('.hero .card-context').inner_text().split())>=110
                assert page.locator('.hero .read-link').get_attribute('href').startswith(SOURCE+'articles/')
                assert page.locator('.hero .lead-overview img').evaluate('(x)=>x.complete&&x.naturalWidth>0&&x.naturalHeight>0')
                assert not page.locator('.hero-grid > .analysis-grid').count()
                assert len(page.locator('#cyprus .newscard .story-content').first.inner_text().split())>45
                reader=page.locator('.hero .read-link').first
                reader.focus()
                assert reader.evaluate('(x)=>document.activeElement===x')
                assert reader.get_attribute('href').endswith('/lead.html')
                assert page.url==base+'/'
                if screenshots and width in [375,1440]:
                    screenshots.mkdir(parents=True,exist_ok=True)
                    page.evaluate('scrollTo(0,0)')
                    page.screenshot(path=str(screenshots/f'{width}-central-briefing.png'))
                    page.locator('.navs a[href="#cyprus"]').click()
                    page.screenshot(path=str(screenshots/f'{width}-large-news-cards.png'))
                checks.append(f'{width}px: complete central briefing, compact lead, substantial previews, decoded photographs and separate reader')
            updated=BeautifulSoup(original,'html.parser')
            updated.find('meta',attrs={'name':'oracle-edition-id'})['content']='2099-01-01-evening'
            updated.find('meta',attrs={'name':'oracle-published-at'})['content']='2099-01-01T19:30:00+02:00'
            updated.select_one('.hero .story-content > h2').string='Δοκιμαστική νεότερη δημοσιευμένη έκδοση'
            state['html']=str(updated)
            state['descriptor']=dict(descriptor,edition_id='2099-01-01-evening',published_at='2099-01-01T19:30:00+02:00',html_sha256=hashlib.sha256(state['html'].encode()).hexdigest())
            page.goto(base+'/',wait_until='networkidle')
            page.wait_for_function('document.querySelector("meta[name=oracle-edition-id]").content==="2099-01-01-evening"')
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
            for case in ['missing','hash','draft']:
                state['fail']=case=='missing'
                state['html']=original
                state['descriptor']=dict(descriptor,html_sha256='0'*64)
                if case=='draft':state['descriptor']['status']='draft'
                page.goto(base+'/',wait_until='networkidle')
                page.wait_for_selector('#latest-status')
                assert page.locator('meta[name="oracle-edition-id"]').get_attribute('content')==descriptor['edition_id']
                assert page.locator('#cyprus .newscard').count()>0
                checks.append(case+': complete dated snapshot remains available')
            state.update(descriptor=descriptor,html=original,fail=False)
            page.add_init_script('Object.defineProperty(window,"localStorage",{get(){throw Error("blocked")}})')
            page.goto(base+'/',wait_until='networkidle')
            page.locator('[data-theme-toggle]').click()
            assert page.locator('html').get_attribute('data-theme')=='dark'
            assert not errors,errors
            checks.append('Blocked browser storage preserves central reading and theme controls')
            browser.close()
    finally:server.shutdown();server.server_close()
    print('\n'.join(checks));print(f'{len(checks)} central browser checks passed')

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--screenshots',type=Path);run(parser.parse_args().screenshots)
