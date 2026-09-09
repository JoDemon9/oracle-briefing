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
    'shipwreck': 'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=800&q=80',
    'politics': 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&q=80',
    'housing': 'https://images.unsplash.com/photo-1560518883-ce09059eeffa?w=800&q=80',
    'diplomacy': 'https://images.unsplash.com/photo-1541872703-74c5e44368f9?w=800&q=80',
    'germany': 'https://images.unsplash.com/photo-1529107386315-e1a2ed48a620?w=800&q=80',
    'volcano': 'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=800&q=80',
    'aviation': 'https://images.unsplash.com/photo-1436491865332-7a61a109cc05?w=800&q=80',
    'justice': 'https://images.unsplash.com/photo-1589829545856-d10d557cf95f?w=800&q=80',
    'general': 'https://images.unsplash.com/photo-1504711434969-e33886168f5c?w=800&q=80'
}


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
    if url in cache and cache[url].get('image'):
        return cache[url]['image'], cache[url].get('category', default_category)

    # Keyword fallback selection
    t_lower = (title + ' ' + url).lower()
    fallback = TOPIC_FALLBACKS['general']
    category = default_category

    if any(k in t_lower for k in ['σχολ', 'μαθητ', 'υποδομ', 'ύψωνα', 'παιδεία']):
        fallback = TOPIC_FALLBACKS['school']
        category = 'ΠΑΙΔΕΙΑ & ΥΠΟΔΟΜΕΣ'
    elif any(k in t_lower for k in ['απασχόληση', 'εργασί', 'cystat', 'μισθ']):
        fallback = TOPIC_FALLBACKS['employment']
        category = 'ΟΙΚΟΝΟΜΙΑ'
    elif any(k in t_lower for k in ['ναυάγ', 'νεκροί', 'σκάφος', 'κερύνει']):
        fallback = TOPIC_FALLBACKS['shipwreck']
        category = 'ΕΚΤΑΚΤΟ'
    elif any(k in t_lower for k in ['λιμουζίν', 'βουλ', 'χριστοδουλίδ', 'πολιτικ']):
        fallback = TOPIC_FALLBACKS['politics']
        category = 'ΠΟΛΙΤΙΚΗ'
    elif any(k in t_lower for k in ['ενοίκι', 'στέγη', 'τεπακ', 'ακίνητ', 'λεμεσ']):
        fallback = TOPIC_FALLBACKS['housing']
        category = 'Ο ΦΑΚΕΛΟΣ ΜΟΥ'
    elif any(k in t_lower for k in ['zelenskyy', 'putin', 'ουκραν', 'κίεβο', 'διπλωματ']):
        fallback = TOPIC_FALLBACKS['diplomacy']
        category = 'ΔΙΠΛΩΜΑΤΙΑ'
    elif any(k in t_lower for k in ['afd', 'γερμανί', 'merz', 'σαξονία']):
        fallback = TOPIC_FALLBACKS['germany']
        category = 'ΓΕΡΜΑΝΙΑ'
    elif any(k in t_lower for k in ['krakatau', 'ηφαίστει', 'ινδονησία']):
        fallback = TOPIC_FALLBACKS['volcano']
        category = 'ΑΣΙΑ'
    elif any(k in t_lower for k in ['amazon', 'boeing', 'μαϊάμι', 'αεροπορικ']):
        fallback = TOPIC_FALLBACKS['aviation']
        category = 'ΗΠΑ'
    elif any(k in t_lower for k in ['icj', 'χάγη', 'δικαστήρι', 'ισραήλ', 'γενοκτον']):
        fallback = TOPIC_FALLBACKS['justice']
        category = 'ΔΙΚΑΙΟΣΥΝΗ'
    elif any(k in t_lower for k in ['dbrs', 'αξιολόγηση', 'οίκος', 'δημοσιονομ']):
        fallback = TOPIC_FALLBACKS['economy']
        category = 'ΟΙΚΟΝΟΜΙΑ & ΑΞΙΟΧΡΕΟ'

    # Try fetching og:image live with short timeout
    og_img = None
    if url.startswith('http'):
        try:
            req = urllib.request.Request(
                url,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
            )
            with urllib.request.urlopen(req, timeout=3.0, context=SSL_CTX) as resp:
                html_txt = resp.read().decode('utf-8', errors='ignore')
                m = re.search(r'<meta[^>]+(?:property|name)=[\'"]og:image[\'"][^>]+content=[\'"]([^\'"]+)[\'"]', html_txt, re.I)
                if not m:
                    m = re.search(r'<meta[^>]+content=[\'"]([^\'"]+)[\'"][^>]+(?:property|name)=[\'"]og:image[\'"]', html_txt, re.I)
                if m:
                    candidate = m.group(1).strip()
                    if candidate.startswith('http'):
                        og_img = candidate
        except Exception:
            pass

    final_img = og_img if og_img else fallback
    cache[url] = {'image': final_img, 'category': category}
    save_image_cache(cache)
    return final_img, category


