from __future__ import annotations

import abc
import typing

from tele_bridge.bases.message import MessageObject


class ChatGetterTry(abc.ABC):

    def __init__(
            self,
            get_type: typing.Literal["chat", "sender"],
            account_id: int
    ):
        self.account_id = account_id
        self.get_type = get_type
        super().__init__()

    @abc.abstractmethod
    async def try_get_chat(self, message: MessageObject):
        pass
