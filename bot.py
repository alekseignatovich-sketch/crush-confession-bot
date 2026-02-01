import asyncio
import logging
import os
import random
from datetime import datetime, timedelta, timezone
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

ANTISPAM_SECONDS = 60

logging.basicConfig(level=logging.INFO)
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
router = Router()
dp.include_router(router)

last_confess_time: Dict[int, datetime] = {}
UTC = timezone.utc

# ────────────────── ШАБЛОНЫ ВАЛЕНТИНОК ──────────────────
VALENTINE_TEMPLATES = {
    "ru": {
        "romantic": [
            "Ты — то самое тепло, которого мне не хватало всю зиму. С 14 февраля ❤️",
            "Каждый день думаю о тебе чуть больше, чем вчера. С Днём всех влюблённых 💕",
            "Если бы сердце могло говорить, оно бы сказало только одно слово — ты.",
            "Ты делаешь мои обычные дни сказкой. Спасибо, что ты есть.",
            "С тобой даже понедельник кажется праздником. Люблю 💌",
        ],
        "funny": [
            "Роза красная, фиалка синяя, я стесняюсь, но ты мне очень нравишься 😏",
            "Я хотел отправить тебе 100 сердец, но бот сказал — хватит спама 😂❤️",
            "Если это признание анонимное — значит, я не виноват, если ты улыбнёшься 😉",
        ],
        "cute": [
            "Ты — мой самый любимый эмодзи в телефоне 💕",
            "Хочу обнять тебя так сильно, что даже бот покраснел",
            "Ты — мой маленький солнечный лучик в пасмурный день",
        ],
        "flirty": [
            "Если бы взгляды могли раздевать — ты бы уже была без одежды 😏",
            "Ты выглядишь так, будто создана, чтобы меня мучить",
            "Хочу узнать, какой у тебя вкус... поцелуя",
        ]
    }
}

# ────────────────── ВАЛИДНЫЕ СТИКЕРЫ (только правильные file_id) ──────────────────
VALENTINE_STICKERS = [
    "CAACAgIAAxkBAAFBmvppfwLgJhUWM52e3-hkWqsCrN9zPwACegEAAiI3jgR80USR9hGNuDgE",
    "CAACAgQAAxkBAAFBmwtpfwP3-t_2oIAJ504J4vIfUd9bOwACJhMAAqwWsVMdVmmblZlr2TgE",
    "CAACAgIAAxkBAAFBmw1pfwQcGerw3hvAK4wy6O6mprff7wACiQIAAladvQqhVs0CITIOPTgE",
    "CAACAgIAAxkBAAFBmw9pfwQuSx9FdGM6HCZg1DF7U-iU4QACDAADwDZPE-LPI__Cd5-8OAQ",
    "CAACAgIAAxkBAAFBmxFpfwQ8IVwbIaGQhEuZIOB5CCitZAACbAADWbv8JbDHPhsbLOD9OAQ",
    "CAACAgEAAxkBAAFBmxNpfwRMBIvttmmut0v7BQaAdKWosQACyQcAAuN4BAABhEkOibFTmls4BA",
    "CAACAgIAAxkBAAFBmxdpfwRh3h4OShF5gv4ZQrSEC5wBAQACcAUAAj-VzArvDuYB7z8lezgE",
    "CAACAgIAAxkBAAFBmxlpfwRueMDiN-98v-PHpgml_rBo_AACYAUAAj-VzApGyHYEZMxRFTgE",
    "CAACAgIAAxkBAAFBmxtpfwSC0Oo1A-zmqCskNzsWzmUmrQACGQMAAladvQqhVs0CITIOPTgE",
    "CAACAgIAAxkBAAFBmx1pfwSNU0Fx9CtU203tqibzZ3pZCAACFwMAAladvQrnhi7ExlTFGzgE",
    "CAACAgIAAxkBAAFBmx9pfwSZfNeT-c4VkSRRpEY8pWdRmgACBQMAAladvQrrlyw2i1A6hjgE",
    "CAACAgIAAxkBAAFBmyFpfwSlsmKcdZe5j5Yd46FsPpm-NAACYgIAAladvQrfUNgPvAABLqw4BA",
    "CAACAgIAAxkBAAFBmyNpfwSyqF9IVZMSA5hqFFSbxdlmzQACBgIAAhZCawof81Hl9_3GOzgE",
    "CAACAgIAAxkBAAFBmyVpfwS_kfEgQTN-H4e87u54FlFKagACXgEAAhZCawqE_ArUAgLZUDgE",
    "CAACAgIAAxkBAAFBmydpfwTNjl-CxWMAAaJ7tFB-Q4WQ9aQAAkwBAAIWQmsKhv8sCUuWpyc4BA",
    "CAACAgIAAxkBAAFBmylpfwTlinj3LVQiQcTdFClXSqG8ZQACRgADQbVWDLXqrL80jAn1OAQ",
    "CAACAgIAAxkBAAFBmyxpfwT6wBHH26I3c4EmhftIo8_bfwACGQADwDZPE9BDgPYgVxRLOAQ",
    "CAACAgIAAxkBAAFBmy5pfwUPJqfYvSreaTPZcmbHZ_vg0wACAgADwDZPEwj1bkX6hKdZOAQ",
    "CAACAgIAAxkBAAFBmzBpfwUfyhd8HP07q_oWwjznhlLhDwACDQEAAladvQpG_UMdBUTXlzgE",
]

