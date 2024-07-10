from __future__ import annotations

from typing import TYPE_CHECKING, Callable

from aiogram import Router, types
from aiogram.filters import Text, Command
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession

from chat_scanner.apps.bot.commands.bot_commands import BaseCommands
from chat_scanner.apps.bot.keyboards.common import account_kbs
from chat_scanner.db.models import User

if TYPE_CHECKING:
    from chat_scanner.locales.stubs.ru.stub import TranslatorRunner

on = Router()


@on.callback_query(Text(BaseCommands.CONNECT_ACCOUNTS.command))
@on.message(Command(BaseCommands.CONNECT_ACCOUNTS))
async def connect_accounts(
        message: types.Message | types.CallbackQuery,
        edit: Callable,
        user: User,
        l10n: TranslatorRunner,
        state: FSMContext
):
    await state.clear()
    accounts = await user.get_not_admin_accounts()
    await edit(
        l10n.get("account-connect"),
        reply_markup=account_kbs.connects_accounts(accounts, l10n)
    )
