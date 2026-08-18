from pathlib import Path

from scrapers.psx.client import classify_announcement_category, parse_company_announcements
from scrapers.psx.schemas import AnnouncementRecord, parse_announcements_from_company_html

FIXTURES = Path(__file__).parent.parent / "fixtures"
ANNOUNCEMENTS_SNIPPET = """
<div id="announcements">
  <div class="tabs__panels">
    <div class="tabs__panel" data-name="Financial Results">
      <table class="tbl"><tbody class="tbl__body">
        <tr>
          <td>Oct 29, 2024</td>
          <td>FINANCIAL RESULTS FOR THE NINE MONTHS ENDED SEPTEMBER 30, 2024</td>
          <td><a href="/download/document/241100.pdf">PDF</a></td>
        </tr>
      </tbody></table>
    </div>
    <div class="tabs__panel" data-name="Others">
      <table class="tbl"><tbody class="tbl__body">
        <tr>
          <td>Jan 15, 2024</td>
          <td>INSIDER BUYING BY DIRECTOR MR. JOHN DOE</td>
          <td><a href="/download/document/123456.pdf">PDF</a></td>
        </tr>
      </tbody></table>
    </div>
  </div>
</div>
"""


def test_parse_company_announcements_snippet() -> None:
    rows = parse_company_announcements(ANNOUNCEMENTS_SNIPPET, "ENGRO", "https://dps.psx.com.pk")
    assert len(rows) == 2
    assert rows[0]["category"] == "financial_result"
    assert rows[0]["pdf_url"] == "https://dps.psx.com.pk/download/document/241100.pdf"
    assert rows[1]["category"] == "insider_trade"


def test_classify_dividend() -> None:
    assert classify_announcement_category("Others", "Cash Dividend of Rs 10 per share") == "dividend"


def test_parse_announcements_from_company_html_validates() -> None:
    records = parse_announcements_from_company_html(
        ANNOUNCEMENTS_SNIPPET, "ENGRO", "https://dps.psx.com.pk"
    )
    assert all(isinstance(r, AnnouncementRecord) for r in records)
    assert records[0].symbol == "ENGRO"


def test_parse_live_engro_fixture() -> None:
    path = FIXTURES / "psx_company_engro_announcements.html"
    if not path.exists():
        return
    html = path.read_text(encoding="utf-8")
    records = parse_announcements_from_company_html(html, "ENGRO", "https://dps.psx.com.pk")
    assert len(records) > 5
    assert any(r.pdf_url for r in records)
