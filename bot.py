import asyncio
import logging
import os
import random
import sys
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

ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))
MODERATION_ENABLED = os.getenv("MODERATION_ENABLED", "false").lower() == "true"

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
    },
    "en": {
        "romantic": [
            "You're the reason my heart beats a little faster every day. Happy Valentine's 💕",
            "Every moment with you feels like the best part of my story. Love you ❤️",
            "You make ordinary days feel magical. Happy Valentine's Day!",
        ],
        "funny": [
            "Roses are red, violets are blue, I anonymously like you... shh 😏",
            "Sending this anonymously because if you reject me, I can pretend it wasn't me 😂",
            "You're the reason I smile at my phone like an idiot",
        ],
        "cute": [
            "You're my favorite emoji in real life 💕",
            "I want to hug you so tight even this bot is blushing",
            "You're my little ray of sunshine on cloudy days",
        ],
        "flirty": [
            "If looks could undress, you'd be naked by now 😏",
            "You're designed to torture me in the best way",
            "I want to know how your lips taste...",
        ]
    }
}

# ────────────────── ВАЛИДНЫЕ СТИКЕРЫ (только проверенные) ──────────────────
ALL_VALENTINE_STICKERS = [
"CAACAgIAAxkBAAFBmvppfwLgJhUWM52e3-hkWqsCrN9zPwACegEAAiI3jgR80USR9hGNuDgE",
    "CAACAgQAAxkBAAFBmwtpfwP3-t_2oIAJ504J4vIfUd9bOwACJhMAAqwWsVMdVmmblZlr2TgE",
    "CAACAgIAAxkBAAFBmw1pfwQcGerw3hvAK4wy6O6mprff7wACiQIAAladvQqhVs0CITIOPTgE",
    "CAACAgIAAxkBAAFBmw9pfwQuSx9FdGM6HCZg1DF7U-iU4QACDAADwDZPE-LPI__Cd5-8OAQ",
    "CAACAgIAAxkBAAFBmxFpfwQ8IVwbIaGQhEuZIOB5CCitZAACbAADWbv8JbDHPhsbLOD9OAQ",
    "CAACAgEAAxkBAAFBmxNpfwRMBIvttmmut0v7BQaAdKWosQACyQcAAuN4BAABhEkOibFTmls4BA",
    "CAACAgIAAxkBAAFBmxdpfwRh3h4OShF5gv4ZQrSEC5wBAQACcAUAAj-VzArvDuYB7z8lezgE",
    "CAACAgIAAxkBAAFBmxlpfwRueMDiN-98v-PHpgml_rBo_AACYAUAAj-VzApGyHYEZMxRFTgE",
    "CAACAgIAAxkBAAFBmxtpfwSC0Oo1A-zmqCskNzsWzmUmrQACGQMAAladvQr6sQ9KOmJSYTgE",
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
    "CAACAgIAAxkBAAFBmvppfwLgJhUWM52e3-hkWqsCrN9zPwACegEAAiI3jgR80USR9hGNuDgE"
]

STICKER_CAPTIONS = [
    "Анонимное признание в анимации 💌",
    "Ты мне нравишься... с анимацией 😏",
    "С 14 февраля ❤️ (анимация)",
]

class ConfessionForm(StatesGroup):
    waiting_for_recipient = State()
    waiting_for_message = State()

# ────────────────── ХЭНДЛЕРЫ ──────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Открытка 💌", callback_data="gen_text")],
        [InlineKeyboardButton(text="Анимированный стикер", callback_data="gen_sticker")],
        [InlineKeyboardButton(text="Отправить признание", callback_data="start_confess")]
    ])
    await message.answer(
        "Привет! 💌\n\n"
        "Я бот для <b>анонимных признаний</b> и crush-сообщений.\n\n"
        "<b>Команды:</b>\n"
        "• /confess — отправить анонимное признание\n"
        "• /valentine — сгенерировать валентинку\n"
        "• /sticker — анимированный стикер\n"
        "• /cancel — отменить текущее действие\n\n"
        "Получатель увидит только меня — 100% анонимно."
    , reply_markup=kb)


@router.callback_query(F.data == "gen_text")
async def callback_gen_text(callback: CallbackQuery):
    await callback.answer()
    templates = VALENTINE_TEMPLATES["ru"]["romantic"]
    selected = random.choice(templates)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другую", callback_data="gen_text")],
        [InlineKeyboardButton(text="💌 Отправить признание", callback_data="start_confess")]
    ])
    await callback.message.answer(
        f"Вот твоя валентинка:\n\n"
        f"<blockquote expandable>{selected}</blockquote>",
        reply_markup=kb
    )


@router.callback_query(F.data == "gen_sticker")
async def callback_gen_sticker(callback: CallbackQuery):
    await callback.answer()
    sticker_id = random.choice(ALL_VALENTINE_STICKERS)
    caption = random.choice(STICKER_CAPTIONS)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другой стикер", callback_data="gen_sticker")],
        [InlineKeyboardButton(text="💌 Отправить признание", callback_data="start_confess")]
    ])
    await callback.message.answer_sticker(sticker=sticker_id)
    await callback.message.answer(f"<i>{caption}</i>", reply_markup=kb)


