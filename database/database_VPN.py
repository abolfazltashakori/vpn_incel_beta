import sqlite3
from datetime import datetime
import threading


class VpnDatabase:
    DB_NAME = 'VPN1_beta.db'
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
            self.conn.commit()



    def close(self):

        if self.conn:
            self.conn.close()
            self.conn = None

    def create_user_if_not_exists(self, telegram_id, first_name, last_name, username, join_date=None):
        cur = self.conn.cursor()
        join_date = join_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cur.execute('''INSERT OR IGNORE INTO users_vpn (
            telegram_id, first_name, last_name, username, join_date
        ) VALUES (?,?,?,?,?)''', (
            telegram_id,
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

    def close(self):
        self.conn.close()
