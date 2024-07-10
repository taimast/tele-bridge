from aiogram import Router

from . import get, create, update, delete

on = Router(name="account")
on.include_routers(
    get.on,
    create.on,
    update.on,
    delete.on
)
