import importlib.util
import json
import shutil
import tempfile
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('central_release',ROOT/'scripts/daily_release.py')
release=importlib.util.module_from_spec(spec);spec.loader.exec_module(release)

class DailyReleaseTests(unittest.TestCase):
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

if __name__=='__main__':unittest.main()
