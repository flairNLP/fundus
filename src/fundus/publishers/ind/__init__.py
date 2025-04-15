from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.ind.bhaskar import BhaskarParser
from fundus.publishers.ind.times_of_india import TimesOfIndiaParser
from fundus.scraping.url import NewsMap, RSSFeed


class IND(metaclass=PublisherGroup):
    default_language = "hi"

    TimesOfIndia = Publisher(
        name="Times Of India",
        domain="https://www.timesofindia.indiatimes.com",
        parser=TimesOfIndiaParser,
        sources=[
            NewsMap("https://timesofindia.indiatimes.com/sitemap/today", languages={"en"}),
            NewsMap("https://timesofindia.indiatimes.com/sitemap/yesterday", languages={"en"}),
            RSSFeed("https://timesofindia.indiatimes.com/rssfeedstopstories.cms", languages={"en"}),
            RSSFeed("https://timesofindia.indiatimes.com/rssfeedmostrecent.cms", languages={"en"}),
        ],
    )

    Bhaskar = Publisher(
        name="Dainik Bhaskar",
        domain="https://www.bhaskar.com/",
        parser=BhaskarParser,
        sources=[NewsMap("https://www.bhaskar.com/sitemaps-v1--sitemap-google-news-index.xml")],
    )
