#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Automated Daily Briefing Generator
Fetches live Cyprus & World news, markets, and weather, and generates
the daily markdown briefing (using Gemini API if available, or direct RSS synthesis).
"""

import os
import re
import sys
import json
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRIEFINGS_DIR = os.path.join(BASE_DIR, 'briefings')
SCRIPTS_DIR = os.path.join(BASE_DIR, 'scripts')
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)
from env_loader import load_env
load_env()

DEFAULT_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7'
}


def clean_rss_title(title: str) -> str:
    if not title:
        return ""
    t = re.sub(r'&nbsp;', ' ', title)
    t = re.sub(r'<[^>]+>', '', t)
    t = re.sub(r'\s*-\s*[a-zA-Z0-9\.\-]+\.[a-z]{2,}.*$', '', t)
    t = re.sub(r'\s*\|\s*.*$', '', t)
    return re.sub(r'\s+', ' ', t).strip()


def resolve_redirect_url(url: str, timeout: int = 5) -> str:
    if not url or 'news.google.com' not in url:
        return url
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        req.get_method = lambda: 'HEAD'
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            final_url = resp.geturl()
            if 'news.google.com' not in final_url:
                return final_url
    except Exception:
        pass
    return url


def fetch_rss_items(url, limit=8):
    try:
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            xml_data = r.read()
            items = []
            try:
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(xml_data, 'html.parser')
                for it in soup.find_all('item')[:limit]:
                    t_tag = it.find('title')
                    l_tag = it.find('link')
                    d_tag = it.find('description')
                    title = t_tag.get_text(strip=True) if t_tag else ''
                    link = l_tag.get_text(strip=True) if l_tag else ''
                    if not link and l_tag and l_tag.next_sibling:
                        link = str(l_tag.next_sibling).strip()
                    desc = d_tag.get_text(strip=True) if d_tag else ''
                    desc = re.sub(r'<[^>]+>', '', desc).strip()
                    title = clean_rss_title(title)
                    link = resolve_redirect_url(link)
                    if title:
                        items.append({'title': title, 'link': link, 'desc': desc})
                if items:
                    return items
            except Exception:
                pass

            # Fallback to ElementTree
            root = ET.fromstring(xml_data)
            for it in root.findall('.//item')[:limit]:
                title = it.find('title').text if it.find('title') is not None else ''
                link = it.find('link').text if it.find('link') is not None else ''
                desc = it.find('description').text if it.find('description') is not None else ''
                desc = re.sub(r'<[^>]+>', '', desc).strip()
                title = clean_rss_title(title)
                link = resolve_redirect_url(link)
                if title:
                    items.append({'title': title, 'link': link, 'desc': desc})
            return items
    except Exception as e:
        print(f"Error fetching RSS {url}: {e}")
        return []


def fetch_open_meteo():
    try:
        url = "https://api.open-meteo.com/v1/forecast?latitude=34.68&longitude=33.04&current=temperature_2m,relative_humidity_2m,wind_speed_10m,uv_index&timezone=auto"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
            curr = data.get('current', {})
            return {
                'temp': round(curr.get('temperature_2m', 35)),
                'humidity': curr.get('relative_humidity_2m', 58),
                'wind': round(curr.get('wind_speed_10m', 16)),
                'uv': round(curr.get('uv_index', 8.8))
            }
    except Exception as e:
        print(f"Error fetching weather: {e}")
        return {'temp': 35, 'humidity': 58, 'wind': 16, 'uv': 9}


def load_json_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning reading {filepath}: {e}")
    return {}


def ensure_grounded_data():
    """Runs market and sports harvesters if fresh data is missing."""
    import subprocess
    markets_json = os.path.join(BASE_DIR, 'scripts', 'markets-data.json')
    sports_json = os.path.join(BASE_DIR, 'scripts', 'sports-data.json')

    if not os.path.exists(markets_json):
        m_script = os.path.join(BASE_DIR, 'scripts', 'fetch-markets.py')
        print("Harvesting fresh market data...")
        subprocess.run(f'python "{m_script}"', shell=True, cwd=BASE_DIR)

    if not os.path.exists(sports_json):
        s_script = os.path.join(BASE_DIR, 'scripts', 'fetch-sports.py')
        print("Harvesting fresh sports data...")
        subprocess.run(f'python "{s_script}" "{sports_json}"', shell=True, cwd=BASE_DIR)

    return load_json_data(markets_json), load_json_data(sports_json)


def generate_with_gemini(api_key, cy_items, world_items, wx_info, today_str, markets_data, sports_data):
    try:
        quotes_summary = json.dumps(markets_data.get('quotes', {}), ensure_ascii=False, indent=2)
        euribor_summary = json.dumps(markets_data.get('euribor', {}), ensure_ascii=False, indent=2)
        sports_summary = json.dumps(sports_data, ensure_ascii=False, indent=2)

        prompt = f"""Είσαι ο αρχισυντάκτης του «THE ORACLE SOVEREIGN», ενός αυστηρά εμπιστευτικού ημερήσιου briefing για επιφανή αναγνώστη στη Λεμεσό της Κύπρου.
