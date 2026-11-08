"""Все тексты бота FindTag (Telegram HTML).

Оформление: <b>, <i>, <code>, <blockquote>. Символы с ru.piliapp.com/symbol.
Приветствие, меню, тарифы, помощь и bonus_line лежат в texts_ui.py.
"""
import html

from texts_ui import welcome, menu, tariffs, help_text, bonus_line, LINE  # noqa: F401
import i18n

# Эти значения main.py перезаписывает при запуске.
AUTO_CRYPTO = True
HIT_CHANCE = {}  # {4: 20, 5: 40} — проценты, main.py задаёт при запуске
DAILY_BONUS = 3
DAILY_HOURS = 24


def _e(value) -> str:
    return html.escape(str(value if value is not None else ""))


def _bar(score, total=10) -> str:
    score = max(0, min(total, int(score)))
    return "▰" * score + "▱" * (total - score)


def _en() -> bool:
    return i18n.current_lang() == "en"


STATUS_RU = {
    "pending": "⏳ в обработке",
    "paid_purchase": "💳 оплачен",
    "done": "✔ выполнен",
    "paid": "✔ оплачен",
    "expired": "✖ истёк",
}

STATUS_EN = {
    "pending": "⏳ processing",
    "paid_purchase": "💳 paid",
    "done": "✔ done",
    "paid": "✔ paid",
    "expired": "✖ expired",
}


def _status(value) -> str:
    table = STATUS_EN if _en() else STATUS_RU
    return table.get(str(value), _e(value))


# ───────────── Поиск ─────────────

def search_hub(free, four, five):
    if _en():
        return (
            "🔍 <b>Username search</b>\n"
            f"{LINE}\n"
            "<blockquote>Pick a length — the bot will find a free name. "
            "The shorter the name, the rarer and more valuable it is ✦</blockquote>\n"
            "🎟 <b>Your attempts</b>\n"
            "<blockquote>"
            f"💎 4 characters: <b>{four}</b>\n"
            f"💎 5 characters: <b>{five}</b>\n"
            f"🔹 6 / 7 / 8 characters: <b>{free}</b>"
            "</blockquote>\n"
            "One attempt — one search.\n"
            "Pick a name length ➤"
        )
    return (
        "🔍 <b>Поиск юзернеймов</b>\n"
        f"{LINE}\n"
        "<blockquote>Выбери длину — бот подберёт свободное имя. "
        "Чем короче имя, тем оно реже и ценнее ✦</blockquote>\n"
        "🎟 <b>Твои попытки</b>\n"
        "<blockquote>"
        f"💎 4 символа: <b>{four}</b>\n"
        f"💎 5 символов: <b>{five}</b>\n"
        f"🔹 6 / 7 / 8 символов: <b>{free}</b>"
        "</blockquote>\n"
        "Одна попытка — один поиск.\n"
        "Выбери длину имени ➤"
    )


def lengths():
    if _en():
        return (
            "🔍 <b>Pick a name length</b>\n"
            f"{LINE}\n"
            "<blockquote>🎲 6 · 7 · 8 — random name of these lengths\n"
            "💎 4 and 5 characters — rare and valuable names (Premium)\n"
            "🎲 Random 4/5 — a rare name of one of the two lengths</blockquote>\n"
            "The shorter the name, the rarer and more expensive it is ✦"
        )
    return (
        "🔍 <b>Выбери длину имени</b>\n"
        f"{LINE}\n"
        "<blockquote>🎲 6 · 7 · 8 — случайное имя из этих длин\n"
        "💎 4 и 5 символов — редкие и дорогие имена (Premium)\n"
        "🎲 Случайное 4/5 — выпадет редкое имя одной из двух длин</blockquote>\n"
        "Чем короче имя, тем оно реже и дороже ✦"
    )


