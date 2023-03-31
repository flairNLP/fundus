from src.library.collection import PublisherCollection
from src.scraping.pipeline import Crawler, Pipeline
from src.scraping.scraper import Scraper
from src.scraping.source import RSSSource, SitemapSource

if __name__ == "__main__":
    # You can use fundus via the Crawler class and the shipped collection of publisher

    de_de = PublisherCollection.de

    crawler = Crawler(de_de)

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

    for article in crawler.crawl(max_articles=5, error_handling="raise"):
        print(article)

    # or explicitly create your own pipeline

    # using rss-feeds

    FAZ = PublisherCollection.de.FAZ

    faz_crawler = [RSSSource(feed, FAZ.name) for feed in FAZ.rss_feeds]
    faz_scraper = Scraper(*faz_crawler, parser=FAZ.parser())

    # or sitemaps

    MDR = PublisherCollection.de.MDR

    mdr_crawler = SitemapSource("https://www.mdr.de/news-sitemap.xml", "MDR", recursive=False)
    mdr_scraper = Scraper(mdr_crawler, parser=MDR.parser())

    # and combine them with the pipeline class

    pipeline = Pipeline(faz_scraper, mdr_scraper)

    for article in pipeline.run(max_articles=5, error_handling="raise"):
        print(article)
