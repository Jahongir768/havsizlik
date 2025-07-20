# import os
# import sqlite3
# import hashlib
# import secrets
# import asyncio
# from datetime import datetime, timedelta
# from contextlib import asynccontextmanager

# from fastapi import FastAPI, Request, Form
# from fastapi.responses import HTMLResponse, RedirectResponse
# from fastapi.templating import Jinja2Templates
# from starlette.middleware.sessions import SessionMiddleware

# from aiogram import Bot, Dispatcher, types, F
# from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
# from aiogram.filters import CommandStart
# from aiogram.enums import ParseMode
# from aiogram.fsm.context import FSMContext
# from aiogram.fsm.state import State, StatesGroup

# # Environment variables
# TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7953097750:AAFigo9U_h89oCuHt1jHXDZkEv_fcLzme3Q")
# ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5757696133")
# SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))

# QR_CODE_IMAGE_URL = "/public/images/qr-code.png"
# PRODUCT_PLACEHOLDER_IMAGE_URL = "/public/images/product_placeholder.png" # Mahsulot rasmi uchun placeholder

# # --- Telegram Bot Setup ---
# bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
# dp = Dispatcher()

# # --- FSM States for Product Creation, Review Submission, and Product Browsing ---
# class ProductCreation(StatesGroup):
#   waiting_for_region = State()
#   waiting_for_district = State()
#   waiting_for_name = State()
#   waiting_for_description = State()
#   waiting_for_image = State()
#   waiting_for_price = State()

# class ReviewSubmission(StatesGroup):
#   waiting_for_review_text = State()
#   waiting_for_stars = State() # Yangi holat

# class ProductBrowse(StatesGroup):
#   waiting_for_browse_region = State()
#   waiting_for_browse_district = State()

# # --- Database Setup ---
# def init_db():
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()

#   # Drop tables to ensure fresh schema on each run (for development)
#   cursor.execute('DROP TABLE IF EXISTS users')
#   cursor.execute('DROP TABLE IF EXISTS login_attempts')
#   cursor.execute('DROP TABLE IF EXISTS verification_codes')
#   cursor.execute('DROP TABLE IF EXISTS bot_buttons')
#   cursor.execute('DROP TABLE IF EXISTS region_prices')
#   cursor.execute('DROP TABLE IF EXISTS products')
#   cursor.execute('DROP TABLE IF EXISTS reviews')
#   cursor.execute('DROP TABLE IF EXISTS districts') # Drop districts before regions
#   cursor.execute('DROP TABLE IF EXISTS regions')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS users (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           username TEXT UNIQUE NOT NULL,
#           password_hash TEXT NOT NULL,
#           is_blocked INTEGER DEFAULT 0,
#           failed_attempts INTEGER DEFAULT 0,
#           failed_verification_attempts INTEGER DEFAULT 0,
#           last_attempt TIMESTAMP,
#           blocked_until TIMESTAMP,
#           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#       )
#   ''')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS login_attempts (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           username TEXT,
#           ip_address TEXT,
#           success INTEGER,
#           timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#           user_agent TEXT
#       )
#   ''')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS verification_codes (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           username TEXT,
#           code TEXT,
#           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#           expires_at TIMESTAMP,
#           used INTEGER DEFAULT 0
#       )
#   ''')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS bot_buttons (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           text TEXT NOT NULL,
#           callback_data TEXT UNIQUE NOT NULL,
#           order_index INTEGER DEFAULT 0,
#           is_active INTEGER DEFAULT 1
#       )
#   ''')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS regions (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           name TEXT UNIQUE NOT NULL
#       )
#   ''')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS districts (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           region_id INTEGER NOT NULL,
#           name TEXT NOT NULL,
#           UNIQUE(region_id, name),
#           FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
#       )
#   ''')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS region_prices (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           region_id INTEGER NOT NULL,
#           item_type TEXT NOT NULL,
#           price REAL NOT NULL,
#           UNIQUE(region_id, item_type),
#           FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
#       )
#   ''')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS products (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           name TEXT NOT NULL,
#           description TEXT,
#           image_url TEXT,
#           price REAL NOT NULL,
#           region_id INTEGER,
#           district_id INTEGER,
#           status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
#           created_by_telegram_id INTEGER NOT NULL,
#           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
#           FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE SET NULL,
#           FOREIGN KEY (district_id) REFERENCES districts(id) ON DELETE SET NULL
#       )
#   ''')

#   cursor.execute('''
#       CREATE TABLE IF NOT EXISTS reviews (
#           id INTEGER PRIMARY KEY AUTOINCREMENT,
#           user_telegram_id INTEGER NOT NULL,
#           review_text TEXT NOT NULL,
#           rating INTEGER, -- Yangi: Reyting uchun ustun
#           status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
#           created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
#       )
#   ''')

#   # Standart admin foydalanuvchisini yaratish (Yangi parol bilan)
#   admin_password = hashlib.sha256('newadmin123'.encode()).hexdigest() # YANGI ADMIN PAROLI
#   cursor.execute('''
#       INSERT INTO users (username, password_hash)
#       VALUES (?, ?)
#   ''', ('admin', admin_password))
#   conn.commit()

#   # Ikkinchi admin foydalanuvchisini yaratish
#   admin2_password = hashlib.sha256('newadmin1234'.encode()).hexdigest()
#   cursor.execute('''
#       INSERT INTO users (username, password_hash)
#       VALUES (?, ?)
#   ''', ('admin2', admin2_password))
#   conn.commit()

#   # Standart bot tugmalarini yaratish
#   default_buttons = [
#       ("📍 Выбрать город", "choose_city", 10),
#       ("⬆️ Пополнить счет", "top_up", 20),
#       ("⭕ TRUE CORE ", "under_control", 30),
#       ("💰 Работа", "work", 40),
#       ("📄 Правила", "rules", 50),
#       ("🆘 Поддержка", "support", 60),
#       ("🛒 ВИТРИНА", "showcase", 70), # Vitrina tugmasi
#       ("ℹ️ Информация", "info", 80),
#       ("⭐ Отзывы", "reviews", 90), # Otziv tugmasi
#       ("🤖 Подключить своего бота", "connect_bot", 100),
#       ("🛍️ Купить", "buy", 5)
#   ]
#   for text, callback_data, order_index in default_buttons:
#       cursor.execute("INSERT INTO bot_buttons (text, callback_data, order_index, is_active) VALUES (?, ?, ?, ?)",
#                      (text, callback_data, order_index, 1))
#   conn.commit()

#   # O'zbekiston viloyatlarini qo'shish
#   uzbek_regions = [
#       "Andijon viloyati", "Buxoro viloyati", "Farg'ona viloyati", "Jizzax viloyati",
#       "Xorazm viloyati", "Namangan viloyati", "Navoiy viloyati", "Qashqadaryo viloyati",
#       "Samarqand viloyati", "Sirdaryo viloyati", "Surxondaryo viloyati", "Toshkent viloyati",
#       "Qoraqalpog'iston Respublikasi"
#   ]
#   for region_name in uzbek_regions:
#       cursor.execute('INSERT OR IGNORE INTO regions (name) VALUES (?)', (region_name,))
#   conn.commit()

#   # Ba'zi tumanlarni qo'shish
#   regions_data = cursor.execute("SELECT id, name FROM regions").fetchall()
#   districts_to_add = {
#       "Toshkent viloyati": ["Bekobod tumani", "Bo'stonliq tumani", "Chirchiq shahri", "Toshkent shahri"],
#       "Samarqand viloyati": ["Samarqand shahri", "Urgut tumani", "Tayloq tumani", "Kattaqo'rg'on tumani"],
#       "Andijon viloyati": ["Andijon shahri", "Asaka tumani", "Xo'jaobod tumani", "Qo'rg'ontepa tumani"]
#   }
#   for region_id, region_name in regions_data:
#       if region_name in districts_to_add:
#           for district_name in districts_to_add[region_name]:
#               cursor.execute('INSERT OR IGNORE INTO districts (region_id, name) VALUES (?, ?)', (region_id, district_name))
#   conn.commit()

#   # Test mahsulotlarini qo'shish (tasdiqlangan holatda)
#   tashkent_region_id = cursor.execute("SELECT id FROM regions WHERE name = 'Toshkent viloyati'").fetchone()[0]
#   tashkent_city_district_id = cursor.execute("SELECT id FROM districts WHERE name = 'Toshkent shahri' AND region_id = ?", (tashkent_region_id,)).fetchone()[0]
  
#   cursor.execute('''
#       INSERT INTO products (name, description, image_url, price, region_id, district_id, status, created_by_telegram_id)
#       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#   ''', ('Test Mahsulot 1 (Toshkent)', 'Bu Toshkent shahridagi ajoyib mahsulot.', PRODUCT_PLACEHOLDER_IMAGE_URL, 150000.0, tashkent_region_id, tashkent_city_district_id, 'approved', 123456789))

#   samarkand_region_id = cursor.execute("SELECT id FROM regions WHERE name = 'Samarqand viloyati'").fetchone()[0]
#   samarkand_city_district_id = cursor.execute("SELECT id FROM districts WHERE name = 'Samarqand shahri' AND region_id = ?", (samarkand_region_id,)).fetchone()[0]

#   cursor.execute('''
#       INSERT INTO products (name, description, image_url, price, region_id, district_id, status, created_by_telegram_id)
#       VALUES (?, ?, ?, ?, ?, ?, ?, ?)
#   ''', ('Test Mahsulot 2 (Samarqand)', 'Samarqanddan sifatli mahsulot.', PRODUCT_PLACEHOLDER_IMAGE_URL, 250000.0, samarkand_region_id, samarkand_city_district_id, 'approved', 987654321))

#   conn.commit()
#   conn.close()

# # --- Telegram funksiyalari ---
# async def _send_telegram_message_task(message: str):
#   if not TELEGRAM_BOT_TOKEN or not ADMIN_CHAT_ID:
#       print(f"Telegram sozlanmagan: {message}")
#       return False
#   try:
#       await bot.send_message(chat_id=ADMIN_CHAT_ID, text=message, parse_mode=ParseMode.HTML)
#       return True
#   except Exception as e:
#       print(f"Telegram xatosi: {e}")
#       return False

# def get_main_menu_keyboard():
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("SELECT text, callback_data FROM bot_buttons WHERE is_active = 1 ORDER BY order_index")
#   conn.close()


#   keyboard_rows = []
#   for i in range(0, len(buttons_data), 2):
#       row = []
#       for j in range(2):
#           if i + j < len(buttons_data):
#               text, callback_data = buttons_data[i+j]
#               row.append(InlineKeyboardButton(text=text, callback_data=callback_data))
#       if row:
#           keyboard_rows.append(row)
#   return InlineKeyboardMarkup(inline_keyboard=keyboard_rows)

# conn = sqlite3.connect('users.db')
# cursor = conn.cursor()
# cursor.execute("SELECT text FROM bot_buttons WHERE is_active = 1")
# rows = cursor.fetchall()
# conn.close()

# texts = [r[0] for r in rows]
# if "продавать" in texts:
#     await message.answer_photo(
#             photo="https://example.com/your-image.jpg",  # bu yerga haqiqiy rasm URL yoki fayl ID yoziladi
#             caption="Mana sizning menyuingiz:",
#             reply_markup=keyboard
#         )
#     else:
#         await message.answer("Mana sizning menyuingiz:", reply_markup=keyboard)

