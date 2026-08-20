# گزارش پیشرفت پروژه V2Ray Aggregator

## Executive Summary (خلاصه اجرایی)

**V2Ray Aggregator** یک سیستم خودکار برای جمع‌آوری، پردازش و انتشار پیکربندی‌های V2Ray از کانال‌های تلگرام به مخازن GitHub است.

### هدف پروژه
- جمع‌آوری خودکار configs از کانال‌های تلگرام منبع
- پردازش و canonicalization پروتکل‌های مختلف (VMess, VLESS, Trojan, Shadowsocks, Hysteria, Hysteria2)
- حذف duplicate configs با استفاده از SHA-256 hashing
- انتشار خودکار به GitHub با فایل‌های جداگانه برای هر پروتکل
- ارائه آمار و وضعیت از طریق Telegram bot

### ارزش پیشنهادی
- صرفه‌جویی در زمان با جمع‌آوری خودکار
- حذف duplicate configs برای کاهش حجم
- پشتیبانی از 6 پروتکل محبوب V2Ray
- قابلیت اطمینان بالا با مدیریت خطا
- رابط کاربری ساده از طریق Telegram bot

### وضعیت فعلی
- **Phase 1 (Foundation):** ✅ تکمیل شده
- **Phase 2 (Parser Implementation):** ✅ تکمیل شده
- **Phase 3 (Database Integration):** ✅ تکمیل شده (در Phase 1)
- **Phase 4 (Telegram Collector):** ✅ تکمیل شده
- **Phase 5 (Output Generator):** ✅ تکمیل شده
- **Phase 6 (GitHub Publisher):** ⏳ در انتظار تایید
- **Phase 7 (Admin Bot):** ⏳ در انتظار تایید

---

## Technology Stack (تکنولوژی‌های استفاده شده)

### Core Technologies
- **Python 3.11+** - زبان اصلی برنامه
- **SQLAlchemy 2.0** - ORM برای دیتابیس
- **SQLite** - دیتابیس محلی با حالت WAL
- **Pydantic 2.0+** - Validation و مدیریت تنظیمات
- **python-dotenv** - بارگذاری environment variables

### Telegram Integration
- **Telethon 1.33+** - Client برای جمع‌آوری از کانال‌ها
- **aiogram 3.0+** - Framework برای admin bot

### Testing
- **pytest 7.0+** - Framework تست
- **pytest-asyncio 0.21+** - تست‌های async

### Scheduling
- **APScheduler 3.10+** - Scheduler برای اجرای دوره‌ای

### Utilities
- **python-dateutil 2.8+** - مدیریت تاریخ و زمان

---

## Architecture Overview (معماری سیستم)

### جریان داده (Data Flow)

```
Telegram Channels
       ↓
   Collector (Telethon)
       ↓
   Parser (Protocol-specific)
       ↓
   Canonicalization (SHA-256)
       ↓
   Database (SQLite)
       ↓
   Output Generator
       ↓
   GitHub Publisher (Git)
       ↓
   GitHub Repository
```

### کامپوننت‌های اصلی

1. **Collector** - جمع‌آوری پیام‌ها از کانال‌های تلگرام
2. **Parser** - استخراج و parse کردن configs
3. **Database** - ذخیره configs و tracking occurrences
4. **Output Generator** - تولید فایل‌های خروجی
5. **GitHub Publisher** - انتشار به GitHub
6. **Admin Bot** - رابط کاربری مدیریت
7. **Scheduler** - اجرای دوره‌ای collection

---

## Key Features (ویژگی‌های کلیدی)

### ویژگی‌های تکمیل شده ✅
- **Parser System** - پشتیبانی از 6 پروتکل (VMess, VLESS, Trojan, Shadowsocks, Hysteria, Hysteria2)
- **Canonicalization** - Protocol-specific canonicalization با SHA-256 hashing
- **Database Layer** - Repository pattern با lifecycle states
- **Configuration Management** - Pydantic-based settings با environment variables
- **Logging** - Structured logging با sensitive data redaction
- **Testing** - 103 تست جامع با pytest

