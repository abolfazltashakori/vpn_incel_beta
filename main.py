import sys
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, KeyboardButton, \
    ReplyKeyboardMarkup
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from datetime import datetime
from database.database_VPN import VpnDatabase
from services.vpn_handler import *
from services.payment_handler import PaymentHandler
from services.admin_menu import AdminMenu
from utils.config import Config
import asyncio

# تنظیم مسیر پروژه
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

# ایجاد کلاینت
bot = Client(
    "vpn_service_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# متغیرهای global برای ذخیره هندلرها
handlers_initialized = False
database_connections = []
user_states = {}
user_locks = {}
admin_menu_instance = None
payment_handler_instance = None
vpn_handler_instance = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
def close_all_db_connections():
    """بستن تمام اتصالات دیتابیس هنگام خروج"""
    for db in database_connections:
        if hasattr(db, 'close'):
            db.close()
    print("✅ تمامی اتصالات دیتابیس بسته شدند")


def initialize_handlers():
    """
    ایجاد نمونه‌ها و ثبت هندلرها
    """
    global handlers_initialized, admin_menu_instance, payment_handler_instance, vpn_handler_instance

    if handlers_initialized:
        logger.info("Handlers already initialized, skipping")
        return

    try:
        logger.info("Initializing handler instances...")

        # نمونه‌سازی هندلرها
        admin_menu_instance = AdminMenu(bot)
        payment_handler_instance = PaymentHandler(bot, user_states, user_locks)
        vpn_handler_instance = VpnHandler(bot)

        # ثبت هندلرها به ترتیب اهمیت
        payment_handler_instance.register()
        vpn_handler_instance.register()
        admin_menu_instance.register_handlers()

        handlers_initialized = True
        logger.info("✅ All handlers initialized successfully")
    except Exception as e:
        logger.exception(f"❌ Error initializing handlers: {e}")

@bot.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    try:
        initialize_handlers()
    except Exception as e:
        logger.exception(f"Error in initialize_handlers: {e}")


    user = message.from_user
    user_id = user.id
    admin_id = 5381391685  # آیدی ادمین

    # ایجاد کاربر در دیتابیس
    db = VpnDatabase()
    db.create_user_if_not_exists(
        telegram_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name or "",
        username=user.username or "",
        join_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    db.close()

    # ایجاد منوی کاربر
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
    reply_keyboard = ReplyKeyboardMarkup(
        [[KeyboardButton("🏠 خانه")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await message.reply_text(
        "از دکمه های زیر استفاده کنید:",
        reply_markup=reply_keyboard  # کیبورد معمولی
    )

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"""
🌟✨ سلام {message.from_user.first_name} عزیز!

به سرویس VPN خوش آمدید! 🚀🌐
لطفا یکی از گزینه‌های زیر را انتخاب کنید:
"""
    await message.reply_text(text, reply_markup=reply_markup)


@bot.on_message(filters.text & filters.regex("^🏠 خانه$"))
async def menu_handler(client: Client, message: Message):
    await start_handler(client, message)


@bot.on_callback_query(filters.regex("^back_to_menu"))
async def back_to_menu(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    admin_id = 5381391685
    message = query.message
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
    🌟✨ سلام {message.from_user.first_name} عزیز!

    به سرویس VPN خوش آمدید! 🚀🌐
    لطفا یکی از گزینه‌های زیر را انتخاب کنید:
    """
    await message.edit_text(text, reply_markup=reply_markup)


@bot.on_callback_query(filters.regex("^support"))
async def support(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = """
🛟 نیاز به کمک دارید؟
✅ تیم پشتیبانی ما آماده پاسخگویی است

📞 برای ارتباط با پشتیبانی روی لینک زیر کلیک کنید:
👉 https://t.me/Incel_support

"""
    await query.message.edit_text(text, reply_markup=reply_markup)


@bot.on_callback_query(filters.regex("^price_info"))
async def price_info(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    keyboard = [
        [InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = """
💰💎 لیست تعرفه سرویس‌های VPN:

🔺 بسته‌های عادی
──────────────────
🔶 20 گیگ | کاربر نامحدود | 1 ماه : 50T
🔷 50 گیگ | کاربر نامحدود | 1 ماه : 110T
🔶 100 گیگ | کاربر نامحدود | 1 ماه : 190T

🔺 بسته‌های لایف‌تایم (بدون محدودیت زمان)
✅ بدون محدودیت کاربر و زمان
──────────────────
🔶 10 گیگ : 35T
🔷 20 گیگ : 60T
🔶 50 گیگ : 160T
🔷 100 گیگ : 360T

🔺 بسته‌های بلندمدت
──────────────────
🔶 50 گیگ | کاربر نامحدود | 2 ماه : 135T
🔷 100 گیگ | کاربر نامحدود | 2 ماه : 260T
🔶 150 گیگ | کاربر نامحدود | 2 ماه : 375T

💡 نکته: تمامی قیمت‌ها به تومان می‌باشند
"""
    await query.message.edit_text(text, reply_markup=reply_markup)


if __name__ == "__main__":
    logger.info("🤖 ربات در حال اجراست...")

    try:
        initialize_handlers()
        bot.run()
    except KeyboardInterrupt:
        logger.info("ربات متوقف شد")
    except Exception as e:
        logger.exception(f"خطای غیرمنتظره: {e}")
    finally:
        close_all_db_connections()