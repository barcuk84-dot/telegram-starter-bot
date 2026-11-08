import asyncio
import base64
import json
import logging
import math
import os
import random
import re
import sqlite3
import string
from datetime import datetime, timedelta, timezone
from io import BytesIO
from typing import Optional

import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command
from aiogram.types import (
    FSInputFile, Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton,
    LabeledPrice, PreCheckoutQuery, WebAppInfo, KeyboardButton, ReplyKeyboardMarkup
)
from dotenv import load_dotenv

import texts as tx
import texts_ui
from emoji_ids import split_icon
import i18n

texts_ui.apply(tx)  # новое оформление: приветствие, меню, тарифы, помощь

# Читаем настройки из файла ".env" или "env" (без точки) рядом с main.py.
# override=True: значения из файла главнее переменных хостинга (там мог остаться старый токен).
_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
for _name in (".env", "env"):
    _path = os.path.join(_BASE_DIR, _name)
    if os.path.isfile(_path):
        load_dotenv(_path, override=True)
        break

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_IDS = {int(x) for x in os.getenv("ADMIN_IDS", "").split(",") if x.strip().isdigit()}
DB_PATH = os.getenv("DB_PATH", "findtag.db")
API_ID = os.getenv("API_ID", "").strip()
API_HASH = os.getenv("API_HASH", "").strip()
TELETHON_SESSION = os.getenv("TELETHON_SESSION", "findtag_user")
TRON_USDT_ADDRESS = os.getenv("TRON_USDT_ADDRESS", "TFoXZKwdBiyfXkomWV3GNipwQtpCrcguMz").strip()

# GRAM (сеть TON): адрес кошелька и курс. Курс меняется, поэтому его можно
# обновлять командой /gramrate без перезапуска (на время работы бота).
TON_GRAM_ADDRESS = os.getenv("TON_GRAM_ADDRESS", "").strip()
GRAM_PER_USD = float((os.getenv("GRAM_PER_USD", "0") or "0").replace(",", "."))

# Автоматическое подтверждение крипто-платежей (бот сам смотрит блокчейн и начисляет попытки).
AUTO_CRYPTO = os.getenv("AUTO_CRYPTO", "1").strip().lower() not in ("0", "false", "no", "off")
CRYPTO_POLL = max(20, int(os.getenv("CRYPTO_POLL", "45") or 45))              # как часто проверять, сек.
CRYPTO_ORDER_TTL_HOURS = int(os.getenv("CRYPTO_ORDER_TTL_HOURS", "48") or 48)  # сколько заказ ждёт оплату
USDT_CONTRACT = os.getenv("USDT_CONTRACT", "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t").strip()  # USDT в сети TRON
TRONGRID_API_KEY = os.getenv("TRONGRID_API_KEY", "").strip()   # необязательно, но с ключом лимиты выше
# Оставь пустым, если GRAM — основная монета сети TON (как обычный TON). Заполняй только для отдельного токена-джеттона.
GRAM_JETTON_MASTER = os.getenv("GRAM_JETTON_MASTER", "").strip()
if GRAM_JETTON_MASTER and not re.fullmatch(r"[EU]Q[A-Za-z0-9_\-]{46}|-?\d:[0-9a-fA-F]{64}", GRAM_JETTON_MASTER):
    logging.getLogger("findtag").warning("GRAM_JETTON_MASTER не похож на адрес, игнорирую: %r", GRAM_JETTON_MASTER)
    GRAM_JETTON_MASTER = ""
TONAPI_KEY = os.getenv("TONAPI_KEY", "").strip()               # необязательно, ключ с tonapi.io
# Автообновление курса GRAM по рыночной цене (нужен GRAM_JETTON_MASTER). GRAM_PER_USD тогда можно не вписывать.
GRAM_RATE_AUTO = os.getenv("GRAM_RATE_AUTO", "1").strip().lower() not in ("0", "false", "no", "off")
GRAM_RATE_REFRESH = max(60, int(os.getenv("GRAM_RATE_REFRESH", "300") or 300))  # как часто обновлять, сек.
tx.AUTO_CRYPTO = AUTO_CRYPTO

# Шанс найти имя за одну попытку в Premium-поиске (4 и 5 символов). Попытка списывается всегда.
# Шанс показывается пользователю на экранах покупки и поиска — до оплаты. Настраивается в .env.
HIT_CHANCE = {
    4: min(1.0, max(0.0, float((os.getenv("HIT_CHANCE_4", "0.2") or "0.2").replace(",", ".")))),
    5: min(1.0, max(0.0, float((os.getenv("HIT_CHANCE_5", "0.4") or "0.4").replace(",", ".")))),
}
tx.HIT_CHANCE = {n: round(v * 100) for n, v in HIT_CHANCE.items()}

FREE_ATTEMPTS = int(os.getenv("FREE_ATTEMPTS", "6"))
# Ежедневное пополнение баланса 6/7/8: +DAILY_BONUS попыток раз в DAILY_HOURS часов.
# Бонус начисляется при первом заходе в бота после истечения срока и не копится за пропущенные дни.
DAILY_BONUS = int(os.getenv("DAILY_BONUS", "3"))
DAILY_HOURS = int(os.getenv("DAILY_HOURS", "24"))
tx.DAILY_BONUS = DAILY_BONUS
tx.DAILY_HOURS = DAILY_HOURS
BONUS_NOTICE: dict[int, int] = {}
MINI_APP_URL = os.getenv("MINI_APP_URL", "").strip()
TRACK_INTERVAL = int(os.getenv("TRACK_INTERVAL", "900"))  # секунд между проверками трекера
# Откуда кнопка «Автопоиск» берёт имена:
#   db       — из твоей базы (то, что загружено файлом); Telegram используется, только если в базе пусто (по умолчанию)
#   telegram — как раньше, проверка через Telegram; если он не ответил или ничего не нашёл — выдаётся имя из базы
AUTO_SOURCE = os.getenv("AUTO_SOURCE", "db").strip().lower()

# Stars: базовые цены повышены на 25% (STARS_MARKUP). USDT-цены не менялись.
# Базовые цены 40/60 можно переопределить в .env (PACK_40_STARS, PACK_40_USD и т.д.).
STARS_MARKUP = float(os.getenv("STARS_MARKUP", "1.25"))


def markup_stars(base: int) -> int:
    return math.ceil(base * STARS_MARKUP - 1e-9) if base > 0 else 0


_BASE_PACKS = {
    5: (15, 0.49),
    10: (25, 0.89),
    20: (45, 1.49),
    40: (int(os.getenv("PACK_40_STARS", "80") or 0), float(os.getenv("PACK_40_USD", "2.49") or 0)),
    60: (int(os.getenv("PACK_60_STARS", "115") or 0), float(os.getenv("PACK_60_USD", "3.49") or 0)),
    100: (160, 4.99),
}
STANDARD_PACKS = {n: {"stars": markup_stars(s), "usd": u} for n, (s, u) in _BASE_PACKS.items()}
PREMIUM_PACKS_4 = {3: 4.99, 5: 7.99, 7: 10.99, 10: 14.99}
PREMIUM_PACKS_5 = {n: round(price * 0.8 + 1e-9, 2) for n, price in PREMIUM_PACKS_4.items()}
PREMIUM_PACKS = PREMIUM_PACKS_4  # backward-compatible alias

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("findtag")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не указан в .env")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()
USER_STATES: dict[int, str] = {}
SEARCH_LENGTH: dict[int, int] = {}
# Особые значения длины: одна кнопка на 6/7/8 (случайная длина) и случайное Premium-имя из 4/5.
MIX_STD, MIX_PREM = 678, 45
# Длины имён, у которых в карточке НЕТ кнопок «Купить» и «Заявка».
# Хочешь убрать их ещё и для 6 и 7 символов: NO_BUY_LENGTHS = {6, 7, 8}
NO_BUY_LENGTHS = {8}
# Покупка самих имён (кнопки «Купить» и «Заявка» в карточке). False = выключена для ВСЕХ длин:
# пользователи покупают только попытки в разделе «Тарифы». Включить обратно: BUY_NAMES = True
BUY_NAMES = False


def can_buy_name(name: str) -> bool:
    return BUY_NAMES and len(name) not in NO_BUY_LENGTHS
# История найденных имён пользователя: по ней работают «Предыдущий» / «Следующий».
USER_HISTORY: dict[int, dict] = {}
HISTORY_LIMIT = 30
telethon_client = None
AUTO_SEARCH_ENABLED = False


def now_iso():
    return datetime.now(timezone.utc).isoformat()


def gram_enabled() -> bool:
    return bool(TON_GRAM_ADDRESS) and GRAM_PER_USD > 0


def gram_amount(usd: float) -> float:
    return round(usd * GRAM_PER_USD, 2) if gram_enabled() else 0.0


