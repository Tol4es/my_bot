import random
from datetime import date
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, MessageHandler, filters, CallbackContext

from ..db.sqlite import ensure_user, is_blocked, get_user_cities, add_city, del_city, add_bug
from ..keyboards.common import main_keyboard, zodiac_inline_keyboard, fx_inline_keyboard
from ..services.weather import fetch_weather
from ..services.fx import parse_monobank
from ..utils.gates import require_phone_gate
from ..config import settings

PREDICTIONS = [
"🌟 Сьогодні вдасться те, що давно відкладав(-ла).",
"🚀 Не бійся почати з малого — результат здивує.",
"💡 Нова ідея прийде з неочікуваного боку.",
"🔎 Уважність до деталей принесе бонус.",
"🦁 Сміливість — твій кращий друг сьогодні.",
"🤝 Поділись добром — воно повернеться.",
"🕊️ Крок назустріч вирішить питання.",
"🌱 Зміни на краще почнуться з тебе.",
"🚶‍♂️ Невеличка прогулянка подарує інсайт.",
"💖 Хтось оцінить твою допомогу більше, ніж ти думаєш.",
"📞 Старий друг може нагадати про себе.",
"📚 Нове знання сьогодні стане у пригоді.",
"🎯 Концентрація приведе до маленької перемоги.",
"🍀 Удача усміхнеться у дрібницях.",
"☕ Чашка кави подарує натхнення.",
"✍️ Запиши свої думки — вони знадобляться.",
"🎁 На тебе чекає маленький сюрприз.",
"🌞 Гарний настрій зарядить оточення.",
"🌊 Будь гнучким — і все вийде.",
"🛤️ Новий шлях відкриється випадково.",
"🕯️ Терпіння — твій найкращий інструмент.",
"🎶 Музика допоможе знайти баланс.",
"👀 Уважно подивись навколо — буде підказка.",
"💬 Несподівана розмова принесе користь.",
"🍎 Подбай про здоров’я — організм подякує.",
]

def _daily_prediction_for(user_id: int, today: date | None = None) -> str:
    d = today or date.today()
    seed = int(f"{user_id}{d.strftime('%Y%m%d')}")
    rnd = random.Random(seed)
    return rnd.choice(PREDICTIONS)

async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await ensure_user(user.id, name=user.full_name)

    if await require_phone_gate(update, context):
        return
    if await is_blocked(user.id):
        return await update.message.reply_text("🚫 Ваш доступ обмежено адміністратором.")

    text = (update.message.text or "").strip()

    #режим баг-репорту
    if context.user_data.get("bug_mode"):
        if text == "⬅️ Назад":
            context.user_data.pop("bug_mode", None)
            cities = await get_user_cities(user.id)
            return await update.message.reply_text("Повернув клавіатуру ✅", reply_markup=main_keyboard(user.id, cities))
        await add_bug(user.id, text)
        try:
            await update.get_bot().send_message(
                chat_id=settings.admin_id,
                text=f"🐞 Новий баг-репорт від {user.full_name} ({user.id}):\n{text}",
            )
        except Exception:
            pass
        context.user_data.pop("bug_mode", None)
        cities = await get_user_cities(user.id)
        return await update.message.reply_text("Дякую! Передав адмінам ✅", reply_markup=main_keyboard(user.id, cities))

    #стандартні кнопки
    if text == "🏙 Додати місто":
        cities = await get_user_cities(user.id)
        if len(cities) >= 3:
            return await update.message.reply_text(
                "Можна зберегти максимум 3 міста. Спочатку видали зайве через «🗑️ Видалити місто».",
                reply_markup=main_keyboard(user.id, cities),
            )
        context.user_data["awaiting_city"] = True
        return await update.message.reply_text("Вкажи місто для збереження:")

    if text == "🗑️ Видалити місто":
        cities = await get_user_cities(user.id)
        if not cities:
            return await update.message.reply_text("Немає збережених міст.", reply_markup=main_keyboard(user.id))
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(c, callback_data=f"delcity:{c}") for c in cities]])
        return await update.message.reply_text("Оберіть місто для видалення:", reply_markup=kb)

    if text.startswith("🏙 "):
        city = text[2:].strip()
        cities = await get_user_cities(user.id)
        return await update.message.reply_text(fetch_weather(city), reply_markup=main_keyboard(user.id, cities))

    if text == "👋 Привітатись":
        cities = await get_user_cities(user.id)
        return await update.message.reply_text("Привіт, як справи? 😊", reply_markup=main_keyboard(user.id, cities))

    if text == "ℹ️Допомога":
        from .start import help_cmd
        return await help_cmd(update, context)

    if text == "❌Прибрати клавіатуру":
        return await update.message.reply_text("Клавіатуру прибрано. Щоб повернути — /start")

    if text == "🔮 Передбачення дня":
        msg = _daily_prediction_for(user.id)
        cities = await get_user_cities(user.id)
        return await update.message.reply_text(f"🔮 {msg}", reply_markup=main_keyboard(user.id, cities))

    if text == "⛅ Погода":
        cities = await get_user_cities(user.id)
        if cities:
            return await update.message.reply_text(
                "Натисни кнопку з містом угорі або «🏙 Додати місто».",
                reply_markup=main_keyboard(user.id, cities),
            )
        context.user_data["awaiting_city"] = True
        return await update.message.reply_text("Вкажи своє місто:")

    if text == "🌌Гороскоп":
        return await update.message.reply_text("Обери свій знак:", reply_markup=zodiac_inline_keyboard())

    if text == "💱Курс валют (🇺🇦 банки)":
        context.user_data["fx_sel"] = []
        return await update.message.reply_text("Обери валюти (до 3):", reply_markup=fx_inline_keyboard([]))

    if text == "🐞 Повідомити про баг":
        context.user_data["bug_mode"] = True
        from ..keyboards.common import bug_keyboard
        return await update.message.reply_text(
            "Опиши, що саме не працює / де бачив(-ла) проблему. Можеш додати місто/валюту/час для прикладу.\n"
            "Коли закінчиш — просто надішли повідомлення.\n\n"
            "Щоб повернутись без надсилання — натисни «⬅️ Назад».",
            reply_markup=bug_keyboard(),
        )

    if text == "👑 Адмін":
        if user.id != settings.admin_id:
            return
        from .admin import admin_cmd
        return await admin_cmd(update, context)

    if context.user_data.get("awaiting_city"):
        context.user_data.pop("awaiting_city", None)
        new_city = (text or "").strip().title()
        ok = await add_city(user.id, new_city)
        cities = await get_user_cities(user.id)
        if not ok:
            return await update.message.reply_text(
                "Або місто вже є, або досягнуто ліміт у 3 міста.",
                reply_markup=main_keyboard(user.id, cities),
            )
        return await update.message.reply_text(
            f"Місто {new_city} збережено ✅", reply_markup=main_keyboard(user.id, cities)
        )

# export
get_handlers = lambda: [MessageHandler(filters.TEXT & ~filters.COMMAND, on_text)]