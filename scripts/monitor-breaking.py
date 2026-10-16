#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
monitor-breaking.py — 24/7 Real-Time Wire & Breaking Flash Engine
Monitors priority Cyprus and international feeds for high-impact breaking developments.
When a keyword indicates potentially important news:
  1. Records event to scripts/live-wire.json and docs/live-wire.json
  2. Avoids duplicate alerts using scripts/breaking-cache.json
  3. Records provider health and freshness. Never generates editions or sends Telegram.
"""

import os
import fcntl
import sys
import json
import time
import hashlib
import re
import urllib.request
import urllib.parse
import ssl
from email.utils import parsedate_to_datetime
from zoneinfo import ZoneInfo
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
HEALTH_FILE = os.path.join(BASE_DIR, 'docs', 'wire-health.json')
PROVIDER_HEALTH = {}
NICOSIA = ZoneInfo('Europe/Nicosia')

DOCS_SUB_WIRE_FILE = os.path.join(BASE_DIR, 'docs', 'briefings', 'live-wire.json')

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
        'name': 'CNBC Top News',
        'url': 'https://www.cnbc.com/id/100003114/device/rss/rss.html',
        'lang': 'en',
        'category': 'finance'
    },
    {
        'name': 'CNBC Markets',
        'url': 'https://www.cnbc.com/id/100727362/device/rss/rss.html',
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

    # Enforce valid HTTP/HTTPS URL
    valid_items = [itm for itm in items if (itm.get('link') or '').startswith('http')]
    sorted_items = sorted(valid_items, key=lambda x: x.get('timestamp', 0), reverse=True)
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

    for path in [LIVE_WIRE_FILE, DOCS_WIRE_FILE, DOCS_SUB_WIRE_FILE]:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(final_items, f, indent=2, ensure_ascii=False)


def get_xml_child_text(elem, tag_names):
    for wanted in tag_names:
        for child in elem:
            t = child.tag.split('}')[-1].lower()
            if t == wanted.lower():
                txt = (child.text or '').strip()
                if txt:
                    if wanted.lower() in ('link', 'guid', 'origlink') and not txt.startswith('http'):
                        continue
                    return txt
                if 'href' in child.attrib:
                    href = child.attrib['href'].strip()
                    if href.startswith('http'):
                        return href
    return ''



def fetch_feed(source):
    items = []
    try:
        PROVIDER_HEALTH[source['name']] = {'status': 'error', 'items': 0}
        req = urllib.request.Request(source['url'], headers=HEADERS)
        ctx = create_ssl_context()
        with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
            content = resp.read(2_000_001)
            if len(content) > 2_000_000:
                raise ValueError('Oversized feed')

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
        PROVIDER_HEALTH[source['name']] = {'status': 'ok' if items else 'empty', 'items': len(items)}
    except Exception as e:
        PROVIDER_HEALTH[source['name']] = {'status': 'error', 'items': 0, 'error': type(e).__name__}
        print(f"[!] Feed fetch error for {source['name']}: {type(e).__name__}", file=sys.stderr)
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



def publication_time(value):
    if not value:
        return None
    try:
        stamp = parsedate_to_datetime(value)
    except (TypeError, ValueError):
        try:
            stamp = datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (TypeError, ValueError):
            return None
    return stamp.astimezone(timezone.utc) if stamp.tzinfo else None


def eligible(item, now=None):
    now = now or datetime.now(timezone.utc)
    title = item.get('title', '').strip()
    if not title or re.search(r'mobile app advert|advertisement|league.table|βαθμολογία.*20\d{2}[-–]20\d{2}', title, re.I):
        return False
    published = publication_time(item.get('pub_date'))
    # Undated feed navigation cannot be labelled as fresh news.
    return bool(published and -300 <= (now-published).total_seconds() <= 48*3600)


def write_health(new_items):
    now = datetime.now(timezone.utc)
    old = {}
    if os.path.exists(HEALTH_FILE):
        try:
            with open(HEALTH_FILE, encoding='utf-8') as stream:
                old = json.load(stream)
        except (ValueError, OSError):
            pass
    successes = sum(p['status'] == 'ok' for p in PROVIDER_HEALTH.values())
    payload = {'schema_version': 1, 'checked_at': now.isoformat(),
               'last_success_at': now.isoformat() if successes else old.get('last_success_at'),
               'status': 'ok' if successes == len(PROVIDER_HEALTH) and successes else 'degraded' if successes else 'failed',
               'successful_providers': successes, 'total_providers': len(PROVIDER_HEALTH),
               'new_items': new_items, 'providers': PROVIDER_HEALTH}
    temporary = HEALTH_FILE+'.tmp'
    with open(temporary, 'w', encoding='utf-8') as stream:
        json.dump(payload, stream, ensure_ascii=False, indent=2)
    os.replace(temporary, HEALTH_FILE)


def run_monitor():
    print("[*] 24/7 Breaking Wire Monitor running...", file=sys.stderr)
    cache = load_cache()
    seen_hashes = set(cache.get('seen_hashes', []))
    current_time = time.time()

    wire_items = [x for x in load_live_wire() if x.get('published_at') and
                  eligible({'title': x.get('title'), 'pub_date': x['published_at']})]
    new_wire_count = 0

    all_harvested = []
    for src in SOURCES:
        items = fetch_feed(src)
        all_harvested.extend(items)

    for item in all_harvested:
        if not eligible(item):
            continue
        if not (item.get('link') or '').startswith('http'):
            continue
        h = hashlib.sha256((item['link'] + item['title']).encode('utf-8')).hexdigest()
        if h in seen_hashes:
            continue

        seen_hashes.add(h)
        item_obj = {
            'id': h,
            'title': item['title'],
            'link': item['link'],
            'snippet': item['description'][:300].strip(),
            'source': item['source'],
            'category': item.get('category', 'international'),
            'timestamp': int(publication_time(item['pub_date']).timestamp()),
            'published_at': publication_time(item['pub_date']).isoformat(),
            'retrieved_at': datetime.now(timezone.utc).isoformat(),
            'time_str': publication_time(item['pub_date']).astimezone(NICOSIA).strftime('%d/%m %H:%M · Κύπρος'),
            'is_breaking': False
        }

        high_impact, matched_tags = is_high_impact(item)
        if high_impact:
            item_obj['is_breaking'] = True
            item_obj['tags'] = matched_tags
            print(f"[!] High-impact item detected: {item['title']} (Tags: {matched_tags})", file=sys.stderr)

        wire_items.insert(0, item_obj)
        new_wire_count += 1

    cache['seen_hashes'] = list(seen_hashes)
    cache.pop('last_flash_time', None)
    save_cache(cache)
    save_live_wire(wire_items)
    write_health(new_wire_count)

    print(f"[✔] Monitor complete. {new_wire_count} new wire items recorded, no Telegram delivery.", file=sys.stderr)
    return new_wire_count


def main():
    try:
        # Share the local snapshot-promotion lock; RSS collection/schedules stay independent.
        lock_dir=os.path.join(BASE_DIR,'.work')
        os.makedirs(lock_dir,exist_ok=True)
        with open(os.path.join(lock_dir,'publication.lock'),'a') as lock:
            fcntl.flock(lock,fcntl.LOCK_EX)
            run_monitor()
        return 0 if any(x['status'] == 'ok' for x in PROVIDER_HEALTH.values()) else 1
    except Exception as error:
        print(f'Monitor failed: {type(error).__name__}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    sys.exit(main())
