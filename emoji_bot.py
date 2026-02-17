"""
Emoji Pack Creator Bot - Создание кастомных эмодзи-паков
Разноцветные и однотонные стили
"""

import os
import re
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

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ТОКЕН БОТА
TELEGRAM_TOKEN = "8514454295:AAGOufeY-pO9ixKBdiPZz6mJ4gO1hQIvCMs"

# Инициализация
storage = MemoryStorage()
bot = Bot(token=TELEGRAM_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=storage)

# ПУТИ К ПАПКАМ С ЭМОДЗИ (для BotHost)
COLORFUL_PATH = "colorful"  # Разноцветные
MONOTONE_PATH = "monotone"  # Однотонные

# Стили для однотонных
MONOTONE_STYLES = {
    "black": "⬛ Черный",
    "cosmos": "🌌 Космос", 
    "sakura": "🌸 Сакура",
    "ocean": "🌊 Океан",
    "sunset": "🌅 Закат",
    "forest": "🌲 Лес"
}

# Машина состояний
class EmojiCreation(StatesGroup):
    choosing_type = State()
    choosing_style = State()
    entering_text = State()
    entering_pack_name = State()

# ═══════════════════════════════════════════════════════════════
# КЛАВИАТУРЫ
# ═══════════════════════════════════════════════════════════════

def get_type_keyboard():
    """Клавиатура выбора типа эмодзи"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎨 Разноцветные", callback_data="type:colorful"),
            InlineKeyboardButton(text="⚫ Однотонные", callback_data="type:monotone")
        ],
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    return keyboard

def get_style_keyboard():
    """Клавиатура выбора стиля для однотонных"""
    buttons = []
    for style_id, style_name in MONOTONE_STYLES.items():
        buttons.append([InlineKeyboardButton(
            text=style_name, 
            callback_data=f"style:{style_id}"
        )])
    buttons.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_type")])
    buttons.append([InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")])
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    return keyboard

def get_cancel_keyboard():
    """Клавиатура отмены"""
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
    ])
    return keyboard

# ═══════════════════════════════════════════════════════════════
# РАБОТА С ЭМОДЗИ
# ═══════════════════════════════════════════════════════════════

def get_emoji_files(emoji_type):
    """Получить список файлов эмодзи"""
    path = COLORFUL_PATH if emoji_type == "colorful" else MONOTONE_PATH
    
    if not os.path.exists(path):
        logger.error(f"❌ Путь не существует: {path}")
        return []
    
    files = sorted([f for f in os.listdir(path) if f.endswith('.tgs')])
    logger.info(f"✅ Найдено {len(files)} файлов в {path}")
    return [os.path.join(path, f) for f in files]

def process_text_to_emoji(text, emoji_files):
    """Подготовка эмодзи под текст пользователя"""
    text_upper = text.upper()
    selected_files = []
    
    for i, char in enumerate(text_upper):
        if i < len(emoji_files):
            selected_files.append({
                'file': emoji_files[i],
                'emoji': char
            })
    
    return selected_files

async def create_sticker_set(user_id, username, pack_name, emoji_data, emoji_type, style=None):
    """Создание набора стикеров"""
    try:
        # Формируем название пака
        pack_title = pack_name
        bot_username = (await bot.get_me()).username
        pack_short_name = f"{pack_name.lower().replace(' ', '_')}_{user_id}_by_{bot_username}"
        
        logger.info(f"🔄 Создаю пак: {pack_short_name}")
        
        # Создаем первый стикер
        first_emoji = emoji_data[0]
        sticker_file = types.FSInputFile(first_emoji['file'])
        
        await bot.create_new_sticker_set(
            user_id=user_id,
            name=pack_short_name,
            title=pack_title,
            stickers=[types.InputSticker(
                sticker=sticker_file,
                emoji_list=[first_emoji['emoji']],
                format="animated"
            )],
            sticker_type="custom_emoji"
        )
        
        logger.info(f"✅ Пак создан, добавляю остальные {len(emoji_data)-1} стикеров...")
        
        # Добавляем остальные стикеры
        for emoji in emoji_data[1:]:
            try:
                sticker_file = types.FSInputFile(emoji['file'])
                
                await bot.add_sticker_to_set(
                    user_id=user_id,
                    name=pack_short_name,
                    sticker=types.InputSticker(
                        sticker=sticker_file,
                        emoji_list=[emoji['emoji']],
                        format="animated"
                    )
                )
                await asyncio.sleep(0.3)
                
            except Exception as e:
                logger.error(f"❌ Ошибка добавления стикера {emoji['emoji']}: {e}")
                continue
        
        pack_url = f"https://t.me/addemoji/{pack_short_name}"
        logger.info(f"🎉 Пак создан успешно: {pack_url}")
        return pack_url
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания пака: {e}")
        raise

# ═══════════════════════════════════════════════════════════════
# КОМАНДЫ
# ═══════════════════════════════════════════════════════════════

@dp.message(CommandStart())
async def start_command(message: Message):
    """Приветствие"""
    welcome_text = """
