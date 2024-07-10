from __future__ import annotations

import contextlib

from tele_bridge import PyrogramClient
from tele_bridge.bases.account import AccountProtocol


def raise_exception():
    raise Exception("Phone code required")


def get_not_updates_pyrogram_client(account: AccountProtocol, no_updates=True):
    api_id, api_hash = account.get_api_data()
    return PyrogramClient(
        api_id=api_id,
        api_hash=api_hash,
        phone_number=account.phone_number,
        phone_code=raise_exception,
        session_string=account.session_string,
        is_pyrogram_session=True,
        in_memory=no_updates,
        no_updates=no_updates
    )


@contextlib.asynccontextmanager
async def get_not_updates_pyrogram_client_context(account: AccountProtocol, no_updates=False):
    async with get_not_updates_pyrogram_client(account, no_updates) as client:
        yield client