# @dp.message(CommandStart())
# async def on_start(message: types.Message):
#   print("Bot ishga tushdi")
#   await message.answer("Assalomu alaykum! sob olish uchun /kupi", reply_markup=get_main_menu_keyboard())

# # --- "Купить" (Sotib olish) oqimi ---
# @dp.callback_query(lambda c: c.data == "buy")
# async def start_product_browse(call: types.CallbackQuery, state: FSMContext):
#   await call.answer("Mahsulotlarni ko'rish...")
#   await state.set_state(ProductBrowse.waiting_for_browse_region)
  
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("SELECT id, name FROM regions ORDER BY name")
#   regions_data = cursor.fetchall()
#   conn.close()

#   region_keyboard_rows = []
#   for region_id, region_name in regions_data:
#       region_keyboard_rows.append([InlineKeyboardButton(text=region_name, callback_data=f"browse_region_{region_id}")])
  
#   region_keyboard = InlineKeyboardMarkup(inline_keyboard=region_keyboard_rows)
#   await call.message.answer("Mahsulot qidirayotgan viloyatingizni tanlang:", reply_markup=region_keyboard)

# @dp.callback_query(F.data.startswith("browse_region_"), ProductBrowse.waiting_for_browse_region)
# async def process_browse_region(call: types.CallbackQuery, state: FSMContext):
#   region_id = int(call.data.split("_")[2])
#   await state.update_data(browse_region_id=region_id)
  
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("SELECT id, name FROM districts WHERE region_id = ? ORDER BY name", (region_id,))
#   districts_data = cursor.fetchall()
#   conn.close()

#   if not districts_data:
#       await call.message.answer("Tanlangan viloyat uchun tumanlar topilmadi. Iltimos, boshqa viloyatni tanlang.")
#       await state.clear()
#       await call.message.answer("Asosiy menyu:", reply_markup=get_main_menu_keyboard())
#       return

#   district_keyboard_rows = []
#   for district_id, district_name in districts_data:
#       district_keyboard_rows.append([InlineKeyboardButton(text=district_name, callback_data=f"browse_district_{district_id}")])
  
#   district_keyboard = InlineKeyboardMarkup(inline_keyboard=district_keyboard_rows)
#   await state.set_state(ProductBrowse.waiting_for_browse_district)
#   await call.message.answer("Mahsulot qidirayotgan tumanni tanlang:", reply_markup=district_keyboard)

# @dp.callback_query(F.data.startswith("browse_district_"), ProductBrowse.waiting_for_browse_district)
# async def process_browse_district(call: types.CallbackQuery, state: FSMContext):
#   district_id = int(call.data.split("_")[2])
#   user_data = await state.get_data()
#   region_id = user_data.get('browse_region_id')

#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       SELECT name, description, image_url, price FROM products
#       WHERE region_id = ? AND district_id = ? AND status = 'approved'
#       ORDER BY created_at DESC
#   ''', (region_id, district_id))
#   products = cursor.fetchall()
#   conn.close()

#   if products:
#       for product in products:
#           name, description, image_url, price = product
#           message_text = f"<b>Mahsulot: {name}</b>\n" \
#                          f"Tavsif: {description}\n" \
#                          f"Narxi: {price} so'm"
          
#           if image_url:
#               await call.message.answer_photo(photo=types.URLInputFile(image_url), caption=message_text, parse_mode=ParseMode.HTML)
#           else:
#               await call.message.answer(message_text, parse_mode=ParseMode.HTML)
#   else:
#       await call.message.answer("Tanlangan hududda tasdiqlangan mahsulotlar topilmadi.")
  
#   await state.clear()
#   await call.message.answer("Asosiy menyu:", reply_markup=get_main_menu_keyboard())

# # --- "ВИТРИНА" (Showcase) tugmasi funksionalligi ---
# @dp.callback_query(lambda c: c.data == "showcase")
# async def handle_showcase_button(call: types.CallbackQuery):
#   await call.answer("Vitrinadagi mahsulotlar...")
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       SELECT p.name, p.description, p.image_url, p.price, r.name, d.name
#       FROM products p
#       LEFT JOIN regions r ON p.region_id = r.id
#       LEFT JOIN districts d ON p.district_id = d.id
#       WHERE p.status = 'approved'
#       ORDER BY p.created_at DESC
#   ''')
#   products = cursor.fetchall()
#   conn.close()

#   if products:
#       for product in products:
#           name, description, image_url, price, region_name, district_name = product
#           # Xato tuzatildi: f-string ichidagi backslash muammosi
#           message_text = (
#               f"<b>Mahsulot: {name}</b>\n"
#               f"Tavsif: {description}\n"
#               f"Narxi: {price} so'm\n"
#               f"Viloyat: {region_name if region_name else 'Nomalum'}\n"
#               f"Tuman: {district_name if district_name else 'Nomalum'}"
#           )
          
#           if image_url:
#               await call.message.answer_photo(photo=types.URLInputFile(image_url), caption=message_text, parse_mode=ParseMode.HTML)
#           else:
#               await call.message.answer(message_text, parse_mode=ParseMode.HTML)
#   else:
#       await call.message.answer("Vitrinada hozircha mahsulotlar mavjud emas.")
  
#   await call.message.answer("Asosiy menyu:", reply_markup=get_main_menu_keyboard())

# # --- "⭐ Отзывы" (Reviews) tugmasi funksionalligi ---
# @dp.callback_query(lambda c: c.data == "reviews")
# async def handle_reviews_button(call: types.CallbackQuery):
#   await call.answer("Tasdiqlangan fikr-mulohazalar...")
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       SELECT review_text, rating, created_at FROM reviews
#       WHERE status = 'approved'
#       ORDER BY created_at DESC
#   ''')
#   reviews = cursor.fetchall()
#   conn.close()

#   if reviews:
#       response_text = "<b>Tasdiqlangan fikr-mulohazalar:</b>\n\n"
#       for review_text, rating, created_at in reviews:
#           stars = "⭐" * rating if rating else ""
#           response_text += f"💬 {review_text}\n" \
#                            f"Reyting: {stars} ({rating}/5)\n" \
#                            f"Vaqt: {datetime.fromisoformat(created_at).strftime('%Y-%m-%d %H:%M')}\n\n"
#       await call.message.answer(response_text, parse_mode=ParseMode.HTML)
#   else:
#       await call.message.answer("Hozircha tasdiqlangan fikr-mulohazalar mavjud emas.")
  
#   await call.message.answer("Asosiy menyu:", reply_markup=get_main_menu_keyboard())


# # --- Product Creation Flow (Admin Panel Only) ---
# # Bu funksiyalar endi bot menyusida ko'rinmaydi, faqat admin panel orqali boshqariladi.
# # Agar siz ularni bot orqali ishlatmoqchi bo'lsangiz, bot_buttons jadvaliga qayta qo'shishingiz kerak.

# # --- Review Submission Flow (After Purchase) ---
# @dp.callback_query(lambda c: c.data.startswith("item_")) # Mahsulot tanlangandan keyin
# async def handle_item_selection(call: types.CallbackQuery):
#   await call.answer("Mahsulot tanlandi...")
#   item_type = call.data.split("_")[1]
  
#   # QR kod rasmini va uning havolasini yuborish
#   await call.message.answer_photo(
#       photo=types.URLInputFile(QR_CODE_IMAGE_URL),
#       caption=f"Siz {item_type} ni tanladingiz. To'lov uchun quyidagi QR koddan foydalaning:\n\n"
#               f"QR kod havolasi: `{QR_CODE_IMAGE_URL}`"
#   )
  
#   # Fikr qoldirish tugmasini qo'shish
#   review_keyboard = InlineKeyboardMarkup(inline_keyboard=[
#       [InlineKeyboardButton(text="Fikr qoldirish", callback_data="start_purchase_review")]
#   ])
#   await call.message.answer("Xaridingiz haqida fikr qoldirmoqchimisiz?", reply_markup=review_keyboard)

# @dp.callback_query(lambda c: c.data == "start_purchase_review")
# async def start_review_submission_after_purchase(call: types.CallbackQuery, state: FSMContext):
#   await call.answer("Fikr-mulohaza qoldirish...")
#   await state.set_state(ReviewSubmission.waiting_for_review_text)
#   await call.message.answer("Iltimos, o'z fikr-mulohazangizni yozing. Matn '4.5 al' bilan boshlanishi shart:")

# @dp.message(ReviewSubmission.waiting_for_review_text)
# async def process_review_text(message: types.Message, state: FSMContext):
#   review_text = message.text
  
#   # Validatsiya: Matn "4.5 al" bilan boshlanishi shart
#   if not review_text or not review_text.strip().lower().startswith("4.5 al"):
#       await message.answer("Fikr-mulohaza '4.5 al' bilan boshlanishi shart. Iltimos, qaytadan kiriting:")
#       return # FSM holatini o'zgartirmaymiz, foydalanuvchi qayta kiritishi kerak

#   await state.update_data(review_text=review_text)
#   await state.set_state(ReviewSubmission.waiting_for_stars)
#   await message.answer("Iltimos, 1 dan 5 gacha yulduzcha (reyting) kiriting:")

# @dp.message(ReviewSubmission.waiting_for_stars)
# async def process_review_stars(message: types.Message, state: FSMContext):
#   try:
#       rating = int(message.text)
#       if not (1 <= rating <= 5):
#           raise ValueError
#   except ValueError:
#       await message.answer("Noto'g'ri yulduzcha kiritildi. Iltimos, 1 dan 5 gacha butun son kiriting:")
#       return # FSM holatini o'zgartirmaymiz

#   user_data = await state.get_data()
#   review_text = user_data['review_text']
#   telegram_user_id = message.from_user.id

#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       INSERT INTO reviews (user_telegram_id, review_text, rating, status)
#       VALUES (?, ?, ?, ?)
#   ''', (telegram_user_id, review_text, rating, 'pending'))
#   review_id = cursor.lastrowid
#   conn.commit()
#   conn.close()

#   await state.clear()
#   await message.answer("Fikr-mulohazangiz qabul qilindi va admin tasdiqlashini kutmoqda. Rahmat!", reply_markup=get_main_menu_keyboard())

#   await _send_telegram_message_task(f"📝 <b>YANGI FIKR-MULOHAZA TASDIQLASH UCHUN</b>\n\n"
#                                     f"ID: {review_id}\n"
#                                     f"Foydalanuvchi ID: {telegram_user_id}\n"
#                                     f"Matn: {review_text}\n"
#                                     f"Reyting: {rating} yulduz\n\n"
#                                     f"Admin panelda tasdiqlang: <a href='http://localhost:8000/admin'>Admin Panel</a>")

# @dp.callback_query()
# async def handle_other_buttons(call: types.CallbackQuery):
#   await call.answer("Buyruq yuborilmoqda...")
#   print(f"Foydalanuvchi {call.from_user.username} ({call.from_user.id}) tugmani bosdi: {call.data}")
#   await call.message.answer(f"✅ Siz tanladingiz: {call.data}")