### ویژگی‌های در حال توسعه ⏳
- **Telegram Collector** - جمع‌آوری خودکار از کانال‌ها
- **Document Attachment Support** - پشتیبانی از فایل‌های .txt تا 10 MB
- **Error Handling** - Graceful error handling برای کانال‌ها و configs
- **Output Generation** - تولید فایل‌های خروجی پروتکل‌ها
- **GitHub Publishing** - انتشار خودکار به GitHub
- **Admin Bot** - Bot مدیریت با دستورات CLI

### ویژگی‌های آینده 📋
- **Statistics Dashboard** - داشبورد آمار
- **Web Interface** - رابط کاربری وب
- **Multi-User Support** - پشتیبانی از چند کاربر
- **Advanced Filtering** - فیلتر پیشرفته configs
- **Backup System** - سیستم پشتیبان‌گیری

---

## How to Run (نحوه اجرا)

### پیش‌نیازها
- Python 3.11 یا بالاتر
- Git (برای GitHub publishing)
- Telegram API credentials

### مراحل نصب

1. **کلون کردن پروژه**
```bash
cd "c:\Users\Hossein\Desktop\Telegram bot"
```

2. **نصب وابستگی‌ها**
```bash
python -m pip install -r requirements.txt
```

3. **تنظیمات اولیه**
```bash
# کپی فایل .env.example به .env
copy .env.example .env

# ویرایش .env و پر کردن مقادیر مورد نیاز
notepad .env
```

4. **راه‌اندازی دیتابیس**
```bash
python main.py init-db
```

### اجرای پروژه

```bash
# اجرای کامل برنامه (scheduler + bot)
python main.py run

# اجرای یک collection cycle
python main.py collect

# بررسی وضعیت
python main.py status

# انتشار به GitHub
python main.py publish

# تولید فایل‌های خروجی
python main.py generate

# تست parser
python main.py test-parser
```

---

## Configuration Example (نمونه تنظیمات)

### فایل .env

```env
# Telegram API
TELEGRAM_API_ID=your_api_id
TELEGRAM_API_HASH=your_api_hash
TELEGRAM_BOT_TOKEN=your_bot_token

# GitHub
GITHUB_TOKEN=your_github_token
GITHUB_OWNER=your_username
GITHUB_REPO=v2ray-configs
GITHUB_BRANCH=main

# Channel Branding
CHANNEL_NAME=My Channel
CHANNEL_USERNAME=@mychannel
CHANNEL_ID=123456789

# Admin Authorization
ADMIN_USER_IDS=123456789,987654321

# Collection Settings
COLLECTION_INTERVAL_MINUTES=30
FIRST_RUN_MESSAGE_LIMIT=5000

# Database
DATABASE_PATH=v2ray_aggregator.db

# Session
TELEGRAM_SESSION_NAME=v2ray_aggregator_session

# Output
OUTPUT_DIR=configs
DRY_RUN=true

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/app.log
```

---

## API/CLI Reference (مرجع دستورات)

### دستورات CLI

#### `python main.py run`
شروع کامل برنامه (scheduler + admin bot)

#### `python main.py collect`
اجرای یک collection cycle دستی

#### `python main.py status`
نمایش وضعیت سیستم:
- تعداد کانال‌ها
- تعداد configs
- آخرین collection run

#### `python main.py init-db`
راه‌اندازی دیتابیس و ایجاد جداول

#### `python main.py test-parser`
تست parser با sample configs

#### `python main.py generate`
تولید فایل‌های خروجی از دیتابیس (Output Generator)

#### `python main.py publish`
انتشار configs به GitHub

---

## Development Guidelines (راهنمای توسعه)

### استانداردهای کد