class ConfessionFlow(StatesGroup):
    waiting_for_recipient = State()
    waiting_for_content_choice = State()
    preview_and_confirm = State()

# ────────────────── ХЭНДЛЕРЫ ──────────────────

@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    # Сброс состояния при /start
    await state.clear()
    
    now = datetime.now(UTC)
    last_time = last_confess_time.get(message.from_user.id)
    if last_time and (now - last_time) < timedelta(seconds=ANTISPAM_SECONDS):
        remaining = int((timedelta(seconds=ANTISPAM_SECONDS) - (now - last_time)).total_seconds())
        await message.answer(f"⏳ Подожди ещё {remaining} сек перед новым признанием 😉")
        return

    await state.set_state(ConfessionFlow.waiting_for_recipient)
    await message.answer(
        "💌 <b>Анонимное признание</b>\n\n"
        "Кому отправить признание?\n"
        "• Напиши @username\n"
        "• Или перешли любое сообщение от этого человека\n\n"
        "Отменить → /cancel"
    )


@router.message(ConfessionFlow.waiting_for_recipient)
async def process_recipient(message: Message, state: FSMContext):
    target_id: Optional[int] = None
    target_username: Optional[str] = None
    is_bot = False

    if message.forward_from:
        target_id = message.forward_from.id
        target_username = message.forward_from.username
        is_bot = message.forward_from.is_bot or False
    elif message.text and message.text.startswith("@"):
        try:
            chat = await bot.get_chat(message.text.strip())
            target_id = chat.id
            target_username = chat.username
            is_bot = getattr(chat, 'is_bot', False) or chat.type == "bot"
        except Exception as e:
            logging.error(f"Не удалось найти чат по @{message.text}: {e}")
            await message.answer("❌ Не нашёл такого пользователя. Попробуй переслать его сообщение.")
            return
    else:
        await message.answer("🔄 Перешли сообщение от человека или укажи @username")
        return

    if target_id == message.from_user.id:
        await message.answer("🤔 Нельзя отправить признание самому себе 😏")
        return

    if is_bot:
        await message.answer("🤖 Нельзя отправлять признания ботам — они не умеют влюбляться 😂")
        return

    if target_id is None:
        await message.answer("❓ Не удалось определить получателя. Попробуй ещё раз.")
        return

    await state.update_data(target_id=target_id, target_username=target_username)
    await state.set_state(ConfessionFlow.waiting_for_content_choice)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💝 Только стикер", callback_data="content_sticker")],
        [InlineKeyboardButton(text="💌 Только валентинка", callback_data="content_text")],
        [InlineKeyboardButton(text="💕 Стикер + валентинка", callback_data="content_both")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")],
    ])
    await message.answer(
        "✨ Отлично! Теперь выбери, что отправить:\n\n"
        "• Стикер — анимированное сердечко ❤️\n"
        "• Валентинка — романтическое сообщение 💬\n"
        "• Оба — полный пакет любви! 🌹",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("content_"))
