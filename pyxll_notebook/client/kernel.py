"""
Jupyter client that runs remotely on a notebook server.
Communication is via the Jupyter Notebook REST and websockets APIs.
"""
from .handler import Handler
from .events import MessageReplyEvent
from ..errors import *
from typing import *
import datetime as dt
import websockets
import logging
import aiohttp
import asyncio
import json
import uuid
import os


_log = logging.getLogger(__name__)


class Kernel:
    """The Kernel starts and manages communication with the remote Jupyter kernel."""

    default_handler_cls = Handler
    message_protocol_version = "5.0"

    def __init__(self, host, port=8888, protocol='http', headers={}, handler=None):
        """Kernel wrapper for running code on a notebook server."""
        if handler is None:
            handler = self.default_handler_cls(self)
        self.__handler = handler
        self.__kernel = None
        self.__ws = None
        self.__session_id = uuid.uuid1().hex
        self.__username = os.getlogin()
        self.__base_url = f"{protocol}://{host}:{port}"
        self.__ws_base_url = f"ws://{host}:{port}"
        self.__kernel_url = None
        self.__headers = headers
        self.__message_events: Dict[str, MessageReplyEvent] = {}

    async def start(self):
        """Starts the kernel and opens the websocket connection."""
        kernels_url = self.__base_url + "/api/kernels"
        async with aiohttp.ClientSession() as session:
            async with session.post(kernels_url, headers=self.__headers) as response:
                kernel = json.loads(await response.text())
                if not "id" in kernel:
                    raise KernelStartError(kernel.get("message"))
                kernel_id = kernel["id"]
                _log.debug(f"Started new kernel {kernel_id}.")

        self.__kernel = kernel
        self.__id = kernel_id
        self.__kernel_url = kernels_url + "/" + self.__kernel["id"]

        # get the websockets channel
        ws_uri = self.__ws_base_url + f"/api/kernels/{kernel_id}/channels?session_id=" + self.__session_id
        self.__ws = await websockets.connect(ws_uri, extra_headers=self.__headers)

        # start polling the websocket connection
        loop = asyncio.get_event_loop()
        loop.create_task(self.__poll_ws())

    async def run_notebook(self, path):
        """Run all cells in a notebook"""
        url = self.__base_url + "/api/contents/" + path
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=self.__headers) as response:
                file = json.loads(await response.text())

        # set the special __pyxll_notebook_session__ variable
        await self.execute(f"__pyxll_notebook_session__ = '{self.__session_id}'")

        cells = file["content"]["cells"]
        code = [c["source"] for c in cells if len(c["source"]) > 0 and c["cell_type"] == "code"]

        for c in code:
            await self.execute(c)

    async def execute(self, code, user_expressions={}):
        """Execute some code on the remote kernel and wait for it to complete."""
        msg_id = uuid.uuid1().hex

        content = {
            'code': code,
            'silent': False,
            'user_expressions': user_expressions
        }

        header = {
            'msg_id': msg_id,
            'msg_type': 'execute_request',
            'username': self.__username,
            'session': self.__session_id,
            'data': dt.datetime.now().isoformat(),
            'version': self.message_protocol_version
        }

        msg = {
            "channel": "shell",
            'header': header,
            'parent_header': header,
            'metadata': {},
            'content': content,
        }

        event = self.__message_events[msg_id] = MessageReplyEvent()

        # send the message to the remote kernel
        await self.__ws.send(json.dumps(msg))

        # wait for a response
        reply = await event.wait()

        content = reply.get("content", {})
        status = content.get("status")
        if status != "ok":
            raise ExecuteRequestError(**reply)

        return content


    async def __poll_ws(self):
        while self.__ws is not None:
            msg = json.loads(await self.__ws.recv())

            # Only process messages for our session
            parent_header = msg.get("parent_header", {})
            parent_session_id = parent_header.get("session")
            if parent_session_id != self.__session_id:
                continue

            # Dispatch the message based on the message type
            header = msg.get("header", {})
            msg_type = header.get("msg_type")

            if "." in msg_type:
                ns, msg_type = msg_type.split(".", 1)
                if ns != "pyxll":
                    continue

            # All replies are processed by the kernel to signal any waiting events
            if msg_type.endswith("_reply"):
                await self.__on_reply(msg)

            # And pass all messages to the handler
            func = getattr(self.__handler, f"on_{msg_type}", None)
            if func:
                try:
                    await func(msg)
                except:
                    _log.error("An error occurred processing a message from the kernel", exc_info=True)

    async def __on_reply(self, msg):
        """Sets any waiting events when a message reply is received."""
        msg_id = msg.get("parent_header", {}).get("msg_id")
        if not msg_id:
            _log.debug(f"Message reply received with no msg_id in the parent_header: {msg}")
            return

        event = self.__message_events.pop(msg_id, None)
        if event:
            event.set(msg)

    async def shutdown(self):
        """Sends the shutdown command to the kernel and closes the websocket connection"""
        kernel_url = self.__kernel_url
        kernel = self.__kernel
        headers = self.__headers
        ws = self.__ws

        self.__kernel = None
        self.__ws = None

        if kernel:
            tasks = []
            if ws:
                tasks.append(ws.close())

            async with aiohttp.ClientSession() as session:
                async with session.delete(kernel_url, headers=headers) as response:
                    tasks.append(response.read())
                    await asyncio.gather(*tasks)
                    _log.debug(f"Shutdown kernel {kernel['id']}")

    def __del__(self):
        if self.__kernel:
            _log.warning("Kernel not shutdown cleanly")
