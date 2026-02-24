#!/usr/bin/env python
"""Test guideline scrapers quickly"""
import sys
sys.path.insert(0, '.')

from app.scrapers.guidelines import (
    FDAGuidelineScraper,
    EMAGuidelineScraper,
    MHRAGuidelineScraper,
)

print("=" * 60)
print("Testing Guideline Scrapers")
print("=" * 60)

scrapers = [
    FDAGuidelineScraper(),
    EMAGuidelineScraper(),
    MHRAGuidelineScraper(),
]

for scraper in scrapers:
    print(f"\nTesting {scraper.authority_name} GuidelineScraper...")
    try:
        updates = scraper.scrape()
        print(f"✓ Scraped {len(updates)} guidelines")
        if updates:
            sample = updates[0]
            print(f"  Sample: {sample.get('title', 'N/A')[:60]}")
            print(f"  is_guideline: {sample.get('is_guideline', False)}")
            print(f"  Has full_text: {bool(sample.get('full_text'))}")
    except Exception as e:
        print(f"✗ Error: {e}")

print("\n" + "=" * 60)
print("Test Complete")
print("=" * 60)