async def process_content_choice(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    
    choice = callback.data.split("_")[1]
    data = await state.get_data()
    
    # Генерируем контент
    sticker_id = random.choice(VALENTINE_STICKERS) if choice in ["sticker", "both"] else None
    valentine_text = random.choice(VALENTINE_TEMPLATES["ru"]["romantic"]) if choice in ["text", "both"] else None
    
    await state.update_data(sticker_id=sticker_id, valentine_text=valentine_text, content_type=choice)
    
    # Формируем превью
    preview = "🎁 <b>Превью признания:</b>\n\n"
    if sticker_id:
        preview += "🖼️ Анимированный стикер ❤️\n"
    if valentine_text:
        preview += f"📝 <i>{valentine_text}</i>\n\n"
    preview += "Получатель увидит только бота — 100% анонимно 🔒"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_send")],
        [InlineKeyboardButton(text="🔄 Другой вариант", callback_data="regenerate")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")],
    ])
    
    # Отправляем превью
    if sticker_id:
        await callback.message.answer_sticker(sticker=sticker_id)
    await callback.message.answer(preview, reply_markup=kb)
    await state.set_state(ConfessionFlow.preview_and_confirm)


@router.callback_query(F.data == "regenerate")
async def regenerate_content(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    choice = data.get("content_type", "both")
    
    # Генерируем новый контент
    sticker_id = random.choice(VALENTINE_STICKERS) if choice in ["sticker", "both"] else None
    valentine_text = random.choice(VALENTINE_TEMPLATES["ru"]["romantic"]) if choice in ["text", "both"] else None
    
    await state.update_data(sticker_id=sticker_id, valentine_text=valentine_text)
    
    # Обновляем превью
    preview = "🎁 <b>Новое превью признания:</b>\n\n"
    if sticker_id:
        preview += "🖼️ Анимированный стикер ❤️\n"
    if valentine_text:
        preview += f"📝 <i>{valentine_text}</i>\n\n"
    preview += "Получатель увидит только бота — 100% анонимно 🔒"
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Отправить", callback_data="confirm_send")],
        [InlineKeyboardButton(text="🔄 Ещё вариант", callback_data="regenerate")],
        [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel")],
    ])
    
    if sticker_id:
        await callback.message.answer_sticker(sticker=sticker_id)
    await callback.message.answer(preview, reply_markup=kb)


@router.callback_query(F.data == "confirm_send")
async def confirm_send(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    data = await state.get_data()
    
    target_id = data.get("target_id")
    sticker_id = data.get("sticker_id")
    valentine_text = data.get("valentine_text")
    
    if not target_id:
        await callback.message.answer("❌ Ошибка: получатель не найден. Начни заново /start")
        await state.clear()
        return
    
    try:
        # Отправляем контент получателю
        if sticker_id:
            await bot.send_sticker(
                target_id,
                sticker=sticker_id,
                caption="💌 Тебе анонимное признание" if not valentine_text else None
            )
        if valentine_text:
            await bot.send_message(
                target_id,
                f"💌 Тебе анонимное признание\n\n<b>{valentine_text}</b>",
                parse_mode=ParseMode.HTML
            )
        
        # Подтверждение отправителю
        await callback.message.answer(
            "✅ Признание успешно отправлено!\n"
            "Получатель увидит только бота — твоя анонимность сохранена 🔒\n\n"
            "Хочешь отправить ещё? → /start"
        )
        
        last_confess_time[callback.from_user.id] = datetime.now(UTC)
        await state.clear()
        
    except Exception as e:
        error_str = str(e).lower()
        logging.error(f"Ошибка доставки: {e}")
        
        if "can't initiate conversation" in error_str or "bot can't initiate" in error_str:
            bot_username = (await bot.get_me()).username
            await callback.message.answer(
                "⚠️ Получатель ещё не писал боту.\n\n"
                f"Попроси его открыть @{bot_username} и написать /start — "
                "тогда признание доставится автоматически! 💌"
            )
        else:
            await callback.message.answer(
                "❌ Не удалось доставить признание.\n"
                "Возможно, получатель заблокировал ботов или удалил аккаунт."
            )
        await state.clear()


@router.callback_query(F.data == "cancel")
@router.message(Command("cancel"))
async def cancel_action(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.answer()
        msg = event.message
    else:
        msg = event
    
    await state.clear()
    await msg.answer("🚫 Действие отменено. Начать заново → /start")


async def main():
    # Проверка токена
    try:
        me = await bot.get_me()
        logging.info(f"✅ Бот запущен: @{me.username} (id={me.id})")
    except Exception as e:
        logging.critical(f"❌ Неверный BOT_TOKEN: {e}")
        return
    
    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    asyncio.run(main())
