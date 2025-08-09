import logging
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message
)
from database.database_VPN import VpnDatabase
from utils.persian_tools import to_jalali  # برای تبدیل تاریخ به شمسی

# وضعیت‌های کانورسیشن
WAITING_FOR_USER_ID = 1
ADMIN_MENU = 0


class AdminMenu:
    def __init__(self, bot):
        self.bot = bot
        self.db = VpnDatabase()
        self.states = {}  # ذخیره وضعیت هر کاربر

    def register(self):
        self.register_handlers()

    def register_handlers(self):
        # هندلر منوی اصلی ادمین
        self.bot.add_handler(CallbackQueryHandler(
            self.show_menu,
            filters.regex("^admin_menu$")
        ))

        # هندلر گزینه "مشخصات کاربر"
        self.bot.add_handler(CallbackQueryHandler(
            self.admin_menu_user_detail,
            filters.regex("^admin_menu_user_detail$")
        ))

        self.bot.add_handler(MessageHandler(
            self.handle_user_id_input,
            filters.private & filters.text
        ))

        # هندلر گزینه "آمار خرید"
        self.bot.add_handler(CallbackQueryHandler(
            self.admin_menu_bot_analays,
            filters.regex("^admin_menu_bot_analays$")
        ))

    async def show_menu(self, client, callback_query: CallbackQuery):
        await callback_query.answer()
        keyboard = [
            [InlineKeyboardButton("مشخصات کاربر", callback_data="admin_menu_user_detail")],
            [InlineKeyboardButton("آمار خرید", callback_data="admin_menu_bot_analays")],
            [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        user_first_name = callback_query.from_user.first_name
        text = f"{user_first_name} عزیز، به پنل ادمین خوش آمدید"
        await callback_query.message.edit_text(text, reply_markup=reply_markup)

        # تنظیم وضعیت به منوی اصلی
        self.states[callback_query.from_user.id] = ADMIN_MENU

    async def admin_menu_user_detail(self, client, callback_query: CallbackQuery):
        # تنظیم وضعیت به انتظار دریافت آیدی کاربر
        self.states[callback_query.from_user.id] = WAITING_FOR_USER_ID

        await callback_query.message.edit_text(
            "لطفاً آیدی عددی کاربر را ارسال کنید:\n\n"
            "⚠️ برای لغو عملیات /cancel را ارسال کنید"
        )

    async def handle_user_id_input(self, client, message: Message):
        user_id = message.from_user.id

        # بررسی وضعیت کاربر
        if self.states.get(user_id) != WAITING_FOR_USER_ID:
            return

        # بررسی لغو عملیات
        if message.text.lower() == "/cancel":
            del self.states[user_id]
            await message.reply_text("❌ عملیات لغو شد.")
            return await self.show_menu(client, message)

        try:
            # تبدیل آیدی به عدد
            target_user_id = int(message.text.strip())

            # دریافت اطلاعات کاربر از دیتابیس
            user_info = self.db.get_user_info(target_user_id)

            if not user_info:
                await message.reply_text("❌ کاربری با این آیدی یافت نشد!")
                return

            # نمایش اطلاعات کاربر
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

            # دکمه بازگشت
            keyboard = [
                [InlineKeyboardButton("🔙 بازگشت به منوی ادمین", callback_data="admin_menu")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(text, reply_markup=reply_markup)

            # بازگشت به وضعیت منوی اصلی
            self.states[user_id] = ADMIN_MENU

        except ValueError:
            await message.reply_text("⚠️ آیدی باید یک عدد باشد! لطفاً مجدداً تلاش کنید.")

    async def admin_menu_bot_analays(self, client, callback_query: CallbackQuery):
        # پیاده‌سازی آمار خرید (می‌توانید کامل کنید)
        text = "📊 آمار خرید کلی ربات:\n\n"
        text += "• تعداد کاربران: 100\n"
        text += "• تعداد خریدهای موفق: 50\n"
        text += "• درآمد کل: 5,000,000 تومان"

        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.message.edit_text(text, reply_markup=reply_markup)