# # --- Umumiy funksiyalar ---
# def generate_verification_code():
#   return str(secrets.randbelow(900000) + 100000)

# def save_verification_code(username, code):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('DELETE FROM verification_codes WHERE username = ?', (username,))
#   expires_at = datetime.utcnow() + timedelta(minutes=5)
#   cursor.execute('''
#       INSERT INTO verification_codes (username, code, expires_at)
#       VALUES (?, ?, ?)
#   ''', (username, code, expires_at.isoformat()))
#   conn.commit()
#   conn.close()

# def verify_code(username, code):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       SELECT id, expires_at FROM verification_codes
#       WHERE username = ? AND code = ? AND used = 0
#   ''', (username, code))
#   result = cursor.fetchone()
#   if result:
#       code_id, expires_at_str = result
#       expires_at_dt = datetime.fromisoformat(expires_at_str)
#       if datetime.utcnow() < expires_at_dt:
#           cursor.execute('''
#               UPDATE verification_codes
#               SET used = 1
#               WHERE id = ?
#           ''', (code_id,))
#           conn.commit()
#           conn.close()
#           return True
#   conn.close()
#   return False

# def log_login_attempt(username, ip_address, success, user_agent):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       INSERT INTO login_attempts (username, ip_address, success, user_agent)
#       VALUES (?, ?, ?, ?)
#   ''', (username, ip_address, 1 if success else 0, user_agent))
#   conn.commit()
#   conn.close()

# def check_user_blocked(username):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       SELECT blocked_until, is_blocked
#       FROM users
#       WHERE username = ?
#   ''', (username,))
#   result = cursor.fetchone()
#   conn.close()
#   if result:
#       blocked_until, is_blocked = result
#       if is_blocked == 1 and blocked_until:
#           blocked_until_dt = datetime.fromisoformat(blocked_until)
#           if datetime.now() < blocked_until_dt:
#               return True, blocked_until_dt
#           else: # Blocked time expired, unblock automatically
#               conn = sqlite3.connect('users.db')
#               cursor = conn.cursor()
#               cursor.execute('''
#                   UPDATE users
#                   SET is_blocked = 0, blocked_until = NULL, failed_attempts = 0, failed_verification_attempts = 0
#                   WHERE username = ?
#               ''', (username,))
#               conn.commit()
#               conn.close()
#               return False, None
#   return False, None

# def update_failed_attempts(username, success=False):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   if success:
#       cursor.execute('''
#           UPDATE users
#           SET failed_attempts = 0, last_attempt = ?, blocked_until = NULL
#           WHERE username = ?
#       ''', (datetime.now(), username))
#   else:
#       cursor.execute('''
#           UPDATE users
#           SET failed_attempts = failed_attempts + 1, last_attempt = ?
#           WHERE username = ?
#       ''', (datetime.now(), username))
#       cursor.execute('SELECT failed_attempts FROM users WHERE username = ?', (username,))
#       result = cursor.fetchone()
#       if result and result[0] >= 3:
#           blocked_until = datetime.now() + timedelta(hours=24)
#           cursor.execute('''
#               UPDATE users
#               SET blocked_until = ?, is_blocked = 1
#               WHERE username = ?
#           ''', (blocked_until, username))
#           asyncio.create_task(_send_telegram_message_task(f"🚨 <b>FOYDALANUVCHI BLOKLANDI (Avtomatik)</b>\n\n"
#                                                           f"👤 Foydalanuvchi: {username}\n"
#                                                           f"⏰ Bloklangan vaqt: 24 soat\n"
#                                                           f"📅 Gacha: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))
#   conn.commit()
#   conn.close()

# def authenticate_user(username, password):
#     conn = sqlite3.connect('users.db')
#     cursor = conn.cursor()
#     password_hash = hashlib.sha256(password.encode()).hexdigest()
    
#     # Debug: Kiritilgan paroldan hosil bo'lgan xeshni chop etish
#     print(f"DEBUG: Kiritilgan parol xeshi: {password_hash}")

#     cursor.execute('''
#         SELECT id, password_hash FROM users
#         WHERE username = ?
#     ''', (username,))
#     result = cursor.fetchone()
#     conn.close()
    
#     if result:
#         user_id, stored_password_hash = result
#         # Debug: Ma'lumotlar bazasidagi xeshni chop etish
#         print(f"DEBUG: DBdagi parol xeshi ({username}): {stored_password_hash}")
#         if stored_password_hash == password_hash:
#             print(f"DEBUG: Parollar mos keldi for {username}")
#             return True
#         else:
#             print(f"DEBUG: Parollar mos kelmadi for {username}")
#             return False
#     print(f"DEBUG: Foydalanuvchi {username} topilmadi.")
#     return False

# def get_client_ip(request: Request):
#   forwarded = request.headers.get("X-Forwarded-For")
#   if forwarded:
#       return forwarded.split(",")[0].strip()
#   return getattr(request.client, 'host', 'unknown')

# # --- Admin Panel Ma'lumotlar Bazasi Funksiyalari ---
# def get_all_users():
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('SELECT username, is_blocked, blocked_until FROM users')
#   users = cursor.fetchall()
#   conn.close()
#   return users

# def add_new_user(username: str, password: str):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   password_hash = hashlib.sha256(password.encode()).hexdigest()
#   try:
#       cursor.execute('''
#           INSERT INTO users (username, password_hash)
#           VALUES (?, ?)
#       ''', (username, password_hash))
#       conn.commit()
#       return True
#   except sqlite3.IntegrityError:
#       return False
#   finally:
#       conn.close()

# def block_user_admin(username: str):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   blocked_until = datetime.now() + timedelta(hours=24)
#   cursor.execute('''
#       UPDATE users
#       SET is_blocked = 1, blocked_until = ?, failed_attempts = 0, failed_verification_attempts = 0
#       WHERE username = ?
#   ''', (blocked_until, username))
#   conn.commit()
#   conn.close()
#   asyncio.create_task(_send_telegram_message_task(f"🚨 <b>FOYDALANUVCHI ADMIN TOMONIDAN BLOKLANDI</b>\n\n"
#                                                   f"👤 Foydalanuvchi: {username}\n"
#                                                   f"⏰ Bloklangan vaqt: 24 soat\n"
#                                                   f"📅 Gacha: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))

# def unblock_user_admin(username: str):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       UPDATE users
#       SET is_blocked = 0, blocked_until = NULL, failed_attempts = 0, failed_verification_attempts = 0
#       WHERE username = ?
#   ''', (username,))
#   conn.commit()
#   conn.close()
#   asyncio.create_task(_send_telegram_message_task(f"✅ <b>FOYDALANUVCHI ADMIN TOMONIDAN BLOKDAN CHIQARILDI</b>\n\n"
#                                                   f"👤 Foydalanuvchi: {username}"))

# def delete_user_admin(username: str):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('DELETE FROM users WHERE username = ?', (username,))
#   conn.commit()
#   conn.close()
#   asyncio.create_task(_send_telegram_message_task(f"🗑️ <b>FOYDALANUVCHI ADMIN TOMONIDAN O'CHIRILDI</b>\n\n"
#                                                   f"👤 Foydalanuvchi: {username}"))

# # --- Bot tugmalarini boshqarish funksiyalari ---
# def get_all_bot_buttons():
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("SELECT id, text, callback_data, order_index, is_active FROM bot_buttons ORDER BY order_index")
#   buttons = cursor.fetchall()
#   conn.close()
#   return buttons

# def add_bot_button_db(text: str, callback_data: str, order_index: int, is_active: bool):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   try:
#       cursor.execute("INSERT INTO bot_buttons (text, callback_data, order_index, is_active) VALUES (?, ?, ?, ?)",
#                      (text, callback_data, order_index, 1 if is_active else 0))
#       conn.commit()
#       return True
#   except sqlite3.IntegrityError:
#       return False
#   finally:
#       conn.close()

# def update_bot_button_db(button_id: int, text: str, callback_data: str, order_index: int, is_active: bool):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   try:
#       cursor.execute("UPDATE bot_buttons SET text = ?, callback_data = ?, order_index = ?, is_active = ? WHERE id = ?",
#                      (text, callback_data, order_index, 1 if is_active else 0, button_id))
#       conn.commit()
#       return True
#   except sqlite3.IntegrityError:
#       return False
#   finally:
#       conn.close()

# def delete_bot_button_db(button_id: int):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("DELETE FROM bot_buttons WHERE id = ?", (button_id,))
#   conn.commit()
#   conn.close()

# # --- Hudud narxlarini boshqarish funksiyalari ---
# def get_all_regions_with_prices():
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("SELECT id, name FROM regions ORDER BY name")
#   regions = cursor.fetchall()
  
#   regions_with_prices = []
#   for region_id, region_name in regions:
#       cursor.execute("SELECT item_type, price FROM region_prices WHERE region_id = ?", (region_id,))
#       prices = cursor.fetchall()
#       prices_dict = {item_type: price for item_type, price in prices}
#       regions_with_prices.append({
#           "id": region_id,
#           "name": region_name,
#           "LTS_price": prices_dict.get("LTS", "N/A"),
#           "BTS_price": prices_dict.get("BTS", "N/A")
#       })
#   conn.close()
#   return regions_with_prices

# def set_region_price_db(region_id: int, item_type: str, price: float):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       INSERT OR REPLACE INTO region_prices (region_id, item_type, price)
#       VALUES (?, ?, ?)
#   ''', (region_id, item_type, price))
#   conn.commit()
#   conn.close()

# def get_region_name_by_id(region_id: int):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("SELECT name FROM regions WHERE id = ?", (region_id,))
#   name = cursor.fetchone()
#   conn.close()
#   return name[0] if name else "Noma'lum viloyat"

# def get_district_name_by_id(district_id: int):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("SELECT name FROM districts WHERE id = ?", (district_id,))
#   name = cursor.fetchone()
#   conn.close()
#   return name[0] if name else "Noma'lum tuman"

# # --- Product Management Functions ---
# def get_pending_products():
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       SELECT p.id, p.name, p.description, p.image_url, p.price, r.name, d.name, p.created_by_telegram_id, p.created_at
#       FROM products p
#       LEFT JOIN regions r ON p.region_id = r.id
#       LEFT JOIN districts d ON p.district_id = d.id
#       WHERE p.status = 'pending'
#       ORDER BY p.created_at DESC
#   ''')
#   products = cursor.fetchall()
#   conn.close()
#   return products

# def approve_product_db(product_id: int):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("UPDATE products SET status = 'approved' WHERE id = ?", (product_id,))
#   conn.commit()
#   conn.close()

# def reject_product_db(product_id: int):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("UPDATE products SET status = 'rejected' WHERE id = ?", (product_id,))
#   conn.commit()
#   conn.close()

# # --- Review Management Functions ---
# def get_pending_reviews():
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute('''
#       SELECT id, user_telegram_id, review_text, rating, created_at
#       FROM reviews
#       WHERE status = 'pending'
#       ORDER BY created_at DESC
#   ''')
#   reviews = cursor.fetchall()
#   conn.close()
#   return reviews

# def approve_review_db(review_id: int):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("UPDATE reviews SET status = 'approved' WHERE id = ?", (review_id,))
#   conn.commit()
#   conn.close()

