from abc import ABC, abstractmethod
from datetime import datetime
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
import re
import requests
import feedparser
from bs4 import BeautifulSoup

class BaseScraper(ABC):
    def __init__(self, authority_name: str, base_url: str):
        self.authority_name = authority_name
        self.authority_country = ""
        self.base_url = base_url
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def fetch_page(self, url: str) -> BeautifulSoup:
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            if not response.encoding or response.encoding.lower() == "iso-8859-1":
                response.encoding = response.apparent_encoding
            return BeautifulSoup(response.text, "lxml")
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None

    def parse_rss(self, feed_url: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        feed = self._fetch_and_parse_feed(feed_url)
        updates: List[Dict[str, Any]] = []

        for entry in feed.entries[:20]:
            published = datetime.utcnow()
            if hasattr(entry, "published_parsed") and entry.published_parsed:
                published = datetime(*entry.published_parsed[:6])
            elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                published = datetime(*entry.updated_parsed[:6])

            raw_link = getattr(entry, "link", "") or ""
            source_link = self._normalize_source_link(raw_link)
            print(f"[SCRAPER] {self.authority_name} source_link: {source_link}")

            if not source_link:
                # Skip entries without a valid, non-homepage link
                continue

            summary = getattr(entry, "summary", "") or ""
            updates.append(
                {
                    "title": entry.title,
                    "category": category or "Update",
                    "published_date": published,
                    "source_link": source_link,
                    "full_text": summary,
                    "short_summary": summary[:220] if summary else "",
                }
            )

        return updates

    def _fetch_and_parse_feed(self, feed_url: str):
        try:
            response = requests.get(feed_url, headers=self.headers, timeout=30)
            response.raise_for_status()
            content = response.content
        except requests.exceptions.SSLError as e:
            print(f"[SCRAPER] SSL error fetching {feed_url}: {e}")
            response = requests.get(feed_url, headers=self.headers, timeout=30, verify=False)
            response.raise_for_status()
            content = response.content
        except requests.RequestException as e:
            print(f"[SCRAPER] Error fetching {feed_url}: {e}")
            return feedparser.parse("")

        feed = feedparser.parse(content)
        if getattr(feed, "bozo", False) and not feed.entries:
            try:
                text = content.decode("utf-8", errors="ignore")
                text = re.sub(r"[\x00-\x08\x0B\x0C\x0E-\x1F]", "", text)
                feed = feedparser.parse(text.encode("utf-8"))
            except Exception as e:
                print(f"[SCRAPER] Feed parse cleanup failed for {feed_url}: {e}")

        if getattr(feed, "bozo", False):
            print(f"[SCRAPER] Feed parse warning for {feed_url}: {getattr(feed, 'bozo_exception', None)}")

        return feed

    def _normalize_source_link(self, link: str) -> Optional[str]:
        if not link:
            return None

        absolute = urljoin(self.base_url.rstrip("/") + "/", link.strip())
        parsed = urlparse(absolute)
        if not parsed.scheme or not parsed.netloc:
            return None

        base_parsed = urlparse(self.base_url)
        same_host = parsed.netloc.lower() == base_parsed.netloc.lower()
        is_homepage = parsed.path in ("", "/") and not parsed.query and not parsed.fragment

        if same_host and is_homepage:
            return None

        return absolute

    @abstractmethod
    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrapes the authority website and returns a list of update dictionaries.
        Each dictionary should contain:
        - title
        - category
        - published_date
        - source_link
        - full_text (optional initially)
        """
        pass
