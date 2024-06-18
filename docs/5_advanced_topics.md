# Table of Contents

* [Saving the crawled articles](#saving-the-crawled-articles)

# Advanced Topics

This tutorial will show further options such as saving the crawled articles.

## Save crawled articles to a file

To save all crawled articles to a file use the `save_to_file` parameter of the `crawl` method.
When given a path, the crawled articles will be saved as a JSON list using the 
[default article serialization](3_the_article_class.md#saving-an-article) and `UTF-8` encoding.