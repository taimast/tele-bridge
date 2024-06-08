from __future__ import annotations

import abc
from typing import Type

from aiogram import types as aiogram_types

from src.bases.message import MessageObject
from src.bases.try_get import ChatGetterTry


class ClientObject(abc.ABC):

    def __init__(self, client):
        self.client = client
        super().__init__()

    @property
    @abc.abstractmethod
    def message_class(self) -> Type[MessageObject]:
        return MessageObject

    @property
    @abc.abstractmethod
    def chat_getter_try(self) -> Type[ChatGetterTry]:
        pass

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

    @abc.abstractmethod
    async def get_media_group(self, message: MessageObject) -> list[aiogram_types.InputMedia]:
        pass

    @abc.abstractmethod
    async def download_media(self, file_id: str) -> bytes:
        pass

    async def download_media_from_msg(self, msg: MessageObject) -> bytes:
        pass

    @abc.abstractmethod
    async def get_media_group_messages(self, message: MessageObject) -> list[MessageObject]:
        pass