# def reject_review_db(review_id: int):
#   conn = sqlite3.connect('users.db')
#   cursor = conn.cursor()
#   cursor.execute("UPDATE reviews SET status = 'rejected' WHERE id = ?", (review_id,))
#   conn.commit()
#   conn.close()

# # FastAPI ilovasini sozlash
# @asynccontextmanager
# async def lifespan(app: FastAPI):
#   init_db()
#   asyncio.create_task(dp.start_polling(bot))
#   yield
#   await bot.session.close()

# app = FastAPI(title="Xavfsiz Kirish Tizimi", lifespan=lifespan)
# app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
# templates = Jinja2Templates(directory="templates")

# # --- FastAPI Yo'nalishlari ---
# @app.get("/", response_class=HTMLResponse)
# async def login_page(request: Request):
#   return templates.TemplateResponse("login.html", {"request": request})

# @app.post("/login")
# async def login(request: Request, username: str = Form(...), password: str = Form(...)):
#     client_ip = get_client_ip(request)
#     user_agent = request.headers.get("user-agent", "")

#     is_blocked, blocked_until = check_user_blocked(username)
#     if is_blocked:
#         print(f"DEBUG: Foydalanuvchi {username} bloklangan.")
#         log_login_attempt(username, client_ip, False, user_agent)
#         asyncio.create_task(_send_telegram_message_task(f"🚫 <b>BLOKLANGAN FOYDALANUVCHI URINIShI</b>\n\n"
#                                                         f"👤 Foydalanuvchi: {username}\n"
#                                                         f"🌐 IP: {client_ip}\n"
#                                                         f"⏰ Bloklangan vaqt: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))
#         return templates.TemplateResponse("login.html", {"request": request,
#                                                           "error": f"Hisob {blocked_until.strftime('%Y-%m-%d %H:%M:%S')} gacha bloklangan."})

#     if authenticate_user(username, password):
#         print(f"DEBUG: Foydalanuvchi {username} muvaffaqiyatli autentifikatsiya qilindi.")
#         code = generate_verification_code()
#         save_verification_code(username, code)
#         asyncio.create_task(_send_telegram_message_task(f"🔐 <b>KIRISHNI TASDIQLASH</b>\n\n"
#                                                         f"👤 Foydalanuvchi: {username}\n"
#                                                         f"🌐 IP: {client_ip}\n"
#                                                         f"🔑 Kod: <code>{code}</code>\n"
#                                                         f"⏰ Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
        
#         request.session["username"] = username
#         request.session["authenticated"] = False
#         log_login_attempt(username, client_ip, True, user_agent)
#         update_failed_attempts(username, success=True)
#         return RedirectResponse(url="/verify", status_code=302)
#     else:
#         print(f"DEBUG: Foydalanuvchi {username} autentifikatsiyadan o'ta olmadi.")
#         log_login_attempt(username, client_ip, False, user_agent)
#         update_failed_attempts(username, success=False)
#         asyncio.create_task(_send_telegram_message_task(f"❌ <b>KIRISH MUVAFFFAQIYATSIZ</b>\n\n"
#                                                         f"👤 Foydalanuvchi: {username}\n"
#                                                         f"🌐 IP: {client_ip}\n"
#                                                         f"⏰ Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
#         return templates.TemplateResponse("login.html", {"request": request, "error": "Noto'g'ri foydalanuvchi nomi yoki parol!"})

# @app.get("/verify", response_class=HTMLResponse)
# async def verify_page(request: Request):
#   if "username" not in request.session:
#       return RedirectResponse(url="/", status_code=302)
#   return templates.TemplateResponse("verify.html", {"request": request})

# @app.post("/verify")
# async def verify(request: Request, code: str = Form(...)):
#   if "username" not in request.session:
#       return RedirectResponse(url="/", status_code=302)
  
#   username = request.session["username"]
#   client_ip = get_client_ip(request)

#   if verify_code(username, code):
#       request.session["authenticated"] = True
#       conn = sqlite3.connect('users.db')
#       cursor = conn.cursor()
#       cursor.execute("UPDATE users SET failed_verification_attempts = 0 WHERE username = ?", (username,))
#       conn.commit()
#       conn.close()

#       asyncio.create_task(_send_telegram_message_task(f"✅ <b>KIRISH MUVAFFFAQIYATLI</b>\n\n"
#                                                       f"👤 Foydalanuvchi: {username}\n"
#                                                       f"🌐 IP: {client_ip}\n"
#                                                       f"⏰ Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
#       if username == "admin" or username == "admin2": # admin2 ham admin paneliga kirishi mumkin
#           return RedirectResponse(url="/admin", status_code=302)
#       return RedirectResponse(url="/welcome", status_code=302)
#   else:
#       conn = sqlite3.connect('users.db')
#       cursor = conn.cursor()
#       cursor.execute("UPDATE users SET failed_verification_attempts = failed_verification_attempts + 1 WHERE username = ?", (username,))
#       cursor.execute("SELECT failed_verification_attempts FROM users WHERE username = ?", (username,))
#       current_failed_attempts = cursor.fetchone()[0]
#       conn.commit()

#       if current_failed_attempts >= 2:
#           blocked_until = datetime.now() + timedelta(hours=24)
#           cursor.execute('''
#               UPDATE users
#               SET is_blocked = 1, blocked_until = ?, failed_verification_attempts = 0
#               WHERE username = ?
#           ''', (blocked_until, username))
#           conn.commit()
#           conn.close()
#           asyncio.create_task(_send_telegram_message_task(f"🚨 <b>FOYDALANUVCHI BLOKLANDI (Kod xatosi)</b>\n\n"
#                                                           f"👤 Foydalanuvchi: {username}\n"
#                                                           f"⏰ Bloklangan vaqt: 24 soat\n"
#                                                           f"📅 Gacha: {blocked_until.strftime('%Y-%m-%d %H:%M:%S')}"))
#           return templates.TemplateResponse("login.html", {"request": request, "error": f"Hisobingiz noto'g'ri kodlar tufayli {blocked_until.strftime('%Y-%m-%d %H:%M:%S')} gacha bloklandi."})
      
#       conn.close()

#       asyncio.create_task(_send_telegram_message_task(f"🚫 <b>NOTO'G'RI TASDIQLASH KODI</b>\n\n"
#                                                       f"👤 Foydalanuvchi: {username}\n"
#                                                       f"🌐 IP: {client_ip}\n"
#                                                       f"🔑 Kiritilgan kod: {code}\n"
#                                                       f"⏰ Vaqt: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"))
#       return templates.TemplateResponse("verify.html", {"request": request, "error": "Noto'g'ri tasdiqlash kodi!"})

# @app.get("/welcome", response_class=HTMLResponse)
# async def welcome(request: Request):
#   if not request.session.get("authenticated"):
#       return RedirectResponse(url="/", status_code=302)
#   username = request.session.get("username")
#   return templates.TemplateResponse("welcome.html", {"request": request, "username": username})

# @app.get("/logout")
# async def logout(request: Request):
#   request.session.clear()
#   return RedirectResponse(url="/", status_code=302)

# @app.get("/health")
# async def health_check():
#   return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# # --- Admin Panel Yo'nalishlari ---
# @app.get("/admin", response_class=HTMLResponse)
# async def admin_panel(request: Request):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   users = get_all_users()
#   buttons = get_all_bot_buttons()
#   regions_with_prices = get_all_regions_with_prices()
#   pending_products = get_pending_products()
#   pending_reviews = get_pending_reviews()
  
#   return templates.TemplateResponse("admin.html", {
#       "request": request,
#       "users": users,
#       "buttons": buttons,
#       "regions": regions_with_prices,
#       "pending_products": pending_products,
#       "pending_reviews": pending_reviews
#   })

# @app.post("/admin/add_user")
# async def admin_add_user(request: Request, username: str = Form(...), password: str = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   if add_new_user(username, password):
#       asyncio.create_task(_send_telegram_message_task(f"➕ <b>YANGI FOYDALANUVCHI ADMIN TOMONIDAN YARATILDI</b>\n\n"
#                                                       f"👤 Foydalanuvchi: {username}"))
#       return RedirectResponse(url="/admin", status_code=302)
#   else:
#       users = get_all_users()
#       buttons = get_all_bot_buttons()
#       regions_with_prices = get_all_regions_with_prices()
#       pending_products = get_pending_products()
#       pending_reviews = get_pending_reviews()
#       return templates.TemplateResponse("admin.html", {
#           "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
#           "pending_products": pending_products, "pending_reviews": pending_reviews,
#           "error": "Foydalanuvchi nomi allaqachon mavjud!"
#       })

# @app.post("/admin/block_user")
# async def admin_block_user(request: Request, username: str = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   if username == "admin" or username == "admin2": # Admin foydalanuvchilarini bloklashni oldini olish
#       users = get_all_users()
#       buttons = get_all_bot_buttons()
#       regions_with_prices = get_all_regions_with_prices()
#       pending_products = get_pending_products()
#       pending_reviews = get_pending_reviews()
#       return templates.TemplateResponse("admin.html", {
#           "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
#           "pending_products": pending_products, "pending_reviews": pending_reviews,
#           "error": "Admin foydalanuvchisini bloklash mumkin emas!"
#       })

#   block_user_admin(username)
#   return RedirectResponse(url="/admin", status_code=302)

# @app.post("/admin/unblock_user")
# async def admin_unblock_user(request: Request, username: str = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   unblock_user_admin(username)
#   return RedirectResponse(url="/admin", status_code=302)

# @app.post("/admin/delete_user")
# async def admin_delete_user(request: Request, username: str = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   if username == "admin" or username == "admin2": # Admin foydalanuvchilarini o'chirishni oldini olish
#       users = get_all_users()
#       buttons = get_all_bot_buttons()
#       regions_with_prices = get_all_regions_with_prices()
#       pending_products = get_pending_products()
#       pending_reviews = get_pending_reviews()
#       return templates.TemplateResponse("admin.html", {
#           "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
#           "pending_products": pending_products, "pending_reviews": pending_reviews,
#           "error": "Admin foydalanuvchisini o'chirish mumkin emas!"
#       })

#   delete_user_admin(username)
#   return RedirectResponse(url="/admin", status_code=302)

# @app.post("/admin/add_button")
# async def admin_add_button(request: Request, text: str = Form(...), callback_data: str = Form(...), order_index: int = Form(...), is_active: bool = Form(False)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   if add_bot_button_db(text, callback_data, order_index, is_active):
#       return RedirectResponse(url="/admin", status_code=302)
#   else:
#       users = get_all_users()
#       buttons = get_all_bot_buttons()
#       regions_with_prices = get_all_regions_with_prices()
#       pending_products = get_pending_products()
#       pending_reviews = get_pending_reviews()
#       return templates.TemplateResponse("admin.html", {
#           "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
#           "pending_products": pending_products, "pending_reviews": pending_reviews,
#           "error": "Tugma callback_data allaqachon mavjud!"
#       })

