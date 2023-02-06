from src.crawler.crawler import Crawler
from src.library.collection import PublisherCollection

if __name__ == '__main__':

    de_de = PublisherCollection.de_de

    crawler = Crawler(de_de)

    """
    Alternative usage:
    
        via attribute search:
        crawler = Crawler(de_de.search(['plaintext']))
        
        or
        
        via explicit
        crawler = Crawler(de_de.MDR)
        
    """
    crawler = Crawler(de_de.SZ)
    for article in crawler.crawl(max_articles=100, error_handling='raise'):
        print(article)
