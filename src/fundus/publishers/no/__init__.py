from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .dagbladet import DagbladetParser
from .nettavisen import NettavisenParser
from .nrk import NRKParser
from .verdensgang import VerdensGangParser


class NO(metaclass=PublisherGroup):
    default_language = "no"

    VerdensGang = Publisher(
        name="Verdens Gang",
        domain="https://www.vg.no/",
        parser=VerdensGangParser,
        sources=[
            Sitemap(
                "https://www.vg.no/sitemap.xml",
                sitemap_filter=inverse(regex_filter(r"vg\.no\/sitemaps/\d{4}\-\d{2}-articles.xml")),
                reverse=True,
            ),
            NewsMap("https://www.vg.no/sitemap/files/articles-48hrs.xml"),
        ],
    )

    Dagbladet = Publisher(
        name="Dagbladet",
        domain="https://www.db.no/",
        parser=DagbladetParser,
        sources=[
            Sitemap("https://www.dagbladet.no/app/jw-api-proxy/sitemap/index/dagbladet.xml", reverse=True),
            NewsMap("https://www.dagbladet.no/sitemap"),
        ],
    )

    Nettavisen = Publisher(
        name="Nettavisen",
        domain="https://www.nettavisen.no/",
        parser=NettavisenParser,
        sources=[
            RSSFeed("https://www.nettavisen.no/service/rich-rss"),
        ],
    )

    NRK = Publisher(
        name="Norsk rikskringkasting",
        domain="https://www.nrk.no/",
        parser=NRKParser,
        sources=[
            RSSFeed("https://www.nrk.no/norge/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/urix/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/sport/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/kultur/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/livsstil/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/viten/toppsaker.rss"),
            RSSFeed("https://www.nrk.no/dokumentar/toppsaker.rss"),
            Sitemap("https://www.nrk.no/sitemap.xml"),
        ],
    )