def find_latest_briefing():
    pattern = os.path.join(BRIEFINGS_DIR, 'oracle-briefing-*.md')
    files = sorted(glob.glob(pattern))
    if not files:
        raise FileNotFoundError(f"No briefing files found in {BRIEFINGS_DIR}")
    return files[-1]


def parse_markdown(md_content):
    data = {
        'title': 'THE ORACLE SOVEREIGN',
        'date_str': '',
        'time_str': '',
        'read_time': "7'",
        'top_story': {},
        'dashboard': [],
        'number_of_day': {},
        'rates': {
            'euribor': [],
            'ecb_rate': '3,75%',
            'next_ecb': '10 Σεπτεμβρίου 2026',
            'cbc_mortgage_rate': '3,78%',
            'example_payment': '€1.032',
            'example_change': '€0 (αμετάβλητο)',
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
        'weather': {},
        'developments': [],
        'portfolio': [],
        'deadlines': [],
        'tomorrow': [],
        'footnotes': []
    }

    lines = md_content.splitlines()
    for line in lines[:6]:
        line_clean = line.strip()
        m_title = re.search(r'#\s+🏛️\s+THE ORACLE SOVEREIGN\s*[—–-]\s*(.+)', line_clean)
        if m_title:
            data['date_str'] = m_title.group(1).strip()
        m_time = re.search(r'\*\*(\d{1,2}:\d{2})\s*ώρα Κύπρου', line_clean)
        if m_time:
            data['time_str'] = m_time.group(1).strip()
        m_read = re.search(r'χρόνος ανάγνωσης\s*~?(\d+)', line_clean)
        if m_read:
            data['read_time'] = f"{m_read.group(1)}'"

    sections = re.split(r'\n##\s+', md_content)
    for sec in sections[1:]:
        sec_lines = sec.strip().splitlines()
        if not sec_lines:
            continue
        sec_header = sec_lines[0].strip()

        # TOP STORY
        if 'ΤΟ ΘΕΜΑ ΤΗΣ ΗΜΕΡΑΣ' in sec_header:
            top_data = {'title': '', 'body': '', 'antilogos': '', 'sources': []}
            h3_match = re.search(r'###\s+(.+)', sec)
            if h3_match:
                top_data['title'] = h3_match.group(1).strip()

            anti_match = re.search(r'\*\*Αντίλογος:\*\*\s*(.+?)(?=\n\n|\n\*\*Πηγές:|\Z)', sec, re.DOTALL)
            if anti_match:
                top_data['antilogos'] = anti_match.group(1).strip()

            src_match = re.search(r'\*\*Πηγές:\*\*\s*(.+)', sec)
            if src_match:
                sources_raw = re.findall(r'\[(.*?)\]\((.*?)\)', src_match.group(1))
                top_data['sources'] = [{'name': name, 'url': url} for name, url in sources_raw]

            body_parts = []
            capture = False
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

        # DASHBOARD
        elif 'DASHBOARD' in sec_header:
            table_lines = [l.strip() for l in sec_lines if l.strip().startswith('|') and not '---' in l]
            for row in table_lines:
                cols = [c.strip() for c in row.split('|')[1:-1]]
                if len(cols) >= 4 and not cols[0].startswith('Δείκτης') and not ':---' in cols[0]:
                    asset_name = re.sub(r'\*\*', '', cols[0]).strip()
                    price = cols[1].strip()
                    change = cols[2].strip()
                    date_ref = cols[3].strip()
                    data['dashboard'].append({
                        'asset': asset_name,
                        'price': price,
                        'change': change,
                        'date_ref': date_ref
                    })
            nod_match = re.search(r'\*\*Ο αριθμός της ημέρας:\*\*\s*\*\*([^*]+)\*\*\s*[—–-]\s*(.+)', sec)
            if nod_match:
                data['number_of_day'] = {
                    'number': nod_match.group(1).strip(),
                    'text': nod_match.group(2).strip()
                }

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
            ecb_m = re.search(r'Επιτόκιο ΕΚΤ.*?:\s*([\d,]+%?).*?Επόμενη συνεδρίαση:\s*([^\n·]+)', sec)
            if ecb_m:
                data['rates']['ecb_rate'] = ecb_m.group(1).strip()
                data['rates']['next_ecb'] = ecb_m.group(2).strip()
            cbc_m = re.search(r'Μέσο επιτόκιο νέων στεγαστικών.*?:.*?([\d,]+%).*?\((.*?)\)', sec)
            if cbc_m:
                data['rates']['cbc_mortgage_rate'] = cbc_m.group(1).strip()

            calc_m = re.search(r'Ενδεικτική δόση.*?→\s*\*\*([^*]+)\*\*', sec)
            if calc_m:
                data['rates']['example_payment'] = calc_m.group(1).strip()

            srcs_m = re.search(r'Πηγές:\s*(.+)', sec)
            if srcs_m:
                sources_raw = re.findall(r'\[(.*?)\]\((.*?)\)', srcs_m.group(1))
                data['rates']['sources'] = [{'name': name, 'url': url} for name, url in sources_raw]

        # CYPRUS
        elif 'ΚΥΠΡΟΣ' in sec_header:
            items_raw = re.split(r'\n###\s+', '\n' + sec)
            for raw_item in items_raw[1:]:
                lines_i = raw_item.strip().splitlines()
                if not lines_i:
                    continue
                title_line = lines_i[0].strip()
                tag_match = re.findall(r'\[([^\]]+)\]', title_line)
                tags = [t for t in tag_match if t not in ['Ο Φάκελός μου']]
                tag = tags[-1] if tags else 'Μονή πηγή'

                is_portfolio = '[Ο Φάκελός μου]' in title_line or 'Ο Φάκελός μου' in title_line
                clean_title = re.sub(r'^\d+\.\s*', '', title_line)
                clean_title = clean_title.replace('[Ο Φάκελός μου]', '').replace(f'[{tag}]', '').strip()

                why_match = re.search(r'\*\*Γιατί με αφορά:\*\*\s*(.+)', raw_item)
                why_text = why_match.group(1).strip() if why_match else ''

                src_match = re.search(r'\*\*(?:Πηγή|Πηγές):\*\*\s*(.+)', raw_item)
                source = None
                if src_match:
                    src_parsed = re.findall(r'\[(.*?)\]\((.*?)\)', src_match.group(1))
                    if src_parsed:
                        source = {'name': src_parsed[0][0], 'url': src_parsed[0][1]}

                body_lines = []
                for bl in lines_i[1:]:
                    bl_c = bl.strip()
                    if bl_c.startswith('**Γιατί με αφορά:') or bl_c.startswith('**Βάθος:') or bl_c.startswith('**Πηγή:') or bl_c.startswith('**Πηγές:'):
                        break
                    if bl_c.startswith('* **') or bl_c.startswith('- **') or bl_c.startswith('• **'):
                        break
                    if bl_c and not bl_c.startswith('---'):
                        body_lines.append(bl_c)
                body_text = ' '.join(body_lines)

                depth = {}
                bg_m = re.search(r'\*\*Το υπόβαθρο:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                pr_m = re.search(r'\*\*Τι σημαίνει πρακτικά:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                nw_m = re.search(r'\*\*Τι να παρακολουθήσω:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                an_m = re.search(r'\*\*Αντίλογος:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                if bg_m and bg_m.group(1).strip():
                    depth['background'] = bg_m.group(1).strip().replace('\n', ' ')
                if pr_m and pr_m.group(1).strip():
                    depth['practical'] = pr_m.group(1).strip().replace('\n', ' ')
                if nw_m and nw_m.group(1).strip():
                    depth['next_watch'] = nw_m.group(1).strip().replace('\n', ' ')
                if an_m and an_m.group(1).strip():
                    depth['antilogos'] = an_m.group(1).strip().replace('\n', ' ')

                data['cyprus'].append({
                    'title': clean_title,
                    'tag': tag,
                    'is_portfolio': is_portfolio,
                    'body': body_text,
                    'why': why_text,
                    'source': source,
                    'depth': depth
                })

        # WORLD
        elif 'ΔΙΕΘΝΗ' in sec_header:
            items_raw = re.split(r'\n###\s+', '\n' + sec)
            for raw_item in items_raw[1:]:
                lines_i = raw_item.strip().splitlines()
                if not lines_i:
                    continue
                title_line = lines_i[0].strip()
                tag_match = re.findall(r'\[([^\]]+)\]', title_line)
                tag = tag_match[-1] if tag_match else 'Μονή πηγή'
                clean_title = re.sub(r'^\d+\.\s*', '', title_line).replace(f'[{tag}]', '').strip()

                src_match = re.search(r'\*\*(?:Πηγή|Πηγές):\*\*\s*(.+)', raw_item)
                source = None
                if src_match:
                    src_parsed = re.findall(r'\[(.*?)\]\((.*?)\)', src_match.group(1))
                    if src_parsed:
                        source = {'name': src_parsed[0][0], 'url': src_parsed[0][1]}

                body_lines = []
                for bl in lines_i[1:]:
                    bl_c = bl.strip()
                    if bl_c.startswith('**Βάθος:') or bl_c.startswith('**Πηγή:') or bl_c.startswith('**Πηγές:'):
                        break
                    if bl_c.startswith('* **') or bl_c.startswith('- **') or bl_c.startswith('• **'):
                        break
                    if bl_c and not bl_c.startswith('---'):
                        body_lines.append(bl_c)
                body_text = ' '.join(body_lines)

                depth = {}
                bg_m = re.search(r'\*\*Το υπόβαθρο:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                pr_m = re.search(r'\*\*Τι σημαίνει πρακτικά:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                nw_m = re.search(r'\*\*Τι να παρακολουθήσω:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                an_m = re.search(r'\*\*Αντίλογος:\*\*\s*(.+?)(?=\n\s*[*•-]\s*\*\*|\n\*\*|\Z)', raw_item, re.DOTALL)
                if bg_m and bg_m.group(1).strip():
                    depth['background'] = bg_m.group(1).strip().replace('\n', ' ')
                if pr_m and pr_m.group(1).strip():
                    depth['practical'] = pr_m.group(1).strip().replace('\n', ' ')
                if nw_m and nw_m.group(1).strip():
                    depth['next_watch'] = nw_m.group(1).strip().replace('\n', ' ')
                if an_m and an_m.group(1).strip():
                    depth['antilogos'] = an_m.group(1).strip().replace('\n', ' ')

                data['world'].append({
                    'title': clean_title,
                    'tag': tag,
                    'body': body_text,
                    'source': source,
                    'depth': depth
                })

        # MARKETS TOP MOVERS
        elif 'ΑΓΟΡΕΣ' in sec_header or 'MOVERS' in sec_header:
            items_raw = re.split(r'\n###\s+', '\n' + sec)
            for raw_item in items_raw[1:]:
                lines_i = raw_item.strip().splitlines()
                if not lines_i:
                    continue
                header_line = lines_i[0].strip()
                cause_m = re.search(r'\*\*Αιτία:\*\*\s*(.+)', raw_item)
                cause = cause_m.group(1).strip() if cause_m else ''

                src_m = re.search(r'\*\*Πηγή:\*\*\s*(.+)', raw_item)
                source = None
                if src_m:
                    src_parsed = re.findall(r'\[(.*?)\]\((.*?)\)', src_m.group(1))
                    if src_parsed:
                        source = {'name': src_parsed[0][0], 'url': src_parsed[0][1]}

                data['markets'].append({
                    'header': header_line,
                    'cause': cause,
                    'source': source
                })

        # SPORTS
        elif 'ΑΘΛΗΤΙΚΑ' in sec_header:
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
                    elif 'Πηγή:' in item_text:
                        src_match = re.search(r'\[(.*?)\]\((.*?)\)', item_text)
                        if src_match:
                            data['sports'][team]['source'] = {
                                'name': src_match.group(1).strip(),
                                'url': src_match.group(2).strip()
                            }
                    else:
                        clean_news = re.sub(r'^\*?\*?(?:Μία γραμμή νέων|Νέα):\*?\*?\s*', '', item_text).strip()
                        data['sports'][team]['news'].append(clean_news)

            # Fallback source search for any team missing source
            for t_key, t_val in data['sports'].items():
                if not t_val['source']:
                    for r in reversed(t_val['raw']):
                        candidates = re.findall(r'\[(.*?)\]\((https?://.*?)\)', r)
                        for name, url in candidates:
                            if 'youtube' not in url.lower():
                                t_val['source'] = {'name': name, 'url': url}
                                break
                        if t_val['source']:
                            break

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
        'unique_properties': '1.427',
        'top_picks_count': '3',
        'top_pick_highlights': '2x 1Υ/Δ Ζακάκι + 1x 2Υ/Δ Ύψωνας (από €196k + ΦΠΑ)',
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
            data = parse_markdown(content)

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

    index_path = os.path.join(BASE_DIR, 'search-index.json')
    docs_index_path = os.path.join(DOCS_DIR, 'search-index.json')
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump(index_entries, f, ensure_ascii=False, indent=2)
    with open(docs_index_path, 'w', encoding='utf-8') as f:
        json.dump(index_entries, f, ensure_ascii=False, indent=2)

    return index_entries


def render_html(data, house_stats, search_index):
    date_display = data['date_str'] or '7 Σεπτεμβρίου 2026'
    time_display = data['time_str'] or '13:30'
    read_time = data['read_time'] or "7'"

    m_iso = re.search(r'(\d{4}-\d{2}-\d{2})', date_display)
    iso_date = m_iso.group(1) if m_iso else datetime.now().strftime('%Y-%m-%d')
    gen_iso = f"{iso_date}T{time_display}:00+03:00" if ':' in time_display else f"{iso_date}T13:30:00+03:00"

    # Ticker Items
    ticker_spans = []
    for d in data['dashboard']:
        color_cls = "text-[var(--up)]" if "+" in d['change'] else ("text-[var(--down)]" if "-" in d['change'] else "text-[var(--ink-quiet)]")
        ticker_spans.append(f'<span class="inline-flex items-center gap-1.5"><span class="font-bold text-[var(--ink)]">{d["asset"]}:</span> <span class="text-[var(--ink-body)]">{d["price"]}</span> <span class="{color_cls} font-semibold">{d["change"]}</span></span>')
    ticker_html = ' '.join(ticker_spans) + ' ' + ' '.join(ticker_spans)

    # Top Story Image Resolution
    top_url = data['top_story']['sources'][0]['url'] if data['top_story'].get('sources') else ''
    top_img, top_category = resolve_image(top_url, data['top_story'].get('title', ''), 'ΟΙΚΟΝΟΜΙΑ & ΑΞΙΟΧΡΕΟ')

    # House Search Nav Button & Card
    house_nav_html = ""
    house_card_html = ""
    if house_stats and house_stats.get('local_url'):
        house_nav_html = f'''<a href="{house_stats['local_url']}" target="_blank" class="whitespace-nowrap flex-shrink-0 px-3 py-1.5 rounded-full bg-[var(--paper)] text-[var(--ink)] border border-[var(--rule)] hover:border-[var(--accent)] hover:text-[var(--accent)] transition font-medium flex items-center gap-1">🏠 <span>Ακίνητα</span></a>'''
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
          <a href="{house_stats['local_url']}" target="_blank" class="inline-flex items-center gap-1.5 t-meta font-bold text-[var(--accent)] hover:underline">
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
        dash_rows.append(f'''
        <tr>
          <td class="py-2.5 font-semibold text-[var(--ink)] font-sans flex items-center gap-2">
            <span>{a_icon}</span> <span>{d['asset']}</span>
          </td>
          <td class="py-2.5 text-[var(--ink-body)] font-mono">{d['price']}</td>
          <td class="py-2.5 {change_cls} font-mono">
            <span class="inline-flex items-center gap-1">{icon} {d['change']}</span>
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
            'default_source': {'name': 'ManUtd.com', 'url': 'https://www.manutd.com/'}
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
  <script src="https://www.gstatic.com/antigravity/web/dev/tailwindcss.min.js"></script>
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

    /* Print styles */
    @media print {{
      body {{
        background-color: #ffffff !important;
        color: #000000 !important;
      }}
      .ticker-wrap,
      nav,
      #themeToggle,
      #archiveSearch,
      #searchResults,
      button[title="Εκτύπωση / PDF"],
      a[href*="youtube.com"] {{
        display: none !important;
      }}
      details {{
        display: block !important;
      }}
      details[open] summary,
      details summary {{
        display: none !important;
      }}
      details > div {{
        display: block !important;
      }}
      .card, .card--hero, .editorial-card {{
        border: 1px solid #ccc !important;
        box-shadow: none !important;
        page-break-inside: avoid;
      }}
      a {{
        text-decoration: none !important;
        color: #000000 !important;
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
  </style>
</head>
<body class="antialiased min-h-screen">

  <!-- TOP BAR & STATUS -->
  <div class="bg-[var(--paper-raised)] border-b border-[var(--rule)] text-xs py-1.5 px-4">
    <div class="max-w-7xl mx-auto flex flex-wrap justify-between items-center gap-2">
      <div class="flex items-center gap-3">
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
      </div>
      <div class="flex items-center gap-4 t-meta text-[var(--ink-quiet)]">
        <span>📍 Λεμεσός, Κύπρος</span>
        <span>⏱️ Ανάγνωση ~{read_time}</span>
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

      <!-- Search Input Container with Instant Dropdown -->
      <div class="relative flex items-center gap-1.5 flex-shrink-0 ml-auto sm:ml-0">
        <div class="relative">
          <label for="archiveSearch" class="sr-only">Αναζήτηση στο αρχείο</label>
          <input type="text" id="archiveSearch" placeholder="🔍 Αναζήτηση στο αρχείο..." 
                 class="t-meta px-3 py-1.5 rounded border border-[var(--rule)] bg-[var(--paper)] text-[var(--ink)] focus:outline-none focus:ring-2 focus:ring-[var(--accent)] w-36 sm:w-60 focus:w-48 sm:focus:w-64 transition-all shadow-xs">
          <!-- Live Search Results Dropdown -->
          <div id="searchResults" class="hidden absolute right-0 top-full mt-2 w-80 sm:w-96 max-h-96 overflow-y-auto bg-[var(--paper-raised)] border border-[var(--rule)] rounded-xl shadow-xl z-50 p-2 text-xs space-y-2">
          </div>
        </div>
        <button onclick="window.print()" class="t-meta px-2 py-1.5 rounded border border-[var(--rule)] hover:bg-[var(--paper)] transition" title="Εκτύπωση / PDF" aria-label="Εκτύπωση σελίδας">
          🖨️
        </button>
        <button id="themeToggleNav" class="t-meta px-2 py-1.5 rounded border border-[var(--rule)] hover:bg-[var(--paper)] transition" title="Εναλλαγή θέματος" aria-label="Εναλλαγή θέματος">
          🌓
        </button>
      </div>
    </div>
  </nav>

  <!-- MAIN CONTAINER (NEWS-FIRST HIERARCHY) -->
  <main class="max-w-7xl mx-auto px-4 py-8 space-y-12">

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
        <div class="lg:col-span-6 card p-5 flex flex-col justify-between">
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

              <div class="bg-[var(--paper)] border border-[var(--rule)] p-4 rounded-xl flex items-center justify-between mt-4">
                <div>
                  <div class="t-meta font-mono text-[var(--ink-quiet)] uppercase tracking-wider">Μηνιαία Δόση</div>
                  <div id="monthlyInstallment" class="font-masthead text-2xl sm:text-3xl font-black text-[var(--accent)]">€1.032</div>
                </div>
                <div class="text-right">
                  <div class="t-meta font-mono text-[var(--ink-quiet)] uppercase tracking-wider">Σύνολο Τόκων</div>
                  <div id="totalInterest" class="font-mono text-sm sm:text-base font-bold text-[var(--ink)]">€109.680</div>
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

    // 2. Interactive Mortgage Calculator
    (function () {{
      const amountEl = document.getElementById('calcAmount');
      const yearsEl = document.getElementById('calcYears');
      const rateEl = document.getElementById('calcRate');

      const amountVal = document.getElementById('amountVal');
      const yearsVal = document.getElementById('yearsVal');
      const rateVal = document.getElementById('rateVal');
      const monthlyInstallment = document.getElementById('monthlyInstallment');
      const totalInterest = document.getElementById('totalInterest');

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

        let m = 0;
        if (r > 0) {{
          m = (P * r) / (1 - Math.pow(1 + r, -n));
        }} else {{
          m = P / n;
        }}

        const totalPay = m * n;
        const interest = totalPay - P;

        monthlyInstallment.textContent = '€' + Math.round(m).toLocaleString('el-CY');
        totalInterest.textContent = '€' + Math.round(interest).toLocaleString('el-CY');
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

    // 4. Instant Archive Search
    (function () {{
      const input = document.getElementById('archiveSearch');
      const resultsContainer = document.getElementById('searchResults');
      let searchData = {json.dumps(search_index, ensure_ascii=False)};

      if (!input || !resultsContainer) return;

      input.addEventListener('input', (e) => {{
        const q = e.target.value.trim().toLowerCase();
        if (q.length < 2) {{
          resultsContainer.classList.add('hidden');
          resultsContainer.innerHTML = '';
          return;
        }}

        const matches = searchData.filter(item => 
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

    // 5. Smart Sticky Navigation Header (Auto-hide on scroll down, reveal on scroll up)
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
  </script>

</body>
</html>
'''
    return html


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

    data = parse_markdown(content)
    house_stats = get_latest_house_search()
    if house_stats:
        print(f"Linked House Search from: {house_stats['date']} ({house_stats['unique_properties']} properties)")

    print("Building cross-edition search index...")
    search_index = build_search_index()
    print(f"Indexed {len(search_index)} items across editions.")

    html_content = render_html(data, house_stats, search_index)

    os.makedirs(BRIEFINGS_DIR, exist_ok=True)
    os.makedirs(DOCS_DIR, exist_ok=True)
    os.makedirs(DOCS_BRIEFINGS_DIR, exist_ok=True)

    root_index = os.path.join(BASE_DIR, 'index.html')
    briefing_html = os.path.join(BRIEFINGS_DIR, f'oracle-briefing-{date_slug}.html')
    root_briefing_slug = os.path.join(BRIEFINGS_DIR, f'{date_slug}.html')
    docs_index = os.path.join(DOCS_DIR, 'index.html')
    docs_briefing_html = os.path.join(DOCS_BRIEFINGS_DIR, f'{date_slug}.html')
    docs_briefing_md = os.path.join(DOCS_BRIEFINGS_DIR, f'{date_slug}.md')

    for path in [root_index, briefing_html, root_briefing_slug, docs_index, docs_briefing_html]:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        print(f"Generated: {path}")

    shutil.copy2(target_md, docs_briefing_md)
    print(f"Copied markdown to docs: {docs_briefing_md}")

    print("\nSUCCESS! The Oracle Sovereign web portal and archives have been built with full news-first layout and imagery.")


if __name__ == '__main__':
    main()
