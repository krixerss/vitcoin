"""
Emoji Pack Creator Bot - SuperGram
"""

import os
import re
import random
import logging
import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8514454295:AAGOufeY-pO9ixKBdiPZz6mJ4gO1hQIvCMs"

storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

COLORFUL_PATH = "colorful"   # 14 файлов: 001-014 → буквы A-N + цифры
MONOTONE_PATH = "monotone"   # 56 файлов: разбиты по стилям

# ═══════════════════════════════════════════════════════
# МАППИНГ БУКВ НА ФАЙЛЫ
# Разноцветных 14 файлов → каждый файл = одна позиция алфавита
# ═══════════════════════════════════════════════════════

# A=001, B=002 ... N=014, цифры по кругу
COLORFUL_CHAR_MAP = {
    'A': '001', 'B': '002', 'C': '003', 'D': '004', 'E': '005',
    'F': '006', 'G': '007', 'H': '008', 'I': '009', 'J': '010',
    'K': '011', 'L': '012', 'M': '013', 'N': '014',
    # Буквы после N — идём по кругу
    'O': '001', 'P': '002', 'Q': '003', 'R': '004', 'S': '005',
    'T': '006', 'U': '007', 'V': '008', 'W': '009', 'X': '010',
    'Y': '011', 'Z': '012',
    # Цифры
    '0': '001', '1': '002', '2': '003', '3': '004', '4': '005',
    '5': '006', '6': '007', '7': '008', '8': '009', '9': '010',
}

# Однотонных 56 файлов делим на 6 стилей по ~9 файлов
# Каждый стиль занимает свой диапазон файлов
MONOTONE_STYLE_RANGES = {
    'black':  list(range(1,  10)),   # 001-009
    'cosmos': list(range(10, 19)),   # 010-018
    'sakura': list(range(19, 28)),   # 019-027
    'ocean':  list(range(28, 37)),   # 028-036
    'sunset': list(range(37, 47)),   # 037-046
    'forest': list(range(47, 57)),   # 047-056
}

# Внутри каждого стиля: буква → индекс в диапазоне (0-8, по кругу)
def get_monotone_file(char: str, style: str) -> str:
    """Получить файл однотонного эмодзи для символа и стиля"""
    char_upper = char.upper()
    
    # Определяем позицию символа
    if char_upper.isalpha():
        pos = ord(char_upper) - ord('A')  # A=0, B=1 ... Z=25
    elif char_upper.isdigit():
        pos = int(char_upper) + 26  # 0=26, 1=27 ... 9=35
    else:
        pos = 0
    
    # Берём диапазон файлов для стиля
    file_range = MONOTONE_STYLE_RANGES.get(style, MONOTONE_STYLE_RANGES['black'])
    
    # Берём файл по позиции (по кругу внутри диапазона)
    file_idx = pos % len(file_range)
    file_num = file_range[file_idx]
    
    return os.path.join(MONOTONE_PATH, f"{file_num:03d}.tgs")

def get_colorful_file(char: str) -> str:
    """Получить файл разноцветного эмодзи для символа"""
    char_upper = char.upper()
    file_num = COLORFUL_CHAR_MAP.get(char_upper, '001')
    return os.path.join(COLORFUL_PATH, f"{file_num}.tgs")

# ═══════════════════════════════════════════════════════
# UNICODE ЭМОДЗИ (Telegram требует настоящий эмодзи)
# ═══════════════════════════════════════════════════════

CHAR_TO_EMOJI = {
    'A': '🅰️', 'B': '🅱️', 'C': '©️',  'D': '↩️', 'E': '📧',
    'F': '🎏', 'G': '⛽', 'H': '♨️', 'I': 'ℹ️', 'J': '🎷',
    'K': '🎋', 'L': '🔋', 'M': '〽️', 'N': '🆕', 'O': '⭕',
    'P': '🅿️', 'Q': '🔍', 'R': '®️', 'S': '💲', 'T': '✝️',
    'U': '⛎', 'V': '✌️', 'W': '🌊', 'X': '❌', 'Y': '✌️',
    'Z': '💤',
    '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
    '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣',
}

def get_emoji_for_char(char: str) -> str:
    return CHAR_TO_EMOJI.get(char.upper(), '⭐')

