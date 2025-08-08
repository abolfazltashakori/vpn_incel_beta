import os


class Config:
    API_ID = int(os.getenv("API_ID", 27424905))
    API_HASH = os.getenv("API_HASH", "3aa07c799d5d1331e353f3d5dec92b30")
    BOT_TOKEN = os.getenv("BOT_TOKEN", "8432923905:AAFyr_o6atsJe8W9h46DzBkstCKy-ySVqAg")
    ADMIN_ID = int(os.getenv("ADMIN_ID", 5381391685))
    BASE_URL = "https://lin.klaris-sub.top"
    MARZBAN_USERNAME = "abolfazl"
    MARZBAN_PASSWORD = "ASDT76yt@#^&"

    # تعرفه بسته‌ها
    PACKAGE_DETAILS = {
        "normal_1": {"volume_gb": 20, "days": 30, "price": 50000},
        "normal_2": {"volume_gb": 50, "days": 30, "price": 110000},
        "normal_3": {"volume_gb": 100, "days": 30, "price": 190000},
        "lifetime_1": {"volume_gb": 10, "days": 0, "price": 35000},
        "lifetime_2": {"volume_gb": 20, "days": 0, "price": 60000},
        "lifetime_3": {"volume_gb": 50, "days": 0, "price": 160000},
        "lifetime_4": {"volume_gb": 100, "days": 0, "price": 360000},
        "unlimited_1": {"volume_gb": 100, "days": 30, "price": 95000},
        "unlimited_2": {"volume_gb": 100, "days": 30, "price": 145000},
        "unlimited_3": {"volume_gb": 100, "days": 60, "price": 185000},
        "unlimited_4": {"volume_gb": 100, "days": 60, "price": 240000},
        "longtime_1": {"volume_gb": 50, "days": 60, "price": 135000},
        "longtime_2": {"volume_gb": 100, "days": 60, "price": 260000},
        "longtime_3": {"volume_gb": 150, "days": 60, "price": 375000},
    }