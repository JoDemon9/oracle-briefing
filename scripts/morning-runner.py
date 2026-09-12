#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Morning Auto-Runner
Runs automatically upon opening/logging into PC:
1. Checks if today's edition was already produced and dispatched.
2. If not, generates today's briefing, builds HTML, verifies quality,
   sends the Telegram message, and pushes to GitHub Pages.
"""

import os
import sys
import json
import subprocess
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
GEN_SCRIPT = os.path.join(SCRIPTS_DIR, 'generate-briefing.py')
DAILY_RUN_SCRIPT = os.path.join(SCRIPTS_DIR, 'daily-run.py')
STATUS_FILE = os.path.join(BASE_DIR, 'briefings', '.last_run.json')


def is_already_done(today_str):
    if os.path.exists(STATUS_FILE):
        try:
            with open(STATUS_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if data.get('last_completed_date') == today_str and data.get('success'):
                    return True
        except Exception:
            pass
    return False


def mark_done(today_str):
    try:
        with open(STATUS_FILE, 'w', encoding='utf-8') as f:
            json.dump({
                'last_completed_date': today_str,
                'completed_at': datetime.now().isoformat(),
                'success': True
            }, f, indent=2)
    except Exception as e:
        print(f"Warning: Could not save status: {e}")


def run_command(cmd, desc):
    print(f"\n▶ {desc}...")
    res = subprocess.run(cmd, shell=True, cwd=BASE_DIR)
    if res.returncode != 0:
        print(f"❌ Error during {desc} (Exit code: {res.returncode})")
        return False
    print(f"✔ Completed: {desc}")
    return True


def main():
    today_str = datetime.now().strftime('%Y-%m-%d')
    force = '--force' in sys.argv

    print("=" * 65)
    print(f"🏛️ THE ORACLE SOVEREIGN — MORNING AUTO-RUNNER ({today_str})")
    print("=" * 65)

    if not force and is_already_done(today_str):
        print(f"✔ Today's edition ({today_str}) has ALREADY been generated & sent.")
        print("Nothing to do. Enjoy your day!")
        sys.exit(0)

    # 1. Generate Briefing Markdown (if needed)
    today_md = os.path.join(BASE_DIR, 'briefings', f'oracle-briefing-{today_str}.md')
    if not os.path.exists(today_md):
        if not run_command(f'python "{GEN_SCRIPT}"', "Generating today's news briefing"):
            print("Failed to generate today's briefing.")
            sys.exit(1)
    else:
        print(f"Briefing markdown already present: {today_md}")

    # 2. Execute Daily Pipeline (Build HTML, Quality Check, Git Push to GitHub Pages, Telegram Dispatch)
    if not run_command(f'python "{DAILY_RUN_SCRIPT}" "{today_md}" --edition morning', "Running Daily Pipeline"):
        print("Daily pipeline encountered an issue.")
        sys.exit(1)

    mark_done(today_str)

    print("\n" + "=" * 65)
    print("🎉 ALL MORNING TASKS COMPLETED SUCCESSFULLY!")
    print(f"📱 Check your Telegram for today's briefing ({today_str})!")
    print("=" * 65)


if __name__ == '__main__':
    main()
