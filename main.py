import sys
import os
from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from utils.config import Config
from services.vpn_handler import VpnHandler
from services.payment_handler import PaymentHandler

from database.database_VPN import VpnDatabase
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

vpn_handler = VpnHandler(bot)
payment_handler = PaymentHandler(bot)

@bot.on_message(filters.command("start"))
async def start_handler(client: Client, message: Message):
    user = message.from_user
    user_id = user.id
    user_name = user.first_name
    user_last_name = user.last_name
    user_name_1 = user.username

    db = VpnDatabase()
    db.create_user_if_not_exists(
        user_id=user.id,
        first_name=user.first_name,
        last_name=user.last_name or "",
        username=user.username or ""
    )

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