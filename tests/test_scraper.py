from bs4 import BeautifulSoup

from malena.scraper import PAGE_SIZE, PhoneDbScraper, parse_device

DEVICE_PAGE = """
<table>
  <tr><td><strong>Model:</strong></td><td>Test Phone X</td></tr>
  <tr><td><strong>Device Category:</strong></td><td>Smartphone</td></tr>
  <tr><td colspan="2">Brief</td></tr>
  <tr><td colspan="2">Display Expand datasheet</td></tr>
  <tr><td><strong>Display Diagonal:</strong></td><td>155 mm, 6.1 inch</td></tr>
  <tr><td><strong>Resolution:</strong></td><td>720x1560</td></tr>
  <tr><td colspan="2">Power Supply</td></tr>
  <tr><td><strong>Battery:</strong></td><td>Li-ion</td></tr>
  <tr><td><strong></strong></td><td>built-in</td></tr>
  <tr><td><strong>Nominal Battery Capacity:</strong></td><td>6000 mAh battery</td></tr>
</table>
"""


def test_parse_device_sections():
    data = parse_device(BeautifulSoup(DEVICE_PAGE, "html.parser"))
    assert list(data) == ["Introduction", "Display", "Power Supply"]
    assert data["Introduction"] == {"Model": "Test Phone X", "Device Category": "Smartphone"}
    assert data["Display"] == {"Display Diagonal": "155 mm, 6.1 inch", "Resolution": "720x1560"}


def test_parse_device_continuation_row_extends_previous_value():
    data = parse_device(BeautifulSoup(DEVICE_PAGE, "html.parser"))
    assert data["Power Supply"]["Battery"] == "Li-ion, built-in"
    assert data["Power Supply"]["Nominal Battery Capacity"] == "6000 mAh battery"


def test_parse_device_without_brief_header_still_has_introduction():
    html = "<table><tr><td><strong>Model:</strong></td><td>Only Intro</td></tr></table>"
    assert parse_device(BeautifulSoup(html, "html.parser")) == {"Introduction": {"Model": "Only Intro"}}


class FakeScraper(PhoneDbScraper):
    """Serves list pages and device pages from memory instead of the network."""

    def __init__(self, pages):  # no network access, no robots.txt
        self.pages = pages
        self.requested = []

    def _get(self, url):
        self.requested.append(url)
        return BeautifulSoup(self.pages.get(url, ""), "html.parser")


def list_page(*hrefs):
    return "".join(f'<div class="content_block_title"><a href="{h}">{h}</a></div>' for h in hrefs)


def test_device_links_follow_pagination_until_the_list_ends():
    base = "https://phonedb.net/index.php?m=device&s=list&filter="
    scraper = FakeScraper({base + "0": list_page("a", "b"), base + str(PAGE_SIZE): list_page("c")})
    assert list(scraper.device_links()) == ["a", "b", "c"]


def test_scrape_respects_limit_and_skips_broken_pages(capsys):
    base = "https://phonedb.net/index.php?m=device&s=list&filter="
    scraper = FakeScraper({base + "0": list_page("a", "b", "c"), "https://phonedb.net/a": DEVICE_PAGE,
                           "https://phonedb.net/c": DEVICE_PAGE})

    def get(url):
        if url.endswith("/b"):
            raise RuntimeError("boom")
        return FakeScraper._get(scraper, url)

    scraper._get = get
    phones = list(scraper.scrape(limit=3))
    assert len(phones) == 2
    assert "skipped b" in capsys.readouterr().out
    assert len(list(scraper.scrape(limit=1))) == 1
