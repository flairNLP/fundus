from datetime import date

from fundus.publishers.base_objects import PublisherEnum, PublisherSpec
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.html import NewsMap, Sitemap

from .i_news import INewsParser
from .the_guardian import TheGuardianParser
from .the_independent import TheIndependentParser
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
