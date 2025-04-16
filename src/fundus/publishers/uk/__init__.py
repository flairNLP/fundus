from datetime import date, datetime

from dateutil.rrule import YEARLY, rrule

from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from ..shared import EuronewsParser
from .daily_mail import DailyMailParser
from .daily_star import DailyStarParser
from .evening_standard import EveningStandardParser
from .express import ExpressParser
from .i_news import INewsParser
from .metro import MetroParser
from .the_bbc import TheBBCParser
from .the_guardian import TheGuardianParser
from .the_independent import TheIndependentParser
from .the_mirror import TheMirrorParser
from .the_sun import TheSunParser
from .the_telegraph import TheTelegraphParser


class UK(metaclass=PublisherGroup):
    default_language = "en"

    TheGuardian = Publisher(
        name="The Guardian",
        domain="https://www.theguardian.com/",
        parser=TheGuardianParser,
        sources=[NewsMap("https://www.theguardian.com/sitemaps/news.xml")],
    )

    TheIndependent = Publisher(
        name="The Independent",
        domain="https://www.independent.co.uk/",
        parser=TheIndependentParser,
        sources=[
            Sitemap(
                "https://www.independent.co.uk/sitemap.xml",
                sitemap_filter=inverse(regex_filter(f"sitemap-articles")),
            ),
            NewsMap("https://www.independent.co.uk/sitemaps/googlenews"),
        ],
    )

    TheMirror = Publisher(
        name="The Mirror",
        domain="https://www.mirror.co.uk/",
        parser=TheMirrorParser,
        sources=[
            Sitemap("https://www.mirror.co.uk/sitemaps/sitemap_index.xml", reverse=True),
            NewsMap("https://www.mirror.co.uk/map_news.xml"),
        ],
    )

    TheTelegraph = Publisher(
        name="The Telegraph",
        domain="https://www.telegraph.co.uk/",
        parser=TheTelegraphParser,
        sources=[
            Sitemap("https://www.telegraph.co.uk/sitemap.xml"),
            NewsMap("https://www.telegraph.co.uk/custom/daily-news/sitemap.xml"),
        ],
        deprecated=True,
    )

    iNews = Publisher(
        name="i",
        domain="https://inews.co.uk/",
        parser=INewsParser,
        sources=[
            Sitemap("https://inews.co.uk/sitemap.xml"),
            NewsMap(
                f"https://inews.co.uk/sitemap.xml"
                f"?yyyy={date.today().year}&mm={str(date.today().month).zfill(2)}&dd={str(date.today().day).zfill(2)}",
            ),
        ],
    )

    EuronewsEN = Publisher(
        name="Euronews (EN)",
        domain="https://www.euronews.com/",
        parser=EuronewsParser,
        sources=[
            Sitemap("https://www.euronews.com/sitemaps/en/articles.xml"),
            NewsMap("https://www.euronews.com/sitemaps/en/latest-news.xml"),
        ],
    )

    DailyStar = Publisher(
        name="Daily Star",
        domain="https://www.dailystar.co.uk/",
        parser=DailyStarParser,
        sources=[
            Sitemap("https://www.dailystar.co.uk/sitemaps/sitemap_index.xml", reverse=True),
            NewsMap("https://www.dailystar.co.uk/map_news.xml"),
        ],
    )

    TheSun = Publisher(
        name="The Sun",
        domain="https://www.thesun.co.uk/",
        parser=TheSunParser,
        sources=[
            Sitemap("https://www.thesun.co.uk/sitemap.xml"),
            NewsMap("https://www.thesun.co.uk/news-sitemap.xml"),
        ],
        url_filter=regex_filter("sun-bingo|web-stories"),
    )

    DailyMail = Publisher(
        name="Daily Mail",
        domain="https://www.dailymail.co.uk/",
        parser=DailyMailParser,
        sources=[
            NewsMap("https://www.dailymail.co.uk/google-news-sitemap.xml"),
        ]
        + [
            Sitemap(f"https://www.dailymail.co.uk/sitemap-articles-year~{year.year}.xml")
            for year in rrule(YEARLY, dtstart=datetime(2021, 1, 1), until=datetime.today())
        ],
    )

    EveningStandard = Publisher(
        name="Evening Standard",
        domain="https://www.standard.co.uk/",
        parser=EveningStandardParser,
        sources=[
            Sitemap(
                "https://www.standard.co.uk/sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-articles|sitemap-recent")),
            ),
            RSSFeed("https://www.standard.co.uk/rss"),
        ],
    )

    Metro = Publisher(
        name="Metro",
        domain="https://metro.co.uk/",
        parser=MetroParser,
        sources=[
            NewsMap("https://metro.co.uk/news-sitemap.xml"),
            Sitemap("https://metro.co.uk/sitemap.xml"),
        ],
    )

    Express = Publisher(
        name="Daily Express",
        domain="https://www.express.co.uk/",
        parser=ExpressParser,
        sources=[
            NewsMap("https://www.express.co.uk/googlenews.xml"),
            Sitemap("https://www.express.co.uk/sitemap.xml"),
        ],
    )

    BBC = Publisher(
        name="The BBC",
        domain="https://www.bbc.co.uk/",
        parser=TheBBCParser,
        sources=[
            NewsMap("https://www.bbc.co.uk/sitemaps/https-index-uk-news.xml"),
            Sitemap("https://www.bbc.co.uk/sitemaps/https-index-com-archive.xml", reverse=True),
        ],
        url_filter=regex_filter("video|live"),
    )
