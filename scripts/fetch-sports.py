#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch-sports.py — Programmatic Sports News Harvester for THE ORACLE SOVEREIGN.
Scrapes latest news headlines, URLs, and metadata for 4 tracked teams:
  1. Omonoia (Cyprus) — Primary: Kerkida.net
  2. Manchester United — Primary: The Guardian (Fallback: BBC Sport / Sky Sports)
  3. Real Madrid — Primary: Marca (Fallback: Marca ES)
  4. Formula 1 — Primary: BBC Sport F1 (Fallback: Formula1.com)

Features:
  - Uses only Python standard library + BeautifulSoup4
  - Configures UTF-8 encoding on stdout/stderr to prevent Windows cp1252 errors
  - SSL context with verification disabled for broad host compatibility
  - Custom browser User-Agent headers
  - Graceful per-source error handling & fallback chaining
  - Standalone CLI support: prints JSON to stdout or saves to destination file path

Usage:
  python scripts/fetch-sports.py                    # Output JSON to stdout
  python scripts/fetch-sports.py output.json        # Save JSON to output.json
  python scripts/fetch-sports.py -o output.json     # Save JSON to output.json
"""

import os
import re
import ssl
import sys
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from bs4 import BeautifulSoup

# Ensure proper UTF-8 output on Windows consoles
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/128.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7',
    'Cache-Control': 'no-cache',
    'Pragma': 'no-cache',
}


def create_ssl_context():
    """Returns an SSL context with certificate verification disabled."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_soup(url, timeout=12, headers=None):
    """Fetches a URL and returns a parsed BeautifulSoup instance, or None on failure."""
    req_headers = headers or DEFAULT_HEADERS
    req = urllib.request.Request(url, headers=req_headers)
    ctx = create_ssl_context()
    try:
        with urllib.request.urlopen(req, context=ctx, timeout=timeout) as response:
            html = response.read()
            return BeautifulSoup(html, 'html.parser'), response.geturl()
    except Exception as e:
        print(f"[!] Warning: HTTP error fetching {url}: {e}", file=sys.stderr)
        return None, url


def get_iso_now():
    """Returns the current ISO-8601 timestamp."""
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Scrapers
# ---------------------------------------------------------------------------

def scrape_omonoia(limit=5):
    """
    Scrapes Omonoia news headlines and links from Kerkida.net.
    Fallback: general category page.
    """
    primary_url = 'https://www.kerkida.net/eidiseis/a-katigoria/omonoia'
    sources_used = []
    articles = []
    seen_urls = set()

    soup, base_url = fetch_soup(primary_url)
    if soup:
        sources_used.append('Kerkida.net')
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Target Omonoia article links, skip index/section anchors
            if '/omonoia' in href and not href.rstrip('/').endswith('/a-katigoria/omonoia'):
                full_url = urllib.parse.urljoin(base_url, href)
                if full_url in seen_urls:
                    continue

                # Preferred clean title tag in Kerkida markup
                title_span = a.find(class_='title') or a.find('span', class_='title')
                if title_span:
                    title = title_span.get_text(strip=True)
                else:
                    raw_text = a.get_text(separator=' ', strip=True)
                    # Strip timestamps like '09/09/2026 - 14:41'
                    title = re.sub(r'\d{2}/\d{2}/\d{4}\s*-\s*\d{2}:\d{2}', '', raw_text).strip()

                title = re.sub(r'\s+', ' ', title).strip()

                if len(title) > 10 and 'kerkida.net' in full_url:
                    seen_urls.add(full_url)
                    articles.append({
                        'title': title,
                        'url': full_url,
                        'source': 'Kerkida.net'
                    })
                if len(articles) >= limit:
                    break

    # Fallback to general category if primary yielded fewer than desired articles
    if len(articles) < limit:
        fallback_url = 'https://www.kerkida.net/eidiseis/a-katigoria'
        fb_soup, fb_base = fetch_soup(fallback_url)
        if fb_soup:
            if 'Kerkida.net' not in sources_used:
                sources_used.append('Kerkida.net')
            for a in fb_soup.find_all('a', href=True):
                href = a['href']
                if '/omonoia' in href:
                    full_url = urllib.parse.urljoin(fb_base, href)
                    if full_url in seen_urls:
                        continue
                    title_span = a.find(class_='title') or a.find('span', class_='title')
                    title = title_span.get_text(strip=True) if title_span else a.get_text(separator=' ', strip=True)
                    title = re.sub(r'\d{2}/\d{2}/\d{4}\s*-\s*\d{2}:\d{2}', '', title).strip()
                    title = re.sub(r'\s+', ' ', title).strip()

                    if len(title) > 10 and 'kerkida.net' in full_url:
                        seen_urls.add(full_url)
                        articles.append({
                            'title': title,
                            'url': full_url,
                            'source': 'Kerkida.net'
                        })
                    if len(articles) >= limit:
                        break

    return {
        'team': 'Omonoia',
        'sources': sources_used,
        'articles': articles[:limit],
        'fetched_at': get_iso_now()
    }