🎨 <b>Добро пожаловать в Emoji Pack Creator!</b>

Я помогу тебе создать кастомный эмодзи-пак для Telegram Premium! ⭐

<b>Что я умею:</b>
✨ Создавать разноцветные эмодзи
⚫ Создавать однотонные эмодзи (6 стилей)
🔤 Превращать твой текст в эмодзи (до 10 символов)
📦 Создавать готовый пак для Telegram

<b>Доступные стили для однотонных:</b>
⬛ Черный • 🌌 Космос • 🌸 Сакура
🌊 Океан • 🌅 Закат • 🌲 Лес

<b>Команды:</b>
/create - Создать новый эмодзи-пак
/help - Помощь

Давай создадим что-то крутое! 🚀
"""
    await message.answer(welcome_text)

@dp.message(Command("create"))
async def create_command(message: Message, state: FSMContext):
    """Начало создания пака"""
    await message.answer(
        "🎨 <b>Выбери тип эмодзи:</b>\n\n"
        "🎨 <b>Разноцветные</b> - яркие и красочные\n"
        "⚫ <b>Однотонные</b> - стильные монохромные (6 стилей на выбор)",
        reply_markup=get_type_keyboard()
    )
    await state.set_state(EmojiCreation.choosing_type)

@dp.message(Command("help"))
async def help_command(message: Message):
    """Справка"""
    help_text = """
📖 <b>Как пользоваться ботом:</b>

1️⃣ Нажми /create
2️⃣ Выбери тип эмодзи (разноцветные или однотонные)
3️⃣ Если выбрал однотонные - выбери стиль
4️⃣ Введи текст до 10 символов (например: HELLO)
5️⃣ Введи название пака
6️⃣ Получи готовый эмодзи-пак! 🎉

<b>Важно:</b>
⚠️ Нужен Telegram Premium для использования эмодзи
⚠️ Текст должен быть до 10 символов
⚠️ Используй английские буквы и цифры

<b>Примеры текста:</b>
• LOVE ❤️
• 2024 🎉
• COOL 😎
• HELLO 👋
• SMILE 😊