1. **Python Style** - پیروی از PEP 8
2. **Type Hints** - استفاده از type hints برای توابع
3. **Docstrings** - نوشتن docstring برای توابع و کلاس‌ها
4. **Error Handling** - استفاده از try-except با logging مناسب

### اضافه کردن feature جدید

1. ایجاد branch جدید
2. نوشتن تست‌ها برای feature
3. پیاده‌سازی feature
4. اجرای تست‌ها
5. commit و push

### نحوه نوشتن تست

```python
def test_feature_name():
    """توضیح کوتاه در مورد تست"""
    # Arrange
    setup_data = create_test_data()
    
    # Act
    result = function_to_test(setup_data)
    
    # Assert
    assert result.expected_value == actual_value
```

---

## Troubleshooting (عیب‌یابی)

### مشکلات رایج

#### 1. خطای "Module not found"
**راه‌حل:** نصب وابستگی‌ها
```bash
python -m pip install -r requirements.txt
```

#### 2. خطای دیتابیس "database is locked"
**راه‌حل:** بستن تمام اتصالات به دیتابیس و حذف فایل .db-wal

#### 3. خطای Telegram API "Invalid API ID"
**راه‌حل:** بررسی صحت TELEGRAM_API_ID و TELEGRAM_API_HASH در .env

#### 4. خطای GitHub "Authentication failed"
**راه‌حل:** بررسی صحت GITHUB_TOKEN و دسترسی به repository

#### 5. تست‌ها fail می‌شوند
**راه‌حل:**
```bash
# پاک کردن cache pytest
python -m pytest --cache-clear

# اجرای مجدد تست‌ها
python -m pytest tests/ -v
```

---

## Future Roadmap (نقشه راه آینده)

### Timeline تخمینی

**Q3 2026**
- Phase 4: Telegram Collector (2-3 هفته)
- Phase 5: Output Generator (1-2 هفته)

**Q4 2026**
- Phase 6: GitHub Publisher (1-2 هفته)
- Phase 7: Admin Bot (2-3 هفته)

**Q1 2027**
- Web Interface
- Advanced Features
- Performance Optimization

### اولویت‌ها

1. **بالا** - تکمیل Collector و Publisher
2. **متوسط** - Admin Bot و Output Generator
3. **پایین** - Web Interface و Advanced Features

---

## خلاصه وضعیت

- **Phase 1 (Foundation):** ✅ تکمیل شده
- **Phase 2 (Parser Implementation):** ✅ تکمیل شده
- **Phase 3 (Database Integration):** ✅ تکمیل شده (در Phase 1)
- **Phase 4 (Telegram Collector):** ✅ تکمیل شده
- **Phase 5 (Output Generator):** ✅ تکمیل شده
- **Phase 6 (GitHub Publisher):** ⏳ در انتظار تایید
- **Phase 7 (Admin Bot):** ⏳ در انتظار تایید

---

## نقشه راه پروژه (Roadmap)

### Phase 0: تحلیل و طراحی ✅
- بررسی معماری کلی
- انتخاب تکنولوژی‌ها
- طراحی دیتابیس
- برنامه‌ریزی فازها

### Phase 1: زیرساخت پروژه ✅
**تکمیل شده:**
- ساختار دایرکتوری پروژه
- مدیریت تنظیمات (Pydantic + python-dotenv)
- فایل .env.example با تمام متغیرهای مورد نیاز
- فایل .gitignore (sessions, .env, __pycache__)
- پیکربندی لاگینگ با فیلتر کردن داده‌های حساس
- پایه داده SQLite با SQLAlchemy و حالت WAL
- مدل‌های دیتابیس (channels, configs, collection_runs, config_occurrences)
- لایه abstraction برای repository
- تنظیم pytest با fixtures
- CLI پایه (main.py)
- راه‌اندازی برنامه (app/main.py)
- فایل requirements.txt

**تعداد تست‌های Phase 1:** 18 تست - همه پاس

