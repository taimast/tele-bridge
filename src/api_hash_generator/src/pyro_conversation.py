import asyncio
from collections import OrderedDict
from typing import Union

import pyrogram


class PyroConversation:
    def __init__(self, client: pyrogram.Client, chat_id: Union[int, str]):
        self._client = client
        self._chat_id = chat_id
        self._peer_user_id = None
        self._incoming = []
        self._handlers = {}
        self._handler_lock = asyncio.Lock()

    async def __aenter__(self):
        try:
            self._peer_user_id = (await self._client.resolve_peer(self._chat_id)).user_id
        except Exception:
            self._peer_user_id = self._chat_id
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        return await self.cancel(pyrogram.filters.chat(self._chat_id))

    async def send_message(self, *args, **kwargs):
        return await self._client.send_message(
            self._peer_user_id, *args, **kwargs
        )

    async def send_file(self, *args, **kwargs):
        return await self._client.send_document(
            self._peer_user_id, *args, **kwargs
        )

    async def read(self, message_id: int = None):
        if not message_id:
            if self._incoming:
                message_id = self._incoming[-1]
            else:
                message_id = 0
        return await self._client.read_chat_history(
            self._peer_user_id, message_id
        )

    async def get_response(self):
        message = await self.Message(
            pyrogram.filters.chat(self._chat_id) & (
                lambda _, m: m.from_user.id == self._peer_user_id
            ),
            timeout=None
        )
        self._incoming.append(message.id)
        return message

    async def __add(self, handler_, filters=None, id_=None, timeout=None):
        _id = id_

        if type(_id) in [pyrogram.filters.InvertFilter, pyrogram.filters.OrFilter, pyrogram.filters.AndFilter]:
            raise ValueError('Combined filters are not allowed as unique id .')

        if _id and type(_id) not in [pyrogram.filters.user, pyrogram.filters.chat, str]:
            raise TypeError('Unique (id) has to be one of pyrogram\'s filters user/chat or a string.')

        if not (_id or filters):
            raise ValueError('Atleast either filters or _id as parameter is required.')

        if str(_id) in self._handlers:
            await self.__remove(str(_id))

        async def dump(_, update):
            await self.__remove(dump._id, update)

        dump._id = str(_id) if _id else hash(dump)
        group = -0x3e7
        event = asyncio.Event()
        filters = (_id & filters) if _id and filters and not isinstance(_id, str) else filters or (
            filters if isinstance(_id, str) else _id)
        handler = handler_(dump, filters)

        if group not in self._client.dispatcher.groups:
            self._client.dispatcher.groups[group] = []
            self._client.dispatcher.groups = OrderedDict(sorted(self._client.dispatcher.groups.items()))

        async with self._handler_lock:
            self._client.dispatcher.groups[group].append(handler)
            self._handlers[dump._id] = (handler, group, event)

        try:
            await asyncio.wait_for(event.wait(), timeout)
        except asyncio.exceptions.TimeoutError:
            await self.__remove(dump._id)
            raise asyncio.exceptions.TimeoutError
        finally:
            result = self._handlers.pop(dump._id, None)
            self._handler_lock.release()
        return result

    async def __remove(self, _id, update=None):
        handler, group, event = self._handlers[_id]
        self._client.dispatcher.groups[group].remove(handler)
        await self._handler_lock.acquire()
        self._handlers[_id] = update
        event.set()

    async def cancel(self, _id) -> bool:
        if str(_id) not in self._handlers:
            return False
        await self.__remove(str(_id))
        return True

    def __getattr__(self, name):
        async def wrapper(*args, **kwargs):
            return await self.__add(getattr(pyrogram.handlers, f'{name}Handler'), *args, **kwargs)

        return wrapper
