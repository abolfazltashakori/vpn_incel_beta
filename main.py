# main.py (بازنویسی کامل)
import sys
import os
import logging
from pyrogram import Client, filters, idle
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, KeyboardButton, \
    ReplyKeyboardMarkup
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from datetime import datetime
from database.database_VPN import VpnDatabase
from services.vpn_handler import VpnHandler
from services.payment_handler import PaymentHandler
from services.admin_menu import AdminMenu
from utils.config import Config
import asyncio
from collections import defaultdict

# تنظیمات logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class VPNBot:
    def __init__(self):
        self.bot = Client(
            "vpn_service_bot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )

        # متغیرهای state
        self.user_states = defaultdict(dict)
        self.user_locks = defaultdict(asyncio.Lock)

        # نمونه‌های هندلر
        self.vpn_handler = None
        self.payment_handler = None
        self.admin_menu = None

        # دیتابیس
        self.db = VpnDatabase()

    async def start(self):
        """شروع و راه‌اندازی ربات"""
        try:
            # راه‌اندازی هندلرها
            self.setup_handlers()

            # شروع ربات
            await self.bot.start()
            logger.info("🤖 ربات VPN راه‌اندازی شد")

            # نگه‌داشتن ربات در حال اجرا
            await idle()

        except Exception as e:
            logger.exception(f"خطا در راه‌اندازی ربات: {e}")
        finally:
            await self.stop()

    async def stop(self):
        """توقف ربات و تمیز کردن منابع"""
        try:
            await self.bot.stop()
            self.db.close()
            logger.info("✅ ربات متوقف شد و منابع آزاد گردید")
        except Exception as e:
            logger.error(f"خطا در توقف ربات: {e}")

    def setup_handlers(self):
        """تنظیم و ثبت تمامی هندلرها"""
        # ایجاد نمونه‌های هندلر
        self.vpn_handler = VpnHandler(self.bot)
        self.payment_handler = PaymentHandler(self.bot, self.user_states, self.user_locks)
        self.admin_menu = AdminMenu(self.bot)

        # ثبت هندلرهای اصلی
        self.bot.add_handler(MessageHandler(self.start_command, filters.command("start")))
        self.bot.add_handler(MessageHandler(self.home_command, filters.text & filters.regex("^🏠 خانه$")))

        # ثبت هندلرهای بازگشت به منو
        self.bot.add_handler(CallbackQueryHandler(self.back_to_menu, filters.regex("^back_to_menu$")))
        self.bot.add_handler(CallbackQueryHandler(self.support, filters.regex("^support$")))
        self.bot.add_handler(CallbackQueryHandler(self.price_info, filters.regex("^price_info$")))

        # ثبت هندلرهای اختصاصی هر ماژول
        self.register_vpn_handlers()
        self.register_payment_handlers()
        self.register_admin_handlers()

        logger.info("✅ تمامی هندلرها با موفقیت ثبت شدند")

    def register_vpn_handlers(self):
        """ثبت هندلرهای مربوط به VPN"""
        if self.vpn_handler:
            # استفاده از متد register داخلی VpnHandler
            self.vpn_handler.register()
        else:
            logger.error("VpnHandler مقداردهی نشده است")

    def register_payment_handlers(self):
        """ثبت هندلرهای مربوط به پرداخت"""
        if self.payment_handler:
            # استفاده از متد register داخلی PaymentHandler
            self.payment_handler.register()
        else:
            logger.error("PaymentHandler مقداردهی نشده است")

    def register_admin_handlers(self):
        """ثبت هندلرهای مربوط به ادمین"""
        if self.admin_menu:
            # استفاده از متد register_handlers داخلی AdminMenu
            self.admin_menu.register_handlers()
        else:
            logger.error("AdminMenu مقداردهی نشده است")

    async def start_command(self, client, message):
        """هندلر دستور /start"""
        user = message.from_user
        user_id = user.id
        admin_id = 5381391685  # آیدی ادمین

        # ایجاد کاربر در دیتابیس
        self.db.create_user_if_not_exists(
            telegram_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name or "",
            username=user.username or "",
            join_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # ایجاد منو
        if user_id == admin_id:
            keyboard = [
                [InlineKeyboardButton("🎁 دریافت اکانت تست رایگان", callback_data="test_vpn_menu")],
                [InlineKeyboardButton("🛒 خرید سرویس جدید", callback_data="buy_new_service_menu"),
                 InlineKeyboardButton("📦 سرویس های من", callback_data="my_service_menu")],
                [InlineKeyboardButton("💳 مدیریت کیف پول", callback_data="money_managment"),
                 InlineKeyboardButton("💰 تعرفه بسته ها", callback_data="price_info")],
                [InlineKeyboardButton("📚 آموزش اتصال", callback_data="connection_info")],
                [InlineKeyboardButton("🛟 ارتباط با پشتیبانی", callback_data="support"),
                 InlineKeyboardButton("👤 مشخصات کاربری", callback_data="user_details")],
                [InlineKeyboardButton("🔐 بخش ادمین", callback_data="admin_menu")],
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🎁 دریافت اکانت تست رایگان", callback_data="test_vpn_menu")],
                [InlineKeyboardButton("🛒 خرید سرویس جدید", callback_data="buy_new_service_menu"),
                 InlineKeyboardButton("📦 سرویس های من", callback_data="my_service_menu")],
                [InlineKeyboardButton("💳 مدیریت کیف پول", callback_data="money_managment"),
                 InlineKeyboardButton("💰 تعرفه بسته ها", callback_data="price_info")],
                [InlineKeyboardButton("📚 آموزش اتصال", callback_data="connection_info")],
                [InlineKeyboardButton("🛟 ارتباط با پشتیبانی", callback_data="support"),
                 InlineKeyboardButton("👤 مشخصات کاربری", callback_data="user_details")],
            ]

        reply_keyboard = ReplyKeyboardMarkup([[KeyboardButton("🏠 خانه")]], resize_keyboard=True)
        await message.reply_text("از دکمه های زیر استفاده کنید:", reply_markup=reply_keyboard)

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"""
🌟✨ سلام {message.from_user.first_name} عزیز!

به سرویس VPN خوش آمدید! 🚀🌐
لطفا یکی از گزینه‌های زیر را انتخاب کنید:
"""
        await message.reply_text(text, reply_markup=reply_markup)

    async def home_command(self, client, message):
        """هندلر دکمه خانه"""
        await self.start_command(client, message)

    async def back_to_menu(self, client, query):
        """هندلر بازگشت به منو"""
        user_id = query.from_user.id
        admin_id = 5381391685

        if user_id == admin_id:
            keyboard = [
                [InlineKeyboardButton("🎁 دریافت اکانت تست رایگان", callback_data="test_vpn_menu")],
                [InlineKeyboardButton("🛒 خرید سرویس جدید", callback_data="buy_new_service_menu"),
                 InlineKeyboardButton("📦 سرویس های من", callback_data="my_service_menu")],
                [InlineKeyboardButton("💳 مدیریت کیف پول", callback_data="money_managment"),
                 InlineKeyboardButton("💰 تعرفه بسته ها", callback_data="price_info")],
                [InlineKeyboardButton("📚 آموزش اتصال", callback_data="connection_info")],
                [InlineKeyboardButton("🛟 ارتباط با پشتیبانی", callback_data="support"),
                 InlineKeyboardButton("👤 مشخصات کاربری", callback_data="user_details")],
                [InlineKeyboardButton("🔐 بخش ادمین", callback_data="admin_menu")],
            ]
        else:
            keyboard = [
                [InlineKeyboardButton("🎁 دریافت اکانت تست رایگان", callback_data="test_vpn_menu")],
                [InlineKeyboardButton("🛒 خرید سرویس جدید", callback_data="buy_new_service_menu"),
                 InlineKeyboardButton("📦 سرویس های من", callback_data="my_service_menu")],
                [InlineKeyboardButton("💳 مدیریت کیف پول", callback_data="money_managment"),
                 InlineKeyboardButton("💰 تعرفه بسته ها", callback_data="price_info")],
                [InlineKeyboardButton("📚 آموزش اتصال", callback_data="connection_info")],
                [InlineKeyboardButton("🛟 ارتباط با پشتیبانی", callback_data="support"),
                 InlineKeyboardButton("👤 مشخصات کاربری", callback_data="user_details")],
            ]

        reply_markup = InlineKeyboardMarkup(keyboard)
        text = f"""
🌟✨ سلام {query.from_user.first_name} عزیز!

به سرویس VPN خوش آمدید! 🚀🌐
لطفا یکی از گزینه‌های زیر را انتخاب کنید:
"""
        await query.message.edit_text(text, reply_markup=reply_markup)

    async def support(self, client, query):
        """هندلر پشتیبانی"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = """
🛟 نیاز به کمک دارید؟
✅ تیم پشتیبانی ما آماده پاسخگویی است

📞 برای ارتباط با پشتیبانی روی لینک زیر کلیک کنید:
👉 https://t.me/Incel_support
"""
        await query.message.edit_text(text, reply_markup=reply_markup)

    async def price_info(self, client, query):
        """هندلر اطلاعات قیمت"""
        keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = """
💰💎 لیست تعرفه سرویس‌های VPN:

📦 بسته‌های عادی:
• ۲۰ گیگابایت | ۱ ماه | ۵۰,۰۰۰ تومان
• ۵۰ گیگابایت | ۱ ماه | ۱۱۰,۰۰۰ تومان
• ۱۰۰ گیگابایت | ۱ ماه | ۱۹۰,۰۰۰ تومان

♾️ بسته‌های لایف‌تایم:
• ۱۰ گیگابایت | مادام‌العمر | ۳۵,۰۰۰ تومان
• ۲۰ گیگابایت | مادام‌العمر | ۶۰,۰۰۰ تومان
• ۵۰ گیگابایت | مادام‌العمر | ۱۶۰,۰۰۰ تومان
• ۱۰۰ گیگابایت | مادام‌العمر | ３۶۰,۰۰۰ تومان

🗓️ بسته‌های بلند مدت:
• ۵۰ گیگابایت | ۲ ماه | ۱۳۵,۰۰۰ تومان
• ۱۰۰ گیگابایت | ۲ ماه | ۲۶۰,۰۰۰ تومان
• ۱۵۰ گیگابایت | ۲ ماه | ۳۷５,۰۰۰ تومان
"""
        await query.message.edit_text(text, reply_markup=reply_markup)


# اجرای ربات
if __name__ == "__main__":
    bot_instance = VPNBot()

    try:
        # اجرای ربات در یک حلقه رویداد
        loop = asyncio.get_event_loop()
        loop.run_until_complete(bot_instance.start())
    except KeyboardInterrupt:
        logger.info("ربات توسط کاربر متوقف شد")
    except Exception as e:
        logger.exception(f"خطای غیرمنتظره: {e}")