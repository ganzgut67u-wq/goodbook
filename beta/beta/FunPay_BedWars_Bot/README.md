# 🚀 FunPay BedWars Discord Auto-Notifier Bot

Автономный чистый Python бот для отслеживания объявлений **Roblox BedWars** на маркетплейсе **FunPay** ([Категория #401: Аккаунты Roblox](https://funpay.com/lots/401/)).

При появлении нового объявления бот мгновенно отправляет стильное уведомление в ваш **Discord Webhook**!

---

## 📂 Файлы проекта

* `main.py` — Главный скрипт бота (парсинг FunPay + интеграция с Discord Webhook).
* `start.bat` — Запуск бота в один клик для Windows (просто дважды кликните).
* `config.json` — Файл настроек (Discord Webhook URL, интервал проверки, ключевые слова, фильтры цен).
* `seen_lots.json` — Автоматически создаваемый база-файл с просмотренными ID лотов (защита от повторов).
* `requirements.txt` — Скрипт использует стандартную библиотеку Python (pip сторонние модули не требуются!).

---

## ⚡ Быстрый запуск

1. Дважды кликните по файлу `start.bat`.
2. При первом запуске вставьте ваш **Discord Webhook URL**.
3. Бот начнет непрерывный мониторинг FunPay каждые 15 секунд и будет мгновенно оповещать вас о новых аккаунтах BedWars!

---

## ⚙️ Конфигурация (`config.json`)

```json
{
  "discord_webhook_url": "https://discord.com/api/webhooks/...",
  "check_interval_seconds": 15,
  "keywords": ["bedwars", "бедварс", "bed wars", "бед варс"],
  "category_url": "https://funpay.com/lots/401/",
  "first_run_notify_existing": false,
  "min_price": 0.0,
  "max_price": 0.0,
  "auto_delivery_only": false
}
```
