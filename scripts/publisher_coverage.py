"""
This script performs a baseline real-time crawler validation for every publisher and reports the test coverage.
The tests include a real-time crawl for each publisher's news map and RSS Feed
checking the received articles for attribute completeness.
Note that this script does not check the attributes' correctness, only their presence.
"""
import sys
import traceback
from enum import EnumMeta
from typing import List, Optional, cast

from fundus import Crawler, NewsMap, PublisherCollection, RSSFeed
from fundus.publishers.base_objects import PublisherEnum
from fundus.scraping.article import Article
from fundus.scraping.filter import RequiresAllSkipBoolean


def main() -> None:
    failed: int = 0

    publisher_regions: List[EnumMeta] = sorted(
        PublisherCollection.get_publisher_enum_mapping().values(), key=lambda region: region.__name__
    )

    for publisher_region in publisher_regions:
        print(f"{publisher_region.__name__:-^50}")

        publisher: PublisherEnum
        for publisher in sorted(
            publisher_region, key=lambda p: cast(PublisherEnum, p).name  # type: ignore[no-any-return]
        ):
            publisher_name: str = publisher.name  # type: ignore[attr-defined]

            if not (publisher.source_mapping[RSSFeed] or publisher.source_mapping[NewsMap]):  # type: ignore[attr-defined]
                # skip publishers providing no NewsMap or RSSFeed
                print(f"⏩  SKIPPED: {publisher_name!r} - NO NewsMap or RSSFeed found")
                continue

            crawler: Crawler = Crawler(publisher, restrict_sources_to=[NewsMap, RSSFeed])
            complete_article: Optional[Article] = next(
                crawler.crawl(max_articles=1, only_complete=RequiresAllSkipBoolean(), error_handling="catch"), None
            )

            if complete_article is None:
                incomplete_article: Optional[Article] = next(
                    crawler.crawl(max_articles=1, only_complete=False, error_handling="suppress"), None
                )

                if incomplete_article is None:
                    print(f"❌ FAILED: {publisher_name!r} - No articles received")
                else:
                    print(
                        f"❌ FAILED: {publisher_name!r} - No complete articles received "
                        f"(URL of an incomplete article: {incomplete_article.html.requested_url})"
                    )
                failed += 1
                continue

            if complete_article.exception is not None:
                print(
                    f"❌ FAILED: {publisher_name!r} - Encountered exception during crawling "
                    f"(URL: {complete_article.html.requested_url})"
                )
                traceback.print_exception(
                    etype=type(complete_article.exception),
                    value=complete_article.exception,
                    tb=complete_article.exception.__traceback__,
                    file=sys.stdout,
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
