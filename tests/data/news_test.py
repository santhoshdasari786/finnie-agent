"""News data layer: provider interface + registry, the Google News RSS provider, clustering and noise filtering.

Run:  .venv/bin/python -m pytest tests/data/news_test.py -v
No network: the provider takes an injectable `fetch(url) -> bytes`.

Live facts (checked 2026-11-14, not assumed): news.google.com/rss/search?q=...+when:7d&hl=en-IN&gl=IN&ceid=IN:en returns
RSS 2.0; each <item> has title ("Headline - Publisher"), link, guid, pubDate (RFC 822, GMT), description (HTML), and
<source> (the publisher name). It also returns aggregator pages ("... Stock Price, News, Quote & History - Yahoo! Finance"),
which are not news and are filtered as noise.
"""
from datetime import datetime, timezone

import pytest

from src.data.news.base import NEWS_PROVIDERS, NewsError, register_news_provider
from src.data.news.cluster import cluster_items, is_noise, normalize_title
from src.data.news.google_news import GoogleNewsProvider
from src.data.news.models import NewsItem

pytestmark = pytest.mark.asyncio


def item(title, publisher="Mint", day=12, hour=8, url=None):
    return NewsItem(title=title, publisher=publisher, url=url or f"https://news.example/{abs(hash(title + publisher))}",
                    published_at=datetime(2026, 11, day, hour, 0, tzinfo=timezone.utc))


# ================================================================ the registry
async def test_google_news_is_registered_after_import():
    assert NEWS_PROVIDERS["google_news"] is GoogleNewsProvider

async def test_a_second_provider_with_the_same_name_is_refused():
    with pytest.raises(ValueError):
        register_news_provider("google_news")(type("X", (), {}))

async def test_a_new_provider_can_be_attached_by_name():
    @register_news_provider("unit_test_provider")
    class P: ...
    try:
        assert NEWS_PROVIDERS["unit_test_provider"] is P
    finally:
        NEWS_PROVIDERS.pop("unit_test_provider")


# ================================================================ the model
async def test_a_news_item_holds_what_the_agent_needs():
    i = item("Infosys wins a deal")
    assert (i.title, i.publisher) == ("Infosys wins a deal", "Mint") and i.published_at.tzinfo is not None


# ================================================================ the Google News provider
FEED = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0"><channel><title>"Infosys when:7d" - Google News</title>
<item><title>Six researchers win Infosys Science Foundation prizes for 2026 - The Hindu</title>
 <link>https://news.google.com/rss/articles/AAA?oc=5</link><guid>AAA</guid>
 <pubDate>Thu, 12 Nov 2026 08:54:11 GMT</pubDate>
 <description>&lt;a href="https://x"&gt;Six researchers&lt;/a&gt;&amp;nbsp;&amp;nbsp;&lt;font color="#6f6f6f"&gt;The Hindu&lt;/font&gt;</description>
 <source url="https://www.thehindu.com">The Hindu</source></item>
<item><title>Infosys Limited (INFY) Stock Price, News, Quote &amp; History - Yahoo! Finance Canada</title>
 <link>https://news.google.com/rss/articles/BBB?oc=5</link><guid>BBB</guid>
 <pubDate>Thu, 12 Nov 2026 16:53:50 GMT</pubDate><description>x</description>
 <source url="https://ca.finance.yahoo.com">Yahoo! Finance Canada</source></item>
<item><title>3 AI Stocks Bought by FIIs - Equitymaster</title>
 <link>https://news.google.com/rss/articles/CCC?oc=5</link><guid>CCC</guid>
 <pubDate>Wed, 11 Nov 2026 10:51:01 GMT</pubDate><description>x</description>
 <source url="https://www.equitymaster.com">Equitymaster</source></item>
<item><title>No date on this one - Mint</title><link>https://news.google.com/rss/articles/DDD</link>
 <source url="https://mint.com">Mint</source></item>
