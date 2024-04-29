from fundus.parser import ParserProxy, BaseParser, attribute
from typing import Optional


class TagesspiegelParser(ParserProxy):
    class V1(BaseParser):
        @attribute
        def title(self) -> Optional[str]:
            # Use the `get` function to retrieve data from the `meta` precomputed attribute
            return self.precomputed.meta.get("og:title")