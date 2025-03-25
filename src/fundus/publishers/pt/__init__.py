from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import regex_filter
from fundus.scraping.url import Sitemap

from .the_portugal_news import ThePortugalNewsParser


class PT(metaclass=PublisherGroup):
    ThePortugalNews = Publisher(
        name="Nine News",
        domain="https://www.9news.com.au/",
        parser=ThePortugalNewsParser,
        sources=[
            Sitemap("https://www.theportugalnews.com/sitemap.xml", sitemap_filter=regex_filter("category-pages")),
        ],
    )
