from __future__ import annotations

from tele_bridge.bases.try_get import ChatGetterTry
from tele_bridge.pyro.message import PyrogramMessageObject


class PyrogramChatGetterTry(ChatGetterTry):

    async def try_get_chat(self, message: PyrogramMessageObject):
        pass
