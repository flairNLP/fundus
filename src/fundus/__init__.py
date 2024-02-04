import pathlib
import sys

from fundus.publishers import PublisherCollection
from fundus.scraping.filter import Requires
from fundus.scraping.pipeline import BaseCrawler, CCNewsCrawler, Crawler
from fundus.scraping.url import NewsMap, RSSFeed, Sitemap

__module_path__ = pathlib.Path(__file__).parent
__development_base_path__ = __module_path__.parents[1]

__all__ = [
    "Crawler",
    "BaseCrawler",
    "CCNewsCrawler",
    "PublisherCollection",
    "Requires",
]

# On a Windows machines, when executing `BaseCrawler.crawl` from our sync API two times,
# Python throws an `RuntimeError: Event loop is closed exception` during Python's clean-up phase.

# To reproduce the error run the following code:
# from fundus import Crawler, PublisherCollection
# crawler = Crawler(PublisherCollection.de.DieWelt)
# for article in crawler.crawl(max_articles=1):
#     pass
# for article in crawler.crawl(max_articles=1):
#     pass

# A workaround involves to modify the event loop policy of asyncio on Windows machines.
# Unfortunately, this is a global modification. For further information see:
# https://stackoverflow.com/questions/45600579/asyncio-event-loop-is-closed-when-getting-loop
if sys.platform == "win32":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
