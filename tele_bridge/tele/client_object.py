from __future__ import annotations

from typing import Type

from aiogram import types as aiogram_types
from telethon.tl.custom import Message as TelethonMessage
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument

from tele_bridge import TelethonClient
from tele_bridge.bases.client_object import ClientObject
from tele_bridge.tele.message import TelethonMessageObject
from tele_bridge.tele.try_get import TelethonChatGetterTry


class TelethonClientInterface(ClientObject):
    message_class: Type[TelethonMessageObject] = TelethonMessageObject
    chat_getter_try: Type[TelethonChatGetterTry] = TelethonChatGetterTry

    client: TelethonClient

    def __init__(self, client: TelethonClient):
        super().__init__(client)

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

    async def _get_media_posts_in_group(self, msg: TelethonMessageObject, max_amp=10) -> list[TelethonMessage]:
        """
        Searches for Telegram posts that are part of the same group of uploads
        The search is conducted around the id of the original post with an amplitude
        of `max_amp` both ways
        Returns a list of [post] where each post has media and is in the same grouped_id
        """
        chat_id = msg.get_chat_id()
        message_id = msg.get_message_id()
        grouped_id = msg.get_media_group_id()

        if grouped_id is None:
            return [msg] if msg.has_media() is not None else []

        search_ids = [i for i in range(message_id - max_amp, message_id + max_amp + 1)]
        posts = await self.client.get_messages(chat_id, ids=search_ids)
        media = []
        for post in posts:
            if post is not None and post.grouped_id == grouped_id and post.media is not None:
                media.append(post)
        return media

    async def get_client_media_group(self, msg: TelethonMessageObject) -> list[TelethonMessage]:
        chat_id = msg.get_chat_id()
        message_id = msg.get_message_id()
        if message_id <= 0:
            raise ValueError("Passed message_id is negative or equal to zero.")

        messages = await self.client.get_messages(
            chat_id,
            ids=[msg_id for msg_id in range(message_id - 9, message_id + 10)]
        )

        # There can be maximum 10 items in a media group.
        # If/else condition to fix the problem of getting correct `media_group_id` when `message_id` is less than 10.
        media_group_id = messages[9].grouped_id if len(messages) == 19 else messages[message_id - 1].grouped_id

        messages = [m for m in messages if m]

        if media_group_id is None:
            raise ValueError("The message doesn't belong to a media group")

        return list(msg for msg in messages if msg.grouped_id == media_group_id)

    async def get_media_group(self, message: TelethonMessageObject) -> list[aiogram_types.InputMedia]:
        messages = await self.get_client_media_group(message)
        medias = []
        for _message in messages:
            print(_message)
            if isinstance(_message.media, MessageMediaPhoto):
                media = await self.client.download_media(_message.media, file=bytes)
                buffer = aiogram_types.BufferedInputFile(file=media, filename="photo.jpg")
                medias.append(aiogram_types.InputMediaPhoto(media=buffer))
            elif isinstance(_message.media, MessageMediaDocument):
                media = await self.client.download_media(_message.media, file=bytes)
                buffer = aiogram_types.BufferedInputFile(file=media,
                                                         filename=_message.media.document.attributes[0].file_name)
                medias.append(aiogram_types.InputMediaDocument(media=buffer))
        return medias

    async def download_media(self, file_id: str) -> bytes:
        media = await self.client.download_media(file_id, file=bytes)
        return media

    async def download_media_from_msg(self, msg: TelethonMessageObject) -> bytes:
        return await self.client.download_media(msg.m.media, file=bytes)

    async def get_media_group_messages(self, message: TelethonMessageObject) -> list[TelethonMessageObject]:
        # messages = await self.get_client_media_group(message)
        messages = await self._get_media_posts_in_group(message)
        return [TelethonMessageObject(m) for m in messages]
