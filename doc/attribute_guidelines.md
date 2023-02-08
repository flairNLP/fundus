The following document aims to describe which parsable attributes of a
parser class represent which semantic piece of a given news article.
Consistency between publishers and parsers is a main goal, please report any
cases you deem to be inconsistent with this document.If you want to contribute a parser to
this library, please ensure that these attributes are named consistently.

# Title

A string representing the headline of a given peace.
Does not include subheaders and summaries,
aims to be as short as possible.
Is not required to be part of the url. If there is a conflict
between the title in the visible layout and
the metadata, the title in the metadata is preferred.
This may result in titles which are not present in the
visible layout.

# Url

A uniform ressource locator as described in the relevant standards.
There is no promise that the article associated with
this particular url will be reachable through the url at any given moment.
More than one url may point to the same article at any time.
If this the case,
we do not prefer any particular url over any other.
It is up to the end user to deal with duplicate articles.

# Author

A list of strings representing entities related to the creation of the article.
A single entity might represent a human, but there is no such promise.
If the metadata and the visible layout differ,
the metadata is preferred. This may result in author entries not present in the visible layout.
At no point will we mix metadata and entries extracted from the visible layout.
We will strip the authors of data we deem extraneous, please refer to the individual parsers for
their documentation.

# Topics

A list of words associated with the article. May be presented as 'keywords' in the metadata.
This description is vague, since the reality of this
concept is messy. Topics from metadata will be preferred. If there is more than one entry in the
metadata, human judgement will be used to choose one and discard the others. We will not mix
metadata-entries. We will not format the topics found.

# Publishing Tim

A datetime object associated with this article.
There is no promise that this particular value is:

- The earliest release date of this article
- Accurate
- Precise
- Timezone-aware
- Updated after updates to the article have taken place

Metadata-entries are preferred over data found in the layout. If an entry from the metadata is used,
checks for data in the visible layout might be omitted.
There is no check if data from the visible layout and the metadata conflict with each other. 

