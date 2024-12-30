from datetime import datetime, timedelta
from dateutil.rrule import MONTHLY, rrule

from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.it.la_repubblica import LaRepubblicaParser
from fundus.scraping.url import RSSFeed, Sitemap

class IT(metaclass=PublisherGroup):
    LaRepubblica = Publisher(
        name="La Repubblica",
        domain="https://www.repubblica.it",
        parser=LaRepubblicaParser,
        sources=[
            RSSFeed("https://www.repubblica.it/rss/homepage/rss2.0.xml"),
        ] + [
            Sitemap(f"https://www.repubblica.it/sitemap-{date.strftime('%Y-%m')}.xml")
            for date in reversed(list(rrule(
                MONTHLY, 
                dtstart=datetime(2020, 1, 1),
                until=datetime.now()+timedelta(days=30)
            )))
        ],
    )
    
print(IT.LaRepubblica.source_mapping)