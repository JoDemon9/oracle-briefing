#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify-links.py — Rigorous HTTP link verifier for Oracle Briefing markdown files.
Exits with 0 if all links are 200 OK. Exits with 1 if any link fails (403, 404, error, etc.).
"""

import sys
import re
import ssl
import urllib.request
from typing import List, Tuple

sys.stdout.reconfigure(encoding='utf-8')

def check_file(filepath: str) -> bool:
    print(f"[*] Checking all URLs in: {filepath}")
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    matches = re.findall(r'\[([^\]]+)\]\((https?://[^\)]+)\)', content)
    if not matches:
        print("[!] Warning: No URLs found in file.")
        return True

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'el-GR,el;q=0.9,en;q=0.8'
    }

    passed: List[Tuple[str, str]] = []
    failed: List[Tuple[str, str, str]] = []

    print(f"[*] Found {len(matches)} links. Starting HTTP verification...\n")

    for idx, (label, url) in enumerate(matches, 1):
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                code = resp.getcode()
                if code == 200:
                    passed.append((label, url))
                    print(f"[{idx}/{len(matches)}] [OK 200] {label[:30]} -> {url[:70]}")
                else:
                    failed.append((label, url, f"Status code {code}"))
                    print(f"[{idx}/{len(matches)}] [FAIL {code}] {label} -> {url}")
        except Exception as e:
            failed.append((label, url, str(e)))
            print(f"[{idx}/{len(matches)}] [ERROR] {label} -> {url}: {e}")

    print("\n" + "="*50)
    print(f"VERIFICATION SUMMARY: {len(passed)}/{len(matches)} PASSED (100% required)")
    print("="*50)

    if failed:
        print(f"\n[FAIL] Found {len(failed)} non-working or blocked URLs:")
        for label, url, err in failed:
            print(f"  - [{label}]({url}): {err}")
        return False
    else:
        print("\n[SUCCESS] All URLs verified successfully with HTTP 200 OK!")
        return True

if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else 'briefings/oracle-briefing-2026-09-09.md'
    ok = check_file(target)
    sys.exit(0 if ok else 1)
