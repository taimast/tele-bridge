import ipaddress
import sys
import typing
import warnings
from functools import partial
from pathlib import Path

from pyrogram.session.internals.data_center import DataCenter
from telethon import TelegramClient, events
from telethon import utils, errors
from telethon.crypto import AuthKey
from telethon.sessions import StringSession

from tele_bridge.bases.mixins import Autofill, SetAttribute
from tele_bridge.bases.proxy import ProxyType, Proxy
from tele_bridge.tele.utils import parse_pyrogram_session

SESSIONS_DIR = Path("sessions")


def raise_exception():
    raise Exception("Phone code or password is required")


class TelethonClient(TelegramClient, SetAttribute):

    def add_message_handler(self, handler):
        with_client_handler = partial(handler, self)
        self.add_event_handler(with_client_handler, events.NewMessage(incoming=True, outgoing=False))

    async def has_handlers(self):
        return bool(self.list_event_handlers())

    async def stop(self, *args, **kwargs):
        await self.disconnect()

    async def restart(self):
        await self.disconnect()
        await self.connect()

    def __init__(
            self,
            api_id: int,
            api_hash: str,
            in_memory: bool = False,
            session_string: str = None,
            phone_number: Autofill = None,
            phone_code: Autofill = None,
            password: Autofill = None,
            proxy: ProxyType = None,
            set_attr_timeout: int = 60,
            is_pyrogram_session: bool = False,
            is_telethon_session: bool = False,
            **kwargs
    ):
        proxy: tuple = Proxy.from_url(proxy).to_telethon_proxy() if proxy else None

        self._attribute_cache = {}
        self._set_attr_timeout = set_attr_timeout
        self.phone_number = phone_number
        self.phone_code = phone_code
        self.password = password

        self.is_pyrogram_session = is_pyrogram_session
        self.is_telethon_session = is_telethon_session

        if is_pyrogram_session:
            pyro_info = parse_pyrogram_session(session_string)
            server_address, port = DataCenter(
                pyro_info.dc_id, False, False, False
            )
            # ip = ipaddress.ip_address(server_address).packed
            session = StringSession()
            session._dc_id = pyro_info.dc_id
            session._port = port
            session._auth_key = AuthKey(pyro_info.auth_key)
            session._server_address = ipaddress.ip_address(server_address).compressed
        elif in_memory:
            session = StringSession(session_string)
        else:
            session_path = SESSIONS_DIR / f"{api_id}.session"
            session = str(session_path.absolute())
        super().__init__(
            session,
            api_id,
            api_hash,
            proxy=proxy,
            app_version="TeleBridge v2",
            device_model="Linux",
            system_version="6.1",
            **kwargs
        )

    def start(
            self: 'TelegramClient',
            phone: typing.Callable[[], str] = raise_exception,
            password: typing.Callable[[], str] = raise_exception,
            # phone: typing.Callable[[], str] = lambda: input('Please enter your phone (or bot token): '),
            # password: typing.Callable[[], str] = lambda: getpass.getpass('Please enter your password: '),
            *,
            bot_token: str = None,
            force_sms: bool = False,
            code_callback: typing.Callable[[], typing.Union[str, int]] = raise_exception,
            first_name: str = 'New User',
            last_name: str = '',
            max_attempts: int = 3) -> 'TelegramClient':

        if code_callback is None:
            def code_callback():
                return input('Please enter the code you received: ')
        elif not callable(code_callback):
            raise ValueError(
                'The code_callback parameter needs to be a callable '
                'function that returns the code you received by Telegram.'
            )

        if not phone and not bot_token:
            raise ValueError('No phone number or bot token provided.')

        if phone and bot_token and not callable(phone):
            raise ValueError('Both a phone and a bot token provided, '
                             'must only provide one of either')

        coro = self._start(
            phone=phone,
            password=password,
            bot_token=bot_token,
            force_sms=force_sms,
            code_callback=code_callback,
            first_name=first_name,
            last_name=last_name,
            max_attempts=max_attempts
        )
        return (
            coro if self.loop.is_running()
            else self.loop.run_until_complete(coro)
        )

    async def _start(
            self,
            phone,
            password,
            bot_token,
            force_sms,
            code_callback,
            first_name,
            last_name,
            max_attempts
    ):
        if not self.is_connected():
            await self.connect()

        # Rather than using `is_user_authorized`, use `get_me`. While this is
        # more expensive and needs to retrieve more data from the server, it
        # enables the library to warn users trying to login to a different
        # account. See #1172.
        me = await self.get_me()
        if me is not None:
            # The warnings here are on a best-effort and may fail.
            if bot_token:
                # bot_token's first part has the bot ID, but it may be invalid
                # so don't try to parse as int (instead cast our ID to string).
                if bot_token[:bot_token.find(':')] != str(me.id):
                    warnings.warn(
                        'the session already had an authorized user so it did '
                        'not login to the bot account using the provided '
                        'bot_token (it may not be using the user you expect)'
                    )
            elif phone and not callable(phone) and utils.parse_phone(phone) != me.phone:
                warnings.warn(
                    'the session already had an authorized user so it did '
                    'not login to the user account using the provided '
                    'phone (it may not be using the user you expect)'
                )

            return self

        if not bot_token:
            # Turn the callable into a valid phone number (or bot token)

            # while not phone:
            # self.phone_number = await self.set_unfilled_attribute("phone_number")
            phone = utils.parse_phone(self.phone_number) or phone

            # while callable(self.phone_number):
            #     value = phone()
            #     if inspect.isawaitable(value):
            #         value = await value
            #
            #     if ':' in value:
            #         # Bot tokens have 'user_id:access_hash' format
            #         bot_token = value
            #         break

            # phone = utils.parse_phone(value) or phone

        if bot_token:
            await self.sign_in(bot_token=bot_token)
            return self

        me = None
        attempts = 0
        two_step_detected = False

        await self.send_code_request(phone, force_sms=force_sms)
        while attempts < max_attempts:
            try:
                # value = code_callback()
                # if inspect.isawaitable(value):
                #     value = await value
                # value = await self.set_unfilled_attribute('code', code_callback)
                value = await self.set_unfilled_attribute('phone_code')

                # Since sign-in with no code works (it sends the code)
                # we must double-check that here. Else we'll assume we
                # logged in, and it will return None as the User.
                if not value:
                    raise errors.PhoneCodeEmptyError(request=None)

                # Raises SessionPasswordNeededError if 2FA enabled
                me = await self.sign_in(phone, code=value)
                break
            except errors.SessionPasswordNeededError:
                two_step_detected = True
                break
            except (errors.PhoneCodeEmptyError,
                    errors.PhoneCodeExpiredError,
                    errors.PhoneCodeHashEmptyError,
                    errors.PhoneCodeInvalidError):
                print('Invalid code. Please try again.', file=sys.stderr)

            attempts += 1
        else:
            raise RuntimeError(
                '{} consecutive sign-in attempts failed. Aborting'
                .format(max_attempts)
            )

        if two_step_detected:
            if not password:
                raise ValueError(
                    "Two-step verification is enabled for this account. "
                    "Please provide the 'password' argument to 'start()'."
                )

            if callable(password):
                for _ in range(max_attempts):
                    try:
                        # value = password()
                        # if inspect.isawaitable(value):
                        #     value = await value
                        value = await self.set_unfilled_attribute('password')
                        # value = await self.set_unfilled_attribute('password', password)

                        me = await self.sign_in(phone=phone, password=value)
                        break
                    except errors.PasswordHashInvalidError:
                        print('Invalid password. Please try again',
                              file=sys.stderr)
                else:
                    raise errors.PasswordHashInvalidError(request=None)
            else:
                me = await self.sign_in(phone=phone, password=password)

        # We won't reach here if any step failed (exit by exception)
        signed, name = 'Signed in successfully as', utils.get_display_name(me)
        try:
            print(signed, name)
        except UnicodeEncodeError:
            # Some terminals don't support certain characters
            print(signed, name.encode('utf-8', errors='ignore')
                  .decode('ascii', errors='ignore'))

        return self
