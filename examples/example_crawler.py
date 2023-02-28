from src.library.collection import PublisherCollection
from src.scraping.pipeline import AutoPipeline

if __name__ == '__main__':

    de_de = PublisherCollection.de_de

    crawler = AutoPipeline(de_de)

    """
    Alternative usage:
    
        via attribute search:
        crawler = Crawler(de_de.search(['plaintext']))
        
        or
        
        via explicit
        crawler = Crawler(de_de.MDR)
        
    """

    for article in crawler.run(max_articles=100, error_handling='raise'):
        print(article)
