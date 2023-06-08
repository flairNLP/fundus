from typing import Iterator


def iterate_all_subclasses(cls: type) -> Iterator[type]:
    subclasses = cls.__subclasses__()
    yield from subclasses
    for subclass in subclasses:
        yield from iterate_all_subclasses(subclass)
