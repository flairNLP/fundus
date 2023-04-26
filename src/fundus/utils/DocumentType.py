from dataclasses import dataclass


@dataclass
class DocumentType():
    html: str
    url: str
class UnClassifiedType(DocumentType):
    pass

class ArticleType(DocumentType):
    pass

class LiveTickerType():
    pass