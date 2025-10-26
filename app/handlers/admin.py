import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes, CommandHandler

from ..config import settings
from ..db.sqlite import query_one, query, block_user

PAGE_SIZE = 10

def _users_page_kb(items: list[sqlite3.Row], page: int, total: int) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for r in items:
        label = f"👤 {r['name'] or '-'} • {r['id']} • {r['phone'] or '—'}"
        rows.append([InlineKeyboardButton(label, callback_data=f"user:{r['id']}")])
        if r["blocked"]:
            rows.append([InlineKeyboardButton("✅ Розблокувати", callback_data=f"unban:{r['id']}")])
        else:
            rows.append([InlineKeyboardButton("🚫 Заблокувати", callback_data=f"ban:{r['id']}")])
    nav: list[InlineKeyboardButton] = []
    pages = (total + PAGE_SIZE - 1) // PAGE_SIZE
    if pages > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"users:page:{page-1}"))
    nav.append(InlineKeyboardButton(f"{page+1}/{max(pages,1)}", callback_data="noop"))
    if page+1 < pages:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"users:page:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)

async def admin_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    if update.effective_user.id != settings.admin_id:
        return await update.message.reply_text("Лише для адміністратора.")
    total_row = await query_one("SELECT COUNT(*) AS c FROM users")
    total = total_row["c"] if total_row else 0
    rows = await query(
        "SELECT id, name, phone, blocked FROM users ORDER BY joined DESC LIMIT ? OFFSET ?",
        (PAGE_SIZE, PAGE_SIZE * page),
    )
    context.user_data["admin_users_page"] = page
    kb = _users_page_kb(rows, page, total)
    await update.message.reply_text("👑 Адмін-панель — користувачі:", reply_markup=kb)

async def _admin_show_page(q, context, page: int):
    total_row = await query_one("SELECT COUNT(*) AS c FROM users")
    total = total_row["c"] if total_row else 0
    rows = await query(
        "SELECT id, name, phone, blocked FROM users ORDER BY joined DESC LIMIT ? OFFSET ?",
        (PAGE_SIZE, PAGE_SIZE * page),
    )
    context.user_data["admin_users_page"] = page
    kb = _users_page_kb(rows, page, total)
    await q.edit_message_reply_markup(reply_markup=kb)

async def _admin_show_user(q, context, user_id: int):
    row = await query_one("SELECT id, name, phone, blocked, joined FROM users WHERE id = ?", (user_id,))
    if not row:
        return await q.answer("Користувача не знайдено", show_alert=True)

    cities = await query("SELECT city FROM cities WHERE user_id=? ORDER BY rowid", (user_id,))
    cities_txt = ", ".join(r["city"] for r in cities) if cities else "—"
    bugs = await query_one("SELECT COUNT(*) AS c FROM bugs WHERE user_id=?", (user_id,))
    bugs_n = bugs["c"] if bugs else 0

    text = (
        "🗂 <b>Профіль користувача</b>\n"
        f"👤 Ім’я: {row['name'] or '—'}\n"
        f"🪪 ID: <code>{row['id']}</code>\n"
        f"📞 Телефон: {row['phone'] or '—'}\n"
        f"🗓 Приєднався: {row['joined'] or '—'}\n"
        f"🏙 Міста: {cities_txt}\n"
        f"🐞 Репортів: {bugs_n}\n"
        f"🚫 Статус: {'заблокований' if row['blocked'] else 'активний'}"
    )

    page = context.user_data.get("admin_users_page", 0)
    kb: list[list[InlineKeyboardButton]] = []
    if row["blocked"]:
        kb.append([InlineKeyboardButton("✅ Розблокувати", callback_data=f"unban:{row['id']}")])
    else:
        kb.append([InlineKeyboardButton("🚫 Заблокувати", callback_data=f"ban:{row['id']}")])
    kb.append([InlineKeyboardButton("⬅️ Назад до списку", callback_data=f"users:back:{page}")])

    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(kb), parse_mode="HTML")

# exports
get_handlers = lambda: [CommandHandler("admin", admin_cmd)]
show_page = _admin_show_page
show_user = _admin_show_user