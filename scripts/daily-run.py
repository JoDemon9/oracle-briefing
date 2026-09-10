#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Daily Workflow Runner
Executes the full automated daily pipeline:
  1. Validates or detects today's briefing markdown
  2. Runs build-html.py (compiles index.html with images, loan calculator, live weather, and search index)
  3. Runs send-briefing.py (formats and dispatches the briefing to Telegram)
  4. Syncs docs/ for GitHub Pages deployment
"""

import os
import sys
import subprocess

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))

MARKETS_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'fetch-markets.py')
SPORTS_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'fetch-sports.py')
MONITOR_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'monitor-breaking.py')
GENERATE_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'generate-briefing.py')
VERIFY_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'verify-links.py')
BUILD_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'build-html.py')
CHECK_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'check-duplication.py')
SEND_SCRIPT = os.path.join(BASE_DIR, 'scripts', 'send-briefing.py')
DOCS_INDEX = os.path.join(BASE_DIR, 'docs', 'index.html')


def run_command(cmd, desc):
    print(f"\n▶ {desc}...")
    res = subprocess.run(cmd, shell=True)
    if res.returncode != 0:
        print(f"❌ Error during: {desc} (Exit code: {res.returncode})")
        return False
    print(f"✔ Completed: {desc}")
    return True


def main():
    import re
    from datetime import datetime

    edition = "morning"
    args = sys.argv[1:]
    target_md = ""

    i = 0
    while i < len(args):
        a = args[i]
        if a == '--edition' and i + 1 < len(args):
            edition = args[i + 1].lower()
            i += 2
            continue
        elif a in ['morning', 'midday', 'evening']:
            edition = a.lower()
        elif not a.startswith('-'):
            target_md = a
        i += 1

    # Auto-detect edition by current hour if none explicitly specified
    if not target_md and '--edition' not in args and not any(e in args for e in ['morning', 'midday', 'evening']):
        hour = datetime.now().hour
        if 5 <= hour < 12:
            edition = "morning"
        elif 12 <= hour < 17:
            edition = "midday"
        else:
            edition = "evening"

    today_str = datetime.now().strftime('%Y-%m-%d')
    if not target_md:
        if edition == 'morning':
            target_md = os.path.join(BASE_DIR, 'briefings', f'oracle-briefing-{today_str}.md')
        else:
            target_md = os.path.join(BASE_DIR, 'briefings', f'oracle-briefing-{today_str}-{edition}.md')

    print("=" * 65)
    print(f"🏛️ THE ORACLE SOVEREIGN — 24/7 PIPELINE [{edition.upper()} EDITION]")
    print("=" * 65)

    # -3. 24/7 Real-Time Wire Monitor (harvest fresh live feeds)
    if os.path.exists(MONITOR_SCRIPT):
        run_command(f'python "{MONITOR_SCRIPT}" --no-dispatch', "Polling 24/7 real-time news wire & breaking feeds")

    # -2. Live Markets & Euribor Harvester
    if os.path.exists(MARKETS_SCRIPT):
        if not run_command(f'python "{MARKETS_SCRIPT}"', "Harvesting live market quotes and Euribor rates"):
            print("   ⚠ Markets harvester warning — proceeding with cached data")

    # -1. Sports Data Harvester
    if os.path.exists(SPORTS_SCRIPT):
        sports_output = os.path.join(BASE_DIR, 'scripts', 'sports-data.json')
        sports_cmd = f'python "{SPORTS_SCRIPT}" "{sports_output}"'
        if not run_command(sports_cmd, "Harvesting live sports fixtures from CFA, BBC, Guardian, Marca, F1"):
            print("   ⚠ Sports harvester failed — continuing with manual data")

    # Ensure briefing exists; generate if missing
    if not os.path.exists(target_md):
        gen_cmd = f'python "{GENERATE_SCRIPT}" --edition {edition}'
        if not run_command(gen_cmd, f"Synthesizing {edition.upper()} edition briefing"):
            sys.exit(1)

    # 0. Mandatory Link Verification Gate (100% 200 OK Requirement)
    verify_cmd = f'python "{VERIFY_SCRIPT}" "{target_md}"'
    if not run_command(verify_cmd, f"Enforcing 100% link verification gate on {os.path.basename(target_md)}"):
        print("\n❌ PIPELINE HALTED: One or more links in the briefing are invalid or blocked.")
        print("   Fix all broken/unreachable URLs before deployment.")
        sys.exit(1)

    # 1. Build HTML & Search Index
    build_cmd = f'python "{BUILD_SCRIPT}" "{target_md}"'
    if not run_command(build_cmd, f"Building HTML portal & search index for {edition.upper()} edition"):
        sys.exit(1)

    # 2. Anti-Duplication Quality Verification
    check_cmd = f'python "{CHECK_SCRIPT}" "{DOCS_INDEX}"'
    if not run_command(check_cmd, "Verifying anti-duplication quality on web edition"):
        sys.exit(1)

    # 3. Sync to GitHub Pages FIRST
    m_d = re.search(r'(\d{4}-\d{2}-\d{2})', target_md)
    d_str = m_d.group(1) if m_d else today_str
    push_cmd = f'git add -A && git commit -m "feat: publish {edition} edition {d_str} [skip-ci-dispatch]" && git push'
    print("\n▶ Syncing live GitHub Pages before dispatching notification...")
    res_push = subprocess.run(push_cmd, shell=True, cwd=BASE_DIR)
    if res_push.returncode != 0:
        print("Note: git push status code", res_push.returncode, "(working tree may already be clean)")

    # 4. Telegram Dispatch (FINAL STEP)
    send_cmd = f'python "{SEND_SCRIPT}" "{target_md}"'
    if not run_command(send_cmd, f"Dispatching {edition.upper()} Briefing to Telegram (FINAL STEP)"):
        print("Note: Telegram dispatch finished with notice (check token configuration).")

    print("\n" + "=" * 65)
    print(f"🎉 24/7 PIPELINE COMPLETED SUCCESSFULLY FOR [{edition.upper()}]!")
    print("=" * 65)


if __name__ == '__main__':
    main()
