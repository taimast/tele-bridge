from dataclasses import dataclass
from typing import Self, TypeAlias, TypedDict, Union

from pydantic import AnyUrl

ProxyType: TypeAlias = Union[str, "ProxyDict", "Proxy", AnyUrl]


# type:host:port:rdns:username:password
# type SOCKS4 = 1
# type SOCKS5 = 2
# type HTTP = 3
# proxies:
#   - [ 2, 193.232.86.35, 8000, true, 7TxtKL, KnTFbA ]


class ProxyDict(TypedDict):
    # "socks4", "socks5" and "http" are supported
    scheme: str
    hostname: str
    port: int
    username: str
    password: str


@dataclass
class Proxy:
    scheme: str
    hostname: str
    port: int | str
    username: str = None
    password: str = None

    def to_dict(self) -> ProxyDict:
        return self.__dict__

    # set_proxy(proxy_type, addr[, port[, rdns[, username[, password]]]])
    # # type:host:port:rdns:username:password
    # # type SOCKS4 = 1
    # # type SOCKS5 = 2
    # # type HTTP = 3
    def to_telethon_proxy(self) -> tuple:
        schemes = {
            "socks4": 1,
            "socks5": 2,
            "http": 3
        }
        return (
            schemes[self.scheme],
            self.hostname,
            self.port,
            True if self.scheme in ("socks4", "socks5") else False,
            self.username,
            self.password
        )

    @classmethod
    def from_url(cls, url: str) -> Self:
        from urllib.parse import urlparse
        parsed = urlparse(url)
        return cls(
            scheme=parsed.scheme,
            hostname=parsed.hostname,
            port=parsed.port,
            username=parsed.username,
            password=parsed.password
        )

    @classmethod
    def parse_proxy(cls, proxy: ProxyType) -> ProxyDict:
        if isinstance(proxy, Proxy):
            proxy = proxy.to_dict()
        elif isinstance(proxy, AnyUrl):
            proxy = Proxy(
                scheme=proxy.scheme,
                hostname=proxy.host,
                port=proxy.port,
                username=proxy.user,
                password=proxy.password
            ).to_dict()
        elif isinstance(proxy, str):
            proxy = Proxy.from_url(proxy).to_dict()
        return proxy
