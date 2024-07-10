from __future__ import annotations

import asyncio
from functools import partial
from typing import TYPE_CHECKING, Callable

from aiogram import F, Router, types, Bot
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from chat_scanner.apps.account.client import Client
from chat_scanner.apps.account.dispatcher import Dispatcher
from chat_scanner.apps.bot.callback_data.account import AccountAction, AccountCallback
from chat_scanner.apps.bot.commands.bot_commands import BaseCommands
from chat_scanner.apps.bot.handlers.common.account.crud.get import connect_accounts
from chat_scanner.apps.bot.keyboards.common import helper_kbs
from chat_scanner.apps.merchant.gecko import Rate
from chat_scanner.db.models import Account, ProjectChat, Rates
from chat_scanner.db.models import User
from chat_scanner.db.models.user.account import AccountStatus, AccountType
from chat_scanner.init.dispatchers import run_dispatcher

if TYPE_CHECKING:
    from chat_scanner.locales.stubs.ru.stub import TranslatorRunner

on = Router()


def clear_string(string: str) -> str:
    return (
        string
        .replace("\u2069", "")
        .replace("\u2068", "")
        .strip()
    )


def back_to_connect_rm(l10n):
    return helper_kbs.custom_back_kb(l10n.get("button-back"), cd=AccountCallback.connect())


@on.callback_query(AccountCallback.filter(F.action == AccountAction.CONNECT))
async def connect(
        call: types.CallbackQuery,
        session: AsyncSession,
        user: User,
        edit: Callable,
        l10n: TranslatorRunner,
        state: FSMContext
):
    if user.rate not in (Rates.DEMO, Rates.PRO):
        return await call.answer(l10n.get("account-connect-error-rates"))

    await state.clear()
    await session.refresh(user, {"accounts"})
    await state.update_data(prev_msg=call.message)
    await call.message.edit_text(
        l10n.get("account-connect-api_id"),
        reply_markup=helper_kbs.custom_back_kb(cd=BaseCommands.CONNECT_ACCOUNTS.command)
    )
    await state.set_state("account-connect-api_id")


@on.message(StateFilter("account-connect-api_id"))
async def connect_api_id(
        msg: types.Message,
        edit: Callable,
        l10n: TranslatorRunner,
        state: FSMContext
):
    api_id = clear_string(msg.text)

    if not api_id.isdigit():
        return msg.answer(l10n.get("account-connect-api_id-invalid"))

    await msg.delete()
    api_id = int(api_id)
    data = await state.update_data(api_id=api_id)
    prev_msg: types.Message = data.get("prev_msg")
    await prev_msg.edit_text(
        l10n.get("account-connect-api_hash"),
        reply_markup=back_to_connect_rm(l10n)
    )
    await state.set_state("account-connect-api_hash")


@on.message(StateFilter("account-connect-api_hash"))
async def connect_api_hash(
        msg: types.Message,
        edit: Callable,
        l10n: TranslatorRunner,
        state: FSMContext
):
    api_hash = clear_string(msg.text)
    if not api_hash.isalnum():
        return msg.answer(l10n.get("account-connect-api_hash-invalid"))

    await msg.delete()
    data = await state.update_data(api_hash=api_hash)
    prev_msg: types.Message = data.get("prev_msg")
    await prev_msg.edit_text(
        l10n.get("account-connect-phone"),
        reply_markup=back_to_connect_rm(l10n)
    )
    await state.set_state("account-connect-phone")


