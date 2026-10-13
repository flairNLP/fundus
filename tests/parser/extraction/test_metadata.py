from fundus.parser.extraction import generic_author_parsing


class TestGenericAuthorParsing:
    def test_generic_author_parsing(self):
        # type None
        assert generic_author_parsing(None) == []

        # type str
        assert generic_author_parsing("Peter") == ["Peter"]
        assert generic_author_parsing("Peter , Funny") == ["Peter", "Funny"]
        test_string = "Peter und Funny and the seven dandelions, right;?,;"
        assert generic_author_parsing(test_string) == ["Peter", "Funny", "the seven dandelions", "right", "?"]
        assert generic_author_parsing(test_string, split_on=["Funny", "dandelions"]) == [
            "Peter und",
            "and the seven",
            ", right;?,;",
        ]

        # type dict
        assert generic_author_parsing({"name": "Peter Funny"}) == ["Peter Funny"]
        assert generic_author_parsing({}) == generic_author_parsing({"what": "ever"}) == []

        # type list[str]
        assert generic_author_parsing([" Now", "we", "test ", " strip ", " ping ? "]) == [
            "Now",
            "we",
            "test",
            "strip",
            "ping ?",
        ]

        # type list[dict]
        assert generic_author_parsing(
            [{"name": "Peter Funny"}, {"name": "Funny Peter"}, {"this": "is not a pipe"}, {}]  # type: ignore
        ) == ["Peter Funny", "Funny Peter"]
        assert generic_author_parsing([{}]) == generic_author_parsing([{}, {"wrong": "key"}]) == []  # type: ignore
