import asyncio

import aiofiles
from aiohttp import ClientSession
from bs4 import BeautifulSoup
from loguru import logger
from pyrogram import Client
from pyrogram.errors.exceptions import Unauthorized
from pyrogram.types import Message

from .pyro_conversation import PyroConversation


class TGData:
    def __init__(
            self, session_path: str,
            app_title: str = 'iPhone 14 Pro',
            app_shortname: str = 'iPhone 14 Pro',
            app_platform: str = 'iOS',
            redirect_url: str = '',
            app_desc: str = '',
            proxy: dict = None,
            save_file_path: str = None
    ):
        self.app_title = app_title
        self.app_shortname = app_shortname
        self.app_platform = app_platform
        self.redirect_url = redirect_url
        self.app_desc = app_desc
        self.session_path = session_path
        self.proxy = proxy
        self.save_file_path = save_file_path

        self.loop = asyncio.get_event_loop()
        self._web_client = ClientSession()

        self.code_hash: str = None
        self.phone_number: str = None
        self.api_id: int = None
        self.api_hash: str = None
        self.cookies: dict = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self._web_client.close()

    async def run(self):
        try:
            async with Client(self.session_path, 123, '123', proxy=self.proxy) as client:
                self.phone_number = (await client.get_me()).phone_number
                if await self._send_password():
                    async with PyroConversation(client, 777000) as conv:
                        await self._get_api_data(await conv.get_response())
        except Unauthorized:
            return logger.error(f'[{self.session_path}.session] Session died!')

    async def _get_api_data(self, message: Message):
        password: str = None
        if 'my.telegram.org' in message.text:
            try:
                password = message.text.split('\n')[1]
            except IndexError:
                logger.error(f'[{self.session_path}.session] Can\'t extract a password from message')
        if not await self._login_app(password):
            return logger.error(f'[{self.session_path}.session] Invalid password!')

        await self._create_app()
        if not self._parse_api_data(await self._get_app()):
            return logger.error(f'[{self.session_path}.session] Error get api data')
        logger.success(f'[{self.session_path}.session] {self.api_id}:{self.api_hash}')

        if self.save_file_path:
            async with aiofiles.open(self.save_file_path, 'a+') as file:
                await file.seek(0)
                if f'{self.api_id}:{self.api_hash}\n' not in await file.read():
                    await file.write(f'{self.api_id}:{self.api_hash}\n')
            logger.success(f'[{self.session_path}.session] Saved api data to {self.save_file_path}')

    def _parse_api_data(self, html_text: str):
        soup = BeautifulSoup(html_text, 'lxml')
        label_api_id = soup.find(
            'label', string='App api_id:'
        )
        if label_api_id:
            self.api_id = label_api_id.find_next_sibling('div').find('strong').text
            self.api_hash = soup.find(
                'label', string='App api_hash:'
            ).find_next_sibling('div').find('span').text
            return True
        return None

    async def _send_password(self):
        response = await self._web_client.post(
            'https://my.telegram.org/auth/send_password',
            data={
                'phone': self.phone_number
            }, ssl=True
        )
        try:
            self.code_hash = (await response.json()).get('random_hash')
            logger.success(f'[{self.session_path}.session] Sent code')
            return True
        except Exception:
            logger.error(f'[{self.session_path}.session] Send Code - {await response.text()}')
            return None

    async def _login_app(self, code: str):
        response = await self._web_client.post(
            'https://my.telegram.org/auth/login',
            data={
                'phone': self.phone_number,
                'random_hash': self.code_hash,
                'password': code
            }, ssl=True
        )
        if await response.text() == 'true':
            self.cookies = response.cookies.items()
            logger.success(f'[{self.session_path}.session] Successfully logged in!')
            return True
        return None

    async def _get_app(self):
        response = await self._web_client.get(
            'https://my.telegram.org/apps/',
            ssl=True
        )
        return await response.text()

    async def _create_app(self):
        app_hash = (await self._get_app()).split('name="hash" value="')[1].split('"')[0]
        await self._web_client.post(
            'https://my.telegram.org/apps/create',
            data={
                'hash': app_hash,
                'app_title': self.app_title,
                'app_shortname': self.app_shortname,
                'app_platform': self.app_platform,
                'redirect_url': self.redirect_url,
                'app_desc': self.app_desc
            },
            ssl=True
        )
