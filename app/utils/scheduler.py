from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from app.core import logger
from app.core import GoogleSheetsClient
import time
import json
import datetime
import os



CACHE_FILE = "cache.json"
async def update_cache():
    gsheets_client = GoogleSheetsClient(credentials_json='app/core/eco-item-search-1fe29998ddf9.json', sheet_name='База')
    gsheets_client2 = GoogleSheetsClient(credentials_json='app/core/eco-item-search-1fe29998ddf9.json', sheet_name='Категория А 36')
    data = await gsheets_client.get_all_records_from_all_sheets()
    data2 = await gsheets_client2.get_all_records_from_all_sheets()
    timestamp = time.time()
    data = data + data2
    # Сохраняем данные в файл
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"data": data, "timestamp": timestamp}, f, ensure_ascii=False, indent=4)


class CacheUpdater:
    def __init__(self, update_time="03:00"):
        self.scheduler = AsyncIOScheduler()
        hours, minutes = map(int, update_time.split(":"))
        self.scheduler.add_job(self.update_cache_task, trigger=CronTrigger(hour=hours, minute=minutes))
        if not os.path.exists(CACHE_FILE):
            nrt = datetime.datetime.now() + datetime.timedelta(seconds=10)
            self.scheduler.add_job(self.update_cache_task, next_run_time=nrt)  # Немедленный запуск

    async def update_cache_task(self):
        logger.info("Cache update started")
        await update_cache()
        logger.info("Cache file updated")

    async def start(self):
        self.scheduler.start()
        logger.info("Cache update planner started")


class BackupUpdater:
    def __init__(self, update_time="04:00"):
        self.scheduler = AsyncIOScheduler()
        self.gsheet_client = GoogleSheetsClient(credentials_json='app/core/eco-item-search-1fe29998ddf9.json', sheet_name='База')
        hours, minutes = map(int, update_time.split(":"))
        self.scheduler.add_job(self.update_sheet_task, trigger=CronTrigger(hour=hours, minute=minutes))
        # self.scheduler.add_job(self.update_sheet_task, next_run_time=datetime.datetime.now())

    async def update_sheet_task(self):
        logger.info("Sheet backup  update started")
        await self.gsheet_client.download_sheet_as_xlsx()
        logger.info("Sheet backup file updated")

    async def start(self):
        self.scheduler.start()
        logger.info("Sheet backup update planner started")