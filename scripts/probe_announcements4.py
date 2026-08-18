#!/usr/bin/env python3
import httpx
from bs4 import BeautifulSoup
import re

headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"}
r = httpx.get("https://dps.psx.com.pk/company/ENGRO", headers=headers, timeout=60)
soup = BeautifulSoup(r.text, "lxml")

ann = soup.find(id="announcements")
if ann:
    print("announcements section found")
    print(ann.prettify()[:3000])
else:
    print("no #announcements id")

# search for announcement rows in company page
for sel in [
    "#announcements tr",
    "#announcements .row",
    ".announcements tr",
    ".announcement__item",
    "[id*='announce']",
]:
    els = soup.select(sel)
    if els:
        print(f"{sel}: {len(els)}")
        for e in els[:3]:
            print(" ", e.get_text(" ", strip=True)[:120])

# PDF links on company page
pdfs = [(a.get_text(strip=True)[:60], a["href"]) for a in soup.find_all("a", href=True) if ".pdf" in a["href"].lower() or "download" in a["href"].lower()]
print(f"\nPDF/download links: {len(pdfs)}")
for t, h in pdfs[:10]:
    print(f"  {t} -> {h}")

# Look for data attributes
for el in soup.find_all(attrs={"data-date": True})[:5]:
    print("data-date:", el)
