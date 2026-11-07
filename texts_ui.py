"""Новое оформление текстов FindTag: приветствие, меню, тарифы, помощь.

Подключается одной строкой в main.py (texts_ui.apply(tx)) и заменяет
одноимённые функции из texts.py. Остальные тексты (карточки, админка,
заказы и т.д.) остаются как были.

Оформление: Telegram HTML — <b>, <i>, <code> и <blockquote>.
Символы взяты с ru.piliapp.com/symbol: ✦ ✧ ➤ ✔ ★ ❤ ✎ ✉ ❝ ❞ ☑ ☼ ♡
"""
import html

import i18n

LINE = "━━━━━━━━━━━━━━"


def _e(value) -> str:
    return html.escape(str(value or ""))


def _lang(lang=None) -> str:
    if lang in ("ru", "en"):
        return lang
    return i18n.current_lang()


def welcome(first_name, free_attempts, auto_search_enabled=False, lang="ru"):
    name = _e(first_name) or ("друг" if lang != "en" else "friend")
    if lang == "en":
        return (
            f"✦ <b>Hi, {name}!</b> ✦\n"
            "I'll help you find a beautiful username, rate it and compare it with another one.\n\n"
            f"{LINE}\n"
            "<blockquote>"
            "🔍 <b>Search</b> — names of 4, 5, 6, 7 and 8 characters\n"
            "⭐ <b>Rating</b> — appeal, liquidity and a price guide\n"
            "⚖️ <b>Compare</b> — two names side by side, with the price of each\n"
            "📡 <b>Tracker</b> — I'll message you when a name becomes free\n"
            "❤️ <b>Favorites</b> — your personal collection"
            "</blockquote>\n"
            f"{LINE}\n\n"
            "💡 <b>How it works:</b> pick a length ➤ get a free name ➤ rate it and save it.\n\n"
            f"🎁 <b>Gift:</b> {free_attempts} free attempts for names of 6, 7 and 8 characters.\n\n"
            "Choose a section below 👇"
        )
    return (
        f"✦ <b>Привет, {name}!</b> ✦\n"
        "Помогу найти красивое имя, оценить его и сравнить с другим.\n\n"
        f"{LINE}\n"
        "<blockquote>"
        "🔍 <b>Поиск</b> — имена из 4, 5, 6, 7 и 8 символов\n"
        "⭐ <b>Оценка</b> — привлекательность, ликвидность и ориентир цены\n"
        "⚖️ <b>Сравнение</b> — два имени рядом, с ценой каждого\n"
        "📡 <b>Трекер</b> — напишу, когда имя освободится\n"
        "❤️ <b>Избранное</b> — твоя личная коллекция"
        "</blockquote>\n"
        f"{LINE}\n\n"
        "💡 <b>Как это работает:</b> выбираешь длину ➤ получаешь свободное имя ➤ оцениваешь и сохраняешь.\n\n"
        f"🎁 <b>В подарок:</b> {free_attempts} бесплатных попыток для имён из 6, 7 и 8 символов.\n\n"
        "Выбери раздел ниже 👇"
    )


def menu():
    if _lang() == "en":
        return (
            "✦ <b>FindTag</b> · main menu ✦\n"
            f"{LINE}\n"
            "<blockquote>Find beautiful free usernames, rate them, "
            "compare and track the ones that are still taken.</blockquote>\n"
            "What are we doing today? 👇"
        )
    return (
        "✦ <b>FindTag</b> · главное меню ✦\n"
        f"{LINE}\n"
        "<blockquote>Ищи красивые свободные юзернеймы, оценивай их, "
        "сравнивай и следи за теми, что пока заняты.</blockquote>\n"
        "Что делаем сегодня? 👇"
    )


def tariffs(gram_on=False, free_attempts=6):
    if _lang() == "en":
        pay = "⭐ Telegram Stars  ·  💲 USDT (TRC20)"
        if gram_on:
            pay += "  ·  💎 GRAM"
        return (
            "💎 <b>FindTag Pricing</b>\n"
            f"{LINE}\n"
            "<blockquote>"
            "❝ One attempt — one name search.\n"
            "Pick a section below and top up your balance. ❞"
            "</blockquote>\n"
            f"<b>Payment:</b> {pay}\n"
            "✔ Attempts are credited right after payment."
        )
    pay = "⭐ Telegram Stars  ·  💲 USDT (TRC20)"
    if gram_on:
        pay += "  ·  💎 GRAM"
    return (
        "💎 <b>Тарифы FindTag</b>\n"
        f"{LINE}\n"
        "<blockquote>"
        "❝ Одна попытка — один поиск имени.\n"
        "Выбери раздел ниже и пополни баланс. ❞"
        "</blockquote>\n"
        f"<b>Оплата:</b> {pay}\n"
        "✔ Попытки начисляются сразу после оплаты."
    )


def help_text(auto_search_enabled=False):
    if _lang() == "en":
        auto = "\n➤ <b>Auto search</b> — the bot picks a free name for you." if auto_search_enabled else ""
        return (
            "ℹ️ <b>How to use FindTag</b>\n"
            f"{LINE}\n"
            "<blockquote expandable>"
            "🔍 <b>Search</b> — pick a name length and get options.\n"
            "⭐ <b>Rate</b> — beauty and liquidity score for a username.\n"
            "⚖️ <b>Compare</b> — two names side by side.\n"
            "📡 <b>Tracker</b> — the bot will message you when a name is free.\n"
            "❤️ <b>Favorites</b> — save names you like."
            f"{auto}"
            "</blockquote>\n"
            "💎 Top up your balance in the <b>Pricing</b> section."
        )
    auto = "\n➤ <b>Автопоиск</b> — бот сам подбирает свободное имя." if auto_search_enabled else ""
    return (
        "ℹ️ <b>Как пользоваться FindTag</b>\n"
        f"{LINE}\n"
        "<blockquote expandable>"
        "🔍 <b>Поиск</b> — выбери длину имени и получай варианты.\n"
        "⭐ <b>Оценить</b> — оценка красоты и ликвидности юзернейма.\n"
        "⚖️ <b>Сравнение</b> — два имени бок о бок.\n"
        "📡 <b>Трекер</b> — бот пришлёт сообщение, когда имя освободится.\n"
        "❤️ <b>Избранное</b> — сохраняй понравившиеся имена."
        f"{auto}"
        "</blockquote>\n"
        "💎 Пополнить баланс можно в разделе <b>Тарифы</b>."
    )


def bonus_line(bonus=0):
    """Строка про начисленный ежедневный бонус (пустая, если бонуса нет)."""
    if not bonus:
        return ""
    if _lang() == "en":
        return f"🎁 <b>Daily bonus: +{int(bonus)} attempts</b> ✧\n\n"
    return f"🎁 <b>Ежедневный бонус: +{int(bonus)} попыток</b> ✧\n\n"


def apply(tx):
    """Подменяет функции в модуле texts."""
    for fn in (welcome, menu, tariffs, help_text):
        setattr(tx, fn.__name__, fn)
    # Запасной вариант: добавляем, только если в texts.py такой функции нет.
    if not hasattr(tx, "bonus_line"):
        tx.bonus_line = bonus_line
    else:
        # Всегда подменяем bonus_line — у нас есть EN-версия.
        tx.bonus_line = bonus_line
