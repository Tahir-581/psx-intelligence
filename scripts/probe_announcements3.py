#!/usr/bin/env python3
import httpx
from bs4 import BeautifulSoup
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
r = httpx.get("https://dps.psx.com.pk/company/ENGRO", headers=headers, timeout=60)
soup = BeautifulSoup(r.text, "lxml")
# tabs / sections
for a in soup.find_all("a", href=True):
    h = a["href"]
    if "announ" in h.lower() or "notice" in h.lower() or "result" in h.lower():
        print("link:", h, a.get_text(strip=True)[:50])

# all ids and classes with announ
for el in soup.find_all(True, class_=True):
    classes = " ".join(el.get("class", []))
    if "announ" in classes.lower() or "notice" in classes.lower():
        print("class:", classes, el.name)

text = r.text
# embedded json
for m in re.finditer(r'<script[^>]*>(.*?)</script>', text, re.S):
    s = m.group(1)
    if len(s) > 50 and ("ENGRO" in s or "announce" in s.lower()):
        print("script chunk:", s[:500])

# Try company announcements subpaths
for path in [
    "/company/ENGRO/announcements",
    "/company/ENGRO/notices",
    "/notices/ENGRO",
    "/company-announcements/ENGRO",
]:
    resp = httpx.get(f"https://dps.psx.com.pk{path}", headers=headers, timeout=30)
    print(path, resp.status_code, len(resp.text))
