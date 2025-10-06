import requests
from bs4 import BeautifulSoup
import json
import time
import datetime
from urllib.parse import urlparse
import os

def scrape_page(url):
    headers = {"User-Agent": "Mozilla/5.0"}
    print(f"🕸 Scraping {url} ...")
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    text = " ".join([t.get_text(strip=True) for t in soup.find_all(["p","h1","h2","h3","h4","h5"])])
    links = [a["href"] for a in soup.find_all("a", href=True)]
    images = [img["src"] for img in soup.find_all("img", src=True)]

    data = {
        "url": url,
        "title": soup.title.string if soup.title else "No Title",
        "text_preview": text[:500],
        "links_found": links[:15],
        "images_found": images[:10],
        "timestamp": datetime.datetime.utcnow().isoformat()
    }

    os.makedirs("data", exist_ok=True)
    domain = urlparse(url).netloc.replace(".", "_")
    filename = f"data/{domain}_{int(time.time())}.json"

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"✅ Saved: {filename}")

if __name__ == "__main__":
    urls = [
        "https://www.python.org/",
        "https://example.com"
    ]
    for url in urls:
        try:
            scrape_page(url)
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error scraping {url}: {e}")
