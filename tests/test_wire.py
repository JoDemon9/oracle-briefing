import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('wire', ROOT/'scripts/monitor-breaking.py')
wire = importlib.util.module_from_spec(spec)
spec.loader.exec_module(wire)


class WireTests(unittest.TestCase):
    def test_certificate_verification_is_enabled(self):
        context = wire.create_ssl_context()
        self.assertTrue(context.check_hostname)
        self.assertEqual(context.verify_mode, __import__('ssl').CERT_REQUIRED)

    def test_old_advertising_and_undated_pages_are_not_fresh_news(self):
        now = datetime(2026, 10, 12, 10, tzinfo=timezone.utc)
        self.assertFalse(wire.eligible({'title': 'Mobile App Advert', 'pub_date': now.isoformat()}, now))
        self.assertFalse(wire.eligible({'title': 'Βαθμολογία Α Κατηγορίας 2021-2022', 'pub_date': now.isoformat()}, now))
        self.assertFalse(wire.eligible({'title': 'News', 'pub_date': (now-timedelta(days=3)).isoformat()}, now))
        self.assertFalse(wire.eligible({'title': 'Undated', 'pub_date': ''}, now))
        self.assertTrue(wire.eligible({'title': 'Actual news', 'pub_date': 'Mon, 12 Oct 2026 09:30:00 GMT'}, now))

    def test_health_survives_provider_failure_without_claiming_success(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'wire-health.json'
            with mock.patch.object(wire, 'HEALTH_FILE', str(path)), mock.patch.dict(wire.PROVIDER_HEALTH, {'A': {'status': 'error', 'items': 0}}, clear=True):
                wire.write_health(0)
                result = json.loads(path.read_text(encoding='utf-8'))
                self.assertEqual(result['status'], 'failed')
                self.assertIsNone(result['last_success_at'])

    def test_all_failed_providers_fail_the_job(self):
        with mock.patch.object(wire, 'run_monitor'), mock.patch.dict(wire.PROVIDER_HEALTH, {'A': {'status': 'error'}}, clear=True):
            self.assertEqual(wire.main(), 1)

    def test_wire_does_not_have_telegram_dispatch(self):
        self.assertFalse(hasattr(wire, 'send_telegram_flash'))
        text = (ROOT/'.github/workflows/wire-monitor.yml').read_text(encoding='utf-8')
        self.assertNotIn('TELEGRAM_BOT_TOKEN', text)


if __name__ == '__main__':
    unittest.main()
