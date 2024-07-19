from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.ind.times_of_india import TimesOfIndiaParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class IND(metaclass=PublisherGroup):
    TimesOfIndia = Publisher(
        name="Times Of India",
        domain="https://www.timesofindia.indiatimes.com",
        parser=TimesOfIndiaParser,
        sources=[
            Sitemap("https://timesofindia.indiatimes.com/sitemap/today"),
            Sitemap("https://timesofindia.indiatimes.com/sitemap/yesterday"),
            RSSFeed("https://timesofindia.indiatimes.com/rssfeedstopstories.cms"),
            RSSFeed("https://timesofindia.indiatimes.com/rssfeedmostrecent.cms"),
        ],
    )
