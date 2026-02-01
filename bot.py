import asyncio
import logging
import os
import random
import signal
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
            "Твоя улыбка — мой любимый способ начать день.",
            "Ты — мой самый красивый повод улыбаться без причины.",
            "В мире миллиарды людей, а мне нужна только ты.",
            "Ты — мой личный кусочек счастья в этом хаосе.",
            "С тобой время летит, но я всё равно хочу, чтобы оно останавливалось.",
            "Ты — причина, по которой я верю в чудеса.",
            "Каждое твоё сообщение — маленький праздник.",
            "Ты — мой самый нежный секрет.",
            "С тобой я чувствую себя дома, даже когда мы далеко.",
            "Ты — мой лучший ответ на вопрос «а вдруг?»"
        ],
        "funny": [
            "Роза красная, фиалка синяя, я стесняюсь, но ты мне очень нравишься 😏",
            "Я хотел отправить тебе 100 сердец, но бот сказал — хватит спама 😂❤️",
            "Если это признание анонимное — значит, я не виноват, если ты улыбнёшься 😉",
            "Ты мой любимый повод краснеть без причины. С 14 февраля!",
            "Не знаю, кто ты по гороскопу, но по моему — идеальный человек 😈",
            "Ты такая милая, что у меня аллергия на твою милоту 😅",
            "Я не врач, но думаю, у меня сердечная недостаточность — ты слишком часто заставляешь его биться быстрее",
            "Если бы ты была Wi-Fi, я бы ловил только тебя",
            "Ты — мой любимый баг в системе «жизнь»",
            "Я не толстый, просто сердце раздулось от мыслей о тебе",
            "Ты — причина, почему я улыбаюсь телефону как идиот",
            "Признаюсь: я влюблён... в твои мемы в сторис 😏",
            "Ты такая красивая, что даже мой кот ревнует",
            "Я не лентяй, просто жду, когда ты сама напишешь первой",
            "Ты — мой самый дорогой способ тратить батарейку"
        ],
        "cute": [
            "Ты — мой самый любимый эмодзи в телефоне 💕",
            "Хочу обнять тебя так сильно, что даже бот покраснел",
            "Ты — мой маленький солнечный лучик в пасмурный день",
            "С тобой даже дождь кажется романтикой",
            "Ты — мой любимый способ начинать утро",
            "Ты такая милая, что хочется спрятать в карман и носить с собой",
            "Ты — мой самый сладкий сон наяву",
            "Хочу держать тебя за руку и гулять вечно",
            "Ты — мой повод верить в хорошее",
            "С тобой мир становится ярче на 100 оттенков",
            "Ты — мой самый уютный плед в холодный вечер",
            "Ты — мой маленький секрет счастья",
            "Ты такая нежная, что даже облака завидуют",
            "Ты — мой любимый звук уведомления",
            "Ты — мой самый тёплый февраль"
        ],
        "flirty": [
            "Если бы взгляды могли раздевать — ты бы уже была без одежды 😏",
            "Ты выглядишь так, будто создана, чтобы меня мучить",
            "Хочу узнать, какой у тебя вкус... поцелуя",
            "Ты — мой самый опасный соблазн",
            "Если ты не ответишь — я начну слать сердечки спамом",
            "Ты такая горячая, что мой телефон перегревается",
            "Хочу быть тем, о ком ты думаешь перед сном",
            "Ты — мой любимый способ нарушать правила",
            "Если бы ты была коктейлем — я бы пил тебя всю ночь",
            "Ты заставляешь меня забывать, как дышать",
            "Хочу узнать все твои секреты... особенно те, что под одеждой 😈",
            "Ты — мой самый приятный запретный плод",
            "Ты такая красивая, что даже зеркало влюбилось",
            "Хочу быть причиной твоей улыбки... и лёгкого румянца",
            "Ты — мой самый сладкий грех"
        ]
    },
    "en": {
        "romantic": [
            "You're the reason my heart beats a little faster every day. Happy Valentine's 💕",
            "Every moment with you feels like the best part of my story. Love you ❤️",
            "You make ordinary days feel magical. Happy Valentine's Day!",
            "If I had a flower for every time I thought of you, I'd have a garden forever.",
            "You're my favorite notification. Happy V-Day 💌",
            "You're the warmth I've been missing all winter long.",
            "Thinking of you is my favorite part of every day.",
            "You turn my ordinary moments into something unforgettable.",
            "With you, even Mondays feel like holidays.",
            "You're the reason I believe in magic again.",
            "Every message from you is a little celebration.",
            "You're my favorite secret to keep.",
            "You feel like home, even when we're miles apart.",
            "You're my best answer to 'what if?'",
            "You're the spark that lights up my darkest days."
        ],
        "funny": [
            "Roses are red, violets are blue, I anonymously like you... shh 😏",
            "Sending this anonymously because if you reject me, I can pretend it wasn't me 😂",
            "You're the reason I smile at my phone like an idiot",
            "If liking you was a crime, I'd be serving life sentence",
            "You're so cute my phone screen fogs up when I look at you",
            "I told Cupid I have a crush on you... he said 'good luck' 🏹",
            "You're my favorite notification spam",
            "If you were Wi-Fi, I'd only connect to you",
            "You're the plot twist I didn't see coming",
            "I'm not lazy, I'm just waiting for you to text first",
            "You're so hot my phone is overheating",
            "You're my favorite glitch in the matrix",
            "If you were a vegetable, you'd be a cute-cumber 😏",
            "You're the reason I have trust issues with my own heart",
            "I'm not staring at your pics... okay, maybe a little"
        ],
        "cute": [
            "You're my favorite emoji in real life 💕",
            "I want to hug you so tight even this bot is blushing",
            "You're my little ray of sunshine on cloudy days",
            "Even rain feels romantic when I think of you",
            "You're my favorite way to start the morning",
            "You're so cute I want to put you in my pocket",
            "You're my sweetest dream that came true",
            "I want to hold your hand forever",
            "You're my reason to believe in good things",
            "You make the world 100 shades brighter",
            "You're my coziest blanket on cold nights",
            "You're my tiny secret happiness",
            "You're so soft even clouds are jealous",
            "You're my favorite sound when my phone buzzes",
            "You're my warmest February"
        ],
        "flirty": [
            "If looks could undress, you'd be naked by now 😏",
            "You're designed to torture me in the best way",
            "I want to know how your lips taste...",
            "You're my most dangerous temptation",
            "If you don't reply, I'll start spamming hearts",
            "You're so hot my phone just overheated",
            "I want to be the one you think about before sleep",
            "You're my favorite way to break the rules",
            "If you were a drink, I'd sip you all night",
            "You make me forget how to breathe",
            "I want to discover all your secrets... especially the ones under clothes 😈",
            "You're my sweetest forbidden fruit",
            "You're so beautiful even mirrors fall in love",
            "I want to be the reason for your smile... and your blush",
            "You're my favorite sin"
        ]
    }
}

