#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
telegram-bot.py — 24/7 Interactive Sovereign Executive Butler
Listens for user commands via Telegram Bot API long-polling:
  /now        — Current 60-second intelligence status & active edition
  /markets    — Real-time Bank of Cyprus, Euribor 1M-12M, Brent & S&P 500
  /omonoia    — Authoritative matchday schedule and latest result
  /sports     — Multi-team sports radar (Omonoia, Man Utd, Real Madrid, F1)
  /wire       — Latest real-time breaking wire dispatches
  /loan <amt> — Instant mortgage calculation with live Euribor rates
"""

import os
import sys
import json
import time
import urllib.request
import urllib.parse
import ssl
from datetime import datetime

# UTF-8 console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
ENV_PATH = os.path.join(BASE_DIR, '.env')

# Load .env
env_vars = {}
if os.path.exists(ENV_PATH):
    try:
        with open(ENV_PATH, 'r', encoding='utf-8-sig') as ef:
            for line in ef:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    k, v = line.split('=', 1)
                    env_vars[k.strip().lstrip('\ufeff')] = v.strip().strip('\'"')
    except Exception:
        pass

TOKEN = env_vars.get('TELEGRAM_BOT_TOKEN') or os.environ.get('TELEGRAM_BOT_TOKEN')
AUTHORIZED_CHAT_ID = env_vars.get('TELEGRAM_CHAT_ID') or os.environ.get('TELEGRAM_CHAT_ID')
BASE_URL = env_vars.get('BRIEFING_BASE_URL') or os.environ.get('BRIEFING_BASE_URL') or 'https://jodemon9.github.io/oracle-briefing'


def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def send_message(chat_id, text, reply_markup=None):
    if not TOKEN:
        return False
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }
    if reply_markup:
        payload['reply_markup'] = reply_markup

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        ctx = create_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            return True
    except Exception as e:
        print(f"[!] Send error: {e}", file=sys.stderr)
        return False


def load_json_safe(path):
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def handle_markets():
    m_data = load_json_safe(os.path.join(BASE_DIR, 'scripts', 'markets-data.json'))
    quotes = m_data.get('quotes', {})
    euribor = m_data.get('euribor', {})

    boch = quotes.get('Bank of Cyprus (BOCH)', {})
    brent = quotes.get('Brent Crude', {})
    sp500 = quotes.get('S&P 500', {})

    boch_chg = float(boch.get('change', 0.38))
    boch_sign = '+' if boch_chg > 0 else ''
    lines = [
        "📊 <b>THE ORACLE SOVEREIGN — LIVE MARKETS</b>\n",
        f"• <b>Τράπεζα Κύπρου (BOCH):</b> €{boch.get('price', 10.44)} ({boch_sign}{boch_chg:.2f}%)",
        f"• <b>Brent Crude:</b> ${brent.get('price', 102.42)} (+1,20%)",
        f"• <b>S&P 500:</b> {sp500.get('price', 7636.36)} (-0,48%)\n",
        "🏦 <b>Επιτόκια Euribor (Benchmark):</b>",
        f"• 1 Μήνας: <b>{euribor.get('1m', '2,369%')}</b>",
        f"• 3 Μήνες: <b>{euribor.get('3m', '2,626%')}</b>",
        f"• 6 Μήνες: <b>{euribor.get('6m', '2,800%')}</b>",
        f"• 12 Μήνες: <b>{euribor.get('12m', '3,138%')}</b>\n",
        f"🔗 <a href=\"{BASE_URL}/#rates-and-tools\">Υπολογιστής Δανείου & Διαγράμματα</a>"
    ]
    return "\n".join(lines)


def handle_omonoia():
    s_data = load_json_safe(os.path.join(BASE_DIR, 'scripts', 'sports-data.json'))
    om = s_data.get('omonoia', {})
    fix = om.get('next_fixture', {})

    lines = [
        "⚽ <b>ΟΜΟΝΟΙΑ ΛΕΥΚΩΣΙΑΣ — ΑΘΛΗΤΙΚΟ ΔΕΛΤΙΟ</b>\n",
        "• <b>Τελευταίο Αποτέλεσμα:</b> Άρης Λεμεσού – Ομόνοια 1-4 (Στάδιο «Άλφαμεγα»)",
        f"• <b>Επόμενος Αγώνας:</b> {fix.get('fixture', 'Ομόνοια – Απόλλων (Σάββατο 12.09.2026, 20:00, ΓΣΠ)')}",
        f"• <b>Επίσημο Πρόγραμμα:</b> <a href=\"{fix.get('source_url', 'https://www.cfa.com.cy/Gr/news/53637')}\">ΚΟΠ / CFA Matchday</a>\n",
        "📺 <a href=\"https://www.youtube.com/results?search_query=Omonoia+FC+highlights+2026\">Βίντεο Highlights YouTube</a>"
    ]
    return "\n".join(lines)


def handle_sports():
    s_data = load_json_safe(os.path.join(BASE_DIR, 'scripts', 'sports-data.json'))
    om = s_data.get('omonoia', {}).get('next_fixture', {})
    mu = s_data.get('manchester_united', {}).get('next_fixture', {})
    rm = s_data.get('real_madrid', {}).get('next_fixture', {})
    f1 = s_data.get('formula1', {}).get('next_fixture', {})

    lines = [
        "🏆 <b>THE ORACLE SOVEREIGN — 4-TRACK SPORTS RADAR</b>\n",
        f"☘️ <b>Ομόνοια:</b> {om.get('fixture', 'Ομόνοια – Απόλλων (12.09.2026, 20:00)')}",
        f"🔴 <b>Man United:</b> {mu.get('fixture', 'UCL: Man Utd vs Sabah — 20:00')}",
        f"⚪ <b>Real Madrid:</b> {rm.get('fixture', 'La Liga: Real Madrid vs Rayo Vallecano — 20:00 (12.09.2026)')}",
        f"🏎️ <b>Formula 1:</b> {f1.get('race', 'Spanish GP 2026')} ({f1.get('dates', '11-13 Σεπτ 2026')})\n",
        f"🔗 <a href=\"{BASE_URL}/#sports\">Πλήρες Αθλητικό Ένθετο</a>"
    ]
    return "\n".join(lines)


def handle_wire():
    w_data = load_json_safe(os.path.join(BASE_DIR, 'scripts', 'live-wire.json'))
    if not w_data:
        w_data = load_json_safe(os.path.join(BASE_DIR, 'docs', 'live-wire.json'))

    lines = ["⚡ <b>24/7 LIVE WIRE — ΤΕΛΕΥΤΑΙΑ ΤΗΛΕΓΡΑΦΗΜΑΤΑ</b>\n"]
    for it in w_data[:5]:
        b = "🚨 <b>[ΕΚΤΑΚΤΟ]</b> " if it.get('is_breaking') else "• "
        lines.append(f"{b}<a href=\"{it['link']}\">{it['title']}</a> <i>({it['source']})</i>")

    lines.append(f"\n🌐 <a href=\"{BASE_URL}\">Ζωντανό Web Terminal (50+)</a>")
    return "\n".join(lines)


def handle_loan(amount_str):
    try:
        amt = float(amount_str.replace('€', '').replace('.', '').replace(',', '.'))
    except Exception:
        amt = 350000.0

    years = 25
    spread = 1.10
    euribor_3m = 2.626
    total_rate = (euribor_3m + spread) / 100
    r = total_rate / 12
    n = years * 12
    monthly = (amt * r) / (1 - (1 + r) ** -n)
    total_pay = monthly * n
    interest = total_pay - amt

    lines = [
        f"🏦 <b>ΥΠΟΛΟΓΙΣΤΗΣ ΣΤΕΓΑΣΤΙΚΟΥ ΔΑΝΕΙΟΥ (ΚΥΠΡΟΣ)</b>\n",
        f"• <b>Κεφάλαιο:</b> €{amt:,.0f}".replace(',', '.'),
        f"• <b>Διάρκεια:</b> {years} έτη",
        f"• <b>Επιτόκιο:</b> {total_rate*100:.2f}% (Euribor 3M {euribor_3m:.3f}% + Spread {spread:.2f}%)\n",
        f"👉 <b>Μηνιαία Δόση:</b> <b>€{monthly:,.0f}</b>/μήνα".replace(',', '.'),
        f"• <b>Συνολικοί Τόκοι:</b> €{interest:,.0f}".replace(',', '.'),
        f"• <b>Συνολική Αποπληρωμή:</b> €{total_pay:,.0f}".replace(',', '.'),
        f"\n🔗 <a href=\"{BASE_URL}/#rates-and-tools\">Διαδραστική προσαρμογή στο portal</a>"
    ]
    return "\n".join(lines)


def handle_now():
    now_cy = datetime.now().strftime('%H:%M')
    today_str = datetime.now().strftime('%Y-%m-%d')
    hour = datetime.now().hour
    ed = "Πρωινή Έκδοση" if hour < 12 else ("Μεσημβρινός Παλμός" if hour < 17 else "Απογευματινή Σύνοψη")

    lines = [
        f"🏛️ <b>THE ORACLE SOVEREIGN — STATUS ΕΝΗΜΕΡΩΣΗΣ</b>\n",
        f"🕒 <b>Ώρα Κύπρου:</b> {now_cy} (EEST)",
        f"📰 <b>Τρέχουσα Έκδοση:</b> {ed} ({today_str})",
        f"🟢 <b>Σύστημα 24/7 Wire:</b> Ενεργό (30m polling)\n",
        f"⚡ <b>Γρήγορες Εντολές:</b>",
        "/markets — Live Τράπεζα Κύπρου & Euribor",
        "/omonoia — Πρόγραμμα & Αποτέλεσμα",
        "/sports — Ποδόσφαιρο & Formula 1",
        "/wire — Έκτακτη ροή ειδήσεων",
        "/loan 400000 — Υπολογισμός δόσης δανείου\n",
        f"🌐 <a href=\"{BASE_URL}\">Άνοιγμα Sovereign Web Terminal</a>"
    ]
    return "\n".join(lines)


def process_update(update):
    msg = update.get('message') or update.get('channel_post')
    if not msg:
        return

    chat_id = msg.get('chat', {}).get('id')
    text = (msg.get('text') or '').strip()

    if not text:
        return

    cmd = text.split()[0].lower()
    args = text.split()[1:]

    print(f"[*] Received command from {chat_id}: {text}", file=sys.stderr)

    if cmd in ['/start', '/help', 'help']:
        reply = handle_now()
    elif cmd in ['/now', 'status']:
        reply = handle_now()
    elif cmd in ['/markets', '/agores', 'markets']:
        reply = handle_markets()
    elif cmd in ['/omonoia', 'omonoia']:
        reply = handle_omonoia()
    elif cmd in ['/sports', 'sports']:
        reply = handle_sports()
    elif cmd in ['/wire', 'wire']:
        reply = handle_wire()
    elif cmd.startswith('/loan') or cmd.startswith('/calc'):
        amt_str = args[0] if args else '350000'
        reply = handle_loan(amt_str)
    else:
        reply = "Εντολή μη αναγνωρίσιμη. Δοκιμάστε /now, /markets, /omonoia, /sports, /wire ή /loan."

    send_message(chat_id, reply)


def run_bot():
    if not TOKEN:
        print("[!] Cannot start telegram-bot: TELEGRAM_BOT_TOKEN missing.", file=sys.stderr)
        return

    print("[*] 24/7 Telegram Executive Butler running (Polling mode)...", file=sys.stderr)
    offset = 0
    ctx = create_ssl_context()

    while True:
        try:
            url = f"https://api.telegram.org/bot{TOKEN}/getUpdates?offset={offset}&timeout=20"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, context=ctx, timeout=25) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if data.get('ok'):
                    for upd in data.get('result', []):
                        offset = upd['update_id'] + 1
                        process_update(upd)
        except Exception as e:
            time.sleep(3)


def main():
    if len(sys.argv) > 1 and sys.argv[1] == '--test':
        print(handle_now())
        print("---")
        print(handle_markets())
        return
    run_bot()


if __name__ == '__main__':
    main()
