import webbrowser
from enum import Enum

from src.library.collection import PublisherCollection
from src.scraping.crawler import RSSCrawler, SitemapCrawler
from src.scraping.pipeline import AutoPipeline
from src.scraping.scraper import Scraper

if __name__ == "__main__":
    # You can use fundus via the shipped collection of publisher

    de_de = PublisherCollection.de_de
    pipeline = AutoPipeline(de_de.Merkur)

    """
    Alternative usage:
    
        via search:
        pipeline = AutoPipeline(de_de.search(attrs=['plaintext'], source_type='news))
        
        or
        
        via explicit
        pipeline = AutoPipeline(de_de.MDR)
        
        also using multiple publisher
        pipeline = AutoPipeline(de_de.MDR, PublisherCollection.at_at)
        
    """

    for article in pipeline.run(max_articles=20, error_handling="raise"):

        print(article.url)
        print(article.extracted['topics'])
        print(article.extracted['authors'])
        #webbrowser.open_new_tab(article.url)


    exit()
    # or explicitly create your own pipeline

    # using rss-feeds

    FAZ = PublisherCollection.de_de.FAZ

    faz_crawler = [RSSCrawler(feed, FAZ.name) for feed in FAZ.rss_feeds]
    faz_scraper = Scraper(*faz_crawler, parser=FAZ.parser())

    for article in faz_scraper.scrape(error_handling="raise"):
        print(article)

    # or sitemaps

    MDR = PublisherCollection.de_de.MDR

    mdr_crawler = SitemapCrawler(MDR.news_map, MDR.name, recursive=False)  # type: ignore[arg-type]
    mdr_scraper = Scraper(mdr_crawler, parser=MDR.parser())

    for article in mdr_scraper.scrape(error_handling="suppress"):
        print(article)

    # TODO: implement base pipeline to enable the same features as with AutoPipeline
