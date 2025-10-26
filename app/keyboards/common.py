from telegram import (
    ReplyKeyboardMarkup, ReplyKeyboardRemove,
    InlineKeyboardButton, InlineKeyboardMarkup, KeyboardButton
)
from ..config import settings

ZODIACS = [
("♈ Овен", "aries"), ("♉ Телець", "taurus"), ("♊ Близнюки", "gemini"),
("♋ Рак", "cancer"), ("♌ Лев", "leo"), ("♍ Діва", "virgo"),
("♎ Терези", "libra"), ("♏ Скорпіон", "scorpio"), ("♐ Стрілець", "sagittarius"),
("♑ Козоріг", "capricorn"), ("♒ Водолій", "aquarius"), ("♓ Риби", "pisces"),
]

FX_SUPPORTED = ["USD", "EUR", "PLN"]

_HELP = (
    "Я бот.\n"
    "Меню внизу — це *клавіатура*.\n"
    "⛅ Погода: натисни кнопку з містом або додай нове через «Додати місто»\n"
    "🌌 Гороскоп на сьогодні: обери свій знак\n"
    "🔮 Передбачення дня: одне випадкове побажання\n"
    "💱 Курс валют (банківський, 🇺🇦 Monobank)\n"
    "🐞 Повідомити про баг — напиши, що саме не працює\n"
    "«ℹ️ Допомога» — щоби побачити цей текст знову\n"
    "«❌ Прибрати клавіатуру» — щоби сховати меню\n"
)

HELP_TEXT = _HELP

def phone_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [[KeyboardButton(text="📱 Поділитись телефоном", request_contact=True)]],
        resize_keyboard=True,
    )

def bug_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup([["⬅️ Назад"]], resize_keyboard=True, one_time_keyboard=True)

def main_keyboard(user_id: int, cities: list[str] | None = None) -> ReplyKeyboardMarkup:
    rows = [
        ["👋 Привітатись", "ℹ️Допомога"],
        ["⛅ Погода", "🌌Гороскоп", "🔮 Передбачення дня"],
        ["🏙 Додати місто", "🗑️ Видалити місто"],
        ["💱Курс валют (🇺🇦 банки)", "🐞 Повідомити про баг"],
        ["❌Прибрати клавіатуру"],
    ]
    if cities:
        rows.insert(0, [f"🏙 {c}" for c in cities])
    if user_id == settings.admin_id:
        rows.insert(0, ["👑 Адмін"])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def zodiac_inline_keyboard() -> InlineKeyboardMarkup:
    rows, row = [], []
    for i, (title, code) in enumerate(ZODIACS, start=1):
        row.append(InlineKeyboardButton(title, callback_data=f"z:{code}"))
        if i % 4 == 0:
            rows.append(row); row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)

def fx_inline_keyboard(selected: list[str]) -> InlineKeyboardMarkup:
    def label(code: str) -> str:
        return f"{'✅' if code in selected else '☑️'} {code}"
    rows = [
        [InlineKeyboardButton(label(c), callback_data=f"fx:{c}") for c in FX_SUPPORTED],
        [InlineKeyboardButton("✅Показати", callback_data="fx:show"),
         InlineKeyboardButton("❌Скинути", callback_data="fx:clear")]
    ]
    return InlineKeyboardMarkup(rows)