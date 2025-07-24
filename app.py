import os
import sqlite3
import hashlib
import secrets
import asyncio
import random
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto
from aiogram.filters import CommandStart
from aiogram.enums import ParseMode  # Bu yerda to'g'ri import
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8188078162:AAF1SVP1U7506KPHZZ8oNUV6C-IT2H_r1hk")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "7479997835")
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "your_admin_username")
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
QR_CODE_IMAGE_URL = "https://i.postimg.cc/6QPGpJ0f/photo-2025-07-20-15-12-46.jpg"
PRODUCT_PLACEHOLDER_IMAGE_URL = "https://picsum.photos/200/200"
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")

# Telegram Bot Setup
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher()

# FSM States
class ProductCreation(StatesGroup):
    waiting_for_region = State()
    waiting_for_district = State()
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_image = State()
    waiting_for_price = State()

class ReviewSubmission(StatesGroup):
    waiting_for_review_text = State()
    waiting_for_stars = State()

class ProductBrowse(StatesGroup):
    waiting_for_browse_region = State()
    waiting_for_browse_district = State()
    waiting_for_product_selection = State()
    waiting_for_payment_confirmation = State()
    waiting_for_paid_amount = State()

# Database Setup
def init_db():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Drop tables to ensure fresh schema
    tables_to_drop = [
        'users', 'login_attempts', 'verification_codes', 'bot_button_contents',
        'bot_buttons', 'region_prices', 'products', 'reviews', 'districts',
        'regions', 'bot_users', 'pending_payments'
    ]
    
    for table in tables_to_drop:
        cursor.execute(f'DROP TABLE IF EXISTS {table}')
    
    # Create tables
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            is_blocked INTEGER DEFAULT 0,
            failed_attempts INTEGER DEFAULT 0,
            failed_verification_attempts INTEGER DEFAULT 0,
            last_attempt TIMESTAMP,
            blocked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            ip_address TEXT,
            success INTEGER,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            user_agent TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS verification_codes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            code TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP,
            used INTEGER DEFAULT 0
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_buttons (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT NOT NULL,
            callback_data TEXT UNIQUE NOT NULL,
            order_index INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_button_contents (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            callback_data TEXT UNIQUE NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (callback_data) REFERENCES bot_buttons(callback_data) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT UNIQUE NOT NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS districts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            UNIQUE(region_id, name),
            FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS region_prices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_id INTEGER NOT NULL,
            item_type TEXT NOT NULL,
            price REAL NOT NULL,
            UNIQUE(region_id, item_type),
            FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            image_url TEXT,
            image_url2 TEXT,
            price REAL NOT NULL,
            region_id INTEGER,
            district_id INTEGER,
            status TEXT DEFAULT 'pending',
            created_by_telegram_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE SET NULL,
            FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE SET NULL
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_telegram_id INTEGER NOT NULL,
            review_text TEXT NOT NULL,
            rating INTEGER,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            last_name TEXT,
            total_purchases INTEGER DEFAULT 0,
            balance REAL DEFAULT 0.0,
            total_spent REAL DEFAULT 0.0,
            is_blocked INTEGER DEFAULT 0,
            blocked_until TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS pending_payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_telegram_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            amount REAL NOT NULL,
            status TEXT DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
        )
    ''')
    
    # Create admin users
    admin_password = hashlib.sha256('newadmin123'.encode()).hexdigest()
    cursor.execute('''
        INSERT INTO users (username, password_hash)
        VALUES (?, ?)
    ''', ('admin', admin_password))
    
    admin2_password = hashlib.sha256('newadmin1234'.encode()).hexdigest()
    cursor.execute('''
        INSERT INTO users (username, password_hash)
        VALUES (?, ?)
    ''', ('admin2', admin2_password))
    
    # Create default bot buttons
    default_buttons = [
        ("⬆️ Пополнить счет", "top_up", 20),
        ("⭕ TRUE CORE ", "under_control", 30),
        ("💰 Работа", "work", 40),
        ("📄 Правила", "rules", 50),
        ("🆘 Поддержка", "support", 60),
        ("🛒 ВИТРИНА", "showcase", 70),
        ("ℹ️ Информация", "info", 80),
        ("⭐ Отзывы", "reviews", 90),
        ("🤖 Подключить своего бота", "connect_bot", 100),
    ]
    
    for text, callback_data, order_index in default_buttons:
        cursor.execute("INSERT INTO bot_buttons (text, callback_data, order_index, is_active) VALUES (?, ?, ?, ?)",
                       (text, callback_data, order_index, 1))
    
    # Create default button contents
    default_button_contents = [
        ("top_up", "Для пополнения счета свяжитесь с администратором. Автоматическая система оплаты скоро будет запущена."),
        ("work", "Для получения информации о возможностях работы свяжитесь с администратором."),
        ("support", f"Если у вас есть вопросы, пожалуйста, свяжитесь с нашей службой поддержки. Для связи с администратором: @{ADMIN_USERNAME}"),
        ("rules", "Правила рассмотрения и заполнения заявки для уточнений при ненаходе: ПРЕДОСТАВЬТЕ ПО ПУНКТАМ:\n- Номер заказа\n- адрес фактической покупки ( ПЕРЕСЛАТЬ с Бота сообщением ) Внимание -  не копировать\n- фото с места (несколько с разных ракурсов)\n- описание состояния места клада по прибытию на адрес\n\n⚠️⚠️ ЕСЛИ АДРЕС НЕ СООТВЕТСТВУЕТ ФОТО/КООРДИНАТАМ ⚠️⚠️ предоставьте, пожалуйста, 4 фотографии местности с отметкой координат. Координаты на Ваших фото должны совпадать с координатами в заказе, желательно в таком же ракурсе как у курьера. Для того чтобы получить фотографии с отметкой GPS координат, можете использовать Notecam если у Вас Android, или Solocator если используете iOS. Ожидаю фотографии в пределах регламентного времени\n\n☝️☝️ВАЖНО ЗНАТЬ! РАССМОТРЕНИЕ И УТОЧНЕНИЕ ВАШЕЙ ЗАЯВКИ ДОПУСТИМО В ТЕЧЕНИИ 3 ЧАСОВ С МОМЕНТА ПОКУПКИ!\n\n‼️ВНИМАНИЕ‼️\n❌ПОЧЕМУ ВАМ МОЖЕТ БЫТЬ ОТКАЗАНО В РАССМОТРЕНИИ?❌\n\n1. Мы оставляем за собой право на отказ в обслуживании, УТОЧНЕНИЯХ или решении той или иной проблемы без каких-либо разъяснений.\n2. Претензии по ненаходам, недовесам и другим проблемам в заказах принимаются в течение 3-х  часов с момента покупки  и решаются только через ЛС!\n3. Передача информации о кладе третьим лицам запрещена - это лишает Вас права на помощь в поисках  в случае ненахода!\n4. Шантаж плохими отзывами, хамство, оскорбления сотрудников магазина и не пристойное поведение - АВТОМАТИЧЕСКИ лишает Вас права на получение помощи в поисках  в случае ненахода!\n5. Если фотографии с места трагедии при сообщении о проблеме были сделаны не сразу и Вы якобы поедете фотографировать место и предоставите их спустя 3-х и более часов - это лишает Вас права на помощь в поисках. Для начала предоставьте пересланным сообщением сам адрес, который Вам выдан ботом! Затем фото, сделанные Вами лично!\n\nПЕРЕЗАКЛАД НА ПЕРЕЗАКЛАД НЕ ВЫДАЁТСЯ"),
        ("connect_bot", "Вы не можете создавать личных ботов, так как не совершено необходимое количество покупок.\nВсего покупок: 0\nНеобходимое количество покупок для создания бота: 1"),
        ("under_control", "Этот раздел находится в разработке. Дополнительная информация будет предоставлена в ближайшее время."),
        ("info", "В этом разделе содержится общая информация о нашем магазине. Для дополнительных вопросов используйте кнопку 'Поддержка'."),
    ]
    
    for callback_data, content in default_button_contents:
        cursor.execute("INSERT INTO bot_button_contents (callback_data, content) VALUES (?, ?)", (callback_data, content))
    
    # Add regions
    uzbek_regions = [
        "Andijon viloyati", "Buxoro viloyati", "Farg'ona viloyati", "Jizzax viloyati",
        "Xorazm viloyati", "Namangan viloyati", "Navoiy viloyati",
        "Qashqadaryo viloyati", "Samarqand viloyati", "Sirdaryo viloyati", "Surxondaryo viloyati",
        "Toshkent viloyati", "Qoraqalpog'iston Respublikasi"
    ]
    
    for region_name in uzbek_regions:
        cursor.execute('INSERT OR IGNORE INTO regions (name) VALUES (?)', (region_name,))
    
    # Add districts
    regions_data = cursor.execute("SELECT id, name FROM regions").fetchall()
    districts_to_add = {
        "Toshkent viloyati": ["Bekobod tumani", "Bo'stonliq tumani", "Chirchiq shahri", "Toshkent shahri"],
        "Samarqand viloyati": ["Samarqand shahri", "Urgut tumani", "Tayloq tumani", "Kattaqo'rg'on tumani"],
        "Andijon viloyati": ["Andijon shahri", "Asaka tumani", "Xo'jaobod tumani", "Qo'rg'ontepa tumani"]
    }
    
    for region_id, region_name in regions_data:
        if region_name in districts_to_add:
            for district_name in districts_to_add[region_name]:
                cursor.execute('INSERT OR IGNORE INTO districts (region_id, name) VALUES (?, ?)', (region_id, district_name))
        else:
            cursor.execute('INSERT OR IGNORE INTO districts (region_id, name) VALUES (?, ?)', (region_id, f"{region_name} Центральный район"))
    
    # Add test products
    tashkent_region_id = cursor.execute("SELECT id FROM regions WHERE name = 'Toshkent viloyati'").fetchone()[0]
    tashkent_city_district_id = cursor.execute("SELECT id FROM districts WHERE name = 'Toshkent shahri' AND region_id = ?", (tashkent_region_id,)).fetchone()[0]
    bektemir_district_id = cursor.execute("SELECT id FROM districts WHERE name = 'Bekobod tumani' AND region_id = ?", (tashkent_region_id,)).fetchone()[0]
    
    cursor.execute('''
        INSERT INTO products (name, description, image_url, image_url2, price, region_id, district_id, status, created_by_telegram_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('Gagarin 33% TGK 1gr', 'Это отличный товар в городе Ташкент.', PRODUCT_PLACEHOLDER_IMAGE_URL, None, 60.0, tashkent_region_id, bektemir_district_id, 'approved', 123456789))
    
    samarkand_region_id = cursor.execute("SELECT id FROM regions WHERE name = 'Samarqand viloyati'").fetchone()[0]
    samarkand_city_district_id = cursor.execute("SELECT id FROM districts WHERE name = 'Samarqand shahri' AND region_id = ?", (samarkand_region_id,)).fetchone()[0]
    
    cursor.execute('''
        INSERT INTO products (name, description, image_url, image_url2, price, region_id, district_id, status, created_by_telegram_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', ('Тестовый товар 2 (Самарканд)', 'Качественный товар из Самарканда.', PRODUCT_PLACEHOLDER_IMAGE_URL, None, 250000.0, samarkand_region_id, samarkand_city_district_id, 'approved', 987654321))
    
    conn.commit()
    conn.close()

# Telegram functions
async def _send_telegram_message_task(message: str, chat_id: int = None, reply_markup: InlineKeyboardMarkup = None):
    target_chat_id = chat_id if chat_id else ADMIN_CHAT_ID
    if not TELEGRAM_BOT_TOKEN or not target_chat_id:
        print(f"Telegram не настроен: {message}")
        return False
    try:
        await bot.send_message(chat_id=target_chat_id, text=message, parse_mode=ParseMode.HTML, reply_markup=reply_markup)
        return True
    except Exception as e:
        print(f"Ошибка Telegram: {e}")
        return False

def get_main_menu_keyboard():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT text, callback_data FROM bot_buttons WHERE is_active = 1 ORDER BY order_index")
    buttons_data = cursor.fetchall()
    conn.close()
    
    keyboard_rows = []
    for i in range(0, len(buttons_data), 2):
        row = []
        for j in range(2):
            if i + j < len(buttons_data):
                text, callback_data = buttons_data[i+j]
                row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
        if row:
            keyboard_rows.append(row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

def get_back_to_main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ Вернуться в главное меню", callback_data="main_menu")]
    ])

@dp.message(CommandStart())
async def on_start(message: types.Message):
    user_telegram_id = message.from_user.id
    is_blocked, blocked_until = check_bot_user_blocked(user_telegram_id)
    if is_blocked:
        await message.answer(f"Извините, ваш аккаунт заблокирован до {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}. Свяжитесь с администратором.")
        return
    
    print("Бот запущен")
    welcome_message = """🎉 Добро пожаловать в наш магазин! 🛍️

🌟Здесь вы найдете широкий ассортимент товаров для всех случаев жизни!

Чтобы начать покупки, необходимо сначала пополнить ваш счет. После пополнения вы сможете использовать баланс для покупки любого товара, который будет выдан вам автоматически. 🎁

💳Пополнение счета простое и безопасное. Все транзакции проходят в защищенном режиме, чтобы вы могли чувствовать себя уверенно и комфортно.

🤔 Если у вас возникнут вопросы, не стесняйтесь обращаться к нашим операторам. Мы здесь, чтобы помочь вам! 🙋‍♂️🙋

🚀 Готовы начать? Приступим к покупкам и наслаждайтесь удобством и разнообразием нашего ассортимента!

💬 Ждем ваших заказов и желаем приятных покупок! 🎉

Кол-во сделок: 450 шт."""
    
    await message.answer(welcome_message, reply_markup=get_main_menu_keyboard())

# Showcase functionality
@dp.callback_query(lambda c: c.data == "showcase")
async def start_showcase_browse(call: types.CallbackQuery, state: FSMContext):
    await call.answer("Товары в витрине загружаются...")
    await state.set_state(ProductBrowse.waiting_for_browse_region)
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM regions ORDER BY name")
    regions_data = cursor.fetchall()
    conn.close()
    
    region_keyboard_rows = []
    for region_id, region_name in regions_data:
        region_keyboard_rows.append([InlineKeyboardButton(text=region_name, callback_data=f"browse_region_{region_id}")])
    
    region_keyboard = InlineKeyboardMarkup(inline_keyboard=region_keyboard_rows)
    await call.message.answer("Выберите область, в которой вы ищете товар:", reply_markup=region_keyboard)

@dp.callback_query(F.data.startswith("browse_region_"), ProductBrowse.waiting_for_browse_region)
async def process_browse_region(call: types.CallbackQuery, state: FSMContext):
    await call.answer("Область выбрана...")
    region_id = int(call.data.split("_")[2])
    await state.update_data(browse_region_id=region_id)
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT DISTINCT d.id, d.name
        FROM districts d
        JOIN products p ON d.id = p.district_id
        WHERE d.region_id = ? AND p.status = 'approved'
        ORDER BY d.name
    ''', (region_id,))
    districts_data = cursor.fetchall()
    conn.close()
    
    if not districts_data:
        await call.message.answer("В выбранной области нет одобренных товаров. Пожалуйста, выберите другую область.", reply_markup=get_back_to_main_menu_keyboard())
        await state.clear()
        return
    
    district_keyboard_rows = []
    for district_id, district_name in districts_data:
        district_keyboard_rows.append([InlineKeyboardButton(text=district_name, callback_data=f"browse_district_{district_id}")])
    
    district_keyboard = InlineKeyboardMarkup(inline_keyboard=district_keyboard_rows)
    await state.set_state(ProductBrowse.waiting_for_browse_district)
    await call.message.answer("Выберите район, в котором вы ищете товар:", reply_markup=district_keyboard)

@dp.callback_query(F.data.startswith("browse_district_"), ProductBrowse.waiting_for_browse_district)
async def process_browse_district(call: types.CallbackQuery, state: FSMContext):
    await call.answer("Район выбран, товары загружаются...")
    district_id = int(call.data.split("_")[2])
    user_data = await state.get_data()
    region_id = user_data.get('browse_region_id')
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.name, p.description, p.price, r.name, d.name
        FROM products p
        LEFT JOIN regions r ON p.region_id = r.id
        LEFT JOIN districts d ON p.district_id = d.id
        WHERE p.region_id = ? AND p.district_id = ? AND p.status = 'approved'
        ORDER BY p.name
    ''', (region_id, district_id))
    products = cursor.fetchall()
    conn.close()
    
    if not products:
        await call.message.answer("В выбранном регионе нет одобренных товаров.", reply_markup=get_back_to_main_menu_keyboard())
        await state.clear()
        return
    
    region_name = get_region_name_by_id(region_id)
    response_text = f"<b>Доступные товары \"{region_name}\"</b>\n\n"
    product_buttons = []
    
    for i, product in enumerate(products):
        product_id, name, description, price, _, district_name = product
        response_text += f"{i+1}) {name} - {price} $\n" \
                         f"{district_name}\n\n"
        product_buttons.append([InlineKeyboardButton(text=f"Купить {name} ({price}$)", callback_data=f"buy_product_{product_id}")])
    
    product_buttons.append([InlineKeyboardButton(text="⬅️ Вернуться в главное меню", callback_data="main_menu")])
    products_keyboard = InlineKeyboardMarkup(inline_keyboard=product_buttons)
    
    await state.update_data(selected_district_id=district_id)
    await state.set_state(ProductBrowse.waiting_for_product_selection)
    await call.message.answer(response_text, reply_markup=products_keyboard, parse_mode=ParseMode.HTML)

@dp.callback_query(F.data.startswith("buy_product_"), ProductBrowse.waiting_for_product_selection)
async def process_product_selection(call: types.CallbackQuery, state: FSMContext):
    await call.answer("Товар выбран, QR-код для оплаты отправляется...")
    product_id = int(call.data.split("_")[2])
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name, description, price FROM products WHERE id = ?", (product_id,))
    product_info = cursor.fetchone()
    conn.close()
    
    if not product_info:
        await call.message.answer("Извините, выбранный товар не найден.", reply_markup=get_back_to_main_menu_keyboard())
        await state.clear()
        return
    
    product_name, product_description, product_price = product_info
    user_telegram_id = call.from_user.id
    
    payment_id = add_pending_payment_db(user_telegram_id, product_id, product_price)
    
    await call.message.answer_photo(
        photo=QR_CODE_IMAGE_URL,
        caption=f"Вы выбрали <b>{product_name}</b> ({product_price} сум).\n"
                f"Используйте следующий QR-код для оплаты:\n\n"
                f"<b>Ваш ID платежа: {payment_id}</b>\n"
                f"Пожалуйста, переведите <b>{product_price} сум</b>.\n\n"
                f"Ссылка для оплаты: <code>Oxf11c6bF4206A8DA0B7caf084c61e3d1006Fee120</code>\n\n"
                f"После оплаты, отправьте мне точную сумму, которую вы перевели (например: 100000).",
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_to_main_menu_keyboard()
    )
    
    await state.update_data(current_payment_id=payment_id, expected_amount=product_price)
    await state.set_state(ProductBrowse.waiting_for_paid_amount)

def delete_product_after_sale(product_id: int):
    """Delete product from database after successful sale"""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("DELETE FROM products WHERE id = ?", (product_id,))
        conn.commit()
        print(f"Product {product_id} deleted after successful sale")
        return True
    except Exception as e:
        print(f"Error deleting product {product_id}: {e}")
        return False
    finally:
        conn.close()

@dp.message(ProductBrowse.waiting_for_paid_amount)
async def process_paid_amount(message: types.Message, state: FSMContext):
    user_telegram_id = message.from_user.id
    user_data = await state.get_data()
    payment_id = user_data.get('current_payment_id')
    expected_amount = user_data.get('expected_amount')
    
    if not payment_id or not expected_amount:
        await message.answer("Произошла ошибка с вашим платежным запросом. Пожалуйста, попробуйте снова.", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    try:
        paid_amount = float(message.text.replace(',', '.'))
        if paid_amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму (например: 100000).", reply_markup=get_back_to_main_menu_keyboard())
        return
    
    # Retrieve product details for delivery
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT p.id, p.name, p.description, p.image_url, p.image_url2, p.price FROM products p JOIN pending_payments pp ON p.id = pp.product_id WHERE pp.id = ?", (payment_id,))
    product_info = cursor.fetchone()
    conn.close()
    
    if not product_info:
        await message.answer("Извините, товар для вашего платежа не найден. Свяжитесь с администратором.", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return
    
    product_id, product_name, product_description, image_url, image_url2, product_price = product_info
    
    if paid_amount >= expected_amount:
        # Payment successful or overpaid
        update_pending_payment_status_db(payment_id, 'completed')
        
        # Handle overpayment
        excess_amount = paid_amount - expected_amount
        if excess_amount > 0:
            update_user_balance_and_spent(user_telegram_id, excess_amount)
            await message.answer(f"✅ Оплата успешно получена! Ваш товар отправлен.\n"
                                 f"У вас осталось {excess_amount:.2f} сум на балансе. Вы можете использовать их для следующих покупок.",
                                 reply_markup=get_main_menu_keyboard())
            asyncio.create_task(_send_telegram_message_task(f"💰 <b>ПЛАТЕЖ ЗАВЕРШЕН (С излишком)</b>\n\n"
                                                            f"ID платежа: {payment_id}\n"
                                                            f"Пользователь: {user_telegram_id}\n"
                                                            f"Товар: {product_name}\n"
                                                            f"Ожидалось: {expected_amount} сум\n"
                                                            f"Оплачено: {paid_amount} сум\n"
                                                            f"Излишек: {excess_amount:.2f} сум (добавлен на баланс пользователя)"))
        else:
            await message.answer("✅ Оплата успешно получена! Ваш товар отправлен.", reply_markup=get_main_menu_keyboard())
            asyncio.create_task(_send_telegram_message_task(f"💰 <b>ПЛАТЕЖ ЗАВЕРШЕН (Точно)</b>\n\n"
                                                            f"ID платежа: {payment_id}\n"
                                                            f"Пользователь: {user_telegram_id}\n"
                                                            f"Товар: {product_name}\n"
                                                            f"Оплачено: {paid_amount} сум"))
        
        # Deliver product
        increment_user_purchases(user_telegram_id)
        update_user_balance_and_spent(user_telegram_id, -product_price)
        
        # Delete product after successful sale
        delete_product_after_sale(product_id)
        asyncio.create_task(_send_telegram_message_task(f"🗑️ <b>ТОВАР АВТОМАТИЧЕСКИ УДАЛЕН ПОСЛЕ ПРОДАЖИ</b>\n\n"
                                                        f"ID товара: {product_id}\n"
                                                        f"Название: {product_name}\n"
                                                        f"Покупатель: {user_telegram_id}"))
        
        max_desc_length = 500
        truncated_description = (product_description[:max_desc_length] + "...") if product_description and len(product_description) > max_desc_length else (product_description if product_description else "Описание отсутствует.")
        
        message_text = f"<b>Ваш товар:</b>\n\n" \
                       f"<b>Название:</b> {product_name}\n" \
                       f"<b>Описание:</b> {truncated_description}\n" \
                       f"<b>Цена:</b> {product_price} сум"
        
        final_image_url_for_telegram = image_url
        if image_url and image_url.startswith("/public/images/"):
            final_image_url_for_telegram = f"{BASE_URL}{image_url}"
        elif not image_url:
            final_image_url_for_telegram = PRODUCT_PLACEHOLDER_IMAGE_URL
        
        final_image_url2_for_telegram = image_url2
        if image_url2 and image_url2.startswith("/public/images/"):
            final_image_url2_for_telegram = f"{BASE_URL}{image_url2}"
        elif not image_url2:
            final_image_url2_for_telegram = None
        
        media_group = []
        if final_image_url_for_telegram:
            media_group.append(InputMediaPhoto(media=final_image_url_for_telegram, caption=message_text, parse_mode=ParseMode.HTML))
        if final_image_url2_for_telegram:
            if not media_group:
                media_group.append(InputMediaPhoto(media=final_image_url2_for_telegram, caption=message_text, parse_mode=ParseMode.HTML))
            else:
                media_group.append(InputMediaPhoto(media=final_image_url2_for_telegram))
        
        try:
            if media_group:
                await bot.send_media_group(chat_id=user_telegram_id, media=media_group)
            else:
                await bot.send_message(chat_id=user_telegram_id, text=message_text, parse_mode=ParseMode.HTML)
            
            review_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Оставить отзыв", callback_data="start_purchase_review")]
            ])
            await bot.send_message(chat_id=user_telegram_id, text="Хотите оставить отзыв о вашей покупке?", reply_markup=review_keyboard)
        except Exception as e:
            print(f"Error sending product to user {user_telegram_id}: {e}")
            await message.answer("Произошла ошибка при отправке товара. Пожалуйста, свяжитесь с администратором.", reply_markup=get_main_menu_keyboard())
    else:
        # Underpayment
        remaining_amount = expected_amount - paid_amount
        update_pending_payment_status_db(payment_id, 'underpaid')
        await message.answer(f"⚠️ Вы оплатили {paid_amount:.2f} сум. Недостаточно средств. Вам не хватает {remaining_amount:.2f} сум для получения товара.\n"
                             f"Пожалуйста, переведите оставшуюся сумму или свяжитесь с администратором.",
                             reply_markup=get_back_to_main_menu_keyboard())
        asyncio.create_task(_send_telegram_message_task(f"❌ <b>ПЛАТЕЖ НЕ ЗАВЕРШЕН (Недостаточно средств)</b>\n\n"
                                                        f"ID платежа: {payment_id}\n"
                                                        f"Пользователь: {user_telegram_id}\n"
                                                        f"Товар: {product_name}\n"
                                                        f"Ожидалось: {expected_amount} сум\n"
                                                        f"Оплачено: {paid_amount} сум\n"
                                                        f"Не хватает: {remaining_amount:.2f} сум"))
    
    await state.clear()

# Reviews functionality
@dp.callback_query(lambda c: c.data == "reviews")
async def handle_reviews_button(call: types.CallbackQuery):
    await call.answer("Одобренные отзывы загружаются...")
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT review_text, rating, created_at FROM reviews
        WHERE status = 'approved'
        ORDER BY created_at DESC
    ''')
    reviews = cursor.fetchall()
    conn.close()
    
    if reviews:
        response_text = "<b>Одобренные отзывы:</b>\n\n"
        for review_text, rating, created_at in reviews:
            stars = "⭐" * rating if rating else ""
            response_text += f"💬 {review_text}\n" \
                             f"Рейтинг: {stars} ({rating}/5)\n" \
                             f"Время: {datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M')}\n\n"
        await call.message.answer(response_text, parse_mode=ParseMode.HTML, reply_markup=get_back_to_main_menu_keyboard())
    else:
        await call.message.answer("Пока нет одобренных отзывов.", reply_markup=get_back_to_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "start_purchase_review")