@router.callback_query(F.data == "start_confess")
async def callback_start_confess(callback: CallbackQuery, state: FSMContext):
    await callback.answer()
    now = datetime.now(UTC)
    last_time = last_confess_time.get(callback.from_user.id)
    if last_time and (now - last_time) < timedelta(seconds=ANTISPAM_SECONDS):
        remaining = int((timedelta(seconds=ANTISPAM_SECONDS) - (now - last_time)).total_seconds())
        await callback.message.answer(f"Подожди ещё {remaining} сек перед следующим признанием 😉")
        return

    await state.set_state(ConfessionForm.waiting_for_recipient)
    await callback.message.answer(
        "Кому отправить признание? 💕\n\n"
        "• Напиши @username\n"
        "• Или перешли любое сообщение от этого человека\n\n"
        "Отменить → /cancel"
    )


@router.message(Command("sticker", "valentinessticker"))
async def cmd_sticker(message: Message):
    sticker_id = random.choice(ALL_VALENTINE_STICKERS)
    caption = random.choice(STICKER_CAPTIONS)
    await message.answer_sticker(sticker=sticker_id)
    await message.answer(f"<i>{caption}</i>")


@router.message(Command("confess", "признание"))
async def cmd_confess(message: Message, state: FSMContext):
    now = datetime.now(UTC)
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
            await message.answer("Не нашёл такого пользователя 😔\nПопробуй переслать его сообщение.")
            return
    else:
        await message.answer("Перешли сообщение от человека или укажи @username")
        return

    if target_id == message.from_user.id:
        await message.answer("Нельзя отправить признание самому себе 😏")
        return

    if is_bot:
        await message.answer("Нельзя отправлять признания ботам — они не умеют влюбляться 😂\nВыбери реального человека!")
        return

    if target_id is None:
        await message.answer("Не удалось определить получателя. Попробуй ещё раз.")
        return

    await state.update_data(
        target_id=target_id,
        target_username=target_username,
        contents=[]
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

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Отправить 💌", callback_data="send_confession")],
        [InlineKeyboardButton(text="Отменить", callback_data="cancel")]
    ])

    await message.answer("Добавлено! Ещё что-то или отправляем?", reply_markup=kb)


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
        last_confess_time[callback.from_user.id] = datetime.now(UTC)

    except Exception as e:
        error_str = str(e).lower()
        logging.error(f"Ошибка доставки: {e}")

        if "can't initiate conversation" in error_str or "forbidden: bot can't" in error_str:
            bot_username = (await bot.get_me()).username
            await callback.message.answer(
                "Не могу доставить 😢\n\n"
                "Получатель ещё не общался со мной — Telegram не даёт ботам писать первыми.\n\n"
                "Попроси его открыть бота и написать /start — "
                f"как только он это сделает, признание улетит! 💌\n\n"
                f"Ссылка: https://t.me/{bot_username}"
            )
        elif "send messages to bots" in error_str:
            await callback.message.answer("Это бот, а не человек — признания ботам не отправляются 😅")
        else:
            await callback.message.answer("Что-то пошло не так при доставке… Попробуй позже или /confess заново.")

    await state.clear()


@router.callback_query(F.data == "cancel")
@router.message(Command("cancel"))
async def cancel_action(event: Message | CallbackQuery, state: FSMContext):
    if isinstance(event, CallbackQuery):
        await event.answer()
        msg = event.message
    else:
        msg = event

    if await state.get_state() is None:
        await msg.answer("Нечего отменять 😊")
        return

    await state.clear()
    await msg.answer("Действие отменено. /confess — чтобы начать заново 💕")


@router.message(Command("valentine", "gen", "валентинка"))
async def generate_valentine(message: Message):
    text = message.text.lower().strip()
    args = text.split()[1:]

    lang = "ru"
    category = "romantic"

    categories = ["romantic", "funny", "cute", "flirty"]

    for arg in args:
        if arg in ["en", "english", "англ"]:
            lang = "en"
        elif arg in categories:
            category = arg

    if lang not in VALENTINE_TEMPLATES or category not in VALENTINE_TEMPLATES[lang]:
        await message.answer(
            "Доступные категории: romantic, funny, cute, flirty\n"
            "Язык: ru (по умолчанию) или en\n\n"
            "Примеры:\n"
            "/valentine funny\n"
            "/valentine cute en"
        )
        return

    templates = VALENTINE_TEMPLATES[lang][category]
    selected = random.choice(templates)

    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔄 Другую", callback_data=f"gen_val_{lang}_{category}")],
    ])

    await message.answer(
        f"Вот твоя валентинка ({category}, {lang.upper()}):\n\n"
        f"<blockquote expandable>{selected}</blockquote>",
        reply_markup=kb
    )


@router.callback_query(F.data.startswith("gen_val_"))
async def regenerate_valentine(callback: CallbackQuery):
    await callback.answer()
    parts = callback.data.split("_")
    if len(parts) >= 4:
        lang = parts[2]
        category = parts[3]
        if lang in VALENTINE_TEMPLATES and category in VALENTINE_TEMPLATES[lang]:
            templates = VALENTINE_TEMPLATES[lang][category]
            selected = random.choice(templates)
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Другую", callback_data=f"gen_val_{lang}_{category}")],
            ])
            await callback.message.edit_text(
                f"Вот твоя валентинка ({category}, {lang.upper()}):\n\n"
                f"<blockquote expandable>{selected}</blockquote>",
                reply_markup=kb
            )
            return
    await callback.message.answer("Ошибка генерации. Попробуй /valentine")


async def main():
    # Проверка валидности токена
    try:
        me = await bot.get_me()
        logging.info(f"✅ Бот запущен: @{me.username} (id={me.id})")
    except Exception as e:
        logging.critical(f"❌ Неверный BOT_TOKEN! Ошибка: {e}")
        logging.critical("Проверьте токен в .env или переменных окружения")
        return

    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    asyncio.run(main())
