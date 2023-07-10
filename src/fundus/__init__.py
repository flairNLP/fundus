import os
import pathlib

from fundus.logging import basic_logger
from fundus.publishers import PublisherCollection
from fundus.scraping.filter import Requires
from fundus.scraping.html import NewsMap, RSSFeed, Sitemap
from fundus.scraping.pipeline import BaseCrawler, Crawler

__module_path__ = pathlib.Path(__file__).parent
__development_base_path__ = __module_path__.parents[1]

__all__ = ["Crawler", "BaseCrawler", "PublisherCollection", "Requires", "RSSFeed", "Sitemap", "NewsMap"]

# event loop policy bug on windows, see
# https://stackoverflow.com/questions/45600579/asyncio-event-loop-is-closed-when-getting-loop
if os.name == "nt":
    import asyncio

    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