# ═══════════════════════════════════════════════════════
# РАНДОМНЫЕ НАЗВАНИЯ
# ═══════════════════════════════════════════════════════

ADJECTIVES = ["Cosmic", "Neon", "Shadow", "Galaxy", "Storm", "Pixel",
              "Vibe", "Dark", "Fire", "Ice", "Dream", "Cyber", "Mystic",
              "Solar", "Nova", "Blaze", "Frost", "Drift", "Echo", "Glow"]
NOUNS = ["Pack", "Set", "Vibes", "World", "Zone", "Space", "Pulse",
         "Wave", "Flow", "Beat", "Core", "Mode", "Style", "Club", "Gang"]

def gen_random_name() -> str:
    return f"{random.choice(ADJECTIVES)} {random.choice(NOUNS)} {random.randint(10,99)}"

# ═══════════════════════════════════════════════════════
# СТИЛИ
# ═══════════════════════════════════════════════════════

MONOTONE_STYLES = {
    "black":  "⬛ Черный",
    "cosmos": "🌌 Космос",
    "sakura": "🌸 Сакура",
    "ocean":  "🌊 Океан",
    "sunset": "🌅 Закат",
    "forest": "🌲 Лес",
}

# ═══════════════════════════════════════════════════════
# СОСТОЯНИЯ
# ═══════════════════════════════════════════════════════

class EmojiCreation(StatesGroup):
    choosing_type = State()
    choosing_style = State()
    entering_text = State()
    entering_pack_name = State()

# ═══════════════════════════════════════════════════════
# КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════

def kb_type():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎨 Разноцветные", callback_data="type:colorful"),
            InlineKeyboardButton(text="⚫ Однотонные", callback_data="type:monotone"),
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])

def kb_style():
    rows = [[InlineKeyboardButton(text=name, callback_data=f"style:{sid}")]
            for sid, name in MONOTONE_STYLES.items()]
    rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_type")])
    rows.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_cancel():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def kb_name(rnd: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"🎲 {rnd}", callback_data="name:random")],
        [InlineKeyboardButton(text="⏭ Пропустить", callback_data="name:skip")],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")],
    ])

# ═══════════════════════════════════════════════════════
# СОЗДАНИЕ ПАКА
# ═══════════════════════════════════════════════════════

def make_short_name(title: str, user_id: int, bot_name: str) -> str:
    clean = re.sub(r'[^a-zA-Z0-9]', '_', title)
    clean = re.sub(r'_+', '_', clean).strip('_')[:15]
    return f"{clean}_{user_id}_by_{bot_name}"

async def build_pack(user_id: int, title: str, text: str, emoji_type: str, style: str = None):
    """Собирает и загружает эмодзи пак"""
    bot_info = await bot.get_me()
    short_name = make_short_name(title, user_id, bot_info.username)

    logger.info(f"▶ Создаю пак '{short_name}' | тип={emoji_type} | стиль={style} | текст={text}")

    stickers_info = []
    for char in text.upper():
        # Выбираем файл в зависимости от типа и стиля
        if emoji_type == "colorful":
            filepath = get_colorful_file(char)
        else:
            filepath = get_monotone_file(char, style or "black")

        # Проверяем что файл существует
        if not os.path.exists(filepath):
            logger.warning(f"⚠️ Файл не найден: {filepath}, беру первый доступный")
            fallback_dir = COLORFUL_PATH if emoji_type == "colorful" else MONOTONE_PATH
            files = sorted(os.listdir(fallback_dir))
            filepath = os.path.join(fallback_dir, files[0])

        emoji_char = get_emoji_for_char(char)
        stickers_info.append((filepath, emoji_char, char))
        logger.info(f"  {char} → {filepath} → {emoji_char}")

    # Создаём первый стикер (без него нельзя создать пак)
    fp0, em0, ch0 = stickers_info[0]
    await bot.create_new_sticker_set(
        user_id=user_id,
        name=short_name,
        title=title,
        stickers=[types.InputSticker(
            sticker=types.FSInputFile(fp0),
            emoji_list=[em0],
            format="animated",
        )],
        sticker_type="custom_emoji",
    )
    logger.info(f"✅ Пак создан, добавляю остальные {len(stickers_info)-1} стикеров...")

    # Добавляем остальные
    for fp, em, ch in stickers_info[1:]:
        await bot.add_sticker_to_set(
            user_id=user_id,
            name=short_name,
            sticker=types.InputSticker(
                sticker=types.FSInputFile(fp),
                emoji_list=[em],
                format="animated",
            ),
        )
        await asyncio.sleep(0.3)

    url = f"https://t.me/addemoji/{short_name}"
    logger.info(f"🎉 Готово: {url}")
    return url, len(stickers_info)

