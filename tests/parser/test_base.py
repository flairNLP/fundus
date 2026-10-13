from typing import Any, Dict, List, Optional, Tuple, Union

import pytest

from fundus.parser import BaseParser, attribute
from fundus.parser.base import AttributeCollection


class TestBaseParser:
    def test_empty_parser(self):
        class ParserWithoutTime(BaseParser):
            pass

        ParserWithoutTime()

    def test_functions_iter(self, parser_with_function_test, parser_with_static_method):
        assert len(BaseParser.functions()) == 0
        assert len(parser_with_static_method.functions()) == 0
        assert len(parser_with_function_test.functions()) == 1
        assert parser_with_function_test.functions().names == ["test"]

    def test_attributes_iter(self, parser_with_attr_title, parser_with_static_method):
        assert len(BaseParser.attributes()) == 1
        assert len(parser_with_static_method.attributes()) == 1
        assert len(parser_with_attr_title.attributes()) == 2
        assert parser_with_attr_title.attributes().names == ["free_access", "title"]

    def test_supported_unsupported(self):
        class ParserWithValidatedAndUnvalidated(BaseParser):
            @attribute
            def validated(self) -> str:
                return "supported"

            @attribute(validate=False)
            def unvalidated(self) -> str:
                return "unsupported"

        parser = ParserWithValidatedAndUnvalidated()
        assert len(parser.attributes()) == 3

        assert (validated := parser.attributes().validated)
        assert isinstance(validated, AttributeCollection)
        assert (funcs := list(validated)) != [parser.validated]
        assert funcs[1].__func__ == parser.validated.__func__

        assert (unvalidated := parser.attributes().unvalidated)
        assert isinstance(validated, AttributeCollection)
        assert (funcs := list(unvalidated)) != [parser.unvalidated]
        assert funcs[0].__func__ == parser.unvalidated.__func__

    def test_default_values_for_attributes(self):
        class Parser(BaseParser):
            @attribute
            def test_optional(self) -> Optional[str]:
                raise Exception

            @attribute
            def test_collection(self) -> Tuple[str, ...]:
                raise Exception

            @attribute
            def test_nested_collection(self) -> List[Tuple[str, str]]:
                raise Exception

            @attribute(default_factory=lambda: "This is a default")
            def test_default_factory(self) -> Union[str, bool]:
                raise Exception

            @attribute
            def test_boolean(self) -> bool:
                raise Exception

        parser = Parser()

        default_values = {attr.__name__: attr.__default__ for attr in parser.attributes()}

        expected_values: Dict[str, Any] = {
            "test_optional": None,
            "test_collection": tuple(),
            "test_nested_collection": list(),
            "test_default_factory": "This is a default",
            "test_boolean": False,
            "free_access": False,
        }

        for name, value in default_values.items():
            assert value == expected_values[name]

        class ParserWithUnion(BaseParser):
            @attribute
            def this_should_fail(self) -> Union[str, bool]:
                raise Exception

        parser_with_union = ParserWithUnion()

        with pytest.raises(NotImplementedError):
            default_values = {attr.__name__: attr.__default__ for attr in parser_with_union.attributes()}
