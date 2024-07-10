from typing import Awaitable, Callable, Any

from pyrogram import Client as _Client
from pyrogram import enums
from pyrogram import filters
from pyrogram.client import log
from pyrogram.enums import ParseMode
from pyrogram.errors import BadRequest, SessionPasswordNeeded
from pyrogram.handlers import MessageHandler
from pyrogram.types import TermsOfService, User
from pyrogram.utils import ainput

from tele_bridge.bases.mixins import Autofill, SetAttribute
from tele_bridge.bases.proxy import Proxy, ProxyType


class PyrogramClient(_Client, SetAttribute):

    def add_message_handler(self, handler: Callable[[Any, Any], Awaitable[Any]]):
        self.add_handler(MessageHandler(handler), filters.incoming)

    def has_handlers(self):
        return bool(self.dispatcher.groups)

    async def stop(
            self: "PyrogramClient",
            block: bool = True
    ):
        try:
            await super().stop(block)
        except ConnectionError:
            pass

    def __init__(
            self,
            api_id: int,
            api_hash: str,
            session_string: str = None,
            phone_number: Autofill = None,
            phone_code: Autofill = None,
            password: Autofill = None,
            phone_number_error: Autofill = None,
            phone_code_error: Autofill = None,
            password_error: Autofill = None,
            proxy: ProxyType = None,
            set_attr_timeout: int = 60,
            is_pyrogram_session: bool = False,
            is_telethon_session: bool = False,
            **kwargs
    ):
        name = f"{api_id}_{phone_number}"
        proxy: dict = Proxy.parse_proxy(proxy) if proxy else None
        self._attribute_cache = {}
        self._set_attr_timeout = set_attr_timeout
        self.is_pyrogram_session = is_pyrogram_session
        self.is_telethon_session = is_telethon_session
        self.phone_number_error = phone_number_error
        self.phone_code_error = phone_code_error
        self.password_error = password_error
        super().__init__(
            name,
            api_id,
            api_hash,
            session_string=session_string,
            phone_number=phone_number,
            phone_code=phone_code,
            password=password,
            proxy=proxy,
            parse_mode=ParseMode.HTML,
            app_version="RedirectBot v2",
            device_model="Linux",
            system_version="6.1",
            **kwargs
        )

    async def handle_updates(self, updates):
        try:
            await super().handle_updates(updates)
        except Exception:
            # fixme L5 11.10.2023 19:22 taima: Переписать все это на rust нахуй
            pass
            # logger.warning(f"[handle_updates] {e}")

    async def authorize(self) -> User:
        if self.bot_token:
            return await self.sign_in_bot(self.bot_token)

        while True:
            try:
                self.phone_number = await self.set_unfilled_attribute("phone_number")
                if not self.phone_number:
                    while True:
                        value = await ainput("Enter phone number or bot token: ")

                        if not value:
                            continue

                        confirm = (await ainput(f'Is "{value}" correct? (y/N): ')).lower()

                        if confirm == "y":
                            break

                    if ":" in value:
                        self.bot_token = value
                        return await self.sign_in_bot(value)
                    else:
                        self.phone_number = value

                sent_code = await self.send_code(self.phone_number)
            except BadRequest as e:
                await self.phone_number_error(e.MESSAGE)
                logger.error(e.MESSAGE)

                self.phone_number = None
                self.bot_token = None
            else:
                break

        sent_code_descriptions = {
            enums.SentCodeType.APP: "Telegram app",
            enums.SentCodeType.SMS: "SMS",
            enums.SentCodeType.CALL: "phone call",
            enums.SentCodeType.FLASH_CALL: "phone flash call"
        }

        print(f"The confirmation code has been sent via {sent_code_descriptions[sent_code.type]}")

        while True:
            self.phone_code = await self.set_unfilled_attribute("phone_code")
            if not self.phone_code:
                self.phone_code = await ainput("Enter confirmation code: ")

            try:
                signed_in = await self.sign_in(self.phone_number, sent_code.phone_code_hash, self.phone_code)
            except BadRequest as e:
                logger.error(e.MESSAGE)
                await self.phone_code_error(e.MESSAGE)

                self.phone_code = await self.set_unfilled_attribute("phone_code")
            except SessionPasswordNeeded as e:
                logger.warning(e.MESSAGE)

                while True:
                    print("Password hint: {}".format(await self.get_password_hint()))
                    self.password = await self.set_unfilled_attribute("password")
                    if not self.password:
                        self.password = await ainput("Enter password (empty to recover): ", hide=self.hide_password)

                    try:
                        if not self.password:
                            confirm = await ainput("Confirm password recovery (y/n): ")

                            if confirm == "y":
                                email_pattern = await self.send_recovery_code()
                                print(f"The recovery code has been sent to {email_pattern}")

                                while True:
                                    recovery_code = await ainput("Enter recovery code: ")

                                    try:
                                        return await self.recover_password(recovery_code)
                                    except BadRequest as e:
                                        print(e.MESSAGE)
                                    except Exception as e:
                                        log.error(e, exc_info=True)
                                        raise
                            else:
                                self.password = None
                        else:
                            return await self.check_password(self.password)
                    except BadRequest as e:
                        logger.error(e.MESSAGE)
                        self.password_error(e.MESSAGE)
                        self.password = await self.set_unfilled_attribute("password")
            else:
                break

        if isinstance(signed_in, User):
            return signed_in

        while True:
            first_name = await ainput("Enter first name: ")
            last_name = await ainput("Enter last name (empty to skip): ")

            try:
                signed_up = await self.sign_up(
                    self.phone_number,
                    sent_code.phone_code_hash,
                    first_name,
                    last_name
                )
            except BadRequest as e:
                print(e.MESSAGE)
            else:
                break

        if isinstance(signed_in, TermsOfService):
            print("\n" + signed_in.text + "\n")
            await self.accept_terms_of_service(signed_in.id)

        return signed_up

