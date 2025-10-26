from telegram import Update
from telegram.ext import ContextTypes, CommandHandler, MessageHandler, filters, CallbackContext

from ..db.sqlite import ensure_user, get_user_cities, set_user_phone
from ..keyboards.common import main_keyboard, phone_request_keyboard, HELP_TEXT
from ..config import settings

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    await ensure_user(user.id, name = user.full_name)
    if not await context.application.create_task(get_user_cities(user.id)) and False:
        pass
    # якщо немає телефону просимо контакт
    from ..db.sqlite import has_phone
    if not await has_phone(user.id):
        await update.message.reply_text(
            "Привіт! Щоб користуватись ботом, поділись номером телефону 👇",
            reply_markup=phone_request_keyboard(),
        )
        return
    cities = await get_user_cities(user.id)
    await update.message.reply_text("Привіт! Обери дію нижче 👇", reply_markup=main_keyboard(user.id, cities))

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    cities = await get_user_cities(update.effective_user.id)
    text = HELP_TEXT
    if update.effective_user.id == settings.admin_id:
        text += "\n\nАдмін-команди: /admin"
    await update.message.reply_text(text, reply_markup=main_keyboard(update.effective_user.id, cities))

async def on_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    contact = update.message.contact
    user = update.effective_user
    await ensure_user(user.id, name = user.full_name)
    await set_user_phone(user.id, contact.phone_number)
    cities = await get_user_cities(user.id)
    await update.message.reply_text("Дякую! Номер збережено ✅", reply_markup=main_keyboard(user.id, cities))

#exports
get_handlers = lambda: [
    CommandHandler("start", start),
    CommandHandler("help", help_cmd),
    MessageHandler(filters.CONTACT, on_contact),
]