def connect_db():
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db():
    with connect_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY, attempts INTEGER NOT NULL DEFAULT 6,
            premium_attempts INTEGER NOT NULL DEFAULT 0, joined_at TEXT NOT NULL,
            attempts_4 INTEGER NOT NULL DEFAULT 0, attempts_5 INTEGER NOT NULL DEFAULT 0)""")
        cols = {r[1] for r in db.execute("PRAGMA table_info(users)")}
        if "premium_attempts" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN premium_attempts INTEGER NOT NULL DEFAULT 0")
        if "attempts_4" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN attempts_4 INTEGER NOT NULL DEFAULT 0")
        if "attempts_5" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN attempts_5 INTEGER NOT NULL DEFAULT 0")
        if "last_refill" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN last_refill TEXT")
        if "lang" not in cols:
            db.execute("ALTER TABLE users ADD COLUMN lang TEXT")
        # Существующим пользователям первый бонус придёт через DAILY_HOURS часов, а не сразу.
        db.execute("UPDATE users SET last_refill=? WHERE last_refill IS NULL", (now_iso(),))
        # One-time transfer of the old combined premium balance to the 4-char balance.
        db.execute("UPDATE users SET attempts_4=premium_attempts, premium_attempts=0 WHERE premium_attempts>0")

        db.execute("""CREATE TABLE IF NOT EXISTS usernames (
            username TEXT PRIMARY KEY, source TEXT NOT NULL DEFAULT 'database',
            status TEXT NOT NULL DEFAULT 'available', price_stars INTEGER NOT NULL DEFAULT 0,
            added_by INTEGER, added_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS name_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            username TEXT NOT NULL, replacement TEXT, status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            username TEXT NOT NULL, kind TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS tracked (
            user_id INTEGER NOT NULL, username TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(user_id, username))""")
        db.execute("""CREATE TABLE IF NOT EXISTS favorites (
            user_id INTEGER NOT NULL, username TEXT NOT NULL, created_at TEXT NOT NULL,
            PRIMARY KEY(user_id, username))""")
        db.execute("""CREATE TABLE IF NOT EXISTS payments (
            telegram_charge_id TEXT PRIMARY KEY, user_id INTEGER NOT NULL,
            payload TEXT NOT NULL, amount INTEGER NOT NULL, created_at TEXT NOT NULL)""")
        db.execute("""CREATE TABLE IF NOT EXISTS crypto_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            kind TEXT NOT NULL, credit_amount INTEGER NOT NULL, amount_usd REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending', txid TEXT,
            created_at TEXT NOT NULL, paid_at TEXT)""")
        crypto_cols = {r[1] for r in db.execute("PRAGMA table_info(crypto_orders)")}
        if "kind" not in crypto_cols:
            db.execute("ALTER TABLE crypto_orders ADD COLUMN kind TEXT NOT NULL DEFAULT 'standard'")
        if "credit_amount" not in crypto_cols:
            db.execute("ALTER TABLE crypto_orders ADD COLUMN credit_amount INTEGER NOT NULL DEFAULT 0")
        if "paid_at" not in crypto_cols:
            db.execute("ALTER TABLE crypto_orders ADD COLUMN paid_at TEXT")
        # Новые колонки для GRAM/TON: существующие заказы остаются USDT.
        if "pay_asset" not in crypto_cols:
            db.execute("ALTER TABLE crypto_orders ADD COLUMN pay_asset TEXT NOT NULL DEFAULT 'USDT'")
        if "pay_amount" not in crypto_cols:
            db.execute("ALTER TABLE crypto_orders ADD COLUMN pay_amount REAL")
        if "package_attempts" in crypto_cols:
            db.execute("UPDATE crypto_orders SET credit_amount=package_attempts WHERE credit_amount=0")
            # Preserve pending premium orders from the previous schema when their
            # count and amount match the old 4-character package list.
            for old_count, old_price in PREMIUM_PACKS_4.items():
                db.execute("UPDATE crypto_orders SET kind='premium4' WHERE kind='standard' AND package_attempts=? AND ABS(amount_usd-?)<0.001",
                           (old_count, old_price))
        db.commit()


def parse_iso(value):
    try:
        return datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def claim_daily(uid: int) -> int:
    """Начисляет ежедневный бонус на баланс 6/7/8, если с прошлого прошло DAILY_HOURS часов."""
    if DAILY_BONUS <= 0:
        return 0
    granted = 0
    with connect_db() as db:
        row = db.execute("SELECT last_refill FROM users WHERE user_id=?", (uid,)).fetchone()
        if row is None:
            return 0
        old = row["last_refill"]
        last = parse_iso(old)
        now = datetime.now(timezone.utc)
        if last is not None and now - last < timedelta(hours=DAILY_HOURS):
            return 0
        # Условие last_refill IS ? защищает от двойного начисления при одновременных запросах.
        cur = db.execute("UPDATE users SET attempts=attempts+?, last_refill=? WHERE user_id=? AND last_refill IS ?",
                         (DAILY_BONUS, now.isoformat(), uid, old))
        if cur.rowcount == 1:
            granted = DAILY_BONUS
    if granted:
        BONUS_NOTICE[uid] = BONUS_NOTICE.get(uid, 0) + granted
    return granted


def refill_in_text(uid: int):
    """Сколько осталось до следующего бонуса, например '5 ч 20 мин' / '5 h 20 min'."""
    with connect_db() as db:
        row = db.execute("SELECT last_refill FROM users WHERE user_id=?", (uid,)).fetchone()
    last = parse_iso(row["last_refill"]) if row else None
    if last is None:
        return None
    secs = max(0, int((last + timedelta(hours=DAILY_HOURS) - datetime.now(timezone.utc)).total_seconds()))
    hours, minutes = secs // 3600, (secs % 3600) // 60
    if i18n.current_lang() == "en":
        return f"{hours} h {minutes} min" if hours else f"{max(1, minutes)} min"
    return f"{hours} ч {minutes} мин" if hours else f"{max(1, minutes)} мин"


def ensure_user(uid: int):
    with connect_db() as db:
        db.execute("""INSERT OR IGNORE INTO users
            (user_id, attempts, premium_attempts, joined_at, attempts_4, attempts_5, last_refill)
            VALUES(?,?,?,?,?,?,?)""", (uid, FREE_ATTEMPTS, 0, now_iso(), 0, 0, now_iso()))
    claim_daily(uid)


def get_lang(uid: int) -> Optional[str]:
    """Язык пользователя ('ru' / 'en') или None, если он ещё не выбирал."""
    with connect_db() as db:
        row = db.execute("SELECT lang FROM users WHERE user_id=?", (uid,)).fetchone()
    return row["lang"] if row and row["lang"] in ("ru", "en") else None


def set_lang(uid: int, lang: str):
    ensure_user(uid)
    with connect_db() as db:
        db.execute("UPDATE users SET lang=? WHERE user_id=?", (lang, uid))


from aiogram import BaseMiddleware


class LangMiddleware(BaseMiddleware):
    """Перед каждым обработчиком выставляет язык пользователя — по нему переводятся кнопки."""
    async def __call__(self, handler, event, data):
        user = data.get("event_from_user")
        i18n.set_lang(get_lang(user.id) if user else "ru")
        return await handler(event, data)


dp.update.outer_middleware(LangMiddleware())


def language_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru"),
        InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en"),
    ]])


LANGUAGE_PROMPT = ("🌍 <b>Прежде чем начать, выберите язык</b>\n"
                   "<b>Before we start, please choose your language</b>")


async def show_main_menu(uid: int, first_name: str):
    """Приветствие + основное меню (показывается после выбора языка)."""
    bonus = BONUS_NOTICE.pop(uid, 0)
    await send_screen(uid, tx.bonus_line(bonus) + tx.welcome(first_name, FREE_ATTEMPTS, AUTO_SEARCH_ENABLED, lang=get_lang(uid)),
                      main_keyboard(), banner="welcome")


def balances(uid: int):
    ensure_user(uid)
    with connect_db() as db:
        r = db.execute("SELECT attempts,attempts_4,attempts_5 FROM users WHERE user_id=?", (uid,)).fetchone()
    return int(r["attempts"]), int(r["attempts_4"]), int(r["attempts_5"])


def balance_for(uid: int, length: int) -> int:
    free, four, five = balances(uid)
    return four if length == 4 else five if length == 5 else free


def spend_attempt(uid: int, length=6) -> bool:
    ensure_user(uid)
    field = "attempts_4" if length == 4 else "attempts_5" if length == 5 else "attempts"
    with connect_db() as db:
        cur = db.execute(f"UPDATE users SET {field}={field}-1 WHERE user_id=? AND {field}>0", (uid,))
        return cur.rowcount == 1


def credit_attempts(uid: int, amount: int, premium=False, length=None):
    ensure_user(uid)
    if length is not None:
        field = "attempts_4" if length == 4 else "attempts_5" if length == 5 else "attempts"
    else:
        field = "attempts_4" if premium else "attempts"
    with connect_db() as db:
        db.execute(f"UPDATE users SET {field}={field}+? WHERE user_id=?", (int(amount), uid))


def add_favorite(uid: int, name: str):
    with connect_db() as db:
        db.execute("INSERT OR IGNORE INTO favorites(user_id,username,created_at) VALUES(?,?,?)", (uid, name, now_iso()))


def list_favorites(uid: int):
    with connect_db() as db:
        return db.execute("SELECT username FROM favorites WHERE user_id=? ORDER BY created_at DESC", (uid,)).fetchall()


def remove_favorite(uid: int, name: str):
    with connect_db() as db:
        db.execute("DELETE FROM favorites WHERE user_id=? AND username=?", (uid, name))


def add_tracked(uid: int, name: str):
    with connect_db() as db:
        db.execute("INSERT OR IGNORE INTO tracked(user_id,username,created_at) VALUES(?,?,?)", (uid, name, now_iso()))


def list_tracked(uid: int):
    with connect_db() as db:
        return db.execute("SELECT username FROM tracked WHERE user_id=? ORDER BY created_at DESC", (uid,)).fetchall()


def remove_tracked(uid: int, name: str):
    with connect_db() as db:
        db.execute("DELETE FROM tracked WHERE user_id=? AND username=?", (uid, name))


def stats_snapshot():
    with connect_db() as db:
        return {
            "users": db.execute("SELECT COUNT(*) c FROM users").fetchone()["c"],
            "tracked": db.execute("SELECT COUNT(*) c FROM tracked").fetchone()["c"],
            "orders": db.execute("SELECT COUNT(*) c FROM orders").fetchone()["c"],
            "pending": db.execute("SELECT COUNT(*) c FROM crypto_orders WHERE status='pending'").fetchone()["c"],
            "paid": db.execute("SELECT COUNT(*) c FROM crypto_orders WHERE status='paid'").fetchone()["c"],
            "stars": db.execute("SELECT COALESCE(SUM(amount),0) s FROM payments").fetchone()["s"],
            "by_length": [(r["l"], r["c"]) for r in db.execute(
                "SELECT length(username) l, COUNT(*) c FROM usernames WHERE status='available' "
                "GROUP BY length(username) ORDER BY l")],
        }


def clean_username(value: str) -> str:
    value = value.strip().lstrip("@").lower()
    if not re.fullmatch(r"[a-z0-9_]{4,32}", value):
        raise ValueError("Допустимы только латинские буквы, цифры и _. Длина: 4–32 символа.")
    return value


def safe_name(value: str) -> Optional[str]:
    try:
        return clean_username(value)
    except ValueError:
        return None


def add_username(username: str, source="database", price_stars=0, admin_id=0):
    username = clean_username(username)
    with connect_db() as db:
        db.execute("""INSERT INTO usernames(username,source,status,price_stars,added_by,added_at)
            VALUES(?,?, 'available', ?, ?, ?) ON CONFLICT(username) DO UPDATE SET
            source=excluded.source,status='available',price_stars=excluded.price_stars,added_by=excluded.added_by""",
            (username, source, max(0, int(price_stars)), admin_id, now_iso()))


def delete_usernames(names):
    deleted = 0
    with connect_db() as db:
        for name in names:
            try:
                name = clean_username(name)
            except ValueError:
                continue
            cur = db.execute("DELETE FROM usernames WHERE username=?", (name,))
            deleted += cur.rowcount
    return deleted


def claim_username(username: str) -> bool:
    """Помечает имя как выданное (больше не попадёт в поиск и не учитывается в статистике available)."""
    with connect_db() as db:
        cur = db.execute(
            "UPDATE usernames SET status='shown' WHERE username=? AND status='available'",
            (username,),
        )
        return cur.rowcount == 1


def get_random_username(length: int, exclude=()):
    """Случайное имя нужной длины. Имена из exclude (уже показанные) пропускаются, если есть другие.
    Сразу помечает имя status='shown', чтобы его не получил другой пользователь и оно
    исчезло из статистики «свободные имена в базе».
    """
    exclude = list(exclude) if exclude else []
    # Несколько попыток на случай гонки двух пользователей за одно имя.
    for _ in range(8):
        with connect_db() as db:
            if exclude:
                marks = ",".join("?" * len(exclude))
                row = db.execute(
                    f"SELECT * FROM usernames WHERE status='available' AND length(username)=? "
                    f"AND username NOT IN ({marks}) ORDER BY RANDOM() LIMIT 1",
                    (length, *exclude),
                ).fetchone()
            else:
                row = None
            if row is None:
                row = db.execute(
                    "SELECT * FROM usernames WHERE status='available' AND length(username)=? "
                    "ORDER BY RANDOM() LIMIT 1",
                    (length,),
                ).fetchone()
            if row is None:
                return None
            cur = db.execute(
                "UPDATE usernames SET status='shown' WHERE username=? AND status='available'",
                (row["username"],),
            )
            if cur.rowcount == 1:
                return row
            # Кто-то успел забрать это имя — исключаем и пробуем другое.
            exclude.append(row["username"])
    return None


def create_order(uid: int, username: str, kind: str) -> int:
    with connect_db() as db:
        cur = db.execute("INSERT INTO orders(user_id,username,kind,status,created_at) VALUES(?,?,?,'pending',?)",
                         (uid, username, kind, now_iso()))
        return cur.lastrowid


def list_orders(uid: int, limit=5):
    with connect_db() as db:
        return db.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT ?", (uid, limit)).fetchall()


def create_crypto_order(uid: int, kind: str, credits: int, usd: float, asset="USDT", pay_amount=None) -> int:
    with connect_db() as db:
        cols = {r[1] for r in db.execute("PRAGMA table_info(crypto_orders)")}
        if "package_attempts" in cols and "currency" in cols:
            cur = db.execute("""INSERT INTO crypto_orders
                (user_id,package_attempts,currency,amount_usd,status,kind,credit_amount,created_at)
                VALUES(?,?,'USDT_TRC20',?,'pending',?,?,?)""",
                (uid, credits, usd, kind, credits, now_iso()))
        else:
            cur = db.execute("INSERT INTO crypto_orders(user_id,kind,credit_amount,amount_usd,created_at) VALUES(?,?,?,?,?)",
                             (uid, kind, credits, usd, now_iso()))
        order_id = int(cur.lastrowid)
        db.execute("UPDATE crypto_orders SET pay_asset=?, pay_amount=? WHERE id=?",
                   (asset, pay_amount if pay_amount is not None else usd, order_id))
        return order_id


def pending_crypto_orders(limit=15):
    with connect_db() as db:
        return db.execute("""SELECT id,user_id,kind,credit_amount,
            COALESCE(pay_amount, amount_usd) AS pay_amount, COALESCE(pay_asset,'USDT') AS pay_asset
            FROM crypto_orders WHERE status='pending' ORDER BY id DESC LIMIT ?""", (limit,)).fetchall()


def confirm_crypto_order(order_id: int, txid: str):
    """Подтверждает заказ и начисляет попытки. Общая логика для /paid и автопроверки.
    Возвращает (статус, заказ): ok | not_found | processed | dup_tx."""
    with connect_db() as db:
        row = db.execute("SELECT * FROM crypto_orders WHERE id=?", (order_id,)).fetchone()
        if not row: return "not_found", None
        if row["status"] not in ("pending", "expired"): return "processed", row
        if db.execute("SELECT id FROM crypto_orders WHERE txid=? AND id<>?", (txid, order_id)).fetchone():
            return "dup_tx", row
        try:
            cur = db.execute("UPDATE crypto_orders SET status='paid',txid=?,paid_at=? WHERE id=? AND status IN ('pending','expired')",
                             (txid, now_iso(), order_id))
        except sqlite3.IntegrityError:
            return "dup_tx", row
        if cur.rowcount != 1: return "processed", row
    kind = row["kind"]
    target_length = 4 if kind in ("premium", "premium4") else 5 if kind == "premium5" else 678
    credit_attempts(row["user_id"], row["credit_amount"], length=target_length)
    return "ok", row


def unique_usdt_amount(usd: float) -> float:
    """К цене добавляются доли цента (0.001–0.099), чтобы платёж однозначно привязывался к заказу."""
    if not AUTO_CRYPTO: return usd
    with connect_db() as db:
        used = {round(float(r["a"]), 3) for r in db.execute(
            "SELECT COALESCE(pay_amount, amount_usd) AS a FROM crypto_orders "
            "WHERE status='pending' AND COALESCE(pay_asset,'USDT')='USDT'")}
    for k in range(1, 100):
        cand = round(usd + k / 1000, 3)
        if cand not in used: return cand
    return usd


def pending_orders_asset(asset: str):
    with connect_db() as db:
        return db.execute("""SELECT id,user_id,kind,credit_amount,created_at,
            COALESCE(pay_amount, amount_usd) AS pay_amount FROM crypto_orders
            WHERE status='pending' AND COALESCE(pay_asset,'USDT')=? ORDER BY id""", (asset,)).fetchall()


def expire_old_crypto_orders():
    cutoff = (datetime.now(timezone.utc) - timedelta(hours=CRYPTO_ORDER_TTL_HOURS)).isoformat()
    with connect_db() as db:
        db.execute("UPDATE crypto_orders SET status='expired' WHERE status='pending' AND created_at<?", (cutoff,))


def txid_used(txid: str) -> bool:
    with connect_db() as db:
        return db.execute("SELECT 1 FROM crypto_orders WHERE txid=?", (txid,)).fetchone() is not None


def order_created_ts(order) -> float:
    dt = parse_iso(order["created_at"])
    return dt.timestamp() if dt else 0.0


def ton_raw(addr: str) -> str:
    """Приводит адрес TON к виду 0:hex, чтобы сравнивать адреса в разных форматах."""
    addr = (addr or "").strip()
    if ":" in addr:
        wc, h = addr.split(":", 1)
        try: return f"{int(wc)}:{h.lower()}"
        except ValueError: return addr
    try:
        b = base64.urlsafe_b64decode(addr.replace("+", "-").replace("/", "_") + "=" * (-len(addr) % 4))
        return f"{int.from_bytes(b[1:2], 'big', signed=True)}:{b[2:34].hex()}"
    except Exception:
        return addr


def username_score(name: str):
    score = 10 if len(name) <= 4 else 9 if len(name) == 5 else 8 if len(name) == 6 else 7 if len(name) <= 8 else 6
    if any(c.isdigit() for c in name): score -= 1
    if "__" in name or name.startswith("_") or name.endswith("_"): score -= 2
    score = max(1, min(10, score))
    liquidity = max(1, score - (1 if any(c.isdigit() for c in name) else 0))
    return score, liquidity


def estimate_value(name: str):
    """Illustrative algorithmic range, not a market quote or verified comparable sale."""
    score, _ = username_score(name)
    five = (12, 80)
    base = {4: (five[0] * 2, five[1] * 2), 5: five, 6: (1, 15), 7: (0.5, 8), 8: (0.2, 5)}.get(len(name), (0.1, 3))
    multiplier = max(0.35, score / 8)
    return round(base[0] * multiplier, 2), round(base[1] * multiplier, 2)


def price_text(name: str):
    low, high = estimate_value(name)
    return f"${low:.2f}–${high:.2f}"


def username_traits(name: str):
    """Короткие человекочитаемые особенности имени для карточек."""
    n = len(name)
    en = i18n.current_lang() == "en"
    if en:
        traits = [f"length {n} chars" + (" — rare category" if n <= 5 else "")]
        if name.isalpha():
            traits.append("letters only — looks clean")
            if any(c in "aeiouy" for c in name):
                traits.append("has vowels — easier to pronounce and remember")
            else:
                traits.append("no vowels — harder to remember")
        if any(c.isdigit() for c in name):
            traits.append("contains digits — lower liquidity")
        if "_" in name:
            traits.append("has underscore — looks less premium")
        if n > 2 and name == name[::-1]:
            traits.append("palindrome — reads the same both ways")
        if n >= 4 and len(set(name)) <= n // 2:
            traits.append("many repeated characters")
        return traits
    traits = [f"длина {n} симв." + (" — редкая категория" if n <= 5 else "")]
    if name.isalpha():
        traits.append("только буквы — выглядит чисто")
        if any(c in "aeiouy" for c in name):
            traits.append("есть гласные — легче произносить и запоминать")
        else:
            traits.append("нет гласных — сложнее запомнить")
    if any(c.isdigit() for c in name):
        traits.append("содержит цифры — ликвидность ниже")
    if "_" in name:
        traits.append("есть подчёркивание — выглядит менее премиально")
    if n > 2 and name == name[::-1]:
        traits.append("палиндром — читается одинаково в обе стороны")
    if n >= 4 and len(set(name)) <= n // 2:
        traits.append("много повторяющихся символов")
    return traits


def username_card(name: str, price_stars=0, source="database", pos=None):
    score, liquidity = username_score(name)
    return tx.username_card(name, score, liquidity, price_text(name), price_stars, source, username_traits(name),
                            pos=pos, can_buy=can_buy_name(name))


# Цвета кнопок (Bot API: success = зелёная, primary = синяя, danger = красная).
# Правило работает по началу callback_data кнопки.
BUTTON_STYLES = (
    # Оплата — зелёные
    ("starbuy:", "success"), ("usdtbuy:", "success"), ("grambuy:", "success"),
    ("prembuy:", "success"), ("premgram:", "success"),
    # Главные действия — синие
    ("search_db", "primary"), ("search_auto", "primary"),
    ("tariffs", "primary"),
    ("premium_shop:", "primary"), ("name_next", "primary"), ("track:", "primary"),
    # В избранное — зелёная, удаление — красные
    ("favorite:", "success"),
    ("taken:", "danger"), ("rep:", "success"), ("rej:", "danger"),
    ("unfav:", "danger"), ("untrack:", "danger"), ("admin_delete", "danger"),
    # Главное меню — единый синий стиль для основных разделов
    ("rate", "primary"), ("tracker", "primary"),
    ("compare", "primary"),
    ("favorites", "primary"), ("profile", "primary"), ("tariffs", "primary"),
    ("help", "success"),
    # Выбор длины и пакетов
    ("length:", "primary"), ("pack:", "primary"),
)


def button_style(data: str):
    for prefix, style in BUTTON_STYLES:
        if data == prefix or (prefix.endswith(":") and data.startswith(prefix)):
            return style
    return None


def btn(text, data, style=None):
    # Если для эмодзи в начале текста задан ID в emoji_ids.py — показываем анимированный эмодзи.
    text = i18n.tr_button(text)
    rest, emoji_id = split_icon(text)
    extra = {}
    if emoji_id:
        text, extra["icon_custom_emoji_id"] = rest, emoji_id
    style = style or button_style(data)
    if style:
        extra["style"] = style
    return InlineKeyboardButton(text=text, callback_data=data, **extra)


def main_keyboard():
    if MINI_APP_URL.startswith("https://"):
        open_label = i18n.tr_button("🌈 Открыть FindTag")
        return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text=open_label, web_app=WebAppInfo(url=MINI_APP_URL))]], resize_keyboard=True, is_persistent=True)
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("🔍 Поиск", "search", style="danger")],
        [btn("⭐ Оценить", "rate"), btn("⚖️ Сравнение", "compare")],
        [btn("📡 Трекер", "tracker"), btn("❤️ Избранное", "favorites")],
        [btn("👤 Профиль", "profile"), btn("💎 Тарифы", "tariffs")],
        [btn("ℹ️ Помощь", "help")]])


def back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("⬅️ В меню", "menu")]])


def search_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("🔍 Найти юзернейм", "search_db")], [btn("⬅️ К поиску", "search")]])


def buy_keyboard(length: int):
    target = f"premium_shop:{length}" if length in (4, 5) else "tariffs"
    return InlineKeyboardMarkup(inline_keyboard=[[btn("💎 Пополнить баланс", target)], [btn("⬅️ К поиску", "search")]])


def length_label(sel: int) -> str:
    if i18n.current_lang() == "en":
        return "6–8 chars" if sel == MIX_STD else "4–5 chars" if sel == MIX_PREM else f"{sel} chars"
    return "6–8 символов" if sel == MIX_STD else "4–5 символов" if sel == MIX_PREM else f"{sel} символов"


def selection_balance(uid: int, sel: int) -> int:
    if sel == MIX_PREM:
        _, four, five = balances(uid)
        return four + five
    return balance_for(uid, 6 if sel == MIX_STD else sel)


def pick_length(uid: int):
    """Реальная длина поиска. Для режимов 6–8 и 4–5 выбирается случайная. None — нет попыток на 4/5."""
    sel = SEARCH_LENGTH.get(uid, MIX_STD)
    if sel == MIX_STD:
        return random.choice((6, 7, 8))
    if sel == MIX_PREM:
        have = [n for n in (4, 5) if balance_for(uid, n) > 0]
        return random.choice(have) if have else None
    return sel


def search_keyboard(uid: int):
    sel = SEARCH_LENGTH.get(uid, MIX_STD)
    group_balance = selection_balance(uid, sel)
    if sel in (4, 5):
        buy_target = f"premium_shop:{sel}"
    elif sel == MIX_PREM:
        buy_target = "premium_shop:5"
    else:
        buy_target = "tariffs"
    if i18n.current_lang() == "en":
        length_btn = f"Length: {length_label(sel)} ⚙️"
        balance_btn = f"Balance: {group_balance} attempts"
    else:
        length_btn = f"Длина: {length_label(sel)} ⚙️"
        balance_btn = f"Баланс: {group_balance} попыток"
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn(length_btn, "lengths")],
        [btn(balance_btn, "lengths")],
        [btn("🔍 Найти юзернейм", "search_db")],
        [btn("💎 Купить попытки", buy_target)],
        [btn("⬅️ В меню", "menu")]])


def lengths_keyboard(uid: int = None):
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("🎲 6 · 7 · 8", f"length:{MIX_STD}")],
        [btn("4 · Premium", "length:4"), btn("5 · Premium", "length:5")],
        [btn("🎲 Случайное 4/5 · Premium", f"length:{MIX_PREM}")],
        [btn("⬅️ Назад", "menu")]])


def premium_offer_keyboard(n=None):
    if n is None:
        buy = [btn("💎 Пакеты 4 символа", "premium_shop:4"), btn("💎 Пакеты 5 символов", "premium_shop:5")]
    else:
        buy = [btn("💎 Купить попытки", f"premium_shop:{n}")]
    return InlineKeyboardMarkup(inline_keyboard=[buy, [btn("⬅️ Назад", "search")]])


def username_keyboard(name: str, uid=None):
    rows = [[btn("❤️ В избранное", f"favorite:{name}")]]
    if can_buy_name(name):
        rows.append([btn("🛒 Купить", f"buy:{name}"), btn("📝 Заявка", f"request:{name}")])
    rows.append([btn("📡 Отслеживать", f"track:{name}"), btn("⚠️ Имя занято", f"taken:{name}")])
    h = USER_HISTORY.get(uid)
    if h:
        nav = []
        if h["idx"] > 0:
            nav.append(btn("⬅️ Предыдущий", "name_prev"))
        at_end = h["idx"] >= len(h["items"]) - 1
        # Дальше по истории — бесплатно, новое имя — списывает попытку.
        nav.append(btn("Следующий ➡️ −1🎟" if at_end else "Следующий ➡️", "name_next"))
        rows.append(nav)
    rows.append([btn("⬅️ К поиску", "search")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def push_history(uid: int, name: str, price_stars: int, source: str):
    h = USER_HISTORY.setdefault(uid, {"items": [], "idx": -1})
    h["items"].append({"name": name, "price_stars": price_stars, "source": source})
    if len(h["items"]) > HISTORY_LIMIT:
        h["items"].pop(0)
    h["idx"] = len(h["items"]) - 1


def screen_username(uid: int):
    """Карточка текущего имени из истории + кнопки."""
    h = USER_HISTORY[uid]
    item = h["items"][h["idx"]]
    pos = (h["idx"] + 1, len(h["items"]))
    return (username_card(item["name"], item["price_stars"], item["source"], pos),
            username_keyboard(item["name"], uid))


def tariffs_keyboard():
    rows = []
    for n, pack in STANDARD_PACKS.items():
        stars = f"{pack['stars']}⭐" if pack["stars"] else "—"
        usd = f"${pack['usd']:.2f}" if pack["usd"] else "—"
        rows.append([btn(f"🎟 {n} попыток · {stars} · {usd}", f"pack:{n}")])
    rows += [[btn("💎 Premium 5 символов", "premium_shop:5")],
             [btn("💎 Premium 4 символа", "premium_shop:4")],
             [btn("⬅️ В меню", "menu")]]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def pack_pay_keyboard(n: int):
    gram_btn = btn("💎 Оплатить GRAM (TON)", f"grambuy:{n}") if gram_enabled() else btn("💎 GRAM (TON) · скоро", "gram_off")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("⭐ Оплатить Stars", f"starbuy:{n}")],
        [btn("💵 Оплатить USDT (TRC20)", f"usdtbuy:{n}")],
        [gram_btn],
        [btn("⬅️ К тарифам", "tariffs")]])


def premium_pay_keyboard(length: int, count: int):
    gram_btn = btn("💎 Оплатить GRAM (TON)", f"premgram:{length}:{count}") if gram_enabled() else btn("💎 GRAM (TON) · скоро", "gram_off")
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("💵 Оплатить USDT (TRC20)", f"prembuy:{length}:{count}")],
        [gram_btn],
        [btn("⬅️ К пакетам", f"premium_shop:{length}")]])


def order_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("👤 Мой профиль", "profile")], [btn("⬅️ В меню", "menu")]])


def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [btn("➕ Добавить юзернейм", "admin_add"), btn("🗑 Удалить юзернейм", "admin_delete")],
        [btn("🎟 Выдать попытки", "admin_grant")],
        [btn("📋 Последние заявки", "admin_orders"), btn("💳 Крипто-заказы", "admin_crypto")],
        [btn("📊 Статистика", "admin_stats")],
        [btn("⬅️ В меню", "menu")]])


def admin_back_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[[btn("⬅️ В админку", "admin")]])


async def notify_admins(text: str):
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, text)
        except Exception: log.exception("Не удалось уведомить администратора %s", admin_id)


async def safe_callback_answer(c: CallbackQuery, text=""):
    try: await c.answer(text)
    except Exception as exc: log.debug("Callback query expired or already answered: %s", exc)


async def delete_callback_message(c: CallbackQuery):
    try:
        if c.message: await c.message.delete()
    except Exception as exc: log.debug("Previous message could not be deleted: %s", exc)


def get_setting(key: str) -> Optional[str]:
    with connect_db() as db:
        row = db.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    return row["value"] if row else None


def set_setting(key: str, value: str):
    with connect_db() as db:
        db.execute("INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                   (key, value))


BANNER_FILE = os.getenv("BANNER_FILE", "banner.jpg")  # необязательно: картинка рядом с main.py для экрана «menu»
# Экраны, к которым можно привязать свой баннер: /banner <экран> (в подписи к фото).
BANNER_SCREENS = {
    "welcome": "приветствие после /start (если не задан — берётся баннер «menu»)",
    "menu": "главное меню",
    "search": "экран «Поиск» (выбор длины)",
    "card": "карточка выданного юзернейма",
    "tariffs": "тарифы",
    "profile": "профиль",
    "help": "помощь",
    "favorites": "избранное",
    "tracker": "трекер",
    "rate": "оценка имени",
    "compare": "сравнение",
}
BANNER_FALLBACK = {"welcome": "menu"}


def banner_photo(key: str):
    """file_id (или файл) баннера для экрана; None, если не задан."""
    photo = get_setting(f"banner:{key}")
    if not photo and key == "menu":
        photo = get_setting("banner_file_id")  # совместимость с прошлой версией
    if not photo and key == "menu" and os.path.exists(BANNER_FILE):
        photo = FSInputFile(BANNER_FILE)
    if not photo and key in BANNER_FALLBACK:
        return banner_photo(BANNER_FALLBACK[key])
    return photo


async def send_screen(chat_id: int, text: str, keyboard=None, banner=None):
    """Отправляет экран. banner — ключ экрана из BANNER_SCREENS (True = «menu»).
    Фото ставится, только если баннер задан и текст влезает в подпись (1024 символа)."""
    key = "menu" if banner is True else banner
    if key and len(text) <= 1024:
        photo = banner_photo(key)
        if photo:
            try:
                msg = await bot.send_photo(chat_id, photo, caption=text, reply_markup=keyboard, parse_mode="HTML")
                if isinstance(photo, FSInputFile) and msg.photo:
                    set_setting(f"banner:{key}", msg.photo[-1].file_id)  # дальше шлём по file_id — быстрее
                return msg
            except Exception:
                log.exception("Не удалось отправить баннер — шлю текстом")
    return await bot.send_message(chat_id, text, reply_markup=keyboard, parse_mode="HTML")


async def edit(c: CallbackQuery, text: str, keyboard=None, banner=None):
    await delete_callback_message(c)
    await send_screen(c.from_user.id, text, keyboard, banner=banner)


# ───────────── Экраны: одни и те же тексты для кнопок и для Mini App ─────────────

def screen_menu():
    return tx.menu(), main_keyboard()


def screen_search(uid: int):
    SEARCH_LENGTH.setdefault(uid, MIX_STD)
    free, four, five = balances(uid)
    bonus = BONUS_NOTICE.pop(uid, 0)
    return tx.bonus_line(bonus) + tx.search_hub(free, four, five), lengths_keyboard(uid)


def screen_length(uid: int, n: int):
    bal = selection_balance(uid, n)
    text = tx.length_screen(n, bal, AUTO_SEARCH_ENABLED)
    if n == 4:
        kb = [[btn("🔍 Найти юзернейм", "search_db")], [btn("💎 Пакеты 4 символа", "premium_shop:4")], [btn("⬅️ Назад", "search")]]
    elif n == 5:
        kb = [[btn("🔍 Найти юзернейм", "search_db")], [btn("💎 Пакеты 5 символов", "premium_shop:5")], [btn("⬅️ Назад", "search")]]
    elif n == MIX_PREM:
        kb = [[btn("🔍 Найти юзернейм", "search_db")],
              [btn("💎 Пакеты 4 символа", "premium_shop:4"), btn("💎 Пакеты 5 символов", "premium_shop:5")],
              [btn("⬅️ Назад", "search")]]
    else:
        kb = [[btn("🔍 Найти юзернейм", "search_db")], [btn("💎 Пакеты 6–8", "tariffs")], [btn("⬅️ Назад", "search")]]
    return text, InlineKeyboardMarkup(inline_keyboard=kb)


def screen_profile(uid: int):
    free, four, five = balances(uid)
    orders = [(o["id"], o["username"], o["status"]) for o in list_orders(uid)]
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [btn("💎 Пополнить баланс", "tariffs")],
        [btn("❤️ Избранное", "favorites"), btn("📡 Трекер", "tracker")],
        [btn("🌍 Выбрать язык", "profile_lang")],
        [btn("⬅️ В меню", "menu")]])
    bonus = BONUS_NOTICE.pop(uid, 0)
    return tx.bonus_line(bonus) + tx.profile(uid, free, four, five, orders, refill_in_text(uid)), kb


def screen_tariffs():
    return tx.tariffs(gram_enabled(), FREE_ATTEMPTS), tariffs_keyboard()


def screen_help():
    return tx.help_text(AUTO_SEARCH_ENABLED), back_keyboard()


def screen_favorites(uid: int):
    names = [r["username"] for r in list_favorites(uid)]
    rows = [[btn(f"❌ @{n}", f"unfav:{n}")] for n in names[:10]]
    rows.append([btn("⬅️ В меню", "menu")])
    return tx.favorites(names), InlineKeyboardMarkup(inline_keyboard=rows)


def screen_tracker(uid: int):
    names = [r["username"] for r in list_tracked(uid)]
    rows = [[btn(f"❌ @{n}", f"untrack:{n}")] for n in names[:10]]
    rows.append([btn("⬅️ В меню", "menu")])
    live = AUTO_SEARCH_ENABLED
    return tx.tracker(names, live, TRACK_INTERVAL // 60), InlineKeyboardMarkup(inline_keyboard=rows)


# ───────────── MTProto, автопоиск, трекер ─────────────

async def setup_mtproto():
    global telethon_client, AUTO_SEARCH_ENABLED
    if not API_ID or not API_HASH:
        log.warning("API_ID/API_HASH не настроены; live-поиск выключен")
        return
    try:
        from telethon import TelegramClient
        telethon_client = TelegramClient(TELETHON_SESSION, int(API_ID), API_HASH, flood_sleep_threshold=0)
        await telethon_client.start()
        AUTO_SEARCH_ENABLED = True
        log.info("MTProto-аккаунт подключён")
    except ImportError: log.warning("Установи Telethon: pip install telethon")
    except Exception: log.exception("Не удалось подключить MTProto")


def candidate_names(length: int, count=12):
    roots = ["nova", "luma", "vibe", "mono", "rare", "mint", "echo", "zen", "flux", "nexo", "aero", "byte", "kira", "mira"]
    found = set()
    while len(found) < count:
        if length <= 5:
            candidate = "".join(random.choices(string.ascii_lowercase, k=length))
        else:
            root = random.choice(roots)
            candidate = (root[:length] if len(root) >= length else root + "".join(random.choices(string.ascii_lowercase, k=length-len(root))))
        found.add(candidate)
    return list(found)


async def automatic_search(length: int) -> Optional[str]:
    if not AUTO_SEARCH_ENABLED or telethon_client is None or length < 5:
        return None
    from telethon import functions, errors
    for candidate in candidate_names(length):
        try:
            if await telethon_client(functions.account.CheckUsernameRequest(username=candidate)):
                return candidate
        except errors.FloodWaitError as exc:
            log.warning("Telegram FloodWait %s sec; прекращаю текущий поиск", exc.seconds)
            # Respect Telegram's limit; do not hold a paid request open for hours.
            raise RuntimeError(f"Telegram ограничил частоту проверок на {exc.seconds} сек.")
        except errors.RPCError as exc:
            if getattr(exc, "message", "") not in {"USERNAME_OCCUPIED", "USERNAME_INVALID", "USERNAME_PURCHASE_AVAILABLE", "BAD_REQUEST"}:
                log.warning("Telegram RPC для @%s: %s", candidate, exc)
        await asyncio.sleep(0.8)
    return None


async def check_tracked_once():
    """Проверяет отслеживаемые имена (от 5 символов) и пишет, когда имя освободилось."""
    from telethon import functions, errors
    with connect_db() as db:
        names = [r["username"] for r in db.execute(
            "SELECT DISTINCT username FROM tracked WHERE length(username)>=5 LIMIT 60")]
    for name in names:
        try:
            free = await telethon_client(functions.account.CheckUsernameRequest(username=name))
        except errors.FloodWaitError as exc:
            log.warning("Трекер: FloodWait %s сек., останавливаю проверку до следующего цикла", exc.seconds)
            return
        except errors.RPCError:
            free = False
        if free:
            with connect_db() as db:
                users = [r["user_id"] for r in db.execute("SELECT user_id FROM tracked WHERE username=?", (name,))]
                db.execute("DELETE FROM tracked WHERE username=?", (name,))
            for user_id in users:
                try:
                    i18n.set_lang(get_lang(user_id))
                    kb = InlineKeyboardMarkup(inline_keyboard=[[btn("❤️ В избранное", f"favorite:{name}")], [btn("⬅️ В меню", "menu")]])
                    await bot.send_message(user_id, tx.tracker_alert(name), parse_mode="HTML", reply_markup=kb)
                except Exception:
                    log.exception("Не удалось отправить уведомление трекера %s", user_id)
        await asyncio.sleep(1.5)


async def tracker_loop():
    await asyncio.sleep(30)
    while True:
        try:
            if AUTO_SEARCH_ENABLED and telethon_client is not None:
                await check_tracked_once()
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("Ошибка трекера")
        await asyncio.sleep(max(60, TRACK_INTERVAL))


# ───────────── Автопроверка крипто-платежей ─────────────

async def auto_confirm(order_id: int, txid: str, note: str) -> bool:
    status, row = confirm_crypto_order(order_id, txid)
    if status != "ok":
        return False
    log.info("Заказ #%s подтверждён автоматически (%s) %s", order_id, note, txid)
    try:
        i18n.set_lang(get_lang(row["user_id"]))
        await bot.send_message(row["user_id"], tx.payment_confirmed(order_id, row["credit_amount"]), parse_mode="HTML")
    except Exception:
        log.exception("Не удалось написать пользователю %s", row["user_id"])
    await notify_admins(f"✅ Заказ #{order_id} подтверждён автоматически ({note})\nПользователь: {row['user_id']}\nTX: {txid}")
    return True


async def check_tron(session):
    """USDT TRC20: ищем входящий перевод на наш адрес с точной суммой заказа."""
    orders = pending_orders_asset("USDT")
    if not orders or not TRON_USDT_ADDRESS:
        return
    oldest = min(order_created_ts(o) for o in orders)
    params = {"only_to": "true", "only_confirmed": "true", "limit": "200",
              "contract_address": USDT_CONTRACT, "min_timestamp": str(int((oldest - 300) * 1000))}
    headers = {"TRON-PRO-API-KEY": TRONGRID_API_KEY} if TRONGRID_API_KEY else {}
    url = f"https://api.trongrid.io/v1/accounts/{TRON_USDT_ADDRESS}/transactions/trc20"
    async with session.get(url, params=params, headers=headers) as resp:
        if resp.status != 200:
            log.warning("TronGrid ответил %s", resp.status)
            return
        data = await resp.json()
    by_amount: dict[int, list] = {}
    for o in orders:
        by_amount.setdefault(int(round(float(o["pay_amount"]) * 1_000_000)), []).append(o)
    for t in data.get("data", []):
        if t.get("to") != TRON_USDT_ADDRESS:
            continue
        info = t.get("token_info") or {}
        if info.get("address") and info["address"] != USDT_CONTRACT:
            continue
        try:
            micro = int(t["value"]) * 1_000_000 // 10 ** int(info.get("decimals", 6))
        except (KeyError, ValueError, TypeError):
            continue
        matches = by_amount.get(micro) or []
        if len(matches) != 1:  # нет заказа или сумма не уникальна: пусть подтвердит админ вручную
            continue
        order = matches[0]
        txid = t.get("transaction_id")
        if not txid or txid_used(txid):
            continue
        if float(t.get("block_timestamp", 0)) / 1000 < order_created_ts(order) - 60:
            continue
        await auto_confirm(order["id"], txid, "USDT TRC20")


async def check_ton(session):
    """GRAM (TON): ищем входящий перевод с комментарием FT<номер заказа>.
    Без GRAM_JETTON_MASTER это основная монета сети, с ним, перевод токена-джеттона."""
    orders = pending_orders_asset("GRAM")
    if not orders or not TON_GRAM_ADDRESS:
        return
    native = not GRAM_JETTON_MASTER
    kind = "TonTransfer" if native else "JettonTransfer"
    headers = {"Authorization": f"Bearer {TONAPI_KEY}"} if TONAPI_KEY else {}
    if native:
        url = f"https://tonapi.io/v2/accounts/{TON_GRAM_ADDRESS}/events"
    else:
        url = f"https://tonapi.io/v2/accounts/{TON_GRAM_ADDRESS}/jettons/{GRAM_JETTON_MASTER}/history"
    async with session.get(url, params={"limit": "50"}, headers=headers) as resp:
        if resp.status != 200:
            log.warning("TonAPI ответил %s", resp.status)
            return
        data = await resp.json()
    me = ton_raw(TON_GRAM_ADDRESS)
    by_comment = {f"ft{o['id']}": o for o in orders}
    for ev in data.get("events", []):
        if ev.get("in_progress"):
            continue
        txid = ev.get("event_id")
        for action in ev.get("actions", []):
            tr = action.get(kind)
            if action.get("type") != kind or not tr or action.get("status") != "ok":
                continue
            if ton_raw((tr.get("recipient") or {}).get("address", "")) != me:
                continue
            order = by_comment.get((tr.get("comment") or "").strip().lower())
            if not order or not txid or txid_used(txid):
                continue
            try:
                decimals = 9 if native else int((tr.get("jetton") or {}).get("decimals", 9))
                amount = int(tr.get("amount", 0)) / 10 ** decimals
            except (ValueError, TypeError):
                continue
            if float(ev.get("timestamp", 0)) < order_created_ts(order) - 60:
                continue
            if amount < float(order["pay_amount"]) * 0.99:
                log.warning("Заказ #%s: пришло %s GRAM, ожидалось %s", order["id"], amount, order["pay_amount"])
                continue
            await auto_confirm(order["id"], txid, "GRAM TON")


async def fetch_gram_usd(session) -> Optional[float]:
    """Рыночная цена 1 GRAM в долларах: сначала TonAPI, запасной источник DexScreener (джеттон) или CoinGecko (основная монета)."""
    token = GRAM_JETTON_MASTER or "ton"
    try:
        headers = {"Authorization": f"Bearer {TONAPI_KEY}"} if TONAPI_KEY else {}
        async with session.get("https://tonapi.io/v2/rates", params={"tokens": token, "currencies": "usd"},
                               headers=headers) as resp:
            if resp.status == 200:
                for v in ((await resp.json()).get("rates") or {}).values():
                    price = (v.get("prices") or {}).get("USD")
                    if price and float(price) > 0:
                        return float(price)
    except Exception as exc:
        log.debug("TonAPI rates: %s", exc)
    if not GRAM_JETTON_MASTER:
        try:
            async with session.get("https://api.coingecko.com/api/v3/simple/price",
                                   params={"ids": "the-open-network", "vs_currencies": "usd"}) as resp:
                if resp.status == 200:
                    price = ((await resp.json()).get("the-open-network") or {}).get("usd")
                    if price and float(price) > 0:
                        return float(price)
        except Exception as exc:
            log.debug("CoinGecko: %s", exc)
        return None
    try:
        async with session.get(f"https://api.dexscreener.com/latest/dex/tokens/{GRAM_JETTON_MASTER}") as resp:
            if resp.status == 200:
                pairs = [p for p in ((await resp.json()).get("pairs") or [])
                         if p.get("chainId") == "ton" and p.get("priceUsd")]
                pairs.sort(key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0), reverse=True)
                if pairs and float(pairs[0]["priceUsd"]) > 0:
                    return float(pairs[0]["priceUsd"])
    except Exception as exc:
        log.debug("DexScreener: %s", exc)
    return None


async def gram_rate_loop():
    """Раз в GRAM_RATE_REFRESH секунд обновляет GRAM_PER_USD по рыночной цене."""
    global GRAM_PER_USD
    if not GRAM_RATE_AUTO:
        return
    warned = None
    await asyncio.sleep(5)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        while True:
            try:
                price = await fetch_gram_usd(session)
                if price:
                    new = round(1 / price, 6)
                    old = GRAM_PER_USD
                    # Защита от неверных данных: резкий скачок больше 30% не применяем, а сообщаем админу.
                    if old > 0 and abs(new - old) / old > 0.30:
                        if warned != new:
                            warned = new
                            await notify_admins(f"⚠️ Курс GRAM изменился больше чем на 30%: было {old:g}, "
                                                f"рынок показывает {new:g} GRAM за $1 (цена ${price:g}). "
                                                "Автоматически не применяю. Если это верно, задай: /gramrate " + f"{new:g}")
                    else:
                        if old != new: log.info("Курс GRAM обновлён: %s → %s за $1 (цена $%s)", old, new, price)
                        GRAM_PER_USD = new
                else:
                    log.warning("Не удалось получить цену GRAM; остаётся курс %s", GRAM_PER_USD)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("Ошибка обновления курса GRAM")
            await asyncio.sleep(GRAM_RATE_REFRESH)


async def crypto_loop():
    if not AUTO_CRYPTO:
        log.info("Автопроверка крипто-платежей выключена (AUTO_CRYPTO=0)")
        return
    await asyncio.sleep(15)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as session:
        while True:
            try: expire_old_crypto_orders()
            except Exception: log.exception("Ошибка очистки старых заказов")
            for check in (check_tron, check_ton):
                try:
                    await check(session)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    log.exception("Ошибка автопроверки платежей (%s)", check.__name__)
            await asyncio.sleep(CRYPTO_POLL)


# ───────────── Команды ─────────────

@dp.message(Command("start"))
async def start(message: Message):
    uid = message.from_user.id
    ensure_user(uid)
    USER_STATES.pop(uid, None)
    if get_lang(uid) is None:
        return await message.answer(LANGUAGE_PROMPT, reply_markup=language_keyboard(), parse_mode="HTML")
    await show_main_menu(uid, message.from_user.first_name)


@dp.message(Command("lang"))
async def lang_command(message: Message):
    """Сменить язык в любой момент."""
    await message.answer(LANGUAGE_PROMPT, reply_markup=language_keyboard(), parse_mode="HTML")


@dp.callback_query(F.data.startswith("lang:"))
async def lang_cb(c: CallbackQuery):
    await safe_callback_answer(c)
    lang = c.data.split(":", 1)[1]
    if lang not in ("ru", "en"): return
    first_time = get_lang(c.from_user.id) is None
    set_lang(c.from_user.id, lang)
    i18n.set_lang(lang)
    await delete_callback_message(c)
    if first_time:
        await show_main_menu(c.from_user.id, c.from_user.first_name)
    else:
        await bot.send_message(c.from_user.id, "✅ Язык изменён." if lang == "ru" else "✅ Language changed.",
                               reply_markup=main_keyboard())


@dp.message(Command("admin"))
async def admin(message: Message):
    if message.from_user.id not in ADMIN_IDS: return await message.answer("⛔ Нет доступа.")
    await message.answer(tx.admin_panel(), reply_markup=admin_keyboard(), parse_mode="HTML")


@dp.message(Command("delname"))
async def delname(message: Message):
    if message.from_user.id not in ADMIN_IDS: return await message.answer("⛔ Нет доступа.")
    parts = (message.text or "").split()[1:]
    if not parts: return await message.answer("Формат: /delname username [username2 ...]")
    count = delete_usernames(parts)
    await message.answer(f"🗑 Удалено из базы: {count} из {len(parts)}.")


@dp.message(Command("addname"))
async def addname_cmd(message: Message):
    if message.from_user.id not in ADMIN_IDS: return await message.answer("⛔ Нет доступа.")
    parts = (message.text or "").split()[1:]
    if not parts: return await message.answer("Формат: /addname username [username2 ...]")
    added = skipped = 0
    for raw in parts:
        try: add_username(raw, "database", 0, message.from_user.id); added += 1
        except ValueError: skipped += 1
    await message.answer(f"✅ Добавлено в базу: {added}. Пропущено: {skipped}.")


@dp.message(Command("give"))
async def give_attempts_command(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Нет доступа.")
    parts = (message.text or "").split()
    if len(parts) != 4 or not parts[1].isdigit() or parts[2] not in ("4", "5", "678") or not parts[3].isdigit() or int(parts[3]) < 1:
        return await message.answer("Формат: /give user_id 4|5|678 количество")
    target, length, amount = int(parts[1]), int(parts[2]), int(parts[3])
    credit_attempts(target, amount, length=length)
    await message.answer(f"✅ Начислено {amount} попыток длины {length} пользователю {target}.")


@dp.message(Command("gramrate"))
async def gramrate_command(message: Message):
    """Обновляет курс GRAM (сколько GRAM за 1 USD) до перезапуска бота."""
    global GRAM_PER_USD
    if message.from_user.id not in ADMIN_IDS:
        return await message.answer("⛔ Нет доступа.")
    parts = (message.text or "").split()
    if len(parts) != 2:
        return await message.answer(f"Формат: /gramrate 123.45 (сколько GRAM за 1 USD)\nСейчас: {GRAM_PER_USD:g}")
    try:
        rate = float(parts[1].replace(",", "."))
        if rate <= 0: raise ValueError
    except ValueError:
        return await message.answer("Курс должен быть положительным числом.")
    GRAM_PER_USD = rate
    if GRAM_RATE_AUTO:
        await message.answer(f"ℹ️ Включено автообновление курса: это значение заменится рыночным в течение {GRAM_RATE_REFRESH // 60} мин. "
                             "Чтобы курс всегда был ручным, поставь GRAM_RATE_AUTO=0 в .env.")
    note = "" if TON_GRAM_ADDRESS else "\n⚠️ TON_GRAM_ADDRESS не задан в .env, оплата GRAM пока выключена."
    await message.answer(f"✅ Курс GRAM: {rate:g} за 1 USD. Действует до перезапуска; для постоянного значения впиши GRAM_PER_USD в .env.{note}")


@dp.message(F.document)
async def import_txt(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    doc = message.document
    if not doc.file_name or not doc.file_name.lower().endswith(".txt"):
        return await message.answer("Пришли TXT-файл: один username на строку.")
    file = await bot.get_file(doc.file_id)
    buf = BytesIO()
    await bot.download_file(file.file_path, buf)
    lines = buf.getvalue().decode("utf-8-sig", errors="ignore").splitlines()
    added = skipped = 0
    for line in lines:
        raw = line.strip().split()[0] if line.strip() else ""
        if not raw: continue
        try:
            add_username(raw, "database", 0, message.from_user.id); added += 1
        except ValueError: skipped += 1
    await message.answer(f"📥 Импорт завершён. Добавлено/обновлено: {added}. Пропущено: {skipped}.")


def name_info(name: str):
    score, liquidity = username_score(name)
    return {"name": name, "score": score, "liq": liquidity, "price": price_text(name)}


def _admin_sent_custom_emoji(message: Message) -> bool:
    return bool(message.from_user and message.from_user.id in ADMIN_IDS and
                any(e.type == "custom_emoji" for e in (message.entities or [])))


@dp.message(_admin_sent_custom_emoji)
async def custom_emoji_ids(message: Message):
    """Админ присылает анимированные эмодзи — бот отвечает их ID для emoji_ids.py."""
    lines, seen = [], set()
    for e in message.entities:
        if e.type != "custom_emoji" or e.custom_emoji_id in seen: continue
        seen.add(e.custom_emoji_id)
        lines.append(f'"{e.extract_from(message.text)}": "{e.custom_emoji_id}",')
    await message.answer("ID анимированных эмодзи (вставь в emoji_ids.py):\n\n<code>" + "\n".join(lines) + "</code>",
                         parse_mode="HTML")


@dp.message(F.text)
async def text_router(message: Message):
    uid = message.from_user.id
    state = USER_STATES.pop(uid, None)
    if not state: return
    if state == "rate":
        try: name = clean_username(message.text)
        except ValueError as e: USER_STATES[uid] = "rate"; return await message.answer(str(e))
        info = name_info(name)
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [btn("❤️ В избранное", f"favorite:{name}"), btn("📡 Отслеживать", f"track:{name}")],
            [btn("⚖️ Сравнить", "compare"), btn("⬅️ В меню", "menu")]])
        await message.answer(tx.rate_card(name, info["score"], info["liq"], info["price"], username_traits(name)),
                             parse_mode="HTML", reply_markup=kb)
    elif state == "compare":
        names = re.findall(r"@?[a-zA-Z0-9_]+", message.text)
        if len(names) < 2:
            USER_STATES[uid] = "compare"; return await message.answer("Отправь два юзернейма через пробел, например: @uvofit @hyvoq")
        try: a, b = clean_username(names[0]), clean_username(names[1])
        except ValueError as e:
            USER_STATES[uid] = "compare"; return await message.answer(str(e))
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [btn("⚖️ Сравнить ещё", "compare"), btn("⬅️ В меню", "menu")]])
        await message.answer(tx.compare_card(name_info(a), name_info(b)), parse_mode="HTML", reply_markup=kb)
    elif state == "admin_add":
        if uid not in ADMIN_IDS: return
        added = skipped = 0
        for raw in message.text.split():
            try: add_username(raw, "database", 0, uid); added += 1
            except ValueError: skipped += 1
        if not added: USER_STATES[uid] = "admin_add"
        await message.answer(f"✅ Добавлено: {added}. Пропущено: {skipped}." if added
                             else "Не нашёл ни одного подходящего юзернейма. Допустимы латиница, цифры и _, длина 4–32.")
    elif state == "admin_grant":
        if uid not in ADMIN_IDS: return
        parts = message.text.split()
        if len(parts) != 3 or not parts[0].isdigit() or parts[1] not in ("4", "5", "678") or not parts[2].isdigit() or int(parts[2]) < 1:
            USER_STATES[uid] = "admin_grant"; return await message.answer("Формат: user_id 4|5|678 количество")
        target, length, amount = int(parts[0]), int(parts[1]) if parts[1].isdigit() else 0, int(parts[2])
        credit_attempts(target, amount, length=length)
        await message.answer(f"✅ Начислено {amount} попыток длины {length} пользователю {target}.")
    elif state == "admin_delete":
        if uid not in ADMIN_IDS: return
        count = delete_usernames(message.text.split())
        await message.answer(f"🗑 Удалено юзернеймов: {count}.")


@dp.message(F.web_app_data)
async def handle_mini_app_data(message: Message):
    try: action = str(json.loads(message.web_app_data.data).get("action", ""))
    except Exception: return await message.answer("Не удалось прочитать действие Mini App.", reply_markup=main_keyboard())
    uid = message.from_user.id
    if action in ("rate", "compare"):
        USER_STATES[uid] = action
        return await message.answer(tx.rate_prompt() if action == "rate" else tx.compare_prompt(),
                                    parse_mode="HTML", reply_markup=back_keyboard())
    if action == "admin":
        if uid not in ADMIN_IDS: return await message.answer("⛔ Нет доступа.", reply_markup=main_keyboard())
        return await message.answer(tx.admin_panel(), reply_markup=admin_keyboard(), parse_mode="HTML")
    screens = {
        "search": lambda: screen_search(uid),
        "profile": lambda: screen_profile(uid),
        "tracker": lambda: screen_tracker(uid),
        "favorites": lambda: screen_favorites(uid),
        "tariffs": screen_tariffs,
        "help": screen_help,
    }
    if action in screens:
        text, kb = screens[action]()
        return await message.answer(text, reply_markup=kb, parse_mode="HTML")
    await message.answer("Выбери раздел в Mini App.", reply_markup=main_keyboard())


# ───────────── Навигация и поиск ─────────────

@dp.callback_query(F.data == "menu")
async def menu(c: CallbackQuery):
    await safe_callback_answer(c); text, kb = screen_menu(); await edit(c, text, kb, banner="menu")


@dp.callback_query(F.data == "search")
async def search(c: CallbackQuery):
    await safe_callback_answer(c); text, kb = screen_search(c.from_user.id); await edit(c, text, kb, banner="search")


@dp.callback_query(F.data == "lengths")
async def lengths(c: CallbackQuery):
    await safe_callback_answer(c); await edit(c, tx.lengths(), lengths_keyboard(c.from_user.id))


@dp.callback_query(F.data.startswith("length:"))
async def set_length(c: CallbackQuery):
    await safe_callback_answer(c)
    try: n = int(c.data.split(":", 1)[1])
    except ValueError: return
    if n not in (4, 5, 6, 7, 8, MIX_STD, MIX_PREM): return
    if n in (4, 5) and balance_for(c.from_user.id, n) <= 0:
        # Нет попыток на Premium-длине — предлагаем купить.
        return await edit(c, tx.premium_offer(n), premium_offer_keyboard(n))
    if n == MIX_PREM and selection_balance(c.from_user.id, n) <= 0:
        return await edit(c, tx.premium_offer(None), premium_offer_keyboard(None))
    SEARCH_LENGTH[c.from_user.id] = n
    text, kb = screen_length(c.from_user.id, n)
    await edit(c, text, kb)


@dp.callback_query(F.data == "search_db")
async def search_db(c: CallbackQuery):
    await safe_callback_answer(c)
    uid = c.from_user.id; n = pick_length(uid)
    if n is None:
        return await edit(c, tx.premium_offer(None), premium_offer_keyboard(None))
    if not spend_attempt(uid, n):
        return await edit(c, tx.no_attempts(n, refill_in_text(uid)), buy_keyboard(n))
    if n in HIT_CHANCE and random.random() >= HIT_CHANCE[n]:
        return await edit(c, tx.premium_miss(n, tx.HIT_CHANCE[n]), search_keyboard(uid))
    seen = [i["name"] for i in USER_HISTORY.get(uid, {}).get("items", [])]
    row = get_random_username(n, seen)
    if not row:
        # Paid/free attempt is consumed: the package never guarantees a result.
        return await edit(c, tx.db_empty(n), search_keyboard(uid))
    push_history(uid, row["username"], row["price_stars"], "database")
    text, kb = screen_username(uid)
    await edit(c, text, kb, banner="card")


async def send_db_name(uid: int, n: int) -> bool:
    """Отправляет пользователю случайное имя из базы (без повторов из его истории). False, если в базе пусто."""
    seen = [i["name"] for i in USER_HISTORY.get(uid, {}).get("items", [])]
    row = get_random_username(n, seen)
    if not row:
        return False
    push_history(uid, row["username"], row["price_stars"], "database")
    text, kb = screen_username(uid)
    await bot.send_message(uid, text, reply_markup=kb, parse_mode="HTML")
    return True


@dp.callback_query(F.data == "search_auto")
async def search_auto(c: CallbackQuery):
    # Автопоиск отключён: имена выдаются только из твоей базы (загруженной файлом).
    return await search_db(c)


async def _search_auto_legacy(c: CallbackQuery):
    await safe_callback_answer(c)
    uid = c.from_user.id; n = pick_length(uid)
    if n is None:
        return await edit(c, tx.premium_offer(None), premium_offer_keyboard(None))
    if n == 4:
        return await edit(c, tx.auto_4_unavailable(), search_back_keyboard())
    telegram_ready = AUTO_SEARCH_ENABLED and telethon_client is not None
    if AUTO_SOURCE != "db" and not telegram_ready:
        return await edit(c, tx.auto_off(), search_back_keyboard())
    if not spend_attempt(uid, n):
        return await edit(c, tx.no_attempts(n, refill_in_text(uid)), buy_keyboard(n))
    await delete_callback_message(c)
    if n in HIT_CHANCE and random.random() >= HIT_CHANCE[n]:
        return await bot.send_message(uid, tx.premium_miss(n, tx.HIT_CHANCE[n]), reply_markup=search_keyboard(uid), parse_mode="HTML")
    if AUTO_SOURCE == "db":
        # Сначала берём имя из базы: Telegram и его лимиты не нужны.
        if await send_db_name(uid, n): return
        if not telegram_ready:
            return await bot.send_message(uid, tx.db_empty(n), reply_markup=search_keyboard(uid), parse_mode="HTML")
    status = await bot.send_message(uid, tx.auto_scanning(n), parse_mode="HTML")
    try:
        started = asyncio.get_running_loop().time()
        name = await automatic_search(n)
        delay = random.randint(6, 10) - (asyncio.get_running_loop().time() - started)
        if delay > 0: await asyncio.sleep(delay)
        try: await status.delete()
        except Exception: pass
        if not name:
            if await send_db_name(uid, n): return  # Telegram ничего не нашёл: выдаём из базы
            return await bot.send_message(uid, tx.auto_not_found(n), reply_markup=search_keyboard(uid), parse_mode="HTML")
        # Кладём в базу уже как shown — другим это имя больше не выдаётся.
        add_username(name, "auto", 0, 0)
        claim_username(name)
        push_history(uid, name, 0, "auto")
        text, kb = screen_username(uid)
        await bot.send_message(uid, text, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        try: await status.delete()
        except Exception: pass
        log.exception("Ошибка автопоиска")
        try:
            if await send_db_name(uid, n): return  # Telegram ограничил проверки: выдаём из базы
        except Exception:
            log.exception("Не удалось выдать имя из базы")
        credit_attempts(uid, 1, length=n)
        await bot.send_message(uid, tx.auto_error(e), reply_markup=search_keyboard(uid), parse_mode="HTML")


@dp.callback_query(F.data == "name_prev")
async def name_prev(c: CallbackQuery):
    uid = c.from_user.id
    h = USER_HISTORY.get(uid)
    if not h or h["idx"] <= 0:
        return await safe_callback_answer(c, "Это первое имя в истории")
    await safe_callback_answer(c)
    h["idx"] -= 1
    text, kb = screen_username(uid)
    await edit(c, text, kb, banner="card")


@dp.callback_query(F.data == "name_next")
async def name_next(c: CallbackQuery):
    uid = c.from_user.id
    h = USER_HISTORY.get(uid)
    if h and h["idx"] < len(h["items"]) - 1:  # уже найденное имя: бесплатно
        await safe_callback_answer(c)
        h["idx"] += 1
        text, kb = screen_username(uid)
        return await edit(c, text, kb, banner="card")
    # Конец истории: ищем новое имя тем же способом и той же длины (спишется попытка).
    source = "database"
    if h and h["items"]:
        item = h["items"][h["idx"]]
        source = item["source"]
        if len(item["name"]) in (4, 5, 6, 7, 8) and SEARCH_LENGTH.get(uid) not in (MIX_STD, MIX_PREM):
            SEARCH_LENGTH[uid] = len(item["name"])
    await search_db(c)



# ───────────── Имя оказалось занятым: жалоба → админ → замена ─────────────

REPORT_LIMIT_PER_DAY = 5  # защита от спама жалобами


def name_status(name: str) -> Optional[str]:
    with connect_db() as db:
        row = db.execute("SELECT status FROM usernames WHERE username=?", (name,)).fetchone()
    return row["status"] if row else None


@dp.callback_query(F.data.startswith("taken:"))
async def name_taken(c: CallbackQuery):
    uid = c.from_user.id
    name = safe_name(c.data.split(":", 1)[1])
    if not name:
        return await safe_callback_answer(c)
    since = (datetime.now(timezone.utc) - timedelta(days=1)).isoformat()
    with connect_db() as db:
        dup = db.execute("SELECT 1 FROM name_reports WHERE user_id=? AND username=?", (uid, name)).fetchone()
        recent = db.execute("SELECT COUNT(*) c FROM name_reports WHERE user_id=? AND created_at>?", (uid, since)).fetchone()["c"]
    if dup:
        return await safe_callback_answer(c, "Ты уже сообщал об этом имени — жди замену.")
    if recent >= REPORT_LIMIT_PER_DAY:
        return await safe_callback_answer(c, "Сегодня лимит жалоб исчерпан. Попробуй завтра.")
    if name_status(name) != "shown":  # жалоба только на имя, которое бот реально выдавал
        return await safe_callback_answer(c, "Это имя уже недоступно для жалобы.")
    with connect_db() as db:
        cur = db.execute("INSERT INTO name_reports(user_id, username, created_at) VALUES(?,?,?)", (uid, name, now_iso()))
        report_id = cur.lastrowid
        db.execute("UPDATE usernames SET status='taken' WHERE username=?", (name,))  # больше никому не выдаётся
    await safe_callback_answer(c)
    await bot.send_message(uid, tx.taken_sent(name), parse_mode="HTML",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("⬅️ В меню", "menu")]]))
    who = f"@{c.from_user.username}" if c.from_user.username else "без @username"
    admin_text = (f"⚠️ <b>Имя занято</b>\n"
                  f"Пользователь: {html_escape(c.from_user.full_name)} ({who}), id <code>{uid}</code>\n"
                  f"Выпало: <code>@{name}</code> ({len(name)} симв.)\n"
                  f"Жалоба №{report_id}")
    kb = InlineKeyboardMarkup(inline_keyboard=[[btn("✅ Вернуть попытку", f"rep:{report_id}"), btn("❌ Отклонить", f"rej:{report_id}")]])
    for admin_id in ADMIN_IDS:
        try: await bot.send_message(admin_id, admin_text, parse_mode="HTML", reply_markup=kb)
        except Exception: log.exception("Не удалось отправить жалобу админу %s", admin_id)


def html_escape(value) -> str:
    import html
    return html.escape(str(value or ""))


def _pending_report(report_id: int):
    with connect_db() as db:
        return db.execute("SELECT * FROM name_reports WHERE id=? AND status='pending'", (report_id,)).fetchone()


@dp.callback_query(F.data.startswith("rep:"))
async def report_refund(c: CallbackQuery):
    """Админ подтвердил, что имя занято: человеку возвращается попытка на баланс."""
    if c.from_user.id not in ADMIN_IDS:
        return await safe_callback_answer(c)
    try: report_id = int(c.data.split(":", 1)[1])
    except ValueError: return await safe_callback_answer(c)
    rep = _pending_report(report_id)
    if not rep:
        return await safe_callback_answer(c, "Эта жалоба уже обработана.")
    user_id, old = rep["user_id"], rep["username"]
    # Меняем статус одним запросом: двойной клик не вернёт попытку дважды.
    with connect_db() as db:
        cur = db.execute("UPDATE name_reports SET status='refunded' WHERE id=? AND status='pending'", (report_id,))
        if cur.rowcount != 1:
            return await safe_callback_answer(c, "Эта жалоба уже обработана.")
    credit_attempts(user_id, 1, length=len(old))
    await safe_callback_answer(c, "Попытка возвращена")
    i18n.set_lang(get_lang(user_id))
    kb = InlineKeyboardMarkup(inline_keyboard=[[btn("🔍 Найти юзернейм", "search")], [btn("⬅️ В меню", "menu")]])
    delivered = True
    try:
        await bot.send_message(user_id, tx.taken_refunded(old, len(old)), parse_mode="HTML", reply_markup=kb)
    except Exception:
        delivered = False
        log.exception("Не удалось написать пользователю %s", user_id)
    try:
        note = "" if delivered else "\n⚠️ Пользователю не удалось написать (возможно, заблокировал бота), но попытка на баланс уже зачислена."
        await c.message.edit_text(f"✅ <b>Попытка возвращена</b>: <code>@{old}</code> ({len(old)} симв.)\n"
                                  f"Пользователь {user_id} получил +1 попытку на баланс.{note}", parse_mode="HTML")
    except Exception: pass


@dp.callback_query(F.data.startswith("rej:"))
async def report_reject(c: CallbackQuery):
    if c.from_user.id not in ADMIN_IDS:
        return await safe_callback_answer(c)
    try: report_id = int(c.data.split(":", 1)[1])
    except ValueError: return await safe_callback_answer(c)
    rep = _pending_report(report_id)
    if not rep:
        return await safe_callback_answer(c, "Эта жалоба уже обработана.")
    with connect_db() as db:
        db.execute("UPDATE name_reports SET status='rejected' WHERE id=?", (report_id,))
    await safe_callback_answer(c, "Отклонено")
    i18n.set_lang(get_lang(rep["user_id"]))
    try: await bot.send_message(rep["user_id"], tx.taken_rejected(rep["username"]), parse_mode="HTML")
    except Exception: pass
    try: await c.message.edit_text(f"❌ Жалоба №{report_id} отклонена (@{rep['username']}).")
    except Exception: pass


# ───────────── Баннеры: админ присылает фото с подписью /banner <экран> ─────────────

def banners_help() -> str:
    lines = []
    for key, title in BANNER_SCREENS.items():
        mark = "✅" if get_setting(f"banner:{key}") or (key == "menu" and banner_photo("menu")) else "▫️"
        lines.append(f"{mark} <code>{key}</code> — {title}")
    return "\n".join(lines)


@dp.message(F.photo)
async def set_banner(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = (message.caption or "").strip().lower().split()
    if not parts or parts[0] != "/banner": return
    key = parts[1] if len(parts) > 1 else "menu"
    if key not in BANNER_SCREENS:
        return await message.answer("Не знаю такого экрана. Доступные:\n\n" + banners_help() +
                                    "\n\nПришли фото с подписью, например: <code>/banner tariffs</code>", parse_mode="HTML")
    set_setting(f"banner:{key}", message.photo[-1].file_id)
    await message.answer(f"✅ Баннер для экрана <code>{key}</code> сохранён.\nУбрать: <code>/nobanner {key}</code>", parse_mode="HTML")


@dp.message(Command("banners"))
async def banners_list(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    await message.answer("🖼 <b>Баннеры по экранам</b> (✅ — задан)\n\n" + banners_help() +
                         "\n\nЗадать: фото с подписью <code>/banner экран</code>\n"
                         "Убрать: <code>/nobanner экран</code> или <code>/nobanner all</code>", parse_mode="HTML")


@dp.message(Command("nobanner"))
async def clear_banner(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    parts = (message.text or "").split()
    key = parts[1].lower() if len(parts) > 1 else "menu"
    with connect_db() as db:
        if key == "all":
            db.execute("DELETE FROM settings WHERE key LIKE 'banner:%' OR key='banner_file_id'")
            return await message.answer("🗑 Все баннеры убраны.")
        if key not in BANNER_SCREENS:
            return await message.answer("Не знаю такого экрана. Список: /banners")
        db.execute("DELETE FROM settings WHERE key=?", (f"banner:{key}",))
        if key == "menu":
            db.execute("DELETE FROM settings WHERE key='banner_file_id'")
    note = "\nФайл banner.jpg рядом с main.py тоже уберите, иначе он подставится снова." if key == "menu" and os.path.exists(BANNER_FILE) else ""
    await message.answer(f"🗑 Баннер для экрана <code>{key}</code> убран.{note}", parse_mode="HTML")


# ───────────── Магазин и оплата ─────────────

@dp.callback_query(F.data.startswith("premium_shop"))
async def premium_shop(c: CallbackQuery):
    await safe_callback_answer(c)
    try: length = int(c.data.split(":", 1)[1]) if ":" in c.data else 4
    except ValueError: length = 4
    if length not in (4, 5): length = 4
    packs = PREMIUM_PACKS_4 if length == 4 else PREMIUM_PACKS_5
    rows = [[btn(f"{count} попыток — ${usd:.2f}", f"prempay:{length}:{count}")] for count, usd in packs.items()]
    rows.append([btn("⬅️ Назад", f"length:{length}")])
    await edit(c, tx.premium_shop(length, gram_enabled()), InlineKeyboardMarkup(inline_keyboard=rows))


def parse_premium(data: str):
    try:
        _, length_text, count_text = data.split(":")
        length, count = int(length_text), int(count_text)
    except Exception:
        return None
    packs = PREMIUM_PACKS_4 if length == 4 else PREMIUM_PACKS_5 if length == 5 else {}
    usd = packs.get(count)
    return (length, count, usd) if usd else None


@dp.callback_query(F.data.startswith("prempay:"))
async def premium_pay(c: CallbackQuery):
    await safe_callback_answer(c)
    parsed = parse_premium(c.data)
    if not parsed: return await edit(c, "Пакет не настроен.", back_keyboard())
    length, count, usd = parsed
    await edit(c, tx.premium_pack_screen(length, count, usd, gram_amount(usd)), premium_pay_keyboard(length, count))


async def place_crypto_order(c: CallbackQuery, kind: str, credits: int, usd: float, asset: str, title: str):
    uid = c.from_user.id
    await delete_callback_message(c)
    if asset == "GRAM":
        pay = gram_amount(usd)
        order_id = create_crypto_order(uid, kind, credits, usd, "GRAM", pay)
        text = tx.order_gram(order_id, title, pay, usd, TON_GRAM_ADDRESS)
    else:
        pay = unique_usdt_amount(usd)
        order_id = create_crypto_order(uid, kind, credits, usd, "USDT", pay)
        text = tx.order_usdt(order_id, title, pay, TRON_USDT_ADDRESS)
    await bot.send_message(uid, text, parse_mode="HTML", reply_markup=order_keyboard())
    await notify_admins(f"💳 Новый крипто-заказ #{order_id}\nПользователь: {uid}\n{title}\nСумма: {pay:g} {asset} (≈ ${usd:.2f})")


@dp.callback_query(F.data.startswith("prembuy:"))
async def premium_buy(c: CallbackQuery):
    await safe_callback_answer(c)
    parsed = parse_premium(c.data)
    if not parsed: return await edit(c, "Пакет не настроен.", back_keyboard())
    length, count, usd = parsed
    title = (f"Pack: {count} attempts for {length}-char search" if i18n.current_lang() == "en"
             else f"Пакет: {count} попыток для поиска длиной {length}")
    await place_crypto_order(c, f"premium{length}", count, usd, "USDT", title)


@dp.callback_query(F.data.startswith("premgram:"))
async def premium_gram(c: CallbackQuery):
    await safe_callback_answer(c)
    parsed = parse_premium(c.data)
    if not parsed: return await edit(c, "Пакет не настроен.", back_keyboard())
    if not gram_enabled(): return await edit(c, tx.gram_off(), back_keyboard())
    length, count, usd = parsed
    title = (f"Pack: {count} attempts for {length}-char search" if i18n.current_lang() == "en"
             else f"Пакет: {count} попыток для поиска длиной {length}")
    await place_crypto_order(c, f"premium{length}", count, usd, "GRAM", title)


@dp.callback_query(F.data == "profile")
async def profile(c: CallbackQuery):
    await safe_callback_answer(c); text, kb = screen_profile(c.from_user.id); await edit(c, text, kb, banner="profile")


@dp.callback_query(F.data == "profile_lang")
async def profile_language(c: CallbackQuery):
    await safe_callback_answer(c)
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang:ru")],
        [InlineKeyboardButton(text="🇬🇧 English", callback_data="lang:en")],
        [btn("⬅️ Назад в профиль", "profile")],
    ])
    await edit(c, LANGUAGE_PROMPT, kb)


@dp.callback_query(F.data == "tariffs")
async def tariffs(c: CallbackQuery):
    await safe_callback_answer(c); text, kb = screen_tariffs(); await edit(c, text, kb, banner="tariffs")


@dp.callback_query(F.data.startswith("pack:"))
async def pack_screen(c: CallbackQuery):
    await safe_callback_answer(c)
    try: count = int(c.data.split(":")[1]); pack = STANDARD_PACKS.get(count)
    except Exception: return
    if not pack: return
    await edit(c, tx.pack_screen(count, pack["stars"], pack["usd"], gram_amount(pack["usd"])), pack_pay_keyboard(count))


@dp.callback_query(F.data == "gram_off")
async def gram_off(c: CallbackQuery):
    await safe_callback_answer(c, tx.gram_off())


@dp.callback_query(F.data.startswith("usdtbuy:"))
async def usdt_buy(c: CallbackQuery):
    await safe_callback_answer(c)
    try: count = int(c.data.split(":")[1]); pack = STANDARD_PACKS.get(count)
    except Exception: return
    if not pack or pack["usd"] <= 0: return await edit(c, "Цена этого USDT-пакета ещё не настроена в .env.", back_keyboard())
    title = (f"Pack: {count} standard attempts (shared 6/7/8 balance)" if i18n.current_lang() == "en"
             else f"Пакет: {count} обычных попыток (общий баланс 6/7/8)")
    await place_crypto_order(c, "standard", count, pack["usd"], "USDT", title)


@dp.callback_query(F.data.startswith("grambuy:"))
async def gram_buy(c: CallbackQuery):
    await safe_callback_answer(c)
    try: count = int(c.data.split(":")[1]); pack = STANDARD_PACKS.get(count)
    except Exception: return
    if not pack or pack["usd"] <= 0: return await edit(c, "Цена этого пакета ещё не настроена в .env.", back_keyboard())
    if not gram_enabled(): return await edit(c, tx.gram_off(), back_keyboard())
    title = (f"Pack: {count} standard attempts (shared 6/7/8 balance)" if i18n.current_lang() == "en"
             else f"Пакет: {count} обычных попыток (общий баланс 6/7/8)")
    await place_crypto_order(c, "standard", count, pack["usd"], "GRAM", title)


@dp.callback_query(F.data.startswith("starbuy:"))
async def star_buy(c: CallbackQuery):
    await safe_callback_answer(c)
    try: count = int(c.data.split(":")[1]); pack = STANDARD_PACKS.get(count)
    except Exception: return
    if not pack or pack["stars"] <= 0: return await edit(c, "Цена этого Stars-пакета ещё не настроена в .env.", back_keyboard())
    await delete_callback_message(c)
    if i18n.current_lang() == "en":
        inv_title, inv_desc, inv_label = f"FindTag — {count} attempts", f"{count} standard search attempts for shared 6/7/8 balance", f"{count} attempts"
    else:
        inv_title, inv_desc, inv_label = f"FindTag — {count} попыток", f"{count} обычных поисковых попыток для общего баланса 6/7/8", f"{count} попыток"
    await bot.send_invoice(chat_id=c.from_user.id, title=inv_title, description=inv_desc, payload=f"std:{c.from_user.id}:{count}:{pack['stars']}", currency="XTR", prices=[LabeledPrice(label=inv_label, amount=pack["stars"])])


# ───────────── Покупка имён, избранное, трекер ─────────────

@dp.callback_query(F.data.startswith("buy:"))
async def buy_username(c: CallbackQuery):
    name = c.data.split(":",1)[1]
    if not can_buy_name(name):
        return await safe_callback_answer(c, "Name purchase unavailable" if i18n.current_lang() == "en" else "Покупка имён недоступна")
    await safe_callback_answer(c); await delete_callback_message(c)
    with connect_db() as db: row = db.execute("SELECT * FROM usernames WHERE username=? AND status='available'", (name,)).fetchone()
    if not row:
        msg = "This name is no longer available." if i18n.current_lang() == "en" else "Это имя больше недоступно в базе."
        return await bot.send_message(c.from_user.id, msg, reply_markup=back_keyboard())
    if row["price_stars"] > 0:
        inv_title = f"Username @{name}"
        inv_desc = "Payment for username purchase request" if i18n.current_lang() == "en" else "Оплата заявки на приобретение юзернейма"
        await bot.send_invoice(chat_id=c.from_user.id, title=inv_title, description=inv_desc, payload=f"username:{c.from_user.id}:{name}:{row['price_stars']}", currency="XTR", prices=[LabeledPrice(label=f"@{name}", amount=int(row["price_stars"]))])
    else:
        oid = create_order(c.from_user.id, name, "purchase")
        await notify_admins(f"🛒 Заявка #{oid}\nПользователь: {c.from_user.id}\nЮзернейм: @{name}\nЦена не установлена.")
        if i18n.current_lang() == "en":
            user_msg = f"✅ <b>Request #{oid} submitted</b>\n\nAn admin will contact you about <code>@{name}</code>.\nCheck status in your profile."
        else:
            user_msg = f"✅ <b>Заявка #{oid} отправлена</b>\n\nАдминистратор свяжется с тобой по имени <code>@{name}</code>.\nСтатус заявки смотри в профиле."
        await bot.send_message(c.from_user.id, user_msg, parse_mode="HTML", reply_markup=order_keyboard())


@dp.callback_query(F.data.startswith("request:"))
async def request_name(c: CallbackQuery):
    name = c.data.split(":",1)[1]
    if not can_buy_name(name):
        return await safe_callback_answer(c, "Name requests unavailable" if i18n.current_lang() == "en" else "Заявки на имена недоступны")
    await safe_callback_answer(c); await delete_callback_message(c); oid = create_order(c.from_user.id, name, "manual")
    await notify_admins(f"📝 Заявка #{oid}\nПользователь: {c.from_user.id}\nЮзернейм: @{name}")
    if i18n.current_lang() == "en":
        user_msg = f"✅ <b>Request #{oid} submitted</b>\n\nWe received your request for <code>@{name}</code> and will reply soon.\nCheck status in your profile."
    else:
        user_msg = f"✅ <b>Заявка #{oid} отправлена</b>\n\nМы получили запрос по имени <code>@{name}</code> и скоро ответим.\nСтатус заявки смотри в профиле."
    await bot.send_message(c.from_user.id, user_msg, parse_mode="HTML", reply_markup=order_keyboard())


@dp.callback_query(F.data.startswith("favorite:"))
async def favorite(c: CallbackQuery):
    await safe_callback_answer(c); name = safe_name(c.data.split(":", 1)[1])
    if not name: return
    add_favorite(c.from_user.id, name)
    await edit(c, tx.favorite_added(name), InlineKeyboardMarkup(inline_keyboard=[[btn("❤️ Избранное", "favorites")], [btn("⬅️ В меню", "menu")]]))


@dp.callback_query(F.data.startswith("unfav:"))
async def unfavorite(c: CallbackQuery):
    await safe_callback_answer(c, "Убрано из избранного")
    name = safe_name(c.data.split(":", 1)[1])
    if name: remove_favorite(c.from_user.id, name)
    text, kb = screen_favorites(c.from_user.id); await edit(c, text, kb, banner="favorites")


@dp.callback_query(F.data == "favorites")
async def favorites(c: CallbackQuery):
    await safe_callback_answer(c); text, kb = screen_favorites(c.from_user.id); await edit(c, text, kb, banner="favorites")


@dp.callback_query(F.data.startswith("track:"))
async def track(c: CallbackQuery):
    await safe_callback_answer(c); await delete_callback_message(c); name = safe_name(c.data.split(":", 1)[1])
    if not name: return
    add_tracked(c.from_user.id, name)
    await bot.send_message(c.from_user.id, tx.tracker_added(name, AUTO_SEARCH_ENABLED, TRACK_INTERVAL // 60), parse_mode="HTML",
                           reply_markup=InlineKeyboardMarkup(inline_keyboard=[[btn("📡 Мой трекер", "tracker")], [btn("⬅️ В меню", "menu")]]))


@dp.callback_query(F.data.startswith("untrack:"))
async def untrack(c: CallbackQuery):
    await safe_callback_answer(c, "Убрано из трекера")
    name = safe_name(c.data.split(":", 1)[1])
    if name: remove_tracked(c.from_user.id, name)
    text, kb = screen_tracker(c.from_user.id); await edit(c, text, kb, banner="tracker")


@dp.callback_query(F.data == "tracker")
async def tracker(c: CallbackQuery):
    await safe_callback_answer(c); text, kb = screen_tracker(c.from_user.id); await edit(c, text, kb, banner="tracker")


@dp.callback_query(F.data == "rate")
async def rate(c: CallbackQuery):
    await safe_callback_answer(c); USER_STATES[c.from_user.id] = "rate"; await edit(c, tx.rate_prompt(), back_keyboard(), banner="rate")


@dp.callback_query(F.data == "compare")
async def compare(c: CallbackQuery):
    await safe_callback_answer(c); USER_STATES[c.from_user.id] = "compare"; await edit(c, tx.compare_prompt(), back_keyboard(), banner="compare")


@dp.callback_query(F.data == "help")
async def help_cb(c: CallbackQuery):
    await safe_callback_answer(c); text, kb = screen_help(); await edit(c, text, kb, banner="help")


# ───────────── Админ-панель ─────────────

@dp.callback_query(F.data == "admin")
async def admin_cb(c: CallbackQuery):
    await safe_callback_answer(c)
    if c.from_user.id not in ADMIN_IDS: return await edit(c, "⛔ Нет доступа.", back_keyboard())
    await edit(c, tx.admin_panel(), admin_keyboard())


@dp.callback_query(F.data == "admin_add")
async def admin_add(c: CallbackQuery):
    await safe_callback_answer(c)
    if c.from_user.id not in ADMIN_IDS: return await edit(c, "⛔ Нет доступа.", back_keyboard())
    USER_STATES[c.from_user.id] = "admin_add"
    await edit(c, "➕ <b>Добавить юзернейм</b>\n\nОтправь один или несколько юзернеймов через пробел или с новой строки.\nПример: <code>nova mira kira</code>\n\nМассовая загрузка: пришли TXT-файл, один username на строку.", admin_back_keyboard())


@dp.callback_query(F.data == "admin_grant")
async def admin_grant(c: CallbackQuery):
    await safe_callback_answer(c)
    if c.from_user.id not in ADMIN_IDS: return await edit(c, "⛔ Нет доступа.", back_keyboard())
    USER_STATES[c.from_user.id] = "admin_grant"
    await edit(c, "🎟 <b>Выдать попытки</b>\n\nОтправь: <code>user_id 4|5|678 количество</code>\nПример: <code>123456789 4 10</code>\n\n4 — баланс 4 символов, 5 — баланс 5 символов, 678 — общий баланс.", admin_back_keyboard())


@dp.callback_query(F.data == "admin_delete")
async def admin_delete(c: CallbackQuery):
    await safe_callback_answer(c)
    if c.from_user.id not in ADMIN_IDS: return await edit(c, "⛔ Нет доступа.", back_keyboard())
    USER_STATES[c.from_user.id] = "admin_delete"
    await edit(c, "🗑 <b>Удалить юзернеймы</b>\n\nОтправь один или несколько юзернеймов через пробел.", admin_back_keyboard())


@dp.callback_query(F.data == "admin_orders")
async def admin_orders(c: CallbackQuery):
    await safe_callback_answer(c)
    if c.from_user.id not in ADMIN_IDS: return await edit(c, "⛔ Нет доступа.", back_keyboard())
    with connect_db() as db: rows = db.execute("SELECT * FROM orders ORDER BY id DESC LIMIT 10").fetchall()
    if not rows: return await edit(c, "📋 <b>Заявки</b>\n\nЗаявок пока нет.", admin_back_keyboard())
    await edit(c, "📋 <b>Последние заявки</b>\n\n" + "\n".join(f"#{r['id']} @{r['username']} | user <code>{r['user_id']}</code> | {r['kind']} | {r['status']}" for r in rows), admin_back_keyboard())


@dp.callback_query(F.data == "admin_crypto")
async def admin_crypto(c: CallbackQuery):
    await safe_callback_answer(c)
    if c.from_user.id not in ADMIN_IDS: return await edit(c, "⛔ Нет доступа.", back_keyboard())
    await edit(c, tx.admin_crypto(pending_crypto_orders()), admin_back_keyboard())


@dp.callback_query(F.data == "admin_stats")
async def admin_stats(c: CallbackQuery):
    await safe_callback_answer(c)
    if c.from_user.id not in ADMIN_IDS: return await edit(c, "⛔ Нет доступа.", back_keyboard())
    await edit(c, tx.admin_stats(stats_snapshot()), admin_back_keyboard())


@dp.message(Command("paid"))
async def mark_paid(message: Message):
    """Ручное подтверждение (запасной вариант, если автопроверка не увидела платёж)."""
    if message.from_user.id not in ADMIN_IDS: return await message.answer("⛔ Нет доступа.")
    parts = (message.text or "").split(maxsplit=2)
    if len(parts) != 3: return await message.answer("Формат: /paid ORDER_ID TXID — только после проверки сети, токена, суммы и адреса.")
    try: order_id = int(parts[1]); txid = parts[2].strip()
    except ValueError: return await message.answer("Неверный номер заказа.")
    status, row = confirm_crypto_order(order_id, txid)
    if status == "not_found": return await message.answer("Заказ не найден.")
    if status == "processed": return await message.answer("Заказ уже обработан.")
    if status == "dup_tx": return await message.answer("Этот TXID уже использовался.")
    await message.answer(f"✅ Заказ #{order_id} подтверждён. Начислено {row['credit_amount']} попыток.")
    try:
        i18n.set_lang(get_lang(row["user_id"]))
        await bot.send_message(row["user_id"], tx.payment_confirmed(order_id, row["credit_amount"]), parse_mode="HTML")
    except Exception:
        pass


@dp.message(Command("gramaddr"))
async def gramaddr_command(message: Message):
    """Задаёт адрес кошелька GRAM (TON) до перезапуска бота."""
    global TON_GRAM_ADDRESS
    if message.from_user.id not in ADMIN_IDS: return await message.answer("⛔ Нет доступа.")
    parts = (message.text or "").split()
    if len(parts) != 2:
        return await message.answer(f"Формат: /gramaddr АДРЕС_TON_КОШЕЛЬКА\nСейчас: {TON_GRAM_ADDRESS or 'не задан'}")
    TON_GRAM_ADDRESS = parts[1].strip()
    note = "" if GRAM_PER_USD > 0 else "\n⚠️ Курс не задан: добавь его командой /gramrate 123.45"
    await message.answer(f"✅ Адрес GRAM сохранён до перезапуска. Для постоянного значения впиши TON_GRAM_ADDRESS в .env.{note}")


@dp.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    try:
        parts = q.invoice_payload.split(":")
        kind, uid = parts[0], int(parts[1])
        valid = uid == q.from_user.id and q.currency == "XTR"
        if kind == "std" and len(parts) == 4:
            count, amount = int(parts[2]), int(parts[3])
            valid = valid and count in STANDARD_PACKS and STANDARD_PACKS[count]["stars"] > 0 and STANDARD_PACKS[count]["stars"] == amount and q.total_amount == amount
        elif kind == "username" and len(parts) == 4:
            name, amount = parts[2], int(parts[3])
            with connect_db() as db:
                row = db.execute("SELECT price_stars FROM usernames WHERE username=? AND status='available'", (name,)).fetchone()
            valid = valid and row is not None and int(row["price_stars"]) == amount and q.total_amount == amount
        else:
            valid = False
        await q.answer(ok=valid, error_message=None if valid else "Счёт недействителен. Открой тарифы и создай новый.")
    except Exception:
        await q.answer(ok=False, error_message="Не удалось проверить счёт.")


@dp.message(F.successful_payment)
async def successful_payment(message: Message):
    p=message.successful_payment
    with connect_db() as db:
        cur=db.execute("INSERT OR IGNORE INTO payments(telegram_charge_id,user_id,payload,amount,created_at) VALUES(?,?,?,?,?)",(p.telegram_payment_charge_id,message.from_user.id,p.invoice_payload,p.total_amount,now_iso()))
    if cur.rowcount!=1: return await message.answer("Этот платёж уже был обработан.")
    parts=p.invoice_payload.split(":")
    if parts[0]=="std" and len(parts)==4:
        _,uid,count,amount=parts
        if int(uid)!=message.from_user.id or int(count) not in STANDARD_PACKS or STANDARD_PACKS[int(count)]["stars"] <= 0 or p.currency!="XTR" or p.total_amount!=int(amount):
            return await message.answer("Платёж получен, но данные не совпали. Администратор проверит его вручную.")
        credit_attempts(message.from_user.id,int(count))
        await message.answer(tx.payment_ok_std(count),reply_markup=main_keyboard(),parse_mode="HTML")
    elif parts[0]=="username" and len(parts)==4:
        _,uid,name,amount=parts
        if int(uid)!=message.from_user.id or p.currency!="XTR" or p.total_amount!=int(amount):
            return await message.answer("Платёж получен, но данные заказа требуют проверки администратором.")
        oid=create_order(int(uid),name,"paid_purchase")
        await notify_admins(f"💳 Оплачен заказ #{oid}\nПользователь: {uid}\nЮзернейм: @{name}\nСумма: {p.total_amount} Stars. Передачу имени проверь вручную.")
        if i18n.current_lang() == "en":
            pay_msg = f"✅ <b>Payment received</b>\n\nOrder #{oid} for <code>@{name}</code> was sent to an admin. Check status in your profile."
        else:
            pay_msg = f"✅ <b>Оплата получена</b>\n\nЗаказ #{oid} на <code>@{name}</code> передан администратору. Статус смотри в профиле."
        await message.answer(pay_msg, parse_mode="HTML", reply_markup=order_keyboard())


async def main():
    init_db()
    if not MINI_APP_URL.startswith("https://"):
        log.warning("MINI_APP_URL не задан: будет показано стандартное меню без цветного Mini App")
    if not TON_GRAM_ADDRESS or (GRAM_PER_USD <= 0 and not GRAM_RATE_AUTO):
        log.warning("GRAM выключен: задай TON_GRAM_ADDRESS (курс подтянется сам) или GRAM_PER_USD в .env")
    await setup_mtproto()
    tracker_task = asyncio.create_task(tracker_loop())
    crypto_task = asyncio.create_task(crypto_loop())
    rate_task = asyncio.create_task(gram_rate_loop())
    log.info("FindTag запускается")
    try: await dp.start_polling(bot)
    finally:
        tracker_task.cancel()
        crypto_task.cancel()
        rate_task.cancel()
        if telethon_client: await telethon_client.disconnect()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