# ═══════════════════════════════════════════════════════
# HANDLERS
# ═══════════════════════════════════════════════════════

@dp.message(CommandStart())
async def cmd_start(msg: Message):
    await msg.answer(
        "🎨 <b>Emoji Pack Creator — SuperGram</b>\n\n"
        "Создаю кастомные эмодзи-паки для Telegram Premium! ⭐\n\n"
        "<b>Типы:</b>\n"
        "🎨 Разноцветные (14 уникальных эмодзи)\n"
        "⚫ Однотонные — 6 стилей:\n"
        "   ⬛ Черный • 🌌 Космос • 🌸 Сакура\n"
        "   🌊 Океан • 🌅 Закат • 🌲 Лес\n\n"
        "/create — Создать пак\n"
        "/help — Помощь"
    )

@dp.message(Command("help"))
async def cmd_help(msg: Message):
    await msg.answer(
        "📖 <b>Как создать эмодзи-пак:</b>\n\n"
        "1️⃣ /create\n"
        "2️⃣ Выбери тип (разноцветные / однотонные)\n"
        "3️⃣ Для однотонных — выбери стиль\n"
        "4️⃣ Введи текст до 10 символов (A-Z, 0-9)\n"
        "5️⃣ Введи название ИЛИ нажми 🎲 рандомное / ⏭ пропустить\n"
        "6️⃣ Получи ссылку на готовый пак! 🎉\n\n"
        "<b>Примеры:</b> <code>LOVE</code> <code>HELLO</code> <code>2024</code> <code>VIBES</code>"
    )

@dp.message(Command("create"))
async def cmd_create(msg: Message, state: FSMContext):
    await msg.answer(
        "🎨 <b>Выбери тип эмодзи:</b>",
        reply_markup=kb_type()
    )
    await state.set_state(EmojiCreation.choosing_type)

# --- CALLBACKS ---

@dp.callback_query(F.data == "cancel")
async def cb_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("❌ Отменено. Начни заново: /create")
    await cb.answer()

@dp.callback_query(F.data.startswith("type:"))
async def cb_type(cb: CallbackQuery, state: FSMContext):
    emoji_type = cb.data.split(":")[1]
    await state.update_data(emoji_type=emoji_type, style=None)

    if emoji_type == "colorful":
        await cb.message.edit_text(
            "🎨 <b>Разноцветные!</b>\n\n"
            "Введи текст (до 10 символов, A-Z, 0-9):\n"
            "Например: <code>LOVE</code> или <code>HELLO</code>",
            reply_markup=kb_cancel()
        )
        await state.set_state(EmojiCreation.entering_text)
    else:
        await cb.message.edit_text(
            "⚫ <b>Однотонные!</b>\n\nВыбери стиль:",
            reply_markup=kb_style()
        )
        await state.set_state(EmojiCreation.choosing_style)
    await cb.answer()

@dp.callback_query(F.data.startswith("style:"))
async def cb_style(cb: CallbackQuery, state: FSMContext):
    style = cb.data.split(":")[1]
    await state.update_data(style=style)
    await cb.message.edit_text(
        f"✅ Стиль: <b>{MONOTONE_STYLES[style]}</b>\n\n"
        "Введи текст (до 10 символов, A-Z, 0-9):\n"
        "Например: <code>LOVE</code> или <code>COOL</code>",
        reply_markup=kb_cancel()
    )
    await state.set_state(EmojiCreation.entering_text)
    await cb.answer()

