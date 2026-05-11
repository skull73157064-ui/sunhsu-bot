"""
三盛公司派車 Telegram Bot
========================
功能：
  - 員工用按鈕申請派車（支援高棉文/中文/英文）
  - 自動通知管理員群組
  - 管理員一鍵核准或拒絕
  - 自動通知申請人結果
  - 所有紀錄存入 Google Sheet（免費）
  - 管理員可查詢今日/本週派車清單

部署：完全免費（Render / Railway 免費方案）
需要：Python 3.10+、Telegram Bot Token（免費）
"""

import os, json, logging, asyncio
from datetime import datetime, timedelta
from typing import Optional
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters, ContextTypes
)
from telegram.constants import ParseMode

logging.basicConfig(format="%(asctime)s %(levelname)s %(message)s", level=logging.INFO)
log = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════
# 設定 — 填入你的資料
# ═══════════════════════════════════════════════════════════
BOT_TOKEN        = os.getenv("BOT_TOKEN", "你的Bot Token")
ADMIN_GROUP_ID   = int(os.getenv("ADMIN_GROUP_ID", "-100xxxxxxxxx"))   # 管理員群組 ID（負數）
GOOGLE_SHEET_ID  = os.getenv("GOOGLE_SHEET_ID", "你的試算表ID")
GOOGLE_CREDS_JSON = os.getenv("GOOGLE_CREDS_JSON", "")  # JSON 字串或檔案路徑

# 語言設定（預設顯示給員工的語言）
# "km" = ភាសាខ្មែរ（高棉文）  "zh" = 中文  "en" = English
DEFAULT_LANG = os.getenv("DEFAULT_LANG", "km")

