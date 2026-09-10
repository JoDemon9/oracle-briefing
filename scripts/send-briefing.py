import os
import sys
import re
import json
import html
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# Automatically load .env file if present
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
env_file = os.path.join(BASE_DIR, '.env')
if os.path.exists(env_file):
    try:
        with open(env_file, 'r', encoding='utf-8-sig') as ef:
            for line in ef:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, v = line.split('=', 1)
                k = k.strip().lstrip('\ufeff')
                v = v.strip().strip('\'"')
                if k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
from datetime import datetime

CHAT  = os.environ.get("TELEGRAM_CHAT_ID")
BASE  = os.environ.get("BRIEFING_BASE_URL", "https://jodemon9.github.io/oracle-briefing")

arg = sys.argv[1] if len(sys.argv) > 1 else ""
if arg and os.path.isfile(arg):
    md_path = arg
    m = re.search(r'(\d{4}-\d{2}-\d{2}(?:-[a-zA-Z]+)?)', os.path.basename(arg))
    date = m.group(1) if m else datetime.now().strftime('%Y-%m-%d')
else:
    date = arg if arg else datetime.now().strftime('%Y-%m-%d')
    hour = datetime.now().hour
    edition_tag = '-evening' if hour >= 17 else ('-midday' if hour >= 12 else '')
    candidates = [
        f"docs/briefings/{date}{edition_tag}.md",
        f"briefings/oracle-briefing-{date}{edition_tag}.md",
        f"docs/briefings/{date}.md",
        f"briefings/oracle-briefing-{date}.md"
    ]
    md_path = next((c for c in candidates if os.path.exists(c)), candidates[0])

if not TOKEN or not CHAT:
    print("Warning: Missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID in environment.")
    print("Test run mode: parsing markdown and validating formatted message...")

with open(md_path, "r", encoding="utf-8") as f:
    md = f.read()

def grab(start, end):
    i = md.find(start)
    if i == -1:
        return ""
    j = md.find(end, i) if end else len(md)
    return md[i:len(md) if j == -1 else j]

def first_heading(block):
    m = re.search(r"^###\s+(.+)$", block, re.MULTILINE)
    if m:
        return m.group(1).strip()
    m = re.search(r"^##\s+(.+)$", block, re.MULTILINE)
    return m.group(1).strip() if m else ""

top_story_block = grab("## ⭐", "## 📊") or grab("## ⚡", "## 📊") or grab("## 🏁", "## 🔔")
top_story = first_heading(top_story_block)

dash_block = grab("## 📊", "## 🏦") or grab("## 📊", "## 🎯") or grab("## 🔔", "## ⚽")
dash_rows = []
for line in dash_block.split("\n"):
    if line.startswith("| **"):
        cols = [c.strip() for c in line.split("|") if c.strip()]
        if len(cols) >= 3:
            name = cols[0].replace("**", "")
            val = cols[1]
            chg = cols[2]
            dash_rows.append(f"• {name}: {val} ({chg})")
dash_rows_str = "\n".join(dash_rows[:6])

my_file_block = grab("## 🎯", "## 📅") or grab("## 🎯", "## ⚽") or grab("## 🎯", "---")
my_file = []
for line in my_file_block.split("\n"):
    if line.startswith("*   **") or (line.startswith("*   ") and "**" in line):
        cleaned = re.sub(r"^\*\s+\*\*", "", line).replace("**", "").split(":")[0].strip()
        my_file.append(f"• {cleaned}")
my_file_str = "\n".join(my_file[:2])

deadlines_block = grab("## 📅", "## 🔍")
deadlines = []
for line in deadlines_block.split("\n"):
    if line.startswith("*   **"):
        cleaned = re.sub(r"^\*\s+\*\*", "", line).replace("**", "")
        cleaned = re.sub(r"\(\[.*?\]\(.*?\)\)", "", cleaned).strip()
        cleaned = re.sub(r"\s+\.$", ".", cleaned)
        deadlines.append(f"• {cleaned}")
