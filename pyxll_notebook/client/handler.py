"""
Handler for websocket messages received by the client.
"""
from .xl_func import bind_xl_func
import weakref
import logging
import sys

_log = logging.getLogger(__name__)


class Handler:
    """Handler for processing messages received by the client."""

    def __init__(self, kernel):
        self.__kernel = weakref.proxy(kernel)

    @staticmethod
    async def on_error(msg):
        traceback = msg.get("content", {}).get("traceback")
        if traceback:
            _log.error("\n" + "\n".join(traceback))

    @staticmethod
    async def on_stream(msg):
        content = msg.get("content", {})
        name = content.get("name")
        text = content.get("text")
        if name and text:
            stream = getattr(sys, name, None)
            if stream:
                stream.write(text)

    async def on_xl_func(self, msg):
        content = msg.get("content")
        if not content:
            raise AssertionError("xl_func message received with no content")

        kwargs = dict(content)
        func_name = kwargs.pop("func", None)
        if not func_name:
            raise AssertionError("xl_func message received with no function name")

        bind_xl_func(self.__kernel, func_name, **kwargs)
