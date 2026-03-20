from typing import List, Dict, Any
from datetime import datetime
from urllib.parse import urljoin
import re
import time
from app.scrapers.base import BaseScraper


class NMPAScraper(BaseScraper):
    def __init__(self):
        super().__init__("NMPA", "https://www.nmpa.gov.cn")
        self.authority_country = "China"
        self.announcements_url = "https://www.nmpa.gov.cn/xxgk/ggtg/"
        # Fallback list of NMPA mirror/alternative URLs
        self.fallback_urls = [
            "https://www.nmpa.gov.cn/xxgk/ggtg/hzhpggtg/",  # Alternative path
            "https://www.nmpa.gov.cn/xxgk/ggtg/jhpggtg/",    # Another section
        ]
        self.session = self._create_session()

    def _create_session(self):
        """Create requests session with connection pooling and retries"""
        import requests
        from requests.adapters import HTTPAdapter
        from urllib3.util.retry import Retry
        
        session = requests.Session()
        
        # Retry strategy for slow/flaky connections
        retry_strategy = Retry(
            total=3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
            backoff_factor=2  # 2s, 4s, 8s delays for server errors
        )
        
        adapter = HTTPAdapter(
            max_retries=retry_strategy,
            pool_connections=10,
            pool_maxsize=10
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session

    def scrape(self) -> List[Dict[str, Any]]:
        """
        Scrape NMPA announcements with fallback URLs and error recovery
        
        Note: NMPA server frequently returns 502 Bad Gateway errors
        This scraper retries with exponential backoff and falls back to alternatives
        """
        updates: List[Dict[str, Any]] = []
        
        print(f"[NMPA] Starting NMPA scraper")
        
        # Try primary URL first, then fallback URLs
        urls_to_try = [self.announcements_url] + self.fallback_urls
        
        for url_idx, url in enumerate(urls_to_try):
            print(f"[NMPA] Attempt {url_idx + 1}/{len(urls_to_try)}: {url}")
            
            try:
                print(f"[NMPA] Fetching with 60s timeout and retry logic...")
                
                # Fetch with longer timeout for slow/problematic servers
                response = self.session.get(
                    url,
                    headers=self.headers,
                    timeout=60,  # 60 second timeout
                    allow_redirects=True
                )
                
                print(f"[NMPA] HTTP Status: {response.status_code}")
                print(f"[NMPA] Final URL: {response.url}")
                print(f"[NMPA] Content length: {len(response.text)} bytes")
                
                # If server returns 502/503, it's temporarily down - try next URL
                if response.status_code in [502, 503]:
                    print(f"[NMPA] Server error {response.status_code} - trying next URL...")
                    continue
                
                if response.status_code != 200:
                    print(f"[NMPA] Warning: Got status {response.status_code}")
                    continue
                
                if len(response.text) < 100:
                    print(f"[NMPA] Warning: Response too short ({len(response.text)} bytes) - trying next URL...")
                    continue
                
                response.raise_for_status()
                response.encoding = response.apparent_encoding or 'utf-8'
                
                from bs4 import BeautifulSoup
                page = BeautifulSoup(response.text, "lxml")
                
                print(f"[NMPA] Successfully parsed HTML")
                
                # Enhanced link extraction
                found_count = 0
                for link in page.find_all("a", href=True):
                    href = link.get("href", "").strip()
                    
                    # Skip invalid hrefs
                    if not href or href.startswith("javascript"):
                        continue
                    
                    # Construct full URL
                    if href.startswith("http"):
                        source_link = href
                    else:
                        source_link = urljoin(self.base_url.rstrip("/") + "/", href.lstrip("/"))
                    
                    # Filter for announcement pages
                    if "/xxgk/ggtg/" not in source_link or not source_link.endswith(".html"):
                        continue
                    
                    title = link.get_text(strip=True)
                    if not title or len(title) < 3:
                        continue
                    
                    # Extract date from parent context
                    parent_text = link.parent.get_text(" ", strip=True) if link.parent else ""
                    date_match = re.search(r"(\d{4}[-/]\d{2}[-/]\d{2})", parent_text)
                    
                    if date_match:
                        date_str = date_match.group(1).replace("/", "-")
                        try:
                            published = datetime.strptime(date_str, "%Y-%m-%d")
                        except Exception:
                            published = datetime.utcnow()
                    else:
                        published = datetime.utcnow()
                    
                    updates.append({
                        "title": title[:200],
                        "category": "Notice",
                        "published_date": published,
                        "source_link": source_link,
                        "full_text": title,
                        "short_summary": title[:220],
                    })
                    
                    found_count += 1
                    if len(updates) >= 20:
                        break
                
                if found_count > 0:
                    print(f"[NMPA] Successfully found {found_count} announcements from {url}")
                    return updates
                else:
                    print(f"[NMPA] No valid links found in {url} - trying next URL...")
                    continue
                    
            except requests.exceptions.Timeout as e:
                print(f"[NMPA] Timeout from {url} after 60s - server may be down")
                continue
            except requests.exceptions.ConnectionError as e:
                print(f"[NMPA] Connection error from {url}: {e}")
                continue
            except Exception as e:
                print(f"[NMPA] Error from {url}: {e}")
                continue
        
        # If all URLs failed, return empty with explanation
        print(f"[NMPA] All URLs failed. NMPA server may be experiencing issues (502 Bad Gateway is common)")
        print(f"[NMPA] The scraper will retry on next scheduled run")
        return updates

