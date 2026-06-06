from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.ca.canada_com import CanadaComParser
from fundus.publishers.ca.cbc_news import CBCNewsParser
from fundus.publishers.ca.financial_post import FinancialPostParser
from fundus.publishers.ca.globe_and_mail import TheGlobeAndMailParser
from fundus.publishers.ca.national_post import NationalPostParser
from fundus.publishers.ca.the_province import TheProvinceParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

# noinspection PyPep8Naming


class CA(metaclass=PublisherGroup):
    default_language = "en"

    CanadaCom = Publisher(
        name="Canada.com",
        domain="https://www.canada.com",
        parser=CanadaComParser,
        sources=[
            NewsMap("https://o.canada.com/sitemap-news.xml"),
            Sitemap("https://o.canada.com/sitemap-old.xml"),
            RSSFeed("https://o.canada.com/feed"),
        ],
    )

    CBCNews = Publisher(
        name="CBC News",
        domain="https://www.cbc.ca/",
        parser=CBCNewsParser,
        sources=[
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-topstories"),
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-world"),
            RSSFeed("https://www.cbc.ca/webfeed/rss/rss-canada"),
        ],
        request_header={"User-Agent": "Fundus/2.0"},
    )

    FinancialPost = Publisher(
        name="Financial Post",
        domain="https://financialpost.com",
        parser=FinancialPostParser,
        sources=[
            NewsMap("https://financialpost.com/sitemap-news.xml"),
            Sitemap("https://financialpost.com/sitemap-old.xml"),
            RSSFeed("https://financialpost.com/feed"),
        ],
    )

    TheGlobeAndMail = Publisher(
        name="The Globe and Mail",
        domain="https://www.theglobeandmail.com",
        parser=TheGlobeAndMailParser,
        sources=[
            NewsMap("https://www.theglobeandmail.com/arc/outboundfeeds/news-sitemap-index/?outputType=xml"),
            NewsMap("https://www.theglobeandmail.com/arc/outboundfeeds/sitemap-index/?outputType=xml"),
        ],
    )

    TheProvince = Publisher(
        name="The Province",
        domain="https://www.theprovince.com",
        parser=TheProvinceParser,
        sources=[
            NewsMap("https://theprovince.com/sitemap-news.xml"),
            Sitemap("https://theprovince.com/sitemap-old.xml"),
            RSSFeed("https://theprovince.com/feed"),
        ],
    )

    NationalPost = Publisher(
        name="National Post",
        domain="https://nationalpost.com",
        parser=NationalPostParser,
        sources=[
            NewsMap("https://nationalpost.com/sitemap-news.xml"),
            Sitemap("https://nationalpost.com/sitemap-old.xml"),
            RSSFeed("https://nationalpost.com/feed"),
        ],
    )
