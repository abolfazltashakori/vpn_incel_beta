import logger
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
import logging
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
        # اضافه کردن هندلر برای منوی ساخت کد
        self.bot.add_handler(CallbackQueryHandler(
            self.create_gift_code_menu,
            filters.regex("^create_gift_code_menu$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.generate_gift_code,
            filters.regex("^generate_gift_code_menu$")
        ))
        self.bot.add_handler(MessageHandler(
            self.process_gift_code_details,
            filters.private & filters.text
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
            [InlineKeyboardButton("ساخت کد هدیه",callback_data="create_gift_code_menu")],
            [InlineKeyboardButton("آمار خرید", callback_data="admin_menu_bot_analays")],
            [InlineKeyboardButton("بازگشت به منوی اصلی", callback_data="back_to_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "به پنل ادمین خوش آمدید"
        if first_name:
            text = f"{first_name} عزیز، به پنل ادمین خوش آمدید"
        return text, reply_markup

    async def create_gift_code_menu(self, client, callback_query: CallbackQuery):
        keyboard = [
            [InlineKeyboardButton("ساخت کد", callback_data="generate_gift_code_menu")],
            [InlineKeyboardButton("بازگشت", callback_data="admin_menu")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "فرمت ساخت کد : تعداد استفاده,مقدار اضافه شدن موجودی تومان"
        await callback_query.message.edit_text(text, reply_markup=reply_markup)

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

    async def generate_gift_code(self, client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        self.states[user_id] = "WAITING_FOR_GIFT_CODE_DETAILS"
        await callback_query.message.edit_text(
            "📝 لطفاً مشخصات کد تخفیف را به فرمت زیر ارسال کنید:\n\n"
            "`مقدار_تخفیف_تومان,تاریخ_انقضا`\n\n"
            "مثال: `50000,2024-12-31`\n"
            "یعنی کد 50,000 تومانی که تا تاریخ 2024-12-31 معتبر است\n\n"
            "⚠️ توجه: تاریخ باید به فرمت YYYY-MM-DD باشد"
        )

    async def process_gift_code_details(self, client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.states or self.states[user_id] != "WAITING_FOR_GIFT_CODE_DETAILS":
            return

        try:
            parts = message.text.split(',')
            if len(parts) != 2:
                raise ValueError("فرمت نادرست")

            amount = int(parts[0].strip())
            expire_date = parts[1].strip()

            # Validate date format
            from datetime import datetime
            datetime.strptime(expire_date, "%Y-%m-%d")

            # Generate random code
            import random
            import string
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

            # Save to database
            db = VpnDatabase()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            db.conn.execute('''INSERT INTO gift_codes (code, amount, expire_date, created_at)
                            VALUES (?, ?, ?, ?)''', (code, amount, expire_date, created_at))
            db.conn.commit()

            text = f"""
    ✅ کد تخفیف با موفقیت ایجاد شد!

    🪪 کد: `{code}`
    💰 مبلغ: {amount:,} تومان
    📅 تاریخ انقضا: {expire_date}
            """

            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="admin_menu")]]
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
            del self.states[user_id]

        except ValueError:
            await message.reply_text("❌ فرمت نادرست! لطفاً به فرمت مثال ارسال کنید")