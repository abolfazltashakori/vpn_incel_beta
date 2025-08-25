# vpn_handler.py
from pyrogram import filters
from pyrogram.handlers import CallbackQueryHandler
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from services.marzban_service import get_admin_token, get_vless_inbound_tags, create_service, reset_service
from database.database_VPN import VpnDatabase
from utils.config import Config
from utils.persian_tools import to_jalali
from datetime import datetime, timedelta

db = VpnDatabase()

async def handle_test_vpn(client, callback_query):
    user = callback_query.from_user
    try:
        db.create_user_if_not_exists(
            user.id,
            user.first_name,
            user.last_name or "",
            user.username or ""
        )

        if db.has_used_test_service(user.id):
            await callback_query.answer("⚠️ شما قبلاً از سرویس تست استفاده کرده‌اید!", show_alert=True)
            return

        token = get_admin_token()
        if not token:
            raise Exception("🔴 خطا در اتصال به سرور")

        inbounds = get_vless_inbound_tags(token)
        if not inbounds:
            raise Exception("⚠️ هیچ inbound فعالی یافت نشد")

        volume_gb = 200 / 1024
        service = create_service(
            token,
            user.id,
            inbounds,
            volume_gb=volume_gb,
            days=1
        )
        if not service:
            raise Exception("🔴 خطا در ایجاد سرویس")

        expire_timestamp = int((datetime.now() + timedelta(days=1)).timestamp())
        db.add_user_service(
            user.id,
            service['username'],
            "test",
            0.2,
            expire_timestamp
        )

        db.active_test_service(user.id, True)

        text = f"""
🎉✨ **سرویس تست فعال شد!**

📛 نام سرویس: `{service['username']}`
📦 حجم: 200 مگابایت
⏳ اعتبار: 24 ساعت
🔗 لینک اتصال:
`{service['subscription_url'] or service['links'][0]}`

💡 توجه: این سرویس فقط برای تست اولیه می‌باشد
"""

        admin_text = f"""
کاربر {user.id}
یوزر نیم {user.username}
سرویس تست دریافت کرد
"""
        await client.send_message(Config.ADMIN_ID, admin_text)
        url = "https://t.me/incel_help"
        keyboard = [[InlineKeyboardButton("راهنما استفاده", url=url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await callback_query.message.edit_text(text, reply_markup=reply_markup)
    except Exception as e:
        await callback_query.message.edit_text(f"❌ خطا: {str(e)}")

async def show_user_account_info(client, callback_query):
    user_id = callback_query.from_user.id
    user_info = db.get_user_info(user_id)

    if not user_info:
        await callback_query.answer("❌ اطلاعات کاربر یافت نشد!")
        return

    join_date = to_jalali(user_info[5])
    current_date = to_jalali(datetime.now())

    text = f"""
👤💼 مشخصات حساب کاربری شما:

🆔 شناسه کاربری: {user_info[0]}
👤 نام: {user_info[1]} {user_info[2] or ''}
👥 کد معرف: {user_info[3] or '─'}
📞 شماره تماس: {user_info[4] or '❌ ثبت نشده'}
📅 زمان ثبت نام: {join_date}
💰 موجودی: {user_info[6]:,} تومان
📦 تعداد سرویس‌ها: {user_info[7]} عدد
🧾 تعداد فاکتورها: {user_info[8]} عدد
👨‍👩‍👧‍👦 زیرمجموعه‌ها: {user_info[9]} نفر
🏷️ گروه کاربری: {user_info[10]}

⏱️ تاریخ: {current_date} → ساعت: {datetime.now().strftime('%H:%M:%S')}
"""

    keyboard = [[InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")]]
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_user_services(client, callback_query):
    user_id = callback_query.from_user.id
    services = db.get_user_services(user_id)

    if not services:
        await callback_query.message.edit_text("📭 شما هیچ سرویس فعالی ندارید!")
        return

    keyboard = []
    for service in services:
        service_name = service[2]
        btn = InlineKeyboardButton(
            text=f"📡 سرویس {service_name}",
            callback_data=f"service_details_{service_name}"
        )
        keyboard.append([btn])

    keyboard.append([InlineKeyboardButton("🔙 بازگشت", callback_data="back_to_menu")])
    text = "📦 سرویس‌های فعال شما:\nلطفا یک سرویس را انتخاب کنید"
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_service_details(client, callback_query):
    service_username = callback_query.data.replace("service_details_", "", 1)
    service = db.get_service_by_username(service_username)

    if not service:
        await callback_query.answer("⚠️ سرویس یافت نشد!")
        return

    expire_date = datetime.fromtimestamp(service[5])
    remaining_days = (expire_date - datetime.now()).days

    text = f"""
🔍📡 مشخصات سرویس:
┌─ 📛 شناسه: `{service[2]}`
├─ 💾 حجم کل: {service[4]} گیگابایت
├─ ⏳ زمان باقیمانده: {remaining_days} روز
└─ 📅 تاریخ انقضا: {expire_date.strftime('%Y-%m-%d %H:%M')}
"""
    keyboard = [
        [InlineKeyboardButton("🔄 تمدید سرویس", callback_data=f"renew_service_{service[2]}")],
        [InlineKeyboardButton("🔙 بازگشت", callback_data="my_service_menu")]
    ]
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_renew_service(client, callback_query):
    service_username = callback_query.data.replace("renew_service_", "", 1)
    service = db.get_service_by_username(service_username)
    user_id = callback_query.from_user.id

    if not service:
        await callback_query.answer("⚠️ سرویس یافت نشد!")
        return

    package_id = service[3]
    package_details = Config.PACKAGE_DETAILS.get(package_id)

    if not package_details:
        await callback_query.message.edit_text("❌ اطلاعات بسته سرویس نامعتبر است!")
        return

    new_expire_date = int((datetime.now() + timedelta(days=30)).timestamp())

    text = f"""
🔄 آیا می‌خواهید این سرویس را تمدید کنید؟
├─ 💰 هزینه: {package_details['price']:,} تومان
└─ ⏳ مدت: 30 روز
"""
    keyboard = [
        [InlineKeyboardButton("✅ بله، تمدید کن", callback_data=f"confirm_renew_{service_username}")],
        [InlineKeyboardButton("❌ خیر، بازگشت", callback_data=f"service_details_{service_username}")]
    ]
    await callback_query.message.edit_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def confirm_renew_service(client, callback_query):
    service_username = callback_query.data.replace("confirm_renew_", "", 1)
    service = db.get_service_by_username(service_username)
    user_id = callback_query.from_user.id

    if not service:
        await callback_query.answer("⚠️ سرویس یافت نشد!")
        return

    package_id = service[3]
    package_details = Config.PACKAGE_DETAILS.get(package_id)

    if not package_details:
        await callback_query.message.edit_text("❌ اطلاعات بسته سرویس نامعتبر است!")
        return

    balance = db.get_balance(user_id)
    if balance < package_details['price']:
        await callback_query.message.edit_text(
            "⚠️ موجودی کافی نیست!\n"
            f"├─ 💰 موجودی فعلی: {balance:,} تومان\n"
            f"└─ 💸 مبلغ مورد نیاز: {package_details['price']:,} تومان"
        )
        return

    try:
        db.balance_decrease(user_id, package_details['price'])
        new_expire_date = int((datetime.now() + timedelta(days=30)).timestamp())

        token = get_admin_token()
        if token:
            reset_service(token, service_username, new_expire_date)

        db.reset_service(service_username, new_expire_date)
        await callback_query.message.edit_text(
            "✅ سرویس با موفقیت تمدید شد!\n"
            f"📆 انقضای جدید: {datetime.fromtimestamp(new_expire_date).strftime('%Y-%m-%d %H:%M')}"
        )
    except Exception as e:
        await callback_query.message.edit_text("❌ خطا در تمدید سرویس!")

def register_vpn_handlers(bot):
    bot.add_handler(CallbackQueryHandler(handle_test_vpn, filters=filters.regex("^test_vpn_menu$")), group=3)
    bot.add_handler(CallbackQueryHandler(show_user_account_info, filters=filters.regex("^user_details$")), group=3)
    bot.add_handler(CallbackQueryHandler(show_user_services, filters=filters.regex("^my_service_menu$")), group=3)
    bot.add_handler(CallbackQueryHandler(show_service_details, filters=filters.regex(r"^service_details_\d+$")), group=3)
    bot.add_handler(CallbackQueryHandler(handle_renew_service, filters=filters.regex(r"^renew_service_\d+$")), group=3)
    bot.add_handler(CallbackQueryHandler(confirm_renew_service, filters=filters.regex(r"^confirm_renew_\d+$")), group=3)