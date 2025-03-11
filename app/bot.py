import asyncio
from aiogram import Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from app.core import aiogram_bot
from app.core.logger import logger
from app.handlers import start
from app.utils import CacheUpdater, BackupUpdater
from app.core import GoogleSheetsClient


async def start_params() -> None:
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(start.router)

    logger.info('Bot started')

    # Пропускаем накопившиеся апдейты и запускаем polling
    await aiogram_bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(aiogram_bot)


async def main():
    cache_updater = CacheUpdater('06:00')
    backup_client = BackupUpdater('07:00')
    task1 = asyncio.create_task(start_params())
    task2 = asyncio.create_task(cache_updater.start())
    task3 = asyncio.create_task(backup_client.start())
    await asyncio.gather(task1, task2, task3)


if __name__ == '__main__':
    asyncio.run(main())
