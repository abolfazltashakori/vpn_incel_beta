# main.py (اصلاح‌شده)
import sys
import os
import logging
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, CallbackQuery, KeyboardButton, ReplyKeyboardMarkup
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from datetime import datetime
from database.database_VPN import VpnDatabase
from services.vpn_handler import VpnHandler
from services.payment_handler import PaymentHandler
from services.admin_menu import AdminMenu
from utils.config import Config
import asyncio
from collections import defaultdict

# تنظیم مسیر پروژه (اگر نیاز دارین نگه دارید)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.append(PROJECT_ROOT)

# Logging ساده
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# ایجاد کلاینت
bot = Client(
    "vpn_service_bot",
    api_id=Config.API_ID,
    api_hash=Config.API_HASH,
    bot_token=Config.BOT_TOKEN
)

# متغیرهای global
handlers_initialized = False
database_connections = []
# shared state & locks (برای استفاده بین هندلرها)
user_states = defaultdict(dict)
user_locks = defaultdict(lambda: asyncio.Lock())
admin_menu_instance = None
payment_handler_instance = None
vpn_handler_instance = None


def close_all_db_connections():
    """بستن تمام اتصالات دیتابیس هنگام خروج"""
    for db in database_connections:
        if hasattr(db, 'close'):
            try:
                db.close()
            except Exception:
                pass
    logger.info("✅ تمامی اتصالات دیتابیس بسته شدند")


def safe_register(obj):
    """
    اگر آبجکت متد register_handlers یا register داشت آن را صدا می‌زند.
    لاگ می‌زند اگر اتفاقی افتاد.
    """
    try:
        if obj is None:
            logger.warning("safe_register: object is None, skipping")
            return
        if hasattr(obj, "register_handlers"):
            obj.register_handlers()
            logger.info("Registered handlers via register_handlers for %s", type(obj).__name__)
        elif hasattr(obj, "register"):
            obj.register()
            logger.info("Registered handlers via register for %s", type(obj).__name__)
        else:
            logger.warning("کلاسی برای ثبت هندلرها متد نداشت: %s", type(obj).__name__)
    except Exception as e:
        logger.exception("خطا هنگام ثبت هندلرها برای %s: %s", type(obj).__name__, e)


def initialize_handlers():
    """
    ایجاد نمونه‌ها و ثبت هندلرها — فقط یکبار اجرا شود.
    """
    global handlers_initialized, admin_menu_instance, payment_handler_instance, vpn_handler_instance, user_states, user_locks

    if handlers_initialized:
        logger.info("Handlers already initialized, skipping")
        return

    try:
        logger.info("Initializing handler instances...")

        # نمونه‌سازی قبل از ثبت
        admin_menu_instance = AdminMenu(bot)
        payment_handler_instance = PaymentHandler(bot, user_states, user_locks)
        vpn_handler_instance = VpnHandler(bot)

        logger.info("Registering handlers in desired order: Payment -> VPN -> Admin (fallback)")
        # ثبت هندلرها به ترتیب منطقی (مطمئن شو فایل‌های handler خود group را تنظیم کرده‌اند)
        safe_register(payment_handler_instance)   # معمولاً group=2
        safe_register(vpn_handler_instance)       # معمولاً group=3
        safe_register(admin_menu_instance)       # معمولاً group=10 (fallback)

        handlers_initialized = True
        logger.info("✅ All handlers initialized successfully (main)")
    except Exception as e:
        logger.exception("❌ Error initializing handlers (main): %s", e)


@bot.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    # در شروع، اطمینان می‌دهیم هندلرها یک‌بار ثبت شده‌اند
    try:
        initialize_handlers()
    except Exception:
        # اگر initialize_handlers خطا داشت، لاگ شود اما ادامه بده
        logger.exception("Error while trying to initialize handlers in start_handler")

    user = message.from_user
    user_id = user.id
    admin_id = 5381391685  # آیدی ادمین

    # ایجاد کاربر در دیتابیس
    db = VpnDatabase()
    try:
        db.create_user_if_not_exists(
            telegram_id=user.id,
            first_name=user.first_name,
            last_name=user.last_name or "",
            username=user.username or "",
            join_date=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )
    finally:
        db.close()

    # منوی کاربر
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

    reply_keyboard = ReplyKeyboardMarkup([[KeyboardButton("🏠 خانه")]], resize_keyboard=True, one_time_keyboard=True)
    await message.reply_text("از دکمه های زیر استفاده کنید:", reply_markup=reply_keyboard)

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"""
🌟✨ سلام {message.from_user.first_name} عزیز!

به سرویس VPN خوش آمدید! 🚀🌐
لطفا یکی از گزینه‌های زیر را انتخاب کنید:
"""
    await message.reply_text(text, reply_markup=reply_markup)


@bot.on_message(filters.text & filters.regex("^🏠 خانه$"))
async def menu_handler(client: Client, message: Message):
    # صدا زدن start_handler برای نمایش منو
    await start_handler(client, message)


@bot.on_callback_query(filters.regex("^back_to_menu"))
async def back_to_menu(client: Client, query: CallbackQuery):
    user_id = query.from_user.id
    admin_id = 5381391685
    message = query.message
    # توجه: از message.edit_text استفاده می‌کنیم (چون اینجا callback داریم)
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
    # ویرایش پیام callback
    await query.message.edit_text(text, reply_markup=reply_markup)


@bot.on_callback_query(filters.regex("^support"))
async def support(client: Client, query: CallbackQuery):
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]
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
    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    text = """
💰💎 لیست تعرفه سرویس‌های VPN:
... (متن تعرفه‌ها)
"""
    await query.message.edit_text(text, reply_markup=reply_markup)


if __name__ == "__main__":
    logger.info("🤖 ربات در حال اجراست...")
    # ثبت هندلرها قبل از start (اختیاری؛ start_handler هم initialize_handlers را صدا می‌زند)
    initialize_handlers()
    try:
        bot.run()
    finally:
        close_all_db_connections()
