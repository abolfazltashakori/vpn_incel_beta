import logging
from pyrogram import filters
from pyrogram.handlers import MessageHandler, CallbackQueryHandler  # اضافه شده
from pyrogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    CallbackQuery,
    Message  # اضافه شده
)

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
                [InlineKeyboardButton("افزایش موجودی", callback_data="balance_increase_menu")],
                [InlineKeyboardButton("بازگشت", callback_data="back_to_menu")],
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
            reply_markup = InlineKeyboardMarkup(keyboard)

            await callback_query.message.edit_text(text, reply_markup=reply_markup)
        except Exception as e:
            logger.error(e)
            await callback_query.message.edit_text("❌ خطا در نمایش منو!")

    async def balance_increase_menu(self, client, callback_query: CallbackQuery):
        keyboard = [
            [InlineKeyboardButton("کارت به کارت", callback_data="start_balance_increase")],
            [InlineKeyboardButton("بازگشت", callback_data="money_managment")],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = "برای افزایش موجودی از طریق کارت به کارت، گزینه زیر را انتخاب کنید:"
        await callback_query.message.edit_text(text, reply_markup=reply_markup)

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

            # تغییرات در این بخش
            if package["volume_gb"] == 0:
                volume_display = "نامحدود"
            else:
                # نمایش حجم به صورت عددی با فرمت مناسب
                volume_display = f"{package['volume_gb']:,.0f} گیگابایت"

            days = "مادام‌العمر" if package["days"] == 0 else f"{package['days']} روز"

            text = (
                "📦 جزئیات بسته انتخابی:\n\n"
                f"• حجم: {volume_display}\n"  # استفاده از متغیر اصلاح شده
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
                volume = "نامحدود" if package["volume_gb"] == 100 else f"{package['volume_gb']} گیگابایت"
                days = "مادام‌العمر" if package["days"] == 0 else f"{package['days']} روز"

                text = f"""
                💳 **خرید شما ثبت شد!**

                ✅ سرویس با موفقیت فعال شد
                📝 شناسه سرویس: `{service['username']}`
                🗓️ مدت اعتبار: {days}
                📦 حجم ماهانه: {volume}
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






    async def start_balance_increase(self, client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        self.states[user_id] = {"state": PaymentStates.GET_AMOUNT}

        text = (
            "💰 لطفا مبلغ مورد نظر برای افزایش موجودی را وارد کنید:\n\n"
            "⚠️ حداقل مبلغ: 50,000 تومان\n"
            "⚠️ حداکثر مبلغ: 500,000 تومان\n\n"
            "❌ برای لغو از دکمه زیر استفاده کنید"
        )

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
                await message.reply_text("❌ مبلغ وارد شده کمتر از حد مجاز است (50,000 تومان)")
                return
            if amount > 500000:
                await message.reply_text("❌ مبلغ وارد شده بیشتر از حد مجاز است (500,000 تومان)")
                return

            self.states[user_id] = {
                "state": PaymentStates.GET_RECEIPT,
                "amount": amount
            }

            # اطلاعات کارت برای پرداخت
            card_info = (
                "💳 لطفا مبلغ به حساب زیر واریز کنید:\n\n"
                "بانک: ملت\n"
                "شماره کارت: 6037-9972-1234-5678\n"
                "به نام: محمد احمدی\n\n"
                "📸 سپس عکس رسید پرداختی خود را ارسال کنید"
            )

            keyboard = [[InlineKeyboardButton("❌ لغو عملیات", callback_data="cancel_operation")]]
            reply_markup = InlineKeyboardMarkup(keyboard)

            await message.reply_text(card_info, reply_markup=reply_markup)

        except ValueError:
            await message.reply_text("❌ لطفا فقط عدد وارد کنید (مثال: 100000)")

    async def get_receipt(self, client, message: Message):
        user_id = message.from_user.id
        if user_id not in self.states or self.states[user_id]["state"] != PaymentStates.GET_RECEIPT:
            return

        amount = self.states[user_id]["amount"]
        user = message.from_user

        # ارسال رسید به ادمین
        admin_text = (
            "📨 درخواست افزایش موجودی:\n\n"
            f"👤 کاربر: {user.first_name} (@{user.username})\n"
            f"🆔 ID: {user.id}\n"
            f"💰 مبلغ: {amount:,} تومان\n\n"
            "لطفا تایید یا رد کنید:"
        )

        keyboard = [
            [
                InlineKeyboardButton("✅ تایید", callback_data=f"approve_balance_{user_id}_{amount}"),
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
            "✅ رسید شما با موفقیت ارسال شد. پس از تایید ادمین، موجودی شما افزایش خواهد یافت."
        )

        # پاکسازی حالت کاربر
        del self.states[user_id]

    async def cancel_operation(self, client, callback_query: CallbackQuery):
        user_id = callback_query.from_user.id
        if user_id in self.states:
            del self.states[user_id]

        await callback_query.message.edit_text("❌ عملیات لغو شد.")

    async def approve_balance(self, client, callback_query: CallbackQuery):
        data = callback_query.data.split('_')
        user_id = int(data[2])
        amount = int(data[3])

        db = VpnDatabase()
        db.balance_increase(user_id, amount)

        # Get balance BEFORE closing connection
        new_balance = db.get_balance(user_id)  # ✅ Get value while connection is open


        await client.send_message(
            user_id,
            f"✅ موجودی حساب شما به مبلغ {amount:,} تومان افزایش یافت.\n\n"
            f"💰 موجودی جدید: {new_balance:,} تومان"  # Use stored value
        )

        await callback_query.message.edit_caption(
            f"✅ موجودی کاربر افزایش یافت.\n💰 مبلغ: {amount:,} تومان"
        )
        await callback_query.answer("موجودی کاربر افزایش یافت")

    async def reject_balance(self, client, callback_query: CallbackQuery):
        data = callback_query.data.split('_')
        user_id = int(data[2])

        # ارسال پیام به کاربر
        try:
            await client.send_message(
                user_id,
                "❌ درخواست افزایش موجودی شما توسط ادمین رد شد."
            )
        except Exception as e:
            logger.error(f"Error sending rejection message: {e}")

        # ویرایش پیام ادمین
        await callback_query.message.edit_caption("❌ درخواست افزایش موجودی رد شد.")