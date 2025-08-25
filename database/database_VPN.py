import sqlite3
from datetime import datetime
import threading


class VpnDatabase:
    DB_NAME = 'VPN6_beta.db'
    _lock = threading.Lock()  # برای مدیریت دسترسی thread-safe

    def __init__(self):
        self.conn = self._create_connection()
        self.create_tables()

    def _create_connection(self):
        """ایجاد اتصال جدید به دیتابیس"""
        return sqlite3.connect(self.DB_NAME)

    def create_tables(self):
        with self._lock:
            cur = self.conn.cursor()
            cur.execute('''CREATE TABLE IF NOT EXISTS users_vpn (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id TEXT,
                first_name TEXT,
                last_name TEXT,
                username TEXT,
                balance INTEGER DEFAULT 0,
                phone_number TEXT,
                ban BOOLEAN DEFAULT FALSE,
                join_date TEXT,
                test_service BOOLEAN DEFAULT FALSE,
                referral_code TEXT,
                user_group TEXT DEFAULT 'عادی',
                purchase_count INTEGER DEFAULT 0,
                invoice_count INTEGER DEFAULT 0,
                referral_count INTEGER DEFAULT 0
            )''')
            cur.execute('''CREATE TABLE IF NOT EXISTS user_services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                service_username TEXT NOT NULL,
                package_id TEXT NOT NULL,
                volume_gb REAL NOT NULL,
                expire_date INTEGER NOT NULL,
                purchase_date INTEGER NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users_vpn (telegram_id)
            )''')

            # Fixed gift_codes table with correct structure
            cur.execute('''CREATE TABLE IF NOT EXISTS gift_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                amount INTEGER NOT NULL,
                expire_date TEXT NOT NULL,
                created_at TEXT NOT NULL,
                used_count INTEGER DEFAULT 0
            )''')

            cur.execute('''CREATE TABLE IF NOT EXISTS gift_code_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                gift_code_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                used_at TEXT NOT NULL,
                FOREIGN KEY (gift_code_id) REFERENCES gift_codes(id)
            )''')

            self.conn.commit()

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def is_gift_code_valid(self, code):
        cur = self.conn.cursor()
        cur.execute('''SELECT id, amount, expire_date, used_count FROM gift_codes WHERE code = ?''', (code,))
        result = cur.fetchone()
        if not result:
            return False, "کد نامعتبر است", None

        gift_id, amount, expire_date, used_count = result
        if used_count > 0:
            return False, "این کد قبلاً استفاده شده است", None

        from datetime import datetime
        if datetime.now() > datetime.strptime(expire_date, "%Y-%m-%d"):
            return False, "کد منقضی شده است", None

        return True, amount, gift_id

    def create_user_if_not_exists(self, telegram_id, first_name, last_name, username, join_date=None):
        cur = self.conn.cursor()
        join_date = join_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute('''INSERT OR IGNORE INTO users_vpn (
            telegram_id, first_name, last_name, username, join_date
        ) VALUES (?,?,?,?,?)''', (
            str(telegram_id),  # Convert to string
            first_name,
            last_name or "",
            username or "",
            join_date
        ))
        self.conn.commit()

    def has_used_test_service(self, telegram_id):
        cur = self.conn.cursor()
        cur.execute('SELECT test_service FROM users_vpn WHERE telegram_id = ?', (telegram_id,))
        result = cur.fetchone()
        return result[0] if result else False

    def active_test_service(self, telegram_id, active=True):
        cur = self.conn.cursor()
        cur.execute('UPDATE users_vpn SET test_service = ? WHERE telegram_id = ?', (active, telegram_id))
        self.conn.commit()

    def get_balance(self, telegram_id):
        cur = self.conn.cursor()
        cur.execute('SELECT balance FROM users_vpn WHERE telegram_id = ?', (telegram_id,))
        result = cur.fetchone()
        return result[0] if result else 0

    def balance_decrease(self, telegram_id, amount):
        cur = self.conn.cursor()
        cur.execute('SELECT balance FROM users_vpn WHERE telegram_id = ?', (telegram_id,))
        current_balance = cur.fetchone()[0]
        new_balance = current_balance - amount
        cur.execute('UPDATE users_vpn SET balance = ? WHERE telegram_id = ?', (new_balance, telegram_id))
        self.conn.commit()

    def balance_increase(self, telegram_id, balance):
        cur = self.conn.cursor()
        cur.execute('SELECT balance FROM users_vpn WHERE telegram_id = ?', (telegram_id,))
        result = cur.fetchone()
        if result:
            new_balance = result[0] + balance  # محاسبه موجودی جدید
            cur.execute('UPDATE users_vpn SET balance = ? WHERE telegram_id = ?', (new_balance, telegram_id))
            self.conn.commit()

    def get_user_info(self, telegram_id):
        # Convert to string to ensure type consistency
        telegram_id = str(telegram_id)
        cur = self.conn.cursor()
        cur.execute('''SELECT telegram_id, first_name, last_name, referral_code, phone_number, 
                    join_date, balance, purchase_count, invoice_count, referral_count, user_group 
                    FROM users_vpn 
                    WHERE telegram_id = ?''', (telegram_id,))
        return cur.fetchone()

    def increment_purchase_count(self, telegram_id):
        cur = self.conn.cursor()
        cur.execute('UPDATE users_vpn SET purchase_count = purchase_count + 1 WHERE telegram_id = ?', (telegram_id,))
        self.conn.commit()

    def increment_invoice_count(self, telegram_id):
        cur = self.conn.cursor()
        cur.execute('UPDATE users_vpn SET invoice_count = invoice_count + 1 WHERE telegram_id = ?', (telegram_id,))
        self.conn.commit()

    def increment_referral_count(self, telegram_id):
        cur = self.conn.cursor()
        cur.execute('UPDATE users_vpn SET referral_count = referral_count + 1 WHERE telegram_id = ?', (telegram_id,))
        self.conn.commit()

    def add_user_service(self, telegram_id, service_username, package_id, volume_gb, expire_date):
        cur = self.conn.cursor()
        purchase_date = int(datetime.now().timestamp())
        cur.execute('''INSERT INTO user_services (
            telegram_id, service_username, package_id, volume_gb, expire_date, purchase_date
        ) VALUES (?,?,?,?,?,?)''', (
            telegram_id, service_username, package_id, volume_gb, expire_date, purchase_date
        ))
        self.conn.commit()

    def get_user_services(self, telegram_id):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM user_services WHERE telegram_id = ?', (telegram_id,))
        return cur.fetchall()

    def get_service_by_username(self, service_username):
        cur = self.conn.cursor()
        cur.execute('SELECT * FROM user_services WHERE service_username = ?', (service_username,))
        return cur.fetchone()

    def reset_service(self, service_username, new_expire_date):
        cur = self.conn.cursor()
        cur.execute('UPDATE user_services SET expire_date = ? WHERE service_username = ?',
                    (new_expire_date, service_username))
        self.conn.commit()

    def create_gift_code(self, code, amount, expire_date):
        with self._lock:
            cur = self.conn.cursor()
            created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cur.execute('''INSERT INTO gift_codes (code, amount, expire_date, created_at)
                        VALUES (?, ?, ?, ?)''', (code, amount, expire_date, created_at))
            self.conn.commit()

    def get_gift_code(self, code):
        cur = self.conn.cursor()
        cur.execute('''SELECT * FROM gift_codes WHERE code = ?''', (code,))
        return cur.fetchone()

    def use_gift_code(self, user_id, gift_code_id):
        with self._lock:
            cur = self.conn.cursor()
            used_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # ثبت استفاده کاربر
            cur.execute('''INSERT INTO gift_code_usage (gift_code_id, user_id, used_at)
                        VALUES (?, ?, ?)''', (gift_code_id, user_id, used_at))

            # افزایش تعداد استفاده کد
            cur.execute('''UPDATE gift_codes 
                        SET used_count = used_count + 1 
                        WHERE id = ?''', (gift_code_id,))

            # دریافت مبلغ کد
            cur.execute('''SELECT amount FROM gift_codes WHERE id = ?''', (gift_code_id,))
            result = cur.fetchone()

            if not result:
                return 0  # یا خطا مدیریت شود

            amount = result[0]

            # افزایش موجودی کاربر
            self.balance_increase(user_id, amount)
            self.conn.commit()
            return amount

    def has_used_gift_code(self, user_id, gift_code_id):
        cur = self.conn.cursor()
        cur.execute('''SELECT * FROM gift_code_usage 
                    WHERE user_id = ? AND gift_code_id = ?''', (user_id, gift_code_id))
        return cur.fetchone() is not None

    def close(self):
        self.conn.close()