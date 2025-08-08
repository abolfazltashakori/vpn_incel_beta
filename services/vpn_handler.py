from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.marzban_service import MarzbanService
from database.vpn_db import VpnDatabase
from utils.config import Config


class VpnHandler:
    def __init__(self, bot):
        self.bot = bot
        self.db = VpnDatabase()
        self.register_handlers()

    def register_handlers(self):
        self.bot.add_handler(self.test_vpn_handler)

    @staticmethod
    @bot.on_callback_query(filters.regex("^test_vpn_menu$"))
    async def test_vpn_handler(client, callback_query):
        handler = VpnHandler.get_handler(client)
        await handler.handle_test_vpn(callback_query)

    async def handle_test_vpn(self, callback_query):
        user = callback_query.from_user
        try:
            # ایجاد کاربر در دیتابیس
            self.db.create_user_if_not_exists(
                user.id,
                user.first_name,
                user.last_name or "",
                user.username or ""
            )

            # بررسی استفاده قبلی از سرویس تست
            if self.db.has_used_test_service(user.id):
                await callback_query.answer("شما قبلاً از سرویس تست استفاده کرده‌اید!", show_alert=True)
                return

            # ایجاد سرویس تست
            token = MarzbanService.get_admin_token()
            if not token:
                raise Exception("خطا در اتصال به سرور")

            inbounds = MarzbanService.get_vless_inbound_tags(token)
            if not inbounds:
                raise Exception("هیچ inbound فعالی یافت نشد")

            service = MarzbanService.create_service(token, user.id, inbounds)
            if not service:
                raise Exception("خطا در ایجاد سرویس")

            # علامت‌گذاری استفاده از سرویس تست
            self.db.active_test_service(user.id, True)

            text = f"""
✅ سرویس تست با موفقیت ایجاد شد!
📛 نام سرویس: {service['username']}
📦 حجم: 0.2 گیگابایت
⏳ مدت اعتبار: 1 روز
🔗 لینک اتصال:
`{service['subscription_url'] or service['links'][0]}`
"""
            await callback_query.message.edit_text(text)
        except Exception as e:
            await callback_query.message.edit_text(f"❌ خطا: {str(e)}")
        finally:
            self.db.close()