def scrape_manchester_united(limit=5):
    """
    Scrapes Manchester United news headlines and links from The Guardian.
    Fallback: BBC Sport Manchester United.
    """
    primary_url = 'https://www.theguardian.com/football/manchester-united'
    sources_used = []
    articles = []
    seen_urls = set()

    soup, base_url = fetch_soup(primary_url)
    if soup:
        sources_used.append('The Guardian')
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Match Guardian football article URLs
            if '/football/' in href and ('/202' in href or 'manchester-united' in href):
                if href.rstrip('/').endswith('/football/manchester-united'):
                    continue
                full_url = urllib.parse.urljoin(base_url, href)
                if full_url in seen_urls:
                    continue

                aria = a.get('aria-label')
                raw_text = aria if aria else a.get_text(separator=' ', strip=True)
                title = re.sub(r'\s+', ' ', raw_text).strip()

                # Filter out navigation / non-article text
                lower_t = title.lower()
                if (len(title) > 18 and
                        not lower_t.startswith('sign in') and
                        not 'privacy' in lower_t and
                        not 'terms of service' in lower_t):
                    seen_urls.add(full_url)
                    articles.append({
                        'title': title,
                        'url': full_url,
                        'source': 'The Guardian'
                    })
                if len(articles) >= limit:
                    break

    # Fallback to BBC Sport Manchester United if needed
    if len(articles) < limit:
        bbc_url = 'https://www.bbc.com/sport/football/teams/manchester-united'
        bbc_soup, bbc_base = fetch_soup(bbc_url)
        if bbc_soup:
            if 'BBC Sport' not in sources_used:
                sources_used.append('BBC Sport')
            for a in bbc_soup.find_all('a', href=True):
                href = a['href']
                if '/sport/football/articles/' in href or '/sport/articles/' in href:
                    full_url = urllib.parse.urljoin(bbc_base, href)
                    if full_url in seen_urls:
                        continue
                    title = a.get_text(separator=' ', strip=True)
                    title = re.sub(r'\s+', ' ', title).strip()
                    # Remove live timestamps like '11:58 BST'
                    title = re.sub(r'^\d{1,2}:\d{2}\s+(?:BST|GMT|UTC)\s*', '', title).strip()
                    if len(title) > 20 and not title.lower().startswith('quiz'):
                        seen_urls.add(full_url)
                        articles.append({
                            'title': title,
                            'url': full_url,
                            'source': 'BBC Sport'
                        })
                    if len(articles) >= limit:
                        break

    return {
        'team': 'Manchester United',
        'sources': sources_used,
        'articles': articles[:limit],
        'fetched_at': get_iso_now()
    }


