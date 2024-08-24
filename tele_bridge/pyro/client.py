from typing import Awaitable, Callable, Any

from loguru import logger
from pyrogram import Client
from pyrogram import enums
from pyrogram import filters
from pyrogram.client import log
from pyrogram.enums import ParseMode
from pyrogram.errors import BadRequest, SessionPasswordNeeded
from pyrogram.handlers import MessageHandler
from pyrogram.types import TermsOfService, User
from pyrogram.utils import ainput

from tele_bridge.bases.client import BaseClient
from tele_bridge.bases.client_params import ClientOpts
from tele_bridge.bases.proxy import Proxy
from tele_bridge.sessions.tele_bridge_session import TeleBridgeSession


class PyrogramClient(Client, BaseClient):

    def add_message_handler(self, handler: Callable[[Any, Any], Awaitable[Any]]):
        self.add_handler(MessageHandler(handler), filters.incoming)

    def has_handlers(self):
        return bool(self.dispatcher.groups)

    async def get_telebridge_session(self) ->TeleBridgeSession:
        session_string = await self.export_session_string()
        return TeleBridgeSession.from_pyrogram_string(session_string)

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
            opts: ClientOpts,
            **kwargs
    ):
        BaseClient.__init__(self, opts=opts)

        name = f"{opts.api_id}_{opts.phone_number}"
        proxy: dict = Proxy.parse_proxy(opts.proxy) if opts.proxy else None

        session_string = None
        if opts.session_bridge:
            session_string = opts.session_bridge.to_pyrogram_string()

        super().__init__(
            name,
            opts.api_id,
            opts.api_hash,
            session_string=session_string,
            phone_number=opts.phone_number,
            phone_code=opts.phone_code,
            password=opts.password,
            proxy=proxy,
            parse_mode=ParseMode.HTML,
            in_memory=opts.in_memory,
            no_updates=not opts.receive_updates,

            app_version=opts.app_version,
            device_model=opts.device_model,
            system_version=opts.system_version,
            **kwargs
        )


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
