from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import Sitemap

from .the_portugal_news import ThePortugalNewsParser


class PT(metaclass=PublisherGroup):
    default_language = "pt"

    ThePortugalNews = Publisher(
        name="The Portugal News",
        domain="https://www.theportugalnews.com/",
        parser=ThePortugalNewsParser,
        sources=[
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-en.xml")),
                languages={"en"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-de.xml")),
                languages={"de"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-nl.xml")),
                languages={"nl"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-fr.xml")),
                languages={"fr"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-es.xml")),
                languages={"es"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-it.xml")),
                languages={"it"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-se.xml")),
                languages={"se"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-ru.xml")),
                languages={"ru"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-zh.xml")),
                languages={"zh"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-tr.xml")),
                languages={"tr"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-pt.xml")),
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-ar.xml")),
                languages={"ar"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-he.xml")),
                languages={"he"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-pl.xml")),
                languages={"pl"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-fi.xml")),
                languages={"fi"},
            ),
            Sitemap(
                "https://www.theportugalnews.com/sitemap-news.xml",
                sitemap_filter=inverse(regex_filter("news-br.xml")),
                languages={"br"},
            ),
        ],
    )