# ────────────────── ВСЕ СТИКЕРЫ В ОДНУ КАТЕГОРИЮ ──────────────────
ALL_VALENTINE_STICKERS = [
    "AAMCAQADGQEAARqOiml-8BkY-A7dEp40DcT05ywrR08rAALJBwAC43gEAAGESQ6JsVOaWwEAB20AAzgE",
    "AAMCAgADGQEAARqOkGl-8rxoWplnK7rktVHALUxxWKPKAAJwBQACP5XMCu8O5gHvPyV7AQAHbQADOAQ",
    "AAMCAgADGQEAARqOlGl-8vIHqKa6DPLGL0Lmga3VD61eAAIXAwACVp29CueGLsTGVMUbAQAHbQADOAQ",
    "AAMCAgADGQEAARqOlml-8wmrULE5165D12HBFazQTl9JAAICAAPANk8TCPVuRfqEp1kBAAdtAAM4BA",
    "AAMCAgADGQEAARqOmml-8yGZxq-LkQLglFki10SlQ3bPAAL6AAP3AsgPcgN0rrC8YjIBAAdtAAM4BA",
    "AAMCAgADGQEAARqOnGl-8zV-TsdF79XpZ-DTbwIROdH2AAJ6AQACIjeOBHzRRJH2EY24AQAHbQADOAQ",
    "AAMCAgADGQEAARqOoGl-80H7pFHzbfv_DSvVfqKmoR0cAAIFAwACVp29CuuXLDaLUDqGAQAHbQADOAQ",
    "AAMCAgADGQEAARqOpGl-80v__AJba1UOUC1zVcncTAeNAAJsAANZu_wlsMc-Gxss4P0BAAdtAAM4BA",
    "AAMCAgADGQEAARqOpml-82FmScSlV4_53VR5jHUfclO1AAIMAAPANk8T4s8j_8J3n7wBAAdtAAM4BA",
    "AAMCAgADGQEAARqOrGl-86nSziYVOh0KJuYUyqm9u22aAAIZAAPANk8T0EOA9iBXFEsBAAdtAAM4BA",
    "AAMCAgADGQEAARqOsGl-8-kF5KnbETG7_C-bssguwi83AAIKAAPANk8T_w2uPugO_QgBAAdtAAM4BA",
    "AAMCAgADGQEAARqOtGl-8_ullzjXIX8eaKRxnNA1po7IAAKJAgACVp29CqFWzQIhMg49AQAHbQADOAQ",
    "AAMCAgADGQEAARqOtml-9AwQPCKHegKW-4COFbV09e6qAAJaEgAC7j_hSzYTwY1_lfrkAQAHbQADOAQ",
    "AAMCAgADGQEAARqOuGl-9BxhvGQXdlyUlqfgAw0W1Qy5AAIKHQACwaggSQiNN_5i8NF4AQAHbQADOAQ",
    "AAMCAgADGQEAARqOuml-9FoKUQzKP4MRYuveH9xwVNDPAAKrEQACyvBQSEm753QxB38OAQAHbQADOAQ",
    "AAMCBAADGQEAARqOvGl-9G260QSes9WEUvNv7H05k_RyAALuEQACpvFxHptzNHbM9taGAQAHbQADOAQ",
    "AAMCAgADGQEAARqOwGl-9IUp2N9kU2M49okk29uJ9Nj1AAIFLQACjgeRSOK9yHW-aXzWAQAHbQADOAQ",
    "AAMCAgADGQEAARqOwml-9JWHx6XENXsxMK85sChog2_-AAKUAAM7YCQU39nXtW9mKSwBAAdtAAM4BA",
]