<item><link>https://news.google.com/rss/articles/EEE</link><pubDate>Wed, 11 Nov 2026 10:51:01 GMT</pubDate></item>
</channel></rss>""".encode()


def provider(feed=FEED, urls=None):
    def fetch(url):
        if urls is not None:
            urls.append(url)
        return feed
    return GoogleNewsProvider(fetch=fetch)

async def test_the_feed_becomes_news_items():
    items = await provider().search("Infosys", days=7, limit=10)
    assert [i.publisher for i in items] == ["The Hindu", "Yahoo! Finance Canada", "Equitymaster"]

async def test_the_publisher_suffix_is_removed_from_the_title():
    items = await provider().search("Infosys", days=7, limit=10)
    assert items[0].title == "Six researchers win Infosys Science Foundation prizes for 2026"

async def test_html_entities_in_titles_are_decoded():
    items = await provider().search("Infosys", days=7, limit=10)
    assert items[1].title == "Infosys Limited (INFY) Stock Price, News, Quote & History"

async def test_the_link_and_date_are_kept_and_the_date_is_utc():
    i = (await provider().search("Infosys", days=7, limit=10))[0]
    assert i.url == "https://news.google.com/rss/articles/AAA?oc=5"
    assert i.published_at == datetime(2026, 11, 12, 8, 54, 11, tzinfo=timezone.utc)

async def test_items_without_a_date_or_a_title_are_skipped():
    titles = [i.title for i in await provider().search("Infosys", days=7, limit=10)]
    assert not any("No date" in t for t in titles) and len(titles) == 3

async def test_the_limit_is_applied():
    assert len(await provider().search("Infosys", days=7, limit=2)) == 2

async def test_the_request_asks_for_the_indian_edition_and_the_window():
    urls = []
    await provider(urls=urls).search("Infosys", days=7, limit=5)
    assert "when%3A7d" in urls[0] or "when:7d" in urls[0]
    assert "hl=en-IN" in urls[0] and "gl=IN" in urls[0] and "q=Infosys" in urls[0]

async def test_the_query_is_url_encoded():
    urls = []
    await provider(urls=urls).search("Tata Motors & Co", days=3, limit=5)
    assert " " not in urls[0] and "%26" in urls[0] and "when%3A3d" in urls[0]

async def test_an_empty_feed_gives_no_items():
    empty = b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>'
    assert await provider(empty).search("Infosys", days=7, limit=5) == []

async def test_garbage_is_a_news_error_not_a_crash():
    with pytest.raises(NewsError):
        await provider(b"this is not xml").search("Infosys", days=7, limit=5)

async def test_a_failing_fetch_is_a_news_error():
    def boom(url):
        raise OSError("network down")
    with pytest.raises(NewsError):
        await GoogleNewsProvider(fetch=boom).search("Infosys", days=7, limit=5)

async def test_a_blank_query_is_refused():
    with pytest.raises(ValueError):
        await provider().search("   ", days=7, limit=5)

async def test_the_provider_has_a_name_for_citations():
    assert GoogleNewsProvider.name == "Google News"


# ================================================================ noise
@pytest.mark.parametrize("title", [
    "Infosys Limited (INFY) Stock Price, News, Quote & History", "INFY Historical Prices", "Infosys Stock Quote and Chart",
])
async def test_aggregator_pages_are_noise(title):
    assert is_noise(title)

@pytest.mark.parametrize("title", [
    "Infosys Q2 profit rises 5%", "Infosys share price rises 3% after results", "Why Infosys shares fell today",
    "Sensex ends higher as IT stocks rally",
])
async def test_real_headlines_are_not_noise(title):
    assert not is_noise(title)


# ================================================================ normalising and clustering
async def test_normalize_lowercases_and_drops_punctuation_and_the_suffix():
    assert normalize_title("TCS Q2 profit rises 5%! - Mint") == normalize_title("tcs q2 profit rises 5%")

async def test_normalize_keeps_a_hyphen_inside_a_word():
    assert "q2" in normalize_title("TCS Q2-FY27 results")

async def test_the_same_story_from_two_outlets_is_one_cluster():
    a = item("TCS Q2 profit rises 5%", "Mint")
    b = item("TCS Q2 profit rises 5%", "Economic Times", hour=9)
    clusters = cluster_items([a, b])
    assert len(clusters) == 1 and clusters[0].publishers == ["Economic Times", "Mint"] or \
        sorted(clusters[0].publishers) == ["Economic Times", "Mint"]

async def test_a_lightly_reworded_headline_joins_the_cluster():
    clusters = cluster_items([item("TCS Q2 profit rises 5%", "Mint"), item("TCS Q2 profit up 5%", "Hindu")])
    assert len(clusters) == 1

async def test_different_stories_stay_apart():
    clusters = cluster_items([item("TCS Q2 profit rises 5%"), item("Infosys wins a large European deal")])
    assert len(clusters) == 2

async def test_the_newest_item_represents_the_cluster():
    old = item("TCS Q2 profit rises 5%", "Mint", day=11)
    new = item("TCS Q2 profit rises 5%", "Hindu", day=12)
    assert cluster_items([old, new])[0].lead.publisher == "Hindu"

async def test_clusters_are_ordered_newest_first():
    older = item("Infosys wins a large European deal", day=10)
    newer = item("TCS Q2 profit rises 5%", day=12)
    assert [c.lead.title for c in cluster_items([older, newer])] == [newer.title, older.title]

async def test_a_cluster_counts_its_members():
    c = cluster_items([item("TCS Q2 profit rises 5%", "A"), item("TCS Q2 profit rises 5%", "B"), item("TCS Q2 profit rises 5%", "C")])
    assert len(c) == 1 and c[0].size == 3

async def test_a_higher_threshold_keeps_near_duplicates_apart():
    items = [item("TCS Q2 profit rises 5%"), item("TCS Q2 profit up 5%")]
    assert len(cluster_items(items, threshold=0.9)) == 2

async def test_an_empty_list_gives_no_clusters():
    assert cluster_items([]) == []

async def test_the_publisher_is_listed_once():
    c = cluster_items([item("TCS Q2 profit rises 5%", "Mint"), item("TCS Q2 profit rises 5%", "Mint", hour=10)])
    assert c[0].publishers == ["Mint"]

async def test_two_unrelated_short_titles_are_not_merged():
    assert len(cluster_items([item("Sensex up"), item("Nifty down")])) == 2


# ================================================================ more noise found on live data (2026-11-15)
@pytest.mark.parametrize("title", [
    "Infosys Share Price Prediction for Monday: 16 Nov 2026", "Infosys target price raised to 1,900", "5 stocks to buy this week",
    "Should you buy Infosys? Experts weigh in", "Is this multibagger stock a hot pick",
])
async def test_tips_and_predictions_are_noise(title):
    assert is_noise(title)

@pytest.mark.parametrize("publisher", ["Instagram", "instagram", "Facebook", "YouTube", "Reddit", "X", "TikTok", "LinkedIn"])
async def test_social_media_posts_are_noise(publisher):
    assert is_noise("Infosys is rethinking its plans for the year", publisher)

@pytest.mark.parametrize("publisher", ["Mint", "The Hindu", "Express Computer", "Xinhua"])
async def test_newspapers_are_not_noise(publisher):
    assert not is_noise("Infosys is rethinking its plans for the year", publisher)

async def test_a_rating_change_headline_is_still_news():
    assert not is_noise("Brokerage downgrades Infosys to hold after weak guidance", "Mint")


async def test_zero_width_characters_are_removed_from_titles():
    feed = FEED.replace(b"<title>Six researchers", "<title>\u200bSix researchers".encode())
    items = await provider(feed).search("Infosys", days=7, limit=10)
    assert items[0].title == "Six researchers win Infosys Science Foundation prizes for 2026"
