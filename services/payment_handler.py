import logging
from pyrogram import filters
from pyrogram.filters import group
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message
)
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from pyrogram import filters
import uuid
from collections import defaultdict
import asyncio
from pyrogram.errors import BadRequest
from services.marzban_service import MarzbanService
from utils.config import Config
from utils.persian_tools import *
from datetime import *
from database.database_VPN import VpnDatabase
logger = logging.getLogger(__name__)



class PaymentStates:
    GET_AMOUNT = 0
    GET_RECEIPT = 1


class PaymentDataStore:
    def __init__(self):
        self.data = defaultdict(dict)
        self.lock = asyncio.Lock()

    async def store(self, user_id, amount, photo_message_id):
        async with self.lock:
            request_id = str(uuid.uuid4())
            self.data[request_id] = {
                'user_id': user_id,
                'amount': amount,
                'photo_message_id': photo_message_id
            }
            return request_id

    async def retrieve(self, request_id):
        async with self.lock:
            return self.data.get(request_id)

    async def remove(self, request_id):
        async with self.lock:
            if request_id in self.data:
                del self.data[request_id]

class PaymentHandler:
    def __init__(self, bot, user_states, user_locks):  # تغییر سازنده
        self.bot = bot
        self.user_db = VpnDatabase()
        self.db = VpnDatabase()
        self.package_details = Config.PACKAGE_DETAILS
        self.states = {}
        self.user_states = user_states
        self.user_locks = user_locks    # ذخیره user_locks
        self.payment_store = PaymentDataStore()

    def register(self):
        self.register_handlers()

    def register_handlers(self):
        # دسته‌بندی‌های اصلی
        self.bot.add_handler(CallbackQueryHandler(
            self.apply_gift_code,
            filters=filters.regex("^apply_gift_code$")
        ), group=2)

        self.bot.add_handler(MessageHandler(
            self.process_gift_code,
            filters=filters.private & filters.text
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.buy_new_service_menu,
            filters=filters.regex("^buy_new_service_menu$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.gift_code_menu,
            filters=filters.regex("^gift_code_menu$")
        ), group=2)

        # خریدهای مختلف
        self.bot.add_handler(CallbackQueryHandler(
            self.normal_buy_service,
            filters=filters.regex("^normal$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.lifetime_buy_service,
            filters=filters.regex("^lifetime$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.unlimited_buy_service,
            filters=filters.regex("^unlimited$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.longtime_buy_service,
            filters=filters.regex("^longtime$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.handle_package_selection,
            filters=filters.regex(r"^(normal|lifetime|unlimited|longtime)_\d+$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.back_to_category,
            filters=filters.regex(r"^back_to_(normal|lifetime|unlimited|longtime)$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.confirm_purchase,
            filters=filters.regex(r"^confirm_(.*)$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.back_to_vpn_menu,
            filters=filters.regex("^back_to_vpn_menu$")
        ), group=2)

        # مدیریت پول
        self.bot.add_handler(CallbackQueryHandler(
            self.money_managment,
            filters=filters.regex("^money_managment$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.balance_increase_menu,
            filters=filters.regex("^balance_increase_menu$")
        ), group=2)

        # سیستم افزایش موجودی — پیام‌ها و عکس‌ها را در گروه 2 قرار می‌دهیم
        self.bot.add_handler(MessageHandler(
            self.get_amount,
            filters=filters.private & filters.text & filters.regex(r'^\d+$')
        ), group=2)

        self.bot.add_handler(MessageHandler(
            self.get_receipt,
            filters=filters.private & filters.photo
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.cancel_operation,
            filters=filters.regex("^cancel_operation$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.approve_balance,
            filters=filters.regex(r"^approve_balance_\d+_\d+$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.reject_balance,
            filters=filters.regex(r"^reject_balance_\d+$")
        ), group=2)

        self.bot.add_handler(CallbackQueryHandler(
            self.start_balance_increase,
            filters=filters.regex("^start_balance_increase$")
        ), group=2)

        # هندلرهای متنی مرتبط با پرداخت (مثلاً capture amounts)
        self.bot.add_handler(MessageHandler(
            self.handle_amount_message,
            filters=filters.private & filters.text
        ), group=2)

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
            [InlineKeyboardButton("🎫 اعمال کد تخفیف", callback_data="apply_gift_code")],
            [InlineKeyboardButton("🔙 بازگشت", callback_data="money_managment")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "🎁 برای استفاده از کد تخفیف، آن را وارد کنید"
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
            self.db.create_user_if_not_exists(
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
                self.db.add_user_service(
                    user_id,
                    service["username"],
                    package_id,
                    package["volume_gb"],
                    expire_date
                )


                url = "https://t.me/incel_help"
                keyboard = [
                    [InlineKeyboardButton("راهنمای استفاده",url=url)],
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                await callback_query.message.edit_text(text,reply_markup=reply_markup)

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

        # تنظیم حالت در هر دو سیستم برای سازگاری
        self.states[user_id] = {"state": PaymentStates.GET_AMOUNT}
        self.user_states[user_id] = {"state": "waiting_for_amount"}

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

    async def handle_amount_message(self, client, message: Message):
        user_id = message.from_user.id

        # ایجاد قفل برای هر کاربر
        if user_id not in self.user_locks:
            self.user_locks[user_id] = asyncio.Lock()

        async with self.user_locks[user_id]:
            # بررسی حالت کاربر
            if user_id not in self.user_states or self.user_states[user_id].get("state") != "waiting_for_amount":
                return

            try:
                # تبدیل مبلغ به عدد (حذف کاما و کاراکترهای غیرعددی)
                amount_text = message.text.replace(',', '').replace('٬', '').strip()
                amount = float(amount_text)

                # بررسی محدوده مجاز مبلغ
                if amount < 50000 or amount > 500000:
                    await message.reply_text(
                        "⚠️ مبلغ باید بین ۵۰,۰۰۰ تا ۵۰۰,۰۰۰ تومان باشد.\n"
                        "لطفاً دوباره وارد کنید:"
                    )
                    return

                # ذخیره مبلغ و تغییر حالت کاربر
                self.user_states[user_id] = {
                    "state": "waiting_for_receipt",
                    "amount": amount
                }

                # ارسال اطلاعات کارت برای واریز
                bank_info = (
                    f"💳 **افزایش موجودی: {amount:,.0f} تومان**\n\n"
                    "لطفاً مبلغ را به شماره کارت زیر واریز کنید:\n"
                    "`6219 8618 0441 5460`\n\n"
                    "🏦 بانک: سامان\n"
                    "👤 به نام: ابوالفضل تشکری\n\n"
                    "📸 پس از واریز، عکس رسید بانکی را ارسال کنید."
                )

                reply_markup = InlineKeyboardMarkup([
                    [InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_operation")]
                ])

                await message.reply_text(bank_info, reply_markup=reply_markup)

            except ValueError:
                await message.reply_text("⚠️ لطفاً یک عدد معتبر وارد کنید (مثال: 50000):")

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

    async def cancel_operation(self, client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id

        # پاکسازی همه حالت‌های کاربر
        if user_id in self.states:
            del self.states[user_id]
        if user_id in self.user_states:
            del self.user_states[user_id]

        await callback_query.message.edit_text("❌ عملیات لغو شد")

        # بازگشت به منوی مدیریت پول
        await self.money_managment(client, callback_query)

    async def get_receipt(self, client, message: Message):
        user_id = message.from_user.id

        # تعیین مبلغ بر اساس سیستم state مورد استفاده
        if user_id in self.states and self.states[user_id]["state"] == PaymentStates.GET_RECEIPT:
            amount = self.states[user_id]["amount"]
            # پاکسازی حالت قدیم
            del self.states[user_id]
        elif user_id in self.user_states and self.user_states[user_id].get("state") == "waiting_for_receipt":
            amount = self.user_states[user_id].get("amount", 0)
            # پاکسازی حالت جدید
            del self.user_states[user_id]
        else:
            return

        user = message.from_user

        # ارسال رسید به ادمین
        admin_text = f"""
    📤 *درخواست افزایش موجودی*

    👤 کاربر: {user.first_name} (@{user.username or 'بدون نام کاربری'})
    🆔 آیدی: `{user.id}`
    💵 مبلغ: {amount:,} تومان

    لطفاً تأیید یا رد کنید:
        """

        amount_int = int(float(amount))
        keyboard = [
            [
                InlineKeyboardButton("✅ تأیید", callback_data=f"approve_balance_{user_id}_{amount_int}"),
                InlineKeyboardButton("❌ رد", callback_data=f"reject_balance_{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        try:
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
        except Exception as e:
            logger.error(f"Error sending receipt to admin: {e}")
            await message.reply_text("⚠️ خطا در ارسال رسید! لطفاً دوباره تلاش کنید.")

    async def approve_balance(self, client, callback_query: CallbackQuery):
        logger.info(f"Approving balance: {callback_query.data}")
        try:
            parts = callback_query.data.split('_')
            user_id = int(parts[2])
            amount_str = parts[3].replace(',', '').replace('٬', '')
            amount = int(float(amount_str))

            db = VpnDatabase()
            db.balance_increase(user_id, amount)
            new_balance = db.get_balance(user_id)
            db.close()

            # ارسال پیام به کاربر
            try:
                await client.send_message(
                    user_id,
                    f"✅ موجودی حساب شما افزایش یافت!\n\n"
                    f"💵 مبلغ واریزی: {amount:,} تومان\n"
                    f"💰 موجودی جدید: {new_balance:,} تومان"
                )
            except Exception as e:
                logger.error(f"Error sending message to user {user_id}: {e}")
                # اطلاع به ادمین در صورت عدم موفقیت
                await callback_query.message.reply_text(
                    f"⚠️ ارسال پیام به کاربر {user_id} ناموفق بود. لطفاً به صورت دستی اطلاع دهید."
                )

            # ویرایش پیام ادمین
            try:
                # سعی در ویرایش کپشن اصلی
                await callback_query.message.edit_caption(
                    caption=f"✅ موجودی کاربر افزایش یافت\n"
                            f"👤 کاربر: {user_id}\n"
                            f"💵 مبلغ: {amount:,} تومان",
                    reply_markup=None  # حذف دکمه‌ها
                )
            except BadRequest:
                # اگر ویرایش کپشن ممکن نبود، یک پیام جدید ارسال کنید
                await callback_query.message.reply_text(
                    f"✅ موجودی کاربر {user_id} افزایش یافت. مبلغ: {amount:,} تومان"
                )

            await callback_query.answer("✅ موجودی کاربر افزایش یافت")

        except Exception as e:
            logger.error(f"Error in approve_balance: {e}")
            await callback_query.answer("⚠️ خطا در پردازش تأیید! لطفاً دوباره امتحان کنید", show_alert=True)

    async def reject_balance(self, client, callback_query: CallbackQuery):
        try:
            # استخراج user_id از callback_data
            parts = callback_query.data.split('_')
            user_id = int(parts[2])

            # ارسال پیام به کاربر
            try:
                await client.send_message(
                    user_id,
                    "⚠️ درخواست افزایش موجودی شما رد شد\n"
                    "❌ لطفاً با پشتیبانی تماس بگیرید"
                )
            except Exception as e:
                logger.error(f"Error sending rejection message to user {user_id}: {e}")
                await callback_query.message.reply_text(
                    f"⚠️ ارسال پیام رد به کاربر {user_id} ناموفق بود."
                )

            # ویرایش پیام ادمین
            try:
                await callback_query.message.edit_caption(
                    caption="❌ درخواست افزایش موجودی رد شد",
                    reply_markup=None
                )
            except BadRequest:
                await callback_query.message.reply_text(
                    f"❌ درخواست افزایش موجودی کاربر {user_id} رد شد."
                )

            await callback_query.answer("❌ درخواست افزایش موجودی رد شد")

        except Exception as e:
            logger.error(f"Error in reject_balance: {e}")
            await callback_query.answer("⚠️ خطا در پردازش رد درخواست!", show_alert=True)

    async def process_gift_code(self, client, message: Message):
        user_id = message.from_user.id

        if user_id not in self.user_states or self.user_states[user_id].get("state") != "waiting_for_gift_code":
            return

        try:
            code = message.text.strip().upper()
            db = VpnDatabase()

            # بررسی اعتبار کد
            result = db.is_gift_code_valid(code)
            if not result[0]:
                await message.reply_text(f"❌ {result[1]}")
                return

            is_valid, amount, gift_id = result
            if not is_valid:
                await message.reply_text(f"❌ {amount}")
                return

            # بررسی استفاده قبلی کاربر از کد
            if db.has_used_gift_code(user_id, gift_id):
                await message.reply_text("❌ شما قبلاً از این کد استفاده کرده‌اید!")
                return

            # افزودن موجودی
            added_amount = db.use_gift_code(user_id, gift_id)
            new_balance = db.get_balance(user_id)

            text = f"""
    🎉 کد تخفیف با موفقیت اعمال شد!

    🪪 کد: `{code}`
    💰 مبلغ اضافه شده: {added_amount:,} تومان
    💳 موجودی جدید: {new_balance:,} تومان
            """

            keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="money_managment")]]
            await message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

            # پاکسازی state
            if user_id in self.user_states:
                del self.user_states[user_id]

        except Exception as e:
            logger.error(f"Error applying gift code: {e}")
            await message.reply_text("⚠️ خطا در پردازش کد! لطفاً مجدداً تلاش کنید")

    async def apply_gift_code(self, client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id

        # پاکسازی هر state قبلی
        if user_id in self.user_states:
            del self.user_states[user_id]

        # تنظیم state جدید برای کد هدیه
        self.user_states[user_id] = {"state": "waiting_for_gift_code"}

        keyboard = [[InlineKeyboardButton("❌ لغو", callback_data="cancel_operation")]]
        await callback_query.message.edit_text(
            "🎁 لطفاً کد تخفیف خود را وارد کنید:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )