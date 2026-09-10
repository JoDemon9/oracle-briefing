import os
import sys
import re
import json
import html
import urllib.request
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from env_loader import load_env
load_env()

TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip().strip("'\"")
CHAT  = os.environ.get("TELEGRAM_CHAT_ID", "").strip().strip("'\"")
BASE  = os.environ.get("BRIEFING_BASE_URL", "https://jodemon9.github.io/oracle-briefing")

if TOKEN:
    masked_token = TOKEN[:6] + "..." + TOKEN[-4:] if len(TOKEN) > 10 else "***"
    print(f"ℹ Telegram Bot Token detected: {masked_token} (length: {len(TOKEN)})")
else:
    print("❌ TELEGRAM_BOT_TOKEN is empty or not found in environment.")

if CHAT:
    print(f"ℹ Telegram Chat ID detected: {CHAT}")
else:
    print("❌ TELEGRAM_CHAT_ID is empty or not found in environment.")

def get_cyprus_now():
    try:
        from zoneinfo import ZoneInfo
        return datetime.now(ZoneInfo("Asia/Nicosia"))
    except Exception:
        from datetime import timezone, timedelta
        return datetime.now(timezone(timedelta(hours=3)))

cy_now = get_cyprus_now()
cy_date_str = cy_now.strftime('%Y-%m-%d')
cy_hour = cy_now.hour

explicit_edition = None
target_file = None

args = sys.argv[1:]
i = 0
while i < len(args):
    a = args[i]
    if a == '--edition' and i + 1 < len(args):
        explicit_edition = args[i + 1].lower()
        i += 2
        continue
    elif a in ['morning', 'midday', 'evening']:
        explicit_edition = a.lower()
    elif os.path.isfile(a):
        target_file = a
    elif re.match(r'^\d{4}-\d{2}-\d{2}', a):
        cy_date_str = a
    i += 1

if target_file and os.path.isfile(target_file):
    md_path = target_file
    m = re.search(r'(\d{4}-\d{2}-\d{2})(?:-(morning|midday|evening))?', os.path.basename(target_file))
    if m:
        date_only = m.group(1)
        edition_detected = m.group(2)
        if edition_detected:
            edition_tag = f"-{edition_detected}"
        else:
            edition_tag = ""
    else:
        date_only = cy_date_str
        edition_tag = ""
else:
    date_only = cy_date_str
    if explicit_edition:
        edition_tag = f"-{explicit_edition}" if explicit_edition != "morning" else ""
    else:
        if 5 <= cy_hour < 12:
            edition_tag = ""
        elif 12 <= cy_hour < 18:
            edition_tag = "-midday"
        else:
            edition_tag = "-evening"

    candidates = [
        f"docs/briefings/{date_only}{edition_tag}.md",
        f"briefings/oracle-briefing-{date_only}{edition_tag}.md",
        f"docs/briefings/{date_only}.md",
        f"briefings/oracle-briefing-{date_only}.md"
    ]
    md_path = next((c for c in candidates if os.path.exists(c)), candidates[0])

edition_slug = f"{date_only}{edition_tag}"
print(f"ℹ Targeting briefing markdown: {md_path} (Edition slug: {edition_slug})")

if not TOKEN or not CHAT:
    if os.environ.get("GITHUB_ACTIONS"):
        print("❌ CRITICAL: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID is NOT set in GitHub Repository Secrets!")
        print("👉 Go to GitHub Repo -> Settings -> Secrets and variables -> Actions -> Secrets and add TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID.")
        sys.exit(1)
    else:
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

top_story_block = grab("## ⭐", "## 📊") or grab("## ⚡", "## 📊") or grab("## 🏁", "## 🔔") or grab("## 🏁", "---")
top_story = first_heading(top_story_block)
top_story_desc = ""
if top_story_block:
    for line in top_story_block.splitlines():
        line_clean = line.strip()
        if line_clean and not line_clean.startswith("#") and not line_clean.startswith("-") and not line_clean.startswith("*") and len(line_clean) > 25:
            top_story_desc = line_clean
            break