def length_screen(n, bal, auto_on=False):
    if _en():
        if n == 678:
            title, rare, chance = "6–8 chars · random length", "🎲 Name length is chosen at random\n", ""
        elif n == 45:
            title, rare = "4–5 chars · random length", "💎 Rare category · length is random\n"
            chance = ""
            if 4 in HIT_CHANCE and 5 in HIT_CHANCE:
                chance = "🎯 If no name drops, the attempt is still spent.\n"
        else:
            title = f"{n} chars"
            rare = "💎 Rare category\n" if n in (4, 5) else ""
            chance = ""
            if n in HIT_CHANCE:
                chance = "🎯 If no name drops, the attempt is still spent.\n"
        auto = "\n🤖 Auto search is available." if (auto_on and n not in (4, 45)) else ""
        return (
            f"🔍 <b>Search · {title}</b>\n"
            f"{LINE}\n"
            f"<blockquote>{rare}{chance}🎟 Attempts on balance: <b>{bal}</b></blockquote>"
            f"{auto}\n"
            "One attempt — one search ➤"
        )
    if n == 678:
        title, rare, chance = "6–8 симв. · случайная длина", "🎲 Длина имени выпадает случайно\n", ""
    elif n == 45:
        title, rare = "4–5 симв. · случайная длина", "💎 Редкая категория · длина выпадает случайно\n"
        chance = ""
        if 4 in HIT_CHANCE and 5 in HIT_CHANCE:
            chance = "🎯 Если имя не выпало, попытка всё равно списывается.\n"
    else:
        title = f"{n} симв."
        rare = "💎 Редкая категория\n" if n in (4, 5) else ""
        chance = ""
        if n in HIT_CHANCE:
            chance = "🎯 Если имя не выпало, попытка всё равно списывается.\n"
    auto = "\n🤖 Доступен автопоиск." if (auto_on and n not in (4, 45)) else ""
    return (
        f"🔍 <b>Поиск · {title}</b>\n"
        f"{LINE}\n"
        f"<blockquote>{rare}{chance}🎟 Попыток на балансе: <b>{bal}</b></blockquote>"
        f"{auto}\n"
        "Одна попытка — один поиск ➤"
    )


def no_attempts(n, refill_text=None):
    if _en():
        refill = ""
        if refill_text and n not in (4, 5):
            refill = f"\n🕒 Free attempts refill in <b>{_e(refill_text)}</b>."
        return (
            f"😔 <b>No attempts left</b> ({n} chars)\n"
            f"<blockquote>This balance has no attempts remaining.</blockquote>{refill}\n"
            "Top up your balance ➤"
        )
    refill = ""
    if refill_text and n not in (4, 5):
        refill = f"\n🕒 Бесплатные попытки вернутся через <b>{_e(refill_text)}</b>."
    return (
        f"😔 <b>Попытки закончились</b> ({n} симв.)\n"
        f"<blockquote>На этом балансе попыток не осталось.</blockquote>{refill}\n"
        "Пополни баланс ➤"
    )


def premium_offer(n=None):
    if _en():
        if n is None:
            head, where = "Premium · 4–5 characters", "for 4 and 5 characters"
            chance = ""
            if 4 in HIT_CHANCE and 5 in HIT_CHANCE:
                chance = "\n🎯 If no name drops, the attempt is still spent."
        else:
            head, where = f"Premium · {n} chars", f"for {n} characters"
            chance = "\n🎯 If no name drops, the attempt is still spent." if n in HIT_CHANCE else ""
        return (
            f"💎 <b>{head}</b>\n"
            f"{LINE}\n"
            "<blockquote>This is a rare name category — search here is paid.\n"
            f"You have no attempts {where} yet.{chance}</blockquote>\n"
            "Top up your balance and start searching ➤"
        )
    if n is None:
        head, where = "Premium · 4–5 символов", "на 4 и 5 символов"
        chance = ""
        if 4 in HIT_CHANCE and 5 in HIT_CHANCE:
            chance = "\n🎯 Если имя не выпало, попытка всё равно списывается."
    else:
        word = "символа" if n == 4 else "символов"
        head, where = f"Premium · {n} {word}", f"на {n} {word}"
        chance = "\n🎯 Если имя не выпало, попытка всё равно списывается." if n in HIT_CHANCE else ""
    return (
        f"💎 <b>{head}</b>\n"
        f"{LINE}\n"
        "<blockquote>Это редкая категория имён — поиск здесь платный.\n"
        f"На балансе пока нет попыток {where}.{chance}</blockquote>\n"
        "Пополни баланс и начни поиск ➤"
    )


