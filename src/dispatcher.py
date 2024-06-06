from __future__ import annotations

import asyncio
import contextlib
import logging
import typing
from functools import cache
from cachetools import TTLCache
from loguru import logger
from socks import ProxyError
from telethon.custom import Message
from telethon.errors import ChannelPrivateError

from .base import BaseDispatcher
from .methods import CachedMethods
from .observer import Observable
from .tele.client import TelethonClient

UserID = ChatID = int
GET_CHAT_ERRORS_BLOCKED_DISPATCHERS = TTLCache(maxsize=1000, ttl=60 * 3)


@cache
def get_lock(key: typing.Any) -> asyncio.Lock:
    """Получение блокировки по ключу"""
    return asyncio.Lock()


async def try_send_bot_message(bot, user_id, text):
    try:
        await bot.send_message(user_id, text, parse_mode=None)
    except Exception as e:
        logger.warning(f"Failed to send bot message: {e}")


def raise_exception():
    raise Exception("Phone code required")


@contextlib.asynccontextmanager
async def get_not_updates_client(account: Account):
    api_id, api_hash = account.get_api_data()
    async with TelethonClient(
            api_id=api_id,
            api_hash=api_hash,
            phone_number=account.phone_number,
            phone_code=raise_exception,
            session_string=account.session_string,
            is_pyrogram_session=False,
            in_memory=True,
            connection_retries=3
    ) as client:
        yield client


class TryGetChatMixin:

    def __init__(self):
        self.get_chat_errors = TTLCache(maxsize=5000, ttl=60 * 5)
        self.get_input_chat_errors = TTLCache(maxsize=5000, ttl=60 * 3)
        self.global_error_count = 0

    def clear_cache(self):
        self.get_chat_errors.clear()
        self.get_input_chat_errors.clear()
        self.global_error_count = 0

    async def try_get_chat(self: Dispatcher, message: Message):
        if GET_CHAT_ERRORS_BLOCKED_DISPATCHERS.get(self.account.id):
            return
        chat_id = message.chat_id
        get_chat_errors = self.get_chat_errors.get(chat_id)
        if not get_chat_errors:
            try:
                return await message.get_chat()
            except ChannelPrivateError:
                # logger.warning(f"{self.account.id}. ChatId {message.chat_id} .ChannelPrivateError: {e}")
                self.get_chat_errors[chat_id] = True
                self.global_error_count += 1
            except Exception:
                # logger.warning(f"{self.account.id}. ChatID {message.chat_id}. Get chat failed: {e}")
                self.get_chat_errors[chat_id] = True
                self.global_error_count += 1

        input_chat_errors = self.get_input_chat_errors.get(chat_id)
        if not input_chat_errors:
            try:
                return await message.get_input_chat()
            except Exception:
                # logger.warning(f"{self.account.id}. ChatID {message.chat_id}. Get input chat failed: {e}")
                self.get_input_chat_errors[chat_id] = True
                self.global_error_count += 1

        if self.global_error_count > 50:
            logger.warning(f"{self.account.id}. Too many errors. Self blocked get chat for 3 minutes")
            GET_CHAT_ERRORS_BLOCKED_DISPATCHERS[self.account.id] = True
            self.global_error_count = 0


