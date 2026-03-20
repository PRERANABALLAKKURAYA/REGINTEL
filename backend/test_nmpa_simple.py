import sys
sys.path.insert(0, '.')
from app.scrapers.nmpa import NMPAScraper

scraper = NMPAScraper()
updates = scraper.scrape()

print("Total updates:", len(updates))
if updates:
    for i, u in enumerate(updates[:3]):
        print("\nUpdate", i+1)
        print("Title:", u['title'][:80])
        print("Link:", u['source_link'])
else:
    print("No updates found")