def scrape_real_madrid(limit=5):
    """
    Scrapes Real Madrid news headlines and links from Marca English.
    Fallback: Marca Spanish.
    """
    primary_url = 'https://www.marca.com/en/football/real-madrid.html'
    sources_used = []
    articles = []
    seen_urls = set()

    soup, base_url = fetch_soup(primary_url)
    if soup:
        sources_used.append('Marca')
        for h in soup.find_all(['h2', 'h3']):
            a = h.find('a', href=True)
            if not a and h.parent.name == 'a' and h.parent.has_attr('href'):
                a = h.parent
            if not a:
                continue

            href = a['href']
            if not href.endswith('.html') or href.endswith('/football/real-madrid.html'):
                continue

            full_url = urllib.parse.urljoin(base_url, href)
            if full_url in seen_urls:
                continue

            title = h.get_text(separator=' ', strip=True)
            title = re.sub(r'\s+', ' ', title).strip()

            lower_t = title.lower()
            if (len(title) > 18 and
                    not 'marca' in lower_t and
                    not 'newsletter' in lower_t and
                    not 'cookies' in lower_t):
                seen_urls.add(full_url)
                articles.append({
                    'title': title,
                    'url': full_url,
                    'source': 'Marca'
                })
            if len(articles) >= limit:
                break

    # Fallback to Marca Spanish if English failed or gave < limit
    if len(articles) < limit:
        es_url = 'https://www.marca.com/futbol/real-madrid.html'
        es_soup, es_base = fetch_soup(es_url)
        if es_soup:
            if 'Marca (ES)' not in sources_used:
                sources_used.append('Marca (ES)')
            for h in es_soup.find_all(['h2', 'h3']):
                a = h.find('a', href=True)
                if not a and h.parent.name == 'a' and h.parent.has_attr('href'):
                    a = h.parent
                if not a:
                    continue
                href = a['href']
                if not href.endswith('.html') or 'real-madrid.html' in href.split('/')[-1]:
                    continue
                full_url = urllib.parse.urljoin(es_base, href)
                if full_url in seen_urls:
                    continue
                title = h.get_text(separator=' ', strip=True)
                title = re.sub(r'\s+', ' ', title).strip()
                if len(title) > 18:
                    seen_urls.add(full_url)
                    articles.append({
                        'title': title,
                        'url': full_url,
                        'source': 'Marca (ES)'
                    })
                if len(articles) >= limit:
                    break

    return {
        'team': 'Real Madrid',
        'sources': sources_used,
        'articles': articles[:limit],
        'fetched_at': get_iso_now()
    }


def scrape_formula1(limit=5):
    """
    Scrapes Formula 1 news headlines and links from BBC Sport F1.
    Fallback: Formula1.com official.
    """
    primary_url = 'https://www.bbc.com/sport/formula1'
    sources_used = []
    articles = []
    seen_urls = set()

    skip_phrases = [
        'send us a question', 'teams & drivers', 'how to follow', 'f1 shorts',
        'results', 'calendar', 'standings', 'gossip', 'formula 1', 'f1 home',
        'driver ratings', 'watch live', 'listen live'
    ]

    soup, base_url = fetch_soup(primary_url)
    if soup:
        sources_used.append('BBC Sport F1')
        for a in soup.find_all('a', href=True):
            href = a['href']
            # Match BBC Sport F1 article paths
            if '/sport/formula1/articles/' in href or '/sport/articles/' in href:
                full_url = urllib.parse.urljoin(base_url, href)
                if full_url in seen_urls:
                    continue

                title = a.get_text(separator=' ', strip=True)
                title = re.sub(r'\s+', ' ', title).strip()
                lower_t = title.lower()

                if len(title) > 20 and not any(sp in lower_t for sp in skip_phrases):
                    seen_urls.add(full_url)
                    articles.append({
                        'title': title,
                        'url': full_url,
                        'source': 'BBC Sport F1'
                    })
                if len(articles) >= limit:
                    break

    # Fallback to official Formula1.com if needed
    if len(articles) < limit:
        f1_url = 'https://www.formula1.com/en/latest/all'
        f1_soup, f1_base = fetch_soup(f1_url)
        if f1_soup:
            if 'Formula1.com' not in sources_used:
                sources_used.append('Formula1.com')
            for a in f1_soup.find_all('a', href=True):
                href = a['href']
                if '/en/latest/article/' in href:
                    full_url = urllib.parse.urljoin(f1_base, href)
                    if full_url in seen_urls:
                        continue
                    title = a.get_text(separator=' ', strip=True)
                    title = re.sub(r'\s+', ' ', title).strip()
                    if len(title) > 20:
                        seen_urls.add(full_url)
                        articles.append({
                            'title': title,
                            'url': full_url,
                            'source': 'Formula1.com'
                        })
                    if len(articles) >= limit:
                        break

    return {
        'team': 'Formula 1',
        'sources': sources_used,
        'articles': articles[:limit],
        'fetched_at': get_iso_now()
    }


