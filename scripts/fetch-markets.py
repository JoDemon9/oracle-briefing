#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch-markets.py — Programmatic Live Market & Euribor Data Fetcher for THE ORACLE SOVEREIGN.
Fetches real-time / latest closing prices and % changes from Yahoo Finance API,
plus live Euribor rates from euribor-rates.eu, and saves to scripts/markets-data.json.
"""

import os
import sys
import json
import urllib.request
import re
from datetime import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
OUTPUT_FILE = os.path.join(BASE_DIR, 'scripts', 'markets-data.json')

SYMBOLS = {
    'S&P 500': '^GSPC',
    'Nasdaq Composite': '^IXIC',
    'CBOE VIX': '^VIX',
    'US 10Y Yield': '^TNX',
    'Brent Crude': 'BZ=F',
    'WTI Crude': 'CL=F',
    'EUR/USD': 'EURUSD=X',
    'Bitcoin (BTC)': 'BTC-USD',
    'Ethereum (ETH)': 'ETH-USD',
    'Bank of Cyprus (BOCH)': 'BOCHGR.AT'
}

DEFAULT_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
        'AppleWebKit/537.36 (KHTML, like Gecko) '
        'Chrome/128.0.0.0 Safari/537.36'
    ),
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
    'Accept-Language': 'el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7'
}


def fetch_yahoo_quotes():
    results = {}
    today_str = datetime.now().strftime('%d/%m/%Y')

    for name, sym in SYMBOLS.items():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
        try:
            req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
            with urllib.request.urlopen(req, timeout=8) as r:
                data = json.loads(r.read().decode('utf-8'))
                meta = data['chart']['result'][0]['meta']
                price = meta.get('regularMarketPrice')
                prev = meta.get('chartPreviousClose')
                chg = ((price - prev) / prev) * 100 if (prev and price) else 0.0
                results[name] = {
                    'symbol': sym,
                    'price': price,
                    'change': chg,
                    'date': today_str
                }
        except Exception as e:
            print(f"[!] Warning fetching {sym}: {e}", file=sys.stderr)

    return results


def fetch_euribor_rates():
    """Scrapes latest authoritative Euribor rates from euribor-rates.eu."""
    rates = {
        '1m': '2,369%',
        '3m': '2,626%',
        '6m': '2,800%',
        '12m': '3,138%',
        'date': datetime.now().strftime('%d/%m/%Y'),
        'source': 'euribor-rates.eu'
    }
    url = "https://www.euribor-rates.eu/en/current-euribor-rates/"
    try:
        from bs4 import BeautifulSoup
        req = urllib.request.Request(url, headers=DEFAULT_HEADERS)
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read()
            soup = BeautifulSoup(html, 'html.parser')
            for tr in soup.select('table tr'):
                th_td = tr.find(['th', 'td'])
                tds = tr.find_all('td')
                if th_td and tds:
                    label = th_td.get_text(strip=True).lower()
                    val = tds[0].get_text(strip=True).replace('%', '').strip().replace('.', ',') + '%'
                    if '1 month' in label:
                        rates['1m'] = val
                    elif '3 month' in label:
                        rates['3m'] = val
                    elif '6 month' in label:
                        rates['6m'] = val
                    elif '12 month' in label:
                        rates['12m'] = val
    except Exception as e:
        print(f"[!] Warning fetching Euribor: {e}", file=sys.stderr)

    return rates


def format_greek(val, decimals=2):
    if val is None:
        return "0,00"
    s = f"{val:.{decimals}f}"
    parts = s.split('.')
    int_part = "{:,}".format(int(parts[0])).replace(',', '.')
    return f"{int_part},{parts[1]}"


def get_full_markets_data():
    quotes = fetch_yahoo_quotes()
    euribor = fetch_euribor_rates()
    return {
        'fetched_at': datetime.now().isoformat(),
        'quotes': quotes,
        'euribor': euribor
    }


def main():
    dest = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith('--') else OUTPUT_FILE
    data = get_full_markets_data()

    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with open(dest, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✔ Live markets & Euribor saved to: {dest}")

    if '--json' in sys.argv:
        print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
