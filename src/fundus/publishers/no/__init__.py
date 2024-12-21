from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.filter import inverse, regex_filter
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

from .dagbladet import DagbladetParser
from .nettavisen import NettavisenParser
from .nrk import NRKParser
from .verdensgang import VerdensGangParser


class NO(metaclass=PublisherGroup):
    VerdensGang = Publisher(
        name="Verdens Gang",
        domain="https://www.vg.no/",
        parser=VerdensGangParser,
        sources=[
            Sitemap(
                "https://www.vg.no/sitemap.xml",
                sitemap_filter=inverse(regex_filter(r"vg\.no\/sitemaps/\d{4}\-\d{2}-articles.xml")),
                reverse=True,
                languages={"no"},
            ),
            NewsMap("https://www.vg.no/sitemap/files/articles-48hrs.xml", languages={"no"}),
        ],
    )

    Dagbladet = Publisher(
        name="Dagbladet",
        domain="https://www.db.no/",
        parser=DagbladetParser,
        sources=[
            Sitemap(
                "https://www.dagbladet.no/app/jw-api-proxy/sitemap/index/dagbladet.xml", reverse=True, languages={"no"}
            ),
            NewsMap("https://www.dagbladet.no/sitemap", languages={"no"}),
        ],
    )

    Nettavisen = Publisher(
        name="Nettavisen",
        domain="https://www.nettavisen.no/",
        parser=NettavisenParser,
        sources=[
            RSSFeed("https://www.nettavisen.no/service/rich-rss", languages={"no"}),
        ],
    )

    NRK = Publisher(
        name="Norsk rikskringkasting",
        domain="https://www.nrk.no/",
        parser=NRKParser,
        sources=[
            RSSFeed("https://www.nrk.no/norge/toppsaker.rss", languages={"no"}),
            RSSFeed("https://www.nrk.no/urix/toppsaker.rss", languages={"no"}),
            RSSFeed("https://www.nrk.no/sport/toppsaker.rss", languages={"no"}),
            RSSFeed("https://www.nrk.no/kultur/toppsaker.rss", languages={"no"}),
            RSSFeed("https://www.nrk.no/livsstil/toppsaker.rss", languages={"no"}),
            RSSFeed("https://www.nrk.no/viten/toppsaker.rss", languages={"no"}),
            RSSFeed("https://www.nrk.no/dokumentar/toppsaker.rss", languages={"no"}),
            Sitemap("https://www.nrk.no/sitemap.xml", languages={"no"}),
        ],
    )
