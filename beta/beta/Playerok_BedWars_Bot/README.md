# 🚀 Playerok Roblox BedWars Accounts Discord Bot

Автоматический Discord-бот для отслеживания **настоящих личных аккаунтов Roblox BedWars** на маркетплейсе **Playerok** (`https://playerok.com/roblox/accounts?games=bedwars`).

## ✨ Особенности

* 🟣 **Поддержка Playerok**: Автоматический мониторинг через GraphQL API Playerok.
* 🛡️ **Защита от Аренды**: Исключает временные аккаунты (*«на 1 день»*, *«на 2 дня»*, *«на 24 часа»*, *«аренда»*).
* 🛑 **Защита от мусора**: Исключает ресурспаки (РП), фонды роста, монеты, киты, гифты и услуги.
* 💬 **Discord Webhook**: Присылает лаконичные фиолетовые карточки с кнопкой покупки, ценой, продавцом и пингом `@everyone`.

## ⚙️ Настройка (`config.json`)

```json
{
  "discord\\\_webhook\\\_url": "ВАШ\\\_WEBHOOK\\\_URL",
  "discord\\\_ping": "@everyone",
  "check\\\_interval\\\_seconds": 15,
  "playerok\\\_url": "https://playerok.com/roblox/accounts?games=bedwars",
  "accounts\\\_only": true,
  "exclude\\\_rentals": true
}
```

## 🚀 Запуск

1. Запустите файл `start.bat`.
2. Бот автоматически начнет отслеживать новые аккаунты BedWars на Playerok.

