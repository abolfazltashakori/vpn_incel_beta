from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.marzban_service import MarzbanService
from database.database_VPN import VpnDatabase
from utils.config import Config
from utils.persian_tools import to_jalali
from datetime import *
class VpnHandler:
    def __init__(self, bot):
        self.bot = bot
        self.db = VpnDatabase()


    def register(self):
        self.register_handlers()

    def register_handlers(self):
        # ثبت هندلر با استفاده از CallbackQueryHandler
        self.bot.add_handler(CallbackQueryHandler(
            self.handle_test_vpn,
            filters.regex("^test_vpn_menu$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.show_user_account_info,
            filters.regex("^user_details$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.show_user_services,
            filters.regex("^my_service_menu$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.show_service_details,
            filters.regex(r"^service_details_")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.handle_renew_service,
            filters.regex(r"^renew_service_")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.confirm_renew_service,
            filters.regex(r"^confirm_renew_")
        ))

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
👤💼 مشخصات حساب کاربری شما:

🆔 شناسه کاربری: {user_info[0]}
👤 نام: {user_info[1]} {user_info[2] or ''}
👥 کد معرف: {user_info[3] or '─'}
📞 شماره تماس: {user_info[4] or '❌ ثبت نشده'}
📅 زمان ثبت نام: {join_date}
💰 موجودی: {user_info[6]:,} تومان
📦 تعداد سرویس‌ها: {user_info[7]} عدد
🧾 تعداد فاکتورها: {user_info[8]} عدد
👨‍👩‍👧‍👦 زیرمجموعه‌ها: {user_info[9]} نفر
🏷️ گروه کاربری: {user_info[10]}

⏱️ تاریخ: {current_date} → ساعت: {datetime.now().strftime('%H:%M:%S')}
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
                raise Exception("🔴 خطا در اتصال به سرور")

            inbounds = MarzbanService.get_vless_inbound_tags(token)
            if not inbounds:
                raise Exception("⚠️ هیچ inbound فعالی یافت نشد")

            volume_gb = 200 / (1024)
            service = MarzbanService.create_service(
                token,
                user.id,
                inbounds,
                volume_gb=volume_gb,  # مقدار تصحیح شده
                days=1
            )
            if not service:
                raise Exception("🔴 خطا در ایجاد سرویس")

            # ذخیره سرویس در دیتابیس (اضافه شده)
            expire_timestamp = int((datetime.now() + timedelta(days=1)).timestamp())
            self.db.add_user_service(
                user.id,
                service['username'],
                "test",  # package_id
                0.2,  # volume_gb (200 مگابایت = 0.2 گیگابایت)
                expire_timestamp
            )

            self.db.active_test_service(user.id, True)

            text = f"""
🎉✨ **سرویس تست فعال شد!**

📛 نام سرویس: `{service['username']}`
📦 حجم: 200 مگابایت
⏳ اعتبار: 24 ساعت
🔗 لینک اتصال:
`{service['subscription_url'] or service['links'][0]}`

💡 توجه: این سرویس فقط برای تست اولیه می‌باشد
"""

            admin_text = f"""
کاربر{user.id}
یوزر نیم{user.username}
سرویس تست دریافت کرد
"""
            await client.send_message(Config.ADMIN_ID, admin_text)
            url = "https://t.me/incel_help"
            keyboard = [
                InlineKeyboardButton("راهنما استفاده", url=url),
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await callback_query.message.edit_reply_markup(text,reply_markup=reply_markup)
        except Exception as e:
            await callback_query.message.edit_text(f"❌ خطا: {str(e)}")


    async def show_user_services(self, client, callback_query):
        user_id = callback_query.from_user.id
        services = self.db.get_user_services(user_id)

        if not services:
            await callback_query.message.edit_text("📭 شما هیچ سرویس فعالی ندارید!")
            return

        keyboard = []
        for service in services:
            service_name = service[2]  # service_username
            btn = InlineKeyboardButton(
                text=f"📡 سرویس {service_name}",
                callback_data=f"service_details_{service_name}"
            )
            keyboard.append([btn])

        keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")])

        text = "📦 سرویس‌های فعال شما:\nلطفا یک سرویس را انتخاب کنید"
        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    async def show_service_details(self, client, callback_query):
        service_username = callback_query.data.replace("service_details_", "", 1)
        service = self.db.get_service_by_username(service_username)

        if not service:
            await callback_query.answer("⚠️ سرویس یافت نشد!")
            return

        # محاسبه زمان باقیمانده
        expire_date = datetime.fromtimestamp(service[5])
        remaining_days = (expire_date - datetime.now()).days

        text = f"""
🔍📡 مشخصات سرویس:
┌─ 📛 شناسه: `{service[2]}`
├─ 💾 حجم کل: {service[4]} گیگابایت
├─ ⏳ زمان باقیمانده: {remaining_days} روز
└─ 📅 تاریخ انقضا: {expire_date.strftime('%Y-%m-%d %H:%M')}
"""
        keyboard = [
            [InlineKeyboardButton("🔄 تمدید سرویس", callback_data=f"renew_service_{service[2]}")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="my_service_menu")]
        ]

        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def handle_renew_service(self, client, callback_query):
        service_username = callback_query.data.replace("renew_service_", "", 1)
        service = self.db.get_service_by_username(service_username)
        user_id = callback_query.from_user.id

        if not service:
            await callback_query.answer("⚠️ سرویس یافت نشد!")
            return

        package_id = service[3]
        package_details = Config.PACKAGE_DETAILS.get(package_id)

        if not package_details:
            await callback_query.message.edit_text("❌ اطلاعات بسته سرویس نامعتبر است!")
            return

        # محاسبه تاریخ انقضای جدید (تمدید 30 روزه)
        new_expire_date = int((datetime.now() + timedelta(days=30)).timestamp())

        text = f"""
🔄 آیا می‌خواهید این سرویس را تمدید کنید؟
├─ 💰 هزینه: {package_details['price']:,} تومان
└─ ⏳ مدت: 30 روز
"""
        keyboard = [
            [InlineKeyboardButton("✅ بله، تمدید کن", callback_data=f"confirm_renew_{service_username}")],
            [InlineKeyboardButton("❌ خیر، بازگشت", callback_data=f"service_details_{service_username}")]
        ]

        await callback_query.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )


    # در main.py این هندلر را اضافه کنید

    async def confirm_renew_service(self, client, callback_query):
        service_username = callback_query.data.replace("confirm_renew_", "", 1)
        db = VpnDatabase()
        service = db.get_service_by_username(service_username)
        user_id = callback_query.from_user.id

        if not service:
            await callback_query.answer("⚠️ سرویس یافت نشد!")
            return

        package_id = service[3]
        package_details = Config.PACKAGE_DETAILS.get(package_id)

        if not package_details:
            await callback_query.message.edit_text("❌ اطلاعات بسته سرویس نامعتبر است!")
            return

        # بررسی موجودی کاربر
        balance = db.get_balance(user_id)
        if balance < package_details['price']:
            await callback_query.message.edit_text(
                "⚠️ موجودی کافی نیست!\n"
                f"├─ 💰 موجودی فعلی: {balance:,} تومان\n"
                f"└─ 💸 مبلغ مورد نیاز: {package_details['price']:,} تومان"
            )
            return

        # کسر هزینه و ریست سرویس
        try:
            db.balance_decrease(user_id, package_details['price'])
            new_expire_date = int((datetime.now() + timedelta(days=30)).timestamp())

            # ریست سرویس در Marzban
            token = MarzbanService.get_admin_token()
            if token:
                MarzbanService.reset_service(
                    token,
                    service_username,
                    new_expire_date
                )

            # به‌روزرسانی دیتابیس
            db.reset_service(service_username, new_expire_date)

            await callback_query.message.edit_text(
                "✅ سرویس با موفقیت تمدید شد!\n"
                f"📆 انقضای جدید: {datetime.fromtimestamp(new_expire_date).strftime('%Y-%m-%d %H:%M')}"
            )
        except Exception as e:
            #logger.error(f"Error renewing service: {e}")
            await callback_query.message.edit_text("❌ خطا در تمدید سرویس!")