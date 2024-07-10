from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Callable

from aiogram import F, Router, types
from aiogram.fsm.context import FSMContext
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from chat_scanner.apps.account.dispatcher import Dispatcher
from chat_scanner.apps.bot.callback_data.account import AccountAction, AccountCallback
from chat_scanner.apps.bot.callback_data.base_callback import Action
from chat_scanner.apps.bot.handlers.common.project.connect.connect import send_connect_group_message
from chat_scanner.apps.bot.handlers.common.project.connect.sender import  get_min_projects_account_and_dispatcher, project_connect_new_account
from chat_scanner.apps.bot.keyboards.common import account_kbs, common_kbs
from chat_scanner.db.models import Account, Project, User

if TYPE_CHECKING:
    from chat_scanner.locales.stubs.ru.stub import TranslatorRunner

on = Router()


@on.callback_query(AccountCallback.filter(F.action == AccountAction.UNBIND))
async def unbind_account(
        call: types.CallbackQuery,
        session: AsyncSession,
        callback_data: AccountCallback,
        l10n: TranslatorRunner,
        state: FSMContext,
):
    await state.clear()
    account = await Account.get_or_none(session, id=callback_data.id)
    if not account:
        # await call.message.answer(l10n("account-not-found"))
        await call.message.answer(l10n.account.not_found())
        return
    account_str = account.pretty(l10n)
    await call.message.answer(
        # l10n("unbind-account-confirm", {"identifier": account.identifier}),
        l10n.account.unbind.confirm(account=account_str),
        reply_markup=account_kbs.unbind_account(account, l10n, ),
    )


async def reconnect_projects_to_another_account(
        answer: Callable,
        session: AsyncSession,
        projects: list[Project],
        l10n: TranslatorRunner,
        user: User,
        account_dispatchers: dict[int, Dispatcher],
):
    account, dispatcher = await get_min_projects_account_and_dispatcher(
        answer, session, user, l10n, account_dispatchers
    )
    if not account or not dispatcher:
        return

    for nut, project in enumerate(projects, 1):
        try:
            is_connect = await project_connect_new_account(
                answer,
                project,
                dispatcher,
                account,
            )
            if not is_connect:
                return
            dispatcher, account = is_connect

            if not account.is_admin:
                account.type = None

            await session.commit()
            await session.refresh(account)
            await session.refresh(project)
            dispatcher.account = account
            success_message = l10n.project.connect.sender.success(name=project.name)
            await answer(success_message)
            await dispatcher.update_account(session)

            await send_connect_group_message(answer, project, l10n)

        except Exception as e:
            logger.exception(e)
            await answer(f"Ошибка переключения проекта {project.name}")
        await answer(f"Проектов переключено {nut} из {len(projects)}")
        await asyncio.sleep(5)


@on.callback_query(AccountCallback.filter(F.action == Action.DELETE))
async def delete_account(
        call: types.CallbackQuery,
        session: AsyncSession,
        callback_data: AccountCallback,
        user: User,
        l10n: TranslatorRunner,
        account_dispatchers: dict[int, Dispatcher],
        state: FSMContext,
):
    await state.clear()

    account = await Account.get(session, id=callback_data.id)
    await account.remove(session, account_dispatchers)
    await session.commit()

    if account.is_admin:
        await call.message.answer(
            "Аккаунт удален",
            reply_markup=common_kbs.custom_back_kb(cb="admin")
        )
        await call.message.answer(
            f"Переключение проектов на другой аккаунт"
        )
        projects = await Project.filter(session, Project.sender_id == None)

    else:
        projects = await user.awaitable_attrs.projects

    await reconnect_projects_to_another_account(
        call.message.answer,
        session,
        projects,
        l10n,
        user,
        account_dispatchers,
    )
    await call.message.answer("Переключение проектов завершено")
