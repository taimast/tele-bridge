from __future__ import annotations

from typing import Type

from aiogram import types as aiogram_types
from aiogram.types import BufferedInputFile
from loguru import logger
from pyrogram import enums as pyro_enums

from src import PyrogramClient
from src.bases.client_object import ClientObject
from src.pyro.message import PyrogramMessageObject
from src.pyro.try_get import PyrogramChatGetterTry


class PyrogramClientInterface(ClientObject):
    message_class: Type[PyrogramMessageObject] = PyrogramMessageObject
    chat_getter_try: Type[PyrogramChatGetterTry] = PyrogramChatGetterTry
    client: PyrogramClient

    def __init__(self, client: PyrogramClient):
        super().__init__(client)

    async def get_media_group(self, message: PyrogramMessageObject) -> list[aiogram_types.InputMedia]:
        text = None
        chat_id = message.get_chat_id()
        message_id = message.get_message_id()

        messages = await self.client.get_media_group(chat_id, message_id=message_id)

        medias = []
        for _message in messages:
            media_attr = getattr(_message, _message.media.value)
            if hasattr(media_attr, "file_size") and media_attr.file_size:
                if media_attr.file_size > 50 * 1024 * 1024:
                    logger.warning(f"File size is too big: {media_attr.file_size}")
                    continue

            media = await self.client.download_media(media_attr.file_id, in_memory=True)
            media.seek(0)
            buffer = BufferedInputFile(file=media.read(),
                                       filename=media.name)
            if _message.media == pyro_enums.MessageMediaType.PHOTO:
                medias.append(aiogram_types.InputMediaPhoto(media=buffer, caption=text))
            elif _message.media in (pyro_enums.MessageMediaType.VIDEO, pyro_enums.MessageMediaType.VIDEO_NOTE):
                medias.append(aiogram_types.InputMediaVideo(media=buffer, caption=text))
            elif _message.media == pyro_enums.MessageMediaType.AUDIO:
                medias.append(aiogram_types.InputMediaAudio(media=buffer, caption=text))
            elif _message.media == pyro_enums.MessageMediaType.VOICE:
                medias.append(aiogram_types.InputMediaAudio(media=buffer, caption=text))
            elif _message.media == pyro_enums.MessageMediaType.DOCUMENT:
                medias.append(aiogram_types.InputMediaDocument(media=buffer, caption=text))
        logger.debug(f"[MSG ID {message_id}]: Media group содержит {len(medias)} файла.")
        # logger.info(f"Prepared media group with содержимое {medias} items.")
        return medias

    async def download_media(self, file_id: str) -> bytes:
        media = await self.client.download_media(file_id, in_memory=True)
        media.seek(0)
        return media.read()

    async def download_media_from_msg(self, msg: PyrogramMessageObject) -> bytes:
        return await self.download_media(msg.get_media_file_id())

    async def get_media_group_messages(self, message: PyrogramMessageObject) -> list[PyrogramMessageObject]:
        messages = await self.client.get_media_group(message.get_chat_id(), message.get_message_id())
        return [PyrogramMessageObject(m) for m in messages]
