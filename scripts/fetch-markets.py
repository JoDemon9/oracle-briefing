#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fetch-markets.py — Programmatic Live Market Data Fetcher for THE ORACLE SOVEREIGN.
Fetches real-time / latest closing prices and % changes from Yahoo Finance API.
"""

import sys
import json
import urllib.request
from datetime import datetime

sys.stdout.reconfigure(encoding='utf-8')

SYMBOLS = {
    'S&P 500': '^GSPC',
    'Nasdaq Composite': '^IXIC',
    'CBOE VIX': '^VIX',
    'US 10Y Yield': '^TNX',
    'Brent Crude': 'BZ=F',
    'WTI Crude': 'CL=F',
    'EUR/USD': 'EURUSD=X',
    'Bitcoin (BTC)': 'BTC-USD',
    'Ethereum (ETH)': 'ETH-USD'
}

def fetch_all():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
    }
    results = {}
    today_str = datetime.now().strftime('%d/%m/%Y')

    for name, sym in SYMBOLS.items():
        url = f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}?interval=1d&range=1d"
        try:
            req = urllib.request.Request(url, headers=headers)
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

def format_greek(val, decimals=2):
    s = f"{val:.{decimals}f}"
    parts = s.split('.')
    # Add thousands dot
    int_part = "{:,}".format(int(parts[0])).replace(',', '.')
    return f"{int_part},{parts[1]}"

def print_markdown_table(data):
    print("## 📊 DASHBOARD\n")
    print("| Δείκτης | Τιμή | Μεταβολή | Ημ. αναφοράς |")
    print("|---|---|---|---|")
    for name, item in data.items():
        p = item['price']
        c = item['change']
        prefix = "$" if 'Crude' in name or 'BTC' in name or 'ETH' in name else ""
        suffix = "%" if 'Yield' in name or 'VIX' in name else ""
        sign = "+" if c > 0 else ""

        p_str = f"{prefix}{format_greek(p)}{suffix}"
        c_str = f"{sign}{format_greek(c)}%"
        print(f"| **{name}** | {p_str} | {c_str} | {item['date']} |")

if __name__ == '__main__':
    data = fetch_all()
    if '--json' in sys.argv:
        print(json.dumps(data, indent=2))
    else:
        print_markdown_table(data)