@dp.callback_query(F.data == "back_type")
async def cb_back(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text("🎨 <b>Выбери тип эмодзи:</b>", reply_markup=kb_type())
    await state.set_state(EmojiCreation.choosing_type)
    await cb.answer()

@dp.message(EmojiCreation.entering_text)
async def handle_text(msg: Message, state: FSMContext):
    text = msg.text.strip()
    if not text:
        await msg.answer("❌ Текст пустой!", reply_markup=kb_cancel())
        return
    if len(text) > 10:
        await msg.answer("❌ Максимум 10 символов!", reply_markup=kb_cancel())
        return
    if not re.match(r'^[A-Za-z0-9]+$', text):
        await msg.answer(
            "❌ Только английские буквы и цифры!\n"
            "Например: <code>LOVE</code>",
            reply_markup=kb_cancel()
        )
        return

    rnd = gen_random_name()
    await state.update_data(text=text.upper(), random_name=rnd)
    await msg.answer(
        f"✅ Текст: <code>{text.upper()}</code>\n\n"
        "Введи название пака, нажми 🎲 для рандомного или ⏭ пропусти:",
        reply_markup=kb_name(rnd)
    )
    await state.set_state(EmojiCreation.entering_pack_name)

@dp.callback_query(F.data == "name:random")
async def cb_name_random(cb: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    name = data.get("random_name", gen_random_name())
    status = await cb.message.edit_text(f"🎲 Название: <b>{name}</b>\n\n⏳ Создаю пак...")
    await cb.answer()
    await do_create(status, state, name)

@dp.callback_query(F.data == "name:skip")
async def cb_name_skip(cb: CallbackQuery, state: FSMContext):
    name = gen_random_name()
    status = await cb.message.edit_text(f"⏭ Название: <b>{name}</b>\n\n⏳ Создаю пак...")
    await cb.answer()
    await do_create(status, state, name)

@dp.message(EmojiCreation.entering_pack_name)
async def handle_name(msg: Message, state: FSMContext):
    name = msg.text.strip()
    if len(name) < 3:
        await msg.answer("❌ Минимум 3 символа!", reply_markup=kb_cancel())
        return
    if len(name) > 64:
        await msg.answer("❌ Максимум 64 символа!", reply_markup=kb_cancel())
        return
    status = await msg.answer(f"📝 Название: <b>{name}</b>\n\n⏳ Создаю пак...")
    await do_create(status, state, name)

# ═══════════════════════════════════════════════════════
# СОЗДАНИЕ
# ═══════════════════════════════════════════════════════

async def do_create(status_msg: Message, state: FSMContext, pack_name: str):
    data = await state.get_data()
    emoji_type = data.get('emoji_type', 'colorful')
    style = data.get('style', 'black')
    text = data.get('text', 'HI')

    type_label = "🎨 Разноцветные" if emoji_type == "colorful" else f"⚫ {MONOTONE_STYLES.get(style,'')}"

    try:
        url, count = await build_pack(
            user_id=status_msg.chat.id,
            title=pack_name,
            text=text,
            emoji_type=emoji_type,
            style=style
        )
        await status_msg.edit_text(
            "🎉 <b>Пак создан!</b>\n\n"
            f"📦 <b>Название:</b> {pack_name}\n"
            f"🔤 <b>Текст:</b> <code>{text}</code>\n"
            f"🎨 <b>Тип:</b> {type_label}\n"
            f"📊 <b>Эмодзи:</b> {count} шт.\n\n"
            f"🔗 {url}\n\n"
            "⭐ Нужен Telegram Premium!\n"
            "Создать ещё? /create 🚀"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")
        await status_msg.edit_text(
            f"❌ <b>Ошибка:</b> {e}\n\nПопробуй ещё: /create"
        )
    finally:
        await state.clear()

# ═══════════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════════

async def main():
    logger.info("╔═══════════════════════════════════════╗")
    logger.info("║  🎨  Emoji Pack Creator — SuperGram   ║")
    logger.info("╚═══════════════════════════════════════╝")

    for path, label in [(COLORFUL_PATH, "Разноцветные"), (MONOTONE_PATH, "Однотонные")]:
        if os.path.exists(path):
            n = len([f for f in os.listdir(path) if f.endswith('.tgs')])
            logger.info(f"✅ {label}: {n} файлов")
        else:
            logger.warning(f"⚠️  Папка {path}/ не найдена!")

    info = await bot.get_me()
    logger.info(f"✅ Бот: @{info.username}")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Остановлен")
    except Exception as e:
        logger.error(f"❌ {e}")