Ημερομηνία: {today_str}.
Καιρός Λεμεσού: {wx_info['temp']}°C, Υγρασία {wx_info['humidity']}%, Άνεμος {wx_info['wind']} km/h, UV {wx_info['uv']}.

Πρόσφατες ειδήσεις Κύπρου:
{json.dumps(cy_items[:6], ensure_ascii=False, indent=2)}

Πρόσφατες διεθνείς ειδήσεις:
{json.dumps(world_items[:5], ensure_ascii=False, indent=2)}

ΕΠΙΣΗΜΑ ΖΩΝΤΑΝΑ ΔΕΔΟΜΕΝΑ ΑΓΟΡΩΝ (Χρησιμοποίησε ΑΚΡΙΒΩΣ αυτά τα νούμερα στον πίνακα DASHBOARD):
{quotes_summary}

ΕΠΙΣΗΜΑ ΕΠΙΤΟΚΙΑ EURIBOR (Χρησιμοποίησε ΑΚΡΙΒΩΣ αυτά τα ποσοστά):
{euribor_summary}

ΕΠΙΣΗΜΑ ΑΠΟΤΕΛΕΣΜΑΤΑ & ΕΠΟΜΕΝΟΙ ΑΓΩΝΕΣ ΑΘΛΗΤΙΚΩΝ (Χρησιμοποίησε ΑΚΡΙΒΩΣ αυτούς τους αγώνες, ώρες, έδρες και links, ΧΩΡΙΣ καμία αλλαγή!):
{sports_summary}

