The following document aims to describe which parsable attributes of a parser class represent which semantic piece of a given news article.
Consistency between publishers and parsers is a main goal, please report any cases you deem to be inconsistent with this document. 
If you want to contribute a parser to this library, please ensure that these attributes are named consistently.

## Attributes table

<table class="annotations">
    <tr>
        <th>Name</th>
        <th>Description</th>
        <th>Type</th>
    </tr>
    <tr>
        <td>title</td>
        <td>A string representing the headline of a given article.
            Does not include subheaders, aims to be as short as possible.</td>
        <td><code>Optional[str]</code></td>
    </tr>
    <tr>
        <td>body</td>
        <td>An object of type `ArticleBody` representing the structural hierarchy of the article content.</td>
        <td><code>ArticleBody</code></td>
    </tr>
    <tr>
        <td>authors</td>
        <td>A list of strings representing entities related to the creation of the article.
            We prefer the most precise description out of the provided information. In this context human entities
            are considered most precise, but we make no promise that any particular string represents a
            human. Parsers are encouraged to strip strings of additional information besides the name.</td>
        <td><code>List[str]</code></td>
    </tr>
    <tr>
        <td>publishing_date</td>
        <td>The earliest release date provided by the publisher. It is not required to be timezone-aware.
            The date must at least include year, month, day, hours and minutes.</td>
        <td><code>Optional[datetime]</code></td>
    </tr>
    <tr>
        <td>topics</td>
        <td>A list of unique strings representing keywords provided by the publisher to describe the article content.
            Stripping of whitespace etc. is encouraged, but formatting is not.</td>
        <td><code>List[str]</code></td>
    </tr>
</table>