@on.message(StateFilter("account-connect-phone"))
async def connect_phone(
        msg: types.Message,
        bot: Bot,
        edit: Callable,
        user: User,
        session: AsyncSession,
        account_dispatchers: dict[int, Dispatcher],
        l10n: TranslatorRunner,
        state: FSMContext
):
    # if not msg.text.isdigit():
    #     return msg.answer(l10n.get("account-connect-phone-invalid"))
    phone_number = clear_string(msg.text)
    data = await state.update_data(phone=phone_number)
    await msg.delete()
    prev_msg: types.Message = data.get("prev_msg")
    await prev_msg.edit_text(
        l10n.get("account-connect-loading"),
        reply_markup=back_to_connect_rm(l10n)
    )
    api_id = data["api_id"]
    api_hash = data["api_hash"]
    phone_number = data["phone"]

    api_data = Account.encode_api_data(api_id, api_hash)
    account = await Account.get_or_none(session, api_data=api_data)
    # if account:
    #     await message.answer(l10n.account.bind.already_exists())
    #     await state.clear()
    #     return
    account_exists = False
    if account:
        account_exists = True

    if not account:
        account = Account(
            user=user,
            phone_number=phone_number,
            api_data=api_data,
        )

    logger.info(f"{user.username}| Полученные данные {api_id}|{api_hash}|{phone_number}")

    queue = asyncio.Queue()
    await state.update_data(queue=queue)
    client = Client(
        api_id=api_id,
        api_hash=api_hash,
        phone_number=phone_number,
        phone_code=lambda: _get_code_callback(queue, phone_number, prev_msg, l10n, state),
        password=lambda: _get_password_callback(queue, phone_number, prev_msg, l10n, state),
        phone_number_error=partial(_error_callback, "phone", prev_msg, l10n),
        phone_code_error=partial(_error_callback, "code", prev_msg, l10n),
        password_error=partial(_error_callback, "password", prev_msg, l10n),
        timeout=120,
        in_memory=True,
    )
    try:
        logger.info("Запуск регистрации {user}", user=user)
        async with Dispatcher(client, bot, account) as dispatcher:
            account_user = await dispatcher.client.get_me()
            session_string = await dispatcher.client.export_session_string()
            account.update(**account_user.__dict__, session_string=session_string)
            account.status = AccountStatus.ACTIVE
            account.is_admin = False

            await user.update_account_sender_receiver(session, account, account_dispatchers)

            if not account_exists:
                session.add(account)

        await prev_msg.edit_text(
            l10n.get("account-connect-success")
        )
        await session.commit()
        logger.info(f"{user.username}| Аккаунт успешно привязан")
        await session.refresh(account)
        await session.refresh(user)
        dispatcher = await run_dispatcher(account, bot)
        if old_dispatcher := account_dispatchers.get(account.id):
            try:
                await old_dispatcher.stop()
            except Exception as e:
                logger.warning(e)

        account_dispatchers[account.id] = dispatcher
        logger.success(f"{user.username}| Диспетчер запущен")

        await connect_accounts(msg, msg.answer, user, l10n, state)

    except asyncio.exceptions.TimeoutError:
        logger.info(f"{user.username}| Время ожидания кода истекло")
        await msg.answer(l10n.account.bind.timeout())

    await state.clear()


async def _error_callback(
        state_str: str,
        message: types.Message,
        l10n: TranslatorRunner,
        error_text: str,
):
    sm = await message.answer(
        l10n.get(f"account-connect-{state_str}-invalid"),
    )

    async def delay_delete():
        await asyncio.sleep(3)
        await sm.delete()

    _task = asyncio.create_task(delay_delete())


async def _get_code_callback(
        queue: asyncio.Queue,
        phone_number: str,
        message: types.Message,
        l10n: TranslatorRunner,
        state: FSMContext
):
    await state.set_state("account-connect-code")
    await message.edit_text(l10n.get("account-connect-code"))
    logger.info(f"Ожидание кода {message.from_user.id}")
    return queue


@on.message(StateFilter("account-connect-code"))
async def get_code(
        message: types.Message,
        l10n: TranslatorRunner,
        state: FSMContext,
):
    code = message.text
    if not code.isdigit():
        return await message.answer(l10n.get("account-connect-code-invalid"))

    await message.delete()
    data = await state.get_data()

    prev_msg: types.Message = data.get("prev_msg")
    await prev_msg.edit_text(
        l10n.get("account-connect-loading"),
        reply_markup=back_to_connect_rm(l10n)
    )

    queue: asyncio.Queue = data.get("queue")
    await queue.put(code)


async def _get_password_callback(
        queue: asyncio.Queue,
        phone_number: str,
        message: types.Message,
        l10n: TranslatorRunner,
        state: FSMContext
):
    await state.set_state("account-connect-password")
    await message.edit_text(l10n.get("account-connect-password"))
    logger.info(f"Ожидание пароля {message.from_user.id}")
    return queue


@on.message(StateFilter("account-connect-password"))
async def get_password(
        message: types.Message,
        state: FSMContext,
        l10n: TranslatorRunner
):
    password = message.text

    data = await state.get_data()
    prev_msg: types.Message = data.get("prev_msg")
    await prev_msg.edit_text(
        l10n.get("account-connect-loading"),
        reply_markup=back_to_connect_rm(l10n)
    )
    queue: asyncio.Queue = data.get("queue")
    await queue.put(password)
    await message.delete()