# ═══════════════════════════════════════════════════════════
# 多語言文字
# ═══════════════════════════════════════════════════════════
TEXT = {
    "km": {
        "welcome":       "🚛 *សូមស្វាគមន៍មកកាន់ប្រព័ន្ធសំណើរថ្ន*\n\nជ្រើសរើសអ្វីដែលអ្នកចង់ធ្វើ:",
        "apply":         "📋 ដាក់ពាក្យស្នើរថ្ន",
        "my_requests":   "📜 ការស្នើររបស់ខ្ញុំ",
        "help":          "❓ ជំនួយ",
        "ask_type":      "🚗 *ស្នើររថ្ន*\n\nជ្រើសប្រភេទ (អាចជ្រើសច្រើន):",
        "ask_date":      "📅 ថ្ងៃចេញ? (ឧ. 2025-06-15)",
        "ask_time":      "🕐 ម៉ោងចេញ? (ឧ. 08:30)",
        "ask_from":      "📍 ចេញពីណា?",
        "ask_to":        "📍 ទៅណា?",
        "ask_pax":       "👥 អ្នកជិះប៉ុន្មាននាក់?",
        "ask_reason":    "📝 មូលហេតុ?",
        "ask_name":      "👤 ឈ្មោះអ្នកស្នើ?",
        "ask_phone":     "📞 លេខទូរស័ព្ទ?",
        "confirm_title": "✅ *ពិនិត្យព័ត៌មាន*",
        "confirm_yes":   "✅ បញ្ជូន",
        "confirm_no":    "❌ បោះបង់",
        "submitted":     "✅ ការស្នើររបស់អ្នកត្រូវបានទទួល!\nលេខ: *{ref}*\nរង់ចាំការអនុម័ត",
        "approved_user": "🎉 ការស្នើររបស់អ្នក *{ref}* ត្រូវបានអនុម័ត!\nរថ្ន: {vehicle}\nចំណាំ: {note}",
        "rejected_user": "❌ ការស្នើររបស់អ្នក *{ref}* ត្រូវបានបដិសេធ\nមូលហេតុ: {note}",
        "done":          "ការស្នើរបានបញ្ចប់",
        "cancelled":     "❌ បានបោះបង់",
        "no_requests":   "មិនមានការស្នើរ",
        "dispatch_types": ["ការងារ", "ដឹកកញ្ចប់", "ទទួលភ្ញៀវ", "ឈប់សម្រាក", "ច្បាប់"],
        "vehicle_types":  ["ឡានតូច", "ឡានជ្រះ", "ឡានធំ", "ឡានអគ្គិសនី", "ឡានធ្វើការ"],
    },
    "zh": {
        "welcome":       "🚛 *歡迎使用三盛派車系統*\n\n請選擇操作:",
        "apply":         "📋 申請派車",
        "my_requests":   "📜 我的申請紀錄",
        "help":          "❓ 使用說明",
        "ask_type":      "🚗 *派車種類*\n\n請選擇（可多選，選完請按「確認」）:",
        "ask_date":      "📅 派車日期？（例如 2025-06-15）",
        "ask_time":      "🕐 派車時間？（例如 08:30）",
        "ask_from":      "📍 出發地點？",
        "ask_to":        "📍 目的地？",
        "ask_pax":       "👥 搭乘人數？",
        "ask_reason":    "📝 申請原因？",
        "ask_name":      "👤 申請人姓名？",
        "ask_phone":     "📞 聯絡電話？",
        "confirm_title": "✅ *確認申請資料*",
        "confirm_yes":   "✅ 確認送出",
        "confirm_no":    "❌ 取消",
        "submitted":     "✅ 申請已送出！\n編號: *{ref}*\n請等待管理員審核",
        "approved_user": "🎉 您的申請 *{ref}* 已核准！\n指派車輛: {vehicle}\n備註: {note}",
        "rejected_user": "❌ 您的申請 *{ref}* 已被拒絕\n原因: {note}",
        "done":          "申請完成",
        "cancelled":     "❌ 已取消",
        "no_requests":   "目前沒有申請紀錄",
        "dispatch_types": ["洽公", "包裹快遞", "接送客人", "休假", "請假"],
        "vehicle_types":  ["麵包車", "水洗車", "大貨車", "電動車", "商務車"],
    },
    "en": {
        "welcome":       "🚛 *Welcome to Sanshen Dispatch System*\n\nChoose an action:",
        "apply":         "📋 Request Vehicle",
        "my_requests":   "📜 My Requests",
        "help":          "❓ Help",
        "ask_type":      "🚗 *Trip Type*\n\nSelect all that apply, then tap Confirm:",
        "ask_date":      "📅 Date? (e.g. 2025-06-15)",
        "ask_time":      "🕐 Time? (e.g. 08:30)",
        "ask_from":      "📍 Departure location?",
        "ask_to":        "📍 Destination?",
        "ask_pax":       "👥 Number of passengers?",
        "ask_reason":    "📝 Reason for trip?",
        "ask_name":      "👤 Your name?",
        "ask_phone":     "📞 Phone number?",
        "confirm_title": "✅ *Confirm Request*",
        "confirm_yes":   "✅ Submit",
        "confirm_no":    "❌ Cancel",
        "submitted":     "✅ Request submitted!\nRef: *{ref}*\nAwaiting approval.",
        "approved_user": "🎉 Request *{ref}* APPROVED!\nVehicle: {vehicle}\nNote: {note}",
        "rejected_user": "❌ Request *{ref}* REJECTED\nReason: {note}",
        "done":          "Done",
        "cancelled":     "❌ Cancelled",
        "no_requests":   "No requests found",
        "dispatch_types": ["Business", "Delivery", "Guest Pickup", "Leave", "Sick Leave"],
        "vehicle_types":  ["Minivan", "Truck (wash)", "Big Truck", "EV Car", "Business Car"],
    }
}

def t(key: str, lang: str = DEFAULT_LANG, **kw) -> str:
    """Get translated text."""
    txt = TEXT.get(lang, TEXT["zh"]).get(key, key)
    return txt.format(**kw) if kw else txt

# ═══════════════════════════════════════════════════════════
# Google Sheets 連接
# ═══════════════════════════════════════════════════════════
_sheet = None

