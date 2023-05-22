from fundus import PublisherCollection


def produce_table():
    full_table = ""
    collections = [PublisherCollection.de, PublisherCollection.at, PublisherCollection.us]

    for collection_el in collections:
        collection_name = collection_el.__name__.split(".")[-1]
        print(collection_name)

        for publisher_el in sorted(collection_el, key=lambda x: x.name):
            entries: List[str] = []
            wrapper = f""" <tr>
        <td> {publisher_el.name}</td>
        <td>
            <a href="{publisher_el.domain}">
                <span>{publisher_el.domain.replace('https://', '')}</span>
            </a>
        </td>
        <td>{collection_name}</td>
        <td><code>{publisher_el._name_}</code></td>
        </tr>"""
            entries.append(wrapper)
            full_table = full_table + "\n".join(entries)

    return full_table


if __name__ == '__main__':
    print(produce_table())
