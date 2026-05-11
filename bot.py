"""
三盛公司派車 Telegram Bot - 修正版
相容 python-telegram-bot 21.x + Python 3.11+
"""

import os, logging, asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ═══ 設定 ═══
BOT_TOKEN      = os.getenv("BOT_TOKEN", "")
ADMIN_GROUP_ID = int(os.getenv("ADMIN_GROUP_ID", "0"))
DEFAULT_LANG   = os.getenv("DEFAULT_LANG", "km")

# ═══ 多語言 ═══
TEXT = {
    "km": {
        "welcome":    "🚛 *សូមស្វាគមន៍ - ប្រព័ន្ធសំណើរថ្ន*\n\nជ្រើសរើស:",
        "apply":      "📋 ដាក់ពាក្យស្នើរថ្ន",
        "my_req":     "📜 ការស្នើររបស់ខ្ញុំ",
        "help":       "❓ ជំនួយ",
        "ask_type":   "🚗 ជ្រើសប្រភេទ (ចុចច្រើន បន្ទាប់មកចុច ✅ យល់ព្រម):",
        "ask_vtype":  "🚙 ជ្រើសប្រភេទរថ្ន:",
        "ask_date":   "📅 ថ្ងៃចេញ? (ឧ. 2025-06-15)",
        "ask_time":   "🕐 ម៉ោងចេញ? (ឧ. 08:30)",
        "ask_from":   "📍 ចេញពីណា?",
        "ask_to":     "📍 ទៅណា?",
        "ask_pax":    "👥 អ្នកជិះប៉ុន្មាននាក់?",
        "ask_reason": "📝 មូលហេតុ?",
        "ask_name":   "👤 ឈ្មោះ?",
        "ask_phone":  "📞 ទូរស័ព្ទ?",
        "confirm":    "✅ *ពិនិត្យ*\n\n{summary}\n\nត្រឹមត្រូវទេ?",
        "yes":        "✅ ផ្ញើ",
        "no":         "❌ បោះបង់",
        "sent":       "✅ បានទទួល! លេខ: *{ref}*\nរង់ចាំ...",
        "approved":   "🎉 *{ref}* អនុម័ត!\nរថ្ន: {vehicle}\nចំណាំ: {note}",
        "rejected":   "❌ *{ref}* បដិសេធ\nមូលហេតុ: {note}",
        "cancelled":  "❌ បោះបង់",
        "no_req":     "មិនមានការស្នើរ",
        "types":  ["ការងារ","ដឹកកញ្ចប់","ទទួលភ្ញៀវ","ឈប់សម្រាក","ច្បាប់"],
        "vtypes": ["ឡានតូច","ឡានជ្រះ","ឡានធំ","ឡានអគ្គិសនី","ឡានធ្វើការ"],
    },
    "zh": {
        "welcome":    "🚛 *歡迎使用三盛派車系統*\n\n請選擇:",
        "apply":      "📋 申請派車",
        "my_req":     "📜 我的申請",
        "help":       "❓ 使用說明",
        "ask_type":   "🚗 派車種類 (可多選，選完按 ✅ 確認):",
        "ask_vtype":  "🚙 選擇車種:",
        "ask_date":   "📅 派車日期? (例: 2025-06-15)",
        "ask_time":   "🕐 派車時間? (例: 08:30)",
        "ask_from":   "📍 出發地點?",
        "ask_to":     "📍 目的地?",
        "ask_pax":    "👥 搭乘人數?",
        "ask_reason": "📝 申請原因?",
        "ask_name":   "👤 申請人姓名?",
        "ask_phone":  "📞 聯絡電話?",
        "confirm":    "✅ *確認申請資料*\n\n{summary}\n\n確定送出?",
        "yes":        "✅ 確認送出",
        "no":         "❌ 取消",
        "sent":       "✅ 申請已送出!\n編號: *{ref}*\n請等待審核",
        "approved":   "🎉 申請 *{ref}* 已核准!\n車輛: {vehicle}\n備註: {note}",
        "rejected":   "❌ 申請 *{ref}* 已拒絕\n原因: {note}",
        "cancelled":  "❌ 已取消",
        "no_req":     "目前沒有申請紀錄",
        "types":  ["洽公","包裹快遞","接送客人","休假","請假"],
        "vtypes": ["麵包車","水洗車","大貨車","電動車","商務車"],
    },
    "en": {
        "welcome":    "🚛 *Sanshen Dispatch System*\n\nChoose:",
        "apply":      "📋 Request Vehicle",
        "my_req":     "📜 My Requests",
        "help":       "❓ Help",
        "ask_type":   "🚗 Trip type (select all, then tap ✅ Confirm):",
        "ask_vtype":  "🚙 Vehicle type:",
        "ask_date":   "📅 Date? (e.g. 2025-06-15)",
        "ask_time":   "🕐 Time? (e.g. 08:30)",
        "ask_from":   "📍 From?",
        "ask_to":     "📍 To?",
        "ask_pax":    "👥 Passengers?",
        "ask_reason": "📝 Reason?",
        "ask_name":   "👤 Your name?",
        "ask_phone":  "📞 Phone?",
        "confirm":    "✅ *Confirm Request*\n\n{summary}\n\nSubmit?",
        "yes":        "✅ Submit",
        "no":         "❌ Cancel",
        "sent":       "✅ Submitted!\nRef: *{ref}*\nAwaiting approval.",
        "approved":   "🎉 Request *{ref}* APPROVED!\nVehicle: {vehicle}\nNote: {note}",
        "rejected":   "❌ Request *{ref}* REJECTED\nReason: {note}",
        "cancelled":  "❌ Cancelled",
        "no_req":     "No requests found",
        "types":  ["Business","Delivery","Guest Pickup","Leave","Sick Leave"],
        "vtypes": ["Minivan","Truck","Big Truck","EV Car","Business Car"],
    }
}

