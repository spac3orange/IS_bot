from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.filters import CommandStart, Command
from aiogram import Router, F
from aiogram.fsm.context import FSMContext

from app.core.logger import logger
from app.core import aiogram_bot
from app.states import SearchQuery
from app.core import GoogleSheetsClient
from pprint import pprint
import time
import json
import os
from app.keyboards import main_kb
from typing import List

router = Router()

CACHE_FILE = "cache.json"  # Путь к файлу, где будет храниться кэш
CACHE_LIFETIME = 7200  # Время жизни кэша (в секундах) — 2 часа

async def analyze_prices(prices_list: List):
    if not prices_list:
        return "Список пуст"

    max_num = max(prices_list)
    min_num = min(prices_list)
    avg_num = sum(prices_list) / len(prices_list)

    return max_num, min_num, avg_num


async def update_cache():
    """Функция для обновления кэша и записи в файл JSON."""
    gsheets_client = GoogleSheetsClient(credentials_json='app/core/eco-item-search-1fe29998ddf9.json', sheet_name='База')
    data = await gsheets_client.get_all_records_from_all_sheets()
    timestamp = time.time()

    # Сохраняем данные в файл
    with open(CACHE_FILE, 'w', encoding='utf-8') as f:
        json.dump({"data": data, "timestamp": timestamp}, f, ensure_ascii=False, indent=4)


async def get_cached_data():
    """Возвращает данные из кэша, обновляет их при необходимости."""
    # Проверяем наличие файла кэша и его актуальность
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
            logger.info('getting cached data')
            return cache["data"]
    else:
        # Если кэш не существует, обновляем его
        logger.info('creating cache file')
        await update_cache()
        return await get_cached_data()


@router.message(Command(commands='start'))
async def process_start(message: Message, state: FSMContext):
    await state.clear()
    uname = message.from_user.username
    logger.info(f'user {uname} connected')
    await message.answer('<b>Выберите тип поиска:</b> ', reply_markup=main_kb.search_by(), parse_mode='HTML')