### Phase 2: پیاده‌سازی Parser ✅
**تکمیل شده:**
- اینترفیس پایه Parser (BaseParser)
- Parser پروتکل VMess با canonicalization
- Parser پروتکل VLESS با canonicalization
- Parser پروتکل Trojan با canonicalization
- Parser پروتکل Shadowsocks با canonicalization
- Parser پروتکل Hysteria با canonicalization
- Parser پروتکل Hysteria2 با canonicalization (جدا از Hysteria طبق درخواست)
- تست‌های جامع برای همه parserها
- تست‌های canonicalization
- تست‌های تشخیص duplicate

**تعداد تست‌های Phase 2:** 35 تست - همه پاس

### Phase 3: یکپارچه‌سازی دیتابیس ✅
**تکمیل شده در Phase 1:**
- مدل‌های دیتابیس با lifecycle states
- Repository pattern برای عملیات CRUD
- تست‌های دیتابیس

### Phase 4: Telegram Collector ✅
**تکمیل شده:**
- اتصال به Telegram با Telethon
- جمع‌آوری پیام‌ها از کانال‌های منبع
- پشتیبانی از فایل‌های متنی پیوست (.txt) تا 10 MB
- رمزگشایی UTF-8
- مدیریت خطاهای دسترسی به کانال
- ادامه پردازش حتی در صورت خطای یک کانال
- مدیریت خطاهای malformed configs
- ذخیره session file به صورت امن
- Integration با existing parser system
- Collection runs tracking با statistics
- Fault-tolerant error handling
- CLI compatibility (python main.py collect)
- Scheduler compatibility

**تعداد تست‌های Phase 4:** 18 تست - همه پاس

### Phase 5: Output Generator ✅
**تکمیل شده:**
- Output Generator class (app/output/generator.py) - reusable component
- Database as source of truth (Config table, is_active + is_structurally_valid filtering)
- Per-protocol output files: all.txt, vmess.txt, vless.txt, trojan.txt, shadowsocks.txt, hysteria.txt, hysteria2.txt
- stats.json with non-sensitive aggregate data
- README.md with channel branding
- Deterministic ordering (sorted by config_hash)
- Deduplication via database unique config_hash constraint
- Atomic generation (temp staging directory → replace)
- Error handling for empty database, filesystem errors
- CLI command: python main.py generate
- ConfigSnapshot dataclass for session-safe data extraction
- No secrets in generated files
- 32 comprehensive tests covering all acceptance criteria

### Phase 6: GitHub Publisher ⏳
**در انتظار تایید:**
- انتشار batch به GitHub
- استفاده از subprocess برای Git
- مدیریت خطاهای push
- عدم rollback در صورت خطای انتشار
- دیتابیس به عنوان منبع حقیقت

### Phase 7: Admin Bot ⏳
**در انتظار تایید:**
- Bot تلگرام با aiogram
- دستورات مدیریت:
  - /status
  - /errors
  - /channels
  - /collect
  - /publish
- احراز هویت با admin_user_ids
- گزارش خطاها

---

## ساختار پروژه (Project Tree)

```
c:\Users\Hossein\Desktop\Telegram bot\
├── .env.example
├── .gitignore
├── main.py
├── PROGRESS.md
├── pytest.ini
├── requirements.txt
├── SPEC.md
├── .pytest_cache/
│   ├── .gitignore
│   ├── CACHEDIR.TAG
│   ├── README.md
│   └── v/
│       └── cache/
│           ├── lastfailed
│           └── nodeids
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── logging_config.py
│   ├── main.py
│   ├── bot/
│   │   └── __init__.py
│   ├── collector/
│   │   └── __init__.py
│   ├── database/
│   │   ├── __init__.py
│   │   ├── database.py
│   │   ├── models.py
│   │   └── repository.py
│   ├── github/
│   │   └── __init__.py
│   ├── output/
│   │   ├── __init__.py
│   │   └── generator.py
│   ├── parser/
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── hysteria.py
│   │   ├── hysteria2.py
│   │   ├── shadowsocks.py
│   │   ├── trojan.py
│   │   ├── vless.py
│   │   └── vmess.py
│   ├── processor/
│   │   └── __init__.py
│   └── scheduler/
│       └── __init__.py
├── configs/
└── tests/
    ├── __init__.py
    ├── conftest.py
    ├── test_database.py
    ├── test_parsers.py
    ├── test_collector.py
    ├── test_output.py
    ├── fixtures/
    └── __pycache__/
```