def premium_miss(n, pct=None):
    if _en():
        return (
            f"🍀 <b>No luck this time</b>\n"
            f"<blockquote>A {n}-character name did not drop this time, "
            "the attempt was spent.\nTry again!</blockquote>"
        )
    return (
        f"🍀 <b>В этот раз не повезло</b>\n"
        f"<blockquote>Имя из {n} символов в этот раз не выпало, "
        "попытка списана.\nПопробуй ещё раз!</blockquote>"
    )


def db_empty(n):
    if _en():
        return (
            f"📭 <b>No new {n}-character names in the database</b>\n"
            "<blockquote>The attempt was spent: the pack does not guarantee a result. "
            "Try later — the database is updated.</blockquote>"
        )
    return (
        f"📭 <b>В базе нет новых имён из {n} символов</b>\n"
        "<blockquote>Попытка списана: пакет не гарантирует результат. "
        "Попробуй позже — база пополняется.</blockquote>"
    )


def auto_scanning(n):
    if _en():
        return f"🤖 <b>Auto search started</b>\n<i>Looking for a free {n}-character name…</i> ✧"
    return f"🤖 <b>Автопоиск запущен</b>\n<i>Ищу свободное имя из {n} символов…</i> ✧"


def auto_off():
    if _en():
        return "🤖 <b>Auto search is currently off</b>\n<blockquote>Use database search.</blockquote>"
    return "🤖 <b>Автопоиск сейчас выключен</b>\n<blockquote>Воспользуйся поиском в базе.</blockquote>"


def auto_not_found(n):
    if _en():
        return (
            f"😕 <b>No free {n}-character name found</b>\n"
            "<blockquote>Try again a bit later.</blockquote>"
        )
    return (
        f"😕 <b>Свободное имя из {n} символов не найдено</b>\n"
        "<blockquote>Попробуй ещё раз немного позже.</blockquote>"
    )


def auto_error(e):
    if _en():
        return (
            "⚠️ <b>Auto search is temporarily unavailable</b>\n"
            f"<blockquote>{_e(e)[:150]}</blockquote>\n"
            "The attempt was returned to your balance ✔"
        )
    return (
        "⚠️ <b>Автопоиск временно недоступен</b>\n"
        f"<blockquote>{_e(e)[:150]}</blockquote>\n"
        "Попытка возвращена на баланс ✔"
    )


def auto_4_unavailable():
    if _en():
        return (
            "💎 <b>Auto search is unavailable for 4 characters</b>\n"
            "<blockquote>Such names are extremely rare — use database search.</blockquote>"
        )
    return (
        "💎 <b>Для 4 символов автопоиск недоступен</b>\n"
        "<blockquote>Такие имена встречаются очень редко — используй поиск в базе.</blockquote>"
    )


# ───────────── Карточки ─────────────

def _source_label(source):
    if _en():
        return "🤖 auto search" if source == "auto" else "🗃 database"
    return "🤖 автопоиск" if source == "auto" else "🗃 база"


def username_card(name, score, liquidity, price, price_stars, source, traits,
                  pos=None, can_buy=False):
    head = f"✦ <b>@{_e(name)}</b> ✦"
    if pos:
        head += f"   <i>{pos[0]}/{pos[1]}</i>"
    if _en():
        lines = [
            head,
            LINE,
            f"★ Score: <b>{score}/10</b>  {_bar(score)}",
            f"💧 Liquidity: <b>{liquidity}/10</b>  {_bar(liquidity)}",
            f"💰 Approx. price: <b>{_e(price)}</b>",
        ]
        if can_buy and price_stars:
            lines.append(f"⭐ Price: <b>{price_stars}</b> Stars")
        card = "\n".join(lines)
        if traits:
            card += "\n<blockquote expandable>" + "\n".join(f"➤ {_e(t)}" for t in traits) + "</blockquote>"
        card += "\n<i>Price is an approximate estimate, not a market quote.</i>"
        return card
    lines = [
        head,
        LINE,
        f"★ Оценка: <b>{score}/10</b>  {_bar(score)}",
        f"💧 Ликвидность: <b>{liquidity}/10</b>  {_bar(liquidity)}",
        f"💰 Примерная цена: <b>{_e(price)}</b>",
    ]
    if can_buy and price_stars:
        lines.append(f"⭐ Цена: <b>{price_stars}</b> Stars")
    card = "\n".join(lines)
    if traits:
        card += "\n<blockquote expandable>" + "\n".join(f"➤ {_e(t)}" for t in traits) + "</blockquote>"
    card += "\n<i>Цена — примерная оценка, а не рыночная котировка.</i>"
    return card


