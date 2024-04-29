from fundus.parser import BaseParser, ParserProxy


class AdevarulParser(ParserProxy):
    class V1(BaseParser):
        @attribute
        def title(self) -> Optional[str]:
            return "This is a title"
