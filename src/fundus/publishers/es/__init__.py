import datetime

from dateutil.rrule import MONTHLY, rrule

from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.es.abc import ABCParser
from fundus.publishers.es.el_mundo import ElMundoParser
from fundus.publishers.es.el_pais import ElPaisParser
from fundus.publishers.es.la_vanguardia import LaVanguardiaParser
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap


class ES(metaclass=PublisherGroup):
    ElPais = Publisher(
        name="El País",
        domain="https://elpais.com/",
        parser=ElPaisParser,
        sources=[RSSFeed("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada")]
        + [
            Sitemap(f"https://elpais.com/sitemaps/{d.year}/{str(d.month).zfill(2)}/sitemap_0.xml")
            for d in reversed(
                list(rrule(MONTHLY, dtstart=datetime.datetime(1976, 5, 1), until=datetime.datetime.now()))
            )
        ],
    )
    ElMundo = Publisher(
        name="El Mundo",
        domain="https://www.elmundo.es/",
        parser=ElMundoParser,
        sources=[
            RSSFeed("https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml"),
            RSSFeed("https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml"),
        ],
    )
    ABC = Publisher(
        name="ABC",
        domain="https://www.abc.es/",
        parser=ABCParser,
        sources=[
            NewsMap("https://www.abc.es/sitemap.xml"),
            RSSFeed("https://www.abc.es/rss/2.0/espana/"),
            RSSFeed("https://www.abc.es/rss/2.0/portada/"),
        ],
    )
    LaVanguardia = Publisher(
        name=" La Vanguardia",
        domain="https://www.lavanguardia.com/",
        parser=LaVanguardiaParser,
        sources=[
            NewsMap("https://www.lavanguardia.com/sitemap-google-news.xml"),
            NewsMap("https://www.lavanguardia.com/sitemap-news-agencias.xml"),
            RSSFeed("https://www.lavanguardia.com/rss/home.xml"),
            RSSFeed("https://www.lavanguardia.com/rss/internacional.xml"),
        ]
        + [
            Sitemap(f"https://www.lavanguardia.com/sitemap-noticias-{d.year}{str(d.month).zfill(2)}.xml.gz")
            for d in reversed(
                list(rrule(MONTHLY, dtstart=datetime.datetime(2019, 1, 1), until=datetime.datetime.now()))
            )
        ],
    )