def rate_prompt():
    if _en():
        return (
            "⭐ <b>Username rating</b>\n"
            f"{LINE}\n"
            "<blockquote>Find out how good a name looks and what it might be worth.\n\n"
            "➤ Appeal — how the name looks and sounds\n"
            "➤ Liquidity — how easy it is to sell\n"
            "➤ Price guide — approximate range in dollars</blockquote>\n"
            "Send a username, e.g. <code>@nova</code> ➤"
        )
    return (
        "⭐ <b>Оценка юзернейма</b>\n"
        f"{LINE}\n"
        "<blockquote>Узнай, насколько имя красивое и сколько оно может стоить.\n\n"
        "➤ Привлекательность — насколько имя выглядит и звучит\n"
        "➤ Ликвидность — как легко такое имя продать\n"
        "➤ Ориентир цены — примерный диапазон в долларах</blockquote>\n"
        "Отправь юзернейм, например: <code>@nova</code> ➤"
    )


def rate_card(name, score, liq, price, traits):
    if _en():
        card = (
            f"⭐ <b>Rating @{_e(name)}</b>\n"
            f"{LINE}\n"
            f"★ Appeal: <b>{score}/10</b>  {_bar(score)}\n"
            f"💧 Liquidity: <b>{liq}/10</b>  {_bar(liq)}\n"
            f"💰 Approx. price: <b>{_e(price)}</b>"
        )
    else:
        card = (
            f"⭐ <b>Оценка @{_e(name)}</b>\n"
            f"{LINE}\n"
            f"★ Красота: <b>{score}/10</b>  {_bar(score)}\n"
            f"💧 Ликвидность: <b>{liq}/10</b>  {_bar(liq)}\n"
            f"💰 Примерная цена: <b>{_e(price)}</b>"
        )
    if traits:
        card += "\n<blockquote expandable>" + "\n".join(f"➤ {_e(t)}" for t in traits) + "</blockquote>"
    return card


def compare_prompt():
    if _en():
        return (
            "⚖️ <b>Compare names</b>\n"
            f"{LINE}\n"
            "<blockquote>Choosing between two options? I'll put them side by side: "
            "score, liquidity and price of each, then a verdict on which is stronger.</blockquote>\n"
            "Send two usernames separated by a space:\n"
            "<code>@nova @mira</code> ➤"
        )
    return (
        "⚖️ <b>Сравнение имён</b>\n"
        f"{LINE}\n"
        "<blockquote>Выбираешь между двумя вариантами? Поставлю их рядом: "
        "оценка, ликвидность и цена каждого, а в конце — вывод, какое сильнее.</blockquote>\n"
        "Отправь два юзернейма через пробел:\n"
        "<code>@nova @mira</code> ➤"
    )


