import requests
from datetime import datetime, timedelta, timezone
import random
import string
from utils.config import Config


class MarzbanService:
    @staticmethod
    def get_admin_token():
        url = f"{Config.BASE_URL}/api/admin/token"
        data = {
            "username": Config.MARZBAN_USERNAME,
            "password": Config.MARZBAN_PASSWORD
        }
        response = requests.post(url, data=data)
        return response.json()["access_token"] if response.status_code == 200 else None

    @staticmethod
    def get_vless_inbound_tags(access_token):
        url = f"{Config.BASE_URL}/api/inbounds"
        headers = {"Authorization": f"Bearer {access_token}"}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            return [item["tag"] for item in response.json().get("vless", []) if "tag" in item]
        return []

    @staticmethod
    def create_service(access_token, telegram_id, inbounds, volume_gb=0.2, days=1):
        url = f"{Config.BASE_URL}/api/user"
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        username = f"user{telegram_id}_{''.join(random.choices(string.digits, k=4))}"

        payload = {
            "username": username,
            "proxies": {"vless": {}},
            "inbounds": {"vless": inbounds},
            "expire": int((datetime.now(timezone.utc) + timedelta(days=days)).timestamp()),
            "data_limit": int(volume_gb * 1024 ** 3),
            "data_limit_reset_strategy": "no_reset"
        }

        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return {
                "username": username,
                "subscription_url": response.json().get("subscription_url", ""),
                "links": response.json().get("links", [])
            }
        return None