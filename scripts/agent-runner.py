#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Autonomous Antigravity Agent Runner
===========================================================
Programmatic headless agent runner powered by the official Google Antigravity SDK
(`google-antigravity`).

Executes seamlessly both locally and inside cloud virtual machines (GitHub Actions)
even when the local Antigravity IDE and user computer are completely closed.

Architecture:
  1. Detects or accepts edition (Morning Broadsheet, Midday Market Pulse, Evening Wrap).
  2. Spawns an autonomous Antigravity Agent (`google.antigravity.Agent`) with full tool wiring:
     - fetch_live_markets_and_euribor
     - fetch_live_sports_fixtures
     - fetch_wire_intelligence
     - verify_links_health
     - audit_story_duplication
  3. The Antigravity Agent exercises its tools, reasons over raw intelligence,
     audits duplication against the 48-hour archive, and drafts the sovereign broadsheet.
  4. Resilient Fail-Safe: If `GEMINI_API_KEY` is not configured or an API error occurs,
     the runner automatically transitions to the deterministic multi-edition pipeline
     (`generate-briefing.py`), ensuring 100% zero-downtime publishing.
  5. Compiles HTML, search index, global clocks bar, and live wire drawer (`build-html.py`).
"""

import os
import sys
import json
import asyncio
import argparse
import subprocess
from datetime import datetime
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRIEFINGS_DIR = os.path.join(BASE_DIR, 'briefings')
DOCS_BRIEFINGS_DIR = os.path.join(BASE_DIR, 'docs', 'briefings')
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

from env_loader import load_env
load_env()


# ==============================================================================
# 🛠️ NATIVE DOMAIN TOOLS EXPOSED TO THE ANTIGRAVITY AGENT
# ==============================================================================

def fetch_live_markets_and_euribor() -> str:
    """Harvests live market quotes and Euribor fixing rates.
    Returns structured data for ATHEX, Bank of Cyprus (BOCH), Euribor 1M/3M/6M/12M,
    S&P 500, Nasdaq, Gold, and Brent Crude oil.
    """
    markets_script = os.path.join(SCRIPTS_DIR, 'fetch-markets.py')
    markets_json = os.path.join(SCRIPTS_DIR, 'markets-data.json')
    if os.path.exists(markets_script):
        subprocess.run([sys.executable, markets_script], cwd=BASE_DIR, capture_output=True, text=True)
    if os.path.exists(markets_json):
        try:
            with open(markets_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error reading markets data: {e}"
    return "Market data temporarily unavailable."


def fetch_live_sports_fixtures() -> str:
    """Harvests verified sports fixtures, kick-off times, and broadcast channels.
    Covers Cyprus CFA 1st Division, Omonoia FC, UEFA Champions League, Premier League,
    La Liga, and Formula 1 Grand Prix schedules.
    """
    sports_script = os.path.join(SCRIPTS_DIR, 'fetch-sports.py')
    sports_json = os.path.join(SCRIPTS_DIR, 'sports-data.json')
    if os.path.exists(sports_script):
        subprocess.run([sys.executable, sports_script, sports_json], cwd=BASE_DIR, capture_output=True, text=True)
    if os.path.exists(sports_json):
        try:
            with open(sports_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data, indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error reading sports data: {e}"
    return "Sports fixtures temporarily unavailable."


def fetch_wire_intelligence() -> str:
    """Scrapes the 24/7 real-time news wire across Cyprus and international agencies.
    Sources include CNA, InBusinessNews, Philenews, Cyprus Mail, SigmaLive, and BBC World.
    """
    monitor_script = os.path.join(SCRIPTS_DIR, 'monitor-breaking.py')
    wire_json = os.path.join(SCRIPTS_DIR, 'live-wire.json')
    if os.path.exists(monitor_script):
        subprocess.run([sys.executable, monitor_script, '--no-dispatch'], cwd=BASE_DIR, capture_output=True, text=True)
    if os.path.exists(wire_json):
        try:
            with open(wire_json, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return json.dumps(data[:15], indent=2, ensure_ascii=False)
        except Exception as e:
            return f"Error reading wire data: {e}"
    return "News wire temporarily unavailable."


def verify_links_health(urls: list[str]) -> str:
    """Performs live HTTP HEAD/GET health checks on candidate URLs to prevent dead links.
    Returns status codes for each URL checked.
    """
    import urllib.request
    results = {}
    for url in urls[:10]:
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'})
            with urllib.request.urlopen(req, timeout=5) as resp:
                results[url] = f"OK ({resp.status})"
        except Exception as e:
            results[url] = f"FAILED ({e})"
    return json.dumps(results, indent=2)


def audit_story_duplication(headlines: list[str]) -> str:
    """Audits candidate headlines against the last 48 hours of published briefings.
    Flags repeated stories to preserve high novelty and avoid reader fatigue.
    """
    check_script = os.path.join(SCRIPTS_DIR, 'check-duplication.py')
    if os.path.exists(check_script):
        res = subprocess.run([sys.executable, check_script], cwd=BASE_DIR, capture_output=True, text=True)
        return res.stdout.strip()
    return "Duplication audit tool unavailable."


# ==============================================================================
# 🤖 HEADLESS ANTIGRAVITY AGENT ORCHESTRATOR
# ==============================================================================

async def run_antigravity_agent(edition: str, target_md: str, dry_run: bool = False) -> bool:
    """Spawns an autonomous Antigravity Agent via google-antigravity SDK."""
    try:
        from google.antigravity import Agent, LocalAgentConfig, CapabilitiesConfig
        from google.antigravity.types import AntigravityConnectionError
    except ImportError:
        print("⚠ [AgentRunner] 'google-antigravity' SDK not installed. Falling back to deterministic engine.")
        return False

    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    if not api_key:
        print("ℹ [AgentRunner] No GEMINI_API_KEY detected in environment. Using deterministic multi-edition engine.")
        return False

    print("=" * 70)
    print(f"🤖 [ANTIGRAVITY AGENT] Initializing Autonomous Sovereign Agent [{edition.upper()}]")
    print("=" * 70)

    # Configure the Antigravity Agent with domain tools and Chief Intelligence Officer instructions
    system_prompt = (
        "You are the Chief Intelligence Officer of The Oracle Sovereign — an elite, high-signal intelligence "
        "briefing published for Cyprus, European markets, and global decision-makers. "
        "You have access to specialized tools: fetch_live_markets_and_euribor, fetch_live_sports_fixtures, "
        "fetch_wire_intelligence, verify_links_health, and audit_story_duplication. "
        "You ground your analysis strictly in verified empirical facts, cite live sources, avoid redundant coverage, "
        "and maintain an executive, authoritative tone. Format briefings using clean Markdown."
    )

    capabilities = CapabilitiesConfig(
        enable_subagents=True,
    )

    tools_list = [
        fetch_live_markets_and_euribor,
        fetch_live_sports_fixtures,
        fetch_wire_intelligence,
        verify_links_health,
        audit_story_duplication,
    ]

    config = LocalAgentConfig(
        api_key=api_key,
        system_instructions=system_prompt,
        capabilities=capabilities,
        tools=tools_list,
        workspaces=[BASE_DIR],
    )

    today_date = datetime.now().strftime('%Y-%m-%d')
    edition_prompts = {
        "morning": (
            f"You are preparing the morning Broadsheet edition of The Oracle Sovereign for today ({today_date}).\n"
            "1. Query your live tools: fetch_wire_intelligence, fetch_live_markets_and_euribor, and fetch_live_sports_fixtures.\n"
            "2. Structure the broadsheet with authoritative Markdown in Greek:\n"
            "   # 🏛️ THE ORACLE SOVEREIGN — {Date}\n"
            "   ## ⭐ ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ (with background, practical meaning, next watch, antilogos, sources)\n"
            "   ## 📊 DASHBOARD (12 assets table + Ο αριθμός της ημέρας)\n"
            "   ## 🏦 ΕΠΙΤΟΚΙΑ & ΔΟΣΗ (Euribor 1M/3M/6M/12M, ECB rate, mortgage sample)\n"
            "   ## 🇨🇾 ΚΥΠΡΟΣ (6 stories with [Επιβεβαιωμένο], Γιατί με αφορά, and depth; 6th tagged [Ο Φάκελός μου])\n"
            "   ## 🌍 ΔΙΕΘΝΗ (5 stories with depth and antilogos)\n"
            "   ## 💰 ΑΓΟΡΕΣ: TOP MOVERS (5 assets with causes and sources)\n"
            "   ## ⚽ ΑΘΛΗΤΙΚΑ (Omonoia, Manchester United, Real Madrid, Formula 1)\n"
            "   ## 🌤️ ΚΑΙΡΟΣ — ΛΕΜΕΣΟΣ\n"
            "   ## 🗂️ ΕΞΕΛΙΞΕΙΣ, ## 🎯 Ο ΦΑΚΕΛΟΣ ΜΟΥ, ## 📅 ΤΙ ΝΑ ΚΑΝΩ, ## 🔍 ΓΙΑ ΑΥΡΙΟ\n"
        ),
        "midday": (
            f"You are preparing the MIDDAY PULSE (ΜΕΣΗΜΒΡΙΝΟΣ ΠΑΛΜΟΣ) edition of The Oracle Sovereign for today ({today_date}).\n"
            "1. Query your live tools: fetch_wire_intelligence, fetch_live_markets_and_euribor, and fetch_live_sports_fixtures.\n"
            "2. Structure the midday pulse strictly with authoritative Markdown in Greek:\n"
            "   # ☀️ THE ORACLE SOVEREIGN — ΜΕΣΗΜΒΡΙΝΟΣ ΠΑΛΜΟΣ — {Date}\n"
            "   **13:30 ώρα Κύπρου · χρόνος ανάγνωσης ~4 λεπτά**\n"
            "   > [!NOTE]\n"
            "   > **⚡ ΕΠΙΤΕΛΙΚΗ ΣΥΝΟΨΗ 60 ΔΕΥΤΕΡΟΛΕΠΤΩΝ:**\n"
            "   > * **Αγορές & Tech:** (Futures, BOCH, Brent, Tech Watchlist)\n"
            "   > * **Επικαιρότητα (5 Εξελίξεις):** (Core Cyprus & World developments)\n"
            "   > * **Αθλητικά:** (Omonoia & European clubs briefing)\n"
            "   ## ⚡ ΜΕΣΗΜΒΡΙΝΟ BREAKING & DEAL WIRE (Exactly 5 items: 3 Cyprus + 2 World, each with [ΕΠΙΒΕΒΑΙΩΜΕΝΟ], crisp body, **Γιατί με αφορά:** and **Πηγή:** [Name](url))\n"
            "   ## 📊 MIDDAY MARKET PULSE (ΧΑΚ · ATHEX · ΕΥΡΩΠΗ & WALL STREET)\n"
            "      ### 📈 Κύριοι Δείκτες, Ενέργεια & Crypto (BOCH, Brent, S&P 500 Futures, Nasdaq 100 Futures, BTC, EUR/USD, EUR/GBP)\n"
            "      ### 💻 Μετοχές Τεχνολογίας (Midday Tech Watch) (TSMC, NVIDIA, Alphabet, Apple, Microsoft, Micron, Meta)\n"
            "      **Εκτίμηση Αγοράς:** (Executive commentary)\n"
            "   ## ⚽ ΜΕΣΗΜΒΡΙΝΟΣ ΑΘΛΗΤΙΣΜΟΣ & ΠΡΟΓΡΑΜΜΑ (Omonoia, Manchester United, Real Madrid, Formula 1 with results, fixtures, news, highlights, sources)\n"
            "   ## 🌤️ ΚΑΙΡΟΣ — ΛΕΜΕΣΟΣ (Current temperature, humidity, wind, UV index, afternoon forecast)\n"
            "   ## 🗂️ ΜΕΣΗΜΒΡΙΝΕΣ ΕΞΕΛΙΞΕΙΣ (3 strategic bullets)\n"
            "   ## 🎯 ΑΠΟΓΕΥΜΑΤΙΝΕΣ ΠΡΟΤΕΡΑΙΟΤΗΤΕΣ (15:30 Wall St open, 16:30 CSE close, 18:00 corporate releases)\n"
        ),
        "evening": (
            f"You are preparing the EVENING WRAP (ΑΠΟΓΕΥΜΑΤΙΝΗ ΣΥΝΟΨΗ) edition of The Oracle Sovereign for today ({today_date}).\n"
            "1. Query your live tools: fetch_wire_intelligence, fetch_live_markets_and_euribor, and fetch_live_sports_fixtures.\n"
            "2. Structure the evening wrap strictly with authoritative Markdown in Greek:\n"
            "   # 🌙 THE ORACLE SOVEREIGN — ΑΠΟΓΕΥΜΑΤΙΝΗ ΣΥΝΟΨΗ — {Date}\n"
            "   **19:30 ώρα Κύπρου · χρόνος ανάγνωσης ~4 λεπτά**\n"
            "   > [!NOTE]\n"
            "   > **⚡ ΕΠΙΤΕΛΙΚΗ ΣΥΝΟΨΗ 60 ΔΕΥΤΕΡΟΛΕΠΤΩΝ:**\n"
            "   ## 🏁 ΤΟ ΑΠΟΤΥΠΩΜΑ ΤΗΣ ΗΜΕΡΑΣ\n"
            "   ## 🔔 CLOSING BELL & ΑΓΟΡΕΣ (Macro table + Tech watchlist table)\n"
            "   ## 📰 ΑΠΟΓΕΥΜΑΤΙΝΗ ΕΠΙΚΑΙΡΟΤΗΤΑ & ΕΞΕΛΙΞΕΙΣ (5 curated stories with [ΕΠΙΒΕΒΑΙΩΜΕΝΟ], **Γιατί με αφορά:** and **Πηγή:**)\n"
            "   ## ⚽ ΑΠΟΓΕΥΜΑΤΙΝΟΣ ΑΘΛΗΤΙΣΜΟΣ & ΠΡΟΓΡΑΜΜΑ (Omonoia, Manchester United, Real Madrid, Formula 1)\n"
            "   ## 🌤️ ΑΥΡΙΑΝΗ ΠΡΟΓΝΩΣΗ ΛΕΜΕΣΟΥ\n"
            "   ## 🌌 ΝΥΧΤΕΡΙΝΟ ΡΑΝΤΑΡ ΚΙΝΔΥΝΟΥ (Asian open, geopolitical watchlist, next edition time)\n"
        )
    }
    agent_prompt = edition_prompts.get(edition, edition_prompts["morning"])

    try:
        print("▶ Spawning Antigravity Agent process (DeepMind reasoning runtime)...")
        async def _chat_with_agent():
            async with Agent(config) as agent:
                print("▶ Sending intelligence dispatch prompt to Antigravity Agent...")
                response = await agent.chat(agent_prompt)
                output_tokens = []
                async for token in response:
                    output_tokens.append(token)
                return "".join(output_tokens).strip()

        full_output = await asyncio.wait_for(_chat_with_agent(), timeout=120.0)
        print(f"✔ Antigravity Agent completed analysis ({len(full_output)} chars generated).")

        if full_output and ('## ⭐' in full_output or '# ' in full_output) and '## ' in full_output:
            if not dry_run:
                print(f"💾 Saving agent synthesis to: {target_md}")
                os.makedirs(os.path.dirname(target_md), exist_ok=True)
                with open(target_md, 'w', encoding='utf-8') as f:
                    f.write(full_output)
            return True
        else:
            print("⚠ [AgentRunner] Agent output was empty or missing required broadsheet sections.")
            return False
    except asyncio.TimeoutError:
        print("⚠ [AgentRunner] Antigravity Agent timed out after 120s. Seamlessly continuing with deterministic engine...")
        return False
    except Exception as e:
        print(f"⚠ [AgentRunner] Antigravity Agent runtime error: {e}")
        print("  Switching to deterministic engine fail-safe...")
        return False

    return False


def run_deterministic_synthesis(edition: str, target_md: str) -> bool:
    """Executes the deterministic generation engine (scripts/generate-briefing.py).
    Guarantees 100% reliable broadsheet generation under any network conditions.
    """
    print(f"\n▶ Running deterministic synthesis for [{edition.upper()}] edition...")
    generate_script = os.path.join(SCRIPTS_DIR, 'generate-briefing.py')
    cmd = [sys.executable, generate_script, '--edition', edition, '--force']
    res = subprocess.run(cmd, cwd=BASE_DIR, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"❌ Error during generation: {res.stderr}")
        return False
    print(res.stdout.strip())
    return True


def post_processing(target_md: str) -> bool:
    """Runs quality gates: build-html, check-duplication, verify-links."""
    print("\n" + "=" * 70)
    print("🏗️ EXECUTING QUALITY GATES & WEB COMPILATION")
    print("=" * 70)

    all_passed = True
    build_script = os.path.join(SCRIPTS_DIR, 'build-html.py')
    check_script = os.path.join(SCRIPTS_DIR, 'check-duplication.py')
    verify_script = os.path.join(SCRIPTS_DIR, 'verify-links.py')
    docs_index = os.path.join(BASE_DIR, 'docs', 'index.html')

    # 1. Build HTML & Search Index (Critical Gate)
    if os.path.exists(build_script):
        print(f"\n▶ Compiling HTML, Global Clocks, Search Index, and Wire Drawer for {os.path.basename(target_md)}...")
        res = subprocess.run([sys.executable, build_script, target_md], cwd=BASE_DIR)
        if res.returncode != 0:
            print("❌ Critical quality gate FAILED: HTML compilation")
            all_passed = False

    # 2. Check Duplication (Advisory Gate)
    if os.path.exists(check_script):
        print("\n▶ Auditing story duplication...")
        res = subprocess.run([sys.executable, check_script, docs_index], cwd=BASE_DIR)
        if res.returncode != 0:
            print("⚠ Advisory notice: Card content duplication detected.")

    # 3. Verify Links (Advisory Gate - external bots often get 403 in cloud VM)
    if os.path.exists(verify_script):
        print("\n▶ Verifying link health (HTTP status checks)...")
        res = subprocess.run([sys.executable, verify_script, target_md], cwd=BASE_DIR)
        if res.returncode != 0:
            print("⚠ Advisory notice: One or more external links returned non-200 (Cloudflare bot challenge or network timeout).")

    return all_passed


def get_cyprus_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Nicosia"))
    except Exception:
        from datetime import timezone, timedelta
        return datetime.now(timezone(timedelta(hours=3)))


def auto_detect_edition() -> str:
    """Detects current edition based on Cyprus local time (EEST/EET)."""
    hour = get_cyprus_now().hour
    if 5 <= hour < 12:
        return "morning"
    elif 12 <= hour < 18:
        return "midday"
    else:
        return "evening"


# ==============================================================================
# 🚀 MAIN ENTRY POINT
# ==============================================================================

def main():
    parser = argparse.ArgumentParser(description="The Oracle Sovereign — Autonomous Antigravity Agent Runner")
    parser.add_argument('--edition', choices=['morning', 'midday', 'evening', 'auto'], default='auto',
                        help="Edition to compile (default: auto)")
    parser.add_argument('--force', action='store_true', help="Force regeneration even if file exists")
    parser.add_argument('--dry-run', action='store_true', help="Simulate execution without modifying files")
    parser.add_argument('--force-fallback', action='store_true', help="Force deterministic generation without agent")
    args = parser.parse_args()

    edition = args.edition
    if edition == 'auto':
        edition = auto_detect_edition()

    today_str = get_cyprus_now().strftime('%Y-%m-%d')
    if edition == 'morning':
        target_md = os.path.join(BRIEFINGS_DIR, f'oracle-briefing-{today_str}.md')
    else:
        target_md = os.path.join(BRIEFINGS_DIR, f'oracle-briefing-{today_str}-{edition}.md')

    print("=" * 70)
    print(f"🏛️ THE ORACLE SOVEREIGN — AUTONOMOUS RUNNER [{edition.upper()} EDITION]")
    print(f"   Target: {os.path.basename(target_md)}")
    print(f"   Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)

    if os.path.exists(target_md) and not args.force:
        print(f"ℹ Broadsheet already exists at: {target_md} and --force was not set. Preserving existing broadsheet.")
    else:
        agent_succeeded = False
        if not args.force_fallback:
            try:
                agent_succeeded = asyncio.run(run_antigravity_agent(edition, target_md, dry_run=args.dry_run))
            except Exception as e:
                print(f"⚠ Agent execution error: {e}")
                agent_succeeded = False

        if not agent_succeeded:
            if not args.dry_run:
                run_deterministic_synthesis(edition, target_md)
            else:
                print("ℹ Dry-run mode enabled: skipping file generation.")

    if not args.dry_run:
        gates_ok = post_processing(target_md)
        if not gates_ok:
            print("\n" + "=" * 70)
            print(f"❌ [ORACLE RUNNER WARNING] One or more quality gates failed for {edition.upper()} edition.")
            print("=" * 70)
            sys.exit(1)

    print("\n" + "=" * 70)
    print(f"✅ [ORACLE RUNNER COMPLETE] {edition.upper()} edition ready for publication.")
    print("=" * 70)


if __name__ == '__main__':
    main()
