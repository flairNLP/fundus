from src.parser.html_parser.utility import generic_author_extraction


def test_generic_author_extraction():
    input = {"author": {"name": "test"}}
    result = generic_author_extraction(input, ["author"])
    assert result == ["test"]


def test_generic_author_extraction_str_input():
    input = {"author": "test"}
    result = generic_author_extraction(input, ["author"])
    assert result == ["test"]


def test_generic_author_extraction_dict_input():
    input = {"author": {"name": "test"}}
    result = generic_author_extraction(input, ["author"])
    assert result == ["test"]


def test_generic_author_extraction_none_input():
    input = {"author": None}
    result = generic_author_extraction(input, ["author"])
    assert result == []


def test_generic_author_extraction_list_input():
    input = {"author": [{"name": "test"}, {"name": None}]}
    result = generic_author_extraction(input, ["author"])
    assert result == ["test"]

    input = {"author": [{"name": "test"}, {}]}
    result = generic_author_extraction(input, ["author"])
    assert result == ["test"]



