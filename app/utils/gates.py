from telegram import Update
from telegram.ext import ContextTypes
from ..config import settings
from ..db.sqlite import has_phone
from ..keyboards.common import phone_request_keyboard

async def require_phone_gate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    if user.id == settings.admin_id:
        return False
    if not await has_phone(user.id):
        if update.message:
            await update.message.reply_text(
                "Щоб користуватись ботом, поділись номером телефону 👇",
                reply_markup=phone_request_keyboard(),
            )
        elif update.callback_query:
            await update.callback_query.answer("Поділись номером телефону, будь ласка.", show_alert=True)
        return True
    return False