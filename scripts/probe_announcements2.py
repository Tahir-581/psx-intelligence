#!/usr/bin/env python3
import httpx
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
r = httpx.get("https://dps.psx.com.pk/announcements/ENGRO", headers=headers, timeout=60)
text = r.text
for marker in ["__NUXT__", "__NEXT", "window.", "announcements", "ANNOUNCEMENT", "pucars", "PUCARS"]:
    idx = text.lower().find(marker.lower())
    if idx >= 0:
        print(f"{marker} at {idx}: {text[idx:idx+200]}")

# try POST endpoints
client = httpx.Client(headers=headers, timeout=30)
posts = [
    ("/announcements/companies", {"symbol": "ENGRO"}),
    ("/announcements/companies", {"company": "ENGRO"}),
    ("/announcements/search", {"symbol": "ENGRO"}),
]
for path, body in posts:
    for as_json in [True, False]:
        try:
            if as_json:
                resp = client.post(f"https://dps.psx.com.pk{path}", json=body)
            else:
                resp = client.post(f"https://dps.psx.com.pk{path}", data=body)
            ct = resp.headers.get("content-type", "")
            if resp.status_code < 400 and ("json" in ct or resp.text.strip().startswith(("{", "["))):
                print(f"POST {path} json={as_json}: {resp.status_code} {resp.text[:400]}")
        except Exception as e:
            print(f"POST {path} err: {e}")

# try www.psx.com.pk
for url in [
    "https://www.psx.com.pk/psx/xml-files/company-announcements.xml",
    "https://dps.psx.com.pk/static/js/app.js",
]:
    try:
        resp = client.get(url)
        print(f"\n{url}: {resp.status_code} len={len(resp.text)}")
        if "announce" in resp.text.lower():
            hits = re.findall(r'["\'](/[^"\']*announce[^"\']*)["\']', resp.text, re.I)
            print("hits", sorted(set(hits))[:20])
    except Exception as e:
        print(url, e)
