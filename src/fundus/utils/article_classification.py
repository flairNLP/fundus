import re

from fundus.scraping.scraper import ArticleClassifier


def regex_url_classifier(regex: str) -> ArticleClassifier:
    def result_func(html: str, url: str):
        return bool(re.search(regex, url))

    return result_func
