import aiofiles


class JSONProxy:
    def __init__(self, proxy_file_name: str):
        self.proxy_file_name = proxy_file_name
        self.proxy_list = []

    def _convert_proxy_to_json(self, proxy_string: str):
        scheme: str = None
        hostname: str = None
        port: int = None
        username: str = None
        password: str = None

        if '://' in proxy_string:
            scheme, proxy_string = proxy_string.split('://', 1)

        if '@' in proxy_string:
            creds, address = proxy_string.split('@')
            username, password = creds.split(':')
        else:
            address = proxy_string

        if scheme in ['socks4', 'socks4a', 'socks5', 'socks5h']:
            if scheme == 'socks4a':
                scheme = 'socks4'
                hostname = address
                port = 1080
            else:
                hostname, port = address.split(':', 1)
            if scheme == 'socks5h':
                scheme = 'socks5'
                hostname = address

        elif scheme in ['http', 'https']:
            hostname, port = address.split(':', 1)

        self.proxy_list.append(
            {
                'scheme': scheme,
                'hostname': hostname,
                'port': int(port),
                'username': username,
                'password': password,
            }
        )

    async def convert(self):
        async with aiofiles.open(self.proxy_file_name, 'r', encoding='utf-8') as file:
            proxy_strings = (await file.read()).split('\n')
        for proxy in proxy_strings:
            self._convert_proxy_to_json(proxy)
        return self.proxy_list