def get_sheet():
    global _sheet
    if _sheet: return _sheet
    try:
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        if GOOGLE_CREDS_JSON.startswith("{"):
            import tempfile, json as _json
            creds_dict = _json.loads(GOOGLE_CREDS_JSON)
            with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
                _json.dump(creds_dict, f); f.flush()
                creds = ServiceAccountCredentials.from_json_keyfile_name(f.name, scope)
        else:
            creds = ServiceAccountCredentials.from_json_keyfile_name(GOOGLE_CREDS_JSON or "credentials.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(GOOGLE_SHEET_ID)
        # 確保「派車紀錄」工作表存在
        try:
            _sheet = sheet.worksheet("派車紀錄")
        except:
            _sheet = sheet.add_worksheet("派車紀錄", rows=1000, cols=20)
            headers = ["編號","申請時間","申請人","電話","Telegram ID","派車種類","車種","日期","時間","出發地","目的地","人數","原因","狀態","指派車輛","審核備註","審核時間","審核人"]
            _sheet.append_row(headers)
        log.info("Google Sheet connected ✅")
    except Exception as e:
        log.warning(f"Google Sheet not connected: {e}. Using memory only.")
        _sheet = None
    return _sheet

# 記憶體儲存（Google Sheet 連不上時的備份）
_memory_store: dict[str, dict] = {}

def gen_ref() -> str:
    now = datetime.now()
    count = len(_memory_store) + 1
    return f"D{now.strftime('%m%d')}-{count:03d}"

def save_request(data: dict) -> str:
    ref = gen_ref()
    data["ref"] = ref
    data["status"] = "pending"
    data["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
    _memory_store[ref] = data

    sheet = get_sheet()
    if sheet:
        try:
            row = [
                ref, data["created_at"], data.get("name",""), data.get("phone",""),
                str(data.get("user_id","")), ", ".join(data.get("types",[])),
                data.get("vehicle_type",""), data.get("date",""), data.get("time",""),
                data.get("from_loc",""), data.get("to_loc",""), data.get("pax",""),
                data.get("reason",""), "待審核", "", "", "", ""
            ]
            sheet.append_row(row)
        except Exception as e:
            log.error(f"Sheet write error: {e}")
    return ref

def update_request(ref: str, status: str, vehicle: str, note: str, admin_name: str):
    if ref in _memory_store:
        _memory_store[ref].update({"status": status, "vehicle": vehicle, "note": note})
    sheet = get_sheet()
    if sheet:
        try:
            records = sheet.get_all_records()
            for i, row in enumerate(records, start=2):
                if row.get("編號") == ref:
                    now = datetime.now().strftime("%Y-%m-%d %H:%M")
                    sheet.update(f"N{i}", status)
                    sheet.update(f"O{i}", vehicle)
                    sheet.update(f"P{i}", note)
                    sheet.update(f"Q{i}", now)
                    sheet.update(f"R{i}", admin_name)
                    break
        except Exception as e:
            log.error(f"Sheet update error: {e}")

def get_today_requests() -> list:
    today = datetime.now().strftime("%Y-%m-%d")
    results = []
    sheet = get_sheet()
    if sheet:
        try:
            records = sheet.get_all_records()
            results = [r for r in records if r.get("日期","").startswith(today[:7])]
            return results[-20:]
        except: pass
    return [v for v in _memory_store.values() if v.get("date","").startswith(today[:7])]

# ═══════════════════════════════════════════════════════════
# 對話狀態
# ═══════════════════════════════════════════════════════════
(CHOOSING_TYPES, CHOOSING_VEHICLE, ASKING_DATE, ASKING_TIME,
 ASKING_FROM, ASKING_TO, ASKING_PAX, ASKING_REASON,
 ASKING_NAME, ASKING_PHONE, CONFIRMING) = range(11)

APPROVE_ASKING_VEHICLE = 50
APPROVE_ASKING_NOTE    = 51
REJECT_ASKING_REASON   = 52

# ═══════════════════════════════════════════════════════════
# 工具函式
# ═══════════════════════════════════════════════════════════
def main_menu_kb(lang: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(t("apply", lang), callback_data="menu_apply")],
        [InlineKeyboardButton(t("my_requests", lang), callback_data="menu_mine"),
         InlineKeyboardButton(t("help", lang), callback_data="menu_help")],
    ])

