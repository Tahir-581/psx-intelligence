"""Unit tests for RSS news parser."""

from scrapers.news.rss import parse_feed_entries

SAMPLE_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Test</title>
    <item>
      <title>ENGRO profit rises 20%</title>
      <link>https://example.com/engro-profit</link>
      <pubDate>Mon, 01 Jan 2024 12:00:00 GMT</pubDate>
      <description>Engro Corporation announced strong quarterly results.</description>
    </item>
  </channel>
</rss>"""


def test_parse_feed_entries():
    articles = parse_feed_entries("business_recorder", "http://test", SAMPLE_RSS)
    assert len(articles) == 1
    assert articles[0].headline == "ENGRO profit rises 20%"
    assert articles[0].source == "business_recorder"
