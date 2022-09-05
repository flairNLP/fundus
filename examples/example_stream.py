from stream import StreamLine, SupplyLayer, UnaryLayer


def supply(x: int):
    yield from range(x + 1)


def process(x: int):
    return x * x


if __name__ == '__main__':
    supplier = SupplyLayer(target=supply, size=2)
    quadratic = UnaryLayer(target=process, size=4)

    with StreamLine([supplier, quadratic]) as stream:
        result = stream.map([1, 2, 3])

    print(result)
