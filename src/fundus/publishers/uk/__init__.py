from datetime import date, datetime

from dateutil.rrule import YEARLY, rrule

from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from ..shared import EuronewsParser
from .daily_mail import DailyMailParser
from .daily_star import DailyStarParser
from .evening_standard import EveningStandardParser
from .i_news import INewsParser
from .the_guardian import TheGuardianParser
from .the_independent import TheIndependentParser
from .the_mirror import TheMirrorParser
from .the_sun import TheSunParser
from .the_telegraph import TheTelegraphParser


class UK(PublisherEnum):
    TheGuardian = PublisherSpec(
        name="The Guardian",
        domain="https://www.theguardian.com/",
        sources=[NewsMap("https://www.theguardian.com/sitemaps/news.xml")],
        parser=TheGuardianParser,
    )

    TheIndependent = PublisherSpec(
        name="The Independent",
        domain="https://www.independent.co.uk/",
        sources=[
            Sitemap(
                "https://www.independent.co.uk/sitemap.xml", sitemap_filter=inverse(regex_filter(f"sitemap-articles"))
            ),
            NewsMap("https://www.independent.co.uk/sitemaps/googlenews"),
        ],
        parser=TheIndependentParser,
    )

    TheMirror = PublisherSpec(
        name="The Mirror",
        domain="https://www.mirror.co.uk/",
        sources=[
            Sitemap("https://www.mirror.co.uk/sitemaps/sitemap_index.xml", reverse=True),
            NewsMap("https://www.mirror.co.uk/map_news.xml"),
        ],
        parser=TheMirrorParser,
    )

    TheTelegraph = PublisherSpec(
        name="The Telegraph",
        domain="https://www.telegraph.co.uk/",
        sources=[
            Sitemap("https://www.telegraph.co.uk/sitemap.xml"),
            NewsMap("https://www.telegraph.co.uk/custom/daily-news/sitemap.xml"),
        ],
        parser=TheTelegraphParser,
    )

    iNews = PublisherSpec(
        name="i",
        domain="https://inews.co.uk/",
        sources=[
            Sitemap("https://inews.co.uk/sitemap.xml"),
            NewsMap(
                f"https://inews.co.uk/sitemap.xml"
                f"?yyyy={date.today().year}&mm={str(date.today().month).zfill(2)}&dd={str(date.today().day).zfill(2)}"
            ),
        ],
        parser=INewsParser,
    )

    EuronewsEN = PublisherSpec(
        name="Euronews (EN)",
        domain="https://www.euronews.com/",
        sources=[
            Sitemap("https://www.euronews.com/sitemaps/en/articles.xml"),
            NewsMap("https://www.euronews.com/sitemaps/en/latest-news.xml"),
        ],
        parser=EuronewsParser,
    )

    DailyStar = PublisherSpec(
        name="Daily Star",
        domain="https://www.dailystar.co.uk/",
        sources=[
            Sitemap("https://www.dailystar.co.uk/sitemaps/sitemap_index.xml", reverse=True),
            NewsMap("https://www.dailystar.co.uk/map_news.xml"),
        ],
        parser=DailyStarParser,
    )

    TheSun = PublisherSpec(
        name="The Sun",
        domain="https://www.thesun.co.uk/",
        sources=[
            Sitemap("https://www.thesun.co.uk/sitemap.xml"),
            NewsMap("https://www.thesun.co.uk/news-sitemap.xml"),
        ],
        url_filter=regex_filter("sun-bingo|web-stories"),
        parser=TheSunParser,
    )

    DailyMail = PublisherSpec(
        name="Daily Mail",
        domain="https://www.dailymail.co.uk/",
        sources=[
            NewsMap("https://www.dailymail.co.uk/google-news-sitemap.xml"),
        ]
        + [
            Sitemap(f"https://www.dailymail.co.uk/sitemap-articles-year~{year.year}.xml")
            for year in rrule(YEARLY, dtstart=datetime(2021, 1, 1), until=datetime.today())
        ],
        parser=DailyMailParser,
    )

    EveningStandard = PublisherSpec(
        name="Evening Standard",
        domain="https://www.standard.co.uk/",
        sources=[
            Sitemap(
                "https://www.standard.co.uk/sitemap.xml",
                sitemap_filter=inverse(regex_filter("sitemap-articles|sitemap-recent")),
            ),
            RSSFeed("https://www.standard.co.uk/rss"),
        ],
        parser=EveningStandardParser,
    )