# @app.post("/admin/update_button")
# async def admin_update_button(request: Request, button_id: int = Form(...), text: str = Form(...), callback_data: str = Form(...), order_index: int = Form(...), is_active: bool = Form(False)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   if update_bot_button_db(button_id, text, callback_data, order_index, is_active):
#       return RedirectResponse(url="/admin", status_code=302)
#   else:
#       users = get_all_users()
#       buttons = get_all_bot_buttons()
#       regions_with_prices = get_all_regions_with_prices()
#       pending_products = get_pending_products()
#       pending_reviews = get_pending_reviews()
#       return templates.TemplateResponse("admin.html", {
#           "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
#           "pending_products": pending_products, "pending_reviews": pending_reviews,
#           "error": "Tugma callback_data allaqachon mavjud yoki ID topilmadi!"
#       })

# @app.post("/admin/delete_button")
# async def admin_delete_button(request: Request, button_id: int = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   delete_bot_button_db(button_id)
#   return RedirectResponse(url="/admin", status_code=302)

# @app.post("/admin/set_region_price")
# async def admin_set_region_price(request: Request, region_id: int = Form(...), item_type: str = Form(...), price: float = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   set_region_price_db(region_id, item_type, price)
#   return RedirectResponse(url="/admin", status_code=302)

# @app.post("/admin/approve_product")
# async def admin_approve_product(request: Request, product_id: int = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   approve_product_db(product_id)
#   return RedirectResponse(url="/admin", status_code=302)

# @app.post("/admin/reject_product")
# async def admin_reject_product(request: Request, product_id: int = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   reject_product_db(product_id)
#   return RedirectResponse(url="/admin", status_code=302)

# @app.post("/admin/approve_review")
# async def admin_approve_review(request: Request, review_id: int = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   approve_review_db(review_id)
#   return RedirectResponse(url="/admin", status_code=302)

# @app.post("/admin/reject_review")
# async def admin_reject_review(request: Request, review_id: int = Form(...)):
#   if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
#       return RedirectResponse(url="/", status_code=302)
  
#   reject_review_db(review_id)
#   return RedirectResponse(url="/admin", status_code=302)

# # --- Asosiy ijro ---
# if __name__ == "__main__":
#   import uvicorn
#   print("FastAPI ilovasi va Telegram boti ishga tushirilmoqda...")
#   uvicorn.run(app, host="0.0.0.0", port=8000)import os

import os
import sqlite3
import hashlib
import secrets
import asyncio
import random # Для случайного выбора товаров
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
from aiogram.enums import ParseMode
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup


# Environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7953097750:AAFigo9U_h89oCuHt1jHXDZkEv_fcLzme3Q")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "5757696133") # Admin chat ID
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "your_admin_username") # Admin Telegram username
SECRET_KEY = os.getenv("SECRET_KEY", secrets.token_hex(32))
QR_CODE_IMAGE_URL = "https://hebbkx1anhila5yf.public.blob.vercel-storage.com/image-kDhb03nWcw2sODwqTpFowmkqVVitL6.png" # Общий URL адрес изменен
PRODUCT_PLACEHOLDER_IMAGE_URL = "https://picsum.photos/200/200" # Новый, надежный URL
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000") # For local development. IMPORTANT: Change this to your deployed Vercel URL (e.g., https://your-app-name.vercel.app) when deploying!

# --- Telegram Bot Setup ---
bot = Bot(token=TELEGRAM_BOT_TOKEN, parse_mode=ParseMode.HTML)
dp = Dispatcher()

# --- FSM States for Product Creation, Review Submission, and Product Browsing ---
class ProductCreation(StatesGroup):
  waiting_for_region = State()
  waiting_for_district = State()
  waiting_for_name = State()
  waiting_for_description = State()
  waiting_for_image = State()
  waiting_for_price = State()

class ReviewSubmission(StatesGroup):
  waiting_for_review_text = State()
  waiting_for_stars = State() # Новое состояние

class ProductBrowse(StatesGroup):
  waiting_for_browse_region = State()
  waiting_for_browse_district = State()
  waiting_for_product_selection = State() # NEW: Состояние выбора товара
  waiting_for_payment_confirmation = State() # Состояние подтверждения оплаты
  waiting_for_paid_amount = State() # NEW: State for user to input paid amount

