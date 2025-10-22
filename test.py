from fundus import PublisherCollection, Crawler

# -------------------------------------------------------------
# THAY ĐỔI TẠI ĐÂY:
# PublisherCollection.<country_section>.<publisher_specification>
# Thay 'us.TheIntercept' bằng 'vn.VnExpress'
publisher = PublisherCollection.vn.VnExpress
# -------------------------------------------------------------

crawler = Crawler(publisher)

# Lặp qua tối đa 2 bài viết để kiểm tra
# only_complete=False cho phép hiển thị các bài viết ngay cả khi thiếu nội dung (parser chưa hoàn chỉnh)
for article in crawler.crawl(max_articles=2, only_complete=False):
    print(article)