def compare_card(a, b):
    def row(label, key):
        return f"{label}: <b>{_e(a[key])}</b>  ⚔  <b>{_e(b[key])}</b>"

    if _en():
        if a["score"] > b["score"]:
            verdict = f"✔ Looks better: <b>@{_e(a['name'])}</b>"
        elif b["score"] > a["score"]:
            verdict = f"✔ Looks better: <b>@{_e(b['name'])}</b>"
        else:
            verdict = "✔ Scores are equal"
        return (
            f"⚖️ <b>@{_e(a['name'])}  vs  @{_e(b['name'])}</b>\n"
            f"{LINE}\n"
            f"{row('★ Score', 'score')}\n"
            f"{row('💧 Liquidity', 'liq')}\n"
            f"{row('💰 Price', 'price')}\n\n"
            f"{verdict}"
        )
    if a["score"] > b["score"]:
        verdict = f"✔ Лучше выглядит <b>@{_e(a['name'])}</b>"
    elif b["score"] > a["score"]:
        verdict = f"✔ Лучше выглядит <b>@{_e(b['name'])}</b>"
    else:
        verdict = "✔ По оценке имена равны"
    return (
        f"⚖️ <b>@{_e(a['name'])}  vs  @{_e(b['name'])}</b>\n"
        f"{LINE}\n"
        f"{row('★ Оценка', 'score')}\n"
        f"{row('💧 Ликвидность', 'liq')}\n"
        f"{row('💰 Цена', 'price')}\n\n"
        f"{verdict}"
    )


# ───────────── Избранное и трекер ─────────────

def favorites(names):
    if _en():
        if not names:
            return (
                "❤️ <b>Favorites</b>\n"
                f"{LINE}\n"
                "<blockquote>Nothing here yet.\n\n"
                "Found a nice name in search? Tap «Add to favorites» on the card — "
                "and it will be saved in your personal collection ♡</blockquote>\n"
                "Start with search 🔍"
            )
        body = "\n".join(f"♡ @{_e(n)}" for n in names)
        return (
            f"❤️ <b>Favorites</b> · {len(names)}\n{LINE}\n"
            f"<blockquote>{body}</blockquote>\n"
            "Tap ❌ next to a name to remove it from the list."
        )
    if not names:
        return (
            "❤️ <b>Избранное</b>\n"
            f"{LINE}\n"
            "<blockquote>Здесь пока пусто.\n\n"
            "Нашёл красивое имя в поиске? Жми «В избранное» в карточке — "
            "и оно сохранится в твоей личной коллекции ♡</blockquote>\n"
            "Начни с поиска 🔍"
        )
    body = "\n".join(f"♡ @{_e(n)}" for n in names)
    return (
        f"❤️ <b>Избранное</b> · {len(names)}\n{LINE}\n"
        f"<blockquote>{body}</blockquote>\n"
        "Нажми ❌ рядом с именем, чтобы убрать его из списка."
    )


def favorite_added(name):
    if _en():
        return f"❤️ <b>@{_e(name)}</b> added to favorites ✔"
    return f"❤️ <b>@{_e(name)}</b> добавлен в избранное ✔"


def tracker(names, live, minutes):
    if _en():
        if not live:
            status = "⚠️ Checking via Telegram is currently unavailable."
        else:
            status = f"✔ Checking every <b>{minutes}</b> min."
        if not names:
            return (
                "📡 <b>Tracker</b>\n"
                f"{LINE}\n"
                "<blockquote>Need a name that is still taken? Add it to the tracker — "
                "I'll check it myself and message you as soon as it becomes free.\n\n"
                "The list is empty. Add names with the «Track» button on a card.</blockquote>\n"
                f"{status}"
            )
        body = "\n".join(f"➤ @{_e(n)}" for n in names)
        return (
            f"📡 <b>Tracker</b> · {len(names)}\n{LINE}\n"
            f"<blockquote>{body}</blockquote>\n"
            f"I'll message you when any of these names becomes free.\n{status}"
        )
    if not live:
        status = "⚠️ Проверка через Telegram сейчас недоступна."
    else:
        status = f"✔ Проверка каждые <b>{minutes}</b> мин."
    if not names:
        return (
            "📡 <b>Трекер</b>\n"
            f"{LINE}\n"
            "<blockquote>Имя, которое тебе нужно, пока занято? Добавь его в трекер — "
            "я буду проверять его сам и напишу, как только оно освободится.\n\n"
            "Список пока пуст. Добавляй имена кнопкой «В трекер» в карточке.</blockquote>\n"
            f"{status}"
        )
    body = "\n".join(f"➤ @{_e(n)}" for n in names)
    return (
        f"📡 <b>Трекер</b> · {len(names)}\n{LINE}\n"
        f"<blockquote>{body}</blockquote>\n"
        f"Я напишу, когда любое из этих имён освободится.\n{status}"
    )


