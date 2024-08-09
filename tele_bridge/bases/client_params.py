from dataclasses import dataclass

from tele_bridge.sessions.tele_bridge_session import TeleBridgeSession


@dataclass
class ClientOpts:
    api_id: int
    api_hash: str

    session_bridge: TeleBridgeSession = None
    in_memory: bool = False
    receive_updates: bool = True

    phone_number: str = None
    phone_code: str = None
    password: str = None

    phone_number_error: str = None
    phone_code_error: str = None
    password_error: str = None
    proxy: str = None

    # seconds
    set_attr_timeout: int = 60

    app_version: str = "TeleBridge v2"
    device_model: str = "Linux"
    system_version: str = "6.1"
