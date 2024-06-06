from typing import Callable, Any, Awaitable

from loguru import logger

from .tele.client import TelethonClient


class BaseDispatcher:

    def __init__(self, client: TelethonClient):
        self.client = client

    async def __aenter__(self):
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.stop()

    async def start(self):
        await self.client.start()

    async def stop(self):
        try:
            await self.client.stop()
        except Exception as e:
            logger.warning(f"Client stop failed: {e}")

    def add_handler(self, handler: Callable[[Any, Any], Awaitable[Any]]):
        self.client.add_message_handler(handler)
