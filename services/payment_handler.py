import logging
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message
)

from pyrogram.errors import BadRequest
from services.marzban_service import MarzbanService
from utils.config import Config
from utils.persian_tools import *
from datetime import *
from database.database_VPN import VpnDatabase
from main import *
logger = logging.getLogger(__name__)



class PaymentStates:
    GET_AMOUNT = 0
    GET_RECEIPT = 1


class PaymentHandler:
    def __init__(self, bot):
        self.bot = bot
        self.user_db = VpnDatabase()
        self.db = VpnDatabase()
        self.package_details = Config.PACKAGE_DETAILS
        self.states = {}

    def register(self):
        self.register_handlers()

    def register_handlers(self):
        # دسته‌بندی‌های اصلی
        self.bot.add_handler(CallbackQueryHandler(
            self.buy_new_service_menu,
            filters.regex("^buy_new_service_menu$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.normal_buy_service,
            filters.regex("^normal$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.lifetime_buy_service,
            filters.regex("^lifetime$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.unlimited_buy_service,
            filters.regex("^unlimited$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.longtime_buy_service,
            filters.regex("^longtime$")
        ))

        self.bot.add_handler(CallbackQueryHandler(
            self.apply_gift_code,
            filters.regex("^apply_gift_code$")
        ))
        self.bot.add_handler(MessageHandler(
            self.process_gift_code,
            filters.private & filters.text
        ))

        # بسته‌های خاص
        self.bot.add_handler(CallbackQueryHandler(
            self.handle_package_selection,
            filters.regex(r"^(normal|lifetime|unlimited|longtime)_\d+$")
        ))

        # بازگشت و تایید
        self.bot.add_handler(CallbackQueryHandler(
            self.back_to_category,
            filters.regex(r"^back_to_(normal|lifetime|unlimited|longtime)$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.confirm_purchase,
            filters.regex(r"^confirm_(.*)$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.back_to_vpn_menu,
            filters.regex("^back_to_vpn_menu$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.money_managment,
            filters.regex("^money_managment$")
        ))

        self.bot.add_handler(CallbackQueryHandler(
            self.balance_increase_menu,
            filters.regex("^balance_increase_menu$")
        ))

        # سیستم افزایش موجودی
        self.bot.add_handler(MessageHandler(
            self.get_amount,
            filters.private & filters.text & filters.regex(r'^\d+$')
        ))
        self.bot.add_handler(MessageHandler(
            self.get_receipt,
            filters.private & filters.photo
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.cancel_operation,
            filters.regex("^cancel_operation$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.approve_balance,
            filters.regex(r"^approve_balance_(\d+)_(\d+)$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.start_balance_increase,
            filters.regex("^start_balance_increase$")
        ))
        self.bot.add_handler(CallbackQueryHandler(
            self.reject_balance,
            filters.regex(r"^reject_balance_(\d+)$")
        ))

    async def money_managment(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("💰 افزایش موجودی", callback_data="balance_increase_menu"),InlineKeyboardButton("کد هدیه",callback_data="gift_code_menu")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")],
            ]

            user_id = callback_query.from_user.id
            user_info = self.db.get_user_info(user_id)

            if not user_info:
                await callback_query.answer("❌ اطلاعات کاربر یافت نشد!")
                return

            # تبدیل تاریخ به شمسی
            join_date = to_jalali(user_info[5])
            current_date = to_jalali(datetime.now())

            text = f"""
📊 *اطلاعات حساب کاربری شما*

🆔 **شناسه کاربری:** `{user_info[0]}`
👤 **نام:** {user_info[1]} {user_info[2] or ''}
🎫 **کد معرف:** `{user_info[3] or 'ندارد'}`
📞 **شماره تماس:** {user_info[4] or '❌ ارسال نشده'}
📅 **زمان ثبت نام:** {join_date}
💰 **موجودی:** {user_info[6]:,} تومان
🛒 **سرویس‌های فعال:** {user_info[7]} عدد
🧾 **فاکتورهای پرداختی:** {user_info[8]} عدد
👥 **زیرمجموعه‌ها:** {user_info[9]} نفر
🔰 **گروه کاربری:** {user_info[10]}

⏰ {current_date} → 🕒 {datetime.now().strftime('%H:%M:%S')}
            """
            reply_markup = InlineKeyboardMarkup(keyboard)

            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(e)
            await callback_query.message.edit_text("⚠️ خطا در نمایش اطلاعات حساب!")

    async def gift_code_menu(self, client, callback_query: CallbackQuery):
        keyboard = [
            [InlineKeyboardButton("🎫 اعمال کد هدیه", callback_data="apply_gift_code")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="money_managment")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "🎁 برای دریافت هدیه کد خود را وارد کنید"
        await callback_query.message.edit_text(text, reply_markup=reply_markup)

    async def balance_increase_menu(self, client, callback_query: CallbackQuery):
        keyboard = [
            [InlineKeyboardButton("💳 کارت به کارت", callback_data="start_balance_increase")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="money_managment")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "📥 برای افزایش موجودی از طریق کارت به کارت، گزینه زیر را انتخاب کنید:"
        await callback_query.message.edit_text(text, reply_markup=reply_markup)

    async def buy_new_service_menu(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("📦 بسته‌های عادی", callback_data="normal")],
                [InlineKeyboardButton("♾️ بسته‌های لایف‌تایم", callback_data="lifetime")],
                [InlineKeyboardButton("🗓️ بسته‌های بلند مدت", callback_data="longtime")],
                #[InlineKeyboardButton("🚀 بسته‌های نامحدود", callback_data="unlimited")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "🎯 لطفا نوع سرویس مورد نظر خود را انتخاب کنید:"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in buy_new_service_menu: {e}")
            await callback_query.message.edit_text("⚠️ خطا در نمایش منو سرویس‌ها!")

    async def normal_buy_service(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("📦 ۲۰ گیگابایت | ۱ ماه | ۵۰,۰۰۰ تومان", callback_data="normal_1")],
                [InlineKeyboardButton("📦 ۵۰ گیگابایت | ۱ ماه | ۱۱۰,۰۰۰ تومان", callback_data="normal_2")],
                [InlineKeyboardButton("📦 ۱۰۰ گیگابایت | ۱ ماه | ۱۹۰,۰۰۰ تومان", callback_data="normal_3")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_vpn_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "📦 لطفا بسته مورد نظر خود را انتخاب کنید:"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in normal_buy_service: {e}")
            await callback_query.message.edit_text("⚠️ خطا در نمایش بسته‌های عادی!")

    async def lifetime_buy_service(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("♾️ ۱۰ گیگابایت | مادام‌العمر | ۳۵,۰۰۰ تومان", callback_data="lifetime_1")],
                [InlineKeyboardButton("♾️ ۲۰ گیگابایت | مادام‌العمر | ۶۰,۰۰۰ تومان", callback_data="lifetime_2")],
                [InlineKeyboardButton("♾️ ۵۰ گیگابایت | مادام‌العمر | ۱۶۰,۰۰۰ تومان", callback_data="lifetime_3")],
                [InlineKeyboardButton("♾️ ۱۰۰ گیگابایت | مادام‌العمر | ۳۶۰,۰۰۰ تومان", callback_data="lifetime_4")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_vpn_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "♾️ لطفا بسته مورد نظر خود را انتخاب کنید:"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in lifetime_buy_service: {e}")
            await callback_query.message.edit_text("⚠️ خطا در نمایش بسته‌های لایف‌تایم!")



    async def unlimited_buy_service(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("🚀 ۱ کاربر | ۱ ماه | ۹۵,۰۰۰ تومان", callback_data="unlimited_1")],
                [InlineKeyboardButton("🚀 ۲ کاربر | ۱ ماه | ۱۴۵,۰۰۰ تومان", callback_data="unlimited_2")],
                [InlineKeyboardButton("🚀 ۱ کاربر | ۲ ماه | ۱۸۰,۰۰۰ تومان", callback_data="unlimited_3")],
                [InlineKeyboardButton("🚀 ۲ کاربر | ۲ ماه | ۲۴۰,۰۰۰ تومان", callback_data="unlimited_4")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_vpn_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "🚀 لطفا بسته مورد نظر خود را انتخاب کنید:"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in unlimited_buy_service: {e}")
            await callback_query.message.edit_text("⚠️ خطا در نمایش بسته‌های نامحدود!")

    async def longtime_buy_service(self, client, callback_query: CallbackQuery):
        try:
            keyboard = [
                [InlineKeyboardButton("🗓️ ۵۰ گیگابایت | ۲ ماه | ۱۳۵,۰۰۰ تومان", callback_data="longtime_1")],
                [InlineKeyboardButton("🗓️ ۱۰۰ گیگابایت | ۲ ماه | ۲۶۰,۰۰۰ تومان", callback_data="longtime_2")],
                [InlineKeyboardButton("🗓️ ۱۵۰ گیگابایت | ۲ ماه | ۳۷۵,۰۰۰ تومان", callback_data="longtime_3")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_vpn_menu")],
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            text = "🗓️ لطفا بسته مورد نظر خود را انتخاب کنید:"
            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(f"Error in longtime_buy_service: {e}")
            await callback_query.message.edit_text("⚠️ خطا در نمایش بسته‌های بلند مدت!")

    async def handle_package_selection(self, client, callback_query: CallbackQuery):
        try:
            package_id = callback_query.data
            if package_id not in self.package_details:
                await callback_query.answer("⚠️ بسته مورد نظر یافت نشد!", show_alert=True)
                return

            package = self.package_details[package_id]

            if package["volume_gb"] == 0:
                volume_display = "♾️ نامحدود"
            else:
                volume_display = f"📦 {package['volume_gb']:,.0f} گیگابایت"

            days = "♾️ مادام‌العمر" if package["days"] == 0 else f"🗓️ {package['days']} روز"

            text = f"""
📦 *جزئیات بسته انتخابی*

{volume_display}
{days}
💵 قیمت: {package['price']:,} تومان

✅ آیا از خرید این بسته اطمینان دارید؟
            """

            keyboard = [
                [InlineKeyboardButton("✅ تایید و پرداخت", callback_data=f"confirm_{package_id}")],
                [InlineKeyboardButton("🔙 بازگشت", callback_data=f"back_to_{package_id.split('_')[0]}")]
            ]

            await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))
        except Exception as e:
            logger.error(f"Error in handle_package_selection: {e}")
            await callback_query.message.edit_text("⚠️ خطا در نمایش جزئیات بسته!")

    async def back_to_category(self, client, callback_query: CallbackQuery):
        try:
            category = callback_query.data.split("_")[-1]
            handler = getattr(self, f"{category}_buy_service")
            await handler(client, callback_query)
        except Exception as e:
            logger.error(f"Error in back_to_category: {e}")
            await callback_query.message.edit_text("⚠️ خطا در بازگشت به دسته‌بندی!")

    async def back_to_vpn_menu(self, client, callback_query: CallbackQuery):
        try:
            await self.buy_new_service_menu(client, callback_query)
        except Exception as e:
            logger.error(f"Error in back_to_vpn_menu: {e}")
            await callback_query.message.edit_text("⚠️ خطا در بازگشت به منو اصلی!")

    async def confirm_purchase(self, client, callback_query: CallbackQuery):
        try:
            package_id = callback_query.data.split("_", 1)[1]
            user_id = callback_query.from_user.id

            if package_id not in self.package_details:
                await callback_query.answer("⚠️ بسته نامعتبر است!", show_alert=True)
                return

            package = self.package_details[package_id]
            balance = self.user_db.get_balance(user_id)

            # بررسی موجودی
            if balance < package["price"]:
                await callback_query.message.edit_text(
                    "⚠️ *موجودی ناکافی!*\n\n"
                    f"💰 موجودی فعلی: {balance:,} تومان\n"
                    f"💵 مبلغ مورد نیاز: {package['price']:,} تومان\n\n"
                    "لطفاً از بخش افزایش موجودی استفاده کنید"
                )
                return

            # ایجاد کاربر در دیتابیس VPN
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
                    raise Exception("🔴 خطا در اتصال به پنل مدیریت")

                inbounds = MarzbanService.get_vless_inbound_tags(token)
                if not inbounds:
                    raise Exception("🔴 هیچ سرور فعالی یافت نشد")

                service = MarzbanService.create_service(
                    token,
                    user_id,
                    inbounds,
                    package["volume_gb"],
                    package["days"]
                )

                if not service:
                    raise Exception("🔴 خطا در ایجاد سرویس")

                # نمایش اطلاعات سرویس
                volume = "♾️ نامحدود" if package["volume_gb"] == 100 else f"📦 {package['volume_gb']} گیگابایت"
                days = "♾️ مادام‌العمر" if package["days"] == 0 else f"🗓️ {package['days']} روز"

                text = f"""
🎉 **خرید با موفقیت انجام شد!**

✅ سرویس شما فعال شد
🆔 شناسه سرویس: `{service['username']}`
{volume} | {days}
🔗 لینک اتصال: 
`{service['subscription_url'] or service['links'][0]}`
                """
                self.user_db.increment_purchase_count(user_id)
                self.user_db.increment_invoice_count(user_id)
                expire_date = int((datetime.now(timezone.utc) + timedelta(days=package["days"])).timestamp())
                self.vpn_db.add_user_service(
                    user_id,
                    service["username"],
                    package_id,
                    package["volume_gb"],
                    expire_date
                )

                await callback_query.message.edit_text(text)

                # ارسال پیام به ادمین
                admin_text = (
                    "🛒 *خرید جدید ثبت شد!*\n\n"
                    f"👤 کاربر: @{user.username or user.id}\n"
                    f"📦 بسته: {package_id}\n"
                    f"💵 مبلغ: {package['price']:,} تومان"
                )
                await client.send_message(Config.ADMIN_ID, admin_text)

            except Exception as e:
                logger.error(f"Error in service creation: {e}")
                # بازگشت موجودی در صورت خطا
                self.user_db.balance_increase(user_id, package["price"])
                await callback_query.message.edit_text(f"⚠️ خطا در ایجاد سرویس: {str(e)}")

        except Exception as e:
            logger.error(f"Error in confirm_purchase: {e}")
            await callback_query.message.edit_text("⚠️ خطای سیستمی در پردازش خرید!")

    async def start_balance_increase(self, client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        self.states[user_id] = {"state": PaymentStates.GET_AMOUNT}

        # تنظیم حالت در user_states
        user_states[user_id] = {"state": "waiting_for_amount"}  # اضافه شده

        text = """
    💳 *افزایش موجودی*

    لطفاً مبلغ مورد نظر را وارد کنید:
    • ✅ حداقل: ۵۰,۰۰۰ تومان
    • ✅ حداکثر: ۵۰۰,۰۰۰ تومان

    ❌ برای لغو عملیات از دکمه زیر استفاده کنید
        """

        keyboard = [[InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_operation")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await callback_query.message.edit_text(text, reply_markup=reply_markup)

    async def get_amount(self, client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.states or self.states[user_id]["state"] != PaymentStates.GET_AMOUNT:
            return

        try:
            amount = int(message.text)
            if amount < 50000:
                await message.reply_text("⚠️ مبلغ وارد شده کمتر از حد مجاز است (حداقل ۵۰,۰۰۰ تومان)")
                return
            if amount > 500000:
                await message.reply_text("⚠️ مبلغ وارد شده بیشتر از حد مجاز است (حداکثر ۵۰۰,۰۰۰ تومان)")
                return

            self.states[user_id] = {
                "state": PaymentStates.GET_RECEIPT,
                "amount": amount
            }

            # اطلاعات کارت برای پرداخت
            card_info = """
💳 *اطلاعات حساب برای واریز*

🏦 بانک: سامان
🔢 شماره کارت: `5460-0441-8618-6219`
👤 به نام: ابوالفضل تشکری

📸 لطفاً پس از واریز، عکس رسید پرداختی را ارسال کنید
            """

            keyboard = [[InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_operation")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(card_info, reply_markup=reply_markup)

        except ValueError:
            await message.reply_text("⚠️ لطفاً فقط عدد وارد کنید (مثال: 100000)")

    async def get_receipt(self, client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.states or self.states[user_id]["state"] != PaymentStates.GET_RECEIPT:
            return

        amount = self.states[user_id]["amount"]
        user = message.from_user

        # ارسال رسید به ادمین
        admin_text = f"""
📤 *درخواست افزایش موجودی*

👤 کاربر: {user.first_name} (@{user.username})
🆔 آیدی: `{user.id}`
💵 مبلغ: {amount:,} تومان

لطفاً تأیید یا رد کنید:
        """

        keyboard = [
            [
                InlineKeyboardButton("✅ تأیید", callback_data=f"approve_balance_{user_id}_{amount}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_balance_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # ارسال عکس و اطلاعات به ادمین
        await client.send_photo(
            Config.ADMIN_ID,
            message.photo.file_id,
            caption=admin_text,
            reply_markup=reply_markup
        )

        # پاسخ به کاربر
        await message.reply_text(
            "✅ رسید شما با موفقیت ارسال شد\n"
            "⏳ پس از تأیید ادمین، موجودی حساب شما افزایش خواهد یافت"
        )

        # پاکسازی حالت کاربر
        del self.states[user_id]

    async def cancel_operation(self, client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        if user_id in self.states:
            del self.states[user_id]
        if user_id in user_states:  # اضافه شده
            del user_states[user_id]
        await callback_query.message.edit_text("❌ عملیات لغو شد")

    async def approve_balance(self, client, callback_query: CallbackQuery):
        data = callback_query.data.split('_')
        user_id = int(data[2])
        amount = int(data[3])

        db = VpnDatabase()
        db.balance_increase(user_id, amount)
        new_balance = db.get_balance(user_id)

        await client.send_message(
            user_id,
            f"✅ موجودی حساب شما افزایش یافت!\n\n"
            f"💵 مبلغ واریزی: {amount:,} تومان\n"
            f"💰 موجودی جدید: {new_balance:,} تومان"
        )

        await callback_query.message.edit_caption(
            f"✅ موجودی کاربر افزایش یافت\n"
            f"💵 مبلغ: {amount:,} تومان"
        )
        await callback_query.answer("✅ موجودی کاربر افزایش یافت")

    async def reject_balance(self, client, callback_query: CallbackQuery):
        data = callback_query.data.split('_')
        user_id = int(data[2])

        # ارسال پیام به کاربر
        try:
            await client.send_message(
                user_id,
                "⚠️ درخواست افزایش موجودی شما رد شد\n"
                "❌ لطفاً با پشتیبانی تماس بگیرید"
            )
        except Exception as e:
            logger.error(f"Error sending rejection message: {e}")

        # ویرایش پیام ادمین
        await callback_query.message.edit_caption("❌ درخواست افزایش موجودی رد شد")

    async def apply_gift_code(self, client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        self.states[user_id] = {"state": "WAITING_FOR_GIFT_CODE"}

        keyboard = [[InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_operation")]]
        await callback_query.message.edit_text(
            "🎁 لطفاً کد هدیه خود را وارد کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    # متد جدید برای پردازش کد هدیه
    async def process_gift_code(self, client, message: Message):
        user_id = message.from_user.id
        state = self.states.get(user_id, {})

        if state.get("state") != "WAITING_FOR_GIFT_CODE":
            return

        try:
            code = message.text.strip()
            db = VpnDatabase()

            # دریافت اطلاعات کد از دیتابیس
            gift_code = db.get_gift_code(code)
            if not gift_code:
                await message.reply_text("❌ کد هدیه نامعتبر است!")
                return

            gift_code_id, _, amount, usage_limit, used_count, _ = gift_code

            # بررسی محدودیت استفاده
            if used_count >= usage_limit:
                await message.reply_text("⚠️ تعداد دفعات استفاده از این کد به پایان رسیده است")
                return

            # بررسی اینکه کاربر قبلاً از این کد استفاده نکرده باشد
            if db.has_used_gift_code(user_id, gift_code_id):
                await message.reply_text("⚠️ شما قبلاً از این کد استفاده کرده‌اید")
                return

            # اعمال کد
            added_amount = db.use_gift_code(user_id, gift_code_id)
            new_balance = db.get_balance(user_id)

            # نمایش نتیجه به کاربر
            text = f"""
            🎉 کد هدیه با موفقیت اعمال شد!

            🪪 کد: `{code}`
            💰 مبلغ اضافه شده: {added_amount:,} تومان
            💳 موجودی جدید: {new_balance:,} تومان
                """

            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="money_managment")]]
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

            # پاک کردن حالت
            self.states.pop(user_id, None)

        except Exception as e:
            logger.error(f"Error applying gift code: {e}")
            await message.reply_text("⚠️ خطا در پردازش کد! لطفاً مجدداً تلاش کنید")