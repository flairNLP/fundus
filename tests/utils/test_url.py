from fundus.utils.url import is_valid_url


class TestIsValidUrl:
    def test_valid_http_url(self):
        assert is_valid_url("http://example.com")

    def test_valid_https_url(self):
        assert is_valid_url("https://example.com")

    def test_valid_url_with_path(self):
        assert is_valid_url("https://example.com/some/path")

    def test_valid_url_with_query(self):
        assert is_valid_url("https://example.com/page?id=1")

    def test_rejects_unsupported_scheme(self):
        assert not is_valid_url("ftp://example.com")

    def test_rejects_missing_netloc(self):
        assert not is_valid_url("https://")

    def test_rejects_empty_string(self):
        assert not is_valid_url("")
