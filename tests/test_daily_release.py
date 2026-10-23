import importlib.util
import json
import hashlib
import shutil
import tempfile
import unittest
from unittest import mock
from urllib.parse import urlsplit
import urllib.error
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('central_release',ROOT/'scripts/daily_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class DailyReleaseTests(unittest.TestCase):
    def object_fixture(self,root):
        docs=root/'docs';(docs/'data').mkdir(parents=True);(docs/'assets/snapshot-objects').mkdir(parents=True)
        raw=b'body{color:green}';identity=hashlib.sha256(raw).hexdigest();relative='assets/snapshot-objects/'+identity+'.css'
        (docs/relative).write_bytes(raw)
        (docs/'index.html').write_text('<html><head><meta name="oracle-day-id" content="2026-10-23"><link rel="stylesheet" href="'+relative+'"></head><body><main>Saved newspaper</main></body></html>',encoding='utf-8')
        snapshot=b'<html><main>Source newspaper</main></html>'
        (docs/'data/day-snapshot.html').write_bytes(snapshot)
        info={'day_id':'2026-10-23','version':'1'*64,'html_sha256':hashlib.sha256(snapshot).hexdigest(),'asset_sha256':{'https://jodemon9.github.io/Claude-Briefing/assets/test.css':identity}}
        (docs/'data/day-latest.json').write_text(json.dumps(info),encoding='utf-8')
        for name in ('days.json','editions.json','latest.json'):(docs/'data'/name).write_text('{}')
        (docs/'data/latest-snapshot.html').write_text('Saved edition');(docs/'assets/latest-briefing.js').write_text('/* loader */')
        return relative

    def test_content_addressed_objects_are_bound_to_reviewed_source_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);relative=self.object_fixture(root)
            self.assertIn(relative,release.record(root)['files'])
            (root/'docs'/relative).write_bytes(b'tampered stylesheet')
            with self.assertRaisesRegex(ValueError,'differs from reviewed'):release.record(root)

    def test_unknown_object_cannot_enter_the_snapshot_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);relative=self.object_fixture(root)
            info=root/'docs/data/day-latest.json';data=json.loads(info.read_text());data['asset_sha256']={};info.write_text(json.dumps(data))
            with self.assertRaisesRegex(ValueError,'differs from reviewed'):release.record(root)

    def test_receipt_is_reproducible_and_wire_is_independent(self):
        receipt=release.manifest()
        self.assertEqual(receipt,release.manifest())
        self.assertIn('index.html',receipt['files'])
        self.assertIn('data/day-latest.json',receipt['files'])
        self.assertNotIn('live-wire.json',receipt['files'])
        self.assertNotIn('wire-health.json',receipt['files'])
    def test_wrong_snapshot_hash_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT/'docs',root/'docs')
            (root/'docs/data/day-snapshot.html').write_text('wrong publication',encoding='utf-8')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):release.record(root)
    def test_wrong_day_identity_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT/'docs',root/'docs')
            p=root/'docs/index.html';text=p.read_text(encoding='utf-8').replace('name="oracle-day-id"','name="wrong-day-id"');p.write_text(text,encoding='utf-8')
            with self.assertRaises((ValueError,TypeError)):release.record(root)
    def test_modified_local_asset_cannot_receive_a_good_release_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT/'docs',root/'docs')
            names=release.manifest(root)['files']
            asset=next(name for name in names if name.endswith('.webp'))
            (root/'docs'/asset).write_bytes(b'corrupted local image')
            with self.assertRaisesRegex(ValueError,'differs from reviewed'):release.record(root)

    def test_verified_receipt_is_retained_when_a_later_check_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT/'docs',root/'docs');release.record(root)
            bad=set()
            def opener(request,**kwargs):
                name=urlsplit(request.full_url).path.removeprefix('/oracle-briefing/')
                response=mock.MagicMock();response.__enter__.return_value=response
                response.status=200;response.geturl.return_value=request.full_url
                response.read.return_value=b'bad' if name in bad else (root/'docs'/name).read_bytes()
                return response
            result=release.verify(root,opener=opener)
            self.assertEqual(result['status'],'verified')
            before=(root/'.work/daily-publication-check.json').read_bytes()
            bad.add('index.html')
            with self.assertRaisesRegex(ValueError,'does not serve'):release.verify(root,opener=opener)
            self.assertEqual(before,(root/'.work/daily-publication-check.json').read_bytes())

    def test_unreachable_release_has_bounded_retries(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);shutil.copytree(ROOT/'docs',root/'docs');release.record(root)
            opener=mock.Mock(side_effect=urllib.error.URLError('offline'))
            with mock.patch.object(release.time,'sleep'):
                with self.assertRaisesRegex(ValueError,'could not be reached'):release.verify(root,opener=opener)
            self.assertEqual(opener.call_count,3)
            self.assertFalse((root/'.work/daily-publication-check.json').exists())

if __name__=='__main__':unittest.main()
