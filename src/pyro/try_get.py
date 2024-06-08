from __future__ import annotations

from src.bases.try_get import ChatGetterTry
from src.pyro.message import PyrogramMessageObject


class PyrogramChatGetterTry(ChatGetterTry):

    async def try_get_chat(self, message: PyrogramMessageObject):
        pass
