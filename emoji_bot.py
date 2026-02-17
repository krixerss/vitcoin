"""
Emoji Pack Creator Bot - Создание кастомных эмодзи-паков
"""

import os
import re
import random
import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = "8514454295:AAGOufeY-pO9ixKBdiPZz6mJ4gO1hQIvCMs"

storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

COLORFUL_PATH = "colorful"
MONOTONE_PATH = "monotone"

# Рандомные части для названий паков
RANDOM_NAME_PARTS = [
    "Cosmic", "Neon", "Shadow", "Galaxy", "Sakura", "Storm", "Pixel",
    "Vibe", "Dark", "Light", "Fire", "Ice", "Dream", "Vapor", "Cyber",
    "Mystic", "Solar", "Lunar", "Nova", "Blaze", "Frost", "Drift",
    "Echo", "Flux", "Glow", "Haze", "Iris", "Jade", "Kilo", "Lumen",
    "Moss", "Nexus", "Onyx", "Prism", "Quasar", "Rune", "Steel", "Tide"
]

# Правильные Unicode эмодзи для каждого символа
EMOJI_MAP = {
    'A': '🅰️', 'B': '🅱️', 'C': '🌊', 'D': '🔷', 'E': '📧',
    'F': '🎏', 'G': '🔰', 'H': '♓', 'I': 'ℹ️', 'J': '🎷',
    'K': '🔑', 'L': '🕹️', 'M': '〽️', 'N': '🆕', 'O': '⭕',
    'P': '🅿️', 'Q': '❓', 'R': '®️', 'S': '💲', 'T': '✝️',
    'U': '⛎', 'V': '✌️', 'W': '〰️', 'X': '❌', 'Y': '💛',
    'Z': '💤',
    '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
    '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣',
}

# Запасные эмодзи (если не нашли в карте)
FALLBACK_EMOJIS = ['⭐', '🔥', '💎', '🎯', '🚀', '💫', '✨', '🌟', '🎪', '🎨']

MONOTONE_STYLES = {
    "black":  "⬛ Черный",
    "cosmos": "🌌 Космос",
    "sakura": "🌸 Сакура",
    "ocean":  "🌊 Океан",
    "sunset": "🌅 Закат",
    "forest": "🌲 Лес"
}

def generate_random_name():
    """Генерация рандомного названия пака"""
    part1 = random.choice(RANDOM_NAME_PARTS)
    part2 = random.choice(RANDOM_NAME_PARTS)
    num = random.randint(10, 99)
    return f"{part1} {part2} {num}"

def get_emoji_for_char(char: str) -> str:
    """Получить правильный Unicode эмодзи для символа"""
    char_upper = char.upper()
    if char_upper in EMOJI_MAP:
        return EMOJI_MAP[char_upper]
    return random.choice(FALLBACK_EMOJIS)

class EmojiCreation(StatesGroup):
    choosing_type = State()
    choosing_style = State()
    entering_text = State()
    entering_pack_name = State()

