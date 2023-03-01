class SupportsText(Protocol):

    def __str__(self) -> str:
        ...
