import logging

_stream_handler = logging.StreamHandler()
_formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
_stream_handler.setFormatter(_formatter)

basic_logger = logging.getLogger("basic_logger")
basic_logger.setLevel(logging.ERROR)
basic_logger.addHandler(_stream_handler)