async def start_review_submission_after_purchase(call: types.CallbackQuery, state: FSMContext):
    await call.answer("Оставить отзыв...")
    await state.set_state(ReviewSubmission.waiting_for_review_text)
    await call.message.answer("Пожалуйста, напишите свой отзыв. Текст должен начинаться с '4.5 al':", reply_markup=get_back_to_main_menu_keyboard())

@dp.message(ReviewSubmission.waiting_for_review_text)
async def process_review_text(message: types.Message, state: FSMContext):
    review_text = message.text
    if not review_text or not review_text.strip().lower().startswith("4.5 al"):
        await message.answer("Отзыв должен начинаться с '4.5 al'. Пожалуйста, введите еще раз:", reply_markup=get_back_to_main_menu_keyboard())
        return
    
    await state.update_data(review_text=review_text)
    await state.set_state(ReviewSubmission.waiting_for_stars)
    await message.answer("Пожалуйста, введите количество звезд (рейтинг) от 1 до 5:", reply_markup=get_back_to_main_menu_keyboard())

@dp.message(ReviewSubmission.waiting_for_stars)
async def process_review_stars(message: types.Message, state: FSMContext):
    try:
        rating = int(message.text)
        if not (1 <= rating <= 5):
            raise ValueError
    except ValueError:
        await message.answer("Неверное количество звезд. Пожалуйста, введите целое число от 1 до 5:", reply_markup=get_back_to_main_menu_keyboard())
        return
    
    user_data = await state.get_data()
    review_text = user_data['review_text']
    telegram_user_id = message.from_user.id
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO reviews (user_telegram_id, review_text, rating, status)
        VALUES (?, ?, ?, ?)
    ''', (telegram_user_id, review_text, rating, 'pending'))
    review_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    await state.clear()
    await message.answer("Ваш отзыв принят и ожидает подтверждения администратором. Спасибо!", reply_markup=get_main_menu_keyboard())
    
    await _send_telegram_message_task(f"📝 <b>НОВЫЙ ОТЗЫВ ДЛЯ ПОДТВЕРЖДЕНИЯ</b>\n\n"
                                      f"ID: {review_id}\n"
                                      f"ID пользователя: {telegram_user_id}\n"
                                      f"Текст: {review_text}\n"
                                      f"Рейтинг: {rating} звезд\n\n"
                                      f"Подтвердите в админ-панели: <a href='http://localhost:8000/admin'>Админ-панель</a>")

@dp.callback_query()
async def handle_other_buttons(call: types.CallbackQuery, state: FSMContext):
    await call.answer("Команда отправляется...")
    print(f"Пользователь {call.from_user.username} ({call.from_user.id}) нажал кнопку: {call.data}")
    
    # Check for specific handlers first
    if call.data == "main_menu":
        await back_to_main_menu_handler(call, state)
        return
    elif call.data == "top_up":
        await handle_top_up_button(call)
        return
    elif call.data == "work":
        await handle_work_button(call)
        return
    elif call.data == "support":
        await handle_support_button(call)
        return
    elif call.data == "rules":
        await handle_rules_button(call)
        return
    elif call.data == "connect_bot":
        await handle_connect_bot_button(call)
        return
    elif call.data == "under_control":
        await handle_under_control_button(call)
        return
    elif call.data == "info":
        await handle_info_button(call)
        return
    elif call.data == "showcase":
        await start_showcase_browse(call, state)
        return
    elif call.data == "start_purchase_review":
        await start_review_submission_after_purchase(call, state)
        return
    
    # If no specific handler, try to fetch content from bot_button_contents
    content = get_button_content_db(call.data)
    if content:
        await call.message.answer(content, parse_mode=ParseMode.HTML, reply_markup=get_back_to_main_menu_keyboard())
    else:
        await call.message.answer(f"Контент для этой кнопки не найден: {call.data}", reply_markup=get_back_to_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "main_menu")
async def back_to_main_menu_handler(call: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer("Возвращено в главное меню.")
    await call.message.answer("Главное меню:", reply_markup=get_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "top_up")
async def handle_top_up_button(call: types.CallbackQuery):
    await call.answer("Информация о вашем счете загружается...")
    user_telegram_id = call.from_user.id
    balance, total_spent = get_user_balance_and_spent(user_telegram_id)
    
    message_text = f"<b>Состояние вашего счета:</b>\n\n" \
                   f"💰 Текущий баланс: {balance:.2f} сум\n" \
                   f"💸 Всего потрачено: {total_spent:.2f} сум\n\n" \
                   f"Для пополнения счета свяжитесь с администратором. Автоматическая система оплаты скоро будет запущена."
    
    await call.message.answer(message_text, parse_mode=ParseMode.HTML, reply_markup=get_back_to_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "work")
async def handle_work_button(call: types.CallbackQuery):
    await call.answer("Информация о работе...")
    content = get_button_content_db("work")
    if content:
        await call.message.answer(content, reply_markup=get_back_to_main_menu_keyboard())
    else:
        await call.message.answer("Для получения информации о возможностях работы свяжитесь с администратором.", reply_markup=get_back_to_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "support")
async def handle_support_button(call: types.CallbackQuery):
    await call.answer("Поддержка...")
    content = get_button_content_db("support")
    if content:
        await call.message.answer(content, reply_markup=get_back_to_main_menu_keyboard())
    else:
        await call.message.answer(f"Если у вас есть вопросы, пожалуйста, свяжитесь с нашей службой поддержки. Для связи с администратором: @{ADMIN_USERNAME}", reply_markup=get_back_to_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "rules")
async def handle_rules_button(call: types.CallbackQuery):
    await call.answer("Правила...")
    content = get_button_content_db("rules")
    if content:
        await call.message.answer(content, reply_markup=get_back_to_main_menu_keyboard())
    else:
        rules_text = """Правила рассмотрения и заполнения заявки для уточнений при ненаходе: ПРЕДОСТАВЬТЕ ПО ПУНКТАМ:
- Номер заказа
- адрес фактической покупки ( ПЕРЕСЛАТЬ с Бота сообщением ) Внимание -  не копировать
- фото с места (несколько с разных ракурсов)
- описание состояния места клада по прибытию на адрес

⚠️⚠️ ЕСЛИ АДРЕС НЕ СООТВЕТСТВУЕТ ФОТО/КООРДИНАТАМ ⚠️⚠️ предоставьте, пожалуйста, 4 фотографии местности с отметкой координат. Координаты на Ваших фото должны совпадать с координатами в заказе, желательно в таком же ракурсе как у курьера. Для того чтобы получить фотографии с отметкой GPS координат, можете использовать Notecam если у Вас Android, или Solocator если используете iOS. Ожидаю фотографии в пределах регламентного времени

☝️☝️ВАЖНО ЗНАТЬ! РАССМОТРЕНИЕ И УТОЧНЕНИЕ ВАШЕЙ ЗАЯВКИ ДОПУСТИМО В ТЕЧЕНИИ 3 ЧАСОВ С МОМЕНТА ПОКУПКИ!

‼️ВНИМАНИЕ‼️
❌ПОЧЕМУ ВАМ МОЖЕТ БЫТЬ ОТКАЗАНО В РАССМОТРЕНИИ?❌

1. Мы оставляем за собой право на отказ в обслуживании, УТОЧНЕНИЯХ или решении той или иной проблемы без каких-либо разъяснений.
2. Претензии по ненаходам, недовесам и другим проблемам в заказах принимаются в течение 3-х  часов с момента покупки  и решаются только через ЛС!
3. Передача информации о кладе третьим лицам запрещена - это лишает Вас права на помощь в поисках  в случае ненахода!
4. Шантаж плохими отзывами, хамство, оскорбления сотрудников магазина и не пристойное поведение - АВТОМАТИЧЕСКИ лишает Вас права на получение помощи в поисках  в случае ненахода!
5. Если фотографии с места трагедии при сообщении о проблеме были сделаны не сразу и Вы якобы поедете фотографировать место и предоставите их спустя 3-х и более часов - это лишает Вас права на помощь в поисках. Для начала предоставьте пересланным сообщением сам адрес, который Вам выдан ботом! Затем фото, сделанные Вами лично!

ПЕРЕЗАКЛАД НА ПЕРЕЗАКЛАД НЕ ВЫДАЁТСЯ"""
        await call.message.answer(rules_text, reply_markup=get_back_to_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "connect_bot")
async def handle_connect_bot_button(call: types.CallbackQuery):
    await call.answer("Подключение бота...")
    user_telegram_id = call.from_user.id
    total_purchases = get_user_purchases(user_telegram_id)
    required_purchases = 1
    
    if total_purchases >= required_purchases:
        message = "Вы можете создать личного бота! Инструкции по созданию бота будут предоставлены в ближайшее время."
    else:
        message = f"Вы не можете создавать личных ботов, так как не совершено необходимое количество покупок.\n" \
                  f"Всего покупок: {total_purchases}\n" \
                  f"Необходимое количество покупок для создания бота: {required_purchases}"
    
    add_or_update_button_content_db("connect_bot", message)
    await call.message.answer(message, reply_markup=get_back_to_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "under_control")
async def handle_under_control_button(call: types.CallbackQuery):
    await call.answer("TRUE CORE...")
    content = get_button_content_db("under_control")
    if content:
        await call.message.answer(content, reply_markup=get_back_to_main_menu_keyboard())
    else:
        await call.message.answer("Этот раздел находится в разработке. Дополнительная информация будет предоставлена в ближайшее время.", reply_markup=get_back_to_main_menu_keyboard())

@dp.callback_query(lambda c: c.data == "info")
async def handle_info_button(call: types.CallbackQuery):
    await call.answer("Информация...")
    content = get_button_content_db("info")
    if content:
        await call.message.answer(content, reply_markup=get_back_to_main_menu_keyboard())
    else:
        await call.message.answer("В этом разделе содержится общая информация о нашем магазине. Для дополнительных вопросов используйте кнопку 'Поддержка'.", reply_markup=get_back_to_main_menu_keyboard())

# General functions
def generate_verification_code():
    return str(secrets.randbelow(900000) + 100000)

def save_verification_code(username, code):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM verification_codes WHERE username = ?', (username,))
    expires_at = datetime.utcnow() + timedelta(minutes=5)
    cursor.execute('''
        INSERT INTO verification_codes (username, code, expires_at)
        VALUES (?, ?, ?)
    ''', (username, code, expires_at.isoformat()))
    conn.commit()
    conn.close()

def verify_code(username, code):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, expires_at FROM verification_codes
        WHERE username = ? AND code = ? AND used = 0
    ''', (username, code))
    result = cursor.fetchone()
    if result:
        code_id, expires_at_str = result
        expires_at_dt = datetime.fromisoformat(expires_at_str)
        if datetime.utcnow() < expires_at_dt:
            cursor.execute('''
                UPDATE verification_codes
                SET used = 1
                WHERE id = ?
            ''', (code_id,))
            conn.commit()
            conn.close()
            return True
    conn.close()
    return False

