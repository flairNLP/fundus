# Table of Contents

* [Logging in Fundus](#logging-in-fundus)
  * [Principals](#principals)
  * [Accessing loggers](#accessing-loggers)
  * [Changing log levels](#changing-log-levels)
  * [Format and handlers](#format-and-handlers)

# Logging in Fundus

This tutorial will introduce you to the logging mechanics used in Fundus

## Principals

Fundus uses module scoped logging with module names as logger names.
Not every module has a logger per se, but every module that logs a message has.
All module related implementation is centralized in Fundus' logging module under `fundus.logging`.

Fundus uses 4 different log levels:

- DEBUG: Not relevant to the average user and mainly used for debugging.
- INFO: Could be interesting to the user, but not necessarily.
- WARNING: Something went wrong, but we're trying to fix it.
- ERROR: Either we tried or not even bothering to resolve this.

with default log level for all Fundus loggers being `ERROR`.

*__NOTE__*: Depending on the spawn method (spawn) your OS uses to spawn new processes in python (this effects mostly Windows), log messages beneath `ERROR` won't be received when using multiprocessing. 

## Accessing loggers

You can import a specific logger from the corresponding module like this:

````python
from fundus.scraping.crawler import logger
````

Or find a collection of all existing loggers with their module names here:

````python
from fundus.logging import loggers

# print all modules having loggers
print("\n".join(sorted(loggers.keys())))

# accessing the 'url' logger
url_logger = loggers["fundus.scraping.url"]
````

## Changing log levels

You can change the log level for the entire library using the `set_log_level` function:

````python
import logging
from fundus.logging import set_log_level

set_log_level(logging.DEBUG)
````

## Format and Handlers

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

*__NOTE__*: All of the above can also be done individually for every logger by [accessing loggers](#accessing-loggers) directly.

