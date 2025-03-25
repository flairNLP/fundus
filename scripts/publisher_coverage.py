"""
This script performs a baseline real-time crawler validation for every publisher and reports the test coverage.
The tests include a real-time crawl for each publisher's news map and RSS Feed
checking the received articles for attribute completeness.
Note that this script does not check the attributes' correctness, only their presence.
"""
import sys
import traceback
from typing import Any, Callable, List, Optional, Union

from fundus import Crawler, PublisherCollection
from fundus.publishers.base_objects import Publisher, PublisherGroup
from fundus.scraping.article import Article


def main() -> None:
    failed: int = 0
    timeout_in_seconds: int = 30

    publisher_regions: List[PublisherGroup] = sorted(
        PublisherCollection.get_subgroup_mapping().values(), key=lambda region: region.__name__
    )

    for publisher_region in publisher_regions:
        print(f"{publisher_region.__name__:-^50}")

        publisher: Publisher
        for publisher in sorted(publisher_region, key=lambda p: p.name):
            publisher_name: str = publisher.name

            if not any(publisher.source_mapping.values()):
                # skip publishers providing no sources for forward crawling
                print(f"⏩  SKIPPED: {publisher_name!r} - No sources defined")
                continue
            if publisher.deprecated:  # type: ignore[attr-defined]
                print(f"⏩  SKIPPED: {publisher_name!r} - Deprecated")
                continue
            crawler: Crawler = Crawler(publisher, delay=0.4, ignore_robots=True)

            complete_article: Optional[Article] = next(
                crawler.crawl(
                    max_articles=1, timeout=timeout_in_seconds, only_complete=True, error_handling="suppress"
                ),
                None,
            )

            if complete_article is None:
                incomplete_article: Optional[Article] = next(
                    crawler.crawl(
                        max_articles=1, timeout=timeout_in_seconds, only_complete=False, error_handling="catch"
                    ),
                    None,
                )

                if incomplete_article is None:
                    print(f"❌ FAILED: {publisher_name!r} - No articles received")

                elif incomplete_article.exception is not None:
                    print(
                        f"❌ FAILED: {publisher_name!r} - Encountered exception during crawling "
                        f"(URL: {incomplete_article.html.requested_url})"
                    )
                    traceback.print_exception(
                        etype=type(incomplete_article.exception),
                        value=incomplete_article.exception,
                        tb=incomplete_article.exception.__traceback__,
                        file=sys.stdout,
                    )

                else:

                    def guard(field, fnc: Callable[[Any], bool] = lambda x: x is not None) -> Union[bool, str]:
                        """Makes a boolean evaluation of <field> based on <fnc> and guards exceptions

                        Args:
                            field: The article field to evaluate
                            fnc:  The evaluation function

                        Returns:
                            Either True, False or Exception if isinstance(field, Exception) = True
                        """
                        return fnc(field) if not isinstance(field, Exception) else repr(field)

                    print(
                        f"❌ FAILED: {publisher_name!r} - No complete articles received "
                        f"(URL of an incomplete article: {incomplete_article.html.requested_url}) with attributes:\n"
                        f"title: {guard(incomplete_article.title)}\n"
                        f"plaintext: {guard(incomplete_article.body, bool)}\n"
                        f"publishing_date: {guard(incomplete_article.publishing_date)}\n"
                        f"authors: {guard(incomplete_article.authors, bool)}\n"
                        f"topics: {guard(incomplete_article.topics, bool)}\n"
                        f"images: {guard(incomplete_article.images, bool)}\n"
                    )
                failed += 1
                continue

            print(f"✔️ PASSED: {publisher_name!r}")
        print()

    total_publishers: int = len(PublisherCollection)
    pass_ratio: str = f"{total_publishers - failed}/{total_publishers}"
    if failed:
        print(f"🚨 {pass_ratio} - Some publishers finished in a 'FAILED' state")
    else:
        print(f"✨ {pass_ratio} - All publishers passed the tests")

    exit(failed)


if __name__ == "__main__":
    main()
