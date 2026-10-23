"""Two current portal cases plus the exact saved release; no archive sweep."""
import argparse
import functools
import importlib.util
import json
from http.server import SimpleHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
import threading
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
CASES=((390,True),(1440,False))


class Quiet(SimpleHTTPRequestHandler):
    def log_message(self,*args):pass


def integrity(root):
    spec=importlib.util.spec_from_file_location('daily_release',Path(root)/'scripts/daily_release.py')
    release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)
    receipt=json.loads((Path(root)/'docs/data/release.json').read_text())
    if release.manifest(root)!=receipt:raise ValueError('Current portal differs from the reviewed release receipt')
    return receipt


def run(root=ROOT,screenshots=None):
    root=Path(root);receipt=integrity(root)
    expected=BeautifulSoup((root/'docs/data/day-snapshot.html').read_text(),'html.parser')
    headline=expected.select_one('.hero h2').get_text(strip=True)
    summary=expected.select_one('.hero .abstract').get_text(' ',strip=True)
    if screenshots:screenshots.mkdir(parents=True,exist_ok=True)
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(Quiet,directory=str(root/'docs')))
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}/'
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(headless=True,args=['--no-sandbox'])
            for width,js in CASES:
                context=browser.new_context(java_script_enabled=js,viewport={'width':width,'height':950},reduced_motion='reduce')
                # Test the saved public fallback without polling a remote live edition.
                context.route('**/*',lambda r:r.continue_() if r.request.url.startswith(base) else r.abort())
                page=context.new_page();errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                response=page.goto(base,wait_until='load')
                assert response and response.status==200
                assert page.locator('main').is_visible()
                assert page.locator('meta[name="oracle-day-id"]').get_attribute('content')==receipt['day_id']
                assert page.locator('.hero h2').inner_text()==headline
                finding=page.locator('.hero .story-findings')
                if finding.count():
                    initially_open=bool(page.locator('html[data-intelligence="1"]').count())
                    assert finding.evaluate('(x)=>x.open')==initially_open
                    toggle=finding.locator('summary');toggle.focus();page.keyboard.press('Enter')
                    if initially_open:page.keyboard.press('Enter')
                    assert finding.locator('.abstract').is_visible()
                    assert finding.locator('.abstract').inner_text()==summary
                    assert toggle.bounding_box()['height']>=44
                    toggle.click();assert not finding.locator('.abstract').is_visible()
                else:assert page.locator('.hero .abstract').inner_text()==summary
                if expected.select_one('.hero img'):
                    photo=page.locator('.hero img').first;photo.scroll_into_view_if_needed()
                    photo.evaluate('(x)=>x.decode()');assert photo.evaluate('(x)=>x.naturalWidth>0&&x.naturalHeight>0')
                assert not errors,errors
                assert not page.evaluate('document.documentElement.scrollWidth>innerWidth+1')
                if screenshots:page.screenshot(path=str(screenshots/f'{width}-current.png'))
                context.close()
            browser.close()
    finally:server.shutdown();server.server_close()
    if integrity(root)!=receipt:raise ValueError('Portal changed during preview')
    result={'status':'passed','checks':['integrity','preview'],'browser_cases':len(CASES),'release_id':receipt['release_id']}
    target=root/'.work/daily-check-report.json';target.parent.mkdir(exist_ok=True);target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result))


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screenshots',type=Path);args=parser.parse_args()
    run(screenshots=args.screenshots)
