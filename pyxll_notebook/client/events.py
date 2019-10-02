import asyncio


class MessageReplyEvent(asyncio.Event):
    """Event used to signal a message reply has been received."""

    def __init__(self):
        super().__init__()
        self.__reply = {}

    def set(self, reply={}):
        self.__reply = reply
        super().set()

    async def wait(self):
        await super().wait()
        return self.__reply
