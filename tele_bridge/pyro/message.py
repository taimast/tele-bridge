from __future__ import annotations

from aiogram import types as aiogram_types
from aiogram.utils.keyboard import InlineKeyboardBuilder
from pyrogram import types as pyro_types
from pyrogram.types import Message as PyrogramMessage

from tele_bridge.bases.message import MessageObject


class PyrogramMessageObject(MessageObject):

    def __init__(self, message: PyrogramMessage):
        super().__init__(message)
        self.m = message

    def get_text(self):
        return self.m.text or self.m.caption

    def get_html_text(self):
        if self.m.text:
            return self.m.text.html
        if self.m.caption:
            return self.m.caption.html
        return None

    def have_from_user(self):
        return bool(self.m.from_user)

    def get_first_name(self):
        if self.m.from_user:
            return self.m.from_user.first_name

    def get_last_name(self):
        if self.m.from_user:
            return self.m.from_user.last_name

    def get_chat_id(self):
        return self.m.chat.id

    def get_chat_username(self):
        return self.m.chat.username

    def get_user_username(self):
        if self.m.from_user:
            return self.m.from_user.username

    def get_user_id(self):
        if self.m.from_user:
            return self.m.from_user.id

    def get_message_id(self):
        return self.m.id

    def get_reply_to_message_id(self):
        return self.m.reply_to_message_id

    def get_message_link(self):
        return self.m.link

    def has_media(self) -> bool:
        return bool(self.m.media)

    def get_media_group_id(self):
        return self.m.media_group_id

    def get_poll(self) -> pyro_types.Poll:
        return self.m.poll

    def get_media_file_size(self):
        media_attr = getattr(self.m, self.m.media.value)
        if hasattr(media_attr, "file_size") and media_attr.file_size:
            return media_attr.file_size
        return None

    def get_media_file_id(self):
        media_attr = getattr(self.m, self.m.media.value)
        if hasattr(media_attr, "file_id") and media_attr.file_id:
            return media_attr.file_id
        return None

    def get_media_type(self):
        return self.m.media

    def get_file_name(self):
        media_attr = getattr(self.m, self.m.media.value)
        if hasattr(media_attr, "file_name") and media_attr.file_name:
            return media_attr.file_name
        return None

    def get_reply_markup(self) -> aiogram_types.InlineKeyboardMarkup | None:
        if self.m.reply_markup:
            try:
                buttons = self.m.reply_markup.inline_keyboard
            except Exception:  # Если нет инлайн-кейборд или прилетела удаленная клавиатура
                return None
            inline_builder = InlineKeyboardBuilder()
            for button in buttons:
                inline_builder.row(
                    *[aiogram_types.InlineKeyboardButton(
                        text=button_inner.text,
                        url=button_inner.url
                    ) for button_inner in button]
                )
            return inline_builder.as_markup()
        return None
