"""Hash and verify the central newspaper, without touching the independent Wire."""
import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import urlsplit
import urllib.request
from bs4 import BeautifulSoup

ROOT=Path(__file__).resolve().parents[1]
BASE='https://jodemon9.github.io/oracle-briefing/'

def digest(raw):
    return hashlib.sha256(raw).hexdigest()

def manifest(root=ROOT):
    docs=Path(root)/'docs'
    info=json.loads((docs/'data/day-latest.json').read_text())
    snapshot=(docs/'data/day-snapshot.html').read_bytes()
    if digest(snapshot)!=info['html_sha256']:
        raise ValueError('Day snapshot hash mismatch')
    doc=BeautifulSoup((docs/'index.html').read_text(),'html.parser')
    if doc.select_one('meta[name="oracle-day-id"]')['content']!=info['day_id']:
        raise ValueError('Central newspaper identity mismatch')
    names={'index.html','assets/latest-briefing.js','data/day-latest.json','data/day-snapshot.html','data/days.json','data/editions.json','data/latest.json','data/latest-snapshot.html'}
    for node in doc.select('link[href],script[src],img[src]'):
        value=node.get('href') or node.get('src')
        if value.startswith('assets/'):
            names.add(urlsplit(value).path)
    files={}
    expected_assets={urlsplit(url).path.removeprefix('/Claude-Briefing/'):sha for url,sha in info['asset_sha256'].items()}
    prefix='assets/latest-snapshot/'+info['version']+'/'
    for relative in sorted(names):
        p=(docs/relative).resolve()
        if not p.is_relative_to(docs.resolve()) or p.is_symlink() or p.suffix not in {'.html','.json','.css','.js','.webp'}:
            raise ValueError('Unsafe central release path')
        files[relative]=digest(p.read_bytes())
        if relative.startswith(prefix) and files[relative]!=expected_assets.get(relative.removeprefix(prefix)):
            raise ValueError('Central asset differs from reviewed day: '+relative)
    return {'schema_version':1,'day_id':info['day_id'],'release_id':digest(json.dumps(files,sort_keys=True).encode()),'files':files,'scope':'Central daily newspaper and compatibility descriptors; Wire remains independent.'}

def record(root=ROOT):
    receipt=manifest(root)
    (Path(root)/'docs/data/release.json').write_text(json.dumps(receipt,indent=2)+'\n')
    return receipt

def verify(root=ROOT):
    root=Path(root)
    receipt=json.loads((root/'docs/data/release.json').read_text())
    if manifest(root)!=receipt:
        raise ValueError('Central release receipt needs rebuilding')
    def check(relative):
        request=urllib.request.Request(BASE+relative+'?release='+receipt['release_id'],headers={'User-Agent':'OracleReleaseCheck/1.0','Cache-Control':'no-cache'})
        with urllib.request.urlopen(request,timeout=30) as response:
            if response.status!=200 or urlsplit(response.geturl()).hostname!='jodemon9.github.io':
                raise ValueError('Unexpected central publication destination')
            raw=response.read(10_000_001)
        expected=digest((root/'docs'/relative).read_bytes())
        if len(raw)>10_000_000 or digest(raw)!=expected:
            raise ValueError('Pages does not serve this central release: '+relative)
    from concurrent.futures import ThreadPoolExecutor
    names=['data/release.json',*receipt['files']]
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(check,names))
    result={'status':'verified','base_url':BASE,'day_id':receipt['day_id'],'release_id':receipt['release_id'],'checked_files':len(names)}
    output=root/'.work/daily-publication-check.json';output.parent.mkdir(exist_ok=True)
    output.write_text(json.dumps(result,indent=2)+'\n')
    return result

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify-live',action='store_true');args=parser.parse_args()
    print(json.dumps(verify() if args.verify_live else record()))
