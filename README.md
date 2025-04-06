# 🦊 FoxyVPN Bot

FoxyVPN Bot یک سیستم مدیریت VPN مبتنی بر پنل Hiddify است که با استفاده از رابط تلگرام، مدیریت اشتراک‌ها و کاربران را آسان می‌کند.

## 🚀 ویژگی‌ها

- **دو ربات تلگرام**: 
  - 🧑‍💼 FoxyAdminBot: برای مدیران سیستم
  - 🧑‍🦰 FoxyVPNBot: برای کاربران نهایی

- **مدیریت اشتراک‌های VPN**:
  - ایجاد و مدیریت اشتراک‌ها
  - پشتیبانی از پنل Hiddify
  - مانیتورینگ مصرف ترافیک
  - هشدارهای مصرف و انقضا

- **سیستم پرداخت**:
  - پرداخت کارت به کارت
  - تأیید تراکنش‌ها توسط ادمین
  - شارژ کیف پول کاربران

- **پنل ادمین**:
  - مدیریت کاربران و اشتراک‌ها
  - مشاهده گزارش‌ها و آمار
  - مدیریت پرداخت‌ها

## 🛠️ نصب و راه‌اندازی

### پیش‌نیازها

- پنل Hiddify نصب شده
- پایتون 3.8 یا بالاتر
- PostgreSQL
- توکن‌های ربات تلگرام (Admin Bot و User Bot)

### نصب خودکار

```bash
wget -O install.sh https://raw.githubusercontent.com/username/foxybot/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

### نصب دستی

1. کلون کردن ریپوزیتوری:
```bash
git clone https://github.com/username/foxybot.git
cd foxybot
```

2. ایجاد محیط مجازی:
```bash
python -m venv venv
source venv/bin/activate  # در لینوکس
# یا
venv\Scripts\activate  # در ویندوز
```

3. نصب وابستگی‌ها:
```bash
pip install -r requirements.txt
```

4. ایجاد فایل .env:
```
ADMIN_BOT_TOKEN=your_admin_bot_token
USER_BOT_TOKEN=your_user_bot_token
DATABASE_URL=postgresql://user:password@localhost:5432/foxybot
HIDDIFY_API_BASE_URL=https://your-hiddify-panel.com
HIDDIFY_PROXY_PATH=admin_proxy_path
HIDDIFY_USER_PROXY_PATH=user_proxy_path
HIDDIFY_API_KEY=your_api_key
```

5. راه‌اندازی دیتابیس:
```bash
# ایجاد دیتابیس در PostgreSQL
```

6. اجرای برنامه:
```bash
python bot/main.py
```

## 🧩 ساختار پروژه

```
foxybot/
├── bot/                # کدهای ربات
│   ├── admin_bot.py    # ربات ادمین
│   ├── user_bot.py     # ربات کاربران
│   ├── main.py         # نقطه شروع برنامه
│   └── utils/          # ابزارهای کمکی
├── db/                 # لایه دیتابیس
│   ├── models.py       # مدل‌های دیتابیس
│   └── crud.py         # عملیات CRUD
├── api/                # ارتباط با API های خارجی
├── logs/               # لاگ‌ها
├── docs/               # مستندات
├── .env                # تنظیمات محیطی
└── config.py           # تنظیمات برنامه
```

## 📝 لایسنس

این پروژه تحت لایسنس MIT منتشر شده است.

## 👨‍💻 مشارکت

برای مشارکت در این پروژه، لطفاً ابتدا یک ایشو ایجاد کنید و سپس پول ریکوئست خود را ارسال نمایید.

## 📨 ارتباط با ما

برای سوالات و پیشنهادات، می‌توانید از طریق [ایمیل](mailto:example@email.com) با ما در ارتباط باشید.