---

## جزئیات پیاده‌سازی

### 1. سیستم تنظیمات (Configuration)

**فایل:** `app/config.py`

- استفاده از Pydantic برای type-safe configuration
- بارگذاری از environment variables با python-dotenv
- تنظیمات کلیدی:
  - Telegram API credentials
  - GitHub credentials
  - Channel branding
  - Admin authorization (comma-separated list)
  - Collection settings
  - Database path

### 2. دیتابیس (Database)

**فایل‌ها:**
- `app/database/database.py` - اتصال و مدیریت session
- `app/database/models.py` - مدل‌های ORM
- `app/database/repository.py` - Repository pattern

**جداول:**

#### channels
- id, telegram_id (unique), username, title, enabled
- last_message_id, last_error
- created_at, updated_at

#### configs
- id, protocol, raw_config, normalized_config
- config_hash (unique), is_structurally_valid
- lifecycle_state (NEW, VALID, INVALID, ACTIVE, INACTIVE)
- is_active, first_seen_at, last_seen_at

#### config_occurrences
- id, config_id, channel_id, source_message_id
- raw_occurrence, first_seen_at, last_seen_at
- Unique constraint on (config_id, channel_id, source_message_id)

#### collection_runs
- id, started_at, finished_at, status
- messages_scanned, configs_found, configs_added
- duplicates_removed, invalid_configs, errors
- github_published, github_commit_hash, github_error

### 3. Parser System

**فایل‌ها:**
- `app/parser/base.py` - BaseParser interface
- `app/parser/vmess.py` - VMess parser
- `app/parser/vless.py` - VLESS parser
- `app/parser/trojan.py` - Trojan parser
- `app/parser/shadowsocks.py` - Shadowsocks parser
- `app/parser/hysteria.py` - Hysteria parser
- `app/parser/hysteria2.py` - Hysteria2 parser

**ویژگی‌ها:**
- Protocol-specific canonicalization
- SHA-256 hashing برای deduplication
- Exclusion of metadata (fragments)
- URL encoding normalization
- Parameter sorting
- Structural validation

### 4. Logging

**فایل:** `app/logging_config.py`

- Console handler
- Optional file handler
- Sensitive data redaction filter
- Structured logging format

---

## تست‌ها

### Phase 1 Tests (18 passed)
- Channel repository operations
- Config repository operations
- ConfigOccurrence repository operations
- CollectionRun repository operations
- Database fixture management

### Phase 2 Tests (35 passed)
- VMess parser (7 tests)
- VLESS parser (6 tests)
- Trojan parser (4 tests)
- Shadowsocks parser (4 tests)
- Hysteria parser (3 tests)
- Hysteria2 parser (3 tests)
- Canonicalization tests (4 tests)
- Malformed config tests (4 tests)

### Phase 4 Tests (18 passed)
- Telegram collector functionality
- Message processing
- Document attachment handling
- Collection run statistics

### Phase 5 Tests (32 passed)
- Empty database generation (2 tests)
- Single protocol configs - all 6 protocols (6 tests)
- Multiple protocols (2 tests)
- Deduplication (2 tests)
- Deterministic ordering (2 tests)
- stats.json structure (2 tests)
- README.md generation (2 tests)
- No secrets in generated files (1 test)
- Lifecycle filtering (3 tests)
- Atomic generation (1 test)
- File format (3 tests)
- CLI generate command (2 tests)
- Protocol separation (2 tests)
- Error handling (2 tests)

