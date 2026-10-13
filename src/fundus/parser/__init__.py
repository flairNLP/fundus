from .base import BaseParser, attribute, function
from .proxy import ParserProxy
from .types.body import ArticleBody, ArticleSection, TextSequence
from .types.image import Image

__all__ = [
    "ParserProxy",
    "BaseParser",
    "attribute",
    "function",
    "ArticleBody",
    "ArticleSection",
    "TextSequence",
    "Image",
]
