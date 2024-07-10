from aiogram import Router

from . import crud

on = Router(name="account")

on.include_router(crud.on)
