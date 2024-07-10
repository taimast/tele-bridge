import asyncio
import os
import random
from configparser import ConfigParser

from loguru import logger

from tele_bridge.api_data import TGData
from tele_bridge.json_proxy import JSONProxy

config = ConfigParser()
config.read('config.ini')

proxies_path = config.get('telegram', 'proxies_path')
sessions_folder = config.get('telegram', 'sessions_folder')
save_file_path = config.get('telegram', 'save_file_path')
app_title = config.get('telegram', 'app_title')
app_shortname = config.get('telegram', 'app_shortname')
app_platform = config.get('telegram', 'app_platform')
redirect_url = config.get('telegram', 'redirect_url')
app_desc = config.get('telegram', 'app_desc')


async def get_api_data(session_path: str, proxy: str):
    async with TGData(
            session_path,
            app_title, app_shortname,
            app_platform, redirect_url,
            app_desc, proxy,
            save_file_path
    ) as api:
        await api.run()


async def main():
    sessions_list = (
        os.listdir(sessions_folder)
        if os.path.exists(sessions_folder)
        else None
    )
    if not sessions_list:
        return logger.error(f'Folder ({sessions_folder}) not found or empty')
    await asyncio.gather(
        *[
            get_api_data(
                f'{sessions_folder}/{session_name.replace(".session", "")}',
                random.choice(await JSONProxy(proxies_path).convert())
                if proxies_path != 'None' else None
            )
            for session_name in sessions_list
            if session_name.endswith('.session')
        ]
    )


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
