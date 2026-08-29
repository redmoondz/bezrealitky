"""Entrypoint: aiogram bot with browse/parser/charts handlers and the notify loop."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.exceptions import TelegramAPIError
from aiogram.types import BotCommandScopeChat, MenuButtonWebApp, WebAppInfo

from src import db

from . import config, notify_loop
from .handlers import browse, charts, parser, start
from .handlers.start import BOT_COMMANDS, bot_commands
from .middlewares import UserTrackingMiddleware

LOGGER = logging.getLogger(__name__)


async def _refresh_known_users_command_menus(bot: Bot) -> None:
    """Re-push every known user's own-language command menu.

    Telegram caches a per-chat command menu once ``set_my_commands`` is
    called with a chat scope (see ``handlers/start.py``'s
    ``_apply_language_choice``) — the default-scope call above only reaches
    chats that never got that per-chat override. Without this, a command
    added after a user's last language pick would never show up for them.
    """
    with db.connect() as conn:
        db.ensure_schema(conn)
        users = db.list_user_languages(conn)
    for telegram_user_id, language_code in users:
        try:
            await bot.set_my_commands(
                bot_commands(language_code), scope=BotCommandScopeChat(chat_id=telegram_user_id)
            )
        except TelegramAPIError as exc:
            LOGGER.warning("Could not refresh command menu for %s: %s", telegram_user_id, exc)


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    tracker = UserTrackingMiddleware()
    dispatcher.message.outer_middleware(tracker)
    dispatcher.callback_query.outer_middleware(tracker)
    dispatcher.include_router(start.router)
    dispatcher.include_router(browse.router)
    dispatcher.include_router(parser.router)
    dispatcher.include_router(charts.router)
    return dispatcher


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not config.BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_API is not set")
    if config.PUBLIC_ACCESS:
        LOGGER.warning(
            "TELEGRAM_PUBLIC_ACCESS is on — every gated command is open to any Telegram "
            "user, regardless of TELEGRAM_ALLOWED_USER_IDS."
        )
    elif not config.ALLOWED_USER_IDS:
        LOGGER.warning(
            "TELEGRAM_ALLOWED_USER_IDS is empty — every gated command will refuse to run "
            "until it's set."
        )

    bot = Bot(token=config.BOT_TOKEN)
    await bot.set_my_commands(BOT_COMMANDS)
    await _refresh_known_users_command_menus(bot)
    if config.WEBAPP_URL:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(text="Open App", web_app=WebAppInfo(url=config.WEBAPP_URL))
        )
    else:
        LOGGER.info("WEBAPP_URL is not set; the bot's menu button will not open the Mini App")
    dispatcher = build_dispatcher()

    notify_task = asyncio.create_task(notify_loop.run(bot))
    try:
        await dispatcher.start_polling(bot)
    finally:
        notify_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