def t(key, lang=None, **kw):
    lang = lang or DEFAULT_LANG
    v = TEXT.get(lang, TEXT["zh"]).get(key, key)
    return v.format(**kw) if kw else v

# ═══ 記憶體儲存 ═══
store: dict = {}
counter = [0]

def new_ref():
    counter[0] += 1
    return f"D{datetime.now().strftime('%m%d')}-{counter[0]:03d}"

def save_req(data):
    ref = new_ref()
    data.update({"ref": ref, "status": "pending", "ts": datetime.now().strftime("%Y-%m-%d %H:%M")})
    store[ref] = data
    return ref

def update_req(ref, status, vehicle, note):
    if ref in store:
        store[ref].update({"status": status, "vehicle": vehicle, "note": note})

# ═══ 對話狀態 ═══
SEL_TYPE, SEL_VTYPE = range(2)
D_DATE, D_TIME, D_FROM, D_TO, D_PAX, D_REASON, D_NAME, D_PHONE, CONFIRM = range(2, 11)
APR_VEH, APR_NOTE, REJ_NOTE = range(11, 14)

# ═══ 鍵盤 ═══
def lang_kb():
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("ភាសាខ្មែរ", callback_data="lang_km"),
        InlineKeyboardButton("中文", callback_data="lang_zh"),
        InlineKeyboardButton("English", callback_data="lang_en"),
    ]])

def menu_kb(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("apply", lang), callback_data="m_apply")],
        [InlineKeyboardButton(t("my_req", lang), callback_data="m_mine"),
         InlineKeyboardButton(t("help", lang), callback_data="m_help")],
    ])

def type_kb(selected, lang):
    rows = []
    for i, tp in enumerate(t("types", lang)):
        mark = "✅ " if tp in selected else ""
        rows.append([InlineKeyboardButton(f"{mark}{tp}", callback_data=f"tp_{i}")])
    rows.append([InlineKeyboardButton("✅ យល់ព្រម / 確認 / Confirm", callback_data="tp_done")])
    return InlineKeyboardMarkup(rows)

def vtype_kb(lang):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(v, callback_data=f"vt_{i}")]
        for i, v in enumerate(t("vtypes", lang))
    ])

