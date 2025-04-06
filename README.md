# 🦊 FoxyBot - ربات مدیریت VPN فاکسی

ربات FoxyVPN یک سیستم هوشمند مدیریت VPN مبتنی بر پنل Hiddify است که با استفاده از رابط تلگرام، مدیریت اشتراک‌ها، کاربران و فروش VPN را به شکلی ساده و خودکار ممکن می‌سازد.

## ✨ ویژگی‌های اصلی

### 🤖 رابط‌های کاربری تلگرامی
- **ربات ادمین** 🧑‍💼: مدیریت کامل سیستم، کاربران و پرداخت‌ها
- **ربات کاربران** 👥: خرید اشتراک، مدیریت حساب و مشاهده وضعیت

### 💎 مدیریت اشتراک‌های VPN
- ایجاد و مدیریت خودکار اشتراک‌ها
- یکپارچه‌سازی کامل با پنل Hiddify
- نظارت بر مصرف ترافیک و مدت زمان اشتراک
- ارسال هشدارهای خودکار مصرف و انقضا

### 💰 سیستم پرداخت هوشمند
- پرداخت کارت به کارت با تأیید خودکار
- سیستم کیف پول داخلی برای کاربران
- مدیریت تراکنش‌ها و گزارش‌های مالی

### ⚙️ پنل مدیریت قدرتمند
- مدیریت کاربران و اشتراک‌ها از طریق تلگرام
- گزارش‌های آماری و نظارت بر عملکرد
- مدیریت پرداخت‌ها و اشتراک‌ها

## 🛠️ نصب و راه‌اندازی

### پیش‌نیازها
- پنل Hiddify نصب شده روی سرور
- Python 3.8 یا بالاتر
- PostgreSQL برای ذخیره‌سازی داده‌ها
- توکن‌های ربات تلگرام (برای ادمین و کاربران)

### ⚡ نصب خودکار (پیشنهاد شده)

```bash
wget -O install.sh https://raw.githubusercontent.com/sina-nozhati/FoxyBot/main/install.sh
chmod +x install.sh
sudo ./install.sh
```

این اسکریپت تمام نیازمندی‌ها را نصب کرده و ربات را راه‌اندازی می‌کند.

### 🔄 نصب دستی

<details>
<summary>برای مشاهده مراحل نصب دستی کلیک کنید</summary>

1. کلون کردن مخزن:
```bash
git clone https://github.com/sina-nozhati/FoxyBot.git /opt/foxybot
cd /opt/foxybot
```

2. ایجاد محیط مجازی پایتون:
```bash
python3 -m venv venv
source venv/bin/activate
```

3. نصب وابستگی‌ها:
```bash
pip install -r requirements.txt
```

4. ایجاد فایل .env در مسیر اصلی پروژه:
```
ADMIN_BOT_TOKEN=<توکن_ربات_ادمین>
USER_BOT_TOKEN=<توکن_ربات_کاربران>
ADMIN_TELEGRAM_ID=<شناسه_تلگرام_ادمین>
DATABASE_URL=postgresql://postgres:admin1234@localhost:5432/foxybot
HIDDIFY_API_BASE_URL=https://<دامنه_پنل_هیدیفای>
HIDDIFY_PROXY_PATH=<مسیر_پروکسی_ادمین>
HIDDIFY_USER_PROXY_PATH=<مسیر_پروکسی_کاربران>
HIDDIFY_API_KEY=<کلید_API_هیدیفای>
PAYMENT_CARD_NUMBER=<شماره_کارت_برای_پرداخت>
```

5. ایجاد سرویس systemd:
```bash
sudo nano /etc/systemd/system/foxybot.service
```

