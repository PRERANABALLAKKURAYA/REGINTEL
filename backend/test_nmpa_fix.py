#!/usr/bin/env python3
"""Test NMPA scraper with redirect handling"""

from app.scrapers.nmpa import NMPAScraper

print("[TEST] Starting NMPA scraper test...")
scraper = NMPAScraper()

try:
    updates = scraper.scrape()
    print(f"[TEST] Found {len(updates)} updates from NMPA")
    
    for i, u in enumerate(updates[:3], 1):
        print(f"\n[UPDATE {i}]")
        print(f"  Title: {u['title'][:80]}")
        print(f"  Published: {u['published_date']}")
        print(f"  Link: {u['source_link']}")
        print(f"  Valid: {u['source_link'].startswith('https://www.nmpa.gov.cn')}")
        
except Exception as e:
    print(f"[ERROR] Test failed: {e}")
    import traceback
    traceback.print_exc()
