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
    user_id: int = 0
    api_id: int = 0

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
                api_id=0,
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


def main():
    tele_session_string = "1ApWapzMBu4ia1ice543QRrQwiRtrwvgN5J7SXE7WwCE6iFVrBjrUdwkE4n0ZzQ7QMkr3KlXXdgpF_2ci6moeTrpRI1gctRBghOolSYHOBa51R2Wql2IQ2mPBES10ZJXNivDqbIvGimDqfoEy9oaTi7q-MCoxufKjqopbtTBRuiFyItylb9-bE6EmQlAj_xLdpg4WBHdAhQUo15hhk_yM_oytE4fYj2f3cmzAjt2crDHoz2oPk5wc38i20RYTshgtvobnWDKkKmxdLVvkXva8RIvEz08A-6CdXyu1cegRMSG9Dy5uuUYhr0IMc9mgvcCpfbuESHnE-iu2ZC4eeNVaqIaW8Y3RCYc="
    tele_session = TeleBridgeSession.from_telethon_string(tele_session_string)
    print(tele_session)
    pyro_session_string = tele_session.to_pyrogram_string()
    print(pyro_session_string)

if __name__ == '__main__':
    main()