from __future__ import annotations
from __future__ import annotations

import io
import typing

from aiogram import Bot
from aiogram.enums import ContentType
from aiogram.types import Message as AiogramMessage
from loguru import logger
from telethon.custom import Message as TelethonMessage
from pyrogram.types import Message as PyrogramMessage
from telethon.errors import VoiceMessagesForbiddenError, FileReferenceExpiredError
from telethon.tl.types import DocumentAttributeVideo
from pyrogram import Client as PyrogramClient
if typing.TYPE_CHECKING:
    from src.tele.client import TelethonClient


class ClientObject:

    async def read_history(self, message: MessageObject, **kwargs):
        pass

    async def send_message(
            self,
            message: MessageObject,
            text: str,
            reply: bool = False,
            disable_web_page_preview: bool = True,
    ):
        pass



class TelethonClientObject(ClientObject):

    def __init__(self, client: TelethonClient):
        self.client = client

    async def read_history(
            self,
            message: TelethonMessageObject,
            **kwargs
    ):
        return await self.client.send_read_acknowledge(
            message.m.chat_id,
            message.m
        )

    async def send_message(
            self,
            message: TelethonMessageObject,
            text: str,
            reply: bool = False,
            disable_web_page_preview: bool = True,
    ):
        return await self.client.send_message(
            message.get_chat_id(),
            text,
            reply_to=message.get_message_id() if reply else None,
            link_preview=not disable_web_page_preview,
        )



class  PyrogramClientObject(ClientObject):

    def __init__(self, client: PyrogramClient):
        self.client = client