dash_block = grab("## 📊", "## 🏦") or grab("## 📊", "## 🎯") or grab("## 🔔", "## ⚽") or grab("## 🔔", "---")
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

sports_block = grab("## ⚽", "## 🌤️") or grab("## ⚽", "## 🌌") or grab("## ⚽", "---")
sports_summary = ""
if sports_block:
    m_om = re.search(r'\*\*ΟΜΟΝΟΙΑ:\*\*\s*(.+)', sports_block) or re.search(r'###\s+ΟΜΟΝΟΙΑ.*?\n\*\*Επόμενος αγώνας:\*\*\s*(.+)', sports_block)
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

is_evening = "-evening" in edition_slug or explicit_edition == "evening"
is_midday = "-midday" in edition_slug or explicit_edition == "midday"

if is_evening:
    header_text = f"🏛️ <b>THE ORACLE SOVEREIGN</b> — {date_only}\n🌙 <b>Night Debrief & Closing Bell</b> (19:30)"
elif is_midday:
    header_text = f"🏛️ <b>THE ORACLE SOVEREIGN</b> — {date_only}\n☀️ <b>Μεσημβρινός Παλμός</b> (13:30)"
else:
    header_text = f"🏛️ <b>THE ORACLE SOVEREIGN</b> — {date_only}"
    if edition_time:
        header_text += f"\n🕒 <i>{esc(edition_time)}</i>"

if top_story_desc and top_story and top_story_desc != top_story:
    clean_top_heading = re.sub(r'^[🏁⭐⚡]\s*', '', top_story).strip()
    if clean_top_heading in ['ΤΟ ΑΠΟΤΥΠΩΜΑ ΤΗΣ ΗΜΕΡΑΣ', 'ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ', 'ΕΚΤΑΚΤΗ ΕΠΙΚΑΙΡΟΤΗΤΑ']:
        top_story_content = esc(top_story_desc)
    else:
        top_story_content = f"<b>{esc(clean_top_heading)}</b>\n{esc(top_story_desc)}"
else:
    clean_top_heading = re.sub(r'^[🏁⭐⚡]\s*', '', top_story).strip()
    top_story_content = esc(clean_top_heading) or "—"

full_edition_url = f"{BASE}/briefings/{edition_slug}.html"

if is_evening:
    # 1. Evening News Headlines
    ev_news_block = grab("## 📰 ΑΠΟΓΕΥΜΑΤΙΝΗ ΕΠΙΚΑΙΡΟΤΗΤΑ", "## ⚽") or grab("## 📰", "## ⚽")
    ev_headlines = []
    if ev_news_block:
        for item in re.split(r'\n###\s+', ev_news_block)[1:]:
            lines = item.strip().splitlines()
            if lines:
                h = lines[0].strip()
                h = re.sub(r'\[(ΕΠΙΒΕΒΑΙΩΜΕΝΟ|ΕΞΕΛΙΣΣΟΜΕΝΟ)\]\s*', '', h)
                ev_headlines.append(f"• {esc(h)}")

    # 2. Sports fixtures
    sp_items = []
    if sports_block:
        m_om = re.search(r'###\s+.*?ΟΜΟΝΟΙΑ.*?\n([\s\S]*?)(?=###|\Z)', sports_block, re.I)
        if m_om:
            om_next = re.search(r'\*\*Επόμενος αγώνας:\*\*\s*(.+)', m_om.group(1))
            if om_next:
                sp_items.append(f"• ☘️ <b>Ομόνοια:</b> {esc(om_next.group(1).strip())}")
        m_mu = re.search(r'###\s+.*?MANCHESTER UNITED.*?\n([\s\S]*?)(?=###|\Z)', sports_block, re.I)
        if m_mu:
            mu_next = re.search(r'\*\*Επόμενος αγώνας:\*\*\s*(.+)', m_mu.group(1))
            if mu_next:
                sp_items.append(f"• 🔴 <b>Man Utd:</b> {esc(mu_next.group(1).strip())}")

    # 3. Night Radar
    nr_block = grab("## 🌌", "---") or grab("## 🌌", "")
    nr_items = []
    if nr_block:
        for l in nr_block.splitlines():
            lc = l.strip()
            if lc and (lc[0].isdigit() or lc.startswith('*') or lc.startswith('-')):
                cleaned = re.sub(r'^\d+\.\s*', '', lc)
                cleaned = re.sub(r'^[*\-]\s*', '', cleaned).strip()
                cleaned = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', cleaned)
                cleaned = cleaned.replace('*', '')
                if cleaned and cleaned not in ['--', '---']:
                    nr_items.append(f"• {cleaned}")

    msg_parts = [
        header_text,
        f"🏁 <b>Το Αποτύπωμα της Ημέρας</b>\n{top_story_content}"
    ]
    if ev_headlines:
        msg_parts.append("📰 <b>Απογευματινή Επικαιρότητα</b>\n" + "\n".join(ev_headlines[:3]))
    if dash_rows_str:
        msg_parts.append(f"🔔 <b>Closing Bell & Αγορές</b>\n{esc(dash_rows_str)}")
    if sp_items:
        msg_parts.append("⚽ <b>Αθλητικό Πρόγραμμα</b>\n" + "\n".join(sp_items))
    if nr_items:
        msg_parts.append("🌌 <b>Νυχτερινό Ραντάρ</b>\n" + "\n".join(nr_items[:3]))

