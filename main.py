#!/usr/bin/env python3
# main.py
# Fast search-based LinkedIn finder using DuckDuckGo (with Bing fallback).
# Usage:
#  python main.py --query "marketing director orlando" --max 50

import requests
from bs4 import BeautifulSoup
import time
import json
import argparse
import os
from urllib.parse import urlparse, parse_qs, unquote, urljoin
from datetime import datetime

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}
SLEEP_BETWEEN_REQUESTS = 2.0  # polite delay

def extract_links_from_duckduckgo(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        # DuckDuckGo sometimes wraps targets in /l/?kh=1&uddg=<encoded-url>
        if "/l/?" in href and "uddg=" in href:
            try:
                q = parse_qs(href.split("?",1)[1])
                if "uddg" in q:
                    decoded = unquote(q["uddg"][0])
                    links.append(decoded)
            except Exception:
                pass
        else:
            links.append(href)
    return links

def extract_links_from_bing(html):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for a in soup.select("li.b_algo h2 a"):
        href = a.get("href")
        if href:
            links.append(href)
    # Generic fallback links
    for a in soup.find_all("a", href=True):
        links.append(a["href"])
    return links

def keep_linkedin_links(urls):
    out = []
    seen = set()
    for u in urls:
        if not u:
            continue
        u = u.strip()
        # normalize possible relative URLs
        if u.startswith("/"):
            continue
        parsed = urlparse(u)
        netloc = parsed.netloc.lower()
        if "linkedin.com" in netloc:
            # normalize (drop tracking params)
            clean = parsed._replace(query="").geturl()
            if clean not in seen:
                seen.add(clean)
                out.append(clean)
    return out

def search_duckduckgo(query, page=1):
    # DuckDuckGo html interface supports simple queries. We'll request a single page.
    url = "https://duckduckgo.com/html/"
    params = {"q": query, "s": str((page-1)*30)}
    r = requests.post(url, headers=HEADERS, data=params, timeout=15)
    r.raise_for_status()
    return extract_links_from_duckduckgo(r.text)

def search_bing(query, page=1):
    url = f"https://www.bing.com/search"
    params = {"q": query, "first": str((page-1)*10)}
    r = requests.get(url, headers=HEADERS, params=params, timeout=15)
    r.raise_for_status()
    return extract_links_from_bing(r.text)

def run_query(query, max_results=50, use_bing_fallback=True):
    results = []
    page = 1
    while len(results) < max_results:
        try:
            links = search_duckduckgo(query, page=page)
        except Exception as e:
            # fallback to Bing if DuckDuckGo fails
            if use_bing_fallback:
                time.sleep(1)
                links = search_bing(query, page=page)
            else:
                print("Search failed:", e)
                break

        linkedin_links = keep_linkedin_links(links)
        for l in linkedin_links:
            if l not in results:
                results.append(l)
                if len(results) >= max_results:
                    break

        # if no new links found, stop
        if not links or page > 5:
            break
        page += 1
        time.sleep(SLEEP_BETWEEN_REQUESTS)
    return results

def save_results(query, results, out_dir="data"):
    os.makedirs(out_dir, exist_ok=True)
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    safeq = "".join(c if c.isalnum() or c in "-_" else "_" for c in query)[:80]
    filename = f"{out_dir}/linkedin_search_{safeq}_{ts}.json"
    payload = {
        "query": query,
        "timestamp_utc": ts,
        "count": len(results),
        "results": results
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)
    print("Saved", filename)
    return filename

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--query", "-q", required=True, help="Search query to find LinkedIn pages")
    p.add_argument("--max", "-m", type=int, default=50, help="Max LinkedIn links to collect")
    p.add_argument("--out", default="data", help="Output folder")
    p.add_argument("--no-bing-fallback", action="store_true", help="Disable Bing fallback")
    args = p.parse_args()

    results = run_query(args.query, max_results=args.max, use_bing_fallback=not args.no_bing_fallback)
    save_results(args.query, results, out_dir=args.out)

if __name__ == "__main__":
    main()