محتوای فایل سرویس:
```
[Unit]
Description=FoxyVPN Telegram Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/foxybot
ExecStart=/opt/foxybot/venv/bin/python /opt/foxybot/bot/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

6. فعال‌سازی و شروع سرویس:
```bash
sudo systemctl daemon-reload
sudo systemctl enable foxybot.service
sudo systemctl start foxybot.service
```
</details>

## 🔄 به‌روزرسانی سیستم

برای به‌روزرسانی ربات به آخرین نسخه، از اسکریپت زیر استفاده کنید:

```bash
wget -O update_bot.sh https://raw.githubusercontent.com/sina-nozhati/FoxyBot/main/update_bot.sh
chmod +x update_bot.sh
sudo ./update_bot.sh
```

اگر قبلاً اسکریپت به‌روزرسانی را دانلود کرده‌اید:

```bash
cd /opt/foxybot
sudo ./update_bot.sh
```

این اسکریپت به طور خودکار:
- سرویس را متوقف می‌کند
- کد را با آخرین نسخه از گیت‌هاب به‌روزرسانی می‌کند
- از فایل .env پشتیبان گرفته و بعد از به‌روزرسانی بازگردانی می‌کند
- وابستگی‌ها را نصب می‌کند
- سرویس را مجدداً راه‌اندازی می‌کند
- اعلانی به ادمین تلگرام ارسال می‌کند

## 🔍 عیب‌یابی و دستورات مفید

### 🔄 راه‌اندازی مجدد بدون به‌روزرسانی کد
```bash
cd /opt/foxybot
sudo ./restart_bot.sh
```

### 💻 دستورات سیستمی

| دستور | توضیحات |
|-------|---------|
| `systemctl status foxybot.service` | بررسی وضعیت فعلی سرویس |
| `journalctl -u foxybot.service -f` | نمایش لاگ‌های زنده سرویس |
| `systemctl restart foxybot.service` | راه‌اندازی مجدد سرویس |

### 🔌 بررسی اتصال‌ها

```bash
cd /opt/foxybot && source venv/bin/activate && python3 bot/test_connection.py
```

### 🛠️ رفع مشکلات رایج

#### مشکل اتصال به دیتابیس
```bash
sudo -u postgres psql -c "ALTER USER postgres WITH PASSWORD 'admin1234';"
```

#### بررسی وضعیت دیتابیس
```bash
sudo systemctl status postgresql
```

## 🧩 ساختار پروژه

```
foxybot/
├── bot/                       # کدهای اصلی ربات
│   ├── admin_bot.py           # ربات ادمین
│   ├── user_bot.py            # ربات کاربران
│   ├── main.py                # نقطه شروع برنامه
│   ├── test_connection.py     # ابزار تست اتصال
│   └── utils/                 # ابزارهای کمکی
│       ├── hiddify.py         # رابط با پنل هیدیفای
│       ├── payment.py         # مدیریت پرداخت
│       └── send_notification.py # ارسال اعلان
├── db/                        # لایه دیتابیس
│   ├── models.py              # مدل‌های دیتابیس
│   └── crud.py                # عملیات CRUD
├── install.sh                 # اسکریپت نصب
├── update_bot.sh              # اسکریپت به‌روزرسانی
├── restart_bot.sh             # اسکریپت راه‌اندازی مجدد
├── requirements.txt           # وابستگی‌های پایتون
└── config.py                  # تنظیمات برنامه
```

## 📝 لایسنس

این پروژه تحت لایسنس MIT منتشر شده است.

## 👨‍💻 مشارکت

برای مشارکت در توسعه این پروژه، لطفاً ابتدا یک ایشو ایجاد کنید و سپس پول ریکوئست خود را ارسال نمایید.

## 📱 ارتباط با ما

برای سؤالات، پیشنهادات و گزارش مشکلات، می‌توانید از طریق موارد زیر با ما در ارتباط باشید:

- 📧 ایمیل: [contact@foxybot.ir](mailto:contact@foxybot.ir)
- 🌐 وبسایت: [foxybot.ir](https://foxybot.ir)
- 💬 تلگرام: [@FoxyVPN_support](https://t.me/FoxyVPN_support)