def lang_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("ភាសាខ្មែរ", callback_data="lang_km"),
        InlineKeyboardButton("中文", callback_data="lang_zh"),
        InlineKeyboardButton("English", callback_data="lang_en"),
    ]])

def type_kb(selected: list, lang: str) -> InlineKeyboardMarkup:
    types = t("dispatch_types", lang)
    rows = []
    for i, tp in enumerate(types):
        mark = "✅ " if tp in selected else ""
        rows.append([InlineKeyboardButton(f"{mark}{tp}", callback_data=f"type_{i}")])
    rows.append([
        InlineKeyboardButton("✅ យល់ព្រម / 確認 / Confirm", callback_data="type_done")
    ])
    return InlineKeyboardMarkup(rows)

def vehicle_kb(lang: str) -> InlineKeyboardMarkup:
    vtypes = t("vehicle_types", lang)
    rows = [[InlineKeyboardButton(v, callback_data=f"vtype_{i}")] for i, v in enumerate(vtypes)]
    return InlineKeyboardMarkup(rows)

def confirm_summary(data: dict, lang: str) -> str:
    types_str = ", ".join(data.get("types", []))
    lines = [
        t("confirm_title", lang),
        f"",
        f"📋 {types_str}",
        f"🚗 {data.get('vehicle_type','')}",
        f"📅 {data.get('date','')} {data.get('time','')}",
        f"📍 {data.get('from_loc','')} → {data.get('to_loc','')}",
        f"👥 {data.get('pax','')} ៣",
        f"📝 {data.get('reason','')}",
        f"👤 {data.get('name','')} | {data.get('phone','')}",
    ]
    return "\n".join(lines)

def admin_notify_text(ref: str, data: dict) -> str:
    types_str = ", ".join(data.get("types", []))
    return (
        f"🔔 *新派車申請 #{ref}*\n\n"
        f"👤 {data.get('name','')} ({data.get('phone','')})\n"
        f"📋 {types_str} | 🚗 {data.get('vehicle_type','')}\n"
        f"📅 {data.get('date','')} {data.get('time','')}\n"
        f"📍 {data.get('from_loc','')} → {data.get('to_loc','')}\n"
        f"👥 {data.get('pax','')} 人\n"
        f"📝 {data.get('reason','')}\n"
        f"🕐 申請時間: {data.get('created_at','')}"
    )

def admin_action_kb(ref: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ 核准", callback_data=f"approve_{ref}"),
        InlineKeyboardButton("❌ 拒絕", callback_data=f"reject_{ref}"),
    ]])

# ═══════════════════════════════════════════════════════════
# HANDLERS — 員工端
# ═══════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data.clear()
    ctx.user_data["lang"] = DEFAULT_LANG
    await update.message.reply_text(
        "🌐 ជ្រើសភាសា / 選擇語言 / Choose language:",
        reply_markup=lang_kb()
    )

async def cb_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lang = q.data.replace("lang_", "")
    ctx.user_data["lang"] = lang
    await q.edit_message_text(
        t("welcome", lang),
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb(lang)
    )

async def cb_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    action = q.data.replace("menu_", "")

    if action == "apply":
        ctx.user_data["apply"] = {"types": []}
        await q.edit_message_text(
            t("ask_type", lang), parse_mode=ParseMode.MARKDOWN,
            reply_markup=type_kb([], lang)
        )
        return CHOOSING_TYPES

    if action == "mine":
        user_id = str(q.from_user.id)
        mine = [v for v in _memory_store.values() if str(v.get("user_id","")) == user_id]
        if not mine:
            await q.edit_message_text(t("no_requests", lang), reply_markup=main_menu_kb(lang))
        else:
            lines = []
            for r in mine[-5:]:
                st = {"pending":"⏳","approved":"✅","rejected":"❌"}.get(r["status"],"?")
                lines.append(f"{st} {r['ref']} | {r.get('date','')} | {r.get('to_loc','')}")
            await q.edit_message_text(
                "\n".join(lines), parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_kb(lang)
            )
        return ConversationHandler.END

    if action == "help":
        help_text = {
            "km": "1️⃣ ចុច 'ដាក់ពាក្យស្នើរថ្ន'\n2️⃣ ជ្រើសប្រភេទ\n3️⃣ បំពេញព័ត៌មាន\n4️⃣ រង់ចាំការអនុម័ត",
            "zh": "1️⃣ 點「申請派車」\n2️⃣ 選擇種類\n3️⃣ 填寫資料\n4️⃣ 等待管理員審核",
            "en": "1️⃣ Tap 'Request Vehicle'\n2️⃣ Choose type\n3️⃣ Fill in details\n4️⃣ Wait for approval"
        }
        await q.edit_message_text(help_text.get(lang, help_text["zh"]), reply_markup=main_menu_kb(lang))
        return ConversationHandler.END

