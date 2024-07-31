from __future__ import annotations

import base64
import ipaddress
import struct
from dataclasses import dataclass

from pyrogram.session.internals import DataCenter


@dataclass
class TeleBridgeSession:
    dc_id: int
    auth_key: bytes
    ip: str
    port: int

    is_bot: bool = False
    test_mode: bool = False
    user_id: int | None = None
    api_id: int | None = None

    @classmethod
    def from_pyrogram_string(cls, session_string: str):
        from pyrogram.storage import MemoryStorage

        if len(session_string) in [MemoryStorage.SESSION_STRING_SIZE, MemoryStorage.SESSION_STRING_SIZE_64]:
            dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
                (MemoryStorage.OLD_SESSION_STRING_FORMAT
                 if len(session_string) == MemoryStorage.SESSION_STRING_SIZE else
                 MemoryStorage.OLD_SESSION_STRING_FORMAT_64),
                base64.urlsafe_b64decode(session_string + "=" * (-len(session_string) % 4))
            )
            server_address, port = DataCenter(
                dc_id, False, False, False
            )
            return cls(
                dc_id=dc_id,
                api_id=None,
                test_mode=test_mode,
                auth_key=auth_key,
                user_id=user_id,
                is_bot=is_bot,
                ip=server_address,
                port=port
            )

        dc_id, api_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
            MemoryStorage.SESSION_STRING_FORMAT,
            base64.urlsafe_b64decode(session_string + "=" * (-len(session_string) % 4))
        )
        server_address, port = DataCenter(
            dc_id, False, False, False
        )
        return cls(
            dc_id=dc_id,
            api_id=api_id,
            test_mode=test_mode,
            auth_key=auth_key,
            user_id=user_id,
            is_bot=is_bot,
            ip=server_address,
            port=port
        )

    @classmethod
    def from_telethon_string(cls, session_string: str):
        from telethon.sessions import StringSession
        session = StringSession(session_string)
        return cls(
            dc_id=session._dc_id,
            auth_key=session._auth_key.key,
            ip=session._server_address,
            port=session._port,
        )

    def to_telethon_string(self):
        from telethon.sessions import StringSession
        from telethon.crypto import AuthKey

        session = StringSession()
        session._dc_id = self.dc_id
        session._port = self.port
        session._auth_key = AuthKey(self.auth_key)
        session._server_address = ipaddress.ip_address(self.ip).compressed
        return session.save()

    def to_pyrogram_string(self):
        from pyrogram.storage import MemoryStorage

        packed = struct.pack(
            MemoryStorage.SESSION_STRING_FORMAT,
            self.dc_id,
            self.api_id,
            self.test_mode,
            self.auth_key,
            self.user_id,
            self.is_bot
        )
        return base64.urlsafe_b64encode(packed).decode().rstrip("=")

    def base64_auth_key(self):
        return base64.urlsafe_b64encode(self.auth_key).decode('ascii')
