# Table of Contents

* [Logging in Fundus](#logging-in-fundus)
  * [Principles](#principles)
  * [Accessing loggers](#accessing-loggers)
  * [Changing log levels](#changing-log-levels)
  * [Format and handlers](#format-and-handlers)
  * [Using Fundus inside an application](#using-fundus-inside-an-application)

# Logging in Fundus

This tutorial will introduce you to the logging mechanics used in Fundus

## Principles

Fundus uses module-scoped logging with module names as logger names.
Not every module has a logger per se, but every module that logs a message has.
All module related implementation is centralized in Fundus' logging module under `fundus.logging`.

Fundus uses 4 different log levels:

- DEBUG: Not relevant to the average user and mainly used for debugging.
- INFO: Could be interesting to the user, but not necessarily.
- WARNING: Something went wrong, but we're trying to fix it.
- ERROR: Either we tried or not even bothering to resolve this.

with default log level for all Fundus loggers being `ERROR`.

Every module logger is a child of the library root logger, `fundus`, which is where the log
level and the handlers live. Module loggers inherit both, so each record is emitted exactly
once no matter how deeply the module is nested.

> [!IMPORTANT]
> The **level** decides which records reach the handlers at all; a **handler** only filters
> further, per destination. So a handler you add never sees records the logger already
> dropped — if you want a handler to capture more than `ERROR`, raise the log level too.

## Accessing loggers

You can import a specific logger from the corresponding module like this:

````python
from fundus.scraping.crawler.web import logger
````

Or find a collection of all existing loggers with their module names here:

````python
from fundus.logging import loggers

# print all modules having loggers
print("\n".join(sorted(loggers.keys())))

# accessing the 'url' logger
url_logger = loggers["fundus.scraping.url"]
````

> [!NOTE]
> These are unconfigured children: their own `level` is `NOTSET` and they hold no handlers,
> both being inherited from the `fundus` logger. Use `logger.getEffectiveLevel()` to read
> the level that actually applies.

## Changing log levels

You can change the log level for the entire library using the `set_log_level` function:

````python
import logging
from fundus.logging import set_log_level

set_log_level(logging.DEBUG)
````

Pass a logger to change the level for a single module, or for a whole package, leaving the
rest of the library at its current level:

````python
import logging
from fundus.logging import set_log_level

# one module
set_log_level(logging.DEBUG, logger="fundus.scraping.url")

# an entire subtree: both source modules underneath it
set_log_level(logging.DEBUG, logger="fundus.scraping.pipeline")
````

The `logger` parameter takes a name or a logger object, so this works as well:

````python
import logging
from fundus.logging import set_log_level
from fundus.scraping.crawler.web import logger

set_log_level(logging.DEBUG, logger=logger)
````

## Format and handlers

By default, all Fundus log messages are written to `stderr` with the following format `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
To add another handler use the `add_handler` function.

````python
import logging
from fundus.logging import add_handler

file_handler = logging.FileHandler(f"fundus.log", encoding="utf-8")
file_handler.set_name("your_custom_file_handler")
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
add_handler(file_handler)
````

As written, that file receives `ERROR` records only, because that is the library's log
level. To log everything to the file, raise the level as well:

````python
import logging
from fundus.logging import set_log_level

set_log_level(logging.DEBUG)
````

That sends `DEBUG` records to `stderr` too, because the default handler does no filtering
of its own. Give a handler a level to hold one destination back:

````python
import logging
from fundus.logging import get_handlers

for handler in get_handlers():
    if handler.name == "fundus-stderr":
        handler.setLevel(logging.ERROR)  # stderr stays quiet, the file gets everything
````

`add_handler` takes the same `logger` parameter as `set_log_level`, so a handler can be
scoped to one module or one package. Use a handler of its own — one already added to the
library root would then be attached twice and log every record twice:

````python
import logging
from fundus.logging import add_handler

url_handler = logging.FileHandler("fundus_url.log", encoding="utf-8")
url_handler.set_name("url_file_handler")
add_handler(url_handler, logger="fundus.scraping.url")
````

Handlers are removed by name with `remove_handler`, which returns the handler so you can
close it. Pass the same `logger` the handler was added to:

````python
from fundus.logging import remove_handler

remove_handler("your_custom_file_handler").close()
remove_handler("url_file_handler", logger="fundus.scraping.url").close()
````

> [!NOTE]
> All of the above can also be done individually for every logger by [accessing loggers](#accessing-loggers) directly.

## Using Fundus inside an application

Fundus attaches a `stderr` handler of its own, named `fundus-stderr`. That is unusual for a
library, but it keeps failures visible when Fundus is used from a script or a notebook.
Records still propagate to the root logger, so an application that configures logging itself
will see every Fundus record twice — once through Fundus' handler and once through its own.

Remove Fundus' handler to take ownership of the output. Propagation is unaffected, so Fundus
records keep flowing into the application's handlers:

````python
from fundus.logging import remove_handler

remove_handler("fundus-stderr").close()
````