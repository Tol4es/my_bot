from telegram import Update
from telegram.error import BadRequest
from telegram.ext import ContextTypes, CallbackQueryHandler, CallbackContext

import asyncio

from ..utils.gates import require_phone_gate
from ..db.sqlite import is_blocked, del_city
from ..services.horoscope import fetch_horoscope
from ..services.fx import parse_monobank
from ..keyboards.common import fx_inline_keyboard
from .admin import show_page as _admin_show_page, show_user as _admin_show_user
from ..config import settings

async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if await require_phone_gate(update, context):
        return
    q = update.callback_query
    await q.answer()
    data = q.data or ""
    uid = update.effective_user.id

    if await is_blocked(uid):
        return await q.edit_message_text("🚫 Ваш доступ обмежено адміністратором.")

    #гороскоп
    if data.startswith("z:"):
        sign = data.split(":", 1)[1]
        text = await asyncio.to_thread( fetch_horoscope, sign)
        return await q.edit_message_text(text)

    #валюти
    if data.startswith("fx:"):
        sel = context.user_data.get("fx_sel", [])
        action = data.split(":")[1]

        if action == "show":
            if not sel:
                try:
                    return await q.edit_message_text("Обери хоча б одну валюту:", reply_markup=fx_inline_keyboard(sel))
                except BadRequest as e:
                    if "Message is not modified" in str(e):
                        return
                    raise
            text = await asyncio.to_thread( parse_monobank, sel)
            try:
                return await q.edit_message_text(text)
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    return
                raise

        if action == "clear":
            context.user_data["fx_sel"] = []
            try:
                return await q.edit_message_text("Скинуто. Обери валюти:", reply_markup=fx_inline_keyboard([]))
            except BadRequest as e:
                if "Message is not modified" in str(e):
                    return
                raise

        code = action.upper()
        if code in sel:
            sel.remove(code)
        else:
            if len(sel) < 3:
                sel.append(code)
        context.user_data["fx_sel"] = sel
        try:
            return await q.edit_message_text("Обери до 3 валют:", reply_markup=fx_inline_keyboard(sel))
        except BadRequest as e:
            if "Message is not modified" in str(e):
                return
            raise

    #видалення міста
    if data.startswith("delcity:"):
        city = data.split(":", 1)[1]
        await del_city(uid, city)
        return await q.edit_message_text(f"Місто {city} видалено.")

    #адмінка
    if uid == settings.admin_id:
        if data.startswith("user:"):
            target = int(data.split(":")[1])
            return await _admin_show_user(q, context, target)
        if data.startswith("users:back:"):
            page = int(data.split(":")[2])
            return await _admin_show_page(q, context, page)
        if data.startswith("ban:") or data.startswith("unban:"):
            target_id = int(data.split(":")[1])
            from ..db.sqlite import block_user
            await block_user(target_id, data.startswith("ban:"))
            return await _admin_show_user(q, context, target_id)
        if data.startswith("users:page:"):
            page = int(data.split(":")[2])
            return await _admin_show_page(q, context, page)
        if data == "noop":
            return await q.answer()

#export
get_handlers = lambda: [CallbackQueryHandler(on_callback)]