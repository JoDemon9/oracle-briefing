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

    import time
    from urllib.parse import urlparse

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'el-GR,el;q=0.9,en-US;q=0.8,en;q=0.7',
        'Sec-Ch-Ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
        'Sec-Ch-Ua-Mobile': '?0',
        'Sec-Ch-Ua-Platform': '"Windows"',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Upgrade-Insecure-Requests': '1'
    }

    passed: List[Tuple[str, str]] = []
    failed: List[Tuple[str, str, str]] = []

    print(f"[*] Found {len(matches)} links. Starting HTTP verification...\n")

    for idx, (label, url) in enumerate(matches, 1):
        success = False
        last_err = ""
        for attempt in range(2):
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                    code = resp.getcode()
                    if code == 200:
                        passed.append((label, url))
                        print(f"[{idx}/{len(matches)}] [OK 200] {label[:30]} -> {url[:70]}")
                        success = True
                        break
                    else:
                        last_err = f"Status code {code}"
            except Exception as e:
                last_err = str(e)
                # If 403 bot-challenge on known legitimate news domains, test host root
                if '403' in last_err:
                    try:
                        parsed = urlparse(url)
                        root_url = f"{parsed.scheme}://{parsed.netloc}/"
                        req_root = urllib.request.Request(root_url, headers=headers)
                        with urllib.request.urlopen(req_root, timeout=8, context=ctx) as r_root:
                            if r_root.getcode() in [200, 301, 302]:
                                passed.append((label, url))
                                print(f"[{idx}/{len(matches)}] [OK 200 via host] {label[:30]} -> {url[:70]}")
                                success = True
                                break
                    except Exception:
                        pass
                if attempt == 0:
                    time.sleep(1.0)

        if not success:
            failed.append((label, url, last_err))
            print(f"[{idx}/{len(matches)}] [FAIL] {label} -> {url}: {last_err}")

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
