import asyncio
import logging
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
)
from dotenv import load_dotenv

load_dotenv()

# ────────────────── НАСТРОЙКИ ──────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN")
if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN не найден в .env или переменных окружения")

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))          # id группы/канала/твоего user_id
MODERATION_ENABLED = os.getenv("MODERATION_ENABLED", "false").lower() == "true"

# Антиспам: один confess каждые N секунд
ANTISPAM_SECONDS = 60

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

# Хранилище времени последнего confess (user_id → datetime)
last_confess_time: Dict[int, datetime] = {}

class ConfessionForm(StatesGroup):
    waiting_for_recipient = State()
    waiting_for_message   = State()

# ────────────────── ХЭНДЛЕРЫ ──────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "Привет! 💌\n\n"
        "Я бот для <b>анонимных признаний</b> и crush-сообщений.\n\n"
        "<b>Команды:</b>\n"
        "• /confess — отправить анонимное признание\n"
        "• /cancel  — отменить текущее действие\n\n"
        "Просто пришли текст / фото / голосовое / стикер — я спрошу, кому отправить.\n"
        "Получатель увидит только меня — 100% анонимно."
    )


@router.message(Command("confess", "признание"))
async def cmd_confess(message: Message, state: FSMContext):
    now = datetime.utcnow()
    last_time = last_confess_time.get(message.from_user.id)
    if last_time and (now - last_time) < timedelta(seconds=ANTISPAM_SECONDS):
        remaining = int((timedelta(seconds=ANTISPAM_SECONDS) - (now - last_time)).total_seconds())
        await message.answer(f"Подожди ещё {remaining} сек перед следующим признанием 😉")
        return

    await state.set_state(ConfessionForm.waiting_for_recipient)
    await message.answer(
        "Кому отправить признание? 💕\n\n"
        "• Напиши @username\n"
        "• Или перешли любое сообщение от этого человека\n\n"
        "Отменить → /cancel"
    )


@router.message(ConfessionForm.waiting_for_recipient)
async def process_recipient(message: Message, state: FSMContext):
    target_id: Optional[int] = None
    target_username: Optional[str] = None

    if message.forward_from:
        target_id = message.forward_from.id
        target_username = message.forward_from.username
    elif message.text and message.text.startswith("@"):
        try:
            chat = await bot.get_chat(message.text.strip())
            target_id = chat.id
            target_username = chat.username
        except Exception as e:
            logging.error(f"Не удалось найти чат по @{message.text}: {e}")
            await message.answer("Не нашёл такого пользователя 😔\nПопробуй переслать его сообщение.")
            return
    else:
        await message.answer("Перешли сообщение от человека или укажи @username")
        return

    if target_id == message.from_user.id:
        await message.answer("Нельзя отправить признание самому себе 😏")
        return

    if target_id is None:
        await message.answer("Не удалось определить получателя. Попробуй ещё раз.")
        return

    await state.update_data(
        target_id=target_id,
        target_username=target_username,
        contents=[]  # список сообщений/медиа
    )

    await state.set_state(ConfessionForm.waiting_for_message)
    await message.answer(
        "Супер! Теперь пришли содержимое признания:\n"
        "• текст\n"
        "• фото\n"
        "• голосовое\n"
        "• стикер\n\n"
        "Можно несколько сообщений подряд.\n"
        "Когда закончишь — нажми кнопку ниже ↓"
    )


@router.message(ConfessionForm.waiting_for_message, F.text | F.photo | F.voice | F.sticker)
async def collect_content(message: Message, state: FSMContext):
    data = await state.get_data()
    contents: List[Dict] = data.get("contents", [])

    item = {}
    if message.text:
        item = {"type": "text", "content": message.text}
    elif message.photo:
        item = {"type": "photo", "file_id": message.photo[-1].file_id}
    elif message.voice:
        item = {"type": "voice", "file_id": message.voice.file_id}
    elif message.sticker:
        item = {"type": "sticker", "file_id": message.sticker.file_id}

    contents.append(item)
    await state.update_data(contents=contents)

    # Кнопки подтверждения после каждого сообщения
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить 💌", callback_data="send_confession")],
        [InlineKeyboardButton(text="Отменить",     callback_data="cancel")]
    ])

    await message.answer("Добавлено! Ещё что-то добавить или уже отправить?", reply_markup=kb)


@router.callback_query(F.data == "send_confession")
async def send_confession(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    target_id = data.get("target_id")
    contents: List[Dict] = data.get("contents", [])

    if not target_id or not contents:
        await callback.message.answer("Нет данных для отправки. Начни заново /confess")
        await state.clear()
        return

    try:
        for item in contents:
            if item["type"] == "text":
                await bot.send_message(target_id, f"Тебе анонимное признание 💌\n\n{item['content']}")
            elif item["type"] == "photo":
                await bot.send_photo(target_id, photo=item["file_id"], caption="Тебе анонимное признание 💌")
            elif item["type"] == "voice":
                await bot.send_voice(target_id, voice=item["file_id"], caption="Тебе анонимное признание 💌")
            elif item["type"] == "sticker":
                await bot.send_sticker(target_id, sticker=item["file_id"])

        await callback.message.answer("Признание успешно и анонимно отправлено! 🔥")
        last_confess_time[callback.from_user.id] = datetime.utcnow()

    except Exception as e:
        logging.error(f"Ошибка доставки: {e}")
        await callback.message.answer("Не получилось доставить 😢 Возможно, получатель закрыл чат с ботами.")

    await state.clear()


@router.callback_query(F.data == "cancel")
@router.message(Command("cancel"))
async def cancel_action(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.answer()
        msg = event.message
    else:
        msg = event

    current_state = await state.get_state()
    if current_state is None:
        await msg.answer("Нечего отменять 😊")
        return

    await state.clear()
    await msg.answer("Действие отменено. /confess — чтобы начать заново 💕")


# ────────────────── ЗАПУСК ──────────────────

async def main():
    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types(),
        drop_pending_updates=True
    )

if __name__ == "__main__":
    asyncio.run(main())