def log_login_attempt(username, ip_address, success, user_agent):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO login_attempts (username, ip_address, success, user_agent)
        VALUES (?, ?, ?, ?)
    ''', (username, ip_address, 1 if success else 0, user_agent))
    conn.commit()
    conn.close()

def check_user_blocked(username):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT blocked_until, is_blocked
        FROM users
        WHERE username = ?
    ''', (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        blocked_until, is_blocked = result
        if is_blocked == 1 and blocked_until:
            blocked_until_dt = datetime.fromisoformat(blocked_until)
            if datetime.now() < blocked_until_dt:
                return True, blocked_until_dt
            else:
                conn = sqlite3.connect('users.db')
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE users
                    SET is_blocked = 0, blocked_until = NULL, failed_attempts = 0, failed_verification_attempts = 0
                    WHERE username = ?
                ''', (username,))
                conn.commit()
                conn.close()
                return False, None
    return False, None

def update_failed_attempts(username, success=False):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    if success:
        cursor.execute('''
            UPDATE users
            SET failed_attempts = 0, last_attempt = ?, blocked_until = NULL
            WHERE username = ?
        ''', (datetime.now(), username))
    else:
        cursor.execute('''
            UPDATE users
            SET failed_attempts = failed_attempts + 1, last_attempt = ?
            WHERE username = ?
        ''', (datetime.now(), username))
        cursor.execute('SELECT failed_attempts FROM users WHERE username = ?', (username,))
        result = cursor.fetchone()
        if result and result[0] >= 3:
            blocked_until = datetime.now() + timedelta(days=365)
            cursor.execute('''
                UPDATE users
                SET blocked_until = ?, is_blocked = 1
                WHERE username = ?
            ''', (blocked_until, username))
            asyncio.create_task(_send_telegram_message_task(f"🚨 <b>ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН (Автоматически)</b>\n\n"
                                                            f"👤 Пользователь: {username}\n"
                                                            f"⏰ Время блокировки: 1 год\n"
                                                            f"📅 До: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))
    conn.commit()
    conn.close()

def authenticate_user(username, password):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    cursor.execute('''
        SELECT id, password_hash FROM users
        WHERE username = ?
    ''', (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        user_id, stored_password_hash = result
        if stored_password_hash == password_hash:
            return True
        else:
            return False
    return False

def get_client_ip(request: Request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return getattr(request.client, 'host', 'unknown')

# Bot user management functions
def increment_user_purchases(user_telegram_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO bot_users (telegram_id) VALUES (?)
    ''', (user_telegram_id,))
    cursor.execute('''
        UPDATE bot_users
        SET total_purchases = total_purchases + 1
        WHERE telegram_id = ?
    ''', (user_telegram_id,))
    conn.commit()
    conn.close()

