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
from utils.persian_tools import to_jalali

# وضعیت‌های کانورسیشن
WAITING_FOR_USER_ID = 1
ADMIN_MENU = 0


class AdminMenu:
    def __init__(self, bot):
        self.bot = bot
        self.db = VpnDatabase()
        self.states = {}  # ذخیره وضعیت هر کاربر

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

    def _get_admin_menu_data(self, first_name=None):
        keyboard = [
            [InlineKeyboardButton("مشخصات کاربر", callback_data="admin_menu_user_detail")],
            [InlineKeyboardButton("آمار خرید", callback_data="admin_menu_bot_analays")],
            [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "به پنل ادمین خوش آمدید"
        if first_name:
            text = f"{first_name} عزیز، به پنل ادمین خوش آمدید"
        return text, reply_markup

    async def send_admin_menu(self, chat_id, user_id, message_id=None):
        """Helper to send/edit admin menu"""
        text, reply_markup = self._get_admin_menu_data()
        if message_id:
            await self.bot.edit_message_text(chat_id, message_id, text, reply_markup=reply_markup)
        else:
            await self.bot.send_message(chat_id, text, reply_markup=reply_markup)
        self.states[user_id] = ADMIN_MENU

    async def show_menu(self, client, callback_query: CallbackQuery):
        await callback_query.answer()
        user_id = callback_query.from_user.id
        await self.send_admin_menu(
            chat_id=callback_query.message.chat.id,
            user_id=user_id,
            message_id=callback_query.message.id
        )

    async def admin_menu_user_detail(self, client, callback_query: CallbackQuery):
        # تنظیم وضعیت به انتظار دریافت آیدی کاربر
        user_id = callback_query.from_user.id
        self.states[user_id] = WAITING_FOR_USER_ID

        await callback_query.answer()
        await callback_query.message.edit_text(
            "لطفاً آیدی عددی کاربر را ارسال کنید:\n\n"
            "⚠️ برای لغو عملیات /cancel را ارسال کنید"
        )

    async def handle_user_id_input(self, client, message: Message):
        user_id = message.from_user.id
        current_state = self.states.get(user_id)

        # فقط اگر در حالت انتظار آیدی هستیم پردازش شود
        if current_state != WAITING_FOR_USER_ID:
            return

        if message.text.lower() == "/cancel":
            # پاک کردن وضعیت و بازگشت به منو
            self.states.pop(user_id, None)
            text, reply_markup = self._get_admin_menu_data()
            await message.reply_text("❌ عملیات لغو شد", reply_markup=reply_markup)
            return

        try:
            target_user_id = message.text.strip()

            # چک کردن وجود کاربر در دیتابیس
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
            self.states[user_id] = ADMIN_MENU

        except Exception as e:
            logging.error(f"Error in handle_user_id_input: {e}")
            await message.reply_text("⚠️ خطا در پردازش درخواست! لطفاً مجدداً تلاش کنید.")

    async def admin_menu_bot_analays(self, client, callback_query: CallbackQuery):
        await callback_query.answer()
        text = "📊 آمار خرید کلی ربات:\n\n"
        text += "• تعداد کاربران: 100\n"
        text += "• تعداد خریدهای موفق: 50\n"
        text += "• درآمد کل: 5,000,000 تومان"

        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.message.edit_text(text, reply_markup=reply_markup)