from dataclasses import dataclass

from tele_bridge.bases.mixins import Autofill
from tele_bridge.sessions.tele_bridge_session import TeleBridgeSession


@dataclass
class ClientOpts:
    api_id: int
    api_hash: str

    session_bridge: TeleBridgeSession = None
    in_memory: bool = False
    receive_updates: bool = True

    phone_number: str | None = None
    phone_code: Autofill | None = None
    password: Autofill | None = None

    phone_number_error: Autofill | None = None
    phone_code_error: Autofill | None = None
    password_error: Autofill | None = None
    proxy: str | None = None

    # seconds
    set_attr_timeout: int = 60

    app_version: str = "TeleBridge v2"
    device_model: str = "Linux"
    system_version: str = "6.1"
