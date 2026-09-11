#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
THE ORACLE SOVEREIGN — Automated HTML Generator
Converts any `oracle-briefing-YYYY-MM-DD.md` into the executive web edition.
Features:
  - News-First Layout: Breaking News, Cyprus (6 items), World (5 items), Movers lead the page
  - Tools (Euribor rates, loan calculator, dashboard) placed logically after news
  - High-resolution editorial images for every news card with fallback
  - Expandable full text / antilogos details for maximum readability
  - Class-based Tailwind Dark Mode (zero FOUC) & reduced-motion support
  - Dynamic Open-Meteo live weather client fetch
  - Weekly House Search (Real Estate Radar) integration
  - Instant Archive Search across all past editions
"""

import os
import sys
import re
import json
import glob
import shutil
import urllib.request
import ssl
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
BRIEFINGS_DIR = os.path.join(BASE_DIR, 'briefings')
DOCS_DIR = os.path.join(BASE_DIR, 'docs')
DOCS_BRIEFINGS_DIR = os.path.join(DOCS_DIR, 'briefings')
HOUSE_SEARCH_DIR = os.path.abspath(os.path.join(BASE_DIR, '..', 'House Search'))
CACHE_FILE = os.path.join(os.path.dirname(__file__), 'image_cache.json')

# SSL context for image fetching
SSL_CTX = ssl._create_unverified_context()

TOPIC_FALLBACKS = {
    'school': 'https://images.unsplash.com/photo-1580582932707-520aed937b7b?w=800&q=80',
    'employment': 'https://images.unsplash.com/photo-1521791136064-7986c2920216?w=800&q=80',
    'economy': 'https://images.unsplash.com/photo-1526304640581-d334cdbbf45e?w=800&q=80',
    'energy': 'https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=800&q=80',
    'banking': 'https://images.unsplash.com/photo-1541354329998-f4d9a9f9297f?w=800&q=80',
    'shipwreck': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80',
    'shipping': 'https://images.unsplash.com/photo-1559136555-9303baea8ebd?w=800&q=80',
    'politics': 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&q=80',
    'housing': 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800&q=80',
    'diplomacy': 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&q=80',
    'climate': 'https://images.unsplash.com/photo-1504370805625-d32c54b16100?w=800&q=80',
    'social': 'https://images.unsplash.com/photo-1511895426328-dc8714191300?w=800&q=80',
    'technology': 'https://images.unsplash.com/photo-1519389950473-47ba0277781c?w=800&q=80',
    'germany': 'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=800&q=80',
    'volcano': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80',
    'aviation': 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800&q=80',
    'justice': 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&q=80',
    'general': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80'
}


def is_valid_content_image(img_url):
    if not img_url or not img_url.startswith('http'):
        return False
    bad_tokens = ['googleusercontent.com', 'gstatic.com', 'default_avatar', 'placeholder', 'blank.gif', 'favicon', 'logo-white', 'logo-black']
    return not any(b in img_url.lower() for b in bad_tokens)


def md_to_inline_html(text):
    if not text:
        return ""
    # Convert markdown links [name](url)
    text = re.sub(r'\[(.*?)\]\((https?://[^\s)]+)\)', r'<a href="\2" target="_blank" rel="noopener noreferrer" class="text-[var(--accent)] hover:underline font-semibold">\1</a>', text)
    # Convert bold **text**
    text = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', text)
    # Convert italic *text*
    text = re.sub(r'(?<!\*)\*([^*]+)\*(?!\*)', r'<em>\1</em>', text)
    return text


def render_depth_html(depth, is_world=False):
    if not depth or len(depth) < 2:
        return ""

    rows = []
    if depth.get('background'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Το υπόβαθρο:</strong> {md_to_inline_html(depth["background"])}</div>')
    if depth.get('practical'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Τι σημαίνει πρακτικά:</strong> {md_to_inline_html(depth["practical"])}</div>')

    if not is_world and depth.get('next_watch'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Τι να παρακολουθήσω:</strong> {md_to_inline_html(depth["next_watch"])}</div>')
    elif is_world and depth.get('antilogos'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Αντίλογος:</strong> {md_to_inline_html(depth["antilogos"])}</div>')
    elif depth.get('next_watch'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Τι να παρακολουθήσω:</strong> {md_to_inline_html(depth["next_watch"])}</div>')
    elif depth.get('antilogos'):
        rows.append(f'<div><strong class="text-[var(--ink)]">Αντίλογος:</strong> {md_to_inline_html(depth["antilogos"])}</div>')

    if len(rows) < 2:
        return ""

    content = '\n'.join(rows)
    return f'''
    <details class="depth mt-3 border-t border-[var(--rule)] pt-2.5">
      <summary class="cursor-pointer t-meta font-semibold text-[var(--accent)] hover:underline flex items-center justify-between py-1">
        <span>Περισσότερα: Υπόβαθρο & Πρακτική Σημασία</span>
        <span class="expand-icon text-[10px] transition-transform">▼</span>
      </summary>
      <div class="mt-2.5 t-meta text-[var(--ink-body)] bg-[var(--paper)] p-3 rounded space-y-2 border border-[var(--rule)] leading-relaxed">
        {content}
      </div>
    </details>
    '''


def load_image_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_image_cache(cache):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def resolve_image(url, title, default_category='ΕΠΙΚΑΙΡΟΤΗΤΑ'):
    cache = load_image_cache()
    if url in cache and is_valid_content_image(cache[url].get('image')):
        return cache[url]['image'], cache[url].get('category', default_category)

    # Keyword fallback selection
    t_lower = (title + ' ' + url).lower()
    fallback = TOPIC_FALLBACKS['general']
    category = default_category

    if any(k in t_lower for k in ['καύσιμ', 'πετρέλαι', 'βενζίν', 'brent', 'wti', 'αέριο', 'ενέργει', 'interconnector']):
        fallback = TOPIC_FALLBACKS['energy']
        category = 'ΕΝΕΡΓΕΙΑ & ΑΓΟΡΕΣ'
    elif any(k in t_lower for k in ['χέρτζογκ', 'ισραήλ', 'ιράν', 'μέση ανατολή', 'κόλπο', 'οηε', 'διπλωματ', 'χριστοδουλίδ', 'ολγκίν', 'κυπριακό']):
        fallback = TOPIC_FALLBACKS['diplomacy']
        category = 'ΓΕΩΠΟΛΙΤΙΚΗ & ΔΙΠΛΩΜΑΤΙΑ'
    elif any(k in t_lower for k in ['κεφαλαιαγορ', 'τράπεζ', 'boch', 'επιτόκι', 'euribor', 'χρηματοπιστωτ', 'dbrs', 'οίκος', 'δημοσιονομ']):
        fallback = TOPIC_FALLBACKS['banking']
        category = 'ΤΡΑΠΕΖΕΣ & ΚΕΦΑΛΑΙΑΓΟΡΑ'
    elif any(k in t_lower for k in ['κλίμα', 'θερμότερ', 'copernicus', 'καύσων', 'περιβάλλον', 'el niño']):
        fallback = TOPIC_FALLBACKS['climate']
        category = 'ΚΛΙΜΑ & ΠΕΡΙΒΑΛΛΟΝ'
    elif any(k in t_lower for k in ['τέκν', 'οικογένει', 'επίδομα', 'κοινωνικ']):
        fallback = TOPIC_FALLBACKS['social']
        category = 'ΚΟΙΝΩΝΙΚΗ ΠΟΛΙΤΙΚΗ'
    elif any(k in t_lower for k in ['forum', 'future realized', 'τεχνολογ', 'επενδύσ', 'ey', 'data center']):
        fallback = TOPIC_FALLBACKS['technology']
        category = 'ΕΠΕΝΔΥΣΕΙΣ & TECH'
    elif any(k in t_lower for k in ['ναυτικ', 'πλοί', 'ναυτιλ', 'σκάφος', 'ναυάγ', 'κερύνει', 'aster']):
        fallback = TOPIC_FALLBACKS['shipping']
        category = 'ΝΑΥΤΙΛΙΑ & ΑΣΦΑΛΕΙΑ'
    elif any(k in t_lower for k in ['σχολ', 'μαθητ', 'υποδομ', 'ύψωνα', 'παιδεία']):
        fallback = TOPIC_FALLBACKS['school']
        category = 'ΠΑΙΔΕΙΑ & ΥΠΟΔΟΜΕΣ'
    elif any(k in t_lower for k in ['απασχόληση', 'εργασί', 'cystat', 'μισθ']):
        fallback = TOPIC_FALLBACKS['employment']
        category = 'ΟΙΚΟΝΟΜΙΑ'
    elif any(k in t_lower for k in ['λιμουζίν', 'βουλ', 'διορισμ', 'θεσμο', 'πολιτικ']):
        fallback = TOPIC_FALLBACKS['politics']
        category = 'ΠΟΛΙΤΙΚΗ & ΘΕΣΜΟΙ'
    elif any(k in t_lower for k in ['ενοίκι', 'στέγη', 'τεπακ', 'ακίνητ', 'λεμεσ', 'κεδιπεσ']):
        fallback = TOPIC_FALLBACKS['housing']
        category = 'Ο ΦΑΚΕΛΟΣ ΜΟΥ'
    elif any(k in t_lower for k in ['zelenskyy', 'putin', 'ουκραν', 'κίεβο', 'σιβηρία']):
        fallback = TOPIC_FALLBACKS['diplomacy']
        category = 'ΔΙΕΘΝΗ'
    elif any(k in t_lower for k in ['afd', 'γερμανί', 'merz', 'σαξονία']):
        fallback = TOPIC_FALLBACKS['germany']
        category = 'ΓΕΡΜΑΝΙΑ'
    elif any(k in t_lower for k in ['krakatau', 'ηφαίστει', 'ινδονησία']):
        fallback = TOPIC_FALLBACKS['volcano']
        category = 'ΑΣΙΑ'
    elif any(k in t_lower for k in ['amazon', 'boeing', 'μαϊάμι', 'αεροπορικ']):
        fallback = TOPIC_FALLBACKS['aviation']
        category = 'ΗΠΑ'
    elif any(k in t_lower for k in ['icj', 'χάγη', 'δικαστήρι', 'γενοκτον', 'δικαιοσύν']):
        fallback = TOPIC_FALLBACKS['justice']
        category = 'ΔΙΚΑΙΟΣΥΝΗ'

    # Try fetching og:image live with short timeout
    og_img = None
    if url.startswith('http') and 'news.google.com' not in url:
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=3.5, context=SSL_CTX) as resp:
                html_txt = resp.read().decode('utf-8', errors='ignore')
                m = re.search(r'<meta[^>]+(?:property|name)=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', html_txt, re.I)
                if not m:
                    m = re.search(r'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+(?:property|name)=[\'"]og:image[\'"]', html_txt, re.I)
                if m:
                    candidate = m.group(1).strip()
                    if candidate.startswith('//'):
                        candidate = 'https:' + candidate
                    elif candidate.startswith('/'):
                        from urllib.parse import urljoin
                        candidate = urljoin(url, candidate)
                    if is_valid_content_image(candidate):
                        og_img = candidate
        except Exception:
            pass

    final_img = og_img if og_img else fallback
    cache[url] = {'image': final_img, 'category': category}
    save_image_cache(cache)
    return final_img, category


def briefing_sort_key(filepath):
    filename = os.path.basename(filepath)
    m = re.search(r'oracle-briefing-(\d{4}-\d{2}-\d{2})(?:-(midday|evening))?\.md', filename)
    if not m:
        return ('0000-00-00', 0)
    date_part = m.group(1)
    ed_part = m.group(2)
    order = 1
    if ed_part == 'midday':
        order = 2
    elif ed_part == 'evening':
        order = 3
    return (date_part, order)


def find_latest_briefing():
    pattern = os.path.join(BRIEFINGS_DIR, 'oracle-briefing-*.md')
    files = glob.glob(pattern)
    if not files:
        raise FileNotFoundError(f"No briefing files found in {BRIEFINGS_DIR}")
    files.sort(key=briefing_sort_key)
    return files[-1]


def annuity_payment(principal: float, annual_rate_pct: float, years: int) -> float:
    """Standard annuity formula: M = P * r(1+r)^n / ((1+r)^n - 1)"""
    r = annual_rate_pct / 100 / 12
    n = years * 12
    if r == 0:
        return principal / n
    return principal * (r * (1 + r)**n) / ((1 + r)**n - 1)



def resolve_edition_urls(iso_date, is_subfolder):
    """Resolves correct relative links between editions and resources.
    Guarantees seamless navigation whether viewing from root index.html or docs/briefings/*.
    """
    if is_subfolder:
        return {
            'home': '../index.html',
            'morning': f'{iso_date}.html',
            'midday': f'{iso_date}-midday.html',
            'evening': f'{iso_date}-evening.html',
            'live_wire': '../live-wire.json',
            'search_index': '../search-index.json',
        }
    else:
        return {
            'home': 'index.html',
            'morning': f'briefings/{iso_date}.html',
            'midday': f'briefings/{iso_date}-midday.html',
            'evening': f'briefings/{iso_date}-evening.html',
            'live_wire': 'live-wire.json',
            'search_index': 'search-index.json',
        }


def render_edition_switcher_html(urls, current_edition):
    active_cls = "bg-[var(--accent)] text-white font-bold shadow-xs"
    inactive_cls = "bg-[var(--paper)] text-[var(--ink-body)] border border-[var(--rule)] hover:border-[var(--accent)]"

    morning_cls = active_cls if current_edition == 'morning' else inactive_cls
    midday_cls = active_cls if current_edition == 'midday' else inactive_cls
    evening_cls = active_cls if current_edition == 'evening' else inactive_cls

    return f'''
    <div class="flex flex-wrap items-center gap-1.5 font-mono text-[11px]">
      <span class="text-[var(--ink-quiet)] uppercase text-[10px] tracking-wider hidden sm:inline mr-0.5">ΕΚΔΟΣΗ:</span>
      <a href="{urls['morning']}" class="px-2 py-0.5 rounded transition {morning_cls}">🌅 07:30 Πρωί</a>
      <a href="{urls['midday']}" class="px-2 py-0.5 rounded transition {midday_cls}">☀️ 13:30 Μεσημέρι</a>
      <a href="{urls['evening']}" class="px-2 py-0.5 rounded transition {evening_cls}">🌙 19:30 Απόγευμα</a>
      <button id="openWireDrawerBtnNav" class="px-2 py-0.5 rounded border border-red-500/30 bg-red-500/10 text-red-600 dark:text-red-400 font-bold hover:bg-red-500/20 transition flex items-center gap-1.5">
        <span class="w-1.5 h-1.5 rounded-full bg-red-500 animate-ping"></span> ⚡ Live Wire
      </button>
    </div>
    '''

def parse_markdown(md_content, filename=""):
    data = {
        'title': 'THE ORACLE SOVEREIGN',
        'edition': 'morning',
        'date_str': '',
        'time_str': '',
        'read_time': "7'",
        'top_story': {},
        'dashboard': [],
        'number_of_day': {},
        'rates': {
            'euribor': [],
            'ecb_rate': '—',
            'next_ecb': '—',
            'cbc_mortgage_rate': '—',
            'example_payment': '—',
            'example_change': '—',
            'sources': []
        },
        'cyprus': [],
        'world': [],
        'markets': [],
        'sports': {
            'omonoia': {'last_result': '', 'next_match': '', 'highlights': None, 'news': [], 'source': None, 'raw': []},
            'manutd': {'last_result': '', 'next_match': '', 'highlights': None, 'news': [], 'source': None, 'raw': []},
            'realmadrid': {'last_result': '', 'next_match': '', 'highlights': None, 'news': [], 'source': None, 'raw': []},
            'formula1': {'last_result': '', 'next_match': '', 'highlights': None, 'news': [], 'source': None, 'raw': []}
        },
        'night_radar': [],
        'midday_news': [],
        'evening_news': [],
        'afternoon_priorities': [],
        'weather': {},
        'tomorrow_weather': {},
        'executive_pulse': [],
        'developments': [],
        'portfolio': [],
        'deadlines': [],
        'tomorrow': [],
        'footnotes': []
    }

    fn = filename.lower()
    if '-evening' in fn or 'evening' in fn:
        data['edition'] = 'evening'
        data['time_str'] = '19:30'
        data['read_time'] = "4'"
    elif '-midday' in fn or 'midday' in fn:
        data['edition'] = 'midday'
        data['time_str'] = '13:30'
        data['read_time'] = "3'"

    lines = md_content.splitlines()
    for line in lines[:8]:
        line_clean = line.strip()
        m_title = re.search(r'#.*?THE ORACLE SOVEREIGN\s*[—–-]\s*(.+)', line_clean)
        if m_title:
            raw_title_rest = m_title.group(1).strip()
            data['title'] = f"THE ORACLE SOVEREIGN — {raw_title_rest}"
            if 'ΑΠΟΓΕΥΜΑΤΙΝΗ' in raw_title_rest.upper() or 'EVENING' in raw_title_rest.upper():
                data['edition'] = 'evening'
            elif 'ΜΕΣΗΜΒΡΙΝ' in raw_title_rest.upper() or 'MIDDAY' in raw_title_rest.upper():
                data['edition'] = 'midday'
            parts = [p.strip() for p in re.split(r'[—–-]', raw_title_rest) if p.strip()]
            data['date_str'] = parts[-1] if parts else raw_title_rest

        m_time = re.search(r'(?:\*\*)?(\d{1,2}:\d{2})\s*ώρα Κύπρου', line_clean)
        if m_time:
            data['time_str'] = m_time.group(1).strip()
        m_read = re.search(r'χρόνος ανάγνωσης\s*~?(\d+)', line_clean)
        if m_read:
            data['read_time'] = f"{m_read.group(1)}'"

    pulse_match = re.search(r'>\s*\[!NOTE\]\s*\n((?:>\s*.*?\n?)+)', md_content)
    if pulse_match:
        for pl in pulse_match.group(1).splitlines():
            pl_clean = re.sub(r'^>\s*', '', pl).strip()
            if pl_clean.startswith('*') or pl_clean.startswith('-'):
                cleaned_item = re.sub(r'^[*\-]\s*', '', pl_clean).strip()
                data['executive_pulse'].append(cleaned_item)

    sections = re.split(r'\n##\s+', md_content)
    for sec in sections[1:]:
        sec_lines = sec.strip().splitlines()
        if not sec_lines:
            continue
        sec_header = sec_lines[0].strip()

        # TOP STORY / FOOTPRINT
        if 'ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ' in sec_header or 'ΤΟ ΑΠΟΤΥΠΩΜΑ ΤΗΣ ΗΜΕΡΑΣ' in sec_header:
            top_data = {'title': '', 'body': '', 'antilogos': '', 'sources': []}
            h3_match = re.search(r'###\s+(.+)', sec)
            if h3_match:
                top_data['title'] = h3_match.group(1).strip()
            elif 'ΤΟ ΑΠΟΤΥΠΩΜΑ ΤΗΣ ΗΜΕΡΑΣ' in sec_header:
                top_data['title'] = '🏁 ΤΟ ΑΠΟΤΥΠΩΜΑ ΤΗΣ ΗΜΕΡΑΣ'
            else:
                top_data['title'] = sec_header.replace('##', '').strip()

            anti_match = re.search(r'\*\*Αντίλογος:\*\*\s*(.+?)(?=\n\n|\n\*\*Πηγές:|\Z)', sec, re.DOTALL)
            if anti_match:
                top_data['antilogos'] = anti_match.group(1).strip()

            src_match = re.search(r'\*\*Πηγές:\*\*\s*(.+)', sec)
            if src_match:
                sources_raw = re.findall(r'\[(.*?)\]\((.*?)\)', src_match.group(1))
                top_data['sources'] = [{'name': name, 'url': url} for name, url in sources_raw]

            body_parts = []
            capture = False if h3_match else True
            for sl in sec_lines[1:]:
                sl_clean = sl.strip()
                if sl_clean.startswith('### '):
                    capture = True
                    continue
                if sl_clean.startswith('**Αντίλογος:') or sl_clean.startswith('**Πηγές:'):
                    capture = False
                    break
                if capture and sl_clean and not sl_clean.startswith('---'):
                    body_parts.append(sl_clean)
            top_data['body'] = ' '.join(body_parts)
            data['top_story'] = top_data

        # MIDDAY BREAKING & DEAL WIRE
        elif 'BREAKING' in sec_header or 'DEAL WIRE' in sec_header:
            items = re.split(r'\n###\s+', sec)
            for itm in items[1:]:
                itm_lines = itm.strip().splitlines()
                if not itm_lines: continue
                raw_title = itm_lines[0].strip()
                region = '🇨🇾 ΚΥΠΡΟΣ' if '🇨🇾' in raw_title else ('🌍 ΔΙΕΘΝΗ' if '🌍' in raw_title else '⚡ ΕΠΙΚΑΙΡΟΤΗΤΑ')
                clean_title = re.sub(r'^(?:🇨🇾|🌍|⚡)\s*', '', raw_title).strip()
                clean_title = re.sub(r'\[(ΕΠΙΒΕΒΑΙΩΜΕΝΟ|ΕΞΕΛΙΣΣΟΜΕΝΟ)\]\s*', '', clean_title).strip()

                itm_body = []
                itm_why = ''
                itm_src = None
                for il in itm_lines[1:]:
                    il_c = il.strip()
                    if il_c.startswith('**Γιατί με αφορά:**') or il_c.startswith('Γιατί με αφορά:'):
                        itm_why = re.sub(r'^\*?\*?Γιατί με αφορά:\*?\*?\s*', '', il_c).strip()
                    elif il_c.startswith('**Πηγή:**') or il_c.startswith('Πηγή:'):
                        src_match = re.search(r'\[(.*?)\]\((.*?)\)', il_c)
                        if src_match:
                            itm_src = {'name': src_match.group(1).strip(), 'url': src_match.group(2).strip()}
                    elif il_c and not il_c.startswith('---'):
                        itm_body.append(il_c)
                data['midday_news'].append({
                    'title': clean_title,
                    'raw_title': raw_title,
                    'region': region,
                    'body': ' '.join(itm_body),
                    'why': itm_why,
                    'source': itm_src
                })

        # EVENING NEWS WIRE
        elif 'ΑΠΟΓΕΥΜΑΤΙΝΗ ΕΠΙΚΑΙΡΟΤΗΤΑ' in sec_header or 'ΕΠΙΚΑΙΡΟΤΗΤΑ & ΕΞΕΛΙΞΕΙΣ' in sec_header:
            items = re.split(r'\n###\s+', sec)
            for itm in items[1:]:
                itm_lines = itm.strip().splitlines()
                if not itm_lines: continue
                raw_title = itm_lines[0].strip()
                region = '🇨🇾 ΚΥΠΡΟΣ' if '🇨🇾' in raw_title else ('🌍 ΔΙΕΘΝΗ' if '🌍' in raw_title else '⚡ ΕΠΙΚΑΙΡΟΤΗΤΑ')
                clean_title = re.sub(r'^(?:🇨🇾|🌍|⚡)\s*', '', raw_title).strip()

                itm_body = []
                itm_why = ''
                itm_src = None
                for il in itm_lines[1:]:
                    il_c = il.strip()
                    if il_c.startswith('**Γιατί με αφορά:**') or il_c.startswith('Γιατί με αφορά:'):
                        itm_why = re.sub(r'^\*?\*?Γιατί με αφορά:\*?\*?\s*', '', il_c).strip()
                    elif il_c.startswith('**Πηγή:**') or il_c.startswith('Πηγή:'):
                        src_match = re.search(r'\[(.*?)\]\((.*?)\)', il_c)
                        if src_match:
                            itm_src = {'name': src_match.group(1).strip(), 'url': src_match.group(2).strip()}
                    elif il_c and not il_c.startswith('---'):
                        itm_body.append(il_c)
                data['evening_news'].append({
                    'title': clean_title,
                    'region': region,
                    'body': ' '.join(itm_body),
                    'why': itm_why,
                    'source': itm_src
                })

        # DASHBOARD / CLOSING BELL / MIDDAY MARKET PULSE
        elif 'DASHBOARD' in sec_header or 'CLOSING BELL' in sec_header or 'MARKET PULSE' in sec_header or 'ΑΓΟΡΕΣ' in sec_header:
            current_category = 'Δείκτες & Συνάλλαγμα'
            for sl in sec_lines:
                sl_c = sl.strip()
                if sl_c.startswith('###'):
                    if any(k in sl_c.upper() for k in ['ΜΕΤΟΧ', 'STOCKS', 'EQUITIES', 'TECH', 'WATCHLIST']):
                        current_category = 'Μετοχές Τεχνολογίας'
                    else:
                        current_category = 'Δείκτες & Συνάλλαγμα'
                elif sl_c.startswith('|') and not '---' in sl_c:
                    cols = [c.strip() for c in sl_c.split('|')[1:-1]]
                    if len(cols) >= 3 and not any(cols[0].startswith(x) for x in ['Δείκτης', 'Αγορά', 'Μετοχή', 'Ticker', 'Asset', ':---']):
                        asset_name = re.sub(r'\*\*', '', cols[0]).strip()
                        cat = current_category
                        if any(s in asset_name.upper() for s in ['TSM', 'NVDA', 'GOOG', 'AAPL', 'MSFT', 'MU', 'META', 'AMZN']):
                            cat = 'Μετοχές Τεχνολογίας'
                        price = cols[1].strip()
                        change = cols[2].strip()
                        date_ref = cols[3].strip() if len(cols) >= 4 else "Κλείσιμο"
                        data['dashboard'].append({
                            'asset': asset_name,
                            'price': price,
                            'change': change,
                            'date_ref': date_ref,
                            'category': cat
                        })
            nod_match = re.search(r'\*\*Ο αριθμός της ημέρας:\*\*\s*\*\*([^*]+)\*\*\s*[—–-]\s*(.+)', sec)
            if nod_match:
                data['number_of_day'] = {
                    'number': nod_match.group(1).strip(),
                    'text': nod_match.group(2).strip()
                }

        # TOMORROW WEATHER / OUTLOOK (EVENING)
        elif 'ΑΥΡΙΑΝΗ ΠΡΟΓΝΩΣΗ' in sec_header or 'ΠΡΟΓΝΩΣΗ ΛΕΜΕΣΟΥ' in sec_header:
            tw = {}
            for sl in sec_lines:
                sl_c = sl.strip()
                if 'Θερμοκρασία:' in sl_c:
                    tw['temp'] = re.sub(r'^\*?\*?Θερμοκρασία:\*?\*?\s*', '', sl_c).strip()
                elif 'Πρόγνωση:' in sl_c:
                    tw['forecast'] = re.sub(r'^\*?\*?Πρόγνωση:\*?\*?\s*', '', sl_c).strip()
                elif 'Άνεμοι' in sl_c:
                    tw['wind'] = re.sub(r'^\*?\*?Άνεμοι.*?:\*?\*?\s*', '', sl_c).strip()
            data['tomorrow_weather'] = tw

        # NOCTURNAL RISK RADAR
        elif 'ΡΑΝΤΑΡ ΚΙΝΔΥΝΟΥ' in sec_header or 'ΝΥΧΤΕΡΙΝΟ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c and (sl_c[0].isdigit() or sl_c.startswith('*') or sl_c.startswith('-')):
                    clean_sl = re.sub(r'^\d+\.\s*', '', sl_c).strip()
                    clean_sl = re.sub(r'^[*\-]\s*', '', clean_sl).strip()
                    if clean_sl and clean_sl not in ['--', '---']:
                        data['night_radar'].append(clean_sl)

        # AFTERNOON PRIORITIES (MIDDAY)
        elif 'ΠΡΟΤΕΡΑΙΟΤΗΤΕΣ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c and (sl_c[0].isdigit() or sl_c.startswith('*') or sl_c.startswith('-')):
                    clean_sl = re.sub(r'^\d+\.\s*', '', sl_c).strip()
                    clean_sl = re.sub(r'^[*\-]\s*', '', clean_sl).strip()
                    if clean_sl and clean_sl not in ['--', '---']:
                        data['afternoon_priorities'].append(clean_sl)

        # RATES & MORTGAGE
        elif 'ΕΠΙΤΟΚΙΑ' in sec_header:
            table_lines = [l.strip() for l in sec_lines if l.strip().startswith('|') and not '---' in l]
            for row in table_lines:
                cols = [c.strip() for c in row.split('|')[1:-1]]
                if len(cols) >= 5 and cols[0] in ['**Τρέχον**', 'Τρέχον', '**Πριν 1 μήνα**', 'Πριν 1 μήνα']:
                    period = re.sub(r'\*\*', '', cols[0]).strip()
                    data['rates']['euribor'].append({
                        'period': period,
                        '1m': cols[1], '3m': cols[2], '6m': cols[3], '12m': cols[4]
                    })
            ecb_match = re.search(r'Βασικό Επιτόκιο ΕΚΤ \(DFR\):\s*\*\*([^*]+)\*\*', sec)
            if ecb_match:
                data['rates']['ecb_rate'] = ecb_match.group(1).strip()
            next_ecb_match = re.search(r'Επόμενη Συνεδρίαση ΕΚΤ:\s*\*\*([^*]+)\*\*', sec)
            if next_ecb_match:
                data['rates']['next_ecb'] = next_ecb_match.group(1).strip()
            cbc_match = re.search(r'Μέσο Επιτόκιο Στεγαστικών ΚΤΚ:\s*\*\*([^*]+)\*\*', sec)
            if cbc_match:
                data['rates']['cbc_mortgage_rate'] = cbc_match.group(1).strip()
            ex_pay_match = re.search(r'Μηνιαία δόση:\s*\*\*([^*]+)\*\*', sec)
            if ex_pay_match:
                data['rates']['example_payment'] = ex_pay_match.group(1).strip()
            ex_chg_match = re.search(r'Μεταβολή:\s*\*\*([^*]+)\*\*', sec)
            if ex_chg_match:
                data['rates']['example_change'] = ex_chg_match.group(1).strip()

        # CYPRUS NEWS
        elif 'ΚΥΠΡΟΣ' in sec_header:
            c_items = re.split(r'\n###\s+', sec)
            for ci in c_items[1:]:
                ci_lines = ci.strip().splitlines()
                if not ci_lines: continue
                c_title = ci_lines[0].strip()
                c_tag = 'Επιβεβαιωμένο'
                if '[ΕΞΕΛΙΣΣΟΜΕΝΟ]' in c_title:
                    c_tag = 'Εξελισσόμενο'
                    c_title = c_title.replace('[ΕΞΕΛΙΣΣΟΜΕΝΟ]', '').strip()
                elif '[ΕΠΙΒΕΒΑΙΩΜΕΝΟ]' in c_title:
                    c_tag = 'Επιβεβαιωμένο'
                    c_title = c_title.replace('[ΕΠΙΒΕΒΑΙΩΜΕΝΟ]', '').strip()

                c_why = ''
                why_m = re.search(r'\*\*Γιατί με αφορά:\*\*\s*(.+?)(?=\n\*\*Πηγή:|\n\n|\Z)', ci, re.DOTALL)
                if why_m:
                    c_why = why_m.group(1).strip()

                c_src = None
                src_m = re.search(r'\*\*Πηγή:\*\*\s*(.+)', ci)
                if src_m:
                    s_raw = re.findall(r'\[(.*?)\]\((.*?)\)', src_m.group(1))
                    if s_raw:
                        c_src = {'name': s_raw[0][0], 'url': s_raw[0][1]}

                c_body = []
                for cl in ci_lines[1:]:
                    cl_c = cl.strip()
                    if cl_c.startswith('**Γιατί με αφορά:') or cl_c.startswith('**Πηγή:'):
                        break
                    if cl_c and not cl_c.startswith('---'):
                        c_body.append(cl_c)

                data['cyprus'].append({
                    'title': c_title,
                    'tag': c_tag,
                    'why': c_why,
                    'source': c_src,
                    'body': ' '.join(c_body),
                    'is_portfolio': False
                })

        # WORLD NEWS
        elif 'ΔΙΕΘΝΗ' in sec_header:
            w_items = re.split(r'\n###\s+', sec)
            for wi in w_items[1:]:
                wi_lines = wi.strip().splitlines()
                if not wi_lines: continue
                w_title = wi_lines[0].strip()
                w_tag = 'Επιβεβαιωμένο'
                if '[ΕΞΕΛΙΣΣΟΜΕΝΟ]' in w_title:
                    w_tag = 'Εξελισσόμενο'
                    w_title = w_title.replace('[ΕΞΕΛΙΣΣΟΜΕΝΟ]', '').strip()
                elif '[ΕΠΙΒΕΒΑΙΩΜΕΝΟ]' in w_title:
                    w_tag = 'Επιβεβαιωμένο'
                    w_title = w_title.replace('[ΕΠΙΒΕΒΑΙΩΜΕΝΟ]', '').strip()

                w_why = ''
                why_m = re.search(r'\*\*Γιατί με αφορά:\*\*\s*(.+?)(?=\n\*\*Πηγή:|\n\n|\Z)', wi, re.DOTALL)
                if why_m:
                    w_why = why_m.group(1).strip()

                w_src = None
                src_m = re.search(r'\*\*Πηγή:\*\*\s*(.+)', wi)
                if src_m:
                    s_raw = re.findall(r'\[(.*?)\]\((.*?)\)', src_m.group(1))
                    if s_raw:
                        w_src = {'name': s_raw[0][0], 'url': s_raw[0][1]}

                w_body = []
                for wl in wi_lines[1:]:
                    wl_c = wl.strip()
                    if wl_c.startswith('**Γιατί με αφορά:') or wl_c.startswith('**Πηγή:'):
                        break
                    if wl_c and not wl_c.startswith('---'):
                        w_body.append(wl_c)

                data['world'].append({
                    'title': w_title,
                    'tag': w_tag,
                    'why': w_why,
                    'source': w_src,
                    'body': ' '.join(w_body)
                })

        # SPORTS
        elif 'ΑΘΛΗΤΙΚΑ' in sec_header or 'ΑΘΛΗΤΙΣΜΟΣ' in sec_header:
            team = None
            for sl in sec_lines:
                sl_c = sl.strip()
                sl_upper = sl_c.upper()
                if sl_c.startswith('###') or sl_c.startswith('##'):
                    if 'ΟΜΟΝΟΙΑ' in sl_upper:
                        team = 'omonoia'
                    elif 'MANCHESTER UNITED' in sl_upper or 'MAN UTD' in sl_upper:
                        team = 'manutd'
                    elif 'REAL MADRID' in sl_upper:
                        team = 'realmadrid'
                    elif 'FORMULA 1' in sl_upper or 'FORMULA1' in sl_upper or 'F1' in sl_upper:
                        team = 'formula1'
                    continue

                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    m_team = re.match(r'^\*\*(.*?):\*\*\s*(.*)$', item_text)
                    if m_team:
                        t_label = m_team.group(1).strip().upper()
                        t_rest = m_team.group(2).strip()
                        matched_team = None
                        if 'ΟΜΟΝΟΙΑ' in t_label:
                            matched_team = 'omonoia'
                        elif 'MANCHESTER' in t_label or 'MAN UTD' in t_label:
                            matched_team = 'manutd'
                        elif 'REAL' in t_label:
                            matched_team = 'realmadrid'
                        elif 'FORMULA' in t_label or 'F1' in t_label:
                            matched_team = 'formula1'
                        if matched_team:
                            team = matched_team
                            data['sports'][team]['raw'].append(t_rest)
                            data['sports'][team]['next_match'] = t_rest
                            continue

                if team and (sl_c.startswith('*') or sl_c.startswith('-')):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    data['sports'][team]['raw'].append(item_text)

                    if 'Τελευταίο αποτέλεσμα:' in item_text:
                        val = re.sub(r'^\*?\*?Τελευταίο αποτέλεσμα:\*?\*?\s*', '', item_text).strip()
                        data['sports'][team]['last_result'] = val
                    elif 'Επόμενος αγώνας:' in item_text:
                        val = re.sub(r'^\*?\*?Επόμενος αγώνας:\*?\*?\s*', '', item_text).strip()
                        data['sports'][team]['next_match'] = val
                    elif 'Highlights:' in item_text or 'Βίντεο Highlights:' in item_text or 'Βίντεο:' in item_text or 'YouTube' in item_text:
                        hl_match = re.search(r'\[(.*?)\]\((.*?)\)', item_text)
                        if hl_match:
                            data['sports'][team]['highlights'] = {
                                'title': hl_match.group(1).strip(),
                                'url': hl_match.group(2).strip()
                            }
                        else:
                            u_match = re.search(r'https?://\S+', item_text)
                            if u_match:
                                data['sports'][team]['highlights'] = {
                                    'title': 'YouTube Highlights',
                                    'url': u_match.group(0).strip(')')
                                }
                    elif 'Πηγή:' in item_text or 'Πηγές:' in item_text:
                        src_match = re.search(r'\[(.*?)\]\((.*?)\)', item_text)
                        if src_match:
                            data['sports'][team]['source'] = {
                                'name': src_match.group(1).strip(),
                                'url': src_match.group(2).strip()
                            }
                    else:
                        clean_news = re.sub(r'^\*?\*?(?:Μία γραμμή νέων|Νέα|Ρεπορτάζ\s*&\s*Νέα|Ρεπορτάζ):\*?\*?\s*', '', item_text).strip()
                        data['sports'][team]['news'].append(clean_news)

        # WEATHER
        elif 'ΚΑΙΡΟΣ' in sec_header:
            w_data = {'raw_items': [], 'source': None}
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if not item_text or item_text in ['--', '---']:
                        continue
                    if 'Πηγή:' in item_text:
                        src_parsed = re.findall(r'\[(.*?)\]\((.*?)\)', item_text)
                        if src_parsed:
                            w_data['source'] = {'name': src_parsed[0][0], 'url': src_parsed[0][1]}
                    else:
                        w_data['raw_items'].append(item_text)
            data['weather'] = w_data

        # DEVELOPMENTS
        elif 'ΕΞΕΛΙΞΕΙΣ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['developments'].append(item_text)

        # PORTFOLIO / STANDING INTERESTS
        elif 'Ο ΦΑΚΕΛΟΣ ΜΟΥ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['portfolio'].append(item_text)

        # DEADLINES
        elif 'ΤΙ ΝΑ ΚΑΝΩ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['deadlines'].append(item_text)

        # TOMORROW
        elif 'ΓΙΑ ΑΥΡΙΟ' in sec_header:
            for sl in sec_lines[1:]:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if re.match(r'^\d+\.', sl_c):
                    item_text = re.sub(r'^\d+\.\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['tomorrow'].append(item_text)

        # FOOTNOTES
        elif 'Υποσημείωση' in sec_header or 'ΥΠΟΣΗΜΕΙΩΣΗ' in sec_header:
            for sl in sec_lines:
                sl_c = sl.strip()
                if sl_c.startswith('---') or sl_c.startswith('***') or sl_c == '--' or not sl_c:
                    continue
                if sl_c.startswith('*') or sl_c.startswith('-'):
                    item_text = re.sub(r'^[*\-]\s*', '', sl_c).strip()
                    if item_text and item_text not in ['--', '---']:
                        data['footnotes'].append(item_text)

    return data


def get_latest_house_search():
    if not os.path.exists(HOUSE_SEARCH_DIR):
        return None

    md_files = sorted(glob.glob(os.path.join(HOUSE_SEARCH_DIR, 'limassol-listings-*.md')))
    html_files = sorted(glob.glob(os.path.join(HOUSE_SEARCH_DIR, 'limassol-listings-*.html')))

    if not md_files:
        return None

    latest_md = md_files[-1]
    latest_html = html_files[-1] if html_files else None

    m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(latest_md))
    date_str = m.group(1) if m else 'Τελευταία Εβδομάδα'

    stats = {
        'date': date_str,
        'unique_properties': '—',
        'top_picks_count': '—',
        'top_pick_highlights': '—',
        'html_filename': os.path.basename(latest_html) if latest_html else None,
        'md_filename': os.path.basename(latest_md)
    }

    try:
        with open(latest_md, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
            m_props = re.search(r'Πραγματικά Μοναδικά Φυσικά Ακίνητα\s*\|\s*\*\*([^\*]+)\*\*', content)
            if m_props:
                stats['unique_properties'] = m_props.group(1).strip()
            m_picks = re.search(r'Κύρια Λίστα \(Top Picks\)\s*\|\s*\*\*([^\*]+)\*\*', content)
            if m_picks:
                stats['top_picks_count'] = m_picks.group(1).strip()
    except Exception as e:
        print(f"Note: Could not parse deep House Search metrics: {e}")

    target_dir = os.path.join(BASE_DIR, 'house-search')
    docs_target_dir = os.path.join(DOCS_DIR, 'house-search')
    os.makedirs(target_dir, exist_ok=True)
    os.makedirs(docs_target_dir, exist_ok=True)

    if latest_html and os.path.exists(latest_html):
        shutil.copy2(latest_html, os.path.join(target_dir, 'latest.html'))
        shutil.copy2(latest_html, os.path.join(docs_target_dir, 'latest.html'))
        stats['local_url'] = 'house-search/latest.html'
    else:
        stats['local_url'] = None

    return stats


def build_search_index():
    index_entries = []
    pattern = os.path.join(BRIEFINGS_DIR, 'oracle-briefing-*.md')
    briefing_files = sorted(glob.glob(pattern), reverse=True)

    for bpath in briefing_files:
        bfilename = os.path.basename(bpath)
        m_date = re.search(r'(\d{4}-\d{2}-\d{2})', bfilename)
        date_str = m_date.group(1) if m_date else bfilename

        try:
            with open(bpath, 'r', encoding='utf-8', errors='replace') as f:
                content = f.read()
            data = parse_markdown(content, bfilename)

            def clean_plain(s):
                if not s: return ""
                s = re.sub(r'\[(.*?)\]\((https?://[^\s)]+)\)', r'\1', s)
                s = re.sub(r'\*+', '', s)
                return s.strip()

            if data['top_story'].get('title'):
                index_entries.append({
                    'date': date_str,
                    'section': '⭐ Πρώτο Θέμα',
                    'title': clean_plain(data['top_story']['title']),
                    'snippet': clean_plain(data['top_story']['body'][:180]) + '...',
                    'url': f"briefings/{date_str}.html#top-story" if date_str != datetime.now().strftime('%Y-%m-%d') else "#top-story"
                })

            for item in data['cyprus']:
                index_entries.append({
                    'date': date_str,
                    'section': '🇨🇾 Κύπρος',
                    'title': clean_plain(item['title']),
                    'snippet': clean_plain(item['body'][:160]) + '...',
                    'url': f"briefings/{date_str}.html#cyprus" if date_str != datetime.now().strftime('%Y-%m-%d') else "#cyprus"
                })

            for item in data['world']:
                index_entries.append({
                    'date': date_str,
                    'section': '🌍 Διεθνή',
                    'title': clean_plain(item['title']),
                    'snippet': clean_plain(item['body'][:160]) + '...',
                    'url': f"briefings/{date_str}.html#world" if date_str != datetime.now().strftime('%Y-%m-%d') else "#world"
                })

            for dl in data['deadlines']:
                clean_dl = clean_plain(dl)
                index_entries.append({
                    'date': date_str,
                    'section': '📅 Προθεσμίες',
                    'title': clean_dl.split('—')[0].strip(),
                    'snippet': clean_dl[:160] + '...',
                    'url': f"briefings/{date_str}.html#deadlines" if date_str != datetime.now().strftime('%Y-%m-%d') else "#deadlines"
                })

        except Exception as e:
            print(f"Error indexing {bpath}: {e}")

    docs_index_path = os.path.join(DOCS_DIR, 'search-index.json')
    with open(docs_index_path, 'w', encoding='utf-8') as f:
        json.dump(index_entries, f, ensure_ascii=False, indent=2)

    return index_entries


def generate_sparkline(change_str):
    if not change_str:
        return ""
    if '+' in change_str:
        stroke = "var(--up)"
        pts = "1,11 10,9 19,5 28,1"
    elif '-' in change_str:
        stroke = "var(--down)"
        pts = "1,1 10,5 19,9 28,11"
    else:
        stroke = "var(--ink-quiet)"
        pts = "1,6 10,6 19,6 28,6"
    return f'<svg class="w-7 h-3 inline-block ml-1.5 opacity-80 flex-shrink-0" viewBox="0 0 29 12" aria-hidden="true"><polyline fill="none" stroke="{stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" points="{pts}" /></svg>'


def render_evening_html(data, house_stats, search_index, is_subfolder=False, date_slug=None):
    date_display = data.get('date_str') or '10 Σεπτεμβρίου 2026'
    time_display = data.get('time_str') or '19:30'
    read_time = data.get('read_time') or "4'"

    if not date_slug:
        m_iso = re.search(r'(\d{4}-\d{2}-\d{2})', date_display)
        iso_date = m_iso.group(1) if m_iso else datetime.now().strftime('%Y-%m-%d')
    else:
        iso_date = date_slug

    gen_iso = f"{iso_date}T{time_display}:00+03:00" if ':' in time_display else f"{iso_date}T19:30:00+03:00"

    urls = resolve_edition_urls(iso_date, is_subfolder)
    home_url = urls['home']
    morning_url = urls['morning']
    midday_url = urls['midday']
    evening_url = urls['evening']
    live_wire_url = urls['live_wire']
    search_index_url = urls['search_index']
    edition_switcher_html = render_edition_switcher_html(urls, 'evening')

    # Ticker Items
    ticker_spans = []
    for d in data.get('dashboard', []):
        color_cls = "text-[var(--up)]" if "+" in d['change'] else ("text-[var(--down)]" if "-" in d['change'] else "text-[var(--ink-quiet)]")
        spk = generate_sparkline(d['change'])
        ticker_spans.append(f'<span class="inline-flex items-center gap-1.5"><span class="font-bold text-[var(--ink)]">{d["asset"]}:</span> <span class="text-[var(--ink-body)]">{d["price"]}</span> <span class="{color_cls} font-semibold inline-flex items-center">{d["change"]}{spk}</span></span>')
    ticker_html = ' · '.join(ticker_spans) + ' · ' + ' · '.join(ticker_spans) if ticker_spans else ''

    # Market Tables (Two-Tier: Macro Radar vs Tech Equities Watchlist)
    macro_rows = []
    stock_rows = []

    for d in data.get('dashboard', []):
        is_up = '+' in d['change']
        is_down = '-' in d['change']
        badge_cls = "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" if is_up else ("bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20" if is_down else "bg-gray-500/10 text-gray-600 border-gray-500/20")
        spk = generate_sparkline(d['change'])
        comment = md_to_inline_html(d.get('date_ref', ''))

        row_html = f'''
        <tr class="border-b border-[var(--rule)] hover:bg-[var(--paper-raised)] transition">
          <td class="py-3 px-3.5 font-bold text-[var(--ink)] flex items-center gap-1.5">
            <span>{d["asset"]}</span>
          </td>
          <td class="py-3 px-3.5 font-mono font-bold text-[var(--ink)]">{d["price"]}</td>
          <td class="py-3 px-3.5 font-mono">
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-bold {badge_cls}">
              <span>{d["change"]}</span> {spk}
            </span>
          </td>
          <td class="py-3 px-3.5 text-xs text-[var(--ink-body)]">{comment}</td>
        </tr>
        '''
        if d.get('category') == 'Μετοχές Τεχνολογίας':
            stock_rows.append(row_html)
        else:
            macro_rows.append(row_html)

    if stock_rows:
        market_section_html = f'''
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <!-- Macro Indices & FX -->
          <div class="lg:col-span-6 card overflow-hidden shadow-xs border border-[var(--rule)]">
            <div class="p-3.5 bg-[var(--paper)] border-b border-[var(--rule)] flex items-center justify-between">
              <h3 class="font-bold text-xs uppercase tracking-wider text-[var(--ink)] flex items-center gap-1.5">
                <span>🏛️</span> <span>Κύριοι Δείκτες, Συνάλλαγμα & Crypto</span>
              </h3>
              <span class="text-[10px] font-mono text-[var(--accent)] font-bold">MACRO & FX</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs">
                <thead class="bg-[var(--paper)] text-[10px] uppercase text-[var(--ink-quiet)] font-mono border-b border-[var(--rule)]">
                  <tr>
                    <th class="py-2.5 px-3.5">Αγορά / Τίτλος</th>
                    <th class="py-2.5 px-3.5 font-mono">Κλείσιμο</th>
                    <th class="py-2.5 px-3.5 font-mono">Μεταβολή</th>
                    <th class="py-2.5 px-3.5">Σχόλιο</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[var(--rule)] font-sans">
                  {''.join(macro_rows)}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Tech Stocks Watchlist -->
          <div class="lg:col-span-6 card overflow-hidden shadow-xs border border-indigo-500/30">
            <div class="p-3.5 bg-gradient-to-r from-[var(--paper)] to-indigo-950/10 border-b border-[var(--rule)] flex items-center justify-between">
              <h3 class="font-bold text-xs uppercase tracking-wider text-[var(--ink)] flex items-center gap-1.5">
                <span>💻</span> <span>Μετοχές Τεχνολογίας (Watchlist)</span>
              </h3>
              <span class="text-[10px] font-mono text-indigo-500 font-bold">TECH RADAR</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs">
                <thead class="bg-[var(--paper)] text-[10px] uppercase text-[var(--ink-quiet)] font-mono border-b border-[var(--rule)]">
                  <tr>
                    <th class="py-2.5 px-3.5">Μετοχή</th>
                    <th class="py-2.5 px-3.5 font-mono">Τιμή</th>
                    <th class="py-2.5 px-3.5 font-mono">Μεταβολή</th>
                    <th class="py-2.5 px-3.5">Σχόλιο</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[var(--rule)] font-sans">
                  {''.join(stock_rows)}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        '''
    else:
        market_section_html = f'''
        <div class="card overflow-hidden shadow-xs">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="bg-[var(--paper)] text-xs uppercase text-[var(--ink-quiet)] font-mono border-b border-[var(--rule)]">
                <tr>
                  <th class="py-3 px-4">Αγορά / Τίτλος</th>
                  <th class="py-3 px-4 font-mono">Κλείσιμο</th>
                  <th class="py-3 px-4 font-mono">Μεταβολή</th>
                  <th class="py-3 px-4">Επιτελικό Σχόλιο</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--rule)] font-sans">
                {''.join(macro_rows)}
              </tbody>
            </table>
          </div>
        </div>
        '''

    # Executive Pulse (60-second summary)
    pulse_items = data.get('executive_pulse', [])
    pulse_html = ""
    if pulse_items:
        pulse_cols = []
        icons = ["📊", "🇨🇾", "⚽"]
        for idx, itm in enumerate(pulse_items):
            ico = icons[idx] if idx < len(icons) else "⚡"
            pulse_cols.append(f'''
            <div class="p-3.5 rounded-xl bg-[var(--paper)] border border-[var(--rule)]">
              <div class="text-xs text-[var(--ink-body)] leading-relaxed">
                <span class="mr-1 text-sm">{ico}</span> {md_to_inline_html(itm)}
              </div>
            </div>
            ''')
        pulse_html = f'''
        <!-- ⚡ 60-SECOND EXECUTIVE PULSE -->
        <div class="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-amber-500/10 via-[var(--paper-raised)] to-[var(--paper-raised)] border border-amber-500/30 shadow-xs">
          <div class="flex items-center justify-between gap-2 mb-3 pb-2 border-b border-[var(--rule)]">
            <span class="text-xs font-mono font-bold uppercase tracking-wider text-[var(--accent)] flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-[var(--accent)] animate-ping"></span> ⚡ ΣΥΝΟΨΗ 60 ΔΕΥΤΕΡΟΛΕΠΤΩΝ
            </span>
            <span class="text-[10px] font-mono text-[var(--ink-quiet)]">EXECUTIVE PULSE</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            {''.join(pulse_cols)}
          </div>
        </div>
        '''

    # Tomorrow's Limassol Outlook
    tw = data.get('tomorrow_weather', {})
    tomorrow_weather_html = ""
    if tw:
        temp_val = md_to_inline_html(tw.get('temp', '34°C / 24°C'))
        fc_val = md_to_inline_html(tw.get('forecast', 'Αίθριος & διαυγής ουρανός'))
        wind_val = md_to_inline_html(tw.get('wind', '16 km/h ΝΔ'))
        tomorrow_weather_html = f'''
        <!-- ==================== 🌤️ 5. ΑΥΡΙΑΝΗ ΠΡΟΓΝΩΣΗ ΛΕΜΕΣΟΥ ==================== -->
        <section id="tomorrow-outlook" class="scroll-mt-24">
          <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
            <h2 class="t-section flex items-center gap-2">
              <span>🌤️</span> <span>Αυριανή Πρόγνωση & Συνθήκες Λεμεσού</span>
            </h2>
            <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">TOMORROW OUTLOOK</span>
          </div>
          <div class="card p-5 bg-gradient-to-br from-[var(--paper-raised)] via-[var(--paper-raised)] to-amber-500/5 border border-amber-500/20 rounded-2xl shadow-xs">
            <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 text-xs">
              <div class="flex items-center gap-3 p-3 rounded-xl bg-[var(--paper)] border border-[var(--rule)]">
                <span class="text-2xl flex-shrink-0">☀️</span>
                <div>
                  <div class="font-bold text-[var(--ink)] text-sm">{temp_val}</div>
                  <div class="text-[11px] text-[var(--ink-quiet)]">{fc_val}</div>
                </div>
              </div>
              <div class="flex items-center gap-3 p-3 rounded-xl bg-[var(--paper)] border border-[var(--rule)]">
                <span class="text-2xl flex-shrink-0">💨</span>
                <div>
                  <div class="font-bold text-[var(--ink)] text-sm">Άνεμοι</div>
                  <div class="text-[11px] text-[var(--ink-quiet)]">{wind_val}</div>
                </div>
              </div>
              <div class="flex items-center gap-3 p-3 rounded-xl bg-[var(--paper)] border border-[var(--rule)]">
                <span class="text-2xl flex-shrink-0">🌊</span>
                <div>
                  <div class="font-bold text-[var(--ink)] text-sm">Θαλάσσιες Συνθήκες</div>
                  <div class="text-[11px] text-[var(--ink-quiet)]">Ήρεμη θάλασσα · Ιδανικό πρωινό</div>
                </div>
              </div>
            </div>
          </div>
        </section>
        '''

    # Sports Cards
    sports = data.get('sports', {})
    sports_config = [
        {
            'key': 'omonoia',
            'name': 'ΟΜΟΝΟΙΑ ΛΕΥΚΩΣΙΑΣ',
            'icon': '☘️',
            'league': 'CYPRUS LEAGUE & EUROPE',
            'border': 'border-emerald-700/30 dark:border-emerald-600/40',
            'header_bg': 'bg-gradient-to-r from-emerald-900 to-green-950',
            'search_q': 'Omonoia FC highlights 2026'
        },
        {
            'key': 'manutd',
            'name': 'MANCHESTER UNITED',
            'icon': '🔴',
            'league': 'UEFA CHAMPIONS LEAGUE',
            'border': 'border-red-700/30 dark:border-red-600/40',
            'header_bg': 'bg-gradient-to-r from-red-900 to-stone-950',
            'search_q': 'Manchester United highlights 2026'
        },
        {
            'key': 'realmadrid',
            'name': 'REAL MADRID',
            'icon': '⚪',
            'league': 'SPANISH LA LIGA',
            'border': 'border-amber-700/30 dark:border-amber-600/40',
            'header_bg': 'bg-gradient-to-r from-indigo-950 via-slate-900 to-purple-950',
            'search_q': 'Real Madrid highlights 2026'
        },
        {
            'key': 'formula1',
            'name': 'FORMULA 1',
            'icon': '🏎️',
            'league': 'FIA WORLD CHAMPIONSHIP',
            'border': 'border-red-600/30 dark:border-red-500/40',
            'header_bg': 'bg-gradient-to-r from-neutral-900 to-red-950',
            'search_q': 'Formula 1 highlights 2026'
        }
    ]

    sports_cards = []
    for sc in sports_config:
        s_data = sports.get(sc['key'], {})
        last_res = s_data.get('last_result') or ''
        next_m = s_data.get('next_match') or ''
        news_list = s_data.get('news') or []
        src = s_data.get('source')
        hl = s_data.get('highlights')

        if next_m in ['--', '---']: next_m = ''
        if last_res in ['--', '---']: last_res = ''
        clean_news = [n for n in news_list if n not in ['--', '---', '']]

        last_res_html = f'''
        <div class="flex items-start gap-2 text-xs">
          <span class="font-bold text-[var(--ink)] flex-shrink-0">⏱️ Τελ. Αποτέλεσμα:</span>
          <span class="text-[var(--ink-body)]">{md_to_inline_html(last_res)}</span>
        </div>''' if last_res else ""

        next_match_html = f'''
        <div class="flex items-start gap-2 text-xs">
          <span class="font-bold text-[var(--ink)] flex-shrink-0">📅 Επόμενος Αγώνας:</span>
          <span class="text-[var(--ink-body)] font-medium">{md_to_inline_html(next_m)}</span>
        </div>''' if next_m else '<div class="text-xs text-[var(--ink-quiet)] italic">Αναμονή ορισμού επόμενου αγώνα</div>'

        news_html = f'''
        <div class="text-xs text-[var(--ink-body)] bg-[var(--paper)] p-3 rounded border border-[var(--rule)] leading-relaxed">
          <strong class="text-[var(--accent)] font-semibold block mb-1">📋 Ρεπορτάζ & Νέα:</strong>
          {' '.join(md_to_inline_html(n) for n in clean_news)}
        </div>''' if clean_news else ""

        src_html = f'''
        <div class="text-[11px] text-[var(--ink-quiet)] flex items-center justify-between pt-2 border-t border-[var(--rule)]">
          <span>Επίσημη Πηγή:</span>
          <a href="{src['url']}" target="_blank" rel="noopener noreferrer" class="text-[var(--accent)] hover:underline font-medium">{src['name']}</a>
        </div>''' if src else ""

        search_url = hl['url'] if hl and hl.get('url') else f"https://www.youtube.com/results?search_query={sc['search_q'].replace(' ', '+')}"
        search_title = hl['title'] if hl and hl.get('title') else "YouTube Highlights & Match Hub"

        sports_cards.append(f'''
        <article class="card overflow-hidden flex flex-col justify-between border rounded-2xl shadow-xs {sc['border']}">
          <div>
            <div class="{sc['header_bg']} p-4 text-white flex items-center justify-between">
              <div class="flex items-center gap-2.5">
                <span class="text-2xl">{sc['icon']}</span>
                <h3 class="font-masthead font-bold text-sm tracking-wide text-white">{sc['name']}</h3>
              </div>
              <span class="t-meta uppercase tracking-wider px-2 py-0.5 rounded-full text-[10px] bg-black/40 text-white/90 border border-white/10">
                {sc['league']}
              </span>
            </div>
            <div class="p-5 space-y-3">
              {last_res_html}
              {next_match_html}
              {news_html}
              {src_html}
            </div>
          </div>
          <div class="p-4 pt-0">
            <a href="{search_url}" target="_blank" rel="noopener noreferrer"
               class="inline-flex items-center justify-center gap-2 w-full py-2 px-3 rounded-lg bg-red-600/10 hover:bg-red-600/20 text-red-600 dark:text-red-400 text-xs font-bold border border-red-500/30 transition">
              <span>▶</span> <span>{search_title}</span>
            </a>
          </div>
        </article>
        ''')
    sports_html = '\n'.join(sports_cards)

    # Evening News Wire Cards (Curated with Broadsheet Images & Typography)
    evening_news_cards = []
    for idx, item in enumerate(data.get('evening_news', []), 1):
        raw_title = item.get('title', '')
        raw_title = re.sub(r'\[(ΕΠΙΒΕΒΑΙΩΜΕΝΟ|ΕΞΕΛΙΣΣΟΜΕΝΟ)\]\s*', '', raw_title)
        raw_title = re.sub(r'^[🇨🇾🌍🇬🇷🇪🇺]\s*', '', raw_title).strip()
        clean_title = md_to_inline_html(raw_title)
        clean_body = md_to_inline_html(item.get('body', ''))
        clean_why = md_to_inline_html(item.get('why', ''))

        region = item.get('region', '🇨🇾 ΚΥΠΡΟΣ')
        reg_badge_cls = "bg-[var(--accent)] text-white" if 'ΚΥΠΡΟΣ' in region else "bg-indigo-900/80 text-white"

        item_url = item['source']['url'] if item.get('source') else ''
        img_url, cat_name = resolve_image(item_url, clean_title, region)

        src_html = ""
        if item.get('source'):
            src_html = f'''<a href="{item['source']['url']}" target="_blank" rel="noopener noreferrer" class="t-meta font-bold text-[var(--accent)] hover:underline flex items-center gap-1"><span>{item['source']['name']}</span> <span>➔</span></a>'''

        why_html = f'''
        <div class="t-meta text-[var(--accent)] bg-[var(--paper)] p-3 rounded mb-3 border-l-2 border-[var(--accent)] leading-relaxed">
          <strong class="font-bold">Γιατί με αφορά:</strong> {clean_why}
        </div>''' if clean_why else ""

        evening_news_cards.append(f'''
        <article class="card overflow-hidden flex flex-col justify-between hover:border-[var(--rule-strong)] transition shadow-xs">
          <div>
            <div class="h-44 bg-[var(--paper)] relative overflow-hidden">
              <img src="{img_url}" alt="{clean_title}" class="w-full h-full object-cover" onerror="this.onerror=null; this.src='{TOPIC_FALLBACKS['general']}';">
              <span class="absolute top-2.5 left-2.5 {reg_badge_cls} t-meta px-2 py-0.5 rounded shadow-xs font-bold uppercase">{region}</span>
              <span class="absolute top-2.5 right-2.5 bg-emerald-500/90 text-white font-bold t-meta px-2 py-0.5 rounded shadow-xs">Επιβεβαιωμένο</span>
            </div>
            <div class="p-5 sm:p-6">
              <h3 class="t-title mb-2.5 text-[var(--ink)]">
                {clean_title}
              </h3>
              <p class="t-body-sm leading-relaxed mb-3 text-[var(--ink-body)]">
                {clean_body}
              </p>
              {why_html}
            </div>
          </div>
          <div class="p-5 sm:p-6 pt-0 border-t border-[var(--rule)] flex items-center justify-between">
            <span class="t-meta text-[var(--ink-quiet)] font-mono">19:30 EEST</span>
            {src_html}
          </div>
        </article>
        ''')
    evening_news_html = '\n'.join(evening_news_cards)

    evening_news_section = f'''
    <!-- ==================== 📰 2. ΑΠΟΓΕΥΜΑΤΙΝΗ ΕΠΙΚΑΙΡΟΤΗΤΑ ==================== -->
    <section id="evening-news" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>📰</span> <span>Απογευματινή Επικαιρότητα & Εξελίξεις</span>
        </h2>
        <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">CURATED DIGEST</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {evening_news_html}
      </div>
    </section>
    ''' if evening_news_cards else ""

    # Night Radar Items
    radar_items = []
    for idx, r in enumerate(data.get('night_radar', []), 1):
        clean_r = md_to_inline_html(r)
        icons = ["🌏", "🛡️", "🌅"]
        ico = icons[idx-1] if idx <= len(icons) else "⚡"
        radar_items.append(f'''
        <li class="flex items-start gap-3 p-3.5 rounded-xl bg-[var(--paper-raised)] border border-[var(--rule)]">
          <span class="text-xl flex-shrink-0 mt-0.5">{ico}</span>
          <div class="text-xs text-[var(--ink-body)] leading-relaxed flex-grow">
            {clean_r}
          </div>
        </li>
        ''')
    radar_html = '\n'.join(radar_items)

    top_body = md_to_inline_html(data.get('top_story', {}).get('body', ''))

    html = f'''<!DOCTYPE html>
<html lang="el">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <title>THE ORACLE SOVEREIGN — 🌙 Night Debrief — {date_display}</title>
  <script src="https://cdn.tailwindcss.com/3.4.16"></script>
  <script>
    tailwind.config = {{ darkMode: 'class' }};
  </script>
  <script>
    (function () {{
      var s = localStorage.getItem('oracle-theme');
      var d = s ? s === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (d) document.documentElement.classList.add('dark');
    }})();
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;900&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;0,6..72,700;1,6..72,400&family=Inter:wght@300;400;500;600;700&display=swap');

    :root {{
      --paper: #f6f3ec;
      --paper-raised: #fffdf8;
      --rule: #d9d3c5;
      --rule-strong: #b3aa96;
      --ink: #17150f;
      --ink-body: #2e2a22;
      --ink-quiet: #6d675a;
      --accent: #8a5320;
      --up: #1f6b3f;
      --down: #a3282b;
      --r-md: 8px;
    }}

    .dark {{
      --paper: #14120e;
      --paper-raised: #1c1a15;
      --rule: #2e2920;
      --rule-strong: #4a4233;
      --ink: #ede8dc;
      --ink-body: #cfc8ba;
      --ink-quiet: #8c8373;
      --accent: #d4954b;
      --up: #43a047;
      --down: #e53935;
    }}

    body {{
      background-color: var(--paper);
      color: var(--ink-body);
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
    }}

    .font-masthead {{ font-family: 'Cinzel', serif; }}
    .font-editorial {{ font-family: 'Newsreader', serif; }}
    .t-masthead {{ font-family: 'Cinzel', serif; font-size: clamp(2rem, 5vw, 3.25rem); letter-spacing: 0.08em; font-weight: 700; line-height: 1.1; }}
    .t-section {{ font-family: 'Cinzel', serif; font-size: 1.25rem; font-weight: 700; letter-spacing: 0.04em; color: var(--ink); }}
    .card {{ background-color: var(--paper-raised); border: 1px solid var(--rule); border-radius: var(--r-md); }}

    .ticker-wrap {{ overflow: hidden; white-space: nowrap; }}
    .ticker-content {{ display: inline-block; animation: tickerAnimation 40s linear infinite; }}
    .ticker-wrap:hover .ticker-content {{ animation-play-state: paused; }}
    @keyframes tickerAnimation {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}
  </style>
</head>
<body class="antialiased min-h-screen">

  <!-- TOP BAR & STATUS -->
  <div class="bg-[var(--paper-raised)] border-b border-[var(--rule)] text-xs py-1.5 px-4">
    <div class="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-2">
      <div class="flex flex-wrap items-center gap-3">
        <span id="freshness" data-generated="{gen_iso}"
              class="inline-flex items-center px-2 py-0.5 rounded font-mono font-semibold text-[11px] bg-amber-500/10 text-amber-800 dark:text-amber-300">
          🌙 19:30 · {date_display}
        </span>

        <!-- Edition Switcher -->
{edition_switcher_html}
      </div>

      <!-- Global Clocks Bar -->
      <div id="globalClocks" class="hidden xl:flex items-center gap-2.5 font-mono text-[11px] text-[var(--ink-quiet)] border-l border-[var(--rule)] pl-3">
        <span class="inline-flex items-center gap-1">🇨🇾 <strong>CY</strong> <span id="clockCY">--:--</span></span>
        <span>·</span>
        <span class="inline-flex items-center gap-1">🇬🇧 <strong>LON</strong> <span id="clockLON">--:--</span></span>
        <span>·</span>
        <span class="inline-flex items-center gap-1">🇺🇸 <strong>NYC</strong> <span id="clockNYC">--:--</span></span>
        <span>·</span>
        <span class="inline-flex items-center gap-1">🇯🇵 <strong>TYO</strong> <span id="clockTYO">--:--</span></span>
      </div>

      <!-- Controls -->
      <div class="flex items-center gap-2">
        <button id="themeToggle" class="px-2 py-1 rounded border border-[var(--rule)] text-xs hover:bg-[var(--paper)] transition" title="Εναλλαγή θέματος">🌓</button>
      </div>
    </div>
  </div>

  <!-- MASTHEAD -->
  <header class="border-b-4 border-double border-[var(--rule-strong)] py-8 px-4 bg-[var(--paper-raised)]">
    <div class="max-w-7xl mx-auto text-center">
      <div class="flex justify-between items-center text-xs uppercase text-[var(--ink-quiet)] border-b border-[var(--rule)] pb-2 mb-4 font-mono">
        <div>ΕΤΟΣ 2026 · DAILY BRIEFING</div>
        <div class="font-bold text-[var(--accent)]">🌙 NIGHT DEBRIEF & CLOSING BELL</div>
        <div>ONE-READER EDITION</div>
      </div>

      <h1 class="t-masthead text-[var(--ink)] mb-2 uppercase">
        THE ORACLE SOVEREIGN
      </h1>
      <p class="font-editorial italic text-lg sm:text-xl text-[var(--ink-quiet)] max-w-2xl mx-auto">
        Απογευματινή Επιτελική Ανασκόπηση, Τελικά Κλεισίματα Αγορών, Αθλητικό Πρόγραμμα & Νυχτερινό Ραντάρ
      </p>

      <div class="flex flex-wrap justify-center items-center gap-3 mt-4 pt-3 border-t border-[var(--rule)] text-xs text-[var(--ink-quiet)] font-mono">
        <span>📅 {date_display}</span>
        <span>·</span>
        <span>⏰ 19:30 ώρα Κύπρου</span>
        <span>·</span>
        <span>⏱️ {read_time} ανάγνωση</span>
        <span>·</span>
        <a href="{home_url}" class="text-[var(--accent)] hover:underline font-bold">🏛️ Πύλη The Oracle</a>
      </div>
    </div>
  </header>

  <!-- LIVE MARKET TICKER -->
  <div class="bg-[var(--paper)] text-[var(--ink)] py-2 border-y border-[var(--rule)] text-xs ticker-wrap">
    <div class="ticker-content space-x-8 font-mono">
      {ticker_html}
    </div>
  </div>

  <!-- ⚡ 24/7 REAL-TIME LIVE WIRE BAR -->
  <div id="liveWireBar" class="bg-[var(--paper-raised)] text-[var(--ink)] py-2 px-4 border-b border-[var(--rule)] text-xs">
    <div class="max-w-6xl mx-auto flex items-center justify-between gap-3">
      <div class="flex items-center gap-2 flex-shrink-0">
        <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-red-600 text-white font-mono text-[10px] font-bold tracking-wider uppercase shadow-xs">
          <span class="w-1.5 h-1.5 rounded-full bg-white animate-ping"></span> 24/7 WIRE
        </span>
      </div>
      <div id="liveWireTicker" class="overflow-hidden whitespace-nowrap text-xs text-[var(--ink-body)] flex-grow font-sans min-w-0">
        <span class="text-[var(--ink-quiet)] italic">Συνεχής ροή έκτακτης ειδησεογραφίας...</span>
      </div>
      <button id="openWireDrawerBtn" class="flex-shrink-0 text-xs font-bold text-[var(--accent)] hover:underline flex items-center gap-1">
        <span>Προβολή Όλων (50+)</span> <span>➔</span>
      </button>
    </div>
  </div>

  <!-- MAIN CONTAINER -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">

    <!-- 🎙️ AUDIO BRIEFING PLAYER -->
    <div id="audioBriefingPlayer" class="p-4 bg-[var(--paper-raised)] border border-[var(--rule)] rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-xs">
      <div class="flex items-center gap-3.5">
        <button id="audioPlayBtn" class="w-11 h-11 rounded-full bg-[var(--accent)] text-white flex items-center justify-center shadow hover:opacity-90 transition font-bold text-lg flex-shrink-0" aria-label="Αναπαραγωγή ηχητικής σύνοψης">
          ▶
        </button>
        <div>
          <div class="text-xs font-bold text-[var(--ink)] flex items-center gap-2">
            <span>🎙️ Ακρόαση Απογευματινής Σύνοψης (The Sovereign Audio Debrief)</span>
            <span id="audioLiveBadge" class="hidden text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-mono font-semibold">LIVE</span>
          </div>
          <div id="audioStatusText" class="text-xs text-[var(--ink-quiet)]">
            Επιτελική σύνοψη κλεισίματος ~1.5 λεπτού · Πατήστε Play για φωνητική ανάγνωση
          </div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button id="audioSpeedBtn" class="text-xs font-mono px-2.5 py-1 rounded border border-[var(--rule)] bg-[var(--paper)] hover:border-[var(--accent)] text-[var(--ink-body)]" title="Ταχύτητα ανάγνωσης">
          1.0x
        </button>
        <button id="audioStopBtn" class="text-xs px-2.5 py-1 rounded border border-[var(--rule)] bg-[var(--paper)] hover:bg-[var(--down)] hover:text-white text-[var(--ink-quiet)] hidden" title="Διακοπή">
          ⏹ Διακοπή
        </button>
      </div>
    </div>

    {pulse_html}

    <!-- ==================== 🏁 1. ΤΟ ΑΠΟΤΥΠΩΜΑ ΤΗΣ ΗΜΕΡΑΣ ==================== -->
    <section id="top-story" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🏁</span> <span>Το Αποτύπωμα της Ημέρας</span>
        </h2>
        <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">EXECUTIVE RECAP</span>
      </div>

      <div class="card overflow-hidden shadow-sm">
        <div class="grid grid-cols-1 md:grid-cols-12 gap-0">
          <div class="md:col-span-5 relative min-h-[220px] bg-[var(--paper)]">
            <img src="https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&q=80" 
                 alt="Evening Capital Recap" 
                 class="w-full h-full object-cover object-center">
            <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent flex items-end p-4">
              <span class="px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider bg-[var(--accent)] text-white font-bold">
                ΑΠΟΓΕΥΜΑΤΙΝΗ ΣΥΝΘΕΣΗ
              </span>
            </div>
          </div>
          <div class="md:col-span-7 p-6 sm:p-7 flex flex-col justify-between">
            <div>
              <div class="flex items-center gap-2 text-xs uppercase tracking-wider mb-2 text-[var(--accent)] font-semibold">
                <span>Τελική Αποτίμηση</span>
                <span>·</span>
                <span class="text-[var(--ink-quiet)] font-mono">{date_display}</span>
              </div>
              <h3 class="t-lead mb-3">
                Ημερήσιο Οικονομικό & Στρατηγικό Αποτύπωμα
              </h3>
              <p id="topStoryBody" class="t-body leading-relaxed mb-4">
                {top_body}
              </p>
            </div>
            <div class="pt-4 mt-4 border-t border-[var(--rule)] flex items-center justify-between text-xs text-[var(--ink-quiet)] font-mono">
              <span>Ώρα Καταγραφής: 19:30 EEST</span>
              <span>The Oracle Sovereign</span>
            </div>
          </div>
        </div>
      </div>
    </section>

    {evening_news_section}

    <!-- ==================== 🔔 3. CLOSING BELL & ΑΓΟΡΕΣ ==================== -->
    <section id="closing-bell" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🔔</span> <span>Closing Bell & Αγορές</span>
        </h2>
        <span class="text-xs font-mono text-[var(--ink-quiet)] ml-auto">ΤΕΛΙΚΑ ΚΛΕΙΣΙΜΑΤΑ</span>
      </div>

      {market_section_html}
    </section>

    <!-- ==================== ⚽ 4. ΑΠΟΓΕΥΜΑΤΙΝΟΣ ΑΘΛΗΤΙΣΜΟΣ ==================== -->
    <section id="sports-radar" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>⚽</span> <span>Απογευματινός Αθλητισμός & Πρόγραμμα</span>
        </h2>
        <span class="text-xs font-mono text-[var(--ink-quiet)] ml-auto">HIGHLIGHTS & FIXTURES</span>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-5">
        {sports_html}
      </div>
    </section>

    {tomorrow_weather_html}

    <!-- ==================== 🌌 6. ΝΥΧΤΕΡΙΝΟ ΡΑΝΤΑΡ ΚΙΝΔΥΝΟΥ ==================== -->
    <section id="night-radar" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🌌</span> <span>Νυχτερινό Ραντάρ Κινδύνου</span>
        </h2>
        <span class="text-xs font-mono text-indigo-500 uppercase font-bold ml-auto">OVERNIGHT WATCH</span>
      </div>

      <div class="card p-5 sm:p-6 bg-gradient-to-br from-[var(--paper-raised)] via-[var(--paper-raised)] to-indigo-950/10 border-indigo-500/20">
        <p class="text-xs text-[var(--ink-quiet)] mb-4 font-mono">
          Κρίσιμοι άξονες παρακολούθησης κατά τη διάρκεια της νύχτας μέχρι το επόμενο πρωινό άνοιγμα:
        </p>
        <ul class="space-y-3">
          {radar_html}
        </ul>
      </div>
    </section>

    <!-- ==================== 🏛️ 7. ΣΥΝΔΕΣΗ ΜΕ ΤΟ ΠΡΩΙΝΟ BROADSHEET ==================== -->
    <div class="card p-6 bg-gradient-to-r from-amber-500/5 via-[var(--paper-raised)] to-[var(--paper-raised)] border-l-4 border-[var(--accent)] flex flex-wrap items-center justify-between gap-4 shadow-xs">
      <div class="max-w-2xl">
        <div class="text-xs font-mono font-bold uppercase tracking-wider text-[var(--accent)] mb-1">
          🏛️ THE SOVEREIGN MORNING BROADSHEET
        </div>
        <h3 class="font-editorial text-xl font-bold text-[var(--ink)] mb-1">
          Χρειάζεστε την πλήρη ανάλυση της ημέρας;
        </h3>
        <p class="text-xs text-[var(--ink-body)] leading-relaxed">
          Ανατρέξτε στην πρωινή έκδοση (07:30) για το πλήρες ρεπορτάζ Κύπρου, τον υπολογιστή δανείων Euribor, την εβδομαδιαία έκθεση ακινήτων Λεμεσού και τα διεθνή νέα.
        </p>
      </div>
      <a href="{morning_url}" class="inline-flex items-center gap-2 px-4 py-2.5 rounded-lg bg-[var(--accent)] text-white font-bold text-xs hover:opacity-90 transition shadow">
        <span>Άνοιγμα Πρωινού Broadsheet</span> <span>➔</span>
      </a>
    </div>

  </main>

  <!-- FOOTER -->
  <footer class="mt-16 border-t border-[var(--rule)] bg-[var(--paper-raised)] py-8 px-4 text-xs text-[var(--ink-quiet)]">
    <div class="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-4">
      <div class="space-y-1">
        <div class="font-bold text-[var(--ink)] font-masthead">THE ORACLE SOVEREIGN</div>
        <div>Confidential Executive Briefing · Night Debrief Edition</div>
      </div>
      <div class="flex items-center gap-4 font-mono text-[11px]">
        <a href="{home_url}" class="hover:text-[var(--accent)]">Αρχική</a>
        <span>·</span>
        <a href="{morning_url}" class="hover:text-[var(--accent)]">Πρωινό Broadsheet</a>
        <span>·</span>
        <a href="{midday_url}" class="hover:text-[var(--accent)]">Μεσημβρινός Παλμός</a>
        <span>·</span>
        <button onclick="window.print()" class="hover:text-[var(--accent)]">Εκτύπωση PDF</button>
      </div>
    </div>
  </footer>

  <!-- ⚡ 24/7 LIVE WIRE DRAWER MODAL -->
  <div id="wireDrawerModal" class="fixed inset-0 bg-black/50 backdrop-blur-xs z-50 hidden flex justify-end transition-opacity duration-300">
    <div class="w-full max-w-md bg-[var(--paper-raised)] h-full shadow-2xl p-5 overflow-y-auto flex flex-col border-l border-[var(--rule)]">
      <div class="flex items-center justify-between pb-3 border-b border-[var(--rule)] mb-4">
        <div class="flex items-center gap-2">
          <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></span>
          <h3 class="font-bold text-sm tracking-wide uppercase text-[var(--ink)]">24/7 Live Wire Intelligence</h3>
        </div>
        <button id="closeWireDrawerBtn" class="text-2xl text-[var(--ink-quiet)] hover:text-[var(--ink)] leading-none px-2">&times;</button>
      </div>
      <div class="text-xs text-[var(--ink-quiet)] mb-3 pb-2 border-b border-[var(--rule)] font-mono">
        Τελευταία 50 τηλεγραφήματα από CNA, InBusinessNews, Philenews, Cyprus Mail, SigmaLive & BBC.
      </div>
      <div id="wireDrawerContent" class="space-y-3 flex-grow overflow-y-auto pr-1">
        <div class="text-xs text-[var(--ink-quiet)] italic text-center py-8">Φόρτωση ζωντανής ροής...</div>
      </div>
    </div>
  </div>

  <!-- JAVASCRIPT ENGINE -->
  <script>
    // Theme Toggle
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {{
      themeBtn.addEventListener('click', () => {{
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('oracle-theme', isDark ? 'dark' : 'light');
      }});
    }}

    // Global Clocks
    function updateClocks() {{
      const now = new Date();
      const fmt = (tz) => new Intl.DateTimeFormat('el-GR', {{ timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false }}).format(now);
      const cy = document.getElementById('clockCY'); if (cy) cy.textContent = fmt('Asia/Nicosia');
      const lon = document.getElementById('clockLON'); if (lon) lon.textContent = fmt('Europe/London');
      const nyc = document.getElementById('clockNYC'); if (nyc) nyc.textContent = fmt('America/New_York');
      const tyo = document.getElementById('clockTYO'); if (tyo) tyo.textContent = fmt('Asia/Tokyo');
    }}
    updateClocks();
    setInterval(updateClocks, 10000);

    // Audio Briefing Player (Web Speech API)
    (function () {{
      const playBtn = document.getElementById('audioPlayBtn');
      const stopBtn = document.getElementById('audioStopBtn');
      const speedBtn = document.getElementById('audioSpeedBtn');
      const statusText = document.getElementById('audioStatusText');
      const liveBadge = document.getElementById('audioLiveBadge');
      if (!playBtn || !('speechSynthesis' in window)) return;

      let synth = window.speechSynthesis;
      let utterance = null;
      let speeds = [1.0, 1.25, 1.5];
      let speedIdx = 0;

      function getBriefingText() {{
        let text = "Απογευματινή επιτελική σύνοψη της εφημερίδας The Oracle Sovereign για τις 10 Σεπτεμβρίου 2026. ";
        const topEl = document.getElementById('topStoryBody');
        if (topEl) text += topEl.innerText + " ";
        text += "Στις αγορές και το closing bell: ";
        {repr([f"{d['asset']}: {d['price']}, μεταβολή {d['change']}." for d in data.get('dashboard', [])])}.forEach(m => text += m + " ");
        text += "Στον νυχτερινό κίνδυνο: Παρακολούθηση ασιατικού ανοίγματος στις δύο τα ξημερώματα και περιφερειακού εναέριου χώρου.";
        return text;
      }}

      playBtn.addEventListener('click', () => {{
        if (synth.speaking && !synth.paused) {{
          synth.pause();
          playBtn.innerHTML = '▶';
          statusText.innerText = 'Σε παύση · Πατήστε Play για συνέχεια';
          return;
        }}
        if (synth.paused) {{
          synth.resume();
          playBtn.innerHTML = '⏸';
          statusText.innerText = 'Αναπαραγωγή σε εξέλιξη...';
          return;
        }}

        utterance = new SpeechSynthesisUtterance(getBriefingText());
        utterance.lang = 'el-GR';
        utterance.rate = speeds[speedIdx];
        utterance.onend = () => {{
          playBtn.innerHTML = '▶';
          stopBtn.classList.add('hidden');
          liveBadge.classList.add('hidden');
          statusText.innerText = 'Ολοκληρώθηκε η ανάγνωση της απογευματινής σύνοψης';
        }};

        synth.speak(utterance);
        playBtn.innerHTML = '⏸';
        stopBtn.classList.remove('hidden');
        liveBadge.classList.remove('hidden');
        statusText.innerText = 'Αναπαραγωγή απογευματινής σύνοψης...';
      }});

      stopBtn.addEventListener('click', () => {{
        synth.cancel();
        playBtn.innerHTML = '▶';
        stopBtn.classList.add('hidden');
        liveBadge.classList.add('hidden');
        statusText.innerText = 'Διακόπηκε η ανάγνωση';
      }});

      speedBtn.addEventListener('click', () => {{
        speedIdx = (speedIdx + 1) % speeds.length;
        speedBtn.innerText = speeds[speedIdx] + 'x';
        if (synth.speaking) {{
          synth.cancel();
          playBtn.click();
        }}
      }});
    }})();

    // 24/7 Live Wire Fetcher & Drawer
    (function () {{
      const tickerEl = document.getElementById('liveWireTicker');
      const drawerContent = document.getElementById('wireDrawerContent');
      const drawerModal = document.getElementById('wireDrawerModal');
      const openBtn = document.getElementById('openWireDrawerBtn');
      const openBtnNav = document.getElementById('openWireDrawerBtnNav');
      const closeBtn = document.getElementById('closeWireDrawerBtn');

      let wireItems = [];
      let activeIndex = 0;
      let rotatorInterval = null;

      function fetchWire() {{
        return fetch('{live_wire_url}')
          .catch(() => fetch('live-wire.json'))
          .catch(() => fetch('../live-wire.json'))
          .then(r => r.json())
          .then(data => {{
            wireItems = data;
            renderTicker();
            renderDrawer();
            if (!rotatorInterval && wireItems.length > 1) {{
              rotatorInterval = setInterval(rotateTicker, 6000);
            }}
          }})
          .catch(e => console.warn('Could not load live-wire:', e));
      }}

      function renderTicker() {{
        if (!tickerEl || !wireItems.length) return;
        const item = wireItems[activeIndex];
        const breakBadge = item.is_breaking ? '<span class="px-1.5 py-0.2 rounded bg-red-600 text-white font-bold text-[10px] mr-1.5 animate-pulse">ΕΚΤΑΚΤΟ</span>' : '';
        const timeBadge = `<span class="font-mono text-[var(--ink-quiet)] mr-2">[${{item.time_str || ''}}]</span>`;
        const srcBadge = `<span class="text-[var(--accent)] font-semibold ml-2">(${{item.source}})</span>`;
        tickerEl.innerHTML = `<div class="truncate">${{breakBadge}}${{timeBadge}}<a href="${{item.link}}" target="_blank" class="hover:underline text-[var(--ink)] font-medium">${{item.title}}</a>${{srcBadge}}</div>`;
      }}

      function rotateTicker() {{
        if (!tickerEl || !wireItems.length) return;
        activeIndex = (activeIndex + 1) % Math.min(wireItems.length, 15);
        renderTicker();
      }}

      function renderDrawer() {{
        if (!drawerContent || !wireItems.length) return;
        drawerContent.innerHTML = wireItems.map(item => {{
          const isB = item.is_breaking;
          const borderCls = isB ? 'border-red-500 bg-red-500/5' : 'border-[var(--rule)] bg-[var(--paper)]';
          const breakTag = isB ? '<span class="px-1.5 py-0.2 rounded bg-red-600 text-white text-[10px] font-bold mr-1.5">ΕΚΤΑΚΤΟ</span>' : '';
          return `
            <div class="p-3 rounded-lg border ${{borderCls}} space-y-1 text-xs">
              <div class="flex items-center justify-between text-[10px] font-mono text-[var(--ink-quiet)]">
                <span>${{item.source}} · ${{item.time_str || ''}}</span>
                ${{isB ? '<span class="text-red-500 font-bold uppercase">⚡ Flash</span>' : ''}}
              </div>
              <a href="${{item.link}}" target="_blank" class="font-bold text-[var(--ink)] hover:text-[var(--accent)] block leading-snug">
                ${{breakTag}}${{item.title}}
              </a>
              ${{item.snippet ? `<p class="text-[var(--ink-body)] line-clamp-2 text-[11px]">${{item.snippet}}</p>` : ''}}
            </div>
          `;
        }}).join('');
      }}

      function toggleDrawer(open) {{
        if (!drawerModal) return;
        if (open) {{
          drawerModal.classList.remove('hidden');
          document.body.style.overflow = 'hidden';
        }} else {{
          drawerModal.classList.add('hidden');
          document.body.style.overflow = '';
        }}
      }}

      if (openBtn) openBtn.addEventListener('click', () => toggleDrawer(true));
      if (openBtnNav) openBtnNav.addEventListener('click', () => toggleDrawer(true));
      if (closeBtn) closeBtn.addEventListener('click', () => toggleDrawer(false));
      if (drawerModal) {{
        drawerModal.addEventListener('click', (e) => {{
          if (e.target === drawerModal) toggleDrawer(false);
        }});
      }}

      fetchWire();
    }})();
  </script>
</body>
</html>
'''
    return html


def render_midday_html(data, house_stats, search_index, is_subfolder=False, date_slug=None):
    date_display = data.get('date_str') or '10 Σεπτεμβρίου 2026'
    time_display = data.get('time_str') or '13:30'
    read_time = data.get('read_time') or "3'"

    if not date_slug:
        m_iso = re.search(r'(\d{4}-\d{2}-\d{2})', date_display)
        iso_date = m_iso.group(1) if m_iso else datetime.now().strftime('%Y-%m-%d')
    else:
        iso_date = date_slug

    gen_iso = f"{iso_date}T{time_display}:00+03:00" if ':' in time_display else f"{iso_date}T13:30:00+03:00"

    urls = resolve_edition_urls(iso_date, is_subfolder)
    home_url = urls['home']
    morning_url = urls['morning']
    midday_url = urls['midday']
    evening_url = urls['evening']
    live_wire_url = urls['live_wire']
    search_index_url = urls['search_index']
    edition_switcher_html = render_edition_switcher_html(urls, 'midday')

    # Ticker Items
    ticker_spans = []
    for d in data.get('dashboard', []):
        color_cls = "text-[var(--up)]" if "+" in d['change'] else ("text-[var(--down)]" if "-" in d['change'] else "text-[var(--ink-quiet)]")
        spk = generate_sparkline(d['change'])
        ticker_spans.append(f'<span class="inline-flex items-center gap-1.5"><span class="font-bold text-[var(--ink)]">{d["asset"]}:</span> <span class="text-[var(--ink-body)]">{d["price"]}</span> <span class="{color_cls} font-semibold inline-flex items-center">{d["change"]}{spk}</span></span>')
    ticker_html = ' · '.join(ticker_spans) + ' · ' + ' · '.join(ticker_spans) if ticker_spans else ''

    # Executive Pulse (60-second summary)
    pulse_items = data.get('executive_pulse', [])
    pulse_html = ""
    if pulse_items:
        pulse_cols = []
        icons = ["📊", "🇨🇾", "⚽"]
        for idx, itm in enumerate(pulse_items):
            ico = icons[idx] if idx < len(icons) else "⚡"
            pulse_cols.append(f'''
            <div class="p-3.5 rounded-xl bg-[var(--paper)] border border-[var(--rule)]">
              <div class="text-xs text-[var(--ink-body)] leading-relaxed">
                <span class="mr-1 text-sm">{ico}</span> {md_to_inline_html(itm)}
              </div>
            </div>
            ''')
        pulse_html = f'''
        <!-- ⚡ 60-SECOND EXECUTIVE PULSE -->
        <div class="p-4 sm:p-5 rounded-2xl bg-gradient-to-r from-amber-500/10 via-[var(--paper-raised)] to-[var(--paper-raised)] border border-amber-500/30 shadow-xs">
          <div class="flex items-center justify-between gap-2 mb-3 pb-2 border-b border-[var(--rule)]">
            <span class="text-xs font-mono font-bold uppercase tracking-wider text-[var(--accent)] flex items-center gap-2">
              <span class="w-2 h-2 rounded-full bg-[var(--accent)] animate-ping"></span> ⚡ ΣΥΝΟΨΗ 60 ΔΕΥΤΕΡΟΛΕΠΤΩΝ
            </span>
            <span class="text-[10px] font-mono text-[var(--ink-quiet)]">MIDDAY PULSE</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
            {''.join(pulse_cols)}
          </div>
        </div>
        '''

    # Midday News Cards (Curated with Editorial Images & Typography)
    news_cards = []
    for idx, item in enumerate(data.get('midday_news', []), 1):
        clean_title = md_to_inline_html(item.get('title', ''))
        clean_body = md_to_inline_html(item.get('body', ''))
        clean_why = md_to_inline_html(item.get('why', ''))

        region = item.get('region', '🇨🇾 ΚΥΠΡΟΣ')
        reg_badge_cls = "bg-[var(--accent)] text-white" if 'ΚΥΠΡΟΣ' in region else "bg-indigo-900/80 text-white"

        item_url = item['source']['url'] if item.get('source') else ''
        img_url, cat_name = resolve_image(item_url, clean_title, region)

        src_html = ""
        if item.get('source'):
            src_html = f'''<a href="{item['source']['url']}" target="_blank" rel="noopener noreferrer" class="t-meta font-bold text-[var(--accent)] hover:underline flex items-center gap-1"><span>{item['source']['name']}</span> <span>➔</span></a>'''

        why_html = f'''
        <div class="t-meta text-[var(--accent)] bg-[var(--paper)] p-3 rounded mb-3 border-l-2 border-[var(--accent)] leading-relaxed">
          <strong class="font-bold">Γιατί με αφορά:</strong> {clean_why}
        </div>''' if clean_why else ""

        news_cards.append(f'''
        <article class="card overflow-hidden flex flex-col justify-between hover:border-[var(--rule-strong)] transition shadow-xs">
          <div>
            <div class="h-44 bg-[var(--paper)] relative overflow-hidden">
              <img src="{img_url}" alt="{clean_title}" class="w-full h-full object-cover" onerror="this.onerror=null; this.src='{TOPIC_FALLBACKS['general']}';">
              <span class="absolute top-2.5 left-2.5 {reg_badge_cls} t-meta px-2 py-0.5 rounded shadow-xs font-bold uppercase">{region}</span>
              <span class="absolute top-2.5 right-2.5 bg-emerald-500/90 text-white font-bold t-meta px-2 py-0.5 rounded shadow-xs">Επιβεβαιωμένο</span>
            </div>
            <div class="p-5 sm:p-6">
              <h3 class="t-title mb-2.5 text-[var(--ink)]">
                {clean_title}
              </h3>
              <p class="t-body-sm leading-relaxed mb-3 text-[var(--ink-body)]">
                {clean_body}
              </p>
              {why_html}
            </div>
          </div>
          <div class="p-5 sm:p-6 pt-0 border-t border-[var(--rule)] flex items-center justify-between">
            <span class="t-meta text-[var(--ink-quiet)] font-mono">13:30 EEST</span>
            {src_html}
          </div>
        </article>
        ''')
    news_html = '\n'.join(news_cards)

    # Market Tables (Two-Tier: Macro Radar vs Tech Equities Watchlist)
    macro_rows = []
    stock_rows = []

    for d in data.get('dashboard', []):
        is_up = '+' in d['change']
        is_down = '-' in d['change']
        badge_cls = "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border-emerald-500/20" if is_up else ("bg-rose-500/10 text-rose-600 dark:text-rose-400 border-rose-500/20" if is_down else "bg-gray-500/10 text-gray-600 border-gray-500/20")
        spk = generate_sparkline(d['change'])
        comment = md_to_inline_html(d.get('date_ref', ''))

        row_html = f'''
        <tr class="border-b border-[var(--rule)] hover:bg-[var(--paper-raised)] transition">
          <td class="py-3 px-3.5 font-bold text-[var(--ink)] flex items-center gap-1.5">
            <span>{d["asset"]}</span>
          </td>
          <td class="py-3 px-3.5 font-mono font-bold text-[var(--ink)]">{d["price"]}</td>
          <td class="py-3 px-3.5 font-mono">
            <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded border text-xs font-bold {badge_cls}">
              <span>{d["change"]}</span> {spk}
            </span>
          </td>
          <td class="py-3 px-3.5 text-xs text-[var(--ink-body)]">{comment}</td>
        </tr>
        '''
        if d.get('category') == 'Μετοχές Τεχνολογίας':
            stock_rows.append(row_html)
        else:
            macro_rows.append(row_html)

    if stock_rows:
        market_section_html = f'''
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-5">
          <!-- Macro Indices & FX -->
          <div class="lg:col-span-6 card overflow-hidden shadow-xs border border-[var(--rule)]">
            <div class="p-3.5 bg-[var(--paper)] border-b border-[var(--rule)] flex items-center justify-between">
              <h3 class="font-bold text-xs uppercase tracking-wider text-[var(--ink)] flex items-center gap-1.5">
                <span>🏛️</span> <span>Κύριοι Δείκτες, Συνάλλαγμα & Crypto</span>
              </h3>
              <span class="text-[10px] font-mono text-[var(--accent)] font-bold">MACRO & FX</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs">
                <thead class="bg-[var(--paper)] text-[10px] uppercase text-[var(--ink-quiet)] font-mono border-b border-[var(--rule)]">
                  <tr>
                    <th class="py-2.5 px-3.5">Αγορά / Τίτλος</th>
                    <th class="py-2.5 px-3.5 font-mono">Τιμή</th>
                    <th class="py-2.5 px-3.5 font-mono">Μεταβολή</th>
                    <th class="py-2.5 px-3.5">Σχόλιο</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[var(--rule)] font-sans">
                  {''.join(macro_rows)}
                </tbody>
              </table>
            </div>
          </div>

          <!-- Tech Stocks Watchlist -->
          <div class="lg:col-span-6 card overflow-hidden shadow-xs border border-indigo-500/30">
            <div class="p-3.5 bg-gradient-to-r from-[var(--paper)] to-indigo-950/10 border-b border-[var(--rule)] flex items-center justify-between">
              <h3 class="font-bold text-xs uppercase tracking-wider text-[var(--ink)] flex items-center gap-1.5">
                <span>💻</span> <span>Μετοχές Τεχνολογίας (Midday Tech Watch)</span>
              </h3>
              <span class="text-[10px] font-mono text-indigo-500 font-bold">TECH RADAR</span>
            </div>
            <div class="overflow-x-auto">
              <table class="w-full text-left text-xs">
                <thead class="bg-[var(--paper)] text-[10px] uppercase text-[var(--ink-quiet)] font-mono border-b border-[var(--rule)]">
                  <tr>
                    <th class="py-2.5 px-3.5">Μετοχή</th>
                    <th class="py-2.5 px-3.5 font-mono">Τιμή</th>
                    <th class="py-2.5 px-3.5 font-mono">Μεταβολή</th>
                    <th class="py-2.5 px-3.5">Σχόλιο</th>
                  </tr>
                </thead>
                <tbody class="divide-y divide-[var(--rule)] font-sans">
                  {''.join(stock_rows)}
                </tbody>
              </table>
            </div>
          </div>
        </div>
        '''
    else:
        market_section_html = f'''
        <div class="card overflow-hidden shadow-xs">
          <div class="overflow-x-auto">
            <table class="w-full text-left text-sm">
              <thead class="bg-[var(--paper)] text-xs uppercase text-[var(--ink-quiet)] font-mono border-b border-[var(--rule)]">
                <tr>
                  <th class="py-3 px-4">Δείκτης / Αξία</th>
                  <th class="py-3 px-4 font-mono">Τιμή</th>
                  <th class="py-3 px-4 font-mono">Μεταβολή</th>
                  <th class="py-3 px-4">Ώρα Αποτίμησης / Σχόλιο</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--rule)] font-sans">
                {''.join(macro_rows)}
              </tbody>
            </table>
          </div>
        </div>
        '''

    # Sports Cards (if present)
    sports = data.get('sports', {})
    has_sports = any(sports.get(k, {}).get('last_result') or sports.get(k, {}).get('next_match') for k in sports)
    sports_section_html = ""
    if has_sports:
        sports_config = [
            {
                'key': 'omonoia',
                'name': 'ΟΜΟΝΟΙΑ ΛΕΥΚΩΣΙΑΣ',
                'icon': '☘️',
                'league': 'CYPRUS LEAGUE & EUROPE',
                'border': 'border-emerald-700/30 dark:border-emerald-600/40',
                'header_bg': 'bg-gradient-to-r from-emerald-900 to-green-950',
                'search_q': 'Omonoia FC highlights 2026'
            },
            {
                'key': 'manutd',
                'name': 'MANCHESTER UNITED',
                'icon': '🔴',
                'league': 'UEFA CHAMPIONS LEAGUE',
                'border': 'border-red-700/30 dark:border-red-600/40',
                'header_bg': 'bg-gradient-to-r from-red-900 to-stone-950',
                'search_q': 'Manchester United highlights 2026'
            },
            {
                'key': 'realmadrid',
                'name': 'REAL MADRID',
                'icon': '⚪',
                'league': 'SPANISH LA LIGA',
                'border': 'border-amber-700/30 dark:border-amber-600/40',
                'header_bg': 'bg-gradient-to-r from-indigo-950 via-slate-900 to-purple-950',
                'search_q': 'Real Madrid highlights 2026'
            },
            {
                'key': 'formula1',
                'name': 'FORMULA 1',
                'icon': '🏎️',
                'league': 'FIA WORLD CHAMPIONSHIP',
                'border': 'border-red-600/30 dark:border-red-500/40',
                'header_bg': 'bg-gradient-to-r from-neutral-900 to-red-950',
                'search_q': 'Formula 1 highlights 2026'
            }
        ]

        sports_cards = []
        for sc in sports_config:
            s_data = sports.get(sc['key'], {})
            last_res = s_data.get('last_result') or ''
            next_m = s_data.get('next_match') or ''
            news_list = s_data.get('news') or []
            src = s_data.get('source')
            hl = s_data.get('highlights')

            if next_m in ['--', '---']: next_m = ''
            if last_res in ['--', '---']: last_res = ''
            clean_news = [n for n in news_list if n not in ['--', '---', '']]

            last_res_html = f'''
            <div class="flex items-start gap-2 text-xs">
              <span class="font-bold text-[var(--ink)] flex-shrink-0">⏱️ Τελ. Αποτέλεσμα:</span>
              <span class="text-[var(--ink-body)]">{md_to_inline_html(last_res)}</span>
            </div>''' if last_res else ""

            next_match_html = f'''
            <div class="flex items-start gap-2 text-xs">
              <span class="font-bold text-[var(--ink)] flex-shrink-0">📅 Επόμενος Αγώνας:</span>
              <span class="text-[var(--ink-body)] font-medium">{md_to_inline_html(next_m)}</span>
            </div>''' if next_m else '<div class="text-xs text-[var(--ink-quiet)] italic">Αναμονή ορισμού επόμενου αγώνα</div>'

            news_html = f'''
            <div class="text-xs text-[var(--ink-body)] bg-[var(--paper)] p-3 rounded border border-[var(--rule)] leading-relaxed">
              <strong class="text-[var(--accent)] font-semibold block mb-1">📋 Ρεπορτάζ & Νέα:</strong>
              {' '.join(md_to_inline_html(n) for n in clean_news)}
            </div>''' if clean_news else ""

            src_html = f'''
            <div class="text-[11px] text-[var(--ink-quiet)] flex items-center justify-between pt-2 border-t border-[var(--rule)]">
              <span>Επίσημη Πηγή:</span>
              <a href="{src['url']}" target="_blank" rel="noopener noreferrer" class="text-[var(--accent)] hover:underline font-medium">{src['name']}</a>
            </div>''' if src else ""

            search_url = hl['url'] if hl and hl.get('url') else f"https://www.youtube.com/results?search_query={sc['search_q'].replace(' ', '+')}"
            search_title = hl['title'] if hl and hl.get('title') else "YouTube Highlights & Match Hub"

            sports_cards.append(f'''
            <article class="card overflow-hidden flex flex-col justify-between border rounded-2xl shadow-xs {sc['border']}">
              <div>
                <div class="{sc['header_bg']} p-4 text-white flex items-center justify-between">
                  <div class="flex items-center gap-2.5">
                    <span class="text-2xl">{sc['icon']}</span>
                    <h3 class="font-masthead font-bold text-sm tracking-wide text-white">{sc['name']}</h3>
                  </div>
                  <span class="t-meta uppercase tracking-wider px-2 py-0.5 rounded-full text-[10px] bg-black/40 text-white/90 border border-white/10">
                    {sc['league']}
                  </span>
                </div>
                <div class="p-5 space-y-3">
                  {last_res_html}
                  {next_match_html}
                  {news_html}
                  {src_html}
                </div>
              </div>
              <div class="p-4 pt-0">
                <a href="{search_url}" target="_blank" rel="noopener noreferrer"
                   class="inline-flex items-center justify-center gap-2 w-full py-2 px-3 rounded-lg bg-red-600/10 hover:bg-red-600/20 text-red-600 dark:text-red-400 text-xs font-bold border border-red-500/30 transition">
                  <span>▶</span> <span>{search_title}</span>
                </a>
              </div>
            </article>
            ''')
        sports_section_html = f'''
        <!-- ==================== ⚽ 3. ΑΘΛΗΤΙΚΑ ==================== -->
        <section id="sports" class="scroll-mt-24">
          <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
            <h2 class="t-section flex items-center gap-2">
              <span>⚽</span> <span>Μεσημβρινός Αθλητισμός & Πρόγραμμα</span>
            </h2>
            <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">SPORTS WIRE</span>
          </div>
          <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-5">
            {''.join(sports_cards)}
          </div>
        </section>
        '''

    # Weather (if present)
    wx_raw = data.get('weather', {}).get('raw_items', [])
    weather_section_html = ""
    if wx_raw:
        wx_formatted_items = []
        for raw in wx_raw:
            if not raw or raw.strip() in ['--', '---'] or raw.startswith('---'):
                continue
            icon = '🌤️'
            low = raw.lower()
            if 'θερμοκρασία' in low: icon = '🌡️'
            elif 'υγρασία' in low: icon = '💧'
            elif 'άνεμος' in low or 'ανεμοι' in low: icon = '💨'
            elif 'uv' in low or 'προειδοποιήσεις' in low: icon = '⚠️'
            elif 'πρόγνωση' in low or 'αίθριος' in low: icon = '☀️'
            elif 'πηγή' in low: icon = '🌐'

            m_label = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', raw)
            if m_label:
                lbl = m_label.group(1).strip()
                rest = md_to_inline_html(m_label.group(2).strip())
                is_warn = (icon == '⚠️')
                bg_cls = "bg-amber-500/10 border border-amber-500/30 dark:bg-amber-950/30" if is_warn else "bg-[var(--paper)] border border-[var(--rule)]"
                wx_formatted_items.append(f'''
                <div class="flex items-start gap-3 p-3 rounded-xl {bg_cls}">
                  <span class="text-xl flex-shrink-0 mt-0.5">{icon}</span>
                  <div class="text-xs text-[var(--ink-body)] leading-relaxed">
                    <span class="font-bold text-[var(--ink)]">{lbl}:</span> {rest}
                  </div>
                </div>''')
            else:
                wx_formatted_items.append(f'''
                <div class="flex items-start gap-3 p-3 rounded-xl bg-[var(--paper)] border border-[var(--rule)]">
                  <span class="text-xl flex-shrink-0 mt-0.5">{icon}</span>
                  <div class="text-xs text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(raw)}</div>
                </div>''')

        weather_section_html = f'''
        <!-- ==================== 🌤️ 4. ΚΑΙΡΟΣ — ΛΕΜΕΣΟΣ ==================== -->
        <section id="weather" class="scroll-mt-24">
          <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
            <h2 class="t-section flex items-center gap-2">
              <span>🌤️</span> <span>Καιρός — Λεμεσός (Μεσημβρινές Συνθήκες)</span>
            </h2>
            <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">METEO RADAR</span>
          </div>
          <div class="card p-5 bg-gradient-to-br from-[var(--paper-raised)] via-[var(--paper-raised)] to-amber-500/5 border border-amber-500/20 rounded-2xl shadow-xs">
            <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
              {''.join(wx_formatted_items)}
            </div>
          </div>
        </section>
        '''

    # Developments (if present)
    dev_items = data.get('developments', [])
    dev_section_html = ""
    if dev_items:
        dev_cards = []
        for itm in dev_items:
            clean_d = md_to_inline_html(itm)
            dev_cards.append(f'''
            <li class="flex items-start gap-3 p-3.5 rounded-xl bg-[var(--paper-raised)] border border-[var(--rule)]">
              <span class="w-2.5 h-2.5 rounded-full bg-[var(--accent)] flex-shrink-0 mt-1.5"></span>
              <div class="text-xs text-[var(--ink-body)] leading-relaxed flex-grow">
                {clean_d}
              </div>
            </li>
            ''')
        dev_section_html = f'''
        <!-- ==================== 🗂️ 5. ΜΕΣΗΜΒΡΙΝΕΣ ΕΞΕΛΙΞΕΙΣ ==================== -->
        <section id="developments" class="scroll-mt-24">
          <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
            <h2 class="t-section flex items-center gap-2">
              <span>🗂️</span> <span>Μεσημβρινές Εξελίξεις</span>
            </h2>
            <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">STRATEGIC HIGHLIGHTS</span>
          </div>
          <ul class="space-y-2.5">
            {''.join(dev_cards)}
          </ul>
        </section>
        '''

    # Priorities List
    priority_items = []
    for p in data.get('afternoon_priorities', []):
        clean_p = md_to_inline_html(p)
        priority_items.append(f'''
        <li class="flex items-start gap-3 p-3 rounded-lg bg-[var(--paper-raised)] border border-[var(--rule)]">
          <span class="text-base flex-shrink-0">🎯</span>
          <div class="text-xs text-[var(--ink-body)] leading-relaxed">
            {clean_p}
          </div>
        </li>
        ''')
    priorities_html = '\n'.join(priority_items)

    html = f'''<!DOCTYPE html>
<html lang="el">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <title>THE ORACLE SOVEREIGN — ☀️ Midday Pulse — {date_display}</title>
  <script src="https://cdn.tailwindcss.com/3.4.16"></script>
  <script>tailwind.config = {{ darkMode: 'class' }};</script>
  <script>
    (function () {{
      var s = localStorage.getItem('oracle-theme');
      var d = s ? s === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (d) document.documentElement.classList.add('dark');
    }})();
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;900&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;0,6..72,700;1,6..72,400&family=Inter:wght@300;400;500;600;700&display=swap');
    :root {{
      --paper: #f6f3ec;
      --paper-raised: #fffdf8;
      --rule: #d9d3c5;
      --rule-strong: #b3aa96;
      --ink: #17150f;
      --ink-body: #2e2a22;
      --ink-quiet: #6d675a;
      --accent: #8a5320;
      --up: #1f6b3f;
      --down: #a3282b;
      --r-md: 8px;
    }}
    .dark {{
      --paper: #14120e;
      --paper-raised: #1c1a15;
      --rule: #2e2920;
      --rule-strong: #4a4233;
      --ink: #ede8dc;
      --ink-body: #cfc8ba;
      --ink-quiet: #8c8373;
      --accent: #d4954b;
      --up: #43a047;
      --down: #e53935;
    }}
    body {{ background-color: var(--paper); color: var(--ink-body); font-family: 'Inter', system-ui, sans-serif; }}
    .font-masthead {{ font-family: 'Cinzel', serif; }}
    .font-editorial {{ font-family: 'Newsreader', serif; }}
    .t-masthead {{ font-family: 'Cinzel', serif; font-size: clamp(2rem, 5vw, 3.25rem); letter-spacing: 0.08em; font-weight: 700; line-height: 1.1; }}
    .t-section {{ font-family: 'Cinzel', serif; font-size: 1.25rem; font-weight: 700; letter-spacing: 0.04em; color: var(--ink); }}
    .card {{ background-color: var(--paper-raised); border: 1px solid var(--rule); border-radius: var(--r-md); }}
    .ticker-wrap {{ overflow: hidden; white-space: nowrap; }}
    .ticker-content {{ display: inline-block; animation: tickerAnimation 40s linear infinite; }}
    .ticker-wrap:hover .ticker-content {{ animation-play-state: paused; }}
    @keyframes tickerAnimation {{ 0% {{ transform: translateX(0); }} 100% {{ transform: translateX(-50%); }} }}
  </style>
</head>
<body class="antialiased min-h-screen">
  <!-- TOP BAR -->
  <div class="bg-[var(--paper-raised)] border-b border-[var(--rule)] text-xs py-1.5 px-4">
    <div class="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-2">
      <div class="flex flex-wrap items-center gap-3">
        <span class="inline-flex items-center px-2 py-0.5 rounded font-mono font-semibold text-[11px] bg-amber-500/10 text-amber-800 dark:text-amber-300">
          ☀️ 13:30 · {date_display}
        </span>
{edition_switcher_html}
      </div>
      <div id="globalClocks" class="hidden xl:flex items-center gap-2.5 font-mono text-[11px] text-[var(--ink-quiet)] border-l border-[var(--rule)] pl-3">
        <span class="inline-flex items-center gap-1">🇨🇾 <strong>CY</strong> <span id="clockCY">--:--</span></span>
        <span>·</span>
        <span class="inline-flex items-center gap-1">🇬🇧 <strong>LON</strong> <span id="clockLON">--:--</span></span>
        <span>·</span>
        <span class="inline-flex items-center gap-1">🇺🇸 <strong>NYC</strong> <span id="clockNYC">--:--</span></span>
      </div>
      <button id="themeToggle" class="px-2 py-1 rounded border border-[var(--rule)] text-xs hover:bg-[var(--paper)] transition" title="Εναλλαγή θέματος">🌓</button>
    </div>
  </div>

  <!-- MASTHEAD -->
  <header class="border-b-4 border-double border-[var(--rule-strong)] py-8 px-4 bg-[var(--paper-raised)] text-center">
    <div class="max-w-5xl mx-auto">
      <div class="flex justify-between items-center text-xs uppercase text-[var(--ink-quiet)] border-b border-[var(--rule)] pb-2 mb-4 font-mono">
        <div>ΕΤΟΣ 2026 · DAILY BRIEFING</div>
        <div class="font-bold text-[var(--accent)]">☀️ MIDDAY EXECUTIVE PULSE</div>
        <div>ONE-READER EDITION</div>
      </div>
      <h1 class="t-masthead text-[var(--ink)] mb-2 uppercase">THE ORACLE SOVEREIGN</h1>
      <p class="font-editorial italic text-lg sm:text-xl text-[var(--ink-quiet)] max-w-2xl mx-auto">
        Μεσημβρινός Παλμός Ειδήσεων, Deal Wire, Ενδιάμεσες Τιμές Αγορών & Απογευματινές Προτεραιότητες
      </p>
      <div class="flex flex-wrap justify-center items-center gap-3 mt-4 pt-3 border-t border-[var(--rule)] text-xs text-[var(--ink-quiet)] font-mono">
        <span>📅 {date_display}</span> <span>·</span> <span>⏰ 13:30 ώρα Κύπρου</span> <span>·</span> <span>⏱️ {read_time} ανάγνωση</span>
      </div>
    </div>
  </header>

  <!-- TICKER -->
  <div class="bg-[var(--paper)] text-[var(--ink)] py-2 border-y border-[var(--rule)] text-xs ticker-wrap">
    <div class="ticker-content space-x-8 font-mono">{ticker_html}</div>
  </div>

  <!-- MAIN CONTENT -->
  <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-10">
    {pulse_html}

    <!-- 1. BREAKING & DEAL WIRE -->
    <section id="midday-news" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>⚡</span> <span>Μεσημβρινό Breaking & Deal Wire</span>
        </h2>
        <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">CURATED DIGEST</span>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {news_html}
      </div>
    </section>

    <!-- 2. MIDDAY MARKET PULSE -->
    <section id="market-pulse" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>📊</span> <span>Midday Market Pulse (ΧΑΚ · ATHEX · Ευρώπη & Wall Street)</span>
        </h2>
        <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">LIVE APPRAISAL</span>
      </div>
      {market_section_html}
    </section>

    {sports_section_html}

    {weather_section_html}

    {dev_section_html}

    <!-- 6. PRIORITIES -->
    <section id="priorities" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🎯</span> <span>Απογευματινές Προτεραιότητες</span>
        </h2>
        <span class="text-xs font-mono text-[var(--accent)] uppercase font-bold ml-auto">TIMELINE</span>
      </div>
      <div class="card p-5">
        <ul class="space-y-2.5">
          {priorities_html}
        </ul>
      </div>
    </section>

    <!-- CALLOUT TO MORNING & EVENING -->
    <div class="card p-6 bg-gradient-to-r from-amber-500/5 to-[var(--paper-raised)] border-l-4 border-[var(--accent)] flex flex-wrap items-center justify-between gap-4">
      <div>
        <div class="text-xs font-mono font-bold uppercase text-[var(--accent)] mb-1">🏛️ ΟΛΕΣ ΟΙ ΕΚΔΟΣΕΙΣ ΤΗΣ ΗΜΕΡΑΣ</div>
        <h3 class="font-editorial text-lg font-bold text-[var(--ink)]">Πρωινό Broadsheet & Απογευματινή Σύνοψη</h3>
        <p class="text-xs text-[var(--ink-body)]">Συνεχής κάλυψη καθ' όλη τη διάρκεια της ημέρας με πλήρη ανάλυση, επιτόκια και closing bell.</p>
      </div>
      <div class="flex items-center gap-3">
        <a href="{morning_url}" class="px-3 py-2 rounded-lg bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] text-xs font-bold">Πρωινό 07:30</a>
        <a href="{evening_url}" class="px-3 py-2 rounded-lg bg-[var(--accent)] text-white text-xs font-bold hover:opacity-90">Απόγευμα 19:30 ➔</a>
      </div>
    </div>
  </main>

  <!-- SCRIPT -->
  <script>
    const themeBtn = document.getElementById('themeToggle');
    if (themeBtn) {{
      themeBtn.addEventListener('click', () => {{
        const isDark = document.documentElement.classList.toggle('dark');
        localStorage.setItem('oracle-theme', isDark ? 'dark' : 'light');
      }});
    }}
    function updateClocks() {{
      const now = new Date();
      const fmt = (tz) => new Intl.DateTimeFormat('el-GR', {{ timeZone: tz, hour: '2-digit', minute: '2-digit', hour12: false }}).format(now);
      const cy = document.getElementById('clockCY'); if (cy) cy.textContent = fmt('Asia/Nicosia');
      const lon = document.getElementById('clockLON'); if (lon) lon.textContent = fmt('Europe/London');
      const nyc = document.getElementById('clockNYC'); if (nyc) nyc.textContent = fmt('America/New_York');
    }}
    updateClocks();
    setInterval(updateClocks, 10000);
  </script>
</body>
</html>
'''
    return html


def render_morning_html(data, house_stats, search_index, is_subfolder=False, date_slug=None):
    date_display = data['date_str'] or '7 Σεπτεμβρίου 2026'
    time_display = data['time_str'] or '13:30'
    read_time = data['read_time'] or "7'"

    if not date_slug:
        m_iso = re.search(r'(\d{4}-\d{2}-\d{2})', date_display)
        iso_date = m_iso.group(1) if m_iso else datetime.now().strftime('%Y-%m-%d')
    else:
        iso_date = date_slug
    gen_iso = f"{iso_date}T{time_display}:00+03:00" if ':' in time_display else f"{iso_date}T13:30:00+03:00"

    # Ticker Items
    ticker_spans = []
    for d in data['dashboard']:
        color_cls = "text-[var(--up)]" if "+" in d['change'] else ("text-[var(--down)]" if "-" in d['change'] else "text-[var(--ink-quiet)]")
        ticker_spans.append(f'<span class="inline-flex items-center gap-1.5"><span class="font-bold text-[var(--ink)]">{d["asset"]}:</span> <span class="text-[var(--ink-body)]">{d["price"]}</span> <span class="{color_cls} font-semibold">{d["change"]}</span></span>')
    ticker_html = ' '.join(ticker_spans) + ' ' + ' '.join(ticker_spans)

    # Detect Current Edition for Switcher
    title_upper = (data.get('title') or '').upper()
    current_edition = 'morning'
    if 'ΜΕΣΗΜΒΡΙΝΟΣ' in title_upper or 'MIDDAY' in title_upper or '13:30' in time_display:
        current_edition = 'midday'
    elif 'ΑΠΟΓΕΥΜΑΤΙΝΗ' in title_upper or 'EVENING' in title_upper or '19:30' in time_display:
        current_edition = 'evening'

    morning_cls = "bg-[var(--accent)] text-white font-bold shadow-xs" if current_edition == 'morning' else "bg-[var(--paper)] text-[var(--ink-body)] border border-[var(--rule)] hover:border-[var(--accent)]"
    midday_cls = "bg-[var(--accent)] text-white font-bold shadow-xs" if current_edition == 'midday' else "bg-[var(--paper)] text-[var(--ink-body)] border border-[var(--rule)] hover:border-[var(--accent)]"
    evening_cls = "bg-[var(--accent)] text-white font-bold shadow-xs" if current_edition == 'evening' else "bg-[var(--paper)] text-[var(--ink-body)] border border-[var(--rule)] hover:border-[var(--accent)]"

    urls = resolve_edition_urls(iso_date, is_subfolder)
    home_url = urls['home']
    morning_url = urls['morning']
    midday_url = urls['midday']
    evening_url = urls['evening']
    live_wire_url = urls['live_wire']
    search_index_url = urls['search_index']
    edition_switcher_html = render_edition_switcher_html(urls, 'morning')

    global_clocks_html = '''
    <div id="globalClocks" class="hidden xl:flex items-center gap-2.5 font-mono text-[11px] text-[var(--ink-quiet)] border-l border-[var(--rule)] pl-3">
      <span class="inline-flex items-center gap-1">🇨🇾 <strong>CY</strong> <span id="clockCY">--:--</span></span>
      <span>·</span>
      <span class="inline-flex items-center gap-1">🇬🇧 <strong>LON</strong> <span id="clockLON">--:--</span> <span id="statusLON" class="text-[9px] px-1 py-0.2 rounded font-bold">--</span></span>
      <span>·</span>
      <span class="inline-flex items-center gap-1">🇺🇸 <strong>NYC</strong> <span id="clockNYC">--:--</span> <span id="statusNYC" class="text-[9px] px-1 py-0.2 rounded font-bold">--</span></span>
      <span>·</span>
      <span class="inline-flex items-center gap-1">🇯🇵 <strong>TYO</strong> <span id="clockTYO">--:--</span> <span id="statusTYO" class="text-[9px] px-1 py-0.2 rounded font-bold">--</span></span>
    </div>
    '''

    live_wire_bar_html = '''
    <!-- ⚡ 24/7 REAL-TIME LIVE WIRE BAR -->
    <div id="liveWireBar" class="bg-[var(--paper-raised)] text-[var(--ink)] py-2 px-4 border-b border-[var(--rule)] t-meta">
      <div class="max-w-7xl mx-auto flex items-center justify-between gap-3">
        <div class="flex items-center gap-2 flex-shrink-0">
          <span class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded bg-red-600 text-white font-mono text-[10px] font-bold tracking-wider uppercase shadow-xs">
            <span class="w-1.5 h-1.5 rounded-full bg-white animate-ping"></span> 24/7 WIRE
          </span>
        </div>
        <div id="liveWireTicker" class="overflow-hidden whitespace-nowrap text-xs text-[var(--ink-body)] flex-grow font-sans min-w-0">
          <span class="text-[var(--ink-quiet)] italic">Συνεχής ροή έκτακτης ειδησεογραφίας...</span>
        </div>
        <button id="openWireDrawerBtn" class="flex-shrink-0 text-xs font-bold text-[var(--accent)] hover:underline flex items-center gap-1">
          <span>Προβολή Όλων (50+)</span> <span>➔</span>
        </button>
      </div>
    </div>
    '''

    wire_drawer_modal_html = '''
    <!-- ⚡ 24/7 LIVE WIRE DRAWER MODAL -->
    <div id="wireDrawerModal" class="fixed inset-0 bg-black/50 backdrop-blur-xs z-50 hidden flex justify-end transition-opacity duration-300">
      <div class="w-full max-w-md bg-[var(--paper-raised)] h-full shadow-2xl p-5 overflow-y-auto flex flex-col border-l border-[var(--rule)]">
        <div class="flex items-center justify-between pb-3 border-b border-[var(--rule)] mb-4">
          <div class="flex items-center gap-2">
            <span class="w-2.5 h-2.5 rounded-full bg-red-500 animate-pulse"></span>
            <h3 class="font-bold text-sm tracking-wide uppercase text-[var(--ink)]">24/7 Live Wire Intelligence</h3>
          </div>
          <button id="closeWireDrawerBtn" class="text-2xl text-[var(--ink-quiet)] hover:text-[var(--ink)] leading-none px-2">&times;</button>
        </div>
        <div class="text-xs text-[var(--ink-quiet)] mb-3 pb-2 border-b border-[var(--rule)] font-mono">
          Τελευταία 50 τηλεγραφήματα από CNA, InBusinessNews, Philenews, Cyprus Mail, SigmaLive & BBC.
        </div>
        <div id="wireDrawerContent" class="space-y-3 flex-grow overflow-y-auto pr-1">
          <div class="text-xs text-[var(--ink-quiet)] italic text-center py-8">Φόρτωση ζωντανής ροής...</div>
        </div>
      </div>
    </div>
    '''
    top_url = data['top_story']['sources'][0]['url'] if data['top_story'].get('sources') else ''
    top_img, top_category = resolve_image(top_url, data['top_story'].get('title', ''), 'ΟΙΚΟΝΟΜΙΑ & ΑΞΙΟΧΡΕΟ')

    # House Search Nav Button & Card
    house_nav_html = ""
    house_card_html = ""
    if house_stats and house_stats.get('local_url'):
        house_href = f"../{house_stats['local_url']}" if is_subfolder else house_stats['local_url']
        house_nav_html = f'''<a href="{house_href}" target="_blank" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition font-medium flex items-center gap-1">🏠 <span>Ακίνητα</span></a>'''
        house_card_html = f'''
        <div class="card p-5 border-l-4 border-[var(--accent)] mb-6">
          <div class="flex flex-wrap items-center justify-between gap-2 mb-2">
            <span class="t-meta font-bold uppercase tracking-wider text-[var(--accent)] flex items-center gap-1.5">
              <span>🏠</span> REAL ESTATE RADAR — ΕΒΔΟΜΑΔΙΑΙΟ ΔΕΛΤΙΟ ΛΕΜΕΣΟΥ
            </span>
            <span class="t-meta font-mono text-[var(--ink-quiet)]">Έκδοση: {house_stats['date']}</span>
          </div>
          <p class="t-body-sm text-[var(--ink-body)] mb-3 leading-relaxed">
            Εντοπίστηκαν <strong>{house_stats['unique_properties']} μοναδικά ακίνητα</strong> (Bazaraki & BuySellCyprus) στον άξονα Ύψωνα → Γερμασόγειας. 
            <strong>{house_stats['top_picks_count']} Top Picks</strong> πέρασαν όλα τα φίλτρα: {house_stats['top_pick_highlights']}.
          </p>
          <a href="{house_href}" target="_blank" class="inline-flex items-center gap-1.5 t-meta font-bold text-[var(--accent)] hover:underline">
            <span>Άνοιγμα πλήρους εβδομαδιαίας έκθεσης ακινήτων</span> <span>➔</span>
          </a>
        </div>
        '''

    # Cyprus Cards with Images, Editorial Hierarchy & Real Depth
    cyprus_cards = []
    for idx, item in enumerate(data['cyprus'], 1):
        item_url = item['source']['url'] if item.get('source') else ''
        img_url, cat_name = resolve_image(item_url, item['title'], 'ΚΥΠΡΟΣ')

        is_lead = (idx == 1)
        is_p6 = (item['is_portfolio'] or idx == 6)

        if is_lead:
            card_cls = "card md:col-span-2 overflow-hidden flex flex-col justify-between"
            img_h_cls = "h-64 sm:h-72"
            title_cls = "t-lead mb-3"
            body_cls = "t-body mb-4"
        else:
            p6_border = "border-l-4 border-[var(--accent)]" if is_p6 else ""
            card_cls = f"card {p6_border} overflow-hidden flex flex-col justify-between"
            img_h_cls = "h-44"
            title_cls = "t-title mb-2.5"
            body_cls = "t-body-sm mb-3"

        if is_p6:
            cat_name = "Ο ΦΑΚΕΛΟΣ ΜΟΥ"
            cat_badge_cls = "bg-[var(--accent)] text-white"
        else:
            cat_badge_cls = "bg-[var(--ink)]/85 text-white"

        tag_cls = "bg-[var(--up)] text-white" if item['tag'] == 'Επιβεβαιωμένο' else ("bg-[var(--accent)] text-white" if item['tag'] == 'Εξελισσόμενο' else "bg-[var(--rule-strong)] text-white")

        why_html = f'''
        <div class="t-meta text-[var(--accent)] bg-[var(--paper)] p-3 rounded mb-3 border-l-2 border-[var(--accent)]">
          <strong class="font-bold">Γιατί με αφορά:</strong> {item["why"]}
        </div>''' if item.get('why') else ''

        src_html = f'''
        <div class="flex justify-between items-center t-meta pt-3 border-t border-[var(--rule)]">
          <a href="{item["source"]["url"]}" target="_blank" rel="noopener noreferrer" class="font-semibold text-[var(--accent)] hover:underline">
            {item["source"]["name"]}
          </a>
          <span class="font-mono text-[var(--ink-quiet)]">{item['tag']}</span>
        </div>''' if item.get('source') else ''

        depth_html = render_depth_html(item.get('depth', {}), is_world=False)

        cyprus_cards.append(f'''
        <article class="{card_cls}">
          <div>
            <div class="{img_h_cls} bg-[var(--paper)] relative overflow-hidden">
              <img src="{img_url}" alt="{item['title']}" class="w-full h-full object-cover" onerror="this.onerror=null; this.src='{TOPIC_FALLBACKS['general']}';">
              <span class="absolute top-2.5 left-2.5 {cat_badge_cls} t-meta px-2 py-0.5 rounded shadow-xs">{cat_name}</span>
              <span class="absolute top-2.5 right-2.5 {tag_cls} t-meta px-2 py-0.5 rounded shadow-xs">{item['tag']}</span>
            </div>
            <div class="p-5 sm:p-6">
              <h3 class="{title_cls}">
                {item['title']}
              </h3>
              <p class="{body_cls} leading-relaxed">
                {item['body']}
              </p>
              {why_html}
            </div>
          </div>
          <div class="p-5 sm:p-6 pt-0">
            {depth_html}
            {src_html}
          </div>
        </article>
        ''')
    cyprus_cards_html = '\n'.join(cyprus_cards)

    # World Cards with Images, Editorial Hierarchy & Real Depth
    world_cards = []
    for idx, item in enumerate(data['world'], 1):
        item_url = item['source']['url'] if item.get('source') else ''
        img_url, cat_name = resolve_image(item_url, item['title'], 'ΔΙΕΘΝΗ')

        is_lead = (idx == 1)
        if is_lead:
            card_cls = "card md:col-span-2 overflow-hidden flex flex-col justify-between"
            img_h_cls = "h-64 sm:h-72"
            title_cls = "t-lead mb-3"
            body_cls = "t-body mb-4"
        else:
            card_cls = "card overflow-hidden flex flex-col justify-between"
            img_h_cls = "h-44"
            title_cls = "t-title mb-2.5"
            body_cls = "t-body-sm mb-3"

        tag_cls = "bg-[var(--up)] text-white" if item['tag'] == 'Επιβεβαιωμένο' else ("bg-[var(--accent)] text-white" if item['tag'] == 'Εξελισσόμενο' else "bg-[var(--rule-strong)] text-white")

        src_html = f'''
        <div class="flex justify-between items-center t-meta pt-3 border-t border-[var(--rule)]">
          <a href="{item["source"]["url"]}" target="_blank" rel="noopener noreferrer" class="font-semibold text-[var(--accent)] hover:underline">
            {item["source"]["name"]}
          </a>
          <span class="font-mono text-[var(--ink-quiet)]">{item['tag']}</span>
        </div>''' if item.get('source') else ''

        depth_html = render_depth_html(item.get('depth', {}), is_world=True)

        world_cards.append(f'''
        <article class="{card_cls}">
          <div>
            <div class="{img_h_cls} bg-[var(--paper)] relative overflow-hidden">
              <img src="{img_url}" alt="{item['title']}" class="w-full h-full object-cover" onerror="this.onerror=null; this.src='{TOPIC_FALLBACKS['diplomacy']}';">
              <span class="absolute top-2.5 left-2.5 bg-[var(--ink)]/85 text-white t-meta px-2 py-0.5 rounded shadow-xs">{cat_name}</span>
              <span class="absolute top-2.5 right-2.5 {tag_cls} t-meta px-2 py-0.5 rounded shadow-xs">{item['tag']}</span>
            </div>
            <div class="p-5 sm:p-6">
              <h3 class="{title_cls}">
                {item['title']}
              </h3>
              <p class="{body_cls} leading-relaxed">
                {item['body']}
              </p>
            </div>
          </div>
          <div class="p-5 sm:p-6 pt-0">
            {depth_html}
            {src_html}
          </div>
        </article>
        ''')
    world_cards_html = '\n'.join(world_cards)

    # Markets Movers HTML
    movers_cards = []
    for item in data['markets']:
        src_html = f'<a href="{item["source"]["url"]}" target="_blank" rel="noopener noreferrer" class="text-[var(--accent)] hover:underline font-semibold t-meta ml-auto">{item["source"]["name"]}</a>' if item.get('source') else ''
        hdr = item['header']
        icon = '📈' if '+' in hdr else ('📉' if '-' in hdr else '📊')
        badge_cls = "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300 border border-emerald-500/30" if '+' in hdr else ("bg-rose-500/10 text-rose-700 dark:text-rose-300 border border-rose-500/30" if '-' in hdr else "bg-[var(--rule)]/40 text-[var(--ink)]")
        movers_cards.append(f'''
        <div class="card p-4 flex flex-col justify-between">
          <div>
            <div class="flex items-center gap-2 mb-2">
              <span class="text-lg">{icon}</span>
              <span class="t-meta px-2 py-0.5 rounded font-mono font-bold {badge_cls}">
                {hdr.split('(')[-1].replace(')', '') if '(' in hdr and '%' in hdr else 'MOVER'}
              </span>
            </div>
            <div class="t-num font-mono font-bold text-sm sm:text-base text-[var(--ink)] mb-1">
              {hdr}
            </div>
            <p class="t-body-sm text-[var(--ink-body)] leading-relaxed mb-2">
              <strong class="text-[var(--ink)]">Αιτία:</strong> {item['cause']}
            </p>
          </div>
          <div class="flex items-center justify-end border-t border-[var(--rule)] pt-2 mt-2">
            {src_html}
          </div>
        </div>
        ''')
    movers_html = '\n'.join(movers_cards)

    # Dashboard rows with asset icons
    dash_rows = []
    asset_icons = {
        's&p': '📊', 'eur/usd': '💶', 'brent': '🛢️', 'gold': '🪙', 'χρυσός': '🪙',
        'bitcoin': '₿', 'treasury': '📑', 'euribor': '⚡'
    }
    for d in data['dashboard']:
        change_cls = "text-[var(--up)] font-bold" if "+" in d['change'] else ("text-[var(--down)] font-bold" if "-" in d['change'] else "text-[var(--ink-quiet)]")
        icon = '📈' if "+" in d['change'] else ('📉' if "-" in d['change'] else '⏺️')
        a_low = d['asset'].lower()
        a_icon = '🔹'
        for k, ico in asset_icons.items():
            if k in a_low:
                a_icon = ico
                break
        spark_svg = generate_sparkline(d['change'])
        dash_rows.append(f'''
        <tr>
          <td class="py-2.5 font-semibold text-[var(--ink)] font-sans flex items-center gap-2">
            <span>{a_icon}</span> <span>{d['asset']}</span>
          </td>
          <td class="py-2.5 text-[var(--ink-body)] font-mono">{d['price']}</td>
          <td class="py-2.5 {change_cls} font-mono whitespace-nowrap">
            <span class="inline-flex items-center gap-1">{icon} {d['change']} {spark_svg}</span>
          </td>
          <td class="py-2.5 text-[var(--ink-quiet)] t-meta">{d['date_ref']}</td>
        </tr>
        ''')
    dash_rows_html = '\n'.join(dash_rows)

    # Euribor rows
    euribor_rows = []
    for er in data['rates']['euribor']:
        euribor_rows.append(f'''
        <tr>
          <td class="py-2.5 font-semibold text-[var(--ink)] font-sans">{er['period']}</td>
          <td class="py-2.5 text-center text-[var(--ink-body)]">{er['1m']}</td>
          <td class="py-2.5 text-center font-bold text-[var(--accent)]">{er['3m']}</td>
          <td class="py-2.5 text-center text-[var(--ink-body)]">{er['6m']}</td>
          <td class="py-2.5 text-center text-[var(--ink-body)]">{er['12m']}</td>
        </tr>
        ''')
    euribor_rows_html = '\n'.join(euribor_rows)

    # Stadium-Grade Executive Sports Cards
    SPORTS_META = {
        'omonoia': {
            'name': 'ΟΜΟΝΟΙΑ ΛΕΥΚΩΣΙΑΣ',
            'badge': 'CYPRUS LEAGUE & EUROPA LEAGUE',
            'icon': '☘️',
            'gradient': 'from-emerald-900 via-green-900 to-emerald-950',
            'border_cls': 'border-emerald-800/40 dark:border-emerald-700/50',
            'badge_bg': 'bg-emerald-950/70 text-emerald-200 border border-emerald-500/30',
            'default_hl_query': 'Omonoia+FC+highlights+2026',
            'default_source': {'name': 'OmonoiaFC.com.cy', 'url': 'https://www.omonoiafc.com.cy/'}
        },
        'manutd': {
            'name': 'MANCHESTER UNITED',
            'badge': 'PREMIER LEAGUE',
            'icon': '🔴',
            'gradient': 'from-red-950 via-zinc-950 to-black',
            'border_cls': 'border-red-900/40 dark:border-red-800/50',
            'badge_bg': 'bg-red-950/70 text-red-200 border border-red-500/30',
            'default_hl_query': 'Manchester+United+highlights+2026',
            'default_source': {'name': 'Premier League', 'url': 'https://www.premierleague.com/'}
        },
        'realmadrid': {
            'name': 'REAL MADRID',
            'badge': 'LA LIGA & CHAMPIONS LEAGUE',
            'icon': '👑',
            'gradient': 'from-slate-950 via-blue-950 to-indigo-950',
            'border_cls': 'border-blue-900/40 dark:border-blue-800/50',
            'badge_bg': 'bg-blue-950/70 text-blue-200 border border-blue-500/30',
            'default_hl_query': 'Real+Madrid+highlights+2026',
            'default_source': {'name': 'RealMadrid.com', 'url': 'https://www.realmadrid.com/'}
        },
        'formula1': {
            'name': 'FORMULA 1',
            'badge': 'FIA WORLD CHAMPIONSHIP',
            'icon': '🏎️',
            'gradient': 'from-neutral-950 via-zinc-900 to-red-950',
            'border_cls': 'border-red-900/40 dark:border-red-800/50',
            'badge_bg': 'bg-red-950/70 text-red-200 border border-red-500/30',
            'default_hl_query': 'Formula+1+highlights+2026',
            'default_source': {'name': 'Formula1.com', 'url': 'https://www.formula1.com/'}
        }
    }

    def build_sport_card(key, team_data):
        meta = SPORTS_META.get(key, {})
        last_res = team_data.get('last_result', '')
        nxt_match = team_data.get('next_match', '')
        hl_info = team_data.get('highlights')
        news_items = team_data.get('news', [])
        src_info = team_data.get('source') or meta.get('default_source')

        # 1. Scoreboard Box
        scoreboard_html = ""
        if last_res:
            if key == 'formula1':
                m_gp = re.search(r'\*\*([^*]+Grand Prix[^*]*)\*\*', last_res, re.I)
                gp_title = m_gp.group(1).strip() if m_gp else 'Italian Grand Prix 2026 (Monza)'
                scoreboard_html = f'''
                <div class="bg-[var(--paper)] border border-[var(--rule)] rounded-2xl p-5 mb-6 shadow-xs">
                  <div class="flex items-center justify-between text-xs font-mono text-[var(--ink-quiet)] uppercase mb-2.5">
                    <span class="flex items-center gap-2 font-bold">🏁 ΤΕΛΕΥΤΑΙΟ GRAND PRIX</span>
                    <span class="px-2.5 py-0.5 rounded-full bg-red-100 text-red-800 dark:bg-red-950/70 dark:text-red-300 font-bold">MONZA</span>
                  </div>
                  <div class="text-base sm:text-lg font-bold text-[var(--ink)] font-sans mb-2.5">{gp_title}</div>
                  <div class="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-red-600/10 dark:bg-red-500/15 border border-red-500/30 text-xs sm:text-sm font-mono font-bold text-red-700 dark:text-red-300 mb-3">
                    <span>🏆</span> <span>P1 Antonelli · P2 Russell · P3 Verstappen</span>
                  </div>
                  <p class="text-sm text-[var(--ink-body)] leading-relaxed">
                    {md_to_inline_html(last_res)}
                  </p>
                </div>'''
            else:
                score_m = re.search(r'\b(\d+)\s*[-–]\s*(\d+)\b', last_res)
                score_str = f"{score_m.group(1)} – {score_m.group(2)}" if score_m else "FT"
                first_part = last_res.split('(')[0].replace('**', '').strip()
                fixture = re.sub(r'\s*\b\d+\s*[-–]\s*\d+\b\s*', '', first_part).strip(' –-')
                fixture = re.sub(r'\s*–\s*', ' vs ', fixture)
                scoreboard_html = f'''
                <div class="bg-[var(--paper)] border border-[var(--rule)] rounded-2xl p-5 mb-6 shadow-xs">
                  <div class="flex items-center justify-between text-xs font-mono text-[var(--ink-quiet)] uppercase mb-2.5">
                    <span class="flex items-center gap-2 font-bold">⚽ ΤΕΛΕΥΤΑΙΟ ΑΠΟΤΕΛΕΣΜΑ</span>
                    <span class="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 dark:bg-emerald-950/70 dark:text-emerald-300 font-bold">FT</span>
                  </div>
                  <div class="flex flex-wrap items-center justify-between gap-3 mb-3">
                    <div class="text-base sm:text-lg font-bold text-[var(--ink)]">{fixture}</div>
                    <div class="px-3.5 py-1.5 rounded-xl bg-slate-900 text-amber-400 font-mono font-black text-lg tracking-wider shadow-inner">
                      {score_str}
                    </div>
                  </div>
                  <p class="text-sm text-[var(--ink-body)] leading-relaxed">
                    {md_to_inline_html(last_res)}
                  </p>
                </div>'''

        # 2. YouTube Highlights Card
        if hl_info and hl_info.get('url'):
            hl_url = hl_info['url']
            hl_title = hl_info['title']
        else:
            hl_url = f"https://www.youtube.com/results?search_query={meta.get('default_hl_query', 'sports+highlights')}"
            hl_title = f"Δείτε τα Highlights ({meta.get('name')})"

        highlights_html = f'''
        <a href="{hl_url}" target="_blank" rel="noopener noreferrer" 
           class="group flex items-center justify-between p-4 rounded-2xl bg-gradient-to-r from-red-600/10 via-red-600/5 to-transparent hover:from-red-600/20 hover:to-red-600/15 border border-red-500/30 hover:border-red-500/50 transition-all duration-200 mb-6 shadow-xs">
          <div class="flex items-center gap-3.5 min-w-0 flex-1">
            <span class="w-10 h-10 flex-shrink-0 rounded-xl bg-red-600 text-white flex items-center justify-center font-bold text-base shadow-sm group-hover:scale-110 transition-transform">
              ▶
            </span>
            <div class="min-w-0 flex-1">
              <div class="text-xs font-mono uppercase tracking-wider text-red-600 dark:text-red-400 font-bold flex items-center gap-1.5">
                <span>🎬 YOUTUBE HIGHLIGHTS</span>
                <span class="text-[9px] px-1.5 py-0.2 rounded bg-red-600 text-white font-semibold">HD</span>
              </div>
              <div class="text-sm font-semibold text-[var(--ink)] group-hover:text-red-600 dark:group-hover:text-red-400 mt-1 break-words">
                {hl_title}
              </div>
            </div>
          </div>
          <span class="text-base text-red-600 dark:text-red-400 font-bold group-hover:translate-x-1.5 transition-transform ml-3 flex-shrink-0">↗</span>
        </a>'''

        # 3. Next Match / Grand Prix
        next_match_html = ""
        if nxt_match:
            lbl = "🏁 ΕΠΟΜΕΝΟ GRAND PRIX" if key == 'formula1' else "📅 ΕΠΟΜΕΝΟΣ ΑΓΩΝΑΣ"
            next_match_html = f'''
            <div class="p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] mb-6 shadow-xs">
              <div class="text-xs font-mono text-[var(--ink-quiet)] uppercase tracking-wider mb-2 flex items-center gap-1.5 font-bold">
                {lbl}
              </div>
              <div class="text-sm sm:text-base font-semibold text-[var(--ink)] leading-relaxed">
                {md_to_inline_html(nxt_match)}
              </div>
            </div>'''

        # 4. News & Squad Report
        news_html = ""
        if news_items:
            bullets = ''.join([f'<li class="leading-relaxed pl-1">{md_to_inline_html(n)}</li>' for n in news_items if n and n not in ['--', '---']])
            news_html = f'''
            <div class="mb-6">
              <div class="text-xs font-mono text-[var(--ink-quiet)] uppercase tracking-wider mb-3 font-bold flex items-center gap-2">
                <span>📋</span> <span>ΑΓΩΝΙΣΤΙΚΑ ΝΕΑ & ΡΕΠΟΡΤΑΖ</span>
              </div>
              <ul class="text-sm text-[var(--ink-body)] space-y-3 list-disc list-inside leading-relaxed">
                {bullets}
              </ul>
            </div>'''

        # Fallback raw list if neither scoreboard nor next match
        fallback_raw = ""
        if not scoreboard_html and not next_match_html and team_data.get('raw'):
            raw_bullets = ''.join([f'<li class="leading-relaxed pl-1">{md_to_inline_html(r)}</li>' for r in team_data['raw'] if r and r not in ['--', '---']])
            fallback_raw = f'<ul class="text-sm text-[var(--ink-body)] space-y-3 list-disc list-inside mb-6">{raw_bullets}</ul>'

        # 5. Source
        src_url = src_info.get('url', '#') if src_info else '#'
        src_name = src_info.get('name', 'Επίσημη Πηγή') if src_info else 'Επίσημη Πηγή'
        source_html = f'''
        <div class="pt-4 border-t border-[var(--rule)] mt-auto flex items-center justify-between t-meta">
          <span class="text-[var(--ink-quiet)] font-mono flex items-center gap-1.5">
            <span>🌐</span> <span>Επίσημο Κανάλι:</span>
          </span>
          <a href="{src_url}" target="_blank" rel="noopener noreferrer" class="font-semibold text-[var(--accent)] hover:underline">
            {src_name}
          </a>
        </div>'''

        return f'''
        <article class="card overflow-hidden flex flex-col justify-between border rounded-2xl shadow-sm {meta.get('border_cls', '')}">
          <div>
            <!-- Header -->
            <div class="bg-gradient-to-r {meta.get('gradient', 'from-slate-900 to-black')} p-5 sm:p-6 text-white">
              <div class="flex flex-wrap items-center justify-between gap-3">
                <div class="flex items-center gap-3">
                  <span class="text-3xl sm:text-4xl">{meta.get('icon', '⚽')}</span>
                  <h3 class="font-masthead font-bold text-base sm:text-lg tracking-wide text-white">{meta.get('name', key.upper())}</h3>
                </div>
                <span class="t-meta uppercase tracking-wider px-3 py-1 rounded-full text-xs {meta.get('badge_bg', 'bg-white/10 text-white/90')}">
                  {meta.get('badge', '')}
                </span>
              </div>
            </div>

            <!-- Content with generous spacing -->
            <div class="p-6 sm:p-7 lg:p-8">
              {scoreboard_html}
              {highlights_html}
              {next_match_html}
              {news_html}
              {fallback_raw}
            </div>
          </div>

          <div class="p-6 sm:p-7 lg:p-8 pt-0">
            {source_html}
          </div>
        </article>
        '''

    sports_cards_html = '\n'.join([
        build_sport_card('omonoia', data['sports'].get('omonoia', {})),
        build_sport_card('manutd', data['sports'].get('manutd', {})),
        build_sport_card('realmadrid', data['sports'].get('realmadrid', {})),
        build_sport_card('formula1', data['sports'].get('formula1', {}))
    ])

    # Weather narrative with rich emojis & badges (never showing -- separators)
    wx_formatted_items = []
    for raw in data['weather'].get('raw_items', []):
        if not raw or raw.strip() in ['--', '---'] or raw.startswith('---'):
            continue
        icon = '🌤️'
        low = raw.lower()
        if 'θερμοκρασία' in low:
            icon = '🌡️'
        elif 'υγρασία' in low:
            icon = '💧'
        elif 'άνεμος' in low or 'ανεμοι' in low:
            icon = '💨'
        elif 'προειδοποιήσεις' in low or 'προειδοποίηση' in low or 'uv' in low:
            icon = '⚠️'
        elif 'πρόγνωση' in low or 'αίθριος' in low:
            icon = '☀️'
        elif 'πηγή' in low:
            icon = '🌐'

        m_label = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', raw)
        if m_label:
            lbl = m_label.group(1).strip()
            rest = md_to_inline_html(m_label.group(2).strip())
            is_warn = (icon == '⚠️')
            bg_cls = "bg-amber-500/10 border border-amber-500/30 dark:bg-amber-950/30" if is_warn else "bg-[var(--paper)] border border-[var(--rule)]"
            wx_formatted_items.append(f'''
            <div class="flex items-start gap-3.5 p-3.5 rounded-xl {bg_cls} shadow-2xs">
              <span class="text-xl flex-shrink-0 mt-0.5">{icon}</span>
              <div class="text-xs sm:text-sm text-[var(--ink-body)] leading-relaxed">
                <span class="font-bold text-[var(--ink)]">{lbl}:</span> {rest}
              </div>
            </div>''')
        else:
            wx_formatted_items.append(f'''
            <div class="flex items-start gap-3.5 p-3.5 rounded-xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <span class="text-xl flex-shrink-0 mt-0.5">{icon}</span>
              <div class="text-xs sm:text-sm text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(raw)}</div>
            </div>''')
    wx_items_html = '\n'.join(wx_formatted_items)

    # Developments Cards (clean executive blocks without raw asterisks)
    dev_cards = []
    for item in data['developments']:
        if not item or item.strip() in ['--', '---'] or item.startswith('---'):
            continue
        m = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', item)
        if m:
            title = m.group(1).strip()
            body = md_to_inline_html(m.group(2).strip())
            dev_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] transition-all shadow-2xs">
              <div class="font-bold text-sm sm:text-base text-[var(--ink)] mb-2 flex items-center gap-2">
                <span class="w-2.5 h-2.5 rounded-full bg-[var(--accent)] flex-shrink-0"></span>
                <span>{title}</span>
              </div>
              <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">{body}</p>
            </div>''')
        else:
            dev_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(item)}</p>
            </div>''')
    dev_html = '\n'.join(dev_cards)

    # Portfolio Cards
    port_cards = []
    for item in data['portfolio']:
        if not item or item.strip() in ['--', '---'] or item.startswith('---'):
            continue
        m = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', item)
        if m:
            title = m.group(1).strip()
            body = md_to_inline_html(m.group(2).strip())
            port_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] transition-all shadow-2xs">
              <div class="font-bold text-sm sm:text-base text-[var(--ink)] mb-2 flex items-center gap-2">
                <span>🎯</span> <span>{title}</span>
              </div>
              <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">{body}</p>
            </div>''')
        else:
            port_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(item)}</p>
            </div>''')
    port_html = '\n'.join(port_cards)

    # Deadlines Cards (actionable timeline pills with active links)
    dead_cards = []
    for item in data['deadlines']:
        if not item or item.strip() in ['--', '---'] or item.startswith('---'):
            continue
        m = re.match(r'^\*\*(.*?)\*\*\s*[—–-]\s*(.*)$', item)
        if m:
            date_str = m.group(1).strip()
            rest_str = m.group(2).strip()
            m_act = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', rest_str)
            if m_act:
                act_title = m_act.group(1).strip()
                det_body = md_to_inline_html(m_act.group(2).strip())
            else:
                act_title = ""
                det_body = md_to_inline_html(rest_str)
            
            dead_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] transition-all shadow-2xs flex flex-col justify-between">
              <div>
                <div class="flex items-center justify-between gap-2 mb-2.5">
                  <span class="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-mono font-bold bg-[var(--accent)]/15 text-[var(--accent)] border border-[var(--accent)]/30">
                    <span>📅</span> <span>{date_str}</span>
                  </span>
                  <span class="t-meta text-[var(--ink-quiet)] uppercase font-mono font-semibold">ΠΡΟΘΕΣΜΙΑ</span>
                </div>
                {f'<div class="font-bold text-sm sm:text-base text-[var(--ink)] mb-1.5">{act_title}</div>' if act_title else ''}
                <div class="t-body-sm text-[var(--ink-body)] leading-relaxed">{det_body}</div>
              </div>
            </div>''')
        else:
            dead_cards.append(f'''
            <div class="p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <div class="t-body-sm text-[var(--ink-body)] leading-relaxed">{md_to_inline_html(item)}</div>
            </div>''')
    dead_html = '\n'.join(dead_cards)

    # Tomorrow Cards (numbered executive agenda points)
    tom_cards = []
    for idx, item in enumerate(data['tomorrow']):
        if not item or item.strip() in ['--', '---'] or item.startswith('---'):
            continue
        m = re.match(r'^\*\*(.*?)\*\*:?\s*(.*)$', item)
        if m:
            title = m.group(1).strip()
            desc = md_to_inline_html(m.group(2).strip())
            tom_cards.append(f'''
            <div class="flex items-start gap-4 p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] hover:border-[var(--accent)] transition-all shadow-2xs">
              <div class="w-9 h-9 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 text-[var(--accent)] flex items-center justify-center font-mono font-black text-sm flex-shrink-0">
                {idx+1:02d}
              </div>
              <div class="flex-1 min-w-0">
                <div class="font-bold text-sm sm:text-base text-[var(--ink)] mb-1">{title}</div>
                <div class="t-body-sm text-[var(--ink-body)] leading-relaxed">{desc}</div>
              </div>
            </div>''')
        else:
            tom_cards.append(f'''
            <div class="flex items-start gap-4 p-4 sm:p-5 rounded-2xl bg-[var(--paper)] border border-[var(--rule)] shadow-2xs">
              <div class="w-9 h-9 rounded-xl bg-[var(--accent)]/15 border border-[var(--accent)]/30 text-[var(--accent)] flex items-center justify-center font-mono font-black text-sm flex-shrink-0">
                {idx+1:02d}
              </div>
              <div class="t-body-sm text-[var(--ink-body)] leading-relaxed flex-1 min-w-0">{md_to_inline_html(item)}</div>
            </div>''')
    tom_html = '\n'.join(tom_cards)

    # Footnotes
    foot_html = ''.join([f'<li class="leading-relaxed">{md_to_inline_html(item)}</li>' for item in data['footnotes'] if item and item not in ['--', '---'] and not item.startswith('---')])

    # Top Story Source Links
    top_sources = []
    for s in data['top_story'].get('sources', []):
        top_sources.append(f'<a href="{s["url"]}" target="_blank" rel="noopener noreferrer" class="text-[var(--accent)] hover:underline font-semibold">{s["name"]}</a>')
    top_sources_html = ' · '.join(top_sources)

    # Full HTML Document
    html = f'''<!DOCTYPE html>
<html lang="el">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <title>THE ORACLE SOVEREIGN — {date_display}</title>
  <script src="https://cdn.tailwindcss.com/3.4.16"></script>
  <script>
    tailwind.config = {{ darkMode: 'class' }};
  </script>
  <script>
    (function () {{
      var s = localStorage.getItem('oracle-theme');
      var d = s ? s === 'dark' : window.matchMedia('(prefers-color-scheme: dark)').matches;
      if (d) document.documentElement.classList.add('dark');
    }})();
  </script>
  <style>
    @import url('https://fonts.googleapis.com/css2?family=Cinzel:wght@600;700;900&family=Newsreader:ital,opsz,wght@0,6..72,400;0,6..72,600;0,6..72,700;1,6..72,400&family=Inter:wght@300;400;500;600;700&display=swap');

    :root {{
      --paper: #f6f3ec;
      --paper-raised: #fffdf8;
      --rule: #d9d3c5;
      --rule-strong: #b3aa96;
      --ink: #17150f;
      --ink-body: #2e2a22;
      --ink-quiet: #6d675a;
      --accent: #8a5320;
      --up: #1f6b3f;
      --down: #a3282b;
      --s1: 4px;
      --s2: 8px;
      --s3: 12px;
      --s4: 16px;
      --s5: 24px;
      --s6: 32px;
      --s7: 48px;
      --s8: 64px;
      --r-sm: 4px;
      --r-md: 8px;

      /* Compatible fallbacks */
      --paper-bg: var(--paper);
      --paper-card: var(--paper-raised);
      --paper-border: var(--rule);
      --ink-dark: var(--ink);
      --ink-muted: var(--ink-quiet);
      --accent-gold: var(--accent);
      --accent-blue: var(--accent);
      --accent-red: var(--down);
      --accent-green: var(--up);
    }}

    .dark {{
      --paper: #14120e;
      --paper-raised: #1c1a15;
      --rule: #33302a;
      --rule-strong: #4a463d;
      --ink: #f4f1e8;
      --ink-body: #ddd8cc;
      --ink-quiet: #948d7e;
      --accent: #d69a5c;
      --up: #56b37c;
      --down: #e0736f;

      /* Compatible fallbacks */
      --paper-bg: var(--paper);
      --paper-card: var(--paper-raised);
      --paper-border: var(--rule);
      --ink-dark: var(--ink);
      --ink-muted: var(--ink-quiet);
      --accent-gold: var(--accent);
      --accent-blue: var(--accent);
      --accent-red: var(--down);
      --accent-green: var(--up);
    }}

    body {{
      font-family: 'Newsreader', Georgia, serif;
      background-color: var(--paper);
      color: var(--ink-body);
      transition: background-color 0.2s ease, color 0.2s ease;
    }}

    /* Typographical scale */
    .t-masthead {{
      font-family: 'Cinzel', serif;
      font-weight: 900;
      font-size: clamp(2.4rem, 7vw, 4.4rem);
      line-height: 0.95;
      letter-spacing: .06em;
    }}
    .t-section {{
      font-family: 'Newsreader', Georgia, serif;
      font-weight: 700;
      font-size: 1.55rem;
      line-height: 1.15;
      letter-spacing: -.01em;
      color: var(--ink);
    }}
    .t-lead {{
      font-family: 'Newsreader', Georgia, serif;
      font-weight: 700;
      font-size: clamp(1.6rem, 3vw, 2.3rem);
      line-height: 1.18;
      letter-spacing: -.02em;
      color: var(--ink);
    }}
    .t-title {{
      font-family: 'Newsreader', Georgia, serif;
      font-weight: 700;
      font-size: 1.2rem;
      line-height: 1.28;
      letter-spacing: -.01em;
      color: var(--ink);
    }}
    .t-body {{
      font-family: 'Newsreader', Georgia, serif;
      font-weight: 400;
      font-size: 1.0625rem;
      line-height: 1.62;
      color: var(--ink-body);
      max-width: 68ch;
    }}
    .t-body-sm {{
      font-family: 'Newsreader', Georgia, serif;
      font-weight: 400;
      font-size: .95rem;
      line-height: 1.6;
      color: var(--ink-body);
    }}
    .t-meta {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
      font-weight: 500;
      font-size: .75rem;
      line-height: 1.4;
      color: var(--ink-quiet);
    }}
    .t-num {{
      font-variant-numeric: tabular-nums;
      font-feature-settings: "tnum";
    }}

    /* Cards */
    .card, .editorial-card {{
      background-color: var(--paper-raised);
      border: 1px solid var(--rule);
      border-radius: var(--r-md);
      transition: border-color 0.2s ease;
    }}
    .card:hover, .editorial-card:hover {{
      border-color: var(--rule-strong);
    }}
    .card--hero {{
      background-color: var(--paper-raised);
      border: 1px solid var(--rule);
      border-radius: var(--r-md);
      box-shadow: 0 4px 20px -2px rgba(0, 0, 0, 0.05);
    }}

    /* Drop cap for lead story */
    .lead-body::first-letter {{
      font-family: 'Cinzel', serif;
      font-size: 3.4rem;
      line-height: 0.8;
      float: left;
      margin-top: 0.12em;
      margin-right: 0.18em;
      margin-bottom: -0.05em;
      font-weight: 700;
      color: var(--accent);
    }}

    /* Focus & Accessibility */
    :focus-visible {{
      outline: 2px solid var(--accent);
      outline-offset: 2px;
    }}

    /* ============================================== */
    /* BESPOKE BROADSHEET PRINT / PDF EXPORT          */
    /* Financial Times / NYT quality broadsheet layout */
    /* ============================================== */
    @media print {{
      @page {{
        size: A4;
        margin: 1.2cm 1.5cm;
      }}

      * {{
        -webkit-print-color-adjust: exact !important;
        print-color-adjust: exact !important;
      }}

      body {{
        background-color: #ffffff !important;
        color: #0a0a0a !important;
        font-size: 9.5pt !important;
        line-height: 1.45 !important;
        font-family: 'Newsreader', 'Georgia', 'Times New Roman', serif !important;
      }}

      /* Hide all interactive / digital-only elements */
      .ticker-wrap,
      nav,
      #mainNav,
      #themeToggle,
      #themeToggleNav,
      #archiveSearch,
      #searchResults,
      button,
      input[type="range"],
      a[href*="youtube.com"],
      .print\\:hidden,
      .no-print,
      footer {{
        display: none !important;
      }}

      /* Force show all expandable content */
      details {{
        display: block !important;
      }}
      details summary {{
        display: none !important;
      }}
      details > div {{
        display: block !important;
        border: none !important;
        padding: 0 !important;
        margin-top: 0.3em !important;
      }}

      /* Broadsheet masthead */
      .font-masthead {{
        font-size: 28pt !important;
        font-weight: 900 !important;
        letter-spacing: -0.02em !important;
        border-bottom: 3pt double #000 !important;
        padding-bottom: 0.3em !important;
        margin-bottom: 0.5em !important;
        text-align: center !important;
      }}

      /* Section headers — broadsheet rules */
      .t-section {{
        font-size: 13pt !important;
        font-weight: 800 !important;
        text-transform: uppercase !important;
        letter-spacing: 0.08em !important;
        border-bottom: 2pt solid #000 !important;
        padding-bottom: 0.15em !important;
        margin-bottom: 0.6em !important;
        page-break-after: avoid !important;
      }}

      /* Card layout — clean flat broadsheet panels */
      .card, .card--hero, .editorial-card {{
        border: none !important;
        border-bottom: 0.5pt solid #ccc !important;
        box-shadow: none !important;
        border-radius: 0 !important;
        padding: 0.4em 0 !important;
        margin-bottom: 0.5em !important;
        page-break-inside: avoid !important;
        background: transparent !important;
      }}

      /* Headlines in print */
      .t-lead {{
        font-size: 16pt !important;
        font-weight: 800 !important;
        line-height: 1.15 !important;
      }}
      .t-title {{
        font-size: 12pt !important;
        font-weight: 700 !important;
        line-height: 1.2 !important;
      }}

      /* Body text — newspaper column style */
      .t-body, .t-body-sm {{
        font-size: 9pt !important;
        line-height: 1.4 !important;
        text-align: justify !important;
        hyphens: auto !important;
      }}

      /* Meta / source lines */
      .t-meta {{
        font-size: 7.5pt !important;
        color: #666 !important;
      }}

      /* Links — print as black, no decoration */
      a {{
        text-decoration: none !important;
        color: #0a0a0a !important;
      }}

      /* Grid columns → stacked for print */
      .grid {{
        display: block !important;
      }}

      /* Images — constrained, captioned */
      img {{
        max-height: 160px !important;
        width: auto !important;
        margin: 0 auto 0.3em !important;
        display: block !important;
        border: 0.5pt solid #ddd !important;
      }}

      /* Dashboard table compact */
      table {{
        font-size: 8pt !important;
        border-collapse: collapse !important;
      }}
      th, td {{
        padding: 2pt 4pt !important;
        border-bottom: 0.5pt solid #ddd !important;
      }}

      /* Sports cards — compact inline */
      .bg-gradient-to-br {{
        background: transparent !important;
        color: #000 !important;
      }}

      /* Weather — inline compact */
      #weatherGrid {{
        display: block !important;
      }}

      /* Page breaks */
      h2 {{
        page-break-after: avoid !important;
      }}
      article {{
        page-break-inside: avoid !important;
      }}

      /* Add print footer with branding */
      body::after {{
        content: "THE ORACLE SOVEREIGN — Confidential Executive Briefing — © 2026";
        display: block;
        text-align: center;
        font-size: 7pt;
        color: #999;
        margin-top: 1cm;
        border-top: 0.5pt solid #ccc;
        padding-top: 0.3em;
      }}
    }}

    .ticker-wrap {{
      overflow: hidden;
      white-space: nowrap;
    }}

    .ticker-content {{
      display: inline-block;
      animation: tickerAnimation 40s linear infinite;
    }}

    .ticker-wrap:hover .ticker-content {{
      animation-play-state: paused;
    }}

    @keyframes tickerAnimation {{
      0% {{ transform: translateX(0); }}
      100% {{ transform: translateX(-50%); }}
    }}

    @media (prefers-reduced-motion: reduce) {{
      .ticker-content {{ animation: none; }}
      body {{ transition: none; }}
    }}
    [id] {{ scroll-margin-top: 5rem; }}
    @media (max-width: 640px) {{ [id] {{ scroll-margin-top: 5rem; }} }}

    /* Smart Navigation Header (Headroom Auto-hide) */
    #mainNav {{
      position: sticky;
      top: 0;
      z-index: 40;
      transition: transform 0.28s cubic-bezier(0.16, 1, 0.3, 1), box-shadow 0.2s ease;
      will-change: transform;
    }}
    #mainNav.nav-hidden {{
      transform: translateY(-100%);
      box-shadow: none !important;
    }}
    .no-scrollbar::-webkit-scrollbar {{
      display: none;
    }}
    .no-scrollbar {{
      -ms-overflow-style: none;
      scrollbar-width: none;
    }}

    details > summary {{
      list-style: none;
    }}
    details > summary::-webkit-details-marker {{
      display: none;
    }}
    details[open] summary .expand-icon {{
      transform: rotate(180deg);
    }}

    /* Executive 60-Second Scan Mode */
    body.scan-mode article:not(:first-of-type),
    body.scan-mode #world,
    body.scan-mode #sports,
    body.scan-mode #portfolio,
    body.scan-mode #developments,
    body.scan-mode #rates-and-tools,
    body.scan-mode details.depth,
    body.scan-mode #houseSearchSection,
    body.scan-mode .ticker-wrap {{
      display: none !important;
    }}
    body.scan-mode #top-story {{
      border: 2px solid var(--accent);
      border-radius: var(--r-md);
      padding: 1.25rem;
      background: var(--paper-raised);
    }}
  </style>