def tracker_added(name, live, minutes):
    if _en():
        note = f"Checking every {minutes} min." if live else "Checking will be available after Telegram is connected."
        return f"📡 <b>@{_e(name)}</b> added to tracker ✔\n<i>{note}</i>"
    note = f"Проверяю каждые {minutes} мин." if live else "Проверка станет доступна после подключения Telegram."
    return f"📡 <b>@{_e(name)}</b> добавлен в трекер ✔\n<i>{note}</i>"


def tracker_alert(name):
    if _en():
        return (
            "🔔 <b>Name is free!</b>\n"
            f"<blockquote>@{_e(name)} is available now ✦\nClaim it while you can.</blockquote>"
        )
    return (
        "🔔 <b>Имя освободилось!</b>\n"
        f"<blockquote>@{_e(name)} сейчас свободно ✦\nУспей занять его.</blockquote>"
    )


# ───────────── Профиль ─────────────

def profile(uid, free, four, five, orders, refill_text=None):
    if _en():
        refill = ""
        if refill_text:
            refill = f"\n🕒 Next 6/7/8 refill: in <b>{_e(refill_text)}</b>"
        text = (
            "👤 <b>Profile</b>\n"
            f"{LINE}\n"
            f"🆔 ID: <code>{uid}</code>\n"
            "<blockquote>"
            f"💎 4 characters: <b>{four}</b>\n"
            f"💎 5 characters: <b>{five}</b>\n"
            f"🔹 6 / 7 / 8 characters: <b>{free}</b>"
            "</blockquote>"
            f"{refill}"
        )
        if orders:
            rows = "\n".join(f"#{oid} · @{_e(name)} · {_status(st)}" for oid, name, st in orders[:10])
            text += f"\n\n📋 <b>Requests</b>\n<blockquote>{rows}</blockquote>"
        return text
    refill = ""
    if refill_text:
        refill = f"\n🕒 Следующее пополнение 6/7/8: через <b>{_e(refill_text)}</b>"
    text = (
        "👤 <b>Профиль</b>\n"
        f"{LINE}\n"
        f"🆔 ID: <code>{uid}</code>\n"
        "<blockquote>"
        f"💎 4 символа: <b>{four}</b>\n"
        f"💎 5 символов: <b>{five}</b>\n"
        f"🔹 6 / 7 / 8 символов: <b>{free}</b>"
        "</blockquote>"
        f"{refill}"
    )
    if orders:
        rows = "\n".join(f"#{oid} · @{_e(name)} · {_status(st)}" for oid, name, st in orders[:10])
        text += f"\n\n📋 <b>Заявки</b>\n<blockquote>{rows}</blockquote>"
    return text


# ───────────── Оплата ─────────────

def _gram_line(gram_amount):
    return f"\n💎 GRAM: <b>{gram_amount:g}</b>" if gram_amount else ""


def pack_screen(count, stars, usd, gram_amount=0):
    if _en():
        return (
            f"🎟 <b>Pack: {count} attempts</b>\n"
            f"{LINE}\n"
            "<blockquote>"
            f"⭐ Stars: <b>{stars}</b>\n"
            f"💵 USDT: <b>${usd:.2f}</b>"
            f"{_gram_line(gram_amount)}"
            "</blockquote>\n"
            "For search of length 6 / 7 / 8 characters.\nChoose a payment method ➤"
        )
    return (
        f"🎟 <b>Пакет: {count} попыток</b>\n"
        f"{LINE}\n"
        "<blockquote>"
        f"⭐ Stars: <b>{stars}</b>\n"
        f"💵 USDT: <b>${usd:.2f}</b>"
        f"{_gram_line(gram_amount)}"
        "</blockquote>\n"
        "Для поиска длиной 6 / 7 / 8 символов.\nВыбери способ оплаты ➤"
    )


def _chance_note(length):
    if length not in HIT_CHANCE:
        return ""
    if _en():
        return "\n🎯 If no name drops, the attempt is still spent."
    return "\n🎯 Если имя не выпало, попытка всё равно списывается."