# --- Database Setup ---
def init_db():
  conn = sqlite3.connect('users.db')
  cursor = conn.cursor()
  # Drop tables to ensure fresh schema on each run (for development)
  cursor.execute('DROP TABLE IF EXISTS users')
  cursor.execute('DROP TABLE IF EXISTS login_attempts')
  cursor.execute('DROP TABLE IF EXISTS verification_codes')
  cursor.execute('DROP TABLE IF EXISTS bot_button_contents') # NEW: Drop button contents table
  cursor.execute('DROP TABLE IF EXISTS bot_buttons')
  cursor.execute('DROP TABLE IF EXISTS region_prices')
  cursor.execute('DROP TABLE IF EXISTS products')
  cursor.execute('DROP TABLE IF EXISTS reviews')
  cursor.execute('DROP TABLE IF EXISTS districts') # Drop districts before regions
  cursor.execute('DROP TABLE IF EXISTS regions')
  cursor.execute('DROP TABLE IF EXISTS bot_users') # NEW: Drop bot_users table
  cursor.execute('DROP TABLE IF EXISTS pending_payments') # NEW: Drop pending_payments table

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
          image_url2 TEXT, -- NEW: Добавлено второе поле для URL изображения
          price REAL NOT NULL,
          region_id INTEGER,
          district_id INTEGER,
          status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
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
          rating INTEGER, -- Новое: Столбец для рейтинга
          status TEXT DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
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
          balance REAL DEFAULT 0.0, -- NEW: Баланс пользователя
          total_spent REAL DEFAULT 0.0, -- NEW: Общая сумма потраченных средств
          is_blocked INTEGER DEFAULT 0,
          blocked_until TIMESTAMP,
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
      )
  ''')
  cursor.execute('''
      CREATE TABLE IF NOT EXISTS pending_payments (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_telegram_id INTEGER NOT NULL,
          product_id INTEGER NOT NULL, -- NEW: Link directly to product
          amount REAL NOT NULL,       -- Expected amount for this product
          status TEXT DEFAULT 'pending', -- 'pending', 'completed', 'underpaid', 'rejected'
          created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
          FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
      )
  ''')

  # Создание стандартного пользователя-администратора (с новым паролем)
  admin_password = hashlib.sha256('newadmin123'.encode()).hexdigest() # НОВЫЙ ПАРОЛЬ АДМИНА
  cursor.execute('''
      INSERT INTO users (username, password_hash)
      VALUES (?, ?)
  ''', ('admin', admin_password))
  conn.commit()

  # Создание второго пользователя-администратора
  admin2_password = hashlib.sha256('newadmin1234'.encode()).hexdigest()
  cursor.execute('''
      INSERT INTO users (username, password_hash)
      VALUES (?, ?)
  ''', ('admin2', admin2_password))
  conn.commit()

  # Создание стандартных кнопок бота
  default_buttons = [
      ("⬆️ Пополнить счет", "top_up", 20),
      ("⭕ TRUE CORE ", "under_control", 30),
      ("💰 Работа", "work", 40),
      ("📄 Правила", "rules", 50),
      ("🆘 Поддержка", "support", 60),
      ("🛒 ВИТРИНА", "showcase", 70), # Кнопка "Витрина"
      ("ℹ️ Информация", "info", 80),
      ("⭐ Отзывы", "reviews", 90), # Кнопка "Отзывы"
      ("🤖 Подключить своего бота", "connect_bot", 100),
  ]
  for text, callback_data, order_index in default_buttons:
      cursor.execute("INSERT INTO bot_buttons (text, callback_data, order_index, is_active) VALUES (?, ?, ?, ?)",
                     (text, callback_data, order_index, 1))
  conn.commit()

  # Создание стандартного содержимого кнопок бота (NEW)
  default_button_contents = [
      ("top_up", "Для пополнения счета свяжитесь с администратором. Автоматическая система оплаты скоро будет запущена."),
      ("work", "Для получения информации о возможностях работы свяжитесь с администратором."),
      ("support", f"Если у вас есть вопросы, пожалуйста, свяжитесь с нашей службой поддержки. Для связи с администратором: @{ADMIN_USERNAME}"),
      ("rules", """Правила рассмотрения и заполнения заявки для уточнений при ненаходе: ПРЕДОСТАВЬТЕ ПО ПУНКТАМ:- Номер заказа- адрес фактической покупки ( ПЕРЕСЛАТЬ с Бота сообщением ) Внимание -  не копировать- фото с места (несколько с разных ракурсов)- описание состояния места клада по прибытию на адрес⚠️⚠️ ЕСЛИ АДРЕС НЕ СООТВЕТСТВУЕТ ФОТО/КООРДИНАТАМ ⚠️⚠️ предоставьте, пожалуйста, 4 фотографии местности с отметкой координат. Координаты на Ваших фото должны совпадать с координатами в заказе, желательно в таком же ракурсе как у курьера. Для того чтобы получить фотографии с отметкой GPS координат, можете использовать Notecam если у Вас Android, или Solocator если используете iOS. Ожидаю фотографии в пределах регламентного времени☝️☝️ВАЖНО ЗНАТЬ! РАССМОТРЕНИЕ И УТОЧНЕНИЕ ВАШЕЙ ЗАЯВКИ ДОПУСТИМО В ТЕЧЕНИИ 3 ЧАСОВ С МОМЕНТА ПОКУПКИ!‼️ВНИМАНИЕ‼️❌ПОЧЕМУ ВАМ МОЖЕТ БЫТЬ ОТКАЗАНО В РАССМОТРЕНИИ?❌1. Мы оставляем за собой право на отказ в обслуживании, УТОЧНЕНИЯХ или решении той или иной проблемы без каких-либо разъяснений.2. Претензии по ненаходам, недовесам и другим проблемам в заказах принимаются в течение 3-х  часов с момента покупки  и решаются только через ЛС!3. Передача информации о кладе третьим лицам запрещена - это лишает Вас права на помощь в поисках  в случае ненахода!4. Шантаж плохими отзывами, хамство, оскорбления сотрудников магазина и не пристойное поведение - АВТОМАТИЧЕСКИ лишает Вас права на получение помощи в поисках  в случае ненахода!5. Если фотографии с места трагедии при сообщении о проблеме были сделаны не сразу и Вы якобы поедете фотографировать место и предоставите их спустя 3-х и более часов - это лишает Вас права на помощь в поисках. Для начала предоставьте пересланным сообщением сам адрес, который Вам выдан ботом! Затем фото, сделанные Вами лично!ПЕРЕЗАКЛАД НА ПЕРЕЗАКЛАД НЕ ВЫДАЁТСЯ    """),
      ("connect_bot", "Вы не можете создавать личных ботов, так как не совершено необходимое количество покупок.\nВсего покупок: 0\nНеобходимое количество покупок для создания бота: 1"), # Default message, will be updated dynamically
      ("under_control", "Этот раздел находится в разработке. Дополнительная информация будет предоставлена в ближайшее время."),
      ("info", "В этом разделе содержится общая информация о нашем магазине. Для дополнительных вопросов используйте кнопку 'Поддержка'."),
  ]
  for callback_data, content in default_button_contents:
      cursor.execute("INSERT INTO bot_button_contents (callback_data, content) VALUES (?, ?)", (callback_data, content))
  conn.commit()

  # Добавление регионов Узбекистана
  uzbek_regions = [
      "Andijon viloyati", "Buxoro viloyati", "Farg'ona viloyati", "Jizzax viloyati",
      "Xorazm viloyati", "Namangan viloyati", "Navoiy viloyati",
      "Qashqadaryo viloyati", "Samarqand viloyati", "Sirdaryo viloyati", "Surxondaryo viloyati",
      "Toshkent viloyati", "Qoraqalpog'iston Respublikasi"
  ]
  for region_name in uzbek_regions:
      cursor.execute('INSERT OR IGNORE INTO regions (name) VALUES (?)', (region_name,))
  conn.commit()

  # Добавление некоторых районов
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
          # Если для области нет конкретного списка районов, добавить стандартный район
          cursor.execute('INSERT OR IGNORE INTO districts (region_id, name) VALUES (?, ?)', (region_id, f"{region_name} Центральный район"))
  conn.commit()

  # Добавление тестовых товаров (в одобренном статусе)
  tashkent_region_id = cursor.execute("SELECT id FROM regions WHERE name = 'Toshkent viloyati'").fetchone()[0]
  tashkent_city_district_id = cursor.execute("SELECT id FROM districts WHERE name = 'Toshkent shahri' AND region_id = ?", (tashkent_region_id,)).fetchone()[0]
  bektemir_district_id = cursor.execute("SELECT id FROM districts WHERE name = 'Bekobod tumani' AND region_id = ?", (tashkent_region_id,)).fetchone()[0] # Bektemir o'rniga Bekobod tumani
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

# --- Telegram функции ---
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
  welcome_message = """🎉 Добро пожаловать в наш магазин! 🛍️🌟Здесь вы найдете широкий ассортимент товаров для всех случаев жизни!Чтобы начать покупки, необходимо сначала пополнить ваш счет. После пополнения вы сможете использовать баланс для покупки любого товара, который будет выдан вам автоматически. 🎁💳Пополнение счета простое и безопасное. Все транзакции проходят в защищенном режиме, чтобы вы могли чувствовать себя уверенно и комфортно.🤔 Если у вас возникнут вопросы, не стесняйтесь обращаться к нашим операторам. Мы здесь, чтобы помочь вам! 🙋‍♂️🙋🚀 Готовы начать? Приступим к покупкам и наслаждайтесь удобством и разнообразием нашего ассортимента!💬 Ждем ваших заказов и желаем приятных покупок! 🎉Кол-во сделок: 450 шт."""
  await message.answer(welcome_message, reply_markup=get_main_menu_keyboard())

# --- Функционал кнопки "ВИТРИНА" (Showcase) (Теперь включает логику "Купить") ---
@dp.callback_query(lambda c: c.data == "showcase")
async def start_showcase_browse(call: types.CallbackQuery, state: FSMContext):
  await call.answer("Товары в витрине загружаются...") # Ответить на callback немедленно
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
  await call.answer("Область выбрана...") # Ответить на callback немедленно
  region_id = int(call.data.split("_")[2])
  await state.update_data(browse_region_id=region_id)
  conn = sqlite3.connect('users.db')
  cursor = conn.cursor()
  # NEW: Select only districts that have approved products in this region
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
      # Example: 1) Гагарин 33% ТГК 1gr - 60 $
      # Assuming price is in USD for display based on image, but stored as REAL.
      # If price is in UZS, change '$' to 'сум'
      response_text += f"{i+1}) {name} - {price} $\n" \
                       f"{district_name}\n\n" # Removed /buy_ command from text to shorten message
      product_buttons.append([InlineKeyboardButton(text=f"Купить {name} ({price}$)", callback_data=f"buy_product_{product_id}")])

  product_buttons.append([InlineKeyboardButton(text="⬅️ Вернуться в главное меню", callback_data="main_menu")])
  products_keyboard = InlineKeyboardMarkup(inline_keyboard=product_buttons)
  await state.update_data(selected_district_id=district_id) # Store district_id for later use
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

    # Add pending payment with product_id
    payment_id = add_pending_payment_db(user_telegram_id, product_id, product_price)

    # Send QR code and ask user to input the amount they paid
    await call.message.answer_photo(
        photo=types.URLInputFile(QR_CODE_IMAGE_URL),
        caption=f"Вы выбрали <b>{product_name}</b> ({product_price} сум).\n"
                f"Используйте следующий QR-код для оплаты:\n\n"
                f"Ссылка на QR-код: `{QR_CODE_IMAGE_URL}`\n\n"
                f"<b>Ваш ID платежа: {payment_id}</b>\n"
                f"Пожалуйста, переведите <b>{product_price} сум</b>.\n\n"
                f"После оплаты, отправьте мне точную сумму, которую вы перевели (например: 100000).",
        parse_mode=ParseMode.HTML,
        reply_markup=get_back_to_main_menu_keyboard() # Allow user to go back
    )

    await state.update_data(current_payment_id=payment_id, expected_amount=product_price)
    await state.set_state(ProductBrowse.waiting_for_paid_amount)

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
        paid_amount = float(message.text.replace(',', '.')) # Allow comma as decimal separator
        if paid_amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("Пожалуйста, введите корректную сумму (например: 100000).", reply_markup=get_back_to_main_menu_keyboard())
        return

    # Retrieve product details for delivery
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT p.name, p.description, p.image_url, p.image_url2, p.price FROM products p JOIN pending_payments pp ON p.id = pp.product_id WHERE pp.id = ?", (payment_id,))
    product_info = cursor.fetchone()
    conn.close()

    if not product_info:
        await message.answer("Извините, товар для вашего платежа не найден. Свяжитесь с администратором.", reply_markup=get_main_menu_keyboard())
        await state.clear()
        return

    product_name, product_description, image_url, image_url2, product_price = product_info

    if paid_amount >= expected_amount:
        # Payment successful or overpaid
        update_pending_payment_status_db(payment_id, 'completed')

        # Handle overpayment
        excess_amount = paid_amount - expected_amount
        if excess_amount > 0:
            update_user_balance_and_spent(user_telegram_id, excess_amount) # Add to balance
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
        # Update user purchases and total spent
        increment_user_purchases(user_telegram_id)
        update_user_balance_and_spent(user_telegram_id, -product_price) # Deduct product price from balance, add to total spent

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
            media_group.append(InputMediaPhoto(media=types.URLInputFile(final_image_url_for_telegram), caption=message_text, parse_mode=ParseMode.HTML))
        if final_image_url2_for_telegram:
            if not media_group:
                media_group.append(InputMediaPhoto(media=types.URLInputFile(final_image_url2_for_telegram), caption=message_text, parse_mode=ParseMode.HTML))
            else:
                media_group.append(InputMediaPhoto(media=types.URLInputFile(final_image_url2_for_telegram)))

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

    await state.clear() # Clear state after processing payment

@dp.callback_query(F.data.startswith("admin_approve_payment_"))
async def admin_approve_payment(call: types.CallbackQuery):
    # This function is now only for admin to manually approve payments if needed,
    # not for automatic product delivery.
    if str(call.from_user.id) != ADMIN_CHAT_ID:
        await call.answer("У вас нет прав для выполнения этого действия!")
        return
    payment_id = int(call.data.split("_")[3])
    payment_data = get_pending_payment_db(payment_id)
    if not payment_data or payment_data[4] != 'pending': # Check status
        await call.answer("Этот запрос на оплату не найден или уже обработан.")
        return
    
    update_pending_payment_status_db(payment_id, 'completed') # Mark as completed by admin
    await call.answer(f"Платеж ID: {payment_id} вручную подтвержден.")
    await call.message.edit_text(f"✅ Платеж ID: {payment_id} вручную подтвержден.")
    asyncio.create_task(_send_telegram_message_task(f"✅ <b>ПЛАТЕЖ ВРУЧНУЮ ПОДТВЕРЖДЕН АДМИНИСТРАТОРОМ</b>\n\n"
                                                    f"ID платежа: {payment_id}\n"
                                                    f"Пользователь: {payment_data[1]}\n"
                                                    f"Товар ID: {payment_data[2]}\n"
                                                    f"Сумма: {payment_data[3]} сум"))


@dp.callback_query(F.data.startswith("admin_reject_payment_"))
async def admin_reject_payment(call: types.CallbackQuery):
    if str(call.from_user.id) != ADMIN_CHAT_ID:
        await call.answer("У вас нет прав для выполнения этого действия!")
        return
    payment_id = int(call.data.split("_")[3])
    payment_data = get_pending_payment_db(payment_id)
    if not payment_data or payment_data[4] != 'pending':
        await call.answer("Этот запрос на оплату не найден или уже обработан.")
        return
    user_telegram_id = payment_data[1]
    update_pending_payment_status_db(payment_id, 'rejected')
    block_bot_user_by_telegram_id(user_telegram_id, duration_days=365)
    try:
        await bot.send_message(chat_id=user_telegram_id, text="Извините, ваша оплата отклонена, и ваш аккаунт заблокирован. Свяжитесь с администратором.")
        await call.answer("Оплата отклонена, пользователь заблокирован.")
        await call.message.edit_text(f"❌ Оплата ID: {payment_id} отклонена, пользователь заблокирован.")
    except Exception as e:
        await call.answer(f"Ошибка при блокировке пользователя или отправке сообщения: {e}")
        await call.message.edit_text(f"❌ Оплата ID: {payment_id} отклонена, но произошла ошибка при блокировке пользователя/отправке сообщения: {e}")
        print(f"Error blocking user {user_telegram_id} or sending message: {e}")

# --- "Reviews" button functionality ---
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

# --- Review submission process (after purchase) ---
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
async def handle_other_buttons(call: types.CallbackQuery, state: FSMContext): # Pass state here
    await call.answer("Команда отправляется...")
    print(f"Пользователь {call.from_user.username} ({call.from_user.id}) нажал кнопку: {call.data}")

    # Check for specific handlers first
    if call.data == "main_menu":
        await back_to_main_menu_handler(call, state) # Pass state
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
        await start_showcase_browse(call, state) # Pass state
        return
    elif call.data == "start_purchase_review":
        await start_review_submission_after_purchase(call, state) # Pass state
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
        rules_text = """Правила рассмотрения и заполнения заявки для уточнений при ненаходе: ПРЕДОСТАВЬТЕ ПО ПУНКТАМ:- Номер заказа- адрес фактической покупки ( ПЕРЕСЛАТЬ с Бота сообщением ) Внимание -  не копировать- фото с места (несколько с разных ракурсов)- описание состояния места клада по прибытию на адрес⚠️⚠️ ЕСЛИ АДРЕС НЕ СООТВЕТСТВУЕТ ФОТО/КООРДИНАТАМ ⚠️⚠️ предоставьте, пожалуйста, 4 фотографии местности с отметкой координат. Координаты на Ваших фото должны совпадать с координатами в заказе, желательно в таком же ракурсе как у курьера. Для того чтобы получить фотографии с отметкой GPS координат, можете использовать Notecam если у Вас Android, или Solocator если используете iOS. Ожидаю фотографии в пределах регламентного времени☝️☝️ВАЖНО ЗНАТЬ! РАССМОТРЕНИЕ И УТОЧНЕНИЕ ВАШЕЙ ЗАЯВКИ ДОПУСТИМО В ТЕЧЕНИИ 3 ЧАСОВ С МОМЕНТА ПОКУПКИ!‼️ВНИМАНИЕ‼️❌ПОЧЕМУ ВАМ МОЖЕТ БЫТЬ ОТКАЗАНО В РАССМОТРЕНИИ?❌1. Мы оставляем за собой право на отказ в обслуживании, УТОЧНЕНИЯХ или решении той или иной проблемы без каких-либо разъяснений.2. Претензии по ненаходам, недовесам и другим проблемам в заказах принимаются в течение 3-х  часов с момента покупки  и решаются только через ЛС!3. Передача информации о кладе третьим лицам запрещена - это лишает Вас права на помощь в поисках  в случае ненахода!4. Шантаж плохими отзывами, хамство, оскорбления сотрудников магазина и не пристойное поведение - АВТОМАТИЧЕСКИ лишает Вас права на получение помощи в поисках  в случае ненахода!5. Если фотографии с места трагедии при сообщении о проблеме были сделаны не сразу и Вы якобы поедете фотографировать место и предоставите их спустя 3-х и более часов - это лишает Вас права на помощь в поисках. Для начала предоставьте пересланным сообщением сам адрес, который Вам выдан ботом! Затем фото, сделанные Вами лично!ПЕРЕЗАКЛАД НА ПЕРЕЗАКЛАД НЕ ВЫДАЁТСЯ    """
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

# --- Общие функции ---
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
          else: # Blocked time expired, unblock automatically
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
          blocked_until = datetime.now() + timedelta(days=365) # Блокировка на 1 год
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

# --- Функции управления пользователями бота (NEW) ---
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
    return result if result else (0.0, 0.0) # Если пользователь не найден, вернуть 0.0

def block_bot_user_by_telegram_id(user_telegram_id: int, duration_days: int = 365):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    blocked_until = datetime.now() + timedelta(days=duration_days)
    cursor.execute('''
        INSERT OR IGNORE INTO bot_users (telegram_id) VALUES (?)
    ''', (user_telegram_id,)) # Обеспечить существование пользователя
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
            else: # Blocked time expired, unblock automatically
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

# --- Функции ожидающих платежей (NEW) ---
def add_pending_payment_db(user_telegram_id: int, product_id: int, amount: float): # NEW: product_id instead of region/district/item_type
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

# --- Функции базы данных админ-панели ---
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
  blocked_until = datetime.now() + timedelta(days=365) # Блокировка на 1 год
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

# --- Функции управления кнопками бота ---
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

# --- Функции управления содержимым кнопок бота (NEW) ---
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

# --- Функции управления ценами регионов ---
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

# --- Функции управления товарами ---
def get_pending_products():
  conn = sqlite3.connect('users.db')
  cursor = conn.cursor()
  cursor.execute('''
      SELECT p.id, p.name, p.description, p.image_url, p.price, p.region_id, p.district_id, r.name, d.name, p.created_by_telegram_id, p.created_at, p.image_url2 -- NEW: image_url2 добавлен
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