</head>
<body class="antialiased min-h-screen">

  <!-- TOP BAR & STATUS -->
  <div class="bg-[var(--paper-raised)] border-b border-[var(--rule)] text-xs py-1.5 px-4">
    <div class="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-2">
      <div class="flex flex-wrap items-center gap-3">
        <span id="freshness" data-generated="{gen_iso}"
              class="inline-flex items-center px-2 py-0.5 rounded t-meta font-semibold"></span>

        <script>
        (function () {{
          const el = document.getElementById('freshness');
          const gen = new Date(el.dataset.generated);
          const paint = () => {{
            const mins = Math.round((Date.now() - gen) / 60000);
            let txt, cls;
            if (mins < 90) {{ txt = `● ΦΡΕΣΚΟ · πριν ${{mins}}′`; cls = 'bg-[var(--up)]/15 text-[var(--up)] border border-[var(--up)]/30'; }}
            else if (mins < 720) {{ txt = `◐ πριν ${{Math.round(mins / 60)}} ώρες`; cls = 'bg-[var(--accent)]/15 text-[var(--accent)] border border-[var(--accent)]/30'; }}
            else {{ txt = `○ ΑΡΧΕΙΟ · ${{gen.toLocaleDateString('el-CY')}}`; cls = 'bg-[var(--rule)]/50 text-[var(--ink-quiet)]'; }}
            el.textContent = txt;
            el.className = 'inline-flex items-center px-2 py-0.5 rounded t-meta font-semibold ' + cls;
          }};
          paint(); setInterval(paint, 60000);
        }})();
        </script>
        <span class="t-meta text-[var(--ink-quiet)]">{date_display}</span>
        <span class="hidden sm:inline text-[var(--ink-quiet)]">·</span>
        <span class="hidden sm:inline t-meta text-[var(--ink-quiet)]">{time_display} ώρα Κύπρου (EEST)</span>
        {edition_switcher_html}
      </div>
      <div class="flex items-center gap-4 t-meta text-[var(--ink-quiet)]">
        {global_clocks_html}
        <span>📍 Λεμεσός</span>
        <span>⏱️ ~{read_time}</span>
        <button id="themeToggle" class="px-2.5 py-1 rounded border border-[var(--rule)] hover:bg-[var(--paper)] transition t-meta" aria-pressed="false" aria-label="Εναλλαγή θέματος">
          🌓 Θέμα
        </button>
      </div>
    </div>
  </div>

  <!-- MASTHEAD -->
  <header class="border-b-4 border-double border-[var(--rule-strong)] py-8 px-4 text-center bg-[var(--paper-raised)]">
    <div class="max-w-6xl mx-auto">
      <div class="flex justify-between items-center t-meta uppercase text-[var(--ink-quiet)] border-b border-[var(--rule)] pb-2 mb-4 font-mono">
        <div>ΕΤΟΣ 2026 · DAILY BRIEFING</div>
        <div class="font-bold text-[var(--accent)]">ΕΜΠΙΣΤΕΥΤΙΚΟ BRIEFING</div>
        <div>ONE-READER EDITION</div>
      </div>

      <h1 class="t-masthead text-[var(--ink)] mb-2 uppercase text-center">
        THE ORACLE SOVEREIGN
      </h1>
      <p class="font-editorial italic text-lg sm:text-xl text-[var(--ink-quiet)] max-w-2xl mx-auto text-center">
        Ημερήσια Εφημερίδα Στρατηγικής, Αγορών, Κυπριακής Οικονομίας & Διεθνών Εξελίξεων
      </p>

      <div class="flex flex-wrap justify-center items-center gap-3 mt-5 pt-3 border-t border-[var(--rule)] t-meta text-[var(--ink-quiet)]">
        <span>🇨🇾 Κύπρος & Ακίνητα</span>
        <span>·</span>
        <span>🌍 Γεωπολιτική</span>
        <span>·</span>
        <span>📊 Αγορές & Euribor</span>
        <span>·</span>
        <span>⚽ Ομόνοια, Clubs & Formula 1</span>
        <span>·</span>
        <span>🌤️ Καιρός Λεμεσού</span>
      </div>
    </div>
  </header>

  <!-- LIVE MARKET TICKER -->
  <div class="bg-[var(--paper)] text-[var(--ink)] py-2 border-y border-[var(--rule)] t-meta ticker-wrap">
    <div class="ticker-content space-x-8 font-mono">
      {ticker_html}
    </div>
  </div>

  {live_wire_bar_html}

  <!-- NAVIGATION & INSTANT SEARCH -->
  <nav id="mainNav" class="bg-[var(--paper-raised)] border-b border-[var(--rule)] sticky top-0 z-40 px-3 sm:px-4 py-2 shadow-xs backdrop-blur-md bg-opacity-95" aria-label="Κύρια πλοήγηση">
    <div class="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2.5">
      <div class="flex items-center gap-1.5 t-meta font-medium overflow-x-auto no-scrollbar py-0.5 max-w-full flex-nowrap sm:flex-wrap">
        <a href="#top-story" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--accent)] text-white font-semibold transition">⭐ Πρώτο Θέμα</a>
        <a href="#cyprus" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition font-semibold">🇨🇾 Κύπρος</a>
        <a href="#world" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition">🌍 Διεθνή</a>
        <a href="#sports" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition font-medium">⚽ Αθλητικά & F1</a>
        <a href="#markets" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition">💰 Αγορές</a>
        <a href="#rates-and-tools" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition">🏦 Επιτόκια & Dashboard</a>
        <a href="#portfolio" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition">🎯 Ο Φάκελός μου</a>
        {house_nav_html}
        <a href="#weather" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition">🌤️ Καιρός</a>
        <a href="#deadlines" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition">📅 Προθεσμίες</a>
      </div>

      <!-- Search Input Container with Instant Dropdown & Actions -->
      <div class="relative flex items-center gap-1.5 flex-shrink-0 ml-auto sm:ml-0">
        <button id="scanModeToggle" class="t-meta px-2.5 py-1.5 rounded border border-[var(--rule)] bg-[var(--paper)] hover:border-[var(--accent)] text-[var(--accent)] font-semibold transition flex items-center gap-1" title="Εναλλαγή σε 60-Second Scan">
          <span>⚡</span> <span class="hidden md:inline">60″ Scan</span>
        </button>
        <button onclick="window.print()" class="t-meta px-2.5 py-1.5 rounded border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition flex items-center gap-1" title="Εκτύπωση ή Αποθήκευση σε Broadsheet PDF" aria-label="Εκτύπωση σελίδας">
          <span>📄</span> <span class="hidden md:inline">PDF Broadsheet</span>
        </button>
        <div class="relative">
          <label for="archiveSearch" class="sr-only">Αναζήτηση στο αρχείο</label>
          <input type="text" id="archiveSearch" placeholder="🔍 Αναζήτηση στο αρχείο..." 
                 class="t-meta px-3 py-1.5 rounded border border-[var(--rule)] bg-[var(--paper)] text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] w-32 sm:w-56 focus:w-44 sm:focus:w-60 transition-all shadow-xs">
          <!-- Live Search Results Dropdown -->
          <div id="searchResults" class="hidden absolute right-0 top-full mt-2 w-80 sm:w-96 max-h-96 overflow-y-auto bg-[var(--paper-raised)] border border-[var(--rule)] rounded-xl shadow-xl z-50 p-2 text-xs space-y-2">
          </div>
        </div>
        <button id="themeToggleNav" class="t-meta px-2 py-1.5 rounded border border-[var(--rule)] hover:bg-[var(--paper)] transition" title="Εναλλαγή θέματος" aria-label="Εναλλαγή θέματος">
          🌓
        </button>
      </div>
    </div>
  </nav>

  <!-- MAIN CONTAINER (NEWS-FIRST HIERARCHY) -->
  <main class="max-w-7xl mx-auto px-4 py-8 space-y-12">

    <!-- 🎙️ THE SOVEREIGN EXECUTIVE AUDIO BRIEFING -->
    <div id="audioBriefingPlayer" class="p-4 bg-[var(--paper-raised)] border border-[var(--rule)] rounded-xl flex flex-wrap items-center justify-between gap-3 shadow-xs">
      <div class="flex items-center gap-3.5">
        <button id="audioPlayBtn" class="w-11 h-11 rounded-full bg-[var(--accent)] text-white flex items-center justify-center shadow hover:opacity-90 transition font-bold text-lg flex-shrink-0" aria-label="Αναπαραγωγή ηχητικής σύνοψης">
          ▶
        </button>
        <div>
          <div class="t-meta font-bold text-[var(--ink)] flex items-center gap-2">
            <span>🎙️ Ακρόαση Πρωινής Σύνοψης (The Sovereign Audio Briefing)</span>
            <span id="audioLiveBadge" class="hidden text-[10px] px-1.5 py-0.2 rounded bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-mono font-semibold">LIVE</span>
          </div>
          <div id="audioStatusText" class="t-meta text-[var(--ink-quiet)]">
            Επιτελική σύνοψη ~2 λεπτών · Πατήστε Play για φωνητική ανάγνωση
          </div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <button id="audioSpeedBtn" class="t-meta font-mono px-2.5 py-1 rounded border border-[var(--rule)] bg-[var(--paper)] hover:border-[var(--accent)] text-[var(--ink-body)]" title="Ταχύτητα ανάγνωσης">
          1.0x
        </button>
        <button id="audioStopBtn" class="t-meta px-2.5 py-1 rounded border border-[var(--rule)] bg-[var(--paper)] hover:bg-[var(--down)] hover:text-white text-[var(--ink-quiet)] hidden" title="Διακοπή">
          ⏹ Διακοπή
        </button>
      </div>
    </div>

    <!-- ==================== ⭐ 1. ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ (HERO NEWS) ==================== -->
    <section id="top-story" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>⭐</span> <span>Το Θέμα της Ημέρας</span>
        </h2>
        <span class="t-meta ml-auto uppercase">{top_category}</span>
      </div>

      <div class="card--hero overflow-hidden">
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-0">
          
          <!-- Image Column -->
          <div class="lg:col-span-6 relative min-h-[340px] bg-[var(--paper)]">
            <img src="{top_img}" 
                 alt="{data['top_story'].get('title', '')}" 
                 class="w-full h-full object-cover object-center"
                 onerror="this.onerror=null; this.src='{TOPIC_FALLBACKS['economy']}';">
            <div class="absolute bottom-0 inset-x-0 bg-gradient-to-t from-black/85 via-black/45 to-transparent p-4 text-white">
              <span class="bg-[var(--accent)] font-semibold px-2 py-0.5 rounded t-meta uppercase tracking-wider text-white">{top_category}</span>
              <p class="mt-1 font-medium leading-snug t-meta">{data['top_story'].get('title', '')}</p>
            </div>
          </div>

          <!-- Text Column -->
          <div class="lg:col-span-6 p-6 sm:p-8 flex flex-col justify-between">
            <div>
              <div class="flex items-center gap-2 t-meta uppercase tracking-wider mb-2 text-[var(--accent)] font-semibold">
                <span>Κορυφαία Εξέλιξη</span>
                <span>·</span>
                <span class="text-[var(--ink-quiet)]">Επιβεβαιωμένο</span>
              </div>

              <h3 class="t-lead mb-4">
                {data['top_story'].get('title', '')}
              </h3>

              <p class="t-body lead-body mb-4 leading-relaxed">
                {data['top_story'].get('body', '')}
              </p>

              <details class="depth mt-3 border-t border-[var(--rule)] pt-2.5">
                <summary class="cursor-pointer flex items-center justify-between t-meta font-semibold text-[var(--accent)] hover:underline py-1">
                  <span>Ανάλυση & Αντίλογος</span>
                  <span class="expand-icon transition-transform duration-200 text-[10px]">▼</span>
                </summary>
                <div class="mt-2.5 t-meta text-[var(--ink-body)] space-y-2 bg-[var(--paper)] p-4 rounded border border-[var(--rule)] leading-relaxed">
                  <p>
                    <strong class="text-[var(--ink)]">Ο Αντίλογος:</strong> {data['top_story'].get('antilogos', 'Δεν καταγράφηκε ουσιαστικός αντίλογος.')}
                  </p>
                </div>
              </details>
            </div>

            <div class="flex flex-wrap items-center justify-between gap-3 pt-4 border-t border-[var(--rule)] mt-4">
              <div class="flex items-center gap-2 t-meta">
                <span class="text-[var(--ink-quiet)]">Πηγές:</span>
                {top_sources_html}
              </div>
              <span class="t-meta text-[var(--ink-quiet)] font-mono">{date_display}</span>
            </div>
          </div>

        </div>
      </div>
    </section>

    <!-- ==================== 🇨🇾 2. ΚΥΠΡΟΣ (NEWS LEAD) ==================== -->
    <section id="cyprus" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🇨🇾</span> <span>Κύπρος</span>
        </h2>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {cyprus_cards_html}
      </div>
    </section>

    <!-- ==================== 🌍 3. ΔΙΕΘΝΗ ==================== -->
    <section id="world" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🌍</span> <span>Διεθνή</span>
        </h2>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {world_cards_html}
      </div>
    </section>

    <!-- ==================== ⚽ 4. ΑΘΛΗΤΙΚΑ & FORMULA 1 ==================== -->
    <section id="sports" class="scroll-mt-24 my-8 sm:my-12">
      <div class="flex items-center gap-2 mb-6 pb-3 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🏆</span> <span>Αθλητικός Παλμός & Formula 1</span>
        </h2>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-7 lg:gap-8">
        {sports_cards_html}
      </div>
    </section>

    <!-- ==================== 💰 5. ΑΓΟΡΕΣ: TOP MOVERS ==================== -->
    <section id="markets" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>💰</span> <span>Αγορές & Top Movers</span>
        </h2>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {movers_html}
      </div>
    </section>

    <!-- ==================== 🏦 5. ΕΠΙΤΟΚΙΑ, ΥΠΟΛΟΓΙΣΤΗΣ ΔΟΣΗΣ & DASHBOARD ==================== -->
    <section id="rates-and-tools" class="scroll-mt-24 space-y-8 bg-[var(--paper-raised)] p-6 rounded border border-[var(--rule)]">
      
      <!-- Rates Header -->
      <div class="flex items-center gap-2 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🏦</span> <span>Χρηματοοικονομικά Εργαλεία & Επιτόκια</span>
        </h2>
      </div>

      <!-- Euribor & Mortgage Calculator Grid -->
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
        
        <!-- Euribor Table -->
        <div class="lg:col-span-6 card p-5 flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-3 border-b border-[var(--rule)] pb-2">
              <h3 class="t-title font-bold text-[var(--ink)]">Διατραπεζικά Επιτόκια Euribor</h3>
              <span class="t-meta font-mono text-[var(--ink-quiet)]">euribor-rates.eu</span>
            </div>
            <table class="w-full text-left t-meta mb-4">
              <thead>
                <tr class="border-b border-[var(--rule)] text-[var(--ink-quiet)] font-mono uppercase t-meta">
                  <th class="pb-2 font-medium">Περίοδος</th>
                  <th class="pb-2 font-medium text-center">1M</th>
                  <th class="pb-2 font-medium text-center">3M</th>
                  <th class="pb-2 font-medium text-center">6M</th>
                  <th class="pb-2 font-medium text-center">12M</th>
                </tr>
              </thead>
              <tbody class="divide-y divide-[var(--rule)] font-mono t-num">
                {euribor_rows_html}
              </tbody>
            </table>
            <div class="t-meta text-[var(--ink-body)] space-y-1 bg-[var(--paper)] p-3 rounded border border-[var(--rule)]">
              <div>• <strong class="text-[var(--ink)]">Επιτόκιο ΕΚΤ (deposit facility):</strong> {data['rates']['ecb_rate']} (Επόμενη συνεδρίαση: {data['rates']['next_ecb']})</div>
              <div>• <strong class="text-[var(--ink)]">Μέσο επιτόκιο νέων στεγαστικών Κύπρου:</strong> {data['rates']['cbc_mortgage_rate']} (στοιχεία ΚΤΚ)</div>
              <div>• <strong class="text-[var(--ink)]">Ενδεικτική δόση έκδοσης:</strong> {data['rates']['example_payment']} ({data['rates']['example_change']})</div>
            </div>
          </div>
        </div>

        <!-- Interactive Mortgage Calculator -->
        <div class="lg:col-span-6 card p-5 flex flex-col justify-between no-print">
          <div>
            <div class="flex items-center justify-between mb-3 border-b border-[var(--rule)] pb-2">
              <h3 class="t-title font-bold text-[var(--ink)]">Υπολογιστής Στεγαστικής Δόσης</h3>
              <span class="t-meta font-mono text-[var(--accent)] font-bold">ΔΙΑΔΡΑΣΤΙΚΟ</span>
            </div>
            
            <div class="space-y-4 t-meta">
              <div>
                <div class="flex justify-between items-center mb-1">
                  <label for="calcAmount" class="font-medium text-[var(--ink)]">Ποσό Δανείου (€):</label>
                  <span id="amountVal" class="font-mono font-bold text-[var(--accent)]">€200.000</span>
                </div>
                <input type="range" id="calcAmount" min="50000" max="800000" step="10000" value="200000" class="w-full" style="accent-color: var(--accent);">
              </div>

              <div>
                <div class="flex justify-between items-center mb-1">
                  <label for="calcYears" class="font-medium text-[var(--ink)]">Διάρκεια (Έτη):</label>
                  <span id="yearsVal" class="font-mono font-bold text-[var(--accent)]">25 έτη</span>
                </div>
                <input type="range" id="calcYears" min="5" max="35" step="1" value="25" class="w-full" style="accent-color: var(--accent);">
              </div>

              <div>
                <div class="flex justify-between items-center mb-1">
                  <label for="calcRate" class="font-medium text-[var(--ink)]">Συνολικό Επιτόκιο (%):</label>
                  <span id="rateVal" class="font-mono font-bold text-[var(--accent)]">3,78%</span>
                </div>
                <input type="range" id="calcRate" min="1.0" max="8.0" step="0.05" value="3.78" class="w-full" style="accent-color: var(--accent);">
              </div>

              <!-- Results Panel -->
              <div class="bg-[var(--paper)] border border-[var(--rule)] p-4 rounded-xl mt-4 space-y-3">
                <div class="flex items-center justify-between">
                  <div>
                    <div class="t-meta font-mono text-[var(--ink-quiet)] uppercase tracking-wider">Μηνιαία Δόση</div>
                    <div id="monthlyInstallment" class="font-masthead text-2xl sm:text-3xl font-black text-[var(--accent)]">€1.032</div>
                  </div>
                  <div class="text-right">
                    <div class="t-meta font-mono text-[var(--ink-quiet)] uppercase tracking-wider">Σύνολο Τόκων</div>
                    <div id="totalInterest" class="font-mono text-sm sm:text-base font-bold text-[var(--down)]">€109.680</div>
                  </div>
                </div>
                <!-- Total repayment + cost of credit -->
                <div class="flex items-center justify-between border-t border-[var(--rule)] pt-2">
                  <div>
                    <div class="t-meta font-mono text-[var(--ink-quiet)] uppercase tracking-wider">Συνολική Αποπληρωμή</div>
                    <div id="totalRepayment" class="font-mono text-sm font-bold text-[var(--ink)]">€309.680</div>
                  </div>
                  <div class="text-right">
                    <div class="t-meta font-mono text-[var(--ink-quiet)] uppercase tracking-wider">Κόστος Πίστωσης</div>
                    <div id="costOfCredit" class="font-mono text-sm font-bold text-[var(--ink)]">54,8%</div>
                  </div>
                </div>
                <!-- Visual cost breakdown bar -->
                <div class="mt-2">
                  <div class="flex w-full h-3 rounded-full overflow-hidden">
                    <div id="principalBar" class="bg-[var(--accent)] transition-all duration-300" style="width:65%"></div>
                    <div id="interestBar" class="bg-[var(--down)] opacity-60 transition-all duration-300" style="width:35%"></div>
                  </div>
                  <div class="flex justify-between mt-1">
                    <span class="t-meta font-mono text-[var(--ink-quiet)]">🟢 Κεφάλαιο</span>
                    <span class="t-meta font-mono text-[var(--ink-quiet)]">🔴 Τόκοι</span>
                  </div>
                </div>
                <!-- Euribor comparison -->
                <div id="euriborCompare" class="border-t border-[var(--rule)] pt-2 mt-2">
                  <div class="t-meta font-mono text-[var(--ink-quiet)] uppercase tracking-wider mb-1">📊 Σύγκριση Euribor 3M</div>
                  <div class="flex items-center gap-2">
                    <span class="t-meta text-[var(--ink-body)]">Αν Euribor 3M + spread 1,1%:</span>
                    <span id="euriborPayment" class="font-mono font-bold text-[var(--up)]">€977</span>
                    <span id="euriborDiff" class="t-meta font-mono text-[var(--up)]">(−€55/μήνα)</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

      </div>

      <!-- Dashboard Watchlist & Number of Day -->
      <div id="dashboard" class="grid grid-cols-1 lg:grid-cols-12 gap-6 pt-4 border-t border-[var(--rule)]">
        <div class="lg:col-span-8 card p-5 overflow-x-auto">
          <div class="flex items-center justify-between mb-3 border-b border-[var(--rule)] pb-2">
            <h3 class="t-title font-bold text-[var(--ink)]">Πίνακας Δεικτών & Assets</h3>
            <span class="t-meta font-mono text-[var(--ink-quiet)]">MARKET WATCHLIST</span>
          </div>
          <table class="w-full text-left t-meta">
            <thead>
              <tr class="border-b border-[var(--rule)] text-[var(--ink-quiet)] font-mono uppercase t-meta">
                <th class="pb-2 font-medium">Δείκτης / Περιουσιακό Στοιχείο</th>
                <th class="pb-2 font-medium">Τιμή</th>
                <th class="pb-2 font-medium">Μεταβολή</th>
                <th class="pb-2 font-medium">Ημ. Αναφοράς</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-[var(--rule)] font-mono t-num">
              {dash_rows_html}
            </tbody>
          </table>
        </div>

        <div class="lg:col-span-4 flex flex-col justify-between gap-4">
          <div class="card p-6 bg-[var(--paper)] border border-[var(--rule)] flex-1 flex flex-col justify-center">
            <span class="t-meta uppercase tracking-widest text-[var(--accent)] font-bold mb-1">
              Ο Αριθμός της Ημέρας
            </span>
            <div class="font-masthead text-4xl sm:text-5xl font-black text-[var(--ink)] my-2">
              {data['number_of_day'].get('number', '—')}
            </div>
            <p class="t-body-sm text-[var(--ink-body)] leading-relaxed">
              {data['number_of_day'].get('text', '')}
            </p>
          </div>
        </div>
      </div>

    </section>

    <!-- ==================== 🏠 6. Ο ΦΑΚΕΛΟΣ ΜΟΥ & REAL ESTATE RADAR ==================== -->
    <section id="portfolio" class="scroll-mt-24">
      <div class="flex items-center gap-2 mb-4 pb-2 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🎯</span> <span>Ο Φάκελός μου & Ακίνητα</span>
        </h2>
      </div>

      <!-- House Search Banner if available -->
      {house_card_html}

      <div class="space-y-3.5">
        {port_html}
      </div>
    </section>

    <!-- ==================== 🌤️ 8. ΚΑΙΡΟΣ ==================== -->
    <section id="weather" class="scroll-mt-24 my-8 sm:my-12">
      <div class="flex items-center justify-between gap-2 mb-6 pb-3 border-b-2 border-[var(--rule-strong)]">
        <h2 class="t-section flex items-center gap-2">
          <span>🌤️</span> <span>Καιρός & Μετεωρολογικές Προγνώσεις 🌡️</span>
        </h2>
        <span class="t-meta text-[var(--ink-quiet)] hidden sm:inline font-mono">Ζωντανά δεδομένα Κύπρου</span>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-12 gap-7 lg:gap-8">
        <div class="lg:col-span-7 card p-5 sm:p-6 shadow-xs">
          <div class="flex items-center justify-between mb-4 border-b border-[var(--rule)] pb-2.5">
            <h3 class="t-title font-bold text-[var(--ink)] flex items-center gap-2">
              <span>📡</span> <span>Ζωντανή Πρόγνωση Πόλεων (Open-Meteo)</span>
            </h3>
            <span class="t-meta font-mono text-[var(--up)] font-bold flex items-center gap-1">● LIVE API</span>
          </div>
          <div id="wx-live" class="grid grid-cols-2 sm:grid-cols-5 gap-3 sm:gap-4 text-center">
            <div class="p-3.5 bg-[var(--paper)] rounded-2xl border border-[var(--rule)] shadow-xs flex flex-col items-center justify-between hover:border-[var(--accent)] transition">
              <div class="t-meta text-[var(--ink-quiet)] font-semibold flex items-center gap-1.5">
                <span>🌊</span> <span>Λεμεσός</span>
              </div>
              <div class="text-3xl sm:text-4xl my-2">☀️</div>
              <div class="text-2xl font-black text-[var(--accent)] t-num">35°C</div>
              <div class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--rule)]/40 text-[var(--ink-quiet)] mt-1.5">Αίθριος</div>
            </div>
            <div class="p-3.5 bg-[var(--paper)] rounded-2xl border border-[var(--rule)] shadow-xs flex flex-col items-center justify-between hover:border-[var(--accent)] transition">
              <div class="t-meta text-[var(--ink-quiet)] font-semibold flex items-center gap-1.5">
                <span>🏛️</span> <span>Λευκωσία</span>
              </div>
              <div class="text-3xl sm:text-4xl my-2">☀️</div>
              <div class="text-2xl font-black text-[var(--accent)] t-num">38°C</div>
              <div class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--rule)]/40 text-[var(--ink-quiet)] mt-1.5">Θερμός</div>
            </div>
            <div class="p-3.5 bg-[var(--paper)] rounded-2xl border border-[var(--rule)] shadow-xs flex flex-col items-center justify-between hover:border-[var(--accent)] transition">
              <div class="t-meta text-[var(--ink-quiet)] font-semibold flex items-center gap-1.5">
                <span>✈️</span> <span>Λάρνακα</span>
              </div>
              <div class="text-3xl sm:text-4xl my-2">☀️</div>
              <div class="text-2xl font-black text-[var(--accent)] t-num">34°C</div>
              <div class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--rule)]/40 text-[var(--ink-quiet)] mt-1.5">Αίθριος</div>
            </div>
            <div class="p-3.5 bg-[var(--paper)] rounded-2xl border border-[var(--rule)] shadow-xs flex flex-col items-center justify-between hover:border-[var(--accent)] transition">
              <div class="t-meta text-[var(--ink-quiet)] font-semibold flex items-center gap-1.5">
                <span>🪨</span> <span>Πάφος</span>
              </div>
              <div class="text-3xl sm:text-4xl my-2">🌤️</div>
              <div class="text-2xl font-black text-[var(--accent)] t-num">32°C</div>
              <div class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--rule)]/40 text-[var(--ink-quiet)] mt-1.5">Αίθριος</div>
            </div>
            <div class="p-3.5 bg-[var(--paper)] rounded-2xl border border-[var(--rule)] shadow-xs flex flex-col items-center justify-between hover:border-[var(--accent)] transition col-span-2 sm:col-span-1">
              <div class="t-meta text-[var(--ink-quiet)] font-semibold flex items-center gap-1.5">
                <span>🌲</span> <span>Τρόοδος</span>
              </div>
              <div class="text-3xl sm:text-4xl my-2">⛅</div>
              <div class="text-2xl font-black text-[var(--accent)] t-num">26°C</div>
              <div class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--rule)]/40 text-[var(--ink-quiet)] mt-1.5">Ήπιος</div>
            </div>
          </div>
        </div>

        <div class="lg:col-span-5 card p-5 sm:p-6 shadow-xs flex flex-col justify-between">
          <div>
            <div class="flex items-center justify-between mb-4 border-b border-[var(--rule)] pb-2.5">
              <h3 class="t-title font-bold text-[var(--ink)] flex items-center gap-2">
                <span>📋</span> <span>Ανάλυση & Προειδοποιήσεις</span>
              </h3>
              <span class="t-meta font-mono text-[var(--ink-quiet)]">KITASWEATHER</span>
            </div>
            <div class="space-y-2.5">
              {wx_items_html}
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- ==================== 🗂️ 9 & 10. ΕΞΕΛΙΞΕΙΣ & ΠΡΟΘΕΣΜΙΕΣ ==================== -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-7 lg:gap-8 my-8 sm:my-10">
      <section id="developments" class="card p-5 sm:p-6 shadow-xs flex flex-col justify-between">
        <div>
          <h3 class="t-section mb-4 border-b border-[var(--rule)] pb-2.5 flex items-center gap-2">
            <span>🗂️</span> <span>Εξελίξεις & Συνέχεια</span>
          </h3>
          <div class="space-y-3.5">
            {dev_html}
          </div>
        </div>
      </section>

      <section id="deadlines" class="card p-5 sm:p-6 shadow-xs flex flex-col justify-between">
        <div>
          <h3 class="t-section mb-4 border-b border-[var(--rule)] pb-2.5 flex items-center gap-2">
            <span>📅</span> <span>Προθεσμίες & Δράσεις</span>
          </h3>
          <div class="space-y-3.5">
            {dead_html}
          </div>
        </div>
      </section>
    </div>

    <!-- ==================== 🔍 11. ΓΙΑ ΑΥΡΙΟ ==================== -->
    <section id="tomorrow" class="card p-6 sm:p-7 shadow-xs border-t-4 border-[var(--accent)] my-8 sm:my-10">
      <h3 class="t-section mb-4 border-b border-[var(--rule)] pb-2.5 flex items-center gap-2">
        <span>🔍</span> <span>Για Αύριο — Θέματα προς Παρακολούθηση</span>
      </h3>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        {tom_html}
      </div>
    </section>

    <!-- ==================== 12. FOOTNOTES ==================== -->
    <footer class="border-t-2 border-[var(--rule-strong)] pt-6 t-meta text-[var(--ink-quiet)] space-y-2 font-mono">
      <div class="font-bold text-[var(--ink)] uppercase">Υποσημειώσεις & Τεκμηρίωση:</div>
      <ul class="space-y-1 list-disc list-inside">
        {foot_html}
      </ul>
      <div class="pt-4 text-center t-meta text-[var(--ink-quiet)]">
        THE ORACLE SOVEREIGN © 2026 · One-Reader Executive Intelligence System
      </div>
    </footer>

  </main>

  <!-- SCRIPTS: Theme Toggle, Calculator, Weather Fetch, Instant Search -->
  <script>
    // 1. Theme Toggle
    (function () {{
      const btn = document.getElementById('themeToggle');
      const btnNav = document.getElementById('themeToggleNav');
      const updateThemeButtons = (isDark) => {{
        if (btn) btn.setAttribute('aria-pressed', isDark ? 'true' : 'false');
        if (btnNav) btnNav.setAttribute('aria-pressed', isDark ? 'true' : 'false');
      }};
      const isDarkInit = document.documentElement.classList.contains('dark');
      updateThemeButtons(isDarkInit);

      const toggleTheme = () => {{
        const darkNow = document.documentElement.classList.toggle('dark');
        localStorage.setItem('oracle-theme', darkNow ? 'dark' : 'light');
        updateThemeButtons(darkNow);
      }};

      if (btn) btn.addEventListener('click', toggleTheme);
      if (btnNav) btnNav.addEventListener('click', toggleTheme);
    }})();

    // 2. Interactive Mortgage Calculator (Enhanced with Euribor comparison)
    (function () {{
      const amountEl = document.getElementById('calcAmount');
      const yearsEl = document.getElementById('calcYears');
      const rateEl = document.getElementById('calcRate');

      const amountVal = document.getElementById('amountVal');
      const yearsVal = document.getElementById('yearsVal');
      const rateVal = document.getElementById('rateVal');
      const monthlyInstallment = document.getElementById('monthlyInstallment');
      const totalInterest = document.getElementById('totalInterest');
      const totalRepayment = document.getElementById('totalRepayment');
      const costOfCredit = document.getElementById('costOfCredit');
      const principalBar = document.getElementById('principalBar');
      const interestBar = document.getElementById('interestBar');
      const euriborPayment = document.getElementById('euriborPayment');
      const euriborDiff = document.getElementById('euriborDiff');

      const EURIBOR_3M = 2.670;  // Current Euribor 3M rate
      const SPREAD = 1.10;       // Typical Cyprus bank spread

      function calcMonthly(P, r, n) {{
        if (r > 0) return (P * r) / (1 - Math.pow(1 + r, -n));
        return P / n;
      }}

      function calculate() {{
        if (!amountEl || !yearsEl || !rateEl) return;
        const P = parseFloat(amountEl.value);
        const y = parseFloat(yearsEl.value);
        const annualRate = parseFloat(rateEl.value);

        amountVal.textContent = '€' + P.toLocaleString('el-CY');
        yearsVal.textContent = y + ' έτη';
        rateVal.textContent = annualRate.toFixed(2).replace('.', ',') + '%';

        const r = (annualRate / 100) / 12;
        const n = y * 12;

        const m = calcMonthly(P, r, n);
        const totalPay = m * n;
        const interest = totalPay - P;

        // Core results
        monthlyInstallment.textContent = '€' + Math.round(m).toLocaleString('el-CY');
        totalInterest.textContent = '€' + Math.round(interest).toLocaleString('el-CY');

        // Total repayment
        if (totalRepayment) totalRepayment.textContent = '€' + Math.round(totalPay).toLocaleString('el-CY');

        // Cost of credit %
        if (costOfCredit) {{
          const pct = ((interest / P) * 100).toFixed(1).replace('.', ',');
          costOfCredit.textContent = pct + '%';
        }}

        // Visual breakdown bar
        if (principalBar && interestBar) {{
          const principalPct = (P / totalPay) * 100;
          const interestPct = (interest / totalPay) * 100;
          principalBar.style.width = principalPct.toFixed(1) + '%';
          interestBar.style.width = interestPct.toFixed(1) + '%';
        }}

        // Euribor 3M comparison
        if (euriborPayment && euriborDiff) {{
          const euriborRate = ((EURIBOR_3M + SPREAD) / 100) / 12;
          const euriborM = calcMonthly(P, euriborRate, n);
          const diff = Math.round(euriborM) - Math.round(m);
          euriborPayment.textContent = '€' + Math.round(euriborM).toLocaleString('el-CY');
          if (diff <= 0) {{
            euriborDiff.textContent = '(−€' + Math.abs(diff).toLocaleString('el-CY') + '/μήνα)';
            euriborDiff.className = 't-meta font-mono text-[var(--up)]';
          }} else {{
            euriborDiff.textContent = '(+€' + diff.toLocaleString('el-CY') + '/μήνα)';
            euriborDiff.className = 't-meta font-mono text-[var(--down)]';
          }}
        }}
      }}

      if (amountEl && yearsEl && rateEl) {{
        amountEl.addEventListener('input', calculate);
        yearsEl.addEventListener('input', calculate);
        rateEl.addEventListener('input', calculate);
        calculate();
      }}
    }})();

    // 3. Open-Meteo Live Client Weather Fetch
    (function () {{
      const cities = [
        {{ name: 'Λεμεσός', icon: '🌊', lat: 34.68, lon: 33.04 }},
        {{ name: 'Λευκωσία', icon: '🏛️', lat: 35.17, lon: 33.36 }},
        {{ name: 'Λάρνακα', icon: '✈️', lat: 34.92, lon: 33.63 }},
        {{ name: 'Πάφος', icon: '🪨', lat: 34.77, lon: 32.42 }},
        {{ name: 'Τρόοδος', icon: '🌲', lat: 34.92, lon: 32.88 }}
      ];

      const wmoText = {{
        0: 'Αίθριος', 1: 'Κυρίως αίθριος', 2: 'Μερικώς νεφελώδης', 3: 'Συννεφιασμένος',
        45: 'Ομίχλη', 51: 'Ψεκάδες', 61: 'Ασθενής βροχή', 63: 'Βροχή', 65: 'Ισχυρή βροχή',
        80: 'Μπόρες', 95: 'Καταιγίδα'
      }};

      const wmoIcons = {{
        0: '☀️', 1: '🌤️', 2: '⛅', 3: '☁️',
        45: '🌫️', 51: '🌦️', 61: '🌧️', 63: '🌧️', 65: '⛈️',
        80: '🌦️', 95: '⛈️'
      }};

      async function fetchWeather() {{
        try {{
          const container = document.getElementById('wx-live');
          if (!container) return;
          const fetches = cities.map(c =>
            fetch(`https://api.open-meteo.com/v1/forecast?latitude=${{c.lat}}&longitude=${{c.lon}}&current=temperature_2m,weather_code&timezone=auto`)
              .then(r => r.json())
              .then(d => ({{ name: c.name, cityIcon: c.icon, temp: Math.round(d.current.temperature_2m), code: d.current.weather_code }}))
              .catch(() => null)
          );

          const results = await Promise.all(fetches);
          if (results.some(r => r !== null)) {{
            container.innerHTML = results.map(r => {{
              if (!r) return '';
              const desc = wmoText[r.code] || 'Ήπιος';
              const icon = wmoIcons[r.code] || '🌤️';
              return `
                <div class="p-3.5 bg-[var(--paper)] rounded-2xl border border-[var(--rule)] shadow-xs flex flex-col items-center justify-between hover:border-[var(--accent)] transition">
                  <div class="t-meta text-[var(--ink-quiet)] font-semibold flex items-center gap-1.5">
                    <span>${{r.cityIcon}}</span> <span>${{r.name}}</span>
                  </div>
                  <div class="text-3xl sm:text-4xl my-2">${{icon}}</div>
                  <div class="text-2xl font-black text-[var(--accent)] t-num">${{r.temp}}°C</div>
                  <div class="text-[11px] font-mono px-2 py-0.5 rounded-full bg-[var(--rule)]/40 text-[var(--ink-quiet)] mt-1.5">${{desc}}</div>
                </div>
              `;
            }}).join('');
          }}
        }} catch (e) {{
          console.warn('Open-Meteo live weather fetch fallback maintained.', e);
        }}
      }}
      fetchWeather();
    }})();

    // 4. Instant Archive Search (Asynchronous Fetch with client-side cache)
    (function () {{
      const input = document.getElementById('archiveSearch');
      const resultsContainer = document.getElementById('searchResults');
      if (!input || !resultsContainer) return;

      let searchData = [];
      let loadingPromise = null;

      function getSearchData() {{
        if (!loadingPromise) {{
          loadingPromise = fetch('search-index.json').catch(() => fetch('../search-index.json'))
            .then(r => r.json())
            .then(d => {{ searchData = d; return d; }})
            .catch(err => {{
              console.warn('Could not load search index asynchronously:', err);
              return [];
            }});
        }}
        return loadingPromise;
      }}

      input.addEventListener('focus', getSearchData);

      input.addEventListener('input', async (e) => {{
        const q = e.target.value.trim().toLowerCase();
        if (q.length < 2) {{
          resultsContainer.classList.add('hidden');
          resultsContainer.innerHTML = '';
          return;
        }}

        const data = searchData.length ? searchData : await getSearchData();
        const matches = data.filter(item => 
          item.title.toLowerCase().includes(q) || 
          item.snippet.toLowerCase().includes(q) ||
          item.section.toLowerCase().includes(q)
        ).slice(0, 8);

        if (matches.length === 0) {{
          resultsContainer.innerHTML = '<div class="p-3 text-center t-meta text-[var(--ink-quiet)]">Δεν βρέθηκαν αποτελέσματα.</div>';
          resultsContainer.classList.remove('hidden');
          return;
        }}

        resultsContainer.innerHTML = matches.map(m => `
          <a href="${{m.url}}" class="block p-2.5 rounded hover:bg-[var(--paper)] transition border-b border-[var(--rule)] last:border-0">
            <div class="flex items-center justify-between text-[10px] font-mono text-[var(--ink-quiet)] mb-1">
              <span>${{m.section}}</span>
              <span>📅 ${{m.date}}</span>
            </div>
            <div class="font-bold text-[var(--ink)] leading-snug mb-1">${{m.title}}</div>
            <div class="t-meta text-[var(--ink-quiet)] line-clamp-2">${{m.snippet}}</div>
          </a>
        `).join('');

        resultsContainer.classList.remove('hidden');
      }});

      document.addEventListener('click', (e) => {{
        if (!input.contains(e.target) && !resultsContainer.contains(e.target)) {{
          resultsContainer.classList.add('hidden');
        }}
      }});
    }})();

    // 5. 60-Second Executive Scan Mode Toggle
    (function () {{
      const scanBtn = document.getElementById('scanModeToggle');
      if (!scanBtn) return;

      const savedMode = localStorage.getItem('oracle-scan-mode') === '1';
      if (savedMode) {{
        document.body.classList.add('scan-mode');
        scanBtn.innerHTML = '<span>📖</span> <span class="hidden md:inline">Πλήρης Έκδοση</span>';
        scanBtn.classList.add('bg-[var(--accent)]', 'text-white');
      }}

      scanBtn.addEventListener('click', () => {{
        const isScan = document.body.classList.toggle('scan-mode');
        localStorage.setItem('oracle-scan-mode', isScan ? '1' : '0');
        if (isScan) {{
          scanBtn.innerHTML = '<span>📖</span> <span class="hidden md:inline">Πλήρης Έκδοση</span>';
          scanBtn.classList.add('bg-[var(--accent)]', 'text-white');
        }} else {{
          scanBtn.innerHTML = '<span>⚡</span> <span class="hidden md:inline">60″ Scan</span>';
          scanBtn.classList.remove('bg-[var(--accent)]', 'text-white');
        }}
      }});
    }})();

    // 6. Sovereign Executive Audio Briefing (SpeechSynthesis)
    (function () {{
      const playBtn = document.getElementById('audioPlayBtn');
      const speedBtn = document.getElementById('audioSpeedBtn');
      const stopBtn = document.getElementById('audioStopBtn');
      const statusText = document.getElementById('audioStatusText');
      const badge = document.getElementById('audioLiveBadge');

      if (!playBtn || !('speechSynthesis' in window)) return;

      const speeds = [1.0, 1.25, 1.5];
      let speedIdx = 0;
      let isSpeaking = false;

      function getBriefingText() {{
        const titleEl = document.querySelector('#top-story h3');
        const title = titleEl ? titleEl.innerText : '';
        const bodyEl = document.querySelector('#top-story p');
        const body = bodyEl ? bodyEl.innerText : '';
        const deadlines = Array.from(document.querySelectorAll('#deadlines li')).slice(0, 3).map(li => li.innerText.split('—')[0]).join('. ');

        return `The Oracle Sovereign. Ημερήσιο εμπιστευτικό briefing. Πρώτο θέμα: ${{title}}. ${{body.slice(0, 320)}}. Σημαντικές προθεσμίες και ενέργειες: ${{deadlines}}. Τέλος συνοπτικής ενημέρωσης.`;
      }}

      function startPlayback() {{
        window.speechSynthesis.cancel();
        const text = getBriefingText();
        const utter = new SpeechSynthesisUtterance(text);
        utter.lang = 'el-GR';
        utter.rate = speeds[speedIdx];

        const voices = window.speechSynthesis.getVoices();
        const elVoice = voices.find(v => v.lang.startsWith('el') || v.lang.includes('GR'));
        if (elVoice) utter.voice = elVoice;

        utter.onstart = () => {{
          isSpeaking = true;
          playBtn.textContent = '⏸';
          if (badge) badge.classList.remove('hidden');
          if (stopBtn) stopBtn.classList.remove('hidden');
          statusText.textContent = `Φωνητική ανάγνωση σε εξέλιξη (${{speeds[speedIdx]}}x)...`;
        }};

        utter.onend = () => {{
          isSpeaking = false;
          playBtn.textContent = '▶';
          if (badge) badge.classList.add('hidden');
          if (stopBtn) stopBtn.classList.add('hidden');
          statusText.textContent = 'Ολοκληρώθηκε η ηχητική σύνοψη.';
        }};

        utter.onerror = () => {{
          isSpeaking = false;
          playBtn.textContent = '▶';
          if (badge) badge.classList.add('hidden');
          if (stopBtn) stopBtn.classList.add('hidden');
          statusText.textContent = 'Πατήστε Play για φωνητική ανάγνωση.';
        }};

        window.speechSynthesis.speak(utter);
      }}

      playBtn.addEventListener('click', () => {{
        if (isSpeaking) {{
          if (window.speechSynthesis.paused) {{
            window.speechSynthesis.resume();
            playBtn.textContent = '⏸';
            statusText.textContent = `Συνέχιση ανάγνωσης (${{speeds[speedIdx]}}x)...`;
          }} else {{
            window.speechSynthesis.pause();
            playBtn.textContent = '▶';
            statusText.textContent = 'Σε παύση.';
          }}
        }} else {{
          startPlayback();
        }}
      }});

      if (stopBtn) {{
        stopBtn.addEventListener('click', () => {{
          window.speechSynthesis.cancel();
          isSpeaking = false;
          playBtn.textContent = '▶';
          if (badge) badge.classList.add('hidden');
          stopBtn.classList.add('hidden');
          statusText.textContent = 'Πατήστε Play για φωνητική ανάγνωση.';
        }});
      }}

      if (speedBtn) {{
        speedBtn.addEventListener('click', () => {{
          speedIdx = (speedIdx + 1) % speeds.length;
          speedBtn.textContent = `${{speeds[speedIdx]}}x`;
          if (isSpeaking) startPlayback();
        }});
      }}
    }})();

    // 7. Smart Sticky Navigation Header (Auto-hide on scroll down, reveal on scroll up)
    (function () {{
      const nav = document.getElementById('mainNav');
      if (!nav) return;

      let lastScrollY = window.pageYOffset || document.documentElement.scrollTop;
      let ticking = false;
      const threshold = 8;
      const minScrollToHide = 100;

      function onScroll() {{
        const currentScrollY = window.pageYOffset || document.documentElement.scrollTop;

        // Near top of the page: always keep visible
        if (currentScrollY <= minScrollToHide) {{
          nav.classList.remove('nav-hidden');
          lastScrollY = currentScrollY;
          ticking = false;
          return;
        }}

        // Prevent triggering on iOS rubber-band overscroll at bottom of document
        const maxScroll = document.documentElement.scrollHeight - window.innerHeight;
        if (currentScrollY >= maxScroll - 20) {{
          ticking = false;
          return;
        }}

        const delta = currentScrollY - lastScrollY;

        if (Math.abs(delta) > threshold) {{
          if (delta > 0) {{
            // Scrolling down -> hide nav
            nav.classList.add('nav-hidden');
            const sr = document.getElementById('searchResults');
            if (sr && !sr.classList.contains('hidden')) sr.classList.add('hidden');
          }} else {{
            // Scrolling up -> show nav
            nav.classList.remove('nav-hidden');
          }}
          lastScrollY = currentScrollY;
        }}
        ticking = false;
      }}

      window.addEventListener('scroll', function () {{
        if (!ticking) {{
          window.requestAnimationFrame(onScroll);
          ticking = true;
        }}
      }}, {{ passive: true }});
    }})();

    // 8. 24/7 Global Market Clocks & Live Trading Badges
    (function () {{
      function updateClocks() {{
        const now = new Date();
        
        function formatTZ(tz) {{
          try {{
            return new Intl.DateTimeFormat('el-GR', {{
              timeZone: tz,
              hour: '2-digit',
              minute: '2-digit',
              hour12: false
            }}).format(now);
          }} catch (e) {{
            return '--:--';
          }}
        }}

        function getMarketStatus(tz, openH, openM, closeH, closeM) {{
          try {{
            const parts = new Intl.DateTimeFormat('en-US', {{
              timeZone: tz,
              weekday: 'short',
              hour: 'numeric',
              minute: 'numeric',
              hour12: false
            }}).formatToParts(now);
            
            const p = {{}};
            parts.forEach(x => p[x.type] = x.value);
            const day = p.weekday;
            const h = parseInt(p.hour, 10);
            const m = parseInt(p.minute, 10);
            
            if (day === 'Sat' || day === 'Sun') return {{ open: false, label: 'CLOSED' }};
            
            const currentMins = h * 60 + m;
            const openMins = openH * 60 + openM;
            const closeMins = closeH * 60 + closeM;
            
            const isOpen = currentMins >= openMins && currentMins < closeMins;
            return {{ open: isOpen, label: isOpen ? 'OPEN' : 'CLOSED' }};
          }} catch (e) {{
            return {{ open: false, label: '--' }};
          }}
        }}

        const cyEl = document.getElementById('clockCY');
        const lonEl = document.getElementById('clockLON');
        const nycEl = document.getElementById('clockNYC');
        const tyoEl = document.getElementById('clockTYO');

        if (cyEl) cyEl.textContent = formatTZ('Asia/Nicosia');
        if (lonEl) lonEl.textContent = formatTZ('Europe/London');
        if (nycEl) nycEl.textContent = formatTZ('America/New_York');
        if (tyoEl) tyoEl.textContent = formatTZ('Asia/Tokyo');

        // London: LSE 08:00 - 16:30
        const lonSt = getMarketStatus('Europe/London', 8, 0, 16, 30);
        const lonStEl = document.getElementById('statusLON');
        if (lonStEl) {{
          lonStEl.textContent = lonSt.label;
          lonStEl.className = 'text-[9px] px-1 py-0.2 rounded font-bold ' + (lonSt.open ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-neutral-500/20 text-neutral-400');
        }}

        // NYC: NYSE 09:30 - 16:00
        const nycSt = getMarketStatus('America/New_York', 9, 30, 16, 0);
        const nycStEl = document.getElementById('statusNYC');
        if (nycStEl) {{
          nycStEl.textContent = nycSt.label;
          nycStEl.className = 'text-[9px] px-1 py-0.2 rounded font-bold ' + (nycSt.open ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-neutral-500/20 text-neutral-400');
        }}

        // Tokyo: TSE 09:00 - 15:30
        const tyoSt = getMarketStatus('Asia/Tokyo', 9, 0, 15, 30);
        const tyoStEl = document.getElementById('statusTYO');
        if (tyoStEl) {{
          tyoStEl.textContent = tyoSt.label;
          tyoStEl.className = 'text-[9px] px-1 py-0.2 rounded font-bold ' + (tyoSt.open ? 'bg-emerald-500/20 text-emerald-600 dark:text-emerald-400' : 'bg-neutral-500/20 text-neutral-400');
        }}
      }}

      updateClocks();
      setInterval(updateClocks, 1000);
    }})();

    // 9. 24/7 Live Wire Feed Ticker & Drawer Modal
    (function () {{
      const tickerEl = document.getElementById('liveWireTicker');
      const drawerModal = document.getElementById('wireDrawerModal');
      const drawerContent = document.getElementById('wireDrawerContent');
      const openBtn = document.getElementById('openWireDrawerBtn');
      const openBtnNav = document.getElementById('openWireDrawerBtnNav');
      const closeBtn = document.getElementById('closeWireDrawerBtn');

      let wireItems = [];
      let activeIndex = 0;
      let rotatorInterval = null;

      function fetchWire() {{
        return fetch('live-wire.json')
          .catch(() => fetch('../live-wire.json'))
          .then(r => r.json())
          .then(data => {{
            wireItems = data;
            renderTicker();
            renderDrawer();
            if (!rotatorInterval && wireItems.length > 1) {{
              rotatorInterval = setInterval(rotateTicker, 6000);
            }}
          }})
          .catch(e => {{
            console.warn('Could not load live-wire:', e);
          }});
      }}

      function renderTicker() {{
        if (!tickerEl || !wireItems.length) return;
        const item = wireItems[activeIndex];
        const breakBadge = item.is_breaking ? '<span class="px-1.5 py-0.2 rounded bg-red-600 text-white font-bold text-[10px] mr-1.5 animate-pulse">ΕΚΤΑΚΤΟ</span>' : '';
        const timeBadge = `<span class="font-mono text-[var(--ink-quiet)] mr-2">[${{item.time_str || ''}}]</span>`;
        const srcBadge = `<span class="text-[var(--accent)] font-semibold ml-2">(${{item.source}})</span>`;
        
        tickerEl.innerHTML = `<div class="truncate transition-opacity duration-300 opacity-100">${{breakBadge}}${{timeBadge}}<a href="${{item.link}}" target="_blank" class="hover:underline text-[var(--ink)] font-medium">${{item.title}}</a>${{srcBadge}}</div>`;
      }}

      function rotateTicker() {{
        if (!tickerEl || !wireItems.length) return;
        activeIndex = (activeIndex + 1) % Math.min(wireItems.length, 15);
        renderTicker();
      }}

      function renderDrawer() {{
        if (!drawerContent || !wireItems.length) return;
        drawerContent.innerHTML = wireItems.map(item => {{
          const isB = item.is_breaking;
          const borderCls = isB ? 'border-red-500 bg-red-500/5' : 'border-[var(--rule)] bg-[var(--paper)]';
          const breakTag = isB ? '<span class="px-1.5 py-0.2 rounded bg-red-600 text-white text-[10px] font-bold mr-1.5">ΕΚΤΑΚΤΟ</span>' : '';
          return `
            <div class="p-3 rounded-lg border ${{borderCls}} space-y-1 text-xs">
              <div class="flex items-center justify-between text-[10px] font-mono text-[var(--ink-quiet)]">
                <span>${{item.source}} · ${{item.time_str || ''}}</span>
                ${{isB ? '<span class="text-red-500 font-bold uppercase">⚡ Flash</span>' : ''}}
              </div>
              <a href="${{item.link}}" target="_blank" class="font-bold text-[var(--ink)] hover:text-[var(--accent)] block leading-snug">
                ${{breakTag}}${{item.title}}
              </a>
              ${{item.snippet ? `<p class="text-[var(--ink-body)] line-clamp-2 text-[11px]">${{item.snippet}}</p>` : ''}}
            </div>
          `;
        }}).join('');
      }}

      function toggleDrawer(open) {{
        if (!drawerModal) return;
        if (open) {{
          drawerModal.classList.remove('hidden');
          document.body.style.overflow = 'hidden';
        }} else {{
          drawerModal.classList.add('hidden');
          document.body.style.overflow = '';
        }}
      }}

      if (openBtn) openBtn.addEventListener('click', () => toggleDrawer(true));
      if (openBtnNav) openBtnNav.addEventListener('click', () => toggleDrawer(true));
      if (closeBtn) closeBtn.addEventListener('click', () => toggleDrawer(false));
      if (drawerModal) {{
        drawerModal.addEventListener('click', (e) => {{
          if (e.target === drawerModal) toggleDrawer(false);
        }});
      }}

      fetchWire();
    }})();
  </script>

  {wire_drawer_modal_html}

</body>
</html>
'''
    return html



def render_html(data, house_stats, search_index, is_subfolder=False, date_slug=None):
    current_edition = data.get('edition') or 'morning'
    title_upper = (data.get('title') or '').upper()
    if 'ΑΠΟΓΕΥΜΑΤΙΝΗ' in title_upper or 'EVENING' in title_upper or current_edition == 'evening':
        current_edition = 'evening'
    elif 'ΜΕΣΗΜΒΡΙΝΟΣ' in title_upper or 'MIDDAY' in title_upper or current_edition == 'midday':
        current_edition = 'midday'
    else:
        current_edition = 'morning'

    if current_edition == 'evening':
        return render_evening_html(data, house_stats, search_index, is_subfolder=is_subfolder, date_slug=date_slug)
    elif current_edition == 'midday':
        return render_midday_html(data, house_stats, search_index, is_subfolder=is_subfolder, date_slug=date_slug)
    else:
        return render_morning_html(data, house_stats, search_index, is_subfolder=is_subfolder, date_slug=date_slug)

def main():
    target_md = None
    if len(sys.argv) > 1:
        target_md = os.path.abspath(sys.argv[1])
    else:
        target_md = find_latest_briefing()

    if not os.path.exists(target_md):
        print(f"Error: Target briefing markdown file does not exist: {target_md}")
        sys.exit(1)

    print(f"Reading briefing: {target_md}")
    with open(target_md, 'r', encoding='utf-8', errors='replace') as f:
        content = f.read()

    filename = os.path.basename(target_md)
    m_date = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    date_slug = m_date.group(1) if m_date else datetime.now().strftime('%Y-%m-%d')

    edition_suffix = "-midday" if "-midday" in filename else ("-evening" if "-evening" in filename else "")
    edition_slug = f"{date_slug}{edition_suffix}"

    data = parse_markdown(content, filename=filename)
    house_stats = get_latest_house_search()
    if house_stats:
        print(f"Linked House Search from: {house_stats['date']} ({house_stats['unique_properties']} properties)")

    print("Building cross-edition search index...")
    search_index = build_search_index()
    print(f"Indexed {len(search_index)} items across editions.")

    html_root = render_html(data, house_stats, search_index, is_subfolder=False, date_slug=date_slug)
    html_sub = render_html(data, house_stats, search_index, is_subfolder=True, date_slug=date_slug)

    os.makedirs(BRIEFINGS_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(DOCS_BRIEFINGS_DIR, exist_ok=True)

    briefing_html = os.path.join(BRIEFINGS_DIR, f'oracle-briefing-{edition_slug}.html')
    docs_index = os.path.join(DOCS_DIR, 'index.html')
    docs_briefing_html = os.path.join(DOCS_BRIEFINGS_DIR, f'{edition_slug}.html')
    docs_briefing_md = os.path.join(DOCS_BRIEFINGS_DIR, f'{edition_slug}.md')

    with open(docs_index, 'w', encoding='utf-8') as f:
        f.write(html_root)
    print(f"Generated root index: {docs_index}")

    for path in [briefing_html, docs_briefing_html]:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_sub)
        print(f"Generated subfolder: {path}")

    shutil.copy2(target_md, docs_briefing_md)
    print(f"Copied markdown to docs: {docs_briefing_md}")

    # Copy live-wire.json to docs/
    live_wire_src = os.path.join(BASE_DIR, 'scripts', 'live-wire.json')
    if os.path.exists(live_wire_src):
        shutil.copy2(live_wire_src, os.path.join(DOCS_DIR, 'live-wire.json'))

    print("\nSUCCESS! The Oracle Sovereign web portal and archives have been built with full news-first layout and imagery.")


if __name__ == '__main__':
    main()