Готов создавать? Жми /create! 🚀
"""
    await message.answer(help_text)

# ═══════════════════════════════════════════════════════════════
# CALLBACK HANDLERS
# ═══════════════════════════════════════════════════════════════

@dp.callback_query(F.data == "cancel")
async def cancel_callback(callback: CallbackQuery, state: FSMContext):
    """Отмена создания"""
    await state.clear()
    await callback.message.edit_text(
        "❌ <b>Создание отменено</b>\n\nЧтобы начать заново, используй /create"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("type:"))
async def type_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор типа эмодзи"""
    emoji_type = callback.data.split(":")[1]
    await state.update_data(emoji_type=emoji_type)
    
    if emoji_type == "colorful":
        await callback.message.edit_text(
            "🎨 <b>Разноцветные эмодзи выбраны!</b>\n\n"
            "Теперь введи текст для эмодзи (до 10 символов):\n"
            "Например: <code>HELLO</code> или <code>LOVE</code>",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(EmojiCreation.entering_text)
    else:
        await callback.message.edit_text(
            "⚫ <b>Однотонные эмодзи выбраны!</b>\n\n"
            "Выбери стиль:",
            reply_markup=get_style_keyboard()
        )
        await state.set_state(EmojiCreation.choosing_style)
    
    await callback.answer()

@dp.callback_query(F.data.startswith("style:"))
async def style_callback(callback: CallbackQuery, state: FSMContext):
    """Выбор стиля для однотонных"""
    style = callback.data.split(":")[1]
    style_name = MONOTONE_STYLES.get(style, "Неизвестный")
    
    await state.update_data(style=style)
    
    await callback.message.edit_text(
        f"✅ <b>Стиль выбран: {style_name}</b>\n\n"
        "Теперь введи текст для эмодзи (до 10 символов):\n"
        "Например: <code>LOVE</code> или <code>COOL</code>",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EmojiCreation.entering_text)
    await callback.answer()

@dp.callback_query(F.data == "back_to_type")
async def back_to_type_callback(callback: CallbackQuery, state: FSMContext):
    """Вернуться к выбору типа"""
    await callback.message.edit_text(
        "🎨 <b>Выбери тип эмодзи:</b>\n\n"
        "🎨 <b>Разноцветные</b> - яркие и красочные\n"
        "⚫ <b>Однотонные</b> - стильные монохромные",
        reply_markup=get_type_keyboard()
    )
    await state.set_state(EmojiCreation.choosing_type)
    await callback.answer()

# ═══════════════════════════════════════════════════════════════
# ОБРАБОТКА ВВОДА
# ═══════════════════════════════════════════════════════════════

@dp.message(EmojiCreation.entering_text)
async def process_text(message: Message, state: FSMContext):
    """Обработка введенного текста"""
    text = message.text.strip()
    
    if len(text) > 10:
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "Текст должен быть не больше 10 символов!\n"
            "Попробуй еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    if len(text) == 0:
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "Текст не может быть пустым!\n"
            "Попробуй еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    if not re.match(r'^[A-Za-z0-9]+$', text):
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "Используй только английские буквы и цифры!\n"
            "Попробуй еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(text=text.upper())
    
    await message.answer(
        f"✅ <b>Текст принят:</b> <code>{text.upper()}</code>\n\n"
        "Теперь введи название для твоего эмодзи-пака:\n"
        "Например: <code>Мои эмодзи</code> или <code>LOVE Pack</code>",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(EmojiCreation.entering_pack_name)

@dp.message(EmojiCreation.entering_pack_name)
async def process_pack_name(message: Message, state: FSMContext):
    """Обработка названия пака"""
    pack_name = message.text.strip()
    
    if len(pack_name) < 3:
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "Название должно быть минимум 3 символа!\n"
            "Попробуй еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    if len(pack_name) > 64:
        await message.answer(
            "❌ <b>Ошибка!</b>\n\n"
            "Название слишком длинное (макс 64 символа)!\n"
            "Попробуй еще раз:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    data = await state.get_data()
    emoji_type = data.get('emoji_type')
    style = data.get('style')
    text = data.get('text')
    
    status_msg = await message.answer(
        "⏳ <b>Создаю твой эмодзи-пак...</b>\n\n"
        f"📝 Название: <b>{pack_name}</b>\n"
        f"🔤 Текст: <code>{text}</code>\n"
        f"🎨 Тип: <b>{'Разноцветные' if emoji_type == 'colorful' else 'Однотонные'}</b>\n" +
        (f"✨ Стиль: <b>{MONOTONE_STYLES.get(style, 'Черный')}</b>\n" if style else "") +
        "\nЭто может занять несколько секунд... ⏱️"
    )
    
    try:
        emoji_files = get_emoji_files(emoji_type)
        
        if not emoji_files:
            await status_msg.edit_text(
                "❌ <b>Ошибка!</b>\n\n"
                "Файлы эмодзи не найдены. Проверь что папки загружены!"
            )
            await state.clear()
            return
        
        emoji_data = process_text_to_emoji(text, emoji_files)
        
        pack_url = await create_sticker_set(
            user_id=message.from_user.id,
            username=message.from_user.username or "user",
            pack_name=pack_name,
            emoji_data=emoji_data,
            emoji_type=emoji_type,
            style=style
        )
        
        await status_msg.edit_text(
            "🎉 <b>Эмодзи-пак успешно создан!</b>\n\n"
            f"📦 <b>Название:</b> {pack_name}\n"
            f"🔤 <b>Текст:</b> <code>{text}</code>\n"
            f"📊 <b>Эмодзи:</b> {len(emoji_data)} шт.\n\n"
            f"🔗 <b>Ссылка:</b> {pack_url}\n\n"
            "⭐ Для использования нужен Telegram Premium!\n\n"
            "Хочешь создать еще? Жми /create 🚀"
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"❌ Ошибка создания пака: {e}")
        await status_msg.edit_text(
            "❌ <b>Ошибка создания пака!</b>\n\n"
            f"Причина: {str(e)}\n\n"
            "Попробуй еще раз: /create"
        )
        await state.clear()

# ═══════════════════════════════════════════════════════════════
# ЗАПУСК
# ═══════════════════════════════════════════════════════════════

async def main():
    """Главная функция"""
    logger.info("╔════════════════════════════════════════════════╗")
    logger.info("║   🎨 Emoji Pack Creator Bot                   ║")
    logger.info("║   Запуск...                                    ║")
    logger.info("╚════════════════════════════════════════════════╝")
    
    # Проверка папок
    if not os.path.exists(COLORFUL_PATH):
        logger.warning(f"⚠️ Папка {COLORFUL_PATH} не найдена!")
    else:
        count = len([f for f in os.listdir(COLORFUL_PATH) if f.endswith('.tgs')])
        logger.info(f"✅ Разноцветные эмодзи: {count} файлов")
    
    if not os.path.exists(MONOTONE_PATH):
        logger.warning(f"⚠️ Папка {MONOTONE_PATH} не найдена!")
    else:
        count = len([f for f in os.listdir(MONOTONE_PATH) if f.endswith('.tgs')])
        logger.info(f"✅ Однотонные эмодзи: {count} файлов")
    
    bot_info = await bot.get_me()
    logger.info(f"✅ Бот запущен: @{bot_info.username}")
    logger.info("💬 Готов к работе!")
    
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("👋 Бот остановлен")
    except Exception as e:
        logger.error(f"❌ Ошибка: {e}")