def get_user_purchases(user_telegram_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT total_purchases FROM bot_users WHERE telegram_id = ?", (user_telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

def update_user_balance_and_spent(user_telegram_id: int, amount: float):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR IGNORE INTO bot_users (telegram_id) VALUES (?)
    ''', (user_telegram_id,))
    cursor.execute('''
        UPDATE bot_users
        SET balance = balance - ?, total_spent = total_spent + ?
        WHERE telegram_id = ?
    ''', (amount, amount, user_telegram_id))
    conn.commit()
    conn.close()

def get_user_balance_and_spent(user_telegram_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT balance, total_spent FROM bot_users WHERE telegram_id = ?", (user_telegram_id,))
    result = cursor.fetchone()
    conn.close()
    return result if result else (0.0, 0.0)

def block_bot_user_by_telegram_id(user_telegram_id: int, duration_days: int = 365):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    blocked_until = datetime.now() + timedelta(days=duration_days)
    cursor.execute('''
        INSERT OR IGNORE INTO bot_users (telegram_id) VALUES (?)
    ''', (user_telegram_id,))
    cursor.execute('''
        UPDATE bot_users
        SET is_blocked = 1, blocked_until = ?
        WHERE telegram_id = ?
    ''', (blocked_until, user_telegram_id))
    conn.commit()
    conn.close()
    asyncio.create_task(_send_telegram_message_task(f"🚨 <b>ПОЛЬЗОВАТЕЛЬ БОТА ЗАБЛОКИРОВАН (Администратором)</b>\n\n"
                                                    f"👤 Telegram ID: {user_telegram_id}\n"
                                                    f"⏰ Время блокировки: {duration_days} дней\n"
                                                    f"📅 До: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))

def unblock_bot_user_by_telegram_id(user_telegram_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE bot_users
        SET is_blocked = 0, blocked_until = NULL
        WHERE telegram_id = ?
    ''', (user_telegram_id,))
    conn.commit()
    conn.close()
    asyncio.create_task(_send_telegram_message_task(f"✅ <b>ПОЛЬЗОВАТЕЛЬ БОТА РАЗБЛОКИРОВАН (Администратором)</b>\n\n"
                                                    f"👤 Telegram ID: {user_telegram_id}"))

