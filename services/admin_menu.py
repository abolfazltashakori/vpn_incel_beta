# admin_menu.py
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from database.database_VPN import VpnDatabase
from utils.persian_tools import to_jalali
import logging

db = VpnDatabase()
states = {}

WAITING_FOR_USER_ID = 1
ADMIN_MENU = 0


def _get_admin_menu_data(first_name=None):
    keyboard = [
        [InlineKeyboardButton("مشخصات کاربر", callback_data="admin_menu_user_detail")],
        [InlineKeyboardButton("ساخت کد هدیه", callback_data="create_gift_code_menu")],
        [InlineKeyboardButton("آمار خرید", callback_data="admin_menu_bot_analays")],
        [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_to_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "به پنل ادمین خوش آمدید"
    if first_name:
        text = f"{first_name} عزیز، به پنل ادمین خوش آمدید"
    return text, reply_markup


async def show_menu(client, callback_query):
    await callback_query.answer()
    user_id = callback_query.from_user.id
    text, reply_markup = _get_admin_menu_data()
    await callback_query.message.edit_text(text, reply_markup=reply_markup)
    states[user_id] = ADMIN_MENU


async def create_gift_code_menu(client, callback_query):
    keyboard = [
        [InlineKeyboardButton("ساخت کد", callback_data="generate_gift_code_menu")],
        [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = "فرمت ساخت کد : تعداد استفاده,مقدار اضافه شدن موجودی تومان"
    await callback_query.message.edit_text(text, reply_markup=reply_markup)


async def admin_menu_user_detail(client, callback_query):
    user_id = callback_query.from_user.id
    states[user_id] = WAITING_FOR_USER_ID
    await callback_query.answer()
    await callback_query.message.edit_text(
        "لطفاً آیدی عددی کاربر را ارسال کنید:\n\n"
        "⚠️ برای لغو عملیات /cancel را ارسال کنید"
    )


async def handle_user_id_input(client, message):
    user_id = message.from_user.id
    current_state = states.get(user_id)

    if current_state != WAITING_FOR_USER_ID:
        return

    if message.text.lower() == "/cancel":
        states.pop(user_id, None)
        text, reply_markup = _get_admin_menu_data()
        await message.reply_text("❌ عملیات لغو شد", reply_markup=reply_markup)
        return

    try:
        target_user_id = message.text.strip()
        user_info = db.get_user_info(target_user_id)

        if not user_info:
            await message.reply_text("❌ کاربری با این آیدی یافت نشد!")
            return

        join_date = to_jalali(user_info[5]) if user_info[5] else "نامشخص"
        text = f"""
📋 مشخصات کاربر:

🪪 شناسه کاربری: {user_info[0]}
👤 نام: {user_info[1]} {user_info[2] or ''}
👨‍👩‍👦 کد معرف: {user_info[3] or 'ندارد'}
📱 شماره تماس: {user_info[4] or '🔴 ارسال نشده است'}
⌚️ تاریخ ثبت‌نام: {join_date}
💰 موجودی: {user_info[6]:,} تومان
🛒 تعداد سرویس‌های خریداری شده: {user_info[7]} عدد
📑 تعداد فاکتورهای پرداخت شده: {user_info[8]} عدد
🤝 تعداد زیرمجموعه: {user_info[9]} نفر
🔖 گروه کاربری: {user_info[10]}
"""

        keyboard = [[InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await message.reply_text(text, reply_markup=reply_markup)
        states[user_id] = ADMIN_MENU

    except Exception as e:
        logging.error(f"Error in handle_user_id_input: {e}")
        await message.reply_text("⚠️ خطا در پردازش درخواست! لطفاً مجدداً تلاش کنید.")


async def admin_menu_bot_analays(client, callback_query):
    await callback_query.answer()
    text = "📊 آمار خرید کلی ربات:\n\n"
    text += "• تعداد کاربران: 100\n"
    text += "• تعداد خریدهای موفق: 50\n"
    text += "• درآمد کل: 5,000,000 تومان"

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await callback_query.message.edit_text(text, reply_markup=reply_markup)


async def generate_gift_code(client, callback_query):
    user_id = callback_query.from_user.id
    states[user_id] = "WAITING_FOR_GIFT_CODE_DETAILS"
    await callback_query.message.edit_text(
        "📝 لطفاً مشخصات کد تخفیف را به فرمت زیر ارسال کنید:\n\n"
        "`مقدار_تخفیف_تومان,تاریخ_انقضا,تعداد_استفاده_مجاز`\n\n"
        "مثال: `50000,2024-12-31,5`\n"
        "یعنی کد 50,000 تومانی که تا تاریخ 2024-12-31 معتبر است و 5 بار قابل استفاده\n\n"
        "⚠️ توجه: تاریخ باید به فرمت YYYY-MM-DD باشد"
    )


async def process_gift_code_details(client, message):
    user_id = message.from_user.id
    if user_id not in states or states[user_id] != "WAITING_FOR_GIFT_CODE_DETAILS":
        return

    try:
        parts = message.text.split(',')
        if len(parts) != 3:
            raise ValueError("فرمت نادرست")

        amount = int(parts[0].strip())
        expire_date = parts[1].strip()
        max_usage = int(parts[2].strip())  # تعداد استفاده مجاز

        from datetime import datetime
        datetime.strptime(expire_date, "%Y-%m-%d")

        import random
        import string
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        db.create_gift_code(code, amount, expire_date, max_usage)  # ارسال پارامتر جدید

        text = f"""
✅ کد تخفیف با موفقیت ایجاد شد!

🪪 کد: `{code}`
💰 مبلغ: {amount:,} تومان
📅 تاریخ انقضا: {expire_date}
🔢 تعداد استفاده مجاز: {max_usage} بار
        """

        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]]
        await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        del states[user_id]

    except ValueError:
        await message.reply_text("❌ فرمت نادرست! لطفاً به فرمت مثال ارسال کنید")


def register_admin_handlers(bot):
    bot.add_handler(CallbackQueryHandler(show_menu, filters=filters.regex("^admin_menu$")), group=10)
    bot.add_handler(CallbackQueryHandler(create_gift_code_menu, filters=filters.regex("^create_gift_code_menu$")),
                    group=10)
    bot.add_handler(CallbackQueryHandler(generate_gift_code, filters=filters.regex("^generate_gift_code_menu$")),
                    group=10)
    bot.add_handler(MessageHandler(process_gift_code_details, filters=filters.private & filters.text), group=10)
    bot.add_handler(CallbackQueryHandler(admin_menu_user_detail, filters=filters.regex("^admin_menu_user_detail$")),
                    group=10)
    bot.add_handler(MessageHandler(handle_user_id_input, filters=filters.private & filters.text), group=11)
    bot.add_handler(CallbackQueryHandler(admin_menu_bot_analays, filters=filters.regex("^admin_menu_bot_analays$")),
                    group=10)