def confirm_kb(lang):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton(t("yes", lang), callback_data="cf_yes"),
        InlineKeyboardButton(t("no", lang), callback_data="cf_no"),
    ]])

def admin_kb(ref):
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 核准", callback_data=f"apr_{ref}"),
        InlineKeyboardButton("❌ 拒絕", callback_data=f"rej_{ref}"),
    ]])

def make_summary(d, lang):
    types_str = ", ".join(d.get("types", []))
    return (
        f"📋 {types_str}\n"
        f"🚙 {d.get('vtype','')}\n"
        f"📅 {d.get('date','')} {d.get('time','')}\n"
        f"📍 {d.get('from_loc','')} → {d.get('to_loc','')}\n"
        f"👥 {d.get('pax','')} {'នាក់' if lang=='km' else '人' if lang=='zh' else 'pax'}\n"
        f"📝 {d.get('reason','')}\n"
        f"👤 {d.get('name','')} | {d.get('phone','')}"
    )

def admin_msg(ref, d):
    types_str = ", ".join(d.get("types", []))
    return (
        f"🔔 *新派車申請 #{ref}*\n\n"
        f"👤 {d.get('name','')} ({d.get('phone','')})\n"
        f"📋 {types_str} | 🚙 {d.get('vtype','')}\n"
        f"📅 {d.get('date','')} {d.get('time','')}\n"
        f"📍 {d.get('from_loc','')} → {d.get('to_loc','')}\n"
        f"👥 {d.get('pax','')} 人\n"
        f"📝 {d.get('reason','')}\n"
        f"🕐 {d.get('ts','')}"
    )

# ═══ 員工端 ═══
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    await update.message.reply_text(
        "🌐 ជ្រើសភាសា / 選擇語言 / Choose language:",
        reply_markup=lang_kb()
    )

async def cb_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = q.data.replace("lang_", "")
    ctx.user_data["lang"] = lang
    await q.edit_message_text(t("welcome", lang), parse_mode=ParseMode.MARKDOWN, reply_markup=menu_kb(lang))

async def cb_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    act = q.data.replace("m_", "")

    if act == "apply":
        ctx.user_data["d"] = {"types": []}
        await q.edit_message_text(t("ask_type", lang), parse_mode=ParseMode.MARKDOWN,
                                  reply_markup=type_kb([], lang))
        return SEL_TYPE

    if act == "mine":
        uid = str(q.from_user.id)
        mine = [v for v in store.values() if str(v.get("uid","")) == uid]
        if not mine:
            await q.edit_message_text(t("no_req", lang), reply_markup=menu_kb(lang))
        else:
            st = {"pending":"⏳","approved":"✅","rejected":"❌"}
            lines = [f"{st.get(r['status'],'?')} {r['ref']} {r.get('to_loc','')} {r.get('date','')}" for r in mine[-5:]]
            await q.edit_message_text("\n".join(lines), reply_markup=menu_kb(lang))
        return ConversationHandler.END

    if act == "help":
        msgs = {
            "km": "1️⃣ ចុច 'ដាក់ពាក្យ'\n2️⃣ ជ្រើសប្រភេទ\n3️⃣ បំពេញព័ត៌មាន\n4️⃣ រង់ចាំការអនុម័ត",
            "zh": "1️⃣ 點「申請派車」\n2️⃣ 選種類\n3️⃣ 填資料\n4️⃣ 等管理員審核",
            "en": "1️⃣ Tap Request\n2️⃣ Choose type\n3️⃣ Fill details\n4️⃣ Wait for approval",
        }
        await q.edit_message_text(msgs.get(lang, msgs["zh"]), reply_markup=menu_kb(lang))
        return ConversationHandler.END

