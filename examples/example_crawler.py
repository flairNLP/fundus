from src.library.collection import PublisherCollection
from src.library.de_de import FAZParser, MDRParser
from src.scraping.crawler.crawler import RSSCrawler, SitemapCrawler
from src.scraping.pipeline import AutoPipeline
from src.scraping.scraper import Scraper

if __name__ == '__main__':

    # You can use fundus via the shipped collection of publisher

    de_de = PublisherCollection.de_de

    pipeline = AutoPipeline(de_de)

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

    for article in pipeline.run(max_articles=10, error_handling='raise'):
        print(article)

    # or explicitly create your own pipeline

    # using rss-feeds

    faz_crawler = [RSSCrawler(feed) for feed in PublisherCollection.de_de.FAZ.rss_feeds]
    faz_scraper = Scraper(*faz_crawler, parser=FAZParser())

    for article in faz_scraper.scrape():
        print(article)

    # or sitemaps

    mdr_crawler = SitemapCrawler(PublisherCollection.de_de.MDR.news_map, recursive=False)
    mdr_scraper = Scraper(mdr_crawler, parser=MDRParser())

    for article in mdr_scraper.scrape():
        print(article)

    # TODO: implement base pipeline to enable the same features as with AutoPipeline
