The following document aims to describe which parsable attributes of a
parser class represent which semantic piece of a given news article.
Consistency between publishers and parsers is a main goal, please report any
cases you deem to be inconsistent with this document.If you want to contribute a parser to
this library, please ensure that these attributes are named consistently.

 Umformulieren das allgemein 
If there is a conflict
between the title in the visible layout and
the metadata, the title in the metadata is preferred.
This may result in titles which are not present in the
visible layout.
At no point will we mix metadata and entries extracted from the visible layout.

| Name | Summary  | Return Type |
| --   | -------- | --------    |
| Text | Text     | Text        |


# Title

A string representing the headline of a given article.
Does not include subheaders, aims to be as short as possible.



# Authors

A list of strings representing entities related to the creation of the article.
We prefer the most precise description out of the provided information.
Human entities are preferred, but make no promise that any particular string represents a
human.
Parsers are encouraged to strip strings of additional information besides the name.

# Topics

A list of unique strings representing keywords provided by the publisher to describe the article content.
Stripping of whitespace etc is encouraged, but formatting is not.

# Publishing Time

The earliest release date provided by the publisher. It is not required to be timezone-aware.
The Date must include Year, Month, Day, Hours and Minutes.

# Body

An object of type `ArticleBody` representing the structural hierarchy of the article content.
