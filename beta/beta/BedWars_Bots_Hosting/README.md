# 🚀 BedWars Marketplace Discord Auto-Notifier Bots (FunPay & Playerok)

Полностью готов к деплою на хостинг (VPS, Railway, Render, Docker, Heroku или Windows Server).

## 📁 Структура проекта
```text
BedWars_Bots_Hosting/
├── .env                       # Конфигурация Webhook для хостинга
├── START_ALL_BOTS.bat          # Главный запускной батник (для Windows)
├── requirements.txt           # Зависимости (Zero external dependencies)
├── FunPay_BedWars_Bot/        # Отдельный бот для FunPay (#401, #402)
│   ├── main.py
│   ├── config.json
│   └── start.bat
└── Playerok_BedWars_Bot/      # Отдельный бот для Playerok (Roblox Accounts BedWars)
    ├── main.py
    ├── config.json
    └── start.bat
```

## ⚙️ Настройка `.env` (Переменные окружения)
Оба бота автоматически считывают настройки из файла `.env`:
```env
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
DISCORD_PING=@everyone
CHECK_INTERVAL_SECONDS=15
```

## 🌐 Деплой на Хостинг (VPS / Server)
На сервере (Linux / Ubuntu / Debian / Windows Server):
```bash
# Запуск бота FunPay:
python FunPay_BedWars_Bot/main.py

# Запуск бота Playerok:
python Playerok_BedWars_Bot/main.py
```
