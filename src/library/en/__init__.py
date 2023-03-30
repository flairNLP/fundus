from src.library.collection.base_objects import PublisherEnum, PublisherSpec
from src.library.en.world_truth import WorldTruthParser


class EN(PublisherEnum):
    WorldTruth= PublisherSpec(
        domain="https://worldtruth.tv/",
        rss_feeds=['https://feeds.feedburner.com/ConsciousnessTv'],
        parser=WorldTruthParser,
    )