def update_product_db(product_id: int, name: str, description: str, price: float, region_id: int, district_id: int, image_url1: str = None, image_url2: str = None): # NEW: image_url1, image_url2
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    # Обновляем оба URL, если они предоставлены. Если нет, оставляем текущее значение.
    # Это упрощает логику, так как FastAPI Form(None) по умолчанию будет None, если файл не загружен.
    cursor.execute('''
        UPDATE products
        SET name = ?, description = ?, price = ?, region_id = ?, district_id = ?, image_url = ?, image_url2 = ?
        WHERE id = ?
    ''', (name, description, price, region_id, district_id, image_url1, image_url2, product_id))
    conn.commit()
    conn.close()

# --- Функции управления отзывами ---
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

# Новые функции: Получение всех областей и районов
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

# NEW: Функции управления регионами и районами
def add_region_db(name: str):
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO regions (name) VALUES (?)", (name,))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False # Region with this name already exists
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
        return False # District with this name already exists in this region
    finally:
        conn.close()

# Настройка FastAPI приложения
@asynccontextmanager
async def lifespan(app: FastAPI):
  init_db()
  asyncio.create_task(dp.start_polling(bot))
  yield
  await bot.session.close()

app = FastAPI(title="Система безопасного входа", lifespan=lifespan)
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)
templates = Jinja2Templates(directory="templates")

# Обслуживание статических файлов
app.mount("/public", StaticFiles(directory="public"), name="public")

# --- Маршруты FastAPI ---
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
      if username == "admin" or username == "admin2": # admin2 также может войти в админ-панель
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
          blocked_until = datetime.now() + timedelta(days=365) # Блокировка на 1 год
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

# --- Маршруты админ-панели ---
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
  bot_button_contents = get_all_button_contents() # NEW

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
      "all_regions": all_regions_list, # Новое: для формы добавления товара
      "all_districts": all_districts_list, # Новое: для формы добавления товара
      "region_names_map": region_names_map, # Новое: для отображения названий районов
      "bot_button_contents": bot_button_contents, # NEW
      "regions_with_districts": regions_with_districts # NEW
  })

@app.post("/admin/add_user")
async def admin_add_user(request: Request, username: str = Form(...), password: str = Form(...)):
  if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
      return RedirectResponse(url="/", status_code=302)
  if add_new_user(username, password):
      asyncio.create_task(_send_telegram_message_task(f"➕ <b>НОВЫЙ ПОЛЬЗОВАТЕЛЬ СОЗДАН АДМИНИСТРАТОРОМ</b>\n\n"
                                                      f"👤 Пользователь: {username}"))
      return RedirectResponse(url="/admin", status_code=302)
  else:
      users = get_all_users()
      buttons = get_all_bot_buttons()
      regions_with_prices = get_all_regions_with_prices()
      pending_products = get_pending_products()
      pending_reviews = get_pending_reviews()
      all_regions_list = get_all_regions()
      all_districts_list = get_all_districts()
      region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
      bot_button_contents = get_all_button_contents() # NEW
      regions_with_districts = [] # Re-fetch for error case
      for region_id, region_name in all_regions_list:
          districts_for_region = [d for d in all_districts_list if d[2] == region_id]
          regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})

      return templates.TemplateResponse("admin.html", {
          "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
          "pending_products": pending_products, "pending_reviews": pending_reviews,
          "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
          "bot_button_contents": bot_button_contents, # NEW
          "regions_with_districts": regions_with_districts, # NEW
          "error": "Имя пользователя уже существует!"
      })

@app.post("/admin/block_user")
async def admin_block_user(request: Request, username: str = Form(...)):
  if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
      return RedirectResponse(url="/", status_code=302)
  if username == "admin" or username == "admin2": # Предотвратить блокировку пользователей-администраторов
      users = get_all_users()
      buttons = get_all_bot_buttons()
      regions_with_prices = get_all_regions_with_prices()
      pending_products = get_pending_products()
      pending_reviews = get_pending_reviews()
      all_regions_list = get_all_regions()
      all_districts_list = get_all_districts()
      region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
      bot_button_contents = get_all_button_contents() # NEW
      regions_with_districts = [] # Re-fetch for error case
      for region_id, region_name in all_regions_list:
          districts_for_region = [d for d in all_districts_list if d[2] == region_id]
          regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})
      return templates.TemplateResponse("admin.html", {
          "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
          "pending_products": pending_products, "pending_reviews": pending_reviews,
          "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
          "bot_button_contents": bot_button_contents, # NEW
          "regions_with_districts": regions_with_districts, # NEW
          "error": "Невозможно заблокировать пользователя-администратора!"
      })
  block_user_admin(username)
  return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/unblock_user")
async def admin_unblock_user(request: Request, username: str = Form(...)):
  if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
      return RedirectResponse(url="/", status_code=302)
  unblock_user_admin(username)
  return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/delete_user")
async def admin_delete_user(request: Request, username: str = Form(...)):
  if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
      return RedirectResponse(url="/", status_code=302)
  if username == "admin" or username == "admin2": # Предотвратить удаление пользователей-администраторов
      users = get_all_users()
      buttons = get_all_bot_buttons()
      regions_with_prices = get_all_regions_with_prices()
      pending_products = get_pending_products()
      pending_reviews = get_pending_reviews()
      all_regions_list = get_all_regions()
      all_districts_list = get_all_districts()
      region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
      bot_button_contents = get_all_button_contents() # NEW
      regions_with_districts = [] # Re-fetch for error case
      for region_id, region_name in all_regions_list:
          districts_for_region = [d for d in all_districts_list if d[2] == region_id]
          regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})
      return templates.TemplateResponse("admin.html", {
          "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
          "pending_products": pending_products, "pending_reviews": pending_reviews,
          "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
          "bot_button_contents": bot_button_contents, # NEW
          "regions_with_districts": regions_with_districts, # NEW
          "error": "Невозможно удалить пользователя-администратора!"
      })
  delete_user_admin(username)
  return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/add_button")
async def admin_add_button(request: Request, text: str = Form(...), callback_data: str = Form(...), order_index: int = Form(...), is_active: bool = Form(False)):
  if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
      return RedirectResponse(url="/", status_code=302)
  if add_bot_button_db(text, callback_data, order_index, is_active):
      return RedirectResponse(url="/admin", status_code=302)
  else:
      users = get_all_users()
      buttons = get_all_bot_buttons()
      regions_with_prices = get_all_regions_with_prices()
      pending_products = get_pending_products()
      pending_reviews = get_pending_reviews()
      all_regions_list = get_all_regions()
      all_districts_list = get_all_districts()
      region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
      bot_button_contents = get_all_button_contents() # NEW
      regions_with_districts = [] # Re-fetch for error case
      for region_id, region_name in all_regions_list:
          districts_for_region = [d for d in all_districts_list if d[2] == region_id]
          regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})
      return templates.TemplateResponse("admin.html", {
          "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
          "pending_products": pending_products, "pending_reviews": pending_reviews,
          "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
          "bot_button_contents": bot_button_contents, # NEW
          "regions_with_districts": regions_with_districts, # NEW
          "error": "Callback_data кнопки уже существует!"
      })

@app.post("/admin/update_button")
async def admin_update_button(request: Request, button_id: int = Form(...), text: str = Form(...), callback_data: str = Form(...), order_index: int = Form(...), is_active: bool = Form(False)):
  if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
      return RedirectResponse(url="/", status_code=302)
  if update_bot_button_db(button_id, text, callback_data, order_index, is_active):
      return RedirectResponse(url="/admin", status_code=302)
  else:
      users = get_all_users()
      buttons = get_all_bot_buttons()
      regions_with_prices = get_all_regions_with_prices()
      pending_products = get_pending_products()
      pending_reviews = get_pending_reviews()
      all_regions_list = get_all_regions()
      all_districts_list = get_all_districts()
      region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
      bot_button_contents = get_all_button_contents() # NEW
      regions_with_districts = [] # Re-fetch for error case
      for region_id, region_name in all_regions_list:
          districts_for_region = [d for d in all_districts_list if d[2] == region_id]
          regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})
      return templates.TemplateResponse("admin.html", {
          "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
          "pending_products": pending_products, "pending_reviews": pending_reviews,
          "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
          "bot_button_contents": bot_button_contents, # NEW
          "regions_with_districts": regions_with_districts, # NEW
          "error": "Callback_data кнопки уже существует или ID не найден!"
      })

