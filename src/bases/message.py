from __future__ import annotations

import abc
import typing

from aiogram.types import Message as AiogramMessage
from telethon.custom import Message as TelethonMessage


class MessageObject(abc.ABC):

    @abc.abstractmethod
    def get_text(self):
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
    def get_message_id(self):
        pass

    @abc.abstractmethod
    def get_chat_type(self) -> ChatTypeForFilter:
        pass


class AiogramMessageObject(MessageObject):

    def __init__(self, message: AiogramMessage):
        self.m = message

    def get_text(self):
        return self.m.text or self.m.caption

    def get_first_name(self):
        return self.m.from_user.first_name

    def get_last_name(self):
        return self.m.from_user.last_name

    def get_chat_id(self):
        return self.m.chat.id

    def get_chat_username(self):
        return self.m.chat.username

    def get_message_id(self):
        return self.m.message_id

    def get_chat_type(self) -> ChatTypeForFilter:
        from autoanswer.db.models.project.components.filters.chat import ChatTypeForFilter
        match self.m.chat.type:
            case 'private':
                return ChatTypeForFilter.PRIVATE
            case 'group':
                return ChatTypeForFilter.GROUP
            case 'supergroup':
                return ChatTypeForFilter.SUPERGROUP
            case 'channel':
                return ChatTypeForFilter.CHANNEL
            case _:
                return ChatTypeForFilter.PRIVATE


class TelethonMessageObject(MessageObject):

    def __init__(self, message: TelethonMessage):
        self.m = message

    def get_text(self):
        return self.m.text

    def get_first_name(self):
        return self.m.sender.first_name

    def get_last_name(self):
        return self.m.sender.last_name

    def get_chat_id(self):
        return self.m.chat_id

    def get_chat_username(self):
        return self.m.chat.username

    def get_message_id(self):
        return self.m.id

    def get_chat_type(self):
        from autoanswer.db.models.project.components.filters.chat import ChatTypeForFilter
        if self.m.is_group:
            return ChatTypeForFilter.GROUP
        if self.m.is_channel:
            return ChatTypeForFilter.CHANNEL
        try:
            if self.m.chat.bot:
                return ChatTypeForFilter.BOT
        except:
            pass
        else:  # message.is_private:
            return ChatTypeForFilter.PRIVATE
