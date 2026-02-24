from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin
from app.scrapers.base import BaseScraper


class CDSCOScraper(BaseScraper):
    def __init__(self):
        super().__init__("CDSCO", "https://cdsco.gov.in")
        self.authority_country = "India"
        self.circulars_url = "https://cdsco.gov.in/opencms/opencms/en/Notifications/Circulars/"

    def scrape(self) -> List[Dict[str, Any]]:
        updates: List[Dict[str, Any]] = []
        page = self.fetch_page(self.circulars_url)
        if not page:
            return updates

        table = page.find("table")
        if not table:
            return updates

        rows = table.find_all("tr")
        for row in rows[1:21]:
            cols = row.find_all("td")
            if len(cols) < 3:
                continue

            title = cols[1].get_text(strip=True)
            date_str = cols[2].get_text(strip=True)
            link = row.find("a")
            href = link.get("href") if link else ""

            if not title or not href:
                continue

            try:
                published = datetime.strptime(date_str, "%Y-%b-%d")
            except Exception:
                published = datetime.utcnow()

            source_link = urljoin(self.base_url.rstrip("/") + "/", href)
            updates.append(
                {
                    "title": title,
                    "category": "Circular",
                    "published_date": published,
                    "source_link": source_link,
                    "full_text": title,
                    "short_summary": title[:220],
                }
            )

        return updates