# Step 1: 選類型
async def cb_choose_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    apply_data = ctx.user_data.setdefault("apply", {"types": []})

    if q.data == "type_done":
        if not apply_data["types"]:
            await q.answer("請至少選一個 / Please select at least one", show_alert=True)
            return CHOOSING_TYPES
        await q.edit_message_text(t("ask_type", lang).split("\n")[0] + "\n\n🚗 " + t("vehicle_types", lang)[0],
                                  parse_mode=ParseMode.MARKDOWN, reply_markup=vehicle_kb(lang))
        return CHOOSING_VEHICLE

    idx = int(q.data.replace("type_", ""))
    types = t("dispatch_types", lang)
    chosen = types[idx]
    if chosen in apply_data["types"]:
        apply_data["types"].remove(chosen)
    else:
        apply_data["types"].append(chosen)

    await q.edit_message_text(
        t("ask_type", lang), parse_mode=ParseMode.MARKDOWN,
        reply_markup=type_kb(apply_data["types"], lang)
    )
    return CHOOSING_TYPES

# Step 2: 選車種
async def cb_choose_vehicle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    idx = int(q.data.replace("vtype_", ""))
    ctx.user_data["apply"]["vehicle_type"] = t("vehicle_types", lang)[idx]
    await q.edit_message_text(t("ask_date", lang), parse_mode=ParseMode.MARKDOWN)
    return ASKING_DATE