# ---------------------------------------------------------------------------
# Aggregator & Orchestrator
# ---------------------------------------------------------------------------

def fetch_all_sports(limit_per_team=5):
    """
    Scrapes sports data for all 4 tracked teams.
    Handles errors per team gracefully, continuing if any single source fails.
    """
    results = {}
    iso_now = get_iso_now()

    # Omonoia
    try:
        results['omonoia'] = scrape_omonoia(limit=limit_per_team)
    except Exception as e:
        print(f"[!] Error scraping Omonoia: {e}", file=sys.stderr)
        results['omonoia'] = {
            'team': 'Omonoia',
            'sources': [],
            'articles': [],
            'fetched_at': iso_now
        }

    # Manchester United
    try:
        results['manchester_united'] = scrape_manchester_united(limit=limit_per_team)
    except Exception as e:
        print(f"[!] Error scraping Manchester United: {e}", file=sys.stderr)
        results['manchester_united'] = {
            'team': 'Manchester United',
            'sources': [],
            'articles': [],
            'fetched_at': iso_now
        }

    # Real Madrid
    try:
        results['real_madrid'] = scrape_real_madrid(limit=limit_per_team)
    except Exception as e:
        print(f"[!] Error scraping Real Madrid: {e}", file=sys.stderr)
        results['real_madrid'] = {
            'team': 'Real Madrid',
            'sources': [],
            'articles': [],
            'fetched_at': iso_now
        }

    # Formula 1
    try:
        results['formula1'] = scrape_formula1(limit=limit_per_team)
    except Exception as e:
        print(f"[!] Error scraping Formula 1: {e}", file=sys.stderr)
        results['formula1'] = {
            'team': 'Formula 1',
            'sources': [],
            'articles': [],
            'fetched_at': iso_now
        }

    return results


def main():
    # Parse CLI argument for output file path
    output_path = None
    args = sys.argv[1:]

    i = 0
    while i < len(args):
        arg = args[i]
        if arg in ('-o', '--output'):
            if i + 1 < len(args):
                output_path = args[i + 1]
                i += 2
                continue
        elif not arg.startswith('-'):
            output_path = arg
        i += 1

    print("[*] Fetching sports data for Omonoia, Manchester United, Real Madrid, and Formula 1...", file=sys.stderr)
    sports_data = fetch_all_sports(limit_per_team=5)

    json_str = json.dumps(sports_data, indent=2, ensure_ascii=False)

    if output_path:
        out_dir = os.path.dirname(os.path.abspath(output_path))
        if out_dir:
            os.makedirs(out_dir, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_str + '\n')
        total_articles = sum(len(team_obj.get('articles', [])) for team_obj in sports_data.values())
        print(f"[✔] Successfully harvested {total_articles} sports articles into: {output_path}", file=sys.stderr)
    else:
        print(json_str)


if __name__ == '__main__':
    main()