def premium_shop(length, gram_on=False):
    if _en():
        gram = " · GRAM" if gram_on else ""
        return (
            f"💎 <b>Premium · {length} chars</b>\n"
            f"{LINE}\n"
            "<blockquote>Separate balance for rare names.\n"
            f"Payment: USDT{gram}{_chance_note(length)}</blockquote>\n"
            "Pick a pack ➤"
        )
    gram = " · GRAM" if gram_on else ""
    return (
        f"💎 <b>Premium · {length} {'символа' if length == 4 else 'символов'}</b>\n"
        f"{LINE}\n"
        "<blockquote>Отдельный баланс для редких имён.\n"
        f"Оплата: USDT{gram}{_chance_note(length)}</blockquote>\n"
        "Выбери пакет ➤"
    )


def premium_pack_screen(length, count, usd, gram_amount=0):
    if _en():
        return (
            f"💎 <b>Premium {length} · {count} attempts</b>\n"
            f"{LINE}\n"
            "<blockquote>"
            f"💵 USDT: <b>${usd:.2f}</b>"
            f"{_gram_line(gram_amount)}"
            f"{_chance_note(length)}"
            "</blockquote>\n"
            "Choose a payment method ➤"
        )
    return (
        f"💎 <b>Premium {length} · {count} попыток</b>\n"
        f"{LINE}\n"
        "<blockquote>"
        f"💵 USDT: <b>${usd:.2f}</b>"
        f"{_gram_line(gram_amount)}"
        f"{_chance_note(length)}"
        "</blockquote>\n"
        "Выбери способ оплаты ➤"
    )


def _confirm_note():
    if _en():
        return ("✔ The bot will detect the payment and credit attempts automatically."
                if AUTO_CRYPTO else "✔ After payment an admin will confirm the order manually.")
    return ("✔ Бот сам увидит платёж и начислит попытки."
            if AUTO_CRYPTO else "✔ После оплаты администратор подтвердит заказ вручную.")


def order_usdt(order_id, title, pay, address):
    if _en():
        return (
            f"💵 <b>Order #{order_id}</b>\n"
            f"{LINE}\n"
            f"<i>{_e(title)}</i>\n\n"
            f"Amount: <b>{pay:g} USDT</b> (network <b>TRC20</b>)\n"
            f"Address:\n<code>{_e(address)}</code>\n\n"
            "<blockquote>⚠️ Send the <b>exact amount</b> and only on the TRON (TRC20) network.</blockquote>\n"
            f"{_confirm_note()}"
        )
    return (
        f"💵 <b>Заказ #{order_id}</b>\n"
        f"{LINE}\n"
        f"<i>{_e(title)}</i>\n\n"
        f"Сумма: <b>{pay:g} USDT</b> (сеть <b>TRC20</b>)\n"
        f"Адрес:\n<code>{_e(address)}</code>\n\n"
        "<blockquote>⚠️ Отправь <b>точную сумму</b> и только в сети TRON (TRC20).</blockquote>\n"
        f"{_confirm_note()}"
    )


def order_gram(order_id, title, pay, usd, address):
    if _en():
        return (
            f"💎 <b>Order #{order_id}</b>\n"
            f"{LINE}\n"
            f"<i>{_e(title)}</i>\n\n"
            f"Amount: <b>{pay:g} GRAM</b> (≈ ${usd:.2f})\n"
            f"Address (TON network):\n<code>{_e(address)}</code>\n\n"
            "<blockquote>⚠️ Send the <b>exact amount</b> and only on the TON network.</blockquote>\n"
            f"{_confirm_note()}"
        )
    return (
        f"💎 <b>Заказ #{order_id}</b>\n"
        f"{LINE}\n"
        f"<i>{_e(title)}</i>\n\n"
        f"Сумма: <b>{pay:g} GRAM</b> (≈ ${usd:.2f})\n"
        f"Адрес (сеть TON):\n<code>{_e(address)}</code>\n\n"
        "<blockquote>⚠️ Отправь <b>точную сумму</b> и только в сети TON.</blockquote>\n"
        f"{_confirm_note()}"
    )


