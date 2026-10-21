import importlib.util
from pathlib import Path
import unittest
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('portal_scope',ROOT/'scripts/check_scope.py')
scope=importlib.util.module_from_spec(spec);spec.loader.exec_module(scope)


class CheckScopeTests(unittest.TestCase):
    def test_missing_baseline_requires_maintenance_units(self):
        self.assertEqual(scope.classify(ROOT,None)['profile'],'maintenance')

    def test_snapshot_only_changes_keep_current_checks(self):
        with mock.patch.object(scope.subprocess,'check_output',return_value='docs/index.html\ndocs/data/release.json\n'):
            self.assertEqual(scope.classify(ROOT,'base')['profile'],'central')

    def test_wire_or_publisher_changes_require_full_regression(self):
        with mock.patch.object(scope.subprocess,'check_output',return_value='scripts/monitor-breaking.py\n'):
            self.assertEqual(scope.classify(ROOT,'base')['profile'],'maintenance')


if __name__=='__main__':unittest.main()
