from typing import Protocol


class AccountProtocol(Protocol):
    id: int
    phone_number: str
    session_string: str

    def get_api_data(self) -> tuple[int, str]:
        pass
