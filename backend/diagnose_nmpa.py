import requests
from bs4 import BeautifulSoup

url = "https://www.nmpa.gov.cn/xxgk/ggtg/hzhpggtg/jmhzphgtg/20260320095800150.html"

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

print(f"Fetching: {url}")
response = requests.get(url, headers=headers, timeout=10, allow_redirects=True)
print(f"Status: {response.status_code}")
print(f"Final URL: {response.url}")
print(f"Content length: {len(response.text)} bytes")
print(f"Encoding detected: {response.apparent_encoding}")

# Check what's in the HTML
soup = BeautifulSoup(response.text, 'lxml')
print(f"\n--- HTML Structure ---")
print(f"Title tag: {soup.title}")
print(f"Body content length: {len(soup.body.get_text()) if soup.body else 0}")

# Look for specific content patterns
divs = soup.find_all('div', limit=5)
print(f"First 5 divs: {[d.get('class') for d in divs]}")

# Check for scripts (JS)
scripts = soup.find_all('script')
print(f"\nNumber of script tags: {len(scripts)}")
if scripts:
    print(f"First script type: {scripts[0].get('type', 'unknown')}")

# Look for common content containers
article = soup.find('article')
main = soup.find('main')
content = soup.find(class_=['content', 'article-content', 'container'])
print(f"\narticle tag found: {article is not None}")
print(f"main tag found: {main is not None}")
print(f"content container found: {content is not None}")

# Print first 2000 chars of raw HTML
print(f"\n--- First 2000 chars of HTML ---")
print(response.text[:2000])
