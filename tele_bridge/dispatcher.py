from __future__ import annotations

import asyncio
import typing
from functools import cache

from loguru import logger
from telethon import TelegramClient
from telethon.custom import Message

from .base import BaseDispatcher
from .bases.account import AccountProtocol
from .bases.client_object import ClientObject
from .bases.message import MessageObject
from .methods import CachedMethods
from .observer import Observable


@cache
def get_lock(key: typing.Any) -> asyncio.Lock:
    """Получение блокировки по ключу"""
    return asyncio.Lock()


async def try_send_bot_message(bot, user_id, text):
    try:
        await bot.send_message(user_id, text, parse_mode=None)
    except Exception as e:
        logger.warning(f"Failed to send bot message: {e}")


class Dispatcher(BaseDispatcher, Observable, CachedMethods):
    """Диспетчер аккаунта"""

    def __init__(
            self,
            account: AccountProtocol,
            client_object: ClientObject,
    ):
        super().__init__(client_object.client)
        self.account = account
        self.client_object = client_object
        self.chat_getter = client_object.chat_getter_try("chat", account.id)
        self.sender_getter = client_object.chat_getter_try("sender", account.id)
        self.processing_media_group_ids = set()

    def need_skip_media(self, msg_object: MessageObject) -> bool:
        media_group_id = msg_object.get_media_group_id()
        if media_group_id:
            if media_group_id in self.processing_media_group_ids:
                logger.debug(f"Media group ID {media_group_id} is already being processed")
                return True
            self.processing_media_group_ids.add(media_group_id)
        return False

    async def message_handler(self, client: TelegramClient, _message: Message):
        msg_object = self.client_object.message_class(_message)

        msg_id = msg_object.get_message_id()
        chat_id = msg_object.get_chat_id()

        # if self.need_skip_media(msg_object):
        #     return

        logger.debug(f"Received message: {msg_id} from chat: {chat_id}")
        await self.chat_getter.try_get_chat(msg_object)
        await self.sender_getter.try_get_chat(msg_object)

    async def start(self):
        self.add_handler(self.message_handler)
        await super().start()
        await self.client.send_message("me", "Dispatcher started")
        # await self.log_all_chats()  # Log all chats at start

    async def restart(self):
        try:
            try:
                await self.client.stop()
            except Exception as e:
                logger.warning(f"[{self.account.id}] Dispatcher stop failed: {e}")
            if not await self.client.has_handlers():
                logger.info(f"[{self.account.id}] Dispatcher has no handlers")
                self.client.add_message_handler(self.message_handler)
            await asyncio.sleep(1)
            await self.client.start()
            logger.success(f"[{self.account.id}] Dispatcher restarted")
        except Exception as e:
            logger.error(f"[{self.account.id}] Dispatcher restart failed: {e}")
            raise e