def payment_confirmed(order_id, credit):
    if _en():
        return f"✅ <b>Order #{order_id} paid</b>\n<blockquote>Attempts credited: <b>{credit}</b> ✦</blockquote>"
    return f"✅ <b>Заказ #{order_id} оплачен</b>\n<blockquote>Начислено попыток: <b>{credit}</b> ✦</blockquote>"


def payment_ok_std(count):
    if _en():
        return f"✅ <b>Payment received</b>\n<blockquote>Attempts credited: <b>{count}</b> ✦</blockquote>\nHappy searching ✧"
    return f"✅ <b>Оплата получена</b>\n<blockquote>Начислено попыток: <b>{count}</b> ✦</blockquote>\nПриятного поиска ✧"


def gram_off():
    if _en():
        return "💎 GRAM will be available soon"
    return "💎 GRAM скоро будет доступен"


# ───────────── Админка ─────────────

def admin_panel():
    return "🛠 <b>Админ-панель</b>\n<blockquote>Выбери действие ➤</blockquote>"


def admin_stats(s):
    lengths_rows = "\n".join(f"➤ {l} симв.: <b>{c}</b>" for l, c in s.get("by_length", [])) or "—"
    return (
        "📊 <b>Статистика</b>\n"
        f"{LINE}\n"
        "<blockquote>"
        f"👥 Пользователей: <b>{s['users']}</b>\n"
        f"📡 В трекере: <b>{s['tracked']}</b>\n"
        f"📋 Заявок: <b>{s['orders']}</b>\n"
        f"⏳ Крипто в ожидании: <b>{s['pending']}</b>\n"
        f"✔ Крипто оплачено: <b>{s['paid']}</b>\n"
        f"⭐ Получено Stars: <b>{s['stars']}</b>"
        "</blockquote>\n"
        f"🗃 <b>Свободные имена в базе</b>\n<blockquote>{lengths_rows}</blockquote>"
    )


def admin_crypto(rows):
    if not rows:
        return "💳 <b>Крипто-заказы</b>\n<blockquote>Ожидающих заказов нет.</blockquote>"
    body = "\n".join(
        f"#{r['id']} · user <code>{r['user_id']}</code> · {r['credit_amount']} поп. · "
        f"{float(r['pay_amount']):g} {_e(r['pay_asset'])}"
        for r in rows
    )
    return (
        f"💳 <b>Ожидают оплаты · {len(rows)}</b>\n{LINE}\n<blockquote>{body}</blockquote>\n"
        "Ручное подтверждение: <code>/paid ORDER_ID TXID</code>"
    )


# ───────────── Замена занятого имени ─────────────

def taken_sent(name):
    if _en():
        return (f"📨 <b>Thanks!</b>\n<blockquote>I told the admin that @{_e(name)} is taken. "
                "Once confirmed, the attempt will be returned to your balance.</blockquote>")
    return (f"📨 <b>Спасибо!</b>\n<blockquote>Передал админу, что @{_e(name)} занято. "
            "После проверки попытка вернётся на твой баланс.</blockquote>")


def taken_refunded(old, length):
    if _en():
        return (f"✅ <b>Attempt returned</b>\n<blockquote>@{_e(old)} really was taken — "
                f"+1 attempt ({length} chars) is back on your balance.</blockquote>")
    return (f"✅ <b>Попытка возвращена</b>\n<blockquote>@{_e(old)} действительно оказалось занято — "
            f"+1 попытка ({length} симв.) снова на твоём балансе.</blockquote>")


def taken_replaced(old, new_card):
    if _en():
        return (f"🔄 <b>Replacement for @{_e(old)}</b>\n"
                "The attempt was not spent ✔\n\n" + new_card)
    return (f"🔄 <b>Замена для @{_e(old)}</b>\n"
            "Попытка не списана ✔\n\n" + new_card)


def taken_rejected(name):
    if _en():
        return f"ℹ️ <b>Report on @{_e(name)} was reviewed</b>\n<blockquote>The admin did not confirm it.</blockquote>"
    return f"ℹ️ <b>Жалоба на @{_e(name)} рассмотрена</b>\n<blockquote>Админ её не подтвердил.</blockquote>"
