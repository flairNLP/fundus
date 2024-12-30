from datetime import datetime, timedelta

from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.publishers.it.la_repubblica import LaRepubblicaParser
from fundus.scraping.url import RSSFeed, Sitemap

start_month = "2020-01"
# end month is the next month
end_month = (datetime.now() + timedelta(days=30)).strftime("%Y-%m")

sitemap_urls = []
# urls in the format https://www.repubblica.it/sitemap-<year>-<month>.xml
# like https://www.repubblica.it/sitemap-2000-01.xml
for year in range(int(start_month.split("-")[0]), int(end_month.split("-")[0]) + 1):
    for month in range(1, 13):
        # month needs to be in the format 01, 02, 03, etc.
        month_str = f"{month:02d}"
        sitemap_urls.append(f"https://www.repubblica.it/sitemap-{year}-{month_str}.xml")
sitemap_urls.reverse()


class IT(metaclass=PublisherGroup):
    LaRepubblica = Publisher(
        name="La Repubblica",
        domain="https://www.repubblica.it",
        parser=LaRepubblicaParser,
        sources=[Sitemap(sitemap_url, reverse=False, recursive=False) for sitemap_url in sitemap_urls]
        + [RSSFeed("https://www.repubblica.it/rss/homepage/rss2.0.xml")],
    )
