import sys
sys.path.insert(0, '.')
from app.scrapers.nmpa import NMPAScraper

print("Testing NMPA scraper with 60s timeout and retry logic...")
scraper = NMPAScraper()
updates = scraper.scrape()

print(f"\nTotal updates: {len(updates)}")
if updates:
    for i, u in enumerate(updates[:3]):
        print(f"\nUpdate {i+1}")
        print(f"  Title: {u['title'][:70]}")
        print(f"  Link: {u['source_link']}")
else:
    print("No updates found")
