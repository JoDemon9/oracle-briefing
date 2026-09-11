#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
catchup-briefings.py — Failsafe Catch-Up Engine
Ensures that if GitHub Actions or local schedulers experience delays or dropped crons,
any missing edition for today is automatically detected, compiled, and dispatched.
"""
import os
import sys
import subprocess
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
DOCS_BRIEFINGS = os.path.join(BASE_DIR, 'docs', 'briefings')

def get_cyprus_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Nicosia"))
    except Exception:
        from datetime import timezone, timedelta
        return datetime.now(timezone(timedelta(hours=3)))

def main():
    now = get_cyprus_now()
    today_str = now.strftime('%Y-%m-%d')
    hour = now.hour
    minute = now.minute

    missing_editions = []

    # Morning check (scheduled for 07:30 Cyprus time)
    # Check if past 07:35 and before 13:30
    if (hour > 7 or (hour == 7 and minute >= 35)) and hour < 13:
        morning_md = os.path.join(DOCS_BRIEFINGS, f"{today_str}.md")
        if not os.path.exists(morning_md):
            missing_editions.append("morning")

    # Midday check (scheduled for 13:30 Cyprus time)
    # Check if past 13:35 and before 19:30
    if (hour > 13 or (hour == 13 and minute >= 35)) and hour < 19:
        midday_md = os.path.join(DOCS_BRIEFINGS, f"{today_str}-midday.md")
        if not os.path.exists(midday_md):
            missing_editions.append("midday")

    # Evening check (scheduled for 19:30 Cyprus time)
    # Check if past 19:35
    if hour > 19 or (hour == 19 and minute >= 35):
        evening_md = os.path.join(DOCS_BRIEFINGS, f"{today_str}-evening.md")
        if not os.path.exists(evening_md):
            missing_editions.append("evening")

    if not missing_editions:
        print(f"✔ Catch-up check ({now.strftime('%H:%M')} Cyprus time): All scheduled editions are up to date.")
        return 0

    print(f"⚡ Catch-up check: Detected missing edition(s): {', '.join(missing_editions)}")
    for edition in missing_editions:
        print(f"\n▶ Executing catch-up dispatch for: [{edition.upper()}]...")
        runner = os.path.join(SCRIPTS_DIR, 'agent-runner.py')
        subprocess.run([sys.executable, runner, '--edition', edition], cwd=BASE_DIR)

        dispatcher = os.path.join(SCRIPTS_DIR, 'send-briefing.py')
        subprocess.run([sys.executable, dispatcher, '--edition', edition], cwd=BASE_DIR)

    return 0

if __name__ == '__main__':
    sys.exit(main())
