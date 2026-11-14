"""Polite phonedb.net scraper that turns a device page into a nested dict.

The result has the shape {"Introduction": {...}, "Display": {...}, ...}: one dict per
datasheet section, mapping the spec name to its raw text value.
"""
import time
from typing import Iterator
from urllib import robotparser

import requests
import truststore
from bs4 import BeautifulSoup

# phonedb.net does not send its intermediate certificate. Browsers and the OS trust store can fetch it,
# Python's bundled CA list cannot, so verify against the operating system's trust store instead of
# switching certificate verification off.
truststore.inject_into_ssl()

BASE = "https://phonedb.net"
USER_AGENT = "malena-graph-db (research/educational scraper)"
PAGE_SIZE = 29  # devices per list page on phonedb.net


class PhoneDbScraper:
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self.http = requests.Session()
        self.http.headers["User-Agent"] = USER_AGENT
        self.robots = robotparser.RobotFileParser()
        # fetched with requests (not urllib) so the same certificate store is used everywhere
        self.robots.parse(self.http.get(f"{BASE}/robots.txt", timeout=30).text.splitlines())

    def _get(self, url: str):
        if not self.robots.can_fetch(USER_AGENT, url):
            raise PermissionError(f"robots.txt disallows {url}")
        time.sleep(self.delay)
        response = self.http.get(url, timeout=30)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")

    def device_links(self) -> Iterator[str]:
        """Yield the relative URL of every device, page by page, until the list ends."""
        offset = 0
        while True:
            soup = self._get(f"{BASE}/index.php?m=device&s=list&filter={offset}")
            titles = soup.find_all("div", class_="content_block_title")
            if not titles:
                return
            for title in titles:
                if title.a and title.a.get("href"):
                    yield title.a["href"]
            offset += PAGE_SIZE

    def scrape_device(self, href: str) -> dict:
        return parse_device(self._get(f"{BASE}/{href}"))

    def scrape(self, limit: int) -> Iterator[dict]:
        for count, href in enumerate(self.device_links()):
            if count >= limit:
                return
            try:
                yield self.scrape_device(href)
            except Exception as error:  # keep going: one broken page should not stop a run
                print(f"skipped {href}: {error}")


def parse_device(soup: BeautifulSoup) -> dict:
    """Parse the datasheet table of one device page.

    Rows before the "Brief" header belong to the Introduction; every full-width header row
    starts a new section; rows with an empty key continue the previous value.
    """
    data: dict = {}
    intro: dict = {}
    seen_brief = False
    section_name = None
    section: dict = {}
    previous_key = None

    for row in soup.find_all("tr"):
        cells = row.find_all("td", recursive=False)

        if len(cells) == 1 and cells[0].has_attr("colspan"):
            heading = (
                cells[0].get_text(strip=True)
                .replace("Expand datasheet", "").replace("|Add to compare", "")
                .strip(":").strip()
            )
            if heading.lower().startswith("brief"):
                seen_brief = True
                section_name, section = "Introduction", dict(intro)
            elif seen_brief:
                if section_name and section:
                    data[section_name] = section
                section_name, section = heading, {}
            continue

        if len(cells) != 2:
            continue
        strong = cells[0].find("strong")
        key = (strong.get_text(strip=True) if strong else cells[0].get_text(strip=True)).rstrip(":").strip()
        value = cells[1].get_text(strip=True)
        target = intro if (not seen_brief and section_name is None) else section

        if key == "":
            if previous_key in target:
                target[previous_key] += f", {value}"
        else:
            target[key] = value
            previous_key = key

    if section_name:
        data[section_name] = section
    data.setdefault("Introduction", intro)
    return data
