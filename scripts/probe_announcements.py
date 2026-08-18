#!/usr/bin/env python3
"""Probe PSX announcements endpoints."""
import httpx
import re
from bs4 import BeautifulSoup

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}

paths = [
    "/announcements/ENGRO",
    "/announcements/companies",
    "/company/ENGRO",
]

for path in paths:
    r = httpx.get(f"https://dps.psx.com.pk{path}", headers=headers, timeout=60)
    print(f"\n=== {path} {r.status_code} ===")
    soup = BeautifulSoup(r.text, "lxml")
    for sel in [".tbl__body tr", "table tr", ".announcements__item", "li"]:
        els = soup.select(sel)
        if els and len(els) > 2:
            print(f"  {sel}: {len(els)} items")
            print(f"  sample: {els[0].get_text(' ', strip=True)[:150]}")

# Try JSON endpoints
json_paths = [
    "/announcements/company/ENGRO.json",
    "/announcements/ENGRO.json",
    "/api/v1/announcements/ENGRO",
    "/announcements/list/ENGRO",
    "/announcements?company=ENGRO",
]
for path in json_paths:
    r = httpx.get(
        f"https://dps.psx.com.pk{path}",
        headers={**headers, "Accept": "application/json"},
        timeout=30,
    )
    ct = r.headers.get("content-type", "")
    if r.status_code == 200 and "json" in ct:
        print(f"\nJSON HIT: {path}")
        print(r.text[:800])

# Search scripts in announcements page
r = httpx.get("https://dps.psx.com.pk/announcements/ENGRO", headers=headers, timeout=60)
urls = sorted(set(re.findall(r'["\'](/[^"\']+)["\']', r.text)))
ann = [u for u in urls if "ann" in u.lower() or "notice" in u.lower() or "pdf" in u.lower()]
print("\nURL patterns:", ann[:30])

scripts = re.findall(r'src="([^"]+\.js)"', r.text)
print("\nJS bundles:", scripts[:5])
for js in scripts[:3]:
    if js.startswith("/"):
        jr = httpx.get(f"https://dps.psx.com.pk{js}", headers=headers, timeout=60)
        hits = re.findall(r"/announcements/[a-zA-Z0-9_/{}/-]+", jr.text)
        if hits:
            print(f"  {js}:", sorted(set(hits))[:15])

# brute force common API patterns
for suffix in ["", "/list", "/all", "/recent", "/data"]:
    for fmt in [f"/announcements/ENGRO{suffix}", f"/announcement/ENGRO{suffix}"]:
        try:
            jr = httpx.get(
                f"https://dps.psx.com.pk{fmt}",
                headers={**headers, "X-Requested-With": "XMLHttpRequest"},
                timeout=15,
            )
            if jr.status_code == 200 and jr.text.strip().startswith(("{", "[")):
                print(f"XHR JSON: {fmt} -> {jr.text[:300]}")
        except Exception:
            pass
