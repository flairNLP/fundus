from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.es.el_mundo import ElMundoParser
from fundus.publishers.es.el_pais import ElPaisParser
from fundus.scraping.url import RSSFeed


class ES(metaclass=PublisherGroup):
    ElPais = Publisher(
        name="El País",
        domain="https://elpais.com/",
        parser=ElPaisParser,
        sources=[
            RSSFeed("https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada"),
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
