import sys
import os
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
user_states = {}
user_locks = {}

def close_all_db_connections():
    """بستن تمام اتصالات دیتابیس هنگام خروج"""
    for db in database_connections:
        if hasattr(db, 'close'):
            db.close()
    print("✅ تمامی اتصالات دیتابیس بسته شدند")


@bot.on_message(filters.text & filters.private)
async def handle_amount_message(client, message: Message):
    user_id = message.from_user.id

    # ایجاد قفل برای هر کاربر
    if user_id not in user_locks:
        user_locks[user_id] = asyncio.Lock()

    async with user_locks[user_id]:
        # بررسی اینکه کاربر در حالت انتظار برای مبلغ است
        if user_id not in user_states or user_states[user_id].get("state") != "waiting_for_amount":
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
            user_states[user_id] = {
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
    print("🤖 ربات در حال اجراست...")
    bot.run()