**مجموع:** 103 تست - همه پاس ✅

---

## تصمیمات و شفاف‌سازی‌های مشخصات

### ✅ پیاده‌سازی شده

**7. Configuration Lifecycle**
- Enum: NEW, VALID, INVALID, ACTIVE, INACTIVE
- مدل state تمیز با فیلدهای boolean جداگانه

**8. Source Records vs Public Configurations**
- جدول ConfigOccurrence برای tracking multiple source
- یک canonical config با multiple occurrences

**6. Canonicalization/Deduplication**
- Protocol-specific canonicalization برای هر 6 پروتکل
- SHA-256 hashing
- Unit tests برای canonicalization

**10. Parser Design**
- Base parser interface
- Protocol-specific parsers جداگانه
- Separate canonicalizers

**2. Hysteria و Hysteria2**
- پروتکل‌های جداگانه
- Parser files جداگانه
- خروجی files جداگانه در Phase 5

### ⏳ برای Phase های بعدی

**1. Document Attachments** → Phase 4
- .txt files تا 10 MB
- UTF-8 encoding
- Modular parsing

**3. Channel Permission Verification** → Phase 4
- Graceful error handling
- Channel state marking
- ادامه پردازش سایر کانال‌ها

**4. Telegram Session Backup** → Phase 4
- Secure session handling
- .gitignore includes *.session files
- Optional configurable backup

**5. Statistics** → Phase 5
- stats.json با فیلدهای مورد نیاز
- Non-sensitive data only

**9. Collector Reliability** → Phase 4
- Per-channel error handling
- Per-message error handling

**11. Output Compatibility** → Phase 5
- Clean machine-readable files
- Branding در README.md فقط
- Separate hysteria.txt و hysteria2.txt

**12. GitHub Publishing** → Phase 6
- Batch publishing
- Database as source of truth

---

## وابستگی‌ها (Dependencies)

```
python-dotenv>=1.0.0
pydantic>=2.0.0
pydantic-settings>=2.0.0
sqlalchemy>=2.0.0
telethon>=1.33.0
aiogram>=3.0.0
pytest>=7.0.0
pytest-asyncio>=0.21.0
apscheduler>=3.10.0
python-dateutil>=2.8.0
```

---

## دستورات Git Bash

```bash
# نصب وابستگی‌ها
python -m pip install python-dotenv
python -m pip install pydantic pydantic-settings
python -m pip install sqlalchemy
python -m pip install pytest pytest-asyncio
python -m pip install telethon aiogram apscheduler python-dateutil

# اجرای تست‌ها
python -m pytest tests/test_database.py -v
python -m pytest tests/test_parsers.py -v
python -m pytest tests/test_output.py -v
python -m pytest tests/ -v

# راه‌اندازی دیتابیس
python main.py init-db

# بررسی وضعیت
python main.py status

# اجرای collection
python main.py collect

# انتشار به GitHub
python main.py publish
```

---

## مسائل حل شده

### Phase 1
1. **Pydantic version conflict** - حل با استفاده از نسخه‌های منعطف (>=)
2. **Configuration validation** - حل با string field و property converter برای admin_user_ids
3. **SQLAlchemy 2.0 compatibility** - حل با استفاده از `text()` برای PRAGMA statements
4. **Count query syntax** - حل با استفاده از `func.count()` به جای `.count()`
5. **Test fixture conflicts** - حل با unique hashes و proper session cleanup
6. **Database file locking** - حل با proper engine disposal و graceful cleanup

### Phase 2
1. **VLESS UUID validation** - حل با استفاده از UUID معتبر در تست‌ها
2. **Parameter handling** - حل با proper validation برای params field

---

## وضعیت فعلی

**Phase 1 و Phase 2 و Phase 4 و Phase 5 کاملاً تکمیل شده و تست‌ها پاس هستند.**

**آماده برای شروع Phase 6 (GitHub Publisher).**

**در انتظار تایید کاربر برای ادامه.**