async def cb_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    d = ctx.user_data.setdefault("d", {"types": []})

    if q.data == "tp_done":
        if not d["types"]:
            await q.answer("請選擇至少一項!", show_alert=True)
            return SEL_TYPE
        await q.edit_message_text(t("ask_vtype", lang), reply_markup=vtype_kb(lang))
        return SEL_VTYPE

    idx = int(q.data.replace("tp_", ""))
    chosen = t("types", lang)[idx]
    if chosen in d["types"]:
        d["types"].remove(chosen)
    else:
        d["types"].append(chosen)
    await q.edit_message_text(t("ask_type", lang), parse_mode=ParseMode.MARKDOWN,
                              reply_markup=type_kb(d["types"], lang))
    return SEL_TYPE

async def cb_vtype(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    idx = int(q.data.replace("vt_", ""))
    ctx.user_data["d"]["vtype"] = t("vtypes", lang)[idx]
    await q.edit_message_text(t("ask_date", lang))
    return D_DATE

async def get_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    text = update.message.text.strip()
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ 格式錯誤，請輸入 YYYY-MM-DD")
        return D_DATE
    ctx.user_data["d"]["date"] = text
    await update.message.reply_text(t("ask_time", lang))
    return D_TIME

async def get_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["d"]["time"] = update.message.text.strip()
    await update.message.reply_text(t("ask_from", lang))
    return D_FROM

async def get_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["d"]["from_loc"] = update.message.text.strip()
    await update.message.reply_text(t("ask_to", lang))
    return D_TO

async def get_to(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["d"]["to_loc"] = update.message.text.strip()
    await update.message.reply_text(t("ask_pax", lang))
    return D_PAX

async def get_pax(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ 請輸入數字")
        return D_PAX
    ctx.user_data["d"]["pax"] = text
    await update.message.reply_text(t("ask_reason", lang))
    return D_REASON

async def get_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["d"]["reason"] = update.message.text.strip()
    await update.message.reply_text(t("ask_name", lang))
    return D_NAME

async def get_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["d"]["name"] = update.message.text.strip()
    await update.message.reply_text(t("ask_phone", lang))
    return D_PHONE

async def get_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["d"]["phone"] = update.message.text.strip()
    ctx.user_data["d"]["uid"] = update.message.from_user.id
    summary = make_summary(ctx.user_data["d"], lang)
    await update.message.reply_text(
        t("confirm", lang, summary=summary),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=confirm_kb(lang)
    )
    return CONFIRM

async def cb_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    lang = ctx.user_data.get("lang", DEFAULT_LANG)

    if q.data == "cf_no":
        await q.edit_message_text(t("cancelled", lang))
        return ConversationHandler.END

    d = ctx.user_data["d"]
    ref = save_req(d)
    await q.edit_message_text(t("sent", lang, ref=ref), parse_mode=ParseMode.MARKDOWN)

    if ADMIN_GROUP_ID:
        try:
            await ctx.bot.send_message(
                ADMIN_GROUP_ID,
                admin_msg(ref, d),
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=admin_kb(ref)
            )
        except Exception as e:
            log.error(f"admin notify: {e}")

    return ConversationHandler.END

async def do_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END

# ═══ 管理員端 ═══
async def cb_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ref = q.data.replace("apr_", "")
    ctx.user_data["ref"] = ref
    await q.edit_message_text(
        f"✅ 核准 *{ref}*\n\n請輸入指派車輛（或輸入「無」）:",
        parse_mode=ParseMode.MARKDOWN
    )
    return APR_VEH

async def apr_vehicle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["vehicle"] = update.message.text.strip()
    await update.message.reply_text("請輸入備註（或輸入「無」）:")
    return APR_NOTE

async def apr_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ref = ctx.user_data.get("ref", "")
    vehicle = ctx.user_data.get("vehicle", "無")
    note = update.message.text.strip()
    update_req(ref, "approved", vehicle, note)

    d = store.get(ref, {})
    uid = d.get("uid")
    await update.message.reply_text(f"✅ 已核准 {ref}")

    if uid:
        try:
            await ctx.bot.send_message(
                uid,
                t("approved", DEFAULT_LANG, ref=ref, vehicle=vehicle, note=note or "無"),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            log.error(f"notify user: {e}")
            await update.message.reply_text("⚠️ 無法通知申請人（需要先對 Bot 發訊息）")

    return ConversationHandler.END

async def cb_reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    ref = q.data.replace("rej_", "")
    ctx.user_data["ref"] = ref
    await q.edit_message_text(
        f"❌ 拒絕 *{ref}*\n\n請輸入拒絕原因:",
        parse_mode=ParseMode.MARKDOWN
    )
    return REJ_NOTE

async def rej_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ref = ctx.user_data.get("ref", "")
    reason = update.message.text.strip()
    update_req(ref, "rejected", "", reason)

    d = store.get(ref, {})
    uid = d.get("uid")
    await update.message.reply_text(f"❌ 已拒絕 {ref}")

    if uid:
        try:
            await ctx.bot.send_message(
                uid,
                t("rejected", DEFAULT_LANG, ref=ref, note=reason),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            log.error(f"notify user: {e}")

    return ConversationHandler.END

# ═══ 查詢指令 ═══
async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    today = datetime.now().strftime("%Y-%m")
    recs = [v for v in store.values() if v.get("date", "").startswith(today)]
    if not recs:
        await update.message.reply_text("📭 本月尚無派車記錄")
        return
    st = {"pending":"⏳","approved":"✅","rejected":"❌"}
    lines = ["📊 *本月派車清單*\n"]
    for r in recs:
        lines.append(f"{st.get(r['status'],'?')} {r['ref']} | {r.get('date','')} | {r.get('name','')} | {r.get('to_loc','')}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    recs = [v for v in store.values() if v.get("status") == "pending"]
    if not recs:
        await update.message.reply_text("✅ 目前沒有待審核申請")
        return
    lines = ["⏳ *待審核申請*\n"]
    for r in recs:
        lines.append(f"• {r['ref']} | {r.get('date','')} | {r.get('name','')} → {r.get('to_loc','')}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "*管理員指令*\n\n/today — 本月紀錄\n/pending — 待審核\n/admin — 說明",
        parse_mode=ParseMode.MARKDOWN
    )

# ═══ 主程式 ═══
def main():
    if not BOT_TOKEN:
        log.error("BOT_TOKEN 未設定!")
        return

    app = Application.builder().token(BOT_TOKEN).build()

    # 員工申請流程
    apply_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_menu, pattern="^m_")],
        states={
            SEL_TYPE:  [CallbackQueryHandler(cb_type,  pattern="^tp_")],
            SEL_VTYPE: [CallbackQueryHandler(cb_vtype, pattern="^vt_")],
            D_DATE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_date)],
            D_TIME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_time)],
            D_FROM:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_from)],
            D_TO:      [MessageHandler(filters.TEXT & ~filters.COMMAND, get_to)],
            D_PAX:     [MessageHandler(filters.TEXT & ~filters.COMMAND, get_pax)],
            D_REASON:  [MessageHandler(filters.TEXT & ~filters.COMMAND, get_reason)],
            D_NAME:    [MessageHandler(filters.TEXT & ~filters.COMMAND, get_name)],
            D_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, get_phone)],
            CONFIRM:   [CallbackQueryHandler(cb_confirm, pattern="^cf_")],
        },
        fallbacks=[CommandHandler("cancel", do_cancel)],
    )

    # 管理員核准流程
    approve_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_approve, pattern="^apr_")],
        states={
            APR_VEH:  [MessageHandler(filters.TEXT & ~filters.COMMAND, apr_vehicle)],
            APR_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, apr_note)],
        },
        fallbacks=[],
    )

    # 管理員拒絕流程
    reject_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_reject, pattern="^rej_")],
        states={
            REJ_NOTE: [MessageHandler(filters.TEXT & ~filters.COMMAND, rej_note)],
        },
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(cb_lang, pattern="^lang_"))
    app.add_handler(apply_conv)
    app.add_handler(approve_conv)
    app.add_handler(reject_conv)
    app.add_handler(CommandHandler("today",   cmd_today))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("admin",   cmd_admin))

    log.info("🚛 Bot 啟動!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
