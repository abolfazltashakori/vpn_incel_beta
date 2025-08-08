# services/payment_handler.py
import logging
from pyrogram import filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from pyrogram.errors import BadRequest
from services.marzban_service import MarzbanService
from utils.config import Config
from database.user_db import UserDatabase
from database.vpn_db import VpnDatabase

logger = logging.getLogger(__name__)


class PaymentHandler:
    def __init__(self, bot):
        self.bot = bot
        self.user_db = UserDatabase()
        self.vpn_db = VpnDatabase()
        self.package_details = Config.PACKAGE_DETAILS
        self.register_handlers()

    def register_handlers(self):
        # دسته‌بندی‌های اصلی
        self.bot.add_handler(
            self.bot.on_callback_query(filters.regex("^buy_new_service_menu$"))(self.buy_new_service_menu))
        self.bot.add_handler(self.bot.on_callback_query(filters.regex("^normal$"))(self.normal_buy_service))
        self.bot.add_handler(self.bot.on_callback_query(filters.regex("^lifetime$"))(self.lifetime_buy_service))
        self.bot.add_handler(self.bot.on_callback_query(filters.regex("^unlimited$"))(self.unlimited_buy_service))
        self.bot.add_handler(self.bot.on_callback_query(filters.regex("^longtime$"))(self.longtime_buy_service))

        # بسته‌های خاص
        self.bot.add_handler(self.bot.on_callback_query(filters.regex(r"^(normal|lifetime|unlimited|longtime)_\d+$"))(
            self.handle_package_selection))

        # بازگشت و تایید
        self.bot.add_handler(
            self.bot.on_callback_query(filters.regex(r"^back_to_(normal|lifetime|unlimited|longtime)$"))(
                self.back_to_category))
        self.bot.add_handler(self.bot.on_callback_query(filters.regex(r"^confirm_(.*)$"))(self.confirm_purchase))
        self.bot.add_handler(self.bot.on_callback_query(filters.regex("^back_to_vpn_menu$"))(self.back_to_vpn_menu))

    async def buy_new_service_menu(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("بسته های عادی", callback_data="normal")],
                [InlineKeyboardButton("بسته های لایف تایم", callback_data="lifetime")],
                [InlineKeyboardButton("بسته های بلند مدت", callback_data="longtime")],
                [InlineKeyboardButton("بسته های نامحدود", callback_data="unlimited")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "سرویس مورد نظر خود را انتخاب کنید"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in buy_new_service_menu: {e}")
            await callback_query.message.edit_text("❌ خطا در نمایش منو!")

    async def normal_buy_service(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("بسته 20 گیگ کاربر نامحدود 1 ماه : 50000", callback_data="normal_1")],
                [InlineKeyboardButton("بسته 50 گیگ کاربر نامحدود 1 ماه : 110000", callback_data="normal_2")],
                [InlineKeyboardButton("بسته 100 گیگ کاربر نامحدود 1 ماه : 190000", callback_data="normal_3")],
                [InlineKeyboardButton("بازگشت", callback_data="back_to_vpn_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "بسته مورد نظر را انتخاب کنید"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in normal_buy_service: {e}")
            await callback_query.message.edit_text("❌ خطا در نمایش بسته‌های عادی!")

    async def lifetime_buy_service(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("10 گیگ بدون محدودیت کاربر و زمان : 35000", callback_data="lifetime_1")],
                [InlineKeyboardButton("20 گیگ بدون محدودیت کاربر و زمان : 60000", callback_data="lifetime_2")],
                [InlineKeyboardButton("50 گیگ بدون محدودیت کاربر و زمان : 160000", callback_data="lifetime_3")],
                [InlineKeyboardButton("100 گیگ بدون محدودیت کاربر و زمان : 360000", callback_data="lifetime_4")],
                [InlineKeyboardButton("بازگشت", callback_data="back_to_vpn_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "بسته مورد نظر را انتخاب کنید"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in lifetime_buy_service: {e}")
            await callback_query.message.edit_text("❌ خطا در نمایش بسته‌های لایف تایم!")

    async def unlimited_buy_service(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("نامحدود 1 کاربر 1 ماهه ( مصرف منصفانه ) : 95000", callback_data="unlimited_1")],
                [InlineKeyboardButton("نامحدود 2 کاربر 1 ماهه ( مصرف منصفانه ) : 145000", callback_data="unlimited_2")],
                [InlineKeyboardButton("نامحدود 1 کاربر 2 ماهه ( مصرف منصفانه ) : 180000", callback_data="unlimited_3")],
                [InlineKeyboardButton("نامحدود 2 کاربر 2 ماهه ( مصرف منصفانه ) : 240000", callback_data="unlimited_4")],
                [InlineKeyboardButton("بازگشت", callback_data="back_to_vpn_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "بسته مورد نظر را انتخاب کنید"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in unlimited_buy_service: {e}")
            await callback_query.message.edit_text("❌ خطا در نمایش بسته‌های نامحدود!")

    async def longtime_buy_service(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("50 گیگ کاربر نامحدود 2 ماه : 135000", callback_data="longtime_1")],
                [InlineKeyboardButton("100 گیگ کاربر نامحدود 2 ماه : 260000", callback_data="longtime_2")],
                [InlineKeyboardButton("150 گیگ کاربر نامحدود 2 ماه : 375000", callback_data="longtime_3")],
                [InlineKeyboardButton("بازگشت", callback_data="back_to_vpn_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "بسته مورد نظر را انتخاب کنید"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in longtime_buy_service: {e}")
            await callback_query.message.edit_text("❌ خطا در نمایش بسته‌های بلند مدت!")

    async def handle_package_selection(self, client, callback_query: CallbackQuery):
        try:
            package_id = callback_query.data
            if package_id not in self.package_details:
                await callback_query.answer("بسته مورد نظر یافت نشد!", show_alert=True)
                return

            package = self.package_details[package_id]
            volume = "نامحدود" if package["volume_gb"] == 0 else f"{package['volume_gb']} گیگابایت"
            days = "مادام‌العمر" if package["days"] == 0 else f"{package['days']} روز"

            text = (
                "📦 جزئیات بسته انتخابی:\n\n"
                f"• حجم: {volume}\n"
                f"• مدت: {days}\n"
                f"• قیمت: {package['price']:,} تومان\n\n"
                "آیا از خرید این بسته اطمینان دارید؟"
            )

            keyboard = [
                [InlineKeyboardButton("✅ تایید و پرداخت", callback_data=f"confirm_{package_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_to_{package_id.split('_')[0]}")]
            ]

            await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Error in handle_package_selection: {e}")
            await callback_query.message.edit_text("❌ خطا در نمایش جزئیات بسته!")

    async def back_to_category(self, client, callback_query: CallbackQuery):
        try:
            category = callback_query.data.split("_")[-1]
            handler = getattr(self, f"{category}_buy_service")
            await handler(client, callback_query)
        except Exception as e:
            logger.error(f"Error in back_to_category: {e}")
            await callback_query.message.edit_text("❌ خطا در بازگشت به دسته‌بندی!")

    async def back_to_vpn_menu(self, client, callback_query: CallbackQuery):
        try:
            await self.buy_new_service_menu(client, callback_query)
        except Exception as e:
            logger.error(f"Error in back_to_vpn_menu: {e}")
            await callback_query.message.edit_text("❌ خطا در بازگشت به منوی اصلی!")

    async def confirm_purchase(self, client, callback_query: CallbackQuery):
        try:
            package_id = callback_query.data.split("_", 1)[1]
            user_id = callback_query.from_user.id

            if package_id not in self.package_details:
                await callback_query.answer("بسته نامعتبر است!", show_alert=True)
                return

            package = self.package_details[package_id]
            balance = self.user_db.get_balance(user_id)

            # بررسی موجودی
            if balance < package["price"]:
                await callback_query.message.edit_text(
                    "❌ موجودی کیف پول شما کافی نیست!\n"
                    f"موجودی فعلی: {balance:,} تومان\n"
                    f"مبلغ مورد نیاز: {package['price']:,} تومان"
                )
                return

            # ایجاد کاربر در دیتابیس VPN اگر وجود ندارد
            user = callback_query.from_user
            self.vpn_db.create_user_if_not_exists(
                user.id,
                user.first_name,
                user.last_name or "",
                user.username or ""
            )

            try:
                # کسر موجودی
                self.user_db.balance_decrease(user_id, package["price"])

                # ایجاد سرویس
                token = MarzbanService.get_admin_token()
                if not token:
                    raise Exception("خطا در اتصال به پنل مدیریت")

                inbounds = MarzbanService.get_vless_inbound_tags(token)
                if not inbounds:
                    raise Exception("هیچ سرور فعالی یافت نشد")

                service = MarzbanService.create_service(
                    token,
                    user_id,
                    inbounds,
                    package["volume_gb"],
                    package["days"]
                )

                if not service:
                    raise Exception("خطا در ایجاد سرویس در پنل مدیریت")

                # نمایش اطلاعات سرویس
                volume = "نامحدود" if package["volume_gb"] == 0 else f"{package['volume_gb']} گیگابایت"
                days = "مادام‌العمر" if package["days"] == 0 else f"{package['days']} روز"

                text = (
                    "✅ سرویس شما با موفقیت فعال شد!\n\n"
                    f"🔖 نام سرویس: `{service['username']}`\n"
                    f"📦 حجم: {volume}\n"
                    f"⏳ مدت: {days}\n\n"
                    f"🔗 لینک اتصال:\n`{service['subscription_url'] or service['links'][0]}`"
                )

                await callback_query.message.edit_text(text)

                # ارسال پیام به ادمین
                admin_text = (
                    "💳 خرید جدید:\n"
                    f"👤 کاربر: @{user.username or user.id}\n"
                    f"📦 بسته: {package_id}\n"
                    f"💵 مبلغ: {package['price']:,} تومان"
                )
                await client.send_message(Config.ADMIN_ID, admin_text)

            except Exception as e:
                logger.error(f"Error in service creation: {e}")
                # بازگشت موجودی در صورت خطا
                self.user_db.balance_increase(user_id, package["price"])
                await callback_query.message.edit_text(f"❌ خطا در ایجاد سرویس: {str(e)}")

        except Exception as e:
            logger.error(f"Error in confirm_purchase: {e}")
            await callback_query.message.edit_text("❌ خطای سیستمی در پردازش خرید!")