deadlines_str = "\n".join(deadlines[:3])

def esc(s):
    return html.escape(s, quote=False)

# Extract edition time/label if present
edition_time = ""
for l in md.splitlines()[:6]:
    m_ed = re.search(r'\*\*(\d{1,2}:\d{2}\s*ώρα Κύπρου.*?)\*\*', l.strip())
    if m_ed:
        edition_time = m_ed.group(1).strip()
        break

sports_block = grab("## ⚽", "## 🌤️")
sports_summary = ""
if "### ΟΜΟΝΟΙΑ" in sports_block:
    m_om = re.search(r'\*\*Επόμενος αγώνας:\*\*\s*(.+)', sports_block)
    if m_om:
        raw_om = m_om.group(1).strip()
        # Convert markdown links to HTML
        raw_om = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2">\1</a>', raw_om)
        raw_om = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', raw_om)
        sports_summary = f"⚽ <b>Αθλητικά:</b> {raw_om}"

weather_block = grab("## 🌤️", "## 🗂️")
weather_summary = ""
m_w = re.search(r'\*\*Θερμοκρασία:\*\*\s*(.+)', weather_block)
if m_w:
    clean_w = re.sub(r'\(\[.*?\]\(.*?\)\)', '', m_w.group(1)).strip()
    clean_w = re.sub(r'[*_]', '', clean_w).strip()
    weather_summary = f"🌤️ <b>Καιρός:</b> {esc(clean_w)}"

header_text = f"🏛️ <b>THE ORACLE SOVEREIGN</b> — {date}"
if edition_time:
    header_text += f"\n🕒 <i>{esc(edition_time)}</i>"

msg_parts = [
    header_text,
    f"⭐ <b>Θέμα της ημέρας</b>\n{esc(top_story)}",
    f"📊 <b>Αγορές</b>\n{esc(dash_rows_str)}",
    f"🎯 <b>Ο φάκελός μου</b>\n{esc(my_file_str) or '—'}",
    f"📅 <b>Προθεσμίες</b>\n{esc(deadlines_str) or '—'}"
]

if sports_summary:
    msg_parts.append(sports_summary)
if weather_summary:
    msg_parts.append(weather_summary)

msg_parts.append(f'📖 <a href="{BASE}/briefings/{date}.html">Πλήρης έκδοση</a>')

text = "\n\n".join(msg_parts)

if len(text) > 4000:
    text = text[:3900] + "\n…\n" + f'<a href="{BASE}/briefings/{date}.html">Πλήρης έκδοση</a>'

print("=" * 60)
print("FORMATTED TELEGRAM MESSAGE PREVIEW:")
print("=" * 60)
print(text)
print("=" * 60)

if TOKEN and CHAT:
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT,
        "text": text,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": False},
        "reply_markup": {
            "inline_keyboard": [
                [{"text": "📖 Διαβάστε την Πλήρη Έκδοση", "url": f"{BASE}/briefings/{date}.html"}],
                [{"text": "🏛️ Αρχική Πύλη (The Oracle)", "url": f"{BASE}/"}]
            ]
        },
        "disable_notification": False
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            if res.get("ok"):
                print(f"✔ Στάλθηκε επιτυχώς το briefing {date} στο Telegram!")
            else:
                print("Error from Telegram API:", res)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"❌ Failed to send message: HTTP {e.code}")
        if "chat not found" in err_body:
            print("👉 Απαιτείται ενέργεια: Ανοίξτε το bot στο Telegram (https://t.me/JohnBriefing_bot) και πατήστε 'START' μία φορά ώστε να επιτραπεί η αποστολή μηνυμάτων!")
        else:
            print("Telegram API Response:", err_body)
    except Exception as e:
        print("Failed to send message:", e)
else:
    print("Dry-run successful! When TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set, this message will be dispatched.")