def check_bot_user_blocked(user_telegram_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT blocked_until, is_blocked
        FROM bot_users
        WHERE telegram_id = ?
    ''', (user_telegram_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        blocked_until, is_blocked = result
        if is_blocked == 1 and blocked_until:
            blocked_until_dt = datetime.fromisoformat(blocked_until)
            if datetime.now() < blocked_until_dt:
                return True, blocked_until_dt
            else:
                conn = sqlite3.connect('users.db')
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE bot_users
                    SET is_blocked = 0, blocked_until = NULL
                    WHERE telegram_id = ?
                ''', (user_telegram_id,))
                conn.commit()
                conn.close()
                return False, None
    return False, None

# Pending payments functions
def add_pending_payment_db(user_telegram_id: int, product_id: int, amount: float):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO pending_payments (user_telegram_id, product_id, amount, status)
        VALUES (?, ?, ?, ?)
    ''', (user_telegram_id, product_id, amount, 'pending'))
    payment_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return payment_id

def get_pending_payment_db(payment_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_telegram_id, product_id, amount, status
        FROM pending_payments WHERE id = ?
    ''', (payment_id,))
    payment = cursor.fetchone()
    conn.close()
    return payment

def update_pending_payment_status_db(payment_id: int, status: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE pending_payments SET status = ? WHERE id = ?", (status, payment_id))
    conn.commit()
    conn.close()

# Admin panel database functions
def get_all_users():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('SELECT username, is_blocked, blocked_until FROM users')
    users = cursor.fetchall()
    conn.close()
    return users

def add_new_user(username: str, password: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    password_hash = hashlib.sha256(password.encode()).hexdigest()
    try:
        cursor.execute('''
            INSERT INTO users (username, password_hash)
            VALUES (?, ?)
        ''', (username, password_hash))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def block_user_admin(username: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    blocked_until = datetime.now() + timedelta(days=365)
    cursor.execute('''
        UPDATE users
        SET is_blocked = 1, blocked_until = ?, failed_attempts = 0, failed_verification_attempts = 0
        WHERE username = ?
    ''', (blocked_until, username))
    conn.commit()
    conn.close()
    asyncio.create_task(_send_telegram_message_task(f"🚨 <b>ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН АДМИНИСТРАТОРОМ</b>\n\n"
                                                    f"👤 Пользователь: {username}\n"
                                                    f"⏰ Время блокировки: 1 год\n"
                                                    f"📅 До: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))

def unblock_user_admin(username: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET is_blocked = 0, blocked_until = NULL, failed_attempts = 0, failed_verification_attempts = 0
        WHERE username = ?
    ''', (username,))
    conn.commit()
    conn.close()
    asyncio.create_task(_send_telegram_message_task(f"✅ <b>ПОЛЬЗОВАТЕЛЬ РАЗБЛОКИРОВАН АДМИНИСТРАТОРОМ</b>\n\n"
                                                    f"👤 Пользователь: {username}"))

def delete_user_admin(username: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('DELETE FROM users WHERE username = ?', (username,))
    conn.commit()
    conn.close()
    asyncio.create_task(_send_telegram_message_task(f"🗑️ <b>ПОЛЬЗОВАТЕЛЬ УДАЛЕН АДМИНИСТРАТОРОМ</b>\n\n"
                                                    f"👤 Пользователь: {username}"))

# Bot buttons management functions
def get_all_bot_buttons():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, text, callback_data, order_index, is_active FROM bot_buttons ORDER BY order_index")
    buttons = cursor.fetchall()
    conn.close()
    return buttons

def add_bot_button_db(text: str, callback_data: str, order_index: int, is_active: bool):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO bot_buttons (text, callback_data, order_index, is_active) VALUES (?, ?, ?, ?)",
                       (text, callback_data, order_index, 1 if is_active else 0))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def update_bot_button_db(button_id: int, text: str, callback_data: str, order_index: int, is_active: bool):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE bot_buttons SET text = ?, callback_data = ?, order_index = ?, is_active = ? WHERE id = ?",
                       (text, callback_data, order_index, 1 if is_active else 0, button_id))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def delete_bot_button_db(button_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bot_buttons WHERE id = ?", (button_id,))
    conn.commit()
    conn.close()

# Bot button content management functions
def add_or_update_button_content_db(callback_data: str, content: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO bot_button_contents (callback_data, content)
            VALUES (?, ?)
            ON CONFLICT(callback_data) DO UPDATE SET content = EXCLUDED.content
        ''', (callback_data, content))
        conn.commit()
        return True
    except Exception as e:
        print(f"Ошибка при добавлении/обновлении содержимого кнопки: {e}")
        return False
    finally:
        conn.close()

def get_button_content_db(callback_data: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT content FROM bot_button_contents WHERE callback_data = ?", (callback_data,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else None

def delete_button_content_db(content_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("DELETE FROM bot_button_contents WHERE id = ?", (content_id,))
    conn.commit()
    conn.close()

def get_all_button_contents():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, callback_data, content FROM bot_button_contents ORDER BY callback_data")
    contents = cursor.fetchall()
    conn.close()
    return contents

# Region price management functions
def get_all_regions_with_prices():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM regions ORDER BY name")
    regions = cursor.fetchall()
    regions_with_prices = []
    
    for region_id, region_name in regions:
        cursor.execute("SELECT item_type, price FROM region_prices WHERE region_id = ?", (region_id,))
        prices = cursor.fetchall()
        prices_dict = {item_type: price for item_type, price in prices}
        regions_with_prices.append({
            "id": region_id,
            "name": region_name,
            "LTS_price": prices_dict.get("LTS", "N/A"),
            "BTS_price": prices_dict.get("BTS", "N/A")
        })
    
    conn.close()
    return regions_with_prices

def set_region_price_db(region_id: int, item_type: str, price: float):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO region_prices (region_id, item_type, price)
        VALUES (?, ?, ?)
    ''', (region_id, item_type, price))
    conn.commit()
    conn.close()

def get_region_name_by_id(region_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM regions WHERE id = ?", (region_id,))
    name = cursor.fetchone()
    conn.close()
    return name[0] if name else "Неизвестная область"

def get_district_name_by_id(district_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM districts WHERE id = ?", (district_id,))
    name = cursor.fetchone()
    conn.close()
    return name[0] if name else "Неизвестный район"

# Product management functions
def get_pending_products():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id, p.name, p.description, p.image_url, p.price, p.region_id, p.district_id, r.name, d.name, p.created_by_telegram_id, p.created_at, p.image_url2
        FROM products p
        LEFT JOIN regions r ON p.region_id = r.id
        LEFT JOIN districts d ON p.district_id = d.id
        WHERE p.status = 'pending'
        ORDER BY p.created_at DESC
    ''')
    products = cursor.fetchall()
    conn.close()
    return products

def approve_product_db(product_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET status = 'approved' WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def reject_product_db(product_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE products SET status = 'rejected' WHERE id = ?", (product_id,))
    conn.commit()
    conn.close()

def update_product_db(product_id: int, name: str, description: str, price: float, region_id: int, district_id: int, image_url1: str = None, image_url2: str = None):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE products
        SET name = ?, description = ?, price = ?, region_id = ?, district_id = ?, image_url = ?, image_url2 = ?
        WHERE id = ?
    ''', (name, description, price, region_id, district_id, image_url1, image_url2, product_id))
    conn.commit()
    conn.close()

# Review management functions
def get_pending_reviews():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, user_telegram_id, review_text, rating, created_at
        FROM reviews
        WHERE status = 'pending'
        ORDER BY created_at DESC
    ''')
    reviews = cursor.fetchall()
    conn.close()
    return reviews

def approve_review_db(review_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE reviews SET status = 'approved' WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()

def reject_review_db(review_id: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("UPDATE reviews SET status = 'rejected' WHERE id = ?", (review_id,))
    conn.commit()
    conn.close()

def update_review_db(review_id: int, review_text: str, rating: int):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE reviews
        SET review_text = ?, rating = ?
        WHERE id = ?
    ''', (review_text, rating, review_id))
    conn.commit()
    conn.close()

# Region and district functions
def get_all_regions():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM regions ORDER BY name")
    regions = cursor.fetchall()
    conn.close()
    return regions

def get_all_districts():
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, region_id FROM districts ORDER BY name")
    districts = cursor.fetchall()
    conn.close()
    return districts

def add_region_db(name: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO regions (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def add_district_db(region_id: int, name: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO districts (region_id, name) VALUES (?, ?)", (region_id, name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

# FastAPI setup
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    asyncio.create_task(dp.start_polling(bot))
    yield
    await bot.session.close()

app = FastAPI(title="Система безопасного входа", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
templates = Jinja2Templates(directory="templates")

# Static files
app.mount("/public", StaticFiles(directory="public"), name="public")

# FastAPI routes
@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    client_ip = get_client_ip(request)
    user_agent = request.headers.get("user-agent", "")
    
    is_blocked, blocked_until = check_user_blocked(username)
    if is_blocked:
        log_login_attempt(username, client_ip, False, user_agent)
        asyncio.create_task(_send_telegram_message_task(f"🚫 <b>ПОПЫТКА ВХОДА ЗАБЛОКИРОВАННОГО ПОЛЬЗОВАТЕЛЯ</b>\n\n"
                                                        f"👤 Пользователь: {username}\n"
                                                        f"🌐 IP: {client_ip}\n"
                                                        f"⏰ Время блокировки: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))
        return templates.TemplateResponse("login.html", {"request": request,
                                                          "error": f"Аккаунт заблокирован до {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}."})
    
    if authenticate_user(username, password):
        code = generate_verification_code()
        save_verification_code(username, code)
        asyncio.create_task(_send_telegram_message_task(f"🔐 <b>ПОДТВЕРЖДЕНИЕ ВХОДА</b>\n\n"
                                                        f"👤 Пользователь: {username}\n"
                                                        f"🌐 IP: {client_ip}\n"
                                                        f"🔑 Код: <code>{code}</code>\n"
                                                        f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        request.session["username"] = username
        request.session["authenticated"] = False
        log_login_attempt(username, client_ip, True, user_agent)
        update_failed_attempts(username, success=True)
        return RedirectResponse(url="/verify", status_code=302)
    else:
        log_login_attempt(username, client_ip, False, user_agent)
        update_failed_attempts(username, success=False)
        asyncio.create_task(_send_telegram_message_task(f"❌ <b>НЕУДАЧНЫЙ ВХОД</b>\n\n"
                                                        f"👤 Пользователь: {username}\n"
                                                        f"🌐 IP: {client_ip}\n"
                                                        f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        return templates.TemplateResponse("login.html", {"request": request, "error": "Неверное имя пользователя или пароль!"})

@app.get("/verify", response_class=HTMLResponse)
async def verify_page(request: Request):
    if "username" not in request.session:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("verify.html", {"request": request})

@app.post("/verify")
async def verify(request: Request, code: str = Form(...)):
    if "username" not in request.session:
        return RedirectResponse(url="/", status_code=302)
    
    username = request.session["username"]
    client_ip = get_client_ip(request)
    
    if verify_code(username, code):
        request.session["authenticated"] = True
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET failed_verification_attempts = 0 WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        asyncio.create_task(_send_telegram_message_task(f"✅ <b>ВХОД УСПЕШЕН</b>\n\n"
                                                        f"👤 Пользователь: {username}\n"
                                                        f"🌐 IP: {client_ip}\n"
                                                        f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        if username == "admin" or username == "admin2":
            return RedirectResponse(url="/admin", status_code=302)
        return RedirectResponse(url="/welcome", status_code=302)
    else:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET failed_verification_attempts = failed_verification_attempts + 1 WHERE username = ?", (username,))
        cursor.execute("SELECT failed_verification_attempts FROM users WHERE username = ?", (username,))
        current_failed_attempts = cursor.fetchone()[0]
        conn.commit()
        
        if current_failed_attempts >= 2:
            blocked_until = datetime.now() + timedelta(days=365)
            cursor.execute('''
                UPDATE users
                SET is_blocked = 1, blocked_until = ?, failed_verification_attempts = 0
                WHERE username = ?
            ''', (blocked_until, username))
            conn.commit()
            conn.close()
            asyncio.create_task(_send_telegram_message_task(f"🚨 <b>ПОЛЬЗОВАТЕЛЬ ЗАБЛОКИРОВАН (Ошибка кода)</b>\n\n"
                                                            f"👤 Пользователь: {username}\n"
                                                            f"⏰ Время блокировки: 1 год\n"
                                                            f"📅 До: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))
            return templates.TemplateResponse("login.html", {"request": request, "error": f"Ваш аккаунт заблокирован до {blocked_until.strftime('%Y-%m-%d %H:%M:%S')} из-за неверных кодов."})
        
        conn.close()
        asyncio.create_task(_send_telegram_message_task(f"🚫 <b>НЕВЕРНЫЙ КОД ПОДТВЕРЖДЕНИЯ</b>\n\n"
                                                        f"👤 Пользователь: {username}\n"
                                                        f"🌐 IP: {client_ip}\n"
                                                        f"🔑 Введенный код: {code}\n"
                                                        f"⏰ Время: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        return templates.TemplateResponse("verify.html", {"request": request, "error": "Неверный код подтверждения!"})

@app.get("/welcome", response_class=HTMLResponse)
async def welcome(request: Request):
    if not request.session.get("authenticated"):
        return RedirectResponse(url="/", status_code=302)
    username = request.session.get("username")
    return templates.TemplateResponse("welcome.html", {"request": request, "username": username})

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=302)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# Admin panel routes
@app.get("/admin", response_class=HTMLResponse)
async def admin_panel(request: Request):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    
    users = get_all_users()
    buttons = get_all_bot_buttons()
    regions_with_prices = get_all_regions_with_prices()
    pending_products = get_pending_products()
    pending_reviews = get_pending_reviews()
    all_regions_list = get_all_regions()
    all_districts_list = get_all_districts()
    region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
    bot_button_contents = get_all_button_contents()
    
    # Prepare regions with their districts for display
    regions_with_districts = []
    for region_id, region_name in all_regions_list:
        districts_for_region = [d for d in all_districts_list if d[2] == region_id]
        regions_with_districts.append({
            "id": region_id,
            "name": region_name,
            "districts": districts_for_region
        })
    
    return templates.TemplateResponse("admin.html", {
        "request": request,
        "users": users,
        "buttons": buttons,
        "regions": regions_with_prices,
        "pending_products": pending_products,
        "pending_reviews": pending_reviews,
        "all_regions": all_regions_list,
        "all_districts": all_districts_list,
        "region_names_map": region_names_map,
        "bot_button_contents": bot_button_contents,
        "regions_with_districts": regions_with_districts
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
