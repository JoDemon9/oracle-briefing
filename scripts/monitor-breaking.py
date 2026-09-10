#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitor-breaking.py — 24/7 Real-Time Wire & Breaking Flash Engine
Monitors priority Cyprus and international feeds for high-impact breaking developments.
When a verified breaking threshold is met:
  1. Records event to scripts/live-wire.json and docs/live-wire.json
  2. Avoids duplicate alerts using scripts/breaking-cache.json
  3. Dispatches high-priority Telegram Flash alert (⚡ THE ORACLE FLASH)
"""

import os
import sys
import json
import time
import hashlib
import re
import urllib.request
import urllib.parse
import ssl
from datetime import datetime, timezone
import warnings
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

# UTF-8 console output
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CACHE_FILE = os.path.join(BASE_DIR, 'scripts', 'breaking-cache.json')
LIVE_WIRE_FILE = os.path.join(BASE_DIR, 'scripts', 'live-wire.json')
DOCS_WIRE_FILE = os.path.join(BASE_DIR, 'docs', 'live-wire.json')

HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/128.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/rss+xml,application/xml,text/xml,text/html,*/*;q=0.9',
    'Accept-Language': 'el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7',
}

SOURCES = [
    # 1. International News (Dominant - 4 sources)
    {
        'name': 'BBC World',
        'url': 'https://feeds.bbci.co.uk/news/world/rss.xml',
        'lang': 'en',
        'category': 'international'
    },
    {
        'name': 'France 24',
        'url': 'https://www.france24.com/en/rss',
        'lang': 'en',
        'category': 'international'
    },
    {
        'name': 'Al Jazeera',
        'url': 'https://www.aljazeera.com/xml/rss/all.xml',
        'lang': 'en',
        'category': 'international'
    },
    {
        'name': 'DW World',
        'url': 'https://rss.dw.com/rdf/rss-en-all',
        'lang': 'en',
        'category': 'international'
    },
    # 2. Finance & Market Intelligence (3 sources)
    {
        'name': 'Yahoo Finance',
        'url': 'https://finance.yahoo.com/news/rssindex',
        'lang': 'en',
        'category': 'finance'
    },
    {
        'name': 'CNBC',
        'url': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
        'lang': 'en',
        'category': 'finance'
    },
    {
        'name': 'MarketWatch',
        'url': 'https://feeds.content.dowjones.io/public/rss/mw_topstories',
        'lang': 'en',
        'category': 'finance'
    },
    # 3. Cyprus National & Strategic (3 sources)
    {
        'name': 'Philenews',
        'url': 'https://www.philenews.com/feed/',
        'lang': 'el',
        'category': 'cyprus'
    },
    {
        'name': 'Sigmalive',
        'url': 'https://www.sigmalive.com/rss',
        'lang': 'el',
        'category': 'cyprus'
    },
    {
        'name': 'Cyprus Mail',
        'url': 'https://cyprus-mail.com/feed/',
        'lang': 'en',
        'category': 'cyprus'
    },
    # 4. Sports Intelligence (3 sources)
    {
        'name': 'BBC Sport',
        'url': 'https://feeds.bbci.co.uk/sport/rss.xml',
        'lang': 'en',
        'category': 'sports'
    },
    {
        'name': 'Sky Sports',
        'url': 'https://www.skysports.com/rss/12040',
        'lang': 'en',
        'category': 'sports'
    },
    {
        'name': 'Kerkida',
        'url': 'https://www.kerkida.net/rss.xml',
        'lang': 'el',
        'category': 'sports'
    }
]

CRITICAL_KEYWORDS_EL = [
    'έκτακτο', 'εκτακτο', 'επείγον', 'επειγον', 'σεισμός', 'σεισμος',
    'τράπεζα κύπρου', 'τραπεζα κυπρου', 'κεντρική τράπεζα', 'εκτ',
    'επιτόκια', 'επιτοκια', 'προεδρικό', 'υπουργικό συμβούλιο',
    'κατάπαυση του πυρός', 'ναυάγιο', 'απαγόρευση', 'πληθωρισμός',
    'χρηματιστήριο', 'ομόλογα', 'κυβερνοεπίθεση'
]

CRITICAL_KEYWORDS_EN = [
    'breaking', 'urgent', 'emergency', 'central bank', 'ecb', 'fed',
    'bank of cyprus', 'rate cut', 'rate hike', 'earthquake', 'inflation',
    'ceasefire', 'explosion', 'presidential decree', 'sanctions', 'cyberattack'
]


def create_ssl_context():
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return {'seen_hashes': [], 'last_flash_time': 0}
    return {'seen_hashes': [], 'last_flash_time': 0}


def save_cache(cache):
    cache['seen_hashes'] = cache.get('seen_hashes', [])[-500:]
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump(cache, f, indent=2, ensure_ascii=False)


def load_live_wire():
    if os.path.exists(LIVE_WIRE_FILE):
        try:
            with open(LIVE_WIRE_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_live_wire(items):
    # Balanced retention across categories:
    # International (largest share: up to 26 items), Finance (up to 14), Cyprus (up to 12), Sports (up to 8)
    cat_limits = {
        'international': 26,
        'finance': 14,
        'cyprus': 12,
        'sports': 8
    }
    cat_buckets = {c: [] for c in cat_limits}
    other_bucket = []

    sorted_items = sorted(items, key=lambda x: x.get('timestamp', 0), reverse=True)
    for itm in sorted_items:
        cat = itm.get('category', 'international')
        if cat in cat_buckets:
            if len(cat_buckets[cat]) < cat_limits[cat]:
                cat_buckets[cat].append(itm)
        else:
            if len(other_bucket) < 5:
                other_bucket.append(itm)

    balanced = []
    for b in cat_buckets.values():
        balanced.extend(b)
    balanced.extend(other_bucket)
    final_items = sorted(balanced, key=lambda x: x.get('timestamp', 0), reverse=True)[:60]

    for path in [LIVE_WIRE_FILE, DOCS_WIRE_FILE]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(final_items, f, indent=2, ensure_ascii=False)


def get_xml_child_text(elem, tag_names):
    for child in elem:
        t = child.tag.split('}')[-1].lower()
        if t in tag_names:
            txt = (child.text or '').strip()
            if txt:
                return txt
            if 'href' in child.attrib:
                return child.attrib['href'].strip()
    return ''


def fetch_feed(source):
    items = []
    try:
        req = urllib.request.Request(source['url'], headers=HEADERS)
        ctx = create_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            content = resp.read()

        # 1. Primary parser: xml.etree.ElementTree
        parsed_via_et = False
        try:
            root = ET.fromstring(content)
            xml_items = [e for e in root.iter() if e.tag.split('}')[-1].lower() in ('item', 'entry')]
            for it in xml_items:
                title = get_xml_child_text(it, ['title'])
                link = get_xml_child_text(it, ['link', 'guid', 'origlink'])
                desc_raw = get_xml_child_text(it, ['description', 'summary', 'content'])
                pub_date = get_xml_child_text(it, ['pubdate', 'updated', 'published', 'date'])

                desc = re.sub(r'<[^>]+>', '', desc_raw)
                desc = re.sub(r'\s+', ' ', desc).strip()

                if title and link:
                    items.append({
                        'title': title,
                        'link': link,
                        'description': desc[:300],
                        'pub_date': pub_date,
                        'source': source['name'],
                        'lang': source['lang'],
                        'category': source.get('category', 'international')
                    })
            if items:
                parsed_via_et = True
        except Exception:
            parsed_via_et = False

        # 2. Fallback parser: BeautifulSoup if ET found nothing or errored
        if not parsed_via_et:
            soup = BeautifulSoup(content, 'html.parser')
            for item in soup.find_all(['item', 'entry']):
                title_tag = item.find('title')
                link_tag = item.find('link')
                desc_tag = item.find(['description', 'summary'])
                pub_tag = item.find(['pubdate', 'updated', 'published'])

                title = title_tag.get_text(strip=True) if title_tag else ''
                link = ''
                if link_tag:
                    link = link_tag.get_text(strip=True) or link_tag.get('href', '')
                desc_raw = desc_tag.get_text(strip=True) if desc_tag else ''
                desc = re.sub(r'<[^>]+>', '', desc_raw)
                desc = re.sub(r'\s+', ' ', desc).strip()
                pub_date = pub_tag.get_text(strip=True) if pub_tag else ''

                if title and link:
                    items.append({
                        'title': title,
                        'link': link,
                        'description': desc[:300],
                        'pub_date': pub_date,
                        'source': source['name'],
                        'lang': source['lang'],
                        'category': source.get('category', 'international')
                    })
    except Exception as e:
        print(f"[!] Feed fetch error for {source['name']}: {e}", file=sys.stderr)
    return items



def is_high_impact(item):
    text = f"{item['title']} {item['description']}".lower()
    keywords = CRITICAL_KEYWORDS_EL if item['lang'] == 'el' else CRITICAL_KEYWORDS_EN

    matched = []
    for kw in keywords:
        if len(kw) <= 4:
            if re.search(rf'(?:\b|_){re.escape(kw)}(?:\b|_)', text):
                matched.append(kw)
        else:
            if kw in text:
                matched.append(kw)

    is_urgent = any(u in item['title'].lower() for u in ['έκτακτο', 'εκτακτο', 'breaking', 'urgent'])

    if is_urgent or len(matched) >= 1:
        return True, matched
    return False, []


def send_telegram_flash(flash_item):
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    chat_id = os.environ.get('TELEGRAM_CHAT_ID')

    if not token or not chat_id:
        env_file = os.path.join(BASE_DIR, '.env')
        if os.path.exists(env_file):
            try:
                with open(env_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        if line.startswith('TELEGRAM_BOT_TOKEN='):
                            token = line.split('=', 1)[1].strip().strip('"\'')
                        elif line.startswith('TELEGRAM_CHAT_ID='):
                            chat_id = line.split('=', 1)[1].strip().strip('"\'')
            except Exception:
                pass

    if not token or not chat_id:
        print("[-] Telegram credentials not configured for flash alert.", file=sys.stderr)
        return False

    now_cy = datetime.now(timezone.utc).strftime('%H:%M')
    msg = (
        f"⚡ <b>THE ORACLE FLASH | ΕΚΤΑΚΤΟ</b>\n"
        f"<i>{now_cy} ώρα Κύπρου · 24/7 Intelligence Wire</i>\n\n"
        f"🚨 <b>{flash_item['title']}</b>\n\n"
        f"{flash_item.get('description', '')[:220]}...\n\n"
        f"🔗 <a href=\"{flash_item['link']}\">Πλήρες Ρεπορτάζ ({flash_item['source']})</a> · "
        f"<a href=\"https://jodemon9.github.io/oracle-briefing/\">Web Terminal</a>"
    )

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        'chat_id': chat_id,
        'text': msg,
        'parse_mode': 'HTML',
        'disable_web_page_preview': False
    }

    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        ctx = create_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
            print("[✔] Telegram flash alert dispatched successfully!", file=sys.stderr)
            return True
    except Exception as e:
        print(f"[!] Error sending Telegram flash: {e}", file=sys.stderr)
        return False


def run_monitor(dispatch=True):
    print("[*] 24/7 Breaking Wire Monitor running...", file=sys.stderr)
    cache = load_cache()
    seen_hashes = set(cache.get('seen_hashes', []))
    last_flash_time = cache.get('last_flash_time', 0)
    current_time = time.time()

    wire_items = load_live_wire()
    new_wire_count = 0
    flashed_count = 0

    all_harvested = []
    for src in SOURCES:
        items = fetch_feed(src)
        all_harvested.extend(items)

    for item in all_harvested:
        h = hashlib.sha256((item['link'] + item['title']).encode('utf-8')).hexdigest()
        if h in seen_hashes:
            continue

        seen_hashes.add(h)
        item_obj = {
            'id': h,
            'title': item['title'],
            'link': item['link'],
            'snippet': item['description'][:180],
            'source': item['source'],
            'category': item.get('category', 'international'),
            'timestamp': int(time.time()),
            'time_str': datetime.now(timezone.utc).strftime('%H:%M UTC'),
            'is_breaking': False
        }

        high_impact, matched_tags = is_high_impact(item)
        if high_impact:
            item_obj['is_breaking'] = True
            item_obj['tags'] = matched_tags
            print(f"[!] High-impact item detected: {item['title']} (Tags: {matched_tags})", file=sys.stderr)

            time_since_flash = current_time - last_flash_time
            is_explicit_breaking = any(u in item['title'].lower() for u in ['έκτακτο', 'εκτακτο', 'breaking', 'urgent'])

            if dispatch and (is_explicit_breaking or time_since_flash > 5400):
                dispatched = send_telegram_flash(item)
                if dispatched:
                    last_flash_time = current_time
                    flashed_count += 1

        wire_items.insert(0, item_obj)
        new_wire_count += 1

    cache['seen_hashes'] = list(seen_hashes)
    cache['last_flash_time'] = last_flash_time
    save_cache(cache)
    save_live_wire(wire_items)

    print(f"[✔] Monitor complete. {new_wire_count} new wire items recorded, {flashed_count} flash alerts sent.", file=sys.stderr)
    return new_wire_count, flashed_count


def main():
    dispatch = '--no-dispatch' not in sys.argv
    run_monitor(dispatch=dispatch)


if __name__ == '__main__':
    main()
