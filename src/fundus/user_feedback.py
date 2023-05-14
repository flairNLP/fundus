from typing import Iterator, Optional, Set

from fundus.scraping.article import Article


class StatusDisplay(Iterator[Article]):
    def __init__(self, stepsize: int = 500):
        self.counter = 0
        self.iterator: Optional[Iterator[Article]] = None
        self.unique_sources: Set[str] = set()
        self.stepsize: int = stepsize

    def __next__(self) -> Article:
        assert self.iterator is not None
        current_article: Article = next(self.iterator)
        self.counter += 1
        if current_article.source.publisher:
            self.unique_sources.add(current_article.source.publisher)
        if self.counter % self.stepsize == 0:
            print(f"{self.counter} articles from {len(self.unique_sources)} Sources processed")
        return current_article

    def summary(self):
        return f"{self.counter} articles from {len(self.unique_sources)} Sources processed"

    def __call__(self, article_iterator: Iterator[Article]) -> Iterator[Article]:
        self.iterator = article_iterator
        return self

    def __enter__(self) -> "StatusDisplay":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        print("exit")