class Dispatcher(BaseDispatcher, Observable, CachedMethods, TryGetChatMixin):
    """Диспетчер аккаунта"""


    def __init__(
            self,
            client: TelethonClient,
    ):
        super().__init__(client)
        TryGetChatMixin.__init__(self)

    async def message_handler(self, client: TelethonClient, message: Message):
        pass

    async def stop_dispatcher(self):
        try:
            await self.stop()
        except Exception as e:
            logger.warning(f"[{self.account.id}] Dispatcher stop failed: {e}")

        stats_job_id = f"project_stats_update_{self.account.id}"
        if job := self.scheduler.get_job(stats_job_id):
            job.remove()

        saved_chats_job_id = f"reset-save-chats-{self.account.id}"
        if job := self.scheduler.get_job(saved_chats_job_id):
            job.remove()

    async def all_fetched_account(self, session: AsyncSession) -> Account:
        query = select(Account).options(
            joinedload(Account.project).joinedload(Project.user),
            joinedload(Account.project),
        ).where(Account.id == self.account.id)
        result = await session.execute(query)
        return result.unique().scalar_one()

    def set_new_account(self, account: Account):
        self.account = account
        if self.account.project:
            self.account.project.clear_observers_cache()
        # self.schedule_project_stats_update()
        SaveChatsFeature.schedule_saved_chats_reset(self)

    async def _update_account(self, session: AsyncSession):
        account = await self.all_fetched_account(session)
        self.set_new_account(account)

    async def update_account(self, session: AsyncSession = None):
        if not session:
            async with self.session_maker() as session:
                await self._update_account(session)
        else:
            await self._update_account(session)

    async def update_project_stats_to_db_with_session(self, session: AsyncSession):
        project: Project = self.account.project
        if not project:
            return
        db_project = await Project.get_or_none(session, id=project.id)
        if db_project:
            project.update_observers_from_objs_cache()
            db_project.observers = project.observers
            db_project.flag_modified()

    @classmethod
    async def all_project_stats_update(
            cls,
            session_maker: async_sessionmaker,
            account_dispatchers: dict[int, Dispatcher],
    ):
        async with session_maker() as session:
            for account_id, dispatcher in account_dispatchers.items():
                if not dispatcher.account.project:
                    continue
                try:
                    await dispatcher.update_project_stats_to_db_with_session(session)
                except Exception as e:
                    logger.warning(f"[{account_id}] Project stats update failed: {e}")

            await session.commit()
        logger.info("Project stats updated")

    @classmethod
    async def all_project_stats_and_account_update(
            cls,
            session_maker: async_sessionmaker,
            account_dispatchers: dict[int, Dispatcher],
    ):
        async with session_maker() as session:
            for account_id, dispatcher in account_dispatchers.items():
                try:
                    db_account = await dispatcher.all_fetched_account(session)
                    if dispatcher.account.project:
                        try:
                            project: Project = dispatcher.account.project
                            db_project: Project = db_account.project
                            if db_project:
                                project.update_observers_from_objs_cache()
                                db_project.observers = project.observers
                                db_project.flag_modified()
                        except Exception as e:
                            logger.warning(f"[{account_id}] Project cache update failed: {e}")

                    dispatcher.set_new_account(db_account)
                except Exception as e:
                    logger.warning(f"[{account_id}] Project stats update failed: {e}")

            await session.commit()
        logger.info("Project stats updated")

    @classmethod
    async def update_project_account(
            cls,
            session: AsyncSession,
            project: Project,
            user_dispatchers: dict[int, Dispatcher]
    ):
        if project.account:
            account_id = project.account.id
            await cls.multi_manager.update_dispatcher(account_id)
            dispatcher = user_dispatchers.get(project.account.id)
            if dispatcher:
                await dispatcher.update_account(session)

    async def run_until_disconnected(self, is_starting: bool = False):
        try:
            if is_starting:
                await self.client.start()
            else:
                await self.client.run_until_disconnected()
        except (
                ConnectionError,
                # ProxyTimeoutError,
                ProxyError
        ) as e:
            logger.error(
                f"[{self.account.id}] {is_starting=}. Error connect with proxy: {self.client._proxy}. {e}\n"
                f"Try to reconnect without proxy..."
            )
            try:
                await self.client.disconnect()
                self.client.set_proxy(())
                await self.client.start()
            except Exception as e:
                logger.error(f"[{self.account.id}] {is_starting=} Reconnect failed: {e}")
                if not is_starting:
                    await try_send_bot_message(
                        self.bot,
                        self.account.user_id,
                        f"Ошибка во врем работы диспетчера {self.account.phone_number}: {e}",
                    )
                raise e

        except Exception as e:
            logger.error(f"[{self.account.id}] {is_starting=} Dispatcher run failed: {e}")
            if not is_starting:
                await try_send_bot_message(
                    self.bot,
                    self.account.user_id,
                    f"Ошибка во врем работы диспетчера {self.account.phone_number}: {e}",
                )
            raise e

    async def start(self):
        self.add_handler(self.message_handler)
        logger.info(f"[{self.account.id}] Dispatcher starting...")
        await self.run_until_disconnected(is_starting=True)
        logger.success(f"[{self.account.id}] Dispatcher started")
        _task = asyncio.create_task(self.run_until_disconnected())

        # try:
        #     await super().start()
        # finally:
        #     async with self.session_maker() as session:
        #         await self.update_account(session)
        #         self.account.session_string = self.client.export_session_string()

        # await self.client.send_message("me", "Dispatcher started")

    async def restart(self):
        try:
            try:
                await self.client.stop()
            except Exception as e:
                logger.warning(f"[{self.account.id}] Dispatcher stop failed: {e}")
            if not await self.client.has_handlers():
                logger.info(f"[{self.account.id}] Dispatcher has no handlers")
                self.client.add_message_handler(self.message_handler)
            await asyncio.sleep(1)
            await self.client.start()
            logger.success(f"[{self.account.id}] Dispatcher restarted")
        except Exception as e:
            logger.error(f"[{self.account.id}] Dispatcher restart failed: {e}")
            raise e
