import base64
import struct
from dataclasses import dataclass

from pyrogram.storage import MemoryStorage


@dataclass
class PyrogramSessionInfo:
    dc_id: int
    test_mode: bool
    auth_key: bytes
    user_id: int
    is_bot: bool
    api_id: int | None = None


def parse_pyrogram_session(session_string: str):
    if session_string:
        # Old format
        if len(session_string) in [MemoryStorage.SESSION_STRING_SIZE, MemoryStorage.SESSION_STRING_SIZE_64]:
            dc_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
                (MemoryStorage.OLD_SESSION_STRING_FORMAT
                 if len(session_string) == MemoryStorage.SESSION_STRING_SIZE else
                 MemoryStorage.OLD_SESSION_STRING_FORMAT_64),
                base64.urlsafe_b64decode(session_string + "=" * (-len(session_string) % 4))
            )
            return PyrogramSessionInfo(
                dc_id=dc_id,
                api_id=None,
                test_mode=test_mode,
                auth_key=auth_key,
                user_id=user_id,
                is_bot=is_bot
            )

        dc_id, api_id, test_mode, auth_key, user_id, is_bot = struct.unpack(
            MemoryStorage.SESSION_STRING_FORMAT,
            base64.urlsafe_b64decode(session_string + "=" * (-len(session_string) % 4))
        )

        return PyrogramSessionInfo(
            dc_id=dc_id,
            api_id=api_id,
            test_mode=test_mode,
            auth_key=auth_key,
            user_id=user_id,
            is_bot=is_bot
        )
