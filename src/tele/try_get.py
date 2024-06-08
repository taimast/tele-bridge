from __future__ import annotations

import typing

from cachetools import TTLCache
from loguru import logger
from telethon.errors import ChannelPrivateError

from src.bases.try_get import ChatGetterTry
from src.tele.message import TelethonMessageObject

UserID = ChatID = int
GET_CHAT_ERRORS_BLOCKED_DISPATCHERS = TTLCache(maxsize=1000, ttl=60 * 3)


class TelethonChatGetterTry(ChatGetterTry):

    def __init__(
            self,
            get_type: typing.Literal["chat", "sender"],
            account_id: int
    ):
        super().__init__(get_type, account_id)
        self.get_chat_errors = TTLCache(maxsize=5000, ttl=60 * 5)
        self.get_input_chat_errors = TTLCache(maxsize=5000, ttl=60 * 3)
        self.global_error_count = 0

    def clear_cache(self):
        self.get_chat_errors.clear()
        self.get_input_chat_errors.clear()
        self.global_error_count = 0

    async def try_get_chat(self, message: TelethonMessageObject):
        message = message.m
        if GET_CHAT_ERRORS_BLOCKED_DISPATCHERS.get(self.account_id):
            return
        chat_id = message.chat_id
        get_chat_errors = self.get_chat_errors.get(chat_id)
        if not get_chat_errors:
            try:
                # return await message.get_chat()
                return await getattr(message, f"get_{self.get_type}")()
            except ChannelPrivateError:
                # logger.warning(f"{self.account_id}. ChatId {message.chat_id} .ChannelPrivateError: {e}")
                self.get_chat_errors[chat_id] = True
                self.global_error_count += 1
            except Exception:
                # logger.warning(f"{self.account_id}. ChatID {message.chat_id}. Get chat failed: {e}")
                self.get_chat_errors[chat_id] = True
                self.global_error_count += 1

        input_chat_errors = self.get_input_chat_errors.get(chat_id)
        if not input_chat_errors:
            try:
                # return await message.get_input_chat()
                return await getattr(message, f"get_input_{self.get_type}")()
            except Exception:
                # logger.warning(f"{self.account_id}. ChatID {message.chat_id}. Get input chat failed: {e}")
                self.get_input_chat_errors[chat_id] = True
                self.global_error_count += 1

        if self.global_error_count > 50:
            logger.warning(f"{self.account_id}. Too many errors. Self blocked get chat for 3 minutes")
            GET_CHAT_ERRORS_BLOCKED_DISPATCHERS[self.account_id] = True
            self.global_error_count = 0
