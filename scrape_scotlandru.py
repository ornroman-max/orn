#!/usr/bin/env python3
import csv
import hashlib
import re
import sys
from pathlib import Path
from urllib.parse import urlparse
import xml.etree.ElementTree as ET

from playwright.sync_api import sync_playwright

SITEMAP_INDEX = "https://scotlandru.com/sitemap_index.xml"
OUTPUT_DIR = Path("scotlandru_pages")
TIMEOUT_MS = 60000
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"


def normalize_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


def find_urls_in_sitemap(root: ET.Element):
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    if root.tag.endswith("sitemapindex"):
        return [loc.text.strip() for loc in root.findall("sm:sitemap/sm:loc", ns) if loc.text]
    if root.tag.endswith("urlset"):
        return [loc.text.strip() for loc in root.findall("sm:url/sm:loc", ns) if loc.text]
    return []


def fetch_xml_via_browser_request(context, url: str) -> ET.Element:
    response = context.request.get(url, timeout=TIMEOUT_MS)
    if not response.ok:
        raise RuntimeError(f"HTTP {response.status} for {url}")
    return ET.fromstring(response.text())


def collect_page_urls(context, sitemap_index_url: str):
    index_root = fetch_xml_via_browser_request(context, sitemap_index_url)
    sitemap_urls = find_urls_in_sitemap(index_root)

    pages = []
    for sitemap_url in sitemap_urls:
        try:
            sitemap_root = fetch_xml_via_browser_request(context, sitemap_url)
            pages.extend(find_urls_in_sitemap(sitemap_root))
        except Exception as exc:
            print(f"WARN: failed to parse sitemap {sitemap_url}: {exc}", file=sys.stderr)

    seen = set()
    unique = []
    for page_url in pages:
        if page_url.startswith("https://scotlandru.com") and page_url not in seen:
            seen.add(page_url)
            unique.append(page_url)
    return unique


def file_stem_from_url(url: str):
    parsed = urlparse(url)
    path = parsed.path.strip("/") or "home"
    safe = re.sub(r"[^a-zA-Z0-9_-]+", "_", path)[:80].strip("_") or "page"
    suffix = hashlib.md5(url.encode("utf-8")).hexdigest()[:8]
    return f"{safe}_{suffix}"


def extract_page_text_via_browser(page, url: str) -> str:
    response = page.goto(url, wait_until="networkidle", timeout=TIMEOUT_MS)
    if response is not None and not response.ok:
        raise RuntimeError(f"HTTP {response.status} for {url}")

    body_text = page.locator("body").inner_text(timeout=TIMEOUT_MS)
    return normalize_text(body_text)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent=USER_AGENT)
        page = context.new_page()

        try:
            urls = collect_page_urls(context, SITEMAP_INDEX)

            with (OUTPUT_DIR / "urls.txt").open("w", encoding="utf-8") as urls_file:
                for url in urls:
                    urls_file.write(url + "\n")

            with (OUTPUT_DIR / "mapping.csv").open("w", encoding="utf-8", newline="") as mapping_file:
                writer = csv.writer(mapping_file)
                writer.writerow(["url", "file"])

                for i, url in enumerate(urls, 1):
                    try:
                        text = extract_page_text_via_browser(page, url)
                    except Exception as exc:
                        text = f"ERROR: {exc}"

                    filename = f"{i:04d}_{file_stem_from_url(url)}.txt"
                    (OUTPUT_DIR / filename).write_text(text + "\n", encoding="utf-8")
                    writer.writerow([url, filename])
                    print(f"[{i}/{len(urls)}] {url} -> {filename}")

            print(f"Done. Saved {len(urls)} pages to {OUTPUT_DIR}")
        finally:
            context.close()
            browser.close()


if __name__ == "__main__":
    main()