STICKER_CAPTIONS = [
    "Анонимное признание в анимации 💌",
    "Ты мне нравишься... с анимацией 😏",
    "С 14 февраля ❤️ (анимация)",
    "Roses are red... anonymously animated",
    "Милый стикер для твоего crush",
    "Анонимно, но с душой 💕",
]

class ConfessionForm(StatesGroup):
    waiting_for_recipient = State()
    waiting_for_message = State()

# ────────────────── ХЭНДЛЕРЫ ──────────────────

@router.message(CommandStart())
async def cmd_start(message: Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("Открытка 💌", callback_data="gen_text")],
        [InlineKeyboardButton("Анимированный стикер", callback_data="gen_sticker")],
        [InlineKeyboardButton("Отправить признание", callback_data="start_confess")]
    ])
    await message.answer(
        "Привет! 💌\n\n"
        "Я бот для <b>анонимных признаний</b> и crush-сообщений.\n\n"
        "<b>Команды:</b>\n"
        "• /confess — отправить анонимное признание\n"
        "• /valentine или /gen — сгенерировать валентинку (можно funny, cute, romantic, flirty + en)\n"
        "• /sticker — анимированный стикер\n"
        "• /cancel — отменить текущее действие\n\n"
        "Просто пришли текст / фото / голосовое / стикер — я спрошу, кому отправить.\n"
        "Получатель увидит только меня — 100% анонимно."
    , reply_markup=kb)


# ─── CALLBACK ХЭНДЛЕРЫ ДЛЯ КНОПОК МЕНЮ ───

@router.callback_query(F.data == "gen_text")
async def callback_gen_text(callback: CallbackQuery):
    await callback.answer()
    # Генерируем случайную валентинку (русская, романтичная по умолчанию)
    templates = VALENTINE_TEMPLATES["ru"]["romantic"]
    selected = random.choice(templates)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton("🔄 Другую", callback_data="gen_text")],
        [InlineKeyboardButton("💌 Отправить признание", callback_data="start_confess")]
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
        [InlineKeyboardButton("🔄 Другой стикер", callback_data="gen_sticker")],
        [InlineKeyboardButton("💌 Отправить признание", callback_data="start_confess")]
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


# ─── КОМАНДА ДЛЯ СТИКЕРОВ ───

@router.message(Command("sticker", "valentinessticker"))
async def cmd_sticker(message: Message):
    sticker_id = random.choice(ALL_VALENTINE_STICKERS)
    caption = random.choice(STICKER_CAPTIONS)
    await message.answer_sticker(sticker=sticker_id)
    await message.answer(f"<i>{caption}</i>")


# ─── ОСНОВНОЙ ФУНКЦИОНАЛ ПРИЗНАНИЙ ───

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
        [InlineKeyboardButton("🔄 Другую", callback_data=f"gen_val_{lang}_{category}")],
    ])

    await message.answer(
        f"Вот твоя валентинка ({category}, {lang.upper()}):\n\n"
        f"<blockquote expandable>{selected}</blockquote>",
        reply_markup=kb
    )


# ─── ДОПОЛНИТЕЛЬНЫЙ ХЭНДЛЕР ДЛЯ КНОПКИ "ДРУГУЮ ВАЛЕНТИНКУ" ───
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
                [InlineKeyboardButton("🔄 Другую", callback_data=f"gen_val_{lang}_{category}")],
            ])
            await callback.message.edit_text(
                f"Вот твоя валентинка ({category}, {lang.upper()}):\n\n"
                f"<blockquote expandable>{selected}</blockquote>",
                reply_markup=kb
            )
            return
    await callback.message.answer("Ошибка генерации. Попробуй /valentine")


# ────────────────── ЗАПУСК ──────────────────

async def on_shutdown():
    logging.info("Остановка бота...")
    await dp.stop_polling()
    await bot.session.close()


def setup_signal_handlers():
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, lambda s=sig: asyncio.create_task(shutdown_handler(s)))


async def shutdown_handler(sig):
    logging.info(f"Получен сигнал {sig.name}")
    await on_shutdown()
    sys.exit(0)


async def main():
    # Проверка валидности токена
    try:
        me = await bot.get_me()
        logging.info(f"✅ Бот запущен: @{me.username} (id={me.id})")
    except Exception as e:
        logging.critical(f"❌ Неверный BOT_TOKEN! Ошибка: {e}")
        logging.critical("Проверьте токен в .env или переменных окружения")
        return

    setup_signal_handlers()

    await dp.start_polling(
        bot,
        allowed_updates=["message", "callback_query"],
        drop_pending_updates=True
    )


if __name__ == "__main__":
    asyncio.run(main())
