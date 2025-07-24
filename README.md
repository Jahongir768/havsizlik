# 🔐 Secure Login System

FastAPI va Telegram bot integratsiyasi bilan xavfsiz login tizimi.

## ✨ Xususiyatlar

- **FastAPI** web framework
- **Telegram Bot** orqali 2FA
- **SQLite** database
- **Avtomatik bloklash** (3 marta noto'g'ri urinish = 24 soat blok)
- **Real-time monitoring**
- **Responsive UI**

## 🚀 O'rnatish

### Local Development
\`\`\`bash
# Dependencies o'rnatish
pip install -r requirements.txt

# Environment variables sozlash
cp .env.example .env
# .env faylini tahrirlang

# Ishga tushirish
python app.py
\`\`\`

### Vercel Deployment
\`\`\`bash
vercel --prod
\`\`\`

Environment variables qo'shish:
- `TELEGRAM_BOT_TOKEN`
- `ADMIN_CHAT_ID`
- `SECRET_KEY`

## 🔧 Konfiguratsiya

### Telegram Bot
1. @BotFather ga `/newbot` yuboring
2. Bot token oling
3. @userinfobot dan chat ID oling

### Default Login
- **Username:** admin
- **Password:** admin123

## 🛡️ Xavfsizlik

- 3 marta noto'g'ri urinish = 24 soat blok
- Barcha urinishlar loglanadi
- IP tracking
- Session xavfsizligi
- Real-time Telegram alerts

## 📊 API Endpoints

- `GET /` - Login sahifasi
- `POST /login` - Login form
- `GET /verify` - Verification sahifasi
- `POST /verify` - Verification form
- `GET /welcome` - Welcome sahifasi
- `GET /logout` - Logout
- `GET /health` - Health check

## 📄 License

MIT License
# Havsizlik
# havsizlik