# Steps 3–10: 文字問答
async def ask_date(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    text = update.message.text.strip()
    # 簡單驗證日期格式
    try:
        datetime.strptime(text, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("❌ 格式錯誤，請輸入 YYYY-MM-DD（例如 2025-06-15）")
        return ASKING_DATE
    ctx.user_data["apply"]["date"] = text
    await update.message.reply_text(t("ask_time", lang), parse_mode=ParseMode.MARKDOWN)
    return ASKING_TIME

async def ask_time(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    text = update.message.text.strip()
    ctx.user_data["apply"]["time"] = text
    await update.message.reply_text(t("ask_from", lang), parse_mode=ParseMode.MARKDOWN)
    return ASKING_FROM

async def ask_from(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["apply"]["from_loc"] = update.message.text.strip()
    await update.message.reply_text(t("ask_to", lang), parse_mode=ParseMode.MARKDOWN)
    return ASKING_TO

async def ask_to(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["apply"]["to_loc"] = update.message.text.strip()
    await update.message.reply_text(t("ask_pax", lang), parse_mode=ParseMode.MARKDOWN)
    return ASKING_PAX

async def ask_pax(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    text = update.message.text.strip()
    if not text.isdigit():
        await update.message.reply_text("❌ 請輸入數字")
        return ASKING_PAX
    ctx.user_data["apply"]["pax"] = text
    await update.message.reply_text(t("ask_reason", lang), parse_mode=ParseMode.MARKDOWN)
    return ASKING_REASON

async def ask_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["apply"]["reason"] = update.message.text.strip()
    await update.message.reply_text(t("ask_name", lang), parse_mode=ParseMode.MARKDOWN)
    return ASKING_NAME

async def ask_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["apply"]["name"] = update.message.text.strip()
    await update.message.reply_text(t("ask_phone", lang), parse_mode=ParseMode.MARKDOWN)
    return ASKING_PHONE

async def ask_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    ctx.user_data["apply"]["phone"] = update.message.text.strip()
    ctx.user_data["apply"]["user_id"] = update.message.from_user.id

    summary = confirm_summary(ctx.user_data["apply"], lang)
    kb = InlineKeyboardMarkup([[
        InlineKeyboardButton(t("confirm_yes", lang), callback_data="confirm_yes"),
        InlineKeyboardButton(t("confirm_no", lang),  callback_data="confirm_no"),
    ]])
    await update.message.reply_text(summary, parse_mode=ParseMode.MARKDOWN, reply_markup=kb)
    return CONFIRMING

async def cb_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query; await q.answer()
    lang = ctx.user_data.get("lang", DEFAULT_LANG)

    if q.data == "confirm_no":
        await q.edit_message_text(t("cancelled", lang))
        return ConversationHandler.END

    data = ctx.user_data["apply"]
    ref = save_request(data)

    # 通知申請人
    await q.edit_message_text(
        t("submitted", lang, ref=ref), parse_mode=ParseMode.MARKDOWN
    )

    # 通知管理員群組
    notify_text = admin_notify_text(ref, data)
    try:
        await ctx.bot.send_message(
            ADMIN_GROUP_ID, notify_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_action_kb(ref)
        )
    except Exception as e:
        log.error(f"Admin notify error: {e}")

    return ConversationHandler.END

async def cb_cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    lang = ctx.user_data.get("lang", DEFAULT_LANG)
    await update.message.reply_text(t("cancelled", lang))
    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════
# HANDLERS — 管理員端
# ═══════════════════════════════════════════════════════════
async def cb_admin_approve(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """管理員點「核准」按鈕"""
    q = update.callback_query; await q.answer()
    ref = q.data.replace("approve_", "")
    ctx.user_data["pending_ref"] = ref
    ctx.user_data["pending_action"] = "approve"
    await q.edit_message_text(
        f"✅ 核准申請 *{ref}*\n\n請輸入指派車輛（或直接回「無需指派」）:",
        parse_mode=ParseMode.MARKDOWN
    )
    return APPROVE_ASKING_VEHICLE

async def admin_ask_vehicle(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ctx.user_data["approve_vehicle"] = update.message.text.strip()
    await update.message.reply_text("備註（或直接回「無」）:")
    return APPROVE_ASKING_NOTE

async def admin_approve_note(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ref = ctx.user_data.get("pending_ref","")
    vehicle = ctx.user_data.get("approve_vehicle","無指派")
    note = update.message.text.strip()
    admin_name = update.message.from_user.full_name

    update_request(ref, "approved", vehicle, note, admin_name)

    data = _memory_store.get(ref, {})
    user_id = data.get("user_id")
    lang = DEFAULT_LANG

    await update.message.reply_text(f"✅ 已核准 {ref}，正在通知申請人...")

    if user_id:
        try:
            await ctx.bot.send_message(
                user_id,
                t("approved_user", lang, ref=ref, vehicle=vehicle, note=note or "無"),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            log.error(f"Notify user error: {e}")
            await update.message.reply_text(f"⚠️ 無法通知申請人（可能尚未啟動 Bot）")

    return ConversationHandler.END

async def cb_admin_reject(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """管理員點「拒絕」按鈕"""
    q = update.callback_query; await q.answer()
    ref = q.data.replace("reject_", "")
    ctx.user_data["pending_ref"] = ref
    ctx.user_data["pending_action"] = "reject"
    await q.edit_message_text(
        f"❌ 拒絕申請 *{ref}*\n\n請輸入拒絕原因:",
        parse_mode=ParseMode.MARKDOWN
    )
    return REJECT_ASKING_REASON

async def admin_reject_reason(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    ref = ctx.user_data.get("pending_ref","")
    reason = update.message.text.strip()
    admin_name = update.message.from_user.full_name

    update_request(ref, "rejected", "", reason, admin_name)

    data = _memory_store.get(ref, {})
    user_id = data.get("user_id")
    lang = DEFAULT_LANG

    await update.message.reply_text(f"❌ 已拒絕 {ref}")

    if user_id:
        try:
            await ctx.bot.send_message(
                user_id,
                t("rejected_user", lang, ref=ref, note=reason),
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            log.error(f"Notify user error: {e}")

    return ConversationHandler.END

# ═══════════════════════════════════════════════════════════
# HANDLERS — 管理員查詢指令
# ═══════════════════════════════════════════════════════════
async def cmd_today(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """管理員查今日申請 /today"""
    records = get_today_requests()
    if not records:
        await update.message.reply_text("📭 本月尚無派車記錄")
        return
    lines = ["📊 *本月派車清單*\n"]
    for r in records:
        if isinstance(r, dict):
            ref = r.get("ref") or r.get("編號","")
            name = r.get("name") or r.get("申請人","")
            dest = r.get("to_loc") or r.get("目的地","")
            date = r.get("date") or r.get("日期","")
            status = r.get("status") or r.get("狀態","?")
            st_icon = {"待審核":"⏳","pending":"⏳","approved":"✅","rejected":"❌","核准":"✅","拒絕":"❌"}.get(status,"❓")
            lines.append(f"{st_icon} {ref} | {date} | {name} | {dest}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_pending(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """查待審核 /pending"""
    pending = [v for v in _memory_store.values() if v.get("status") == "pending"]
    if not pending:
        await update.message.reply_text("✅ 目前沒有待審核申請")
        return
    lines = ["⏳ *待審核申請*\n"]
    for r in pending:
        lines.append(f"• {r['ref']} | {r.get('date','')} | {r.get('name','')} → {r.get('to_loc','')}")
    await update.message.reply_text("\n".join(lines), parse_mode=ParseMode.MARKDOWN)

async def cmd_help_admin(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """管理員說明 /admin"""
    await update.message.reply_text(
        "*管理員指令*\n\n"
        "/today — 查本月派車紀錄\n"
        "/pending — 查待審核申請\n\n"
        "在申請通知訊息上點「✅ 核准」或「❌ 拒絕」按鈕即可審核。",
        parse_mode=ParseMode.MARKDOWN
    )

# ═══════════════════════════════════════════════════════════
# 主程式
# ═══════════════════════════════════════════════════════════
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    # 員工申請對話流程
    apply_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_menu, pattern="^menu_")],
        states={
            CHOOSING_TYPES:   [CallbackQueryHandler(cb_choose_type, pattern="^type_")],
            CHOOSING_VEHICLE: [CallbackQueryHandler(cb_choose_vehicle, pattern="^vtype_")],
            ASKING_DATE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_date)],
            ASKING_TIME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_time)],
            ASKING_FROM:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_from)],
            ASKING_TO:        [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_to)],
            ASKING_PAX:       [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_pax)],
            ASKING_REASON:    [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_reason)],
            ASKING_NAME:      [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_name)],
            ASKING_PHONE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_phone)],
            CONFIRMING:       [CallbackQueryHandler(cb_confirm, pattern="^confirm_")],
        },
        fallbacks=[MessageHandler(filters.COMMAND, cb_cancel)],
        per_message=False,
    )

    # 管理員審批對話流程
    approve_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_approve, pattern="^approve_")],
        states={
            APPROVE_ASKING_VEHICLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ask_vehicle)],
            APPROVE_ASKING_NOTE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_approve_note)],
        },
        fallbacks=[],
        per_message=False,
    )

    reject_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(cb_admin_reject, pattern="^reject_")],
        states={
            REJECT_ASKING_REASON: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reject_reason)],
        },
        fallbacks=[],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(cb_lang, pattern="^lang_"))
    app.add_handler(apply_conv)
    app.add_handler(approve_conv)
    app.add_handler(reject_conv)
    app.add_handler(CommandHandler("today", cmd_today))
    app.add_handler(CommandHandler("pending", cmd_pending))
    app.add_handler(CommandHandler("admin", cmd_help_admin))

    log.info("🚛 Bot started!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