@app.post("/admin/delete_button")
async def admin_delete_button(request: Request, button_id: int = Form(...)):
  if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
      return RedirectResponse(url="/", status_code=302)
  delete_bot_button_db(button_id)
  return RedirectResponse(url="/admin", status_code=302)

# NEW: Endpoints for managing bot button content
@app.post("/admin/add_or_update_button_content")
async def admin_add_or_update_button_content(request: Request, callback_data: str = Form(...), content: str = Form(...), content_id: int = Form(None)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)

    if content_id:
        conn = sqlite3.connect('users.db')
        cursor = conn.cursor()
        try:
            cursor.execute("UPDATE bot_button_contents SET content = ? WHERE id = ?", (content, content_id))
            conn.commit()
            success = True
        except Exception as e:
            print(f"Error updating button content by ID: {e}")
            success = False
        finally:
            conn.close()
    else:
        success = add_or_update_button_content_db(callback_data, content)

    if success:
        asyncio.create_task(_send_telegram_message_task(f"📝 <b>СОДЕРЖИМОЕ КНОПКИ БОТА ОБНОВЛЕНО/ДОБАВЛЕНО</b>\n\n"
                                                        f"Callback Data: {callback_data}\n"
                                                        f"Содержимое (первые 100 символов): {content[:100]}..."))
        return RedirectResponse(url="/admin", status_code=302)
    else:
        users = get_all_users()
        buttons = get_all_bot_buttons()
        regions_with_prices = get_all_regions_with_prices()
        pending_products = get_pending_products()
        pending_reviews = get_pending_reviews()
        all_regions_list = get_all_regions()
        all_districts_list = get_all_districts()
        region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
        bot_button_contents = get_all_button_contents()
        regions_with_districts = []
        for region_id, region_name in all_regions_list:
            districts_for_region = [d for d in all_districts_list if d[2] == region_id]
            regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})
        return templates.TemplateResponse("admin.html", {
            "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
            "pending_products": pending_products, "pending_reviews": pending_reviews,
            "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
            "bot_button_contents": bot_button_contents,
            "regions_with_districts": regions_with_districts,
            "error": "Ошибка при сохранении содержимого кнопки!"
        })

@app.post("/admin/set_region_price")
async def admin_set_region_price(request: Request, region_id: int = Form(...), item_type: str = Form(...), price: float = Form(...)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    set_region_price_db(region_id, item_type, price)
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/approve_product")
async def admin_approve_product(request: Request, product_id: int = Form(...)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    approve_product_db(product_id)
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/reject_product")
async def admin_reject_product(request: Request, product_id: int = Form(...)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    reject_product_db(product_id)
    return RedirectResponse(url="/admin", status_code=302)

# New: Endpoint for adding product
@app.post("/admin/add_product")
async def admin_add_product(
    request: Request,
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    region_id: int = Form(...),
    district_id: int = Form(...),
    image1: UploadFile = File(None),
    image2: UploadFile = File(None)
):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)

    image_url1 = None
    if image1 and image1.filename:
        upload_dir = "public/images"
        os.makedirs(upload_dir, exist_ok=True)
        file_extension = os.path.splitext(image1.filename)[1]
        unique_filename = f"{secrets.token_hex(8)}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(await image1.read())
            image_url1 = f"/public/images/{unique_filename}"
        except Exception as e:
            print(f"Error saving image 1: {e}")
            image_url1 = None

    image_url2 = None
    if image2 and image2.filename:
        upload_dir = "public/images"
        os.makedirs(upload_dir, exist_ok=True)
        file_extension = os.path.splitext(image2.filename)[1]
        unique_filename = f"{secrets.token_hex(8)}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(await image2.read())
            image_url2 = f"/public/images/{unique_filename}"
        except Exception as e:
            print(f"Error saving image 2: {e}")
            image_url2 = None

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    try:
        created_by_telegram_id = 0
        cursor.execute('''
            INSERT INTO products (name, description, image_url, image_url2, price, region_id, district_id, status, created_by_telegram_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (name, description, image_url1, image_url2, price, region_id, district_id, 'approved', created_by_telegram_id))
        conn.commit()
        asyncio.create_task(_send_telegram_message_task(f"📦 <b>НОВЫЙ ТОВАР ДОБАВЛЕН (Админ-панель)</b>\n\n"
                                                        f"Название: {name}\n"
                                                        f"Описание: {description}\n"
                                                        f"Цена: {price} сум\n"
                                                        f"ID области: {region_id}\n"
                                                        f"ID района: {district_id}\n"
                                                        f"URL изображения 1: {image_url1 if image_url1 else 'Недоступно'}\n"
                                                        f"URL изображения 2: {image_url2 if image_url2 else 'Недоступно'}\n\n"
                                                        f"Статус: Одобрено"))
        return RedirectResponse(url="/admin", status_code=302)
    except Exception as e:
        print(f"Error adding product: {e}")
        users = get_all_users()
        buttons = get_all_bot_buttons()
        regions_with_prices = get_all_regions_with_prices()
        pending_products = get_pending_products()
        pending_reviews = get_pending_reviews()
        all_regions_list = get_all_regions()
        all_districts_list = get_all_districts()
        region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
        bot_button_contents = get_all_button_contents()
        regions_with_districts = []
        for region_id, region_name in all_regions_list:
            districts_for_region = [d for d in all_districts_list if d[2] == region_id]
            regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})
        return templates.TemplateResponse("admin.html", {
            "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
            "pending_products": pending_products, "pending_reviews": pending_reviews,
            "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
            "bot_button_contents": bot_button_contents,
            "regions_with_districts": regions_with_districts,
            "error": f"Error adding product: {e}"
        })
    finally:
        conn.close()

@app.post("/admin/update_product")
async def admin_update_product(
    request: Request,
    product_id: int = Form(...),
    name: str = Form(...),
    description: str = Form(...),
    price: float = Form(...),
    region_id: int = Form(...),
    district_id: int = Form(...),
    image1: UploadFile = File(None),
    image2: UploadFile = File(None)
):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)

    image_url1 = None
    if image1 and image1.filename:
        upload_dir = "public/images"
        os.makedirs(upload_dir, exist_ok=True)
        file_extension = os.path.splitext(image1.filename)[1]
        unique_filename = f"{secrets.token_hex(8)}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(await image1.read())
            image_url1 = f"/public/images/{unique_filename}"
        except Exception as e:
            print(f"Error saving image 1: {e}")
            image_url1 = None

    image_url2 = None
    if image2 and image2.filename:
        upload_dir = "public/images"
        os.makedirs(upload_dir, exist_ok=True)
        file_extension = os.path.splitext(image2.filename)[1]
        unique_filename = f"{secrets.token_hex(8)}{file_extension}"
        file_path = os.path.join(upload_dir, unique_filename)
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(await image2.read())
            image_url2 = f"/public/images/{unique_filename}"
        except Exception as e:
            print(f"Error saving image 2: {e}")
            image_url2 = None

    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    cursor.execute("SELECT image_url, image_url2 FROM products WHERE id = ?", (product_id,))
    current_image_urls = cursor.fetchone()
    conn.close()

    if current_image_urls:
        if image_url1 is None:
            image_url1 = current_image_urls[0]
        if image_url2 is None:
            image_url2 = current_image_urls[1]

    update_product_db(product_id, name, description, price, region_id, district_id, image_url1, image_url2)
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/approve_review")
async def admin_approve_review(request: Request, review_id: int = Form(...)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    approve_review_db(review_id)
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/reject_review")
async def admin_reject_review(request: Request, review_id: int = Form(...)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    reject_review_db(review_id)
    return RedirectResponse(url="/admin", status_code=302)

@app.post("/admin/update_review")
async def admin_update_review(request: Request, review_id: int = Form(...), review_text: str = Form(...), rating: int = Form(...)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    update_review_db(review_id, review_text, rating)
    return RedirectResponse(url="/admin", status_code=302)

# NEW: Endpoints for managing regions and districts
@app.post("/admin/add_region")
async def admin_add_region(request: Request, region_name: str = Form(...)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    if add_region_db(region_name):
        asyncio.create_task(_send_telegram_message_task(f"➕ <b>НОВАЯ ОБЛАСТЬ ДОБАВЛЕНА (Админ-панель)</b>\n\n"
                                                        f"Название: {region_name}"))
        return RedirectResponse(url="/admin", status_code=302)
    else:
        users = get_all_users()
        buttons = get_all_bot_buttons()
        regions_with_prices = get_all_regions_with_prices()
        pending_products = get_pending_products()
        pending_reviews = get_pending_reviews()
        all_regions_list = get_all_regions()
        all_districts_list = get_all_districts()
        region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
        bot_button_contents = get_all_button_contents()
        regions_with_districts = []
        for region_id, region_name in all_regions_list:
            districts_for_region = [d for d in all_districts_list if d[2] == region_id]
            regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})
        return templates.TemplateResponse("admin.html", {
            "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
            "pending_products": pending_products, "pending_reviews": pending_reviews,
            "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
            "bot_button_contents": bot_button_contents,
            "regions_with_districts": regions_with_districts,
            "error": "Название области уже существует!"
        })

@app.post("/admin/add_district")
async def admin_add_district(request: Request, region_id: int = Form(...), district_name: str = Form(...)):
    if not request.session.get("authenticated") or (request.session.get("username") != "admin" and request.session.get("username") != "admin2"):
        return RedirectResponse(url="/", status_code=302)
    if add_district_db(region_id, district_name):
        region_name = get_region_name_by_id(region_id)
        asyncio.create_task(_send_telegram_message_task(f"➕ <b>НОВЫЙ РАЙОН ДОБАВЛЕН (Админ-панель)</b>\n\n"
                                                        f"Название: {district_name}\n"
                                                        f"Область: {region_name}"))
        return RedirectResponse(url="/admin", status_code=302)
    else:
        users = get_all_users()
        buttons = get_all_bot_buttons()
        regions_with_prices = get_all_regions_with_prices()
        pending_products = get_pending_products()
        pending_reviews = get_pending_reviews()
        all_regions_list = get_all_regions()
        all_districts_list = get_all_districts()
        region_names_map = {region_id: region_name for region_id, region_name in all_regions_list}
        bot_button_contents = get_all_button_contents()
        regions_with_districts = []
        for region_id, region_name in all_regions_list:
            districts_for_region = [d for d in all_districts_list if d[2] == region_id]
            regions_with_districts.append({"id": region_id, "name": region_name, "districts": districts_for_region})
        return templates.TemplateResponse("admin.html", {
            "request": request, "users": users, "buttons": buttons, "regions": regions_with_prices,
            "pending_products": pending_products, "pending_reviews": pending_reviews,
            "all_regions": all_regions_list, "all_districts": all_districts_list, "region_names_map": region_names_map,
            "bot_button_contents": bot_button_contents,
            "regions_with_districts": regions_with_districts,
            "error": "Название района уже существует в этой области!"
        })


# --- Основное выполнение ---
if __name__ == "__main__":
  import uvicorn
  print("FastAPI application and Telegram bot are starting...")
  uvicorn.run(app, host="0.0.0.0", port=8000)
