from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.marzban_service import MarzbanService
from database.database_VPN import VpnDatabase
from utils.config import Config
from utils.persian_tools import to_jalali
from datetime import datetime
class VpnHandler:
    def __init__(self, bot):
        self.bot = bot
        self.db = VpnDatabase()


    def register(self):
        self.register_handlers()

    def register_handlers(self):
        # ثبت هندلر با استفاده از self.bot
        self.bot.add_handler(
            self.bot.on_callback_query(filters.regex("^test_vpn_menu$"))(self.handle_test_vpn)
        )

        self.bot.add_handler(
            self.bot.on_callback_query(filters.regex("^user_details$"))(self.show_user_account_info)
        )

    async def show_user_account_info(self, client, callback_query):
        user_id = callback_query.from_user.id
        user_info = self.db.get_user_info(user_id)

        if not user_info:
            await callback_query.answer("❌ اطلاعات کاربر یافت نشد!")
            return

        # تبدیل تاریخ به شمسی
        join_date = to_jalali(user_info[5])
        current_date = to_jalali(datetime.now())

        text = f"""
    🗂 اطلاعات حساب کاربری شما :

    🪪 شناسه کاربری: {user_info[0]}
    👤 نام: {user_info[1]} {user_info[2] or ''}
    👨‍👩‍👦 کد معرف شما : {user_info[3] or 'ندارد'}
    📱 شماره تماس : {user_info[4] or '🔴 ارسال نشده است 🔴'}
    ⌚️ زمان ثبت نام : {join_date}
    💰 موجودی: {user_info[6]:,} تومان
    🛒 تعداد سرویس های خریداری شده : {user_info[7]} عدد
    📑 تعداد فاکتور های پرداخت شده : {user_info[8]} عدد
    🤝 تعداد زیر مجموعه های شما : {user_info[9]} نفر
    🔖 گروه کاربری : {user_info[10]}

    📆 {current_date} → ⏰ {datetime.now().strftime('%H:%M:%S')}
    """

        keyboard = [
            [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]
        ]

        await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

    async def handle_test_vpn(self, client, callback_query):
        user = callback_query.from_user
        try:
            self.db.create_user_if_not_exists(
                user.id,
                user.first_name,
                user.last_name or "",
                user.username or ""
            )

            if self.db.has_used_test_service(user.id):
                await callback_query.answer("⚠️ شما قبلاً از سرویس تست استفاده کرده‌اید!", show_alert=True)
                return

            token = MarzbanService.get_admin_token()
            if not token:
                raise Exception("خطا در اتصال به سرور")

            inbounds = MarzbanService.get_vless_inbound_tags(token)
            if not inbounds:
                raise Exception("هیچ inbound فعالی یافت نشد")

            volume_gb = 200 / (1024)
            service = MarzbanService.create_service(
                token,
                user.id,
                inbounds,
                volume_gb=volume_gb,  # مقدار تصحیح شده
                days=1
            )
            if not service:
                raise Exception("خطا در ایجاد سرویس")

            self.db.active_test_service(user.id, True)

            text = f"""
🎉 **سرویس تست فعال شد!**

📛 نام سرویس: `{service['username']}`
📦 حجم: 200 مگابایت
⏳ اعتبار: 24 ساعت
🔗 لینک اتصال:
`{service['subscription_url'] or service['links'][0]}`

⚠️ توجه: این سرویس فقط برای تست اولیه می‌باشد
"""
            await callback_query.message.edit_text(text)
        except Exception as e:
            await callback_query.message.edit_text(f"❌ خطا: {str(e)}")
