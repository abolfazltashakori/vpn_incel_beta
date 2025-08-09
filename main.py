import sys
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
from datetime import datetime
from database.database_VPN import VpnDatabase
from services.vpn_handler import VpnHandler
from services.payment_handler import PaymentHandler
from services.admin_menu import AdminMenu
from utils.config import Config

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

# متغیر برای ذخیره هندلرها
handlers_initialized = False
database_connections = []

def close_all_db_connections():
    """بستن تمام اتصالات دیتابیس هنگام خروج"""
    for db in database_connections:
        if hasattr(db, 'close'):
            db.close()
    print("تمامی اتصالات دیتابیس بسته شدند")

atexit.register(close_all_db_connections)

async def initialize_handlers():
    """تابع برای مقداردهی اولیه هندلرها"""
    global handlers_initialized
    if not handlers_initialized:
        # ایجاد نمونه‌های هندلر
        vpn_handler = VpnHandler(bot)
        payment_handler = PaymentHandler(bot)
        admin_menu = AdminMenu(bot)

        # ثبت هندلرها
        vpn_handler.register_handlers()
        payment_handler.register_handlers()
        admin_menu.register_handlers()

        handlers_initialized = True


@bot.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    # مقداردهی اولیه هندلرها در اولین اجرای start
    await initialize_handlers()

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
            [InlineKeyboardButton("دریافت اکانت تست رایگان", callback_data="test_vpn_menu")],
            [InlineKeyboardButton("خرید سرویس جدید", callback_data="buy_new_service_menu"),
             InlineKeyboardButton("سرویس های من", callback_data="my_service_menu")],
            [InlineKeyboardButton("مدیریت کیف پول", callback_data="money_managment"),
             InlineKeyboardButton("تعرفه بسته ها", callback_data="price_info")],
            [InlineKeyboardButton("آموزش اتصال", callback_data="connection_info")],
            [InlineKeyboardButton("ارتباط با پشتیبانی", callback_data="support"),
             InlineKeyboardButton("مشخصات کاربری", callback_data="user_details")],
            [InlineKeyboardButton("بخش ادمین", callback_data="admin_menu")],
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("دریافت اکانت تست رایگان", callback_data="test_vpn_menu")],
            [InlineKeyboardButton("خرید سرویس جدید", callback_data="buy_new_service_menu"),
             InlineKeyboardButton("سرویس های من", callback_data="my_service_menu")],
            [InlineKeyboardButton("مدیریت کیف پول", callback_data="money_managment"),
             InlineKeyboardButton("تعرفه بسته ها", callback_data="price_info")],
            [InlineKeyboardButton("آموزش اتصال", callback_data="connection_info")],
            [InlineKeyboardButton("ارتباط با پشتیبانی", callback_data="support"),
             InlineKeyboardButton("مشخصات کاربری", callback_data="user_details")],
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    text = f"""
🌟 سلام {message.from_user.first_name} عزیز!

به سرویس VPN خوش آمدید!
لطفا یکی از گزینه‌های زیر را انتخاب کنید:
"""
    await message.reply_text(text, reply_markup=reply_markup)


if __name__ == "__main__":
    print("Bot is running...")
    bot.run()