@router.callback_query(F.data == 'search_model')
async def search_model(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer('Введите модель: ')
    await state.set_state(SearchQuery.input_model)

@router.callback_query(F.data == 'search_code')
async def search_code(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer('Введите штрихкод: ')
    await state.set_state(SearchQuery.input_code)

@router.message(SearchQuery.input_code)
async def search_bycode(message: Message, state: FSMContext):
    try:
        uname = message.from_user.username
        uid = message.from_user.id
        logger.info(f'user {uname} searching: {message.text}')
        smessage = await message.answer('Идет поиск...')
        if len(message.text) <= 1:
            await message.answer('Ошибка'
                                 '\nКод должен состоять минимум из <b>2 символов</b>'
                                 '\nВведите штрихкод:', parse_mode='HTML')
            return
        item_name = int(message.text)
        gsheets_client = GoogleSheetsClient(credentials_json='app/core/eco-item-search-1fe29998ddf9.json', sheet_name='База')
        data = await get_cached_data()
        match_found = False
        price_list = []
        for d in data:
            try:
                for k, v in d.items():
                    # print(k)
                    # pprint(v)
                    for i in v:
                        for key, value in i.items():
                            if key == 'Штрих-код производителя' or key == 'Штрихкод производителя':
                                if item_name == value:
                                    match_found = True
                                    rrc = i.get("РРЦ", "Нет")
                                    if rrc == 'Нет':
                                        pass
                                    else:
                                        price_list.append(int(rrc))
                                    code = i.get("Штрих-код производителя") or i.get("Штрихкод производителя") or "Нет"
                                    link = f'<a href="{i.get("Ссылка", "Нет")}">открыть в браузере</a>'
                                    await message.answer('<b>Найдено совпадение</b>'
                                                         f'\n<b>Вкладка:</b> {k}'
                                                         f'\n\n<b>Наименование:</b> <code>{i.get('Наименование', 'Нет')}</code>'
                                                         f'\n<b>РРЦ:</b> <code>{i.get("РРЦ", "Нет")}</code>'
                                                         f'\n<b>Ссылка:</b> <b>{link}</b>'
                                                         f'\n<b>Штрих-код производителя:</b> <code>{code}</code>',
                                                         disable_web_page_preview=True, parse_mode='HTML')

            except Exception as e:
                logger.error(f'Iteration failed: {e}')
                continue

        links = {'ya': f'https://ya.ru/search/?text={item_name}',
                 'wb': f'https://www.wildberries.ru/catalog/0/search.aspx?search={item_name}',
                 'ozon': f'https://www.ozon.ru/search/?text={item_name}',
                 'eld': f'https://www.eldorado.ru/search/catalog.php?q={item_name}&utf',
                 'dns': f'https://www.dns-shop.ru/search/?q={item_name}',
                 'instr': f'https://www.vseinstrumenti.ru/search/?what={item_name}',
                 'market': f'https://market.yandex.ru/search?text={item_name}'
                 }
        if match_found:
            maxp, minp, avg = await analyze_prices(price_list)
            await message.answer(f'<b>Анализ РРЦ из найденных записей ({len(price_list)}):</b>'
                                 f'\n\n<b>Максимальная:</b> <code>{maxp}</code>'
                                 f'\n<b>Минимальная:</b> <code>{minp}</code>'
                                 f'\n<b>Средняя:</b> <code>{avg}</code>'
                                 f'\n\nПоиск на маркетплейсах по запросу <b><code>{item_name}</code></b>:'
                                 f'\n<b><a href="{links['ya']}">Яндекс</a></b>'
                                 f'\n<b><a href="{links['wb']}">Wildberries</a></b>'
                                 f'\n<b><a href="{links['ozon']}">Ozon</a></b>'
                                 f'\n<b><a href="{links['market']}">Яндекс Маркет</a></b>'
                                 f'\n<b><a href="{links['eld']}">Эльдорадо</a></b>'
                                 f'\n<b><a href="{links['dns']}">DNS</a></b>'
                                 f'\n<b><a href="{links['instr']}">Все Инструменты</a></b>',
                                 parse_mode='HTML', disable_web_page_preview=True
                                 )

        elif not match_found:
            # await aiogram_bot.delete_message(message.chat.id, smessage)
            await state.clear()
            await message.answer('<b>Данные не найдены</b>'
                                 f'\n\nПоиск на маркетплейсах по запросу <b><code>{item_name}</code></b>:'
                                 f'\n<b><a href="{links['ya']}">Яндекс</a></b>'
                                 f'\n<b><a href="{links['wb']}">Wildberries</a></b>'
                                 f'\n<b><a href="{links['ozon']}">Ozon</a></b>'
                                 f'\n<b><a href="{links['market']}">Яндекс Маркет</a></b>'
                                 f'\n<b><a href="{links['eld']}">Эльдорадо</a></b>'
                                 f'\n<b><a href="{links['dns']}">DNS</a></b>'
                                 f'\n<b><a href="{links['instr']}">Все Инструменты</a></b>',
                                 parse_mode='HTML', disable_web_page_preview=True)

    except Exception as e:
        logger.error(f'Ошибка поиска {item_name}: {e}')
        await message.answer(f'Ошибка поиска {item_name}. Попробуйте еще раз.')
    finally:
        await process_start(message, state)


@router.message(SearchQuery.input_model)
async def search_bymodel(message: Message, state: FSMContext):
    try:
        smessage = await message.answer('Идет поиск...')
        uname = message.from_user.username
        uid = message.from_user.id
        item_name = message.text
        logger.info(f'user {uname} searching: {item_name}')
        if len(item_name) <= 1:
            await message.answer('\nОшибка'
                                 '\nМодель должна состоять минимум из <b>2-х символов</b>'
                                 '\nВведите модель:', parse_mode='HTML')
            return
        gsheets_client = GoogleSheetsClient(credentials_json='app/core/eco-item-search-1fe29998ddf9.json', sheet_name='База')
        data = await get_cached_data()
        match_found = False
        price_list = []
        for d in data:
            try:
                for k, v in d.items():
                    # print(k)
                    # pprint(v)
                    for i in v:
                        for key, value in i.items():
                            # print(key, value)
                            if key == 'Наименование':
                                if isinstance(value, int):
                                    logger.error(f'Skipping value {value}: value is int')
                                    continue
                                    # пропуск итерации если значение состоит только из цифр
                                elif item_name.lower() in value.lower():
                                    match_found = True
                                    rrc = i.get("РРЦ", "Нет")
                                    if rrc == 'Нет':
                                        pass
                                    else:
                                        price_list.append(int(rrc))
                                    code = i.get("Штрих-код производителя") or i.get("Штрихкод производителя") or "Нет"
                                    link = f'<a href="{i.get("Ссылка", "Нет")}">открыть в браузере</a>'
                                    await message.answer('<b>Найдено совпадение</b>'
                                                         f'\n<b>Вкладка:</b> {k}'
                                                         f'\n\n<b>Наименование:</b> <code>{i.get('Наименование', 'Нет')}</code>'
                                                         f'\n<b>РРЦ:</b> <code>{i.get("РРЦ", "Нет")}</code>'
                                                         f'\n<b>Ссылка:</b> <b>{link}</b>'
                                                         f'\n<b>Штрих-код производителя:</b> <code>{code}</code>',
                                                         disable_web_page_preview=True, parse_mode='HTML')
            except Exception as e:
                logger.error(f'Iteration failed: {e}')
                continue

                            # elif key == 'Штрих-код производителя':
                            #     if item_name.isdigit():
                            #         item_name_int = int(item_name)
                            #         if item_name_int == value:
                            #             await message.answer('<b>Найдено совпадение</b>'
                            #                                  f'\n\n<b>Вкладка:</b> {k}'
                            #                                  f'\n<b>Наименование:</b> {i.get('Наименование'), 'Нет'}'
                            #                                  f'\n<b>РРЦ:</b> {i.get("РРЦ", "Нет")}'
                            #                                  f'\n<b>Ссылка:</b> {i.get("Ссылка", "Нет")}'
                            #                                  f'\n<b>Штрих-код производителя:</b> {i.get("Штрих-код производителя", "Нет")}',
                            #                                  disable_web_page_preview=True, parse_mode='HTML')
                            #     elif item_name.lower() in value.lower():
                            #         await message.answer('<b>Найдено совпадение</b>'
                            #                              f'\n\n<b>Вкладка:</b> {k}'
                            #                              f'\n<b>Наименование:</b> {i.get('Наименование'), 'Нет'}'
                            #                              f'\n<b>РРЦ:</b> {i.get("РРЦ", "Нет")}'
                            #                              f'\n<b>Ссылка:</b> {i.get("Ссылка", "Нет")}'
                            #                              f'\n<b>Штрих-код производителя:</b> {i.get("Штрих-код производителя", "Нет")}',
                            #                              disable_web_page_preview=True, parse_mode='HTML')

        links = {'ya': f'https://ya.ru/search/?text={item_name}',
                 'wb': f'https://www.wildberries.ru/catalog/0/search.aspx?search={item_name}',
                 'ozon': f'https://www.ozon.ru/search/?text={item_name}',
                 'eld': f'https://www.eldorado.ru/search/catalog.php?q={item_name}&utf',
                 'dns': f'https://www.dns-shop.ru/search/?q={item_name}',
                 'instr': f'https://www.vseinstrumenti.ru/search/?what={item_name}',
                 'market': f'https://market.yandex.ru/search?text={item_name}'
                 }
        if match_found:
            maxp, minp, avg = await analyze_prices(price_list)
            await message.answer(f'\n<b>Анализ РРЦ из найденных записей ({len(price_list)}):</b>'
                                 f'\n\n<b>Максимальная:</b> <code>{maxp}</code>'
                                 f'\n<b>Минимальная:</b> <code>{minp}</code>'
                                 f'\n<b>Средняя:</b> <code>{avg}</code>'
                                 f'\n\nПоиск на маркетплейсах по запросу <b><code>{item_name}</code></b>:'
                                 f'\n<b><a href="{links['ya']}">Яндекс</a></b>'
                                 f'\n<b><a href="{links['wb']}">Wildberries</a></b>'
                                 f'\n<b><a href="{links['ozon']}">Ozon</a></b>'
                                 f'\n<b><a href="{links['market']}">Яндекс Маркет</a></b>'
                                 f'\n<b><a href="{links['eld']}">Эльдорадо</a></b>'
                                 f'\n<b><a href="{links['dns']}">DNS</a></b>'
                                 f'\n<b><a href="{links['instr']}">Все Инструменты</a></b>',
                                 parse_mode='HTML', disable_web_page_preview=True
                                 )
        if not match_found:
            # await aiogram_bot.delete_message(message.chat.id, smessage)
            await state.clear()
            await message.answer('<b>Данные не найдены</b>'
                                 f'\n\nПоиск на маркетплейсах по запросу <b><code>{item_name}</code></b>:'
                                 f'\n<b><a href="{links['ya']}">Яндекс</a></b>'
                                 f'\n<b><a href="{links['wb']}">Wildberries</a></b>'
                                 f'\n<b><a href="{links['ozon']}">Ozon</a></b>'
                                 f'\n<b><a href="{links['market']}">Яндекс Маркет</a></b>'
                                 f'\n<b><a href="{links['eld']}">Эльдорадо</a></b>'
                                 f'\n<b><a href="{links['dns']}">DNS</a></b>'
                                 f'\n<b><a href="{links['instr']}">Все Инструменты</a></b>',
                                 parse_mode='HTML', disable_web_page_preview=True)
    except Exception as e:
        logger.error(f'Ошибка поиска {item_name}: {e}')
        await message.answer(f'Ошибка поиска {item_name}. Попробуйте еще раз.')
    finally:
        await process_start(message, state)