elif is_midday:
    # Midday priorities
    prio_block = grab("## 🎯", "## 🏦") or grab("## 🎯", "---")
    prio_items = []
    if prio_block:
        for l in prio_block.splitlines():
            lc = l.strip()
            if lc and (lc.startswith('*') or lc.startswith('-') or lc[0].isdigit()):
                cleaned = re.sub(r'^\d+\.\s*', '', lc)
                cleaned = re.sub(r'^[*\-]\s*', '', cleaned).strip()
                if cleaned and cleaned not in ['--', '---']:
                    prio_items.append(f"• {esc(cleaned)}")

    msg_parts = [
        header_text,
        f"⚡ <b>Μεσημβρινή Έκτακτη Επικαιρότητα</b>\n{top_story_content}"
    ]
    if dash_rows_str:
        msg_parts.append(f"📊 <b>Αγορές & Τάσεις</b>\n{esc(dash_rows_str)}")
    if prio_items:
        msg_parts.append("🎯 <b>Απογευματινές Προτεραιότητες</b>\n" + "\n".join(prio_items[:3]))

else:
    # Morning Broadsheet
    msg_parts = [
        header_text,
        f"⭐ <b>Θέμα της ημέρας</b>\n{top_story_content}",
        f"📊 <b>Αγορές</b>\n{esc(dash_rows_str) or '—'}",
        f"🎯 <b>Ο φάκελός μου</b>\n{esc(my_file_str) or '—'}",
        f"📅 <b>Προθεσμίες</b>\n{esc(deadlines_str) or '—'}"
    ]
    if sports_summary:
        msg_parts.append(sports_summary)
    if weather_summary:
        msg_parts.append(weather_summary)

msg_parts.append(f'📖 <a href="{full_edition_url}">Πλήρης έκδοση</a>')
text = "\n\n".join(msg_parts)

if len(text) > 4000:
    text = text[:3900] + "\n…\n" + f'<a href="{full_edition_url}">Πλήρης έκδοση</a>'

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
                [{"text": "📖 Διαβάστε την Πλήρη Έκδοση", "url": full_edition_url}],
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
                print(f"✔ Στάλθηκε επιτυχώς το briefing {edition_slug} στο Telegram!")
            else:
                print("Error from Telegram API:", res)
                sys.exit(1)
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        print(f"❌ Failed to send message: HTTP {e.code}")
        if "chat not found" in err_body:
            print("👉 Απαιτείται ενέργεια: Ανοίξτε το bot στο Telegram (https://t.me/JohnBriefing_bot) και πατήστε 'START' μία φορά ώστε να επιτραπεί η αποστολή μηνυμάτων!")
        else:
            print("Telegram API Response:", err_body)
        sys.exit(1)
    except Exception as e:
        print("Failed to send message:", e)
        sys.exit(1)
else:
    print("Dry-run successful! When TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set, this message will be dispatched.")
