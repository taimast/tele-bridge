from __future__ import annotations

import abc

from aiogram import types as aiogram_types
from pyrogram import enums as pyro_enums
from pyrogram import types as pyro_types


class MessageObject(abc.ABC):

    def __init__(self, message):
        super().__init__()

    @abc.abstractmethod
    def get_text(self) -> str | None:
        pass

    @abc.abstractmethod
    def get_html_text(self) -> str | None:
        pass

    @abc.abstractmethod
    def have_from_user(self) -> bool:
        pass

    @abc.abstractmethod
    def get_first_name(self):
        pass

    @abc.abstractmethod
    def get_last_name(self):
        pass

    @abc.abstractmethod
    def get_chat_id(self):
        pass

    @abc.abstractmethod
    def get_chat_username(self):
        pass

    @abc.abstractmethod
    def get_user_username(self):
        pass

    @abc.abstractmethod
    def get_user_id(self):
        pass

    @abc.abstractmethod
    def get_message_id(self):
        pass

    @abc.abstractmethod
    def get_reply_to_message_id(self):
        pass

    @abc.abstractmethod
    def get_message_link(self):
        pass

    @abc.abstractmethod
    def has_media(self) -> bool:
        pass

    @abc.abstractmethod
    def get_media_group_id(self) -> int:
        pass

    @abc.abstractmethod
    def get_poll(self) -> pyro_types.Poll:
        pass

    @abc.abstractmethod
    def get_media_file_size(self) -> int | None:
        pass

    @abc.abstractmethod
    def get_media_file_id(self) -> str | None:
        pass

    @abc.abstractmethod
    def get_media_type(self) -> pyro_enums.MessageMediaType | None:
        pass

    @abc.abstractmethod
    def get_file_name(self) -> str | None:
        pass

    @abc.abstractmethod
    def get_reply_markup(self) -> aiogram_types.InlineKeyboardButton | None:
        pass
