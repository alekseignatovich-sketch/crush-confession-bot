import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile, BufferedInputFile
)
from dotenv import load_dotenv

load_dotenv()

# ------------------ НАСТРОЙКИ ------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # группа или твой id
MODERATION_ENABLED = os.getenv("MODERATION_ENABLED", "true").lower() == "true"

# Антиспам: один confess каждые 60 секунд
ANTISPAM_SECONDS = 60

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Хранилище последнего confess времени по user_id
last_confess_time: dict[int, datetime] = {}

class ConfessionForm(StatesGroup):
    waiting_for_recipient = State()      # Кому отправить?
    waiting_for_message = State()        # Само признание
    waiting_for_moderation = State()     # (внутреннее)

# ------------------ ХЭНДЛЕРЫ ------------------

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! 💌\n"
        "Я — бот для анонимных признаний и crush-сообщений.\n\n"
        "<b>Как пользоваться:</b>\n"
        "/confess — отправить анонимное признание\n"
        "Или просто пришли текст/фото/голос — я спрошу, кому отправить.\n\n"
        "Всё 100% анонимно — получатель увидит только меня."
    )

@router.message(Command("confess", "признание"))
async def cmd_confess(message: Message, state: FSMContext):
    # Проверка антиспама
    now = datetime.utcnow()
    last_time = last_confess_time.get(message.from_user.id)
    if last_time and (now - last_time) < timedelta(seconds=ANTISPAM_SECONDS):
        remaining = (timedelta(seconds=ANTISPAM_SECONDS) - (now - last_time)).seconds
        await message.answer(f"Подожди {remaining} сек перед следующим признанием 😉")
        return

    await state.set_state(ConfessionForm.waiting_for_recipient)
    await message.answer(
        "Кому отправить? 💕\n"
        "Напиши @username или перешли любое сообщение от этого человека.\n"
        "(Чтобы отменить — /cancel)"
    )

@router.message(ConfessionForm.waiting_for_recipient)
async def process_recipient(message: Message, state: FSMContext, bot: Bot):
    target_id: Optional[int] = None

    if message.forward_from:
        target_id = message.forward_from.id
    elif message.text and message.text.startswith("@"):
        try:
            chat = await bot.get_chat(message.text.strip())
            target_id = chat.id
        except Exception as e:
            logging.error(e)
            await message.answer("Не смог найти такого пользователя 😔\nПопробуй переслать его сообщение.")
            return
    else:
        await message.answer("Перешли сообщение от человека или укажи @username")
        return

    if target_id == message.from_user.id:
        await message.answer("Нельзя отправить признание самому себе 😏")
        return

    await state.update_data(target_id=target_id, target_username=message.text.strip() if message.text else None)
    await state.set_state(ConfessionForm.waiting_for_message)

    await message.answer(
        "Отлично! Теперь пришли само признание:\n"
        "• текст\n"
        "• фото\n"
        "• голосовое\n"
        "• стикер\n\n"
        "Когда закончишь — нажми «Отправить» или пришли ещё контент."
    )

@router.message(ConfessionForm.waiting_for_message, F.text | F.photo | F.voice | F.sticker)
async def process_content(message: Message, state: FSMContext):
    data = await state.get_data()
    contents = data.get("contents", [])

    if message.text:
        contents.append({"type": "text", "content": message.text})
    elif message.photo:
        contents.append({"type": "photo", "file_id": message.photo[-1].file_id})
    elif message.voice:
        contents.append({"type": "voice", "file_id": message.voice.file_id})
    elif message.sticker:
        contents.append({"type": "sticker", "file_id": message.sticker.file_id})

    await state.update_data(contents=contents)

    # Показываем кнопки подтверждения
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить 💌", callback_data="send_confession")],
        [InlineKeyboardButton(text="Отменить", callback_data="cancel")]
    ])

    preview_text = "Твоё признание сейчас выглядит так:\n\n"
    for item in contents:
        if item["type"] == "text":
            preview_text += item["content"] + "\n"
    await message.answer(preview_text, reply_markup=kb)

@router.callback_query(F.data == "send_confession")
async def send_confession(callback: CallbackQuery, state: FSMContext, bot: Bot):
    await callback.answer()
    data = await state.get_data()
    target_id = data.get("target_id")
    contents = data.get("contents", [])

    if not target_id or not contents:
        await callback.message.answer("Что-то пошло не так... Попробуй заново /confess")
        await state.clear()
        return

    try:
        # Отправляем получателю
        for item in contents:
            if item["type"] == "text":
                await bot.send_message(target_id, f"Тебе анонимное признание 💌\n\n{item['content']}")
            elif item["type"] == "photo":
                await bot.send_photo(target_id, photo=item["file_id"], caption="Тебе анонимное признание 💌")
            elif item["type"] == "voice":
                await bot.send_voice(target_id, voice=item["file_id"], caption="Тебе анонимное признание 💌")
            elif item["type"] == "sticker":
                await bot.send_sticker(target_id, sticker=item["file_id"])

        await callback.message.answer("Признание успешно отправлено анонимно! 🔥")
        last_confess_time[callback.from_user.id] = datetime.utcnow()

    except Exception as e:
        logging.error(e)
        await callback.message.answer("Не удалось доставить 😢 Возможно, получатель заблокировал бота.")

    await state.clear()

@router.callback_query(F.data == "cancel")
@router.message(Command("cancel"))
async def cancel_handler(message: Message | CallbackQuery, state: FSMContext):
    if isinstance(message, CallbackQuery):
        await message.answer()
        message = message.message

    current_state = await state.get_state()
    if current_state is None:
        return

    await state.clear()
    await message.answer("Отменено. Начни заново /confess если хочешь 💕")

# ------------------ ЗАПУСК ------------------

async def main():
    await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

if __name__ == "__main__":
    asyncio.run(main())
