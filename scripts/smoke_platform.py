#!/usr/bin/env python3
"""Smoke test for PSX Intelligence Platform endpoints."""

import sys

import httpx

BASE = "http://localhost:8000"


def check(path: str, expect: int = 200) -> bool:
    try:
        r = httpx.get(f"{BASE}{path}", timeout=10)
        ok = r.status_code == expect or (expect == 200 and r.status_code < 500)
        print(f"{'OK' if ok else 'FAIL'} {path} -> {r.status_code}")
        return ok
    except Exception as exc:
        print(f"FAIL {path} -> {exc}")
        return False


def main() -> int:
    checks = [
        "/health",
        "/market/summary",
        "/market/corporate-calendar",
        "/health/data",
        "/openapi.json",
    ]
    passed = sum(check(p) for p in checks)
    print(f"\n{passed}/{len(checks)} passed")
    return 0 if passed == len(checks) else 1


if __name__ == "__main__":
    sys.exit(main())
