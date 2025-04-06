# FoxyVPN - سیستم مدیریت VPN

سیستم مدیریت VPN مبتنی بر پنل Hiddify با دو ربات تلگرام برای مدیریت ادمین و کاربران.

## ویژگی‌ها

### ربات ادمین (FoxyAdminBot)
- مدیریت پنل‌های Hiddify
- مدیریت کاربران و اشتراک‌ها
- تأیید پرداخت‌ها
- مشاهده گزارشات و آمار

### ربات کاربران (FoxyVPNBot)
- خرید اشتراک VPN
- مدیریت حساب کاربری
- مشاهده وضعیت اشتراک
- افزایش موجودی کیف پول

## پیش‌نیازها

- Python 3.8 یا بالاتر
- PostgreSQL
- پنل Hiddify
- توکن‌های ربات تلگرام

## نصب

1. کلون کردن مخزن:
```bash
git clone https://github.com/yourusername/foxybot.git
cd foxybot
```

2. ایجاد محیط مجازی:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. نصب وابستگی‌ها:
```bash
pip install -r requirements.txt
```

4. تنظیم فایل `.env`:
```env
# توکن‌های ربات
ADMIN_BOT_TOKEN=your_admin_bot_token
USER_BOT_TOKEN=your_user_bot_token

# تنظیمات دیتابیس
DATABASE_URL=postgresql://user:password@localhost:5432/foxybot

# تنظیمات امنیتی
SECRET_KEY=your_secret_key
ENCRYPTION_KEY=your_encryption_key

# تنظیمات پنل
HIDDIFY_API_VERSION=v1
HIDDIFY_BASE_URL=https://your-panel.com

# تنظیمات پرداخت
PAYMENT_CARD_NUMBER=your_card_number

# تنظیمات هشدار
TRAFFIC_ALERT_THRESHOLD=0.8
EXPIRY_ALERT_DAYS=3
```

5. ایجاد دیتابیس:
```bash
createdb foxybot
```

6. اجرای ربات‌ها:
```bash
python bot/main.py
```

## ساختار پروژه

```
foxybot/
├── bot/
│   ├── admin_bot.py
│   ├── user_bot.py
│   ├── main.py
│   └── utils/
│       ├── hiddify.py
│       └── payment.py
├── db/
│   ├── models.py
│   └── crud.py
├── api/
├── logs/
├── docs/
├── config.py
├── requirements.txt
└── README.md
```

## دستورات ربات ادمین

- `/start` - شروع کار با ربات
- `/help` - نمایش راهنما
- `/add_panel` - افزودن پنل جدید
- `/panels` - مشاهده لیست پنل‌ها
- `/users` - مشاهده لیست کاربران
- `/transactions` - مشاهده لیست تراکنش‌ها

## دستورات ربات کاربران

- `/start` - شروع کار با ربات
- `/help` - نمایش راهنما
- `/plans` - مشاهده پلن‌های موجود
- `/subscriptions` - مشاهده اشتراک‌های فعال
- `/profile` - مشاهده پروفایل
- `/wallet` - مشاهده موجودی و تراکنش‌ها

## امنیت

- رمزنگاری داده‌های حساس
- احراز هویت ادمین‌ها
- محدودیت دسترسی‌ها
- لاگینگ فعالیت‌ها

## توسعه

1. Fork کردن مخزن
2. ایجاد شاخه جدید (`git checkout -b feature/amazing-feature`)
3. Commit تغییرات (`git commit -m 'Add some amazing feature'`)
4. Push به شاخه (`git push origin feature/amazing-feature`)
5. ایجاد Pull Request

## مجوز

این پروژه تحت مجوز MIT منتشر شده است. برای اطلاعات بیشتر به فایل `LICENSE` مراجعه کنید.

## پشتیبانی

برای گزارش مشکلات و پیشنهادات، لطفاً یک Issue جدید ایجاد کنید. 