def get_type_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎨 Разноцветные", callback_data="type:colorful"),
            InlineKeyboardButton(text="⚫ Однотонные", callback_data="type:monotone")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def get_style_keyboard():
    buttons = []
    for style_id, style_name in MONOTONE_STYLES.items():
        buttons.append([InlineKeyboardButton(text=style_name, callback_data=f"style:{style_id}")])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_type")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_cancel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def get_pack_name_keyboard(random_name: str):
    """Клавиатура при вводе названия - с кнопкой пропустить"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(
            text=f"🎲 Рандомное: {random_name}",
            callback_data="name:random"
        )],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])

def get_emoji_files(emoji_type: str):
    """Получить список файлов эмодзи"""
    path = COLORFUL_PATH if emoji_type == "colorful" else MONOTONE_PATH
    if not os.path.exists(path):
        logger.error(f"❌ Путь не существует: {path}")
        return []
    files = sorted([f for f in os.listdir(path) if f.endswith('.tgs')])
    logger.info(f"✅ Найдено {len(files)} файлов в {path}")
    return [os.path.join(path, f) for f in files]

def make_short_name(pack_name: str, user_id: int, bot_username: str) -> str:
    """Сделать правильное короткое имя для пака"""
    # Берем только латиницу и цифры из названия
    clean = re.sub(r'[^a-zA-Z0-9]', '_', pack_name)
    clean = re.sub(r'_+', '_', clean).strip('_')[:20]
    return f"{clean}_{user_id}_by_{bot_username}"

async def create_emoji_pack(user_id: int, pack_title: str, text: str, emoji_type: str):
    """Создание эмодзи-пака"""
    emoji_files = get_emoji_files(emoji_type)
    if not emoji_files:
        raise Exception("Файлы эмодзи не найдены!")

    bot_info = await bot.get_me()
    short_name = make_short_name(pack_title, user_id, bot_info.username)

    stickers = []
    for i, char in enumerate(text.upper()):
        if i >= len(emoji_files):
            break
        emoji_char = get_emoji_for_char(char)
        sticker_file = types.FSInputFile(emoji_files[i])
        stickers.append(types.InputSticker(
            sticker=sticker_file,
            emoji_list=[emoji_char],
            format="animated"
        ))

    logger.info(f"🔄 Создаю пак: {short_name} ({len(stickers)} стикеров)")
    logger.info(f"📝 Эмодзи для символов: {[get_emoji_for_char(c) for c in text.upper()]}")

    # Создаём пак с первым стикером
    await bot.create_new_sticker_set(
        user_id=user_id,
        name=short_name,
        title=pack_title,
        stickers=[stickers[0]],
        sticker_type="custom_emoji"
    )

    # Добавляем остальные
    for sticker in stickers[1:]:
        await bot.add_sticker_to_set(
            user_id=user_id,
            name=short_name,
            sticker=sticker
        )
        await asyncio.sleep(0.3)

    return f"https://t.me/addemoji/{short_name}", len(stickers)

# ═══ HANDLERS ═══════════════════════════════════════════════════

@dp.message(CommandStart())
async def start_cmd(message: Message):
    await message.answer(
        "🎨 <b>Emoji Pack Creator — SuperGram</b>\n\n"
        "Создаю кастомные эмодзи-паки для Telegram Premium! ⭐\n\n"
        "<b>Типы эмодзи:</b>\n"
        "🎨 Разноцветные\n"
        "⚫ Однотонные (6 стилей)\n\n"
        "<b>Стили однотонных:</b>\n"
        "⬛ Черный • 🌌 Космос • 🌸 Сакура\n"
        "🌊 Океан • 🌅 Закат • 🌲 Лес\n\n"
        "/create — Создать пак\n"
        "/help — Помощь"
    )

@dp.message(Command("help"))
async def help_cmd(message: Message):
    await message.answer(
        "📖 <b>Как создать эмодзи-пак:</b>\n\n"
        "1️⃣ /create\n"
        "2️⃣ Выбери тип (разноцветные/однотонные)\n"
        "3️⃣ Для однотонных — выбери стиль\n"
        "4️⃣ Введи текст до 10 символов (только A-Z, 0-9)\n"
        "5️⃣ Введи название пака ИЛИ нажми кнопку рандомного\n"
        "6️⃣ Получи ссылку на пак! 🎉\n\n"
        "<b>Примеры текста:</b>\n"
        "<code>LOVE</code> • <code>HELLO</code> • <code>2024</code> • <code>VIBES</code>"
    )

@dp.message(Command("create"))
async def create_cmd(message: Message, state: FSMContext):
    await message.answer(
        "🎨 <b>Выбери тип эмодзи:</b>\n\n"
        "🎨 <b>Разноцветные</b> — яркие и красочные\n"
        "⚫ <b>Однотонные</b> — стильные монохромные (6 стилей)",
        reply_markup=get_type_keyboard()
    )
    await state.set_state(EmojiCreation.choosing_type)

@dp.callback_query(F.data == "cancel")
async def cancel_cb(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("❌ Отменено. Начни заново: /create")
    await cb.answer()

@dp.callback_query(F.data.startswith("type:"))
async def type_cb(cb: CallbackQuery, state: FSMContext):
    emoji_type = cb.data.split(":")[1]
    await state.update_data(emoji_type=emoji_type)

    if emoji_type == "colorful":
        await cb.message.edit_text(
            "🎨 <b>Разноцветные выбраны!</b>\n\n"
            "Введи текст для эмодзи (до 10 символов, только A-Z и 0-9):\n\n"
            "Примеры: <code>LOVE</code>, <code>HELLO</code>, <code>2024</code>",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(EmojiCreation.entering_text)
    else:
        await cb.message.edit_text(
            "⚫ <b>Однотонные выбраны!</b>\n\nВыбери стиль:",
            reply_markup=get_style_keyboard()
        )
        await state.set_state(EmojiCreation.choosing_style)
    await cb.answer()

@dp.callback_query(F.data.startswith("style:"))
async def style_cb(cb: CallbackQuery, state: FSMContext):
    style = cb.data.split(":")[1]
    await state.update_data(style=style)
    await cb.message.edit_text(
        f"✅ <b>Стиль: {MONOTONE_STYLES[style]}</b>\n\n"
        "Введи текст для эмодзи (до 10 символов, только A-Z и 0-9):\n\n"
        "Примеры: <code>LOVE</code>, <code>HELLO</code>, <code>2024</code>",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EmojiCreation.entering_text)
    await cb.answer()

@dp.callback_query(F.data == "back_to_type")
async def back_cb(cb: CallbackQuery, state: FSMContext):
    await cb.message.edit_text(
        "🎨 <b>Выбери тип эмодзи:</b>",
        reply_markup=get_type_keyboard()
    )
    await state.set_state(EmojiCreation.choosing_type)
    await cb.answer()

@dp.message(EmojiCreation.entering_text)
async def text_handler(message: Message, state: FSMContext):
    text = message.text.strip()

    if len(text) > 10:
        await message.answer(
            "❌ Максимум 10 символов! Попробуй еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return

    if not text:
        await message.answer("❌ Текст не может быть пустым!", reply_markup=get_cancel_keyboard())
        return

    if not re.match(r'^[A-Za-z0-9]+$', text):
        await message.answer(
            "❌ Только английские буквы и цифры!\n"
            "Например: <code>LOVE</code> или <code>2024</code>",
            reply_markup=get_cancel_keyboard()
        )
        return

    await state.update_data(text=text.upper())

    # Генерируем рандомное название
    random_name = generate_random_name()
    await state.update_data(random_name=random_name)

    await message.answer(
        f"✅ <b>Текст:</b> <code>{text.upper()}</code>\n\n"
        "Введи название пака или нажми кнопку для рандомного:",
        reply_markup=get_pack_name_keyboard(random_name)
    )
    await state.set_state(EmojiCreation.entering_pack_name)

@dp.callback_query(F.data == "name:random")
async def random_name_cb(cb: CallbackQuery, state: FSMContext):
    """Использовать рандомное название"""
    data = await state.get_data()
    random_name = data.get("random_name", generate_random_name())
    await state.update_data(pack_name=random_name)
    await cb.message.edit_text(
        f"🎲 <b>Название:</b> {random_name}\n\n⏳ Создаю пак..."
    )
    await cb.answer()
    await do_create_pack(cb.message, state, random_name)

@dp.message(EmojiCreation.entering_pack_name)
async def pack_name_handler(message: Message, state: FSMContext):
    """Обработка введённого названия"""
    pack_name = message.text.strip()

    if len(pack_name) < 3:
        await message.answer("❌ Название минимум 3 символа!", reply_markup=get_cancel_keyboard())
        return

    if len(pack_name) > 64:
        await message.answer("❌ Название максимум 64 символа!", reply_markup=get_cancel_keyboard())
        return

    status = await message.answer(f"✅ <b>Название:</b> {pack_name}\n\n⏳ Создаю пак...")
    await do_create_pack(status, state, pack_name)

async def do_create_pack(msg: Message, state: FSMContext, pack_name: str):
    """Основная функция создания пака"""
    data = await state.get_data()
    emoji_type = data.get('emoji_type', 'colorful')
    style = data.get('style')
    text = data.get('text', 'HI')

    try:
        pack_url, count = await create_emoji_pack(
            user_id=msg.chat.id,
            pack_title=pack_name,
            text=text,
            emoji_type=emoji_type
        )

        type_label = "🎨 Разноцветные" if emoji_type == "colorful" else f"⚫ Однотонные — {MONOTONE_STYLES.get(style,'')}"

        await msg.edit_text(
            "🎉 <b>Эмодзи-пак создан!</b>\n\n"
            f"📦 <b>Название:</b> {pack_name}\n"
            f"🔤 <b>Текст:</b> <code>{text}</code>\n"
            f"🎨 <b>Тип:</b> {type_label}\n"
            f"📊 <b>Эмодзи:</b> {count} шт.\n\n"
            f"🔗 <b>Ссылка:</b> {pack_url}\n\n"
            "⭐ Для использования нужен Telegram Premium!\n"
            "Создать ещё? /create 🚀"
        )
    except Exception as e:
        logger.error(f"❌ Ошибка создания пака: {e}")
        await msg.edit_text(
            f"❌ <b>Ошибка:</b> {str(e)}\n\n"
            "Попробуй ещё раз: /create"
        )
    finally:
        await state.clear()

# ═══ ЗАПУСК ══════════════════════════════════════════════════════

async def main():
    logger.info("╔═════════════════════════════════╗")
    logger.info("║  🎨 Emoji Pack Creator Bot      ║")
    logger.info("╚═════════════════════════════════╝")

    for path, label in [(COLORFUL_PATH, "Разноцветные"), (MONOTONE_PATH, "Однотонные")]:
        if os.path.exists(path):
            count = len([f for f in os.listdir(path) if f.endswith('.tgs')])
            logger.info(f"✅ {label}: {count} файлов")
        else:
            logger.warning(f"⚠️ Папка {path} не найдена!")

    bot_info = await bot.get_me()
    logger.info(f"✅ Бот: @{bot_info.username}")

    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

