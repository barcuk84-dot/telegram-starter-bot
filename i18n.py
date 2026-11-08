"""Перевод текста кнопок (русский → английский) по выбранному языку пользователя."""
import re
from contextvars import ContextVar

_LANG: ContextVar[str] = ContextVar("findtag_lang", default="ru")


def set_lang(lang):
    _LANG.set(lang if lang in ("ru", "en") else "ru")


def current_lang() -> str:
    return _LANG.get()


EN = {
    "Следующий ➡️ −1🎟": "Next ➡️ −1🎟",
    "Следующий ➡️": "Next ➡️",
    "ℹ️ Помощь": "ℹ️ Help",
    "⚖️ Сравнение": "⚖️ Compare",
    "⚖️ Сравнить ещё": "⚖️ Compare again",
    "⚖️ Сравнить": "⚖️ Compare",
    "❤️ В избранное": "❤️ Add to favorites",
    "❤️ Избранное": "❤️ Favorites",
    "⬅️ В меню": "⬅️ Menu",
    "⬅️ К пакетам": "⬅️ To packs",
    "⬅️ К поиску": "⬅️ To search",
    "⬅️ К тарифам": "⬅️ To pricing",
    "⬅️ Назад": "⬅️ Back",
    "⬅️ Предыдущий": "⬅️ Previous",
    "⬅️ Назад в профиль": "⬅️ Back to profile",
    "⬅️ В админку": "⬅️ Admin panel",
    "⭐ Оплатить Stars": "⭐ Pay with Stars",
    "⭐ Оценить": "⭐ Rate",
    "👤 Мой профиль": "👤 My profile",
    "👤 Профиль": "👤 Profile",
    "💎 GRAM (TON) · скоро": "💎 GRAM (TON) · soon",
    "💎 Premium 4 символа": "💎 Premium 4 chars",
    "💎 Premium 5 символов": "💎 Premium 5 chars",
    "💎 Купить попытки": "💎 Buy attempts",
    "💎 Оплатить GRAM (TON)": "💎 Pay with GRAM (TON)",
    "💎 Пакеты 4 символа": "💎 4-char packs",
    "💎 Пакеты 5 символов": "💎 5-char packs",
    "💎 Пакеты 6–8": "💎 6–8 packs",
    "💎 Пополнить баланс": "💎 Top up balance",
    "💎 Тарифы": "💎 Pricing",
    "💵 Оплатить USDT (TRC20)": "💵 Pay with USDT (TRC20)",
    "📝 Заявка": "📝 Request",
    "📡 Мой трекер": "📡 My tracker",
    "📡 Отслеживать": "📡 Track",
    "📡 Трекер": "📡 Tracker",
    "🔍 Поиск": "🔍 Search",
    "🔍 Найти юзернейм": "🔍 Find username",
    "⚠️ Имя занято": "⚠️ Name is taken",
    "✅ Вернуть попытку": "✅ Return attempt",
    "⚙️ Сменить длину": "⚙️ Change length",
    "🗃 Поиск в базе": "🗃 Search database",
    "🛒 Купить": "🛒 Buy",
    "🤖 Автоматический поиск": "🤖 Auto search",
    "🤖 Автопоиск": "🤖 Auto search",
    "🎲 Случайное 4/5 · Premium": "🎲 Random 4/5 · Premium",
    "🌍 Выбрать язык": "🌍 Language",
    "🌈 Открыть FindTag": "🌈 Open FindTag",
    "➕ Добавить юзернейм": "➕ Add username",
    "🗑 Удалить юзернейм": "🗑 Delete username",
    "🎟 Выдать попытки": "🎟 Grant attempts",
    "📋 Последние заявки": "📋 Recent requests",
    "💳 Крипто-заказы": "💳 Crypto orders",
    "📊 Статистика": "📊 Stats",
}

_PATTERNS = (
    (re.compile(r"^(\d+) попыток — (.*)$"), r"\1 attempts — \2"),
    (re.compile(r"^Баланс: (\d+) попыток$"), r"Balance: \1 attempts"),
    (re.compile(r"^Длина: ([\d–]+) символов ⚙️$"), r"Length: \1 chars ⚙️"),
    (re.compile(r"^🎟 (\d+) попыток · (.*)$"), r"🎟 \1 attempts · \2"),
    (re.compile(r"^Длина: ([\d–]+) chars ⚙️$"), r"Length: \1 chars ⚙️"),  # already EN
)


def tr_button(text: str) -> str:
    """Переводит подпись кнопки, если выбран английский. Незнакомые подписи остаются как есть."""
    if _LANG.get() != "en":
        return text
    if text in EN:
        return EN[text]
    for rx, repl in _PATTERNS:
        if rx.match(text):
            return rx.sub(repl, text)
    return text