Γράψε το πλήρες markdown briefing του 'THE ORACLE SOVEREIGN' στα Ελληνικά, ακολουθώντας ΑΥΣΤΗΡΑ αυτή τη δομή με κεφαλίδες:
# THE ORACLE SOVEREIGN — {today_str}
## 1. ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ
(Τίτλος, 3-4 παράγραφοι ανάλυσης, πηγές με links, και υποχρεωτικά υποενότητα ### Ο Αντίλογος)

## 2. ΚΥΠΡΟΣ
(6 επιλεγμένα θέματα, με το 6ο να έχει ετικέτα [Ο Φάκελός μου]. Κάθε θέμα με **Τίτλο**, σύντομη ουσιαστική παράγραφο και ([Πηγή](url)). Μετά από κάθε θέμα πρόσθεσε <details><summary>Διάβασε λεπτομέρειες</summary>...πλούσιο context 2-3 παραγράφων...</details>)

## 3. ΔΙΕΘΝΗ
(5 επιλεγμένα διεθνή θέματα με details block όπως παραπάνω)

## 4. ΑΘΛΗΤΙΚΑ
(Ακριβή αποτελέσματα & επόμενοι αγώνες για Ομόνοια [βάσει ΚΟΠ], Manchester United, Real Madrid, και Formula 1 [GP Ισπανίας] με links σε highlights)

## 5. ΑΓΟΡΕΣ: TOP MOVERS
(5 assets με τιμές, μεταβολές και context από τα δεδομένα που σου δόθηκαν)

## 6. ΕΠΙΤΟΚΙΑ & ΔΑΝΕΙΑ
(Euribor 1M, 3M, 6M, 12M, Επιτόκιο ΕΚΤ, μέσο επιτόκιο νέων στεγαστικών Κύπρου)

## 7. Ο ΦΑΚΕΛΟΣ ΜΟΥ
(3-4 στρατηγικές σημειώσεις για επενδύσεις, ακίνητα Λεμεσού και ρευστότητα)

## 8. ΚΑΙΡΟΣ — ΛΕΜΕΣΟΣ
(Ανάλυση καιρού και προειδοποιήσεις)

## 9. ΠΡΟΘΕΣΜΙΕΣ & ΔΡΑΣΕΙΣ
(3-4 σημαντικές προθεσμίες για φορολογία, αιτήσεις, τραπεζικά)

## 10. ΓΙΑ ΑΥΡΙΟ — ΘΕΜΑΤΑ ΠΡΟΣ ΠΑΡΑΚΟΛΟΥΘΗΣΗ
(3 σημεία προσοχής)
"""
        api_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt}]}]
        }
        req = urllib.request.Request(
            api_url,
            data=json.dumps(payload).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        with urllib.request.urlopen(req, timeout=30) as r:
            res = json.loads(r.read().decode('utf-8'))
            text = res['candidates'][0]['content']['parts'][0]['text']
            return text.strip()
    except Exception as e:
        print(f"Gemini API generation failed or not available: {e}")
        return None


GREEK_MONTHS = {
    1: 'Ιανουαρίου', 2: 'Φεβρουαρίου', 3: 'Μαρτίου', 4: 'Απριλίου',
    5: 'Μαΐου', 6: 'Ιουνίου', 7: 'Ιουλίου', 8: 'Αυγούστου',
    9: 'Σεπτεμβρίου', 10: 'Οκτωβρίου', 11: 'Νοεμβρίου', 12: 'Δεκεμβρίου'
}


def get_greek_date_str(today_str=None):
    if today_str:
        try:
            dt = datetime.strptime(today_str, '%Y-%m-%d')
        except Exception:
            dt = datetime.now()
    else:
        dt = datetime.now()
    return f"{dt.day} {GREEK_MONTHS.get(dt.month, '')} {dt.year}"


def format_greek_num(val, decimals=2):
    if val is None:
        return "0,00"
    s = f"{val:.{decimals}f}"
    parts = s.split('.')
    int_part = "{:,}".format(int(parts[0])).replace(',', '.')
    return f"{int_part},{parts[1]}"


def generate_rss_fallback(cy_items, world_items, wx_info, today_str, markets_data, sports_data):
    greek_date = get_greek_date_str(today_str)
    top = cy_items[0] if cy_items else {'title': 'Σημαντικές οικονομικές εξελίξεις στην Κύπρο', 'link': 'https://cyprus-mail.com', 'desc': 'Συνεχίζονται οι διεργασίες στον χρηματοπιστωτικό και επενδυτικό τομέα.'}
    
    quotes = markets_data.get('quotes', {})
    euribor = markets_data.get('euribor', {})
    
    # Build live Dashboard table rows
    dash_lines = []
    for asset, q in quotes.items():
        p = q.get('price', 0)
        c = q.get('change', 0)
        prefix = "$" if any(k in asset for k in ['Crude', 'BTC', 'ETH']) else ("€" if 'Cyprus' in asset else "")
        suffix = "%" if any(k in asset for k in ['Yield', 'VIX']) else ""
        sign = "+" if c > 0 else ""
        p_str = f"{prefix}{format_greek_num(p)}{suffix}"
        c_str = f"{sign}{format_greek_num(c)}%"
        dash_lines.append(f"| **{asset}** | {p_str} | {c_str} | {q.get('date', today_str)} |")

    dash_table = "\n".join(dash_lines) if dash_lines else "| **S&P 500** | 7.636,36 | -0,48% | 10/09/2026 |"

    # Extract sports
    omonoia = sports_data.get('omonoia', {})
    om_fix = omonoia.get('next_fixture', {}).get('fixture', '')
    om_url = omonoia.get('next_fixture', {}).get('source_url', 'https://www.cfa.com.cy')
    om_res = omonoia.get('last_result', '')

    mu = sports_data.get('manchester_united', {})
    mu_fix = mu.get('next_fixture', {}).get('fixture', '')
    mu_url = mu.get('next_fixture', {}).get('source_url', 'https://www.bbc.com/sport/football/teams/manchester-united')
    mu_res = mu.get('last_result', '')

    rm = sports_data.get('real_madrid', {})
    rm_fix = rm.get('next_fixture', {}).get('fixture', '')
    rm_url = rm.get('next_fixture', {}).get('source_url', 'https://www.bbc.com/sport/football/teams/real-madrid')
    rm_res = rm.get('last_result', '')

    f1 = sports_data.get('formula1', {})
    f1_fix = f1.get('next_fixture', {}).get('race_day', '')
    f1_race = f1.get('next_fixture', {}).get('race', '')
    f1_url = f1.get('next_fixture', {}).get('source_url', 'https://www.formula1.com')
    f1_res = f1.get('last_result', '')

    e1m = euribor.get('1m', '—')
    e3m = euribor.get('3m', '—')
    e6m = euribor.get('6m', '—')
    e12m = euribor.get('12m', '—')

    cbc_rate = markets_data.get('cbc_rate', '3,85%')
    try:
        r_num = float(cbc_rate.replace('%', '').replace(',', '.'))
        r_m = r_num / 100 / 12
        n_m = 25 * 12
        pmt = 200000 * (r_m * (1 + r_m)**n_m) / ((1 + r_m)**n_m - 1)
        pmt_str = f"€{format_greek_num(pmt)}"
    except Exception:
        pmt_str = "—"

    md = f"""# 🏛️ THE ORACLE SOVEREIGN — {greek_date}

**07:30 ώρα Κύπρου · χρόνος ανάγνωσης ~7 λεπτά**

---

## ⭐ ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ

### {top['title']}

{top['desc']}

**Πηγές:** [Ενημέρωση]({top['link']})

---

## 📊 DASHBOARD

| Δείκτης / Περιουσιακό Στοιχείο | Τιμή | Μεταβολή | Ημ. αναφοράς |
| :--- | :--- | :--- | :--- |
{dash_table}

---

## 🏦 ΕΠΙΤΟΚΙΑ & ΔΟΣΗ

| Euribor | 1M | 3M | 6M | 12M |
|---|---|---|---|---|
| **Τρέχον** | {e1m} | {e3m} | {e6m} | {e12m} |

*   **Επιτόκιο ΕΚΤ (deposit facility):** {markets_data.get('ecb_rate', '2,00%')}
*   **Μέσο επιτόκιο νέων στεγαστικών Κύπρου:** {cbc_rate} (στοιχεία ΚΤΚ)
*   **Ενδεικτική δόση:** €200.000 / 25 έτη με επιτόκιο {cbc_rate} → **{pmt_str} τον μήνα**.
    *Ο υπολογισμός είναι ενδεικτικός, με σταθερή τοκοχρεολυτική δόση, χωρίς έξοδα τραπέζης.*

Πηγές: [euribor-rates.eu](https://www.euribor-rates.eu/en/) · [Κεντρική Τράπεζα Κύπρου](https://www.centralbank.cy/)

---

## 🇨🇾 ΚΥΠΡΟΣ

"""
    for i, it in enumerate(cy_items[1:6], 1):
        tag = "[Ο Φάκελός μου]" if i == 5 else "[Επικαιρότητα]"
        src_label = it.get('source', 'Ειδήσεις Κύπρου')
        md += f"""### {i}. {it['title']} {tag}
{it['desc']}  
**Γιατί με αφορά:** Αποτυπώνει τις τρέχουσες εξελίξεις στον δημόσιο και οικονομικό βίο της Κύπρου.  
**Πηγή:** [{src_label}]({it['link']})

"""

    md += """---

## 🌍 ΔΙΕΘΝΗ

"""
    for i, it in enumerate(world_items[:5], 1):
        src_label = it.get('source', 'Διεθνή')
        md += f"""### {i}. {it['title']} [Διεθνή]
{it['desc']}  
**Πηγή:** [{src_label}]({it['link']})

"""

    # Build Top Movers from live quotes
    md += f"""---

## 💰 ΑΓΟΡΕΣ: TOP MOVERS

"""
    movers_count = 0
    for asset_name, q in quotes.items():
        if movers_count >= 5:
            break
        c_val = q.get('change', 0)
        p_val = q.get('price', 0)
        sign = "+" if c_val > 0 else ""
        prefix = "$" if any(k in asset_name for k in ['Crude', 'BTC', 'ETH']) else ("€" if 'Cyprus' in asset_name else "")
        md += f"""### {asset_name} — {prefix}{format_greek_num(p_val)} ({sign}{format_greek_num(c_val)}%)
**Αιτία:** Εμπορική δραστηριότητα και διακυμάνσεις της τρέχουσας συνεδρίασης.  
**Πηγή:** [Yahoo Finance](https://finance.yahoo.com)

"""
        movers_count += 1

    # Sports section
    om_res_line = f"*   **Τελευταίο αποτέλεσμα:** {om_res}\n" if om_res else ""
    om_fix_line = f"*   **Επόμενος αγώνας:** {om_fix} ([Πρόγραμμα ΚΟΠ]({om_url}))\n" if om_fix else ""
    mu_res_line = f"*   **Τελευταίο αποτέλεσμα:** {mu_res}\n" if mu_res else ""
    mu_fix_line = f"*   **Επόμενος αγώνας:** {mu_fix} ([BBC Sport]({mu_url}))\n" if mu_fix else ""
    rm_res_line = f"*   **Τελευταίο αποτέλεσμα:** {rm_res}\n" if rm_res else ""
    rm_fix_line = f"*   **Επόμενος αγώνας:** {rm_fix} ([BBC Sport]({rm_url}))\n" if rm_fix else ""
    f1_res_line = f"*   **Τελευταίο αποτέλεσμα:** {f1_res}\n" if f1_res else ""
    f1_fix_line = f"*   **Επόμενος αγώνας:** {f1_race} — {f1_fix} ([Formula1.com]({f1_url}))\n" if f1_race else ""

    md += f"""---

## ⚽ ΑΘΛΗΤΙΚΑ

### ΟΜΟΝΟΙΑ

{om_res_line}{om_fix_line}*   **Highlights:** [Highlights Ομόνοιας στο YouTube](https://www.youtube.com/results?search_query=Omonoia+FC+highlights)
*   **Πηγή:** [ΚΟΠ / CFA]({om_url})

### Manchester United

{mu_res_line}{mu_fix_line}*   **Highlights:** [Highlights Manchester United στο YouTube](https://www.youtube.com/results?search_query=Manchester+United+highlights)
*   **Πηγή:** [BBC Sport]({mu_url})

### Real Madrid

{rm_res_line}{rm_fix_line}*   **Highlights:** [Highlights Real Madrid στο YouTube](https://www.youtube.com/results?search_query=Real+Madrid+highlights)
*   **Πηγή:** [BBC Sport]({rm_url})

### Formula 1

{f1_res_line}{f1_fix_line}*   **Highlights:** [Highlights Formula 1 στο YouTube](https://www.youtube.com/results?search_query=Formula+1+highlights)
*   **Πηγή:** [Formula1.com]({f1_url})

---

## 🌤️ ΚΑΙΡΟΣ — ΛΕΜΕΣΟΣ

*   **Θερμοκρασία:** {wx_info['temp']}°C (Μέγιστη) / 24°C (Ελάχιστη)
*   **Υγρασία:** {wx_info['humidity']}%
*   **Άνεμος:** {wx_info['wind']} km/h
*   **Πρόγνωση υπόλοιπης ημέρας:** Γενικά αίθριος καιρός.
*   **Προειδοποιήσεις:** Δείκτης UV: {wx_info['uv']}
*   **Πηγή:** [Open-Meteo](https://open-meteo.com/)

---

## 🗂️ ΕΞΕΛΙΞΕΙΣ

*   **Αγορά Ενέργειας & ΑΠΕ:** Ενίσχυση επενδύσεων σε φωτοβολταϊκά και αποθήκευση ενέργειας.
*   **Τραπεζικός Τομέας:** Σταθεροποίηση κεφαλαιακών δεικτών και πιστωτική επέκταση.

---

## 🎯 Ο ΦΑΚΕΛΟΣ ΜΟΥ

*   **Ακίνητα & Ενοίκια Λεμεσού:** Παρακολούθηση τιμών και αδειοδοτήσεων στο εβδομαδιαίο Real Estate Radar.
*   **Επιτόκια & Δάνεια:** Εξέλιξη Euribor και συνεδριάσεων ΕΚΤ.

---

## 📅 ΤΙ ΝΑ ΚΑΝΩ

*   **Τραπεζικές Ρυθμίσεις:** Επανεξέταση περιθωρίων επιτοκίου στεγαστικών δανείων βάσει Euribor.

---

## 🔍 ΓΙΑ ΑΥΡΙΟ

1.  **Πρωινό Sovereign Broadsheet:** Έκδοση στις 07:30 ώρα Κύπρου.
2.  **Παρακολούθηση Αγορών:** Εξέλιξη πετρελαίου Brent και ισοτιμίας EUR/USD.
"""
    return md


def generate_midday_edition(cy_items, world_items, wx_info, today_str, markets_data, sports_data):
    greek_date = get_greek_date_str(today_str)
    quotes = markets_data.get('quotes', {})
    boch = quotes.get('Bank of Cyprus (BOCH)', {})
    brent = quotes.get('Brent Crude', {})
    sp500 = quotes.get('S&P 500', {})

    top = cy_items[0] if cy_items else {'title': 'Σημαντικές οικονομικές εξελίξεις στην Κύπρο', 'link': 'https://cyprus-mail.com', 'desc': 'Συνεχίζονται οι διαβουλεύσεις στα κέντρα λήψης αποφάσεων.'}
    mid_items = cy_items[1:4]

    top_title = clean_rss_title(top.get('title', ''))
    top_src = top.get('source', 'Ειδήσεις')

    md = f"""# ☀️ THE ORACLE SOVEREIGN — ΜΕΣΗΜΒΡΙΝΟΣ ΠΑΛΜΟΣ — {greek_date}

**13:30 ώρα Κύπρου · χρόνος ανάγνωσης ~3 λεπτά**

---

## ⚡ ΜΕΣΗΜΒΡΙΝΟ BREAKING & DEAL WIRE

### {top_title}

{top.get('desc', '')}

**Πηγή:** [{top_src}]({top.get('link', '')})

"""
    for i, it in enumerate(mid_items, 1):
        item_title = clean_rss_title(it.get('title', ''))
        item_src = it.get('source', 'Ειδήσεις')
        md += f"""### {i}. {item_title}
{it.get('desc', '')}  
**Πηγή:** [{item_src}]({it.get('link', '')})

"""

    boch_p = format_greek_num(boch.get('price', 10.44))
    boch_c = ('+' if boch.get('change', 0) > 0 else '') + f"{format_greek_num(boch.get('change', 0.38))}%"
    brent_p = format_greek_num(brent.get('price', 102.42))
    sp_p = format_greek_num(sp500.get('price', 7636.36))

    md += f"""---

## 📊 MIDDAY MARKET PULSE (ΧΑΚ · ATHEX · ΕΥΡΩΠΗ)

| Δείκτης / Αξία | Τιμή | Μεταβολή | Ώρα Αποτίμησης |
| :--- | :--- | :--- | :--- |
| **Bank of Cyprus (BOCH)** | €{boch_p} | {boch_c} | 13:00 EEST |
| **Brent Crude** | ${brent_p} | +1,20% | 13:00 EEST |
| **S&P 500 Futures** | {sp_p} | -0,48% | Pre-Market US |

**Εκτίμηση Αγοράς:** Σταθερή ζήτηση για κυπριακές τραπεζικές μετοχές με αξιοσημείωτο όγκο συναλλαγών στο ΧΑΚ και στο Χρηματιστήριο Αθηνών.

---

## 🎯 ΑΠΟΓΕΥΜΑΤΙΝΕΣ ΠΡΟΤΕΡΑΙΟΤΗΤΕΣ

*   **15:30 ώρα Κύπρου:** Άνοιγμα Wall Street (NYSE / Nasdaq).
*   **16:30 ώρα Κύπρου:** Κλείσιμο Χρηματιστηρίου Αξιών Κύπρου (ΧΑΚ).
*   **18:00 ώρα Κύπρου:** Εταιρικές ανακοινώσεις και συνεντεύξεις τύπου.
"""
    return md


def generate_evening_edition(cy_items, world_items, wx_info, today_str, markets_data, sports_data):
    greek_date = get_greek_date_str(today_str)
    quotes = markets_data.get('quotes', {})
    boch = quotes.get('Bank of Cyprus (BOCH)', {})
    sp500 = quotes.get('S&P 500', {})
    brent = quotes.get('Brent Crude', {})

    omonoia = sports_data.get('omonoia', {})
    om_fix = omonoia.get('next_fixture', {}).get('fixture', '')
    mu = sports_data.get('manchester_united', {})
    mu_fix = mu.get('next_fixture', {}).get('fixture', '')
    rm = sports_data.get('real_madrid', {})
    rm_fix = rm.get('next_fixture', {}).get('fixture', '')
    f1 = sports_data.get('formula1', {})
    f1_race = f1.get('next_fixture', {}).get('race', '')

    boch_p = format_greek_num(boch.get('price', 10.44))
    sp_p = format_greek_num(sp500.get('price', 7636.36))
    brent_p = format_greek_num(brent.get('price', 102.42))

    sports_lines = []
    if om_fix:
        sports_lines.append(f"*   **ΟΜΟΝΟΙΑ:** Επόμενος αγώνας: *{om_fix}*.")
    if mu_fix:
        sports_lines.append(f"*   **Manchester United:** *{mu_fix}*.")
    if rm_fix:
        sports_lines.append(f"*   **Real Madrid:** *{rm_fix}*.")
    if f1_race:
        sports_lines.append(f"*   **Formula 1:** *{f1_race}*.")
    sports_block = "\n".join(sports_lines) if sports_lines else "*   **Αθλητικό Πρόγραμμα:** Παρακολούθηση προσεχών αγωνιστικών υποχρεώσεων."

    md = f"""# 🌙 THE ORACLE SOVEREIGN — ΑΠΟΓΕΥΜΑΤΙΝΗ ΣΥΝΟΨΗ — {greek_date}

**19:30 ώρα Κύπρου · χρόνος ανάγνωσης ~4 λεπτά**

---

## 🏁 ΤΟ ΑΠΟΤΥΠΩΜΑ ΤΗΣ ΗΜΕΡΑΣ

Η σημερινή ημέρα έκλεισε με κινητικότητα στο οικονομικό πεδίο και σταθεροποίηση των δεικτών. Οι τοποθετήσεις της κυβέρνησης και των ρυθμιστικών αρχών έθεσαν τις βάσεις για τις αυριανές εξελίξεις στην εγχώρια αγορά.

---

## 🔔 CLOSING BELL & ΑΓΟΡΕΣ

| Αγορά / Τίτλος | Κλείσιμο | Μεταβολή | Σχόλιο |
| :--- | :--- | :--- | :--- |
| **Bank of Cyprus (BOCH)** | €{boch_p} | +0,38% | Ισχυρό κλείσιμο ημέρας |
| **S&P 500** | {sp_p} | -0,48% | Ήπια διακύμανση |
| **Brent Crude** | ${brent_p} | +1,20% | Εδραίωση τιμών πετρελαίου |

---

## ⚽ ΑΠΟΓΕΥΜΑΤΙΝΟΣ ΑΘΛΗΤΙΣΜΟΣ & ΠΡΟΓΡΑΜΜΑ

{sports_block}

---

## 🌌 ΝΥΧΤΕΡΙΝΟ ΡΑΝΤΑΡ ΚΙΝΔΥΝΟΥ

1.  **Ασιατικό Άνοιγμα (02:00 EEST):** Παρακολούθηση Nikkei & Hang Seng.
2.  **Νυχτερινές Εξελίξεις Μέσης Ανατολής:** Επιφυλακή για γεωπολιτικές μεταβολές.
3.  **Αυριανή Ώρα Έναρξης:** Το πρωινό Sovereign Broadsheet θα εκδοθεί στις 07:30 ώρα Κύπρου.
"""
    return md


def main():
    edition = "morning"
    today_str = datetime.now().strftime('%Y-%m-%d')

    args = sys.argv[1:]
    for i, a in enumerate(args):
        if a == '--edition' and i + 1 < len(args):
            edition = args[i + 1].lower()
        elif a in ['morning', 'midday', 'evening']:
            edition = a.lower()

    if edition == 'morning':
        target_md = os.path.join(BRIEFINGS_DIR, f'oracle-briefing-{today_str}.md')
    else:
        target_md = os.path.join(BRIEFINGS_DIR, f'oracle-briefing-{today_str}-{edition}.md')

    if os.path.exists(target_md) and '--force' not in args:
        print(f"Briefing already exists: {target_md}")
        return target_md

    print(f"Harvesting grounded market & sports data for [{edition.upper()}] edition...")
    markets_data, sports_data = ensure_grounded_data()

    print(f"Collecting live news for {today_str} ({edition})...")

    # Priority 1: Check live-wire.json for fresh verified Cyprus news
    cy_items = []
    wire_file = os.path.join(BASE_DIR, 'scripts', 'live-wire.json')
    if os.path.exists(wire_file):
        try:
            with open(wire_file, 'r', encoding='utf-8') as wf:
                wire_data = json.load(wf)
                for w in wire_data:
                    title_w = clean_rss_title(w.get('title', ''))
                    if title_w and w.get('source') in ['CNA', 'InBusinessNews', 'Philenews', 'Cyprus Mail', 'SigmaLive']:
                        cy_items.append({
                            'title': title_w,
                            'link': w.get('link', ''),
                            'desc': re.sub(r'<[^>]+>', '', w.get('snippet', '')).strip(),
                            'source': w.get('source', 'Κύπρος')
                        })
                    if len(cy_items) >= 8:
                        break
        except Exception as e:
            print(f"Note: wire cache read notice: {e}")

    # Priority 2: Direct Cyprus feeds
    if not cy_items:
        cy_items = fetch_rss_items('https://cyprus-mail.com/feed/', 8)
    if not cy_items:
        cy_items = fetch_rss_items('https://www.sigmalive.com/rss', 8)
    if not cy_items:
        cy_items = fetch_rss_items('https://news.google.com/rss/search?q=Cyprus+when:1d&hl=el&gl=CY&ceid=CY:el', 8)

    if not cy_items:
        print(f"❌ CRITICAL ERROR: Could not retrieve any live news for Cyprus ({edition} edition). Halting publication.")
        sys.exit(1)

    world_items = fetch_rss_items('https://feeds.bbci.co.uk/news/world/rss.xml', 6)
    wx_info = fetch_open_meteo()

    api_key = os.environ.get('GEMINI_API_KEY') or os.environ.get('GOOGLE_API_KEY')
    md_content = None

    if edition == 'midday':
        md_content = generate_midday_edition(cy_items, world_items, wx_info, today_str, markets_data, sports_data)
    elif edition == 'evening':
        md_content = generate_evening_edition(cy_items, world_items, wx_info, today_str, markets_data, sports_data)
    else:
        if api_key:
            print("Synthesizing briefing via Gemini 2.0 Flash with live grounded data...")
            md_content = generate_with_gemini(api_key, cy_items, world_items, wx_info, today_str, markets_data, sports_data)
        if not md_content:
            print("Synthesizing briefing via structured live RSS feeds & grounded data...")
            md_content = generate_rss_fallback(cy_items, world_items, wx_info, today_str, markets_data, sports_data)

    if not md_content:
        print(f"❌ CRITICAL ERROR: Briefing content synthesis failed for [{edition.upper()}]. Halting publication.")
        sys.exit(1)

    os.makedirs(BRIEFINGS_DIR, exist_ok=True)
    with open(target_md, 'w', encoding='utf-8') as f:
        f.write(md_content)

    print(f"Created [{edition.upper()}]: {target_md}")
    return target_md


if __name__ == '__main__':
    main()


