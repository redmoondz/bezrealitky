"""Entrypoint: aiogram bot with browse/parser/charts handlers and the notify loop."""

from __future__ import annotations

import asyncio
import logging

from aiogram import Bot, Dispatcher

from . import config, notify_loop
from .handlers import browse, charts, parser, start
from .handlers.start import BOT_COMMANDS

LOGGER = logging.getLogger(__name__)


def build_dispatcher() -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher.include_router(start.router)
    dispatcher.include_router(browse.router)
    dispatcher.include_router(parser.router)
    dispatcher.include_router(charts.router)
    return dispatcher


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    if not config.BOT_TOKEN:
        raise SystemExit("TELEGRAM_BOT_API is not set")
    if not config.ALLOWED_USER_IDS:
        LOGGER.warning(
            "TELEGRAM_ALLOWED_USER_IDS is empty — every gated command will refuse to run "
            "until it's set."
        )

    bot = Bot(token=config.BOT_TOKEN)
    await bot.set_my_commands(BOT_COMMANDS)
    dispatcher = build_dispatcher()

    notify_task = asyncio.create_task(notify_loop.run(bot))
    try:
        await dispatcher.start_polling(bot)
    finally:
        notify_task.cancel()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
