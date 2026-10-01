#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Playerok Roblox BedWars Accounts Auto-Notifier Bot for Discord Webhooks
Monitors https://playerok.com/roblox/accounts?games=bedwars directly using Playerok's native GraphQL API.
Supports hosting via .env environment variables.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime, timezone

# Reconfigure stdout for Windows console UTF-8 support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass


def load_env():
    """Loads environment variables from .env file if available."""
    search_paths = [
        '.env',
        '../.env',
        os.path.join(os.path.dirname(__file__), '.env'),
        os.path.join(os.path.dirname(__file__), '..', '.env')
    ]
    for p in search_paths:
        if os.path.exists(p):
            try:
                with open(p, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            k, v = line.split('=', 1)
                            os.environ[k.strip()] = v.strip().strip('"').strip("'")
            except Exception:
                pass


load_env()

# Configuration Files
CONFIG_FILE = "config.json"
SEEN_FILE = "seen_lots.json"

DEFAULT_CONFIG = {
    "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),
    "discord_ping": os.getenv("DISCORD_PING", "@everyone"),
    "check_interval_seconds": int(os.getenv("CHECK_INTERVAL_SECONDS", 15)),
    "playerok_url": "https://playerok.com/roblox/accounts?games=bedwars",
    "first_run_notify_existing": os.getenv("FIRST_RUN_NOTIFY_EXISTING", "true").lower() == "true",
    "max_price": 0.0,
    "min_price": 0.0
}

# Playerok Native Category ID for Roblox Accounts
ROBLOX_ACCOUNTS_GAME_CATEGORY_ID = "1ecc48ce-52d9-6cc0-3b47-8e8d85cc8c7c"


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg or not cfg[k]:
                        cfg[k] = v
                if os.getenv("DISCORD_WEBHOOK_URL"):
                    cfg["discord_webhook_url"] = os.getenv("DISCORD_WEBHOOK_URL")
                return cfg
        except Exception as e:
            print(f"[⚠️ Warn] Ошибка чтения {CONFIG_FILE}: {e}. Используем стандартные настройки.")
    
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(DEFAULT_CONFIG, f, ensure_ascii=False, indent=2)
    return DEFAULT_CONFIG


def save_config(cfg):
    with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_seen_lots():
    if os.path.exists(SEEN_FILE):
        try:
            with open(SEEN_FILE, 'r', encoding='utf-8') as f:
                return set(json.load(f))
        except Exception as e:
            print(f"[⚠️ Warn] Ошибка чтения {SEEN_FILE}: {e}")
    return set()


def save_seen_lots(seen_set):
    try:
        seen_list = list(seen_set)[-3000:]
        with open(SEEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(seen_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[⚠️ Warn] Ошибка сохранения {SEEN_FILE}: {e}")


def fetch_playerok_native_bedwars_accounts():
    """
    Fetches the exact listings from Playerok Roblox BedWars Accounts category (https://playerok.com/roblox/accounts?games=bedwars)
    using Playerok's native GraphQL API attribute filter.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Content-Type': 'application/json',
        'Origin': 'https://playerok.com',
        'Referer': 'https://playerok.com/roblox/accounts?games=bedwars'
    }
    
    items = []
    graphql_url = "https://playerok.com/graphql"

    payload = {
        "operationName": "items",
        "variables": {
            "pagination": {
                "first": 20
            },
            "filter": {
                "status": "APPROVED",
                "gameCategoryId": ROBLOX_ACCOUNTS_GAME_CATEGORY_ID,
                "attributes": [
                    {
                        "field": "games",
                        "type": "RADIO",
                        "value": "bedwars"
                    }
                ]
            }
        },
        "query": """
        query items($pagination: Pagination, $filter: ItemFilter) {
          items(pagination: $pagination, filter: $filter) {
            totalCount
            edges {
              node {
                id
                name
                price
                slug
                user {
                  username
                }
              }
            }
          }
        }
        """
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(graphql_url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req, timeout=12) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            edges = res_json.get('data', {}).get('items', {}).get('edges', [])
            
            for ed in edges:
                node = ed.get('node', {})
                item_id = str(node.get('id', ''))
                if not item_id:
                    continue

                name = node.get('name', 'Roblox BedWars Аккаунт')
                price_val = float(node.get('price', 0))
                slug = node.get('slug', item_id)
                user_obj = node.get('user', {})
                seller = user_obj.get('username', 'Продавец Playerok') if user_obj else 'Продавец Playerok'
                
                href = f"https://playerok.com/products/{slug}" if slug else f"https://playerok.com/products/{item_id}"
                
                items.append({
                    'id': f"playerok_{item_id}",
                    'href': href,
                    'desc': name,
                    'price': f"{price_val:.0f} ₽",
                    'price_val': price_val,
                    'seller': seller,
                    'auto': True
                })
    except Exception as e:
        print(f"[⚠️ Error] Ошибка запроса к Playerok API: {e}")

    return items


def send_discord_webhook(webhook_url, lot, ping_text="@everyone"):
    if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
        print("[⚠️ Error] Неверный или отсутствующий Discord Webhook URL!")
        return False

    site_icon = "https://playerok.com/favicon-2026/favicon-96x96.png"

    title_desc = lot['desc']
    if len(title_desc) > 300:
        short_desc = title_desc[:297] + "..."
    else:
        short_desc = title_desc

    embed = {
        "title": "🎮 Roblox BedWars — Аккаунт (Playerok)",
        "url": lot['href'],
        "description": (
            f"📌 **Заголовок:**\n"
            f"```text\n{short_desc}\n```\n"
            f"👉 **[КУПИТЬ ЛОТ НА PLAYEROK]({lot['href']})**"
        ),
        "color": 10181046,  # Purple (#9B59B6)
        "fields": [
            {
                "name": "💰 Цена",
                "value": f"**{lot['price'] if lot['price'] else 'Не указана'}**",
                "inline": True
            },
            {
                "name": "👤 Продавец",
                "value": f"**{lot['seller'] if lot['seller'] else 'Аноним'}**",
                "inline": True
            },
            {
                "name": "🌐 Маркетплейс",
                "value": "🟣 **Playerok**",
                "inline": True
            }
        ],
        "footer": {
            "text": f"Playerok BedWars Monitor • Ссылка: {lot['href']}",
            "icon_url": site_icon
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    content_message = (
        f"{ping_text} 🚨 **НАЙДЕН АКТИВНЫЙ АККАУНТ BEDWARS НА PLAYEROK!**\n🔗 **Прямая ссылка:** {lot['href']}"
        if ping_text else
        f"🚨 **НАЙДЕН АКТИВНЫЙ АККАУНТ BEDWARS НА PLAYEROK!**\n🔗 **Прямая ссылка:** {lot['href']}"
    )

    payload = {
        "content": content_message,
        "username": "Playerok BedWars Bot",
        "avatar_url": site_icon,
        "embeds": [embed]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        if e.code == 401:
            print(f"[❌ Discord Error 401] Недействительный токен Webhook URL! Создайте новый Webhook в Discord.")
        else:
            print(f"[❌ Discord API Error {e.code}] {error_body}")
        return False
    except Exception as e:
        print(f"[❌ Error Sending Webhook] {e}")
        return False


def main():
    print("=" * 65)
    print(" 🚀 Playerok Roblox BedWars Accounts Discord Auto-Notifier Bot v3.0")
    print("=" * 65)

    config = load_config()

    webhook_url = config.get("discord_webhook_url", "").strip()
    if not webhook_url:
        print("\n[👉 Ввод Webhook] Вставьте ваш Discord Webhook URL:")
        webhook_url = input("Webhook URL: ").strip()
        if webhook_url:
            config["discord_webhook_url"] = webhook_url
            save_config(config)
            print("[✅] Webhook URL сохранен!")
        else:
            print("[❌ Error] Webhook URL обязателен для работы бота. Завершение работы.")
            return

    check_interval = max(5, int(config.get("check_interval_seconds", 15)))
    playerok_url = config.get("playerok_url", "https://playerok.com/roblox/accounts?games=bedwars")
    ping_text = config.get("discord_ping", "@everyone").strip()
    seen_lots = load_seen_lots()

    print(f"\n[ℹ️ Info] Категория Playerok: {playerok_url} ✅")
    print(f"[ℹ️ Info] Интервал проверки: {check_interval} сек.")
    print(f"[ℹ️ Info] Пинг участников: '{ping_text}'")
    print(f"[ℹ️ Info] Ранее просмотренных лотов в базе: {len(seen_lots)}")
    print("\n[🔄] Бот запущен и отслеживает нативные товары категории Playerok...\n")

    is_first_check = True

    while True:
        try:
            now_str = datetime.now().strftime("%H:%M:%S")
            
            p_lots = fetch_playerok_native_bedwars_accounts()
            matching_lots = []
            
            for item in p_lots:
                if config.get("min_price", 0) > 0 and item['price_val'] < config["min_price"]:
                    continue
                if config.get("max_price", 0) > 0 and item['price_val'] > config["max_price"]:
                    continue
                matching_lots.append(item)

            new_count = 0
            for lot in reversed(matching_lots):
                lot_id = lot['id']
                should_notify = (lot_id not in seen_lots) or (is_first_check and config.get("first_run_notify_existing", True))
                
                if should_notify:
                    seen_lots.add(lot_id)
                    new_count += 1

                    print(f"[{now_str}] ⚡ НАЙДЕН АКТИВНЫЙ АККАУНТ (Playerok)! ID: {lot['id']} | {lot['price']} | {lot['seller']}")
                    print(f"         Ссылка: {lot['href']}")
                    print(f"         Заголовок: {lot['desc'][:80]}...")
                    
                    success = send_discord_webhook(webhook_url, lot, ping_text)
                    if success:
                        print("         [✅] Уведомление отправлено в Discord!")
                    else:
                        print("         [❌] Ошибка отправки уведомления в Discord.")
                    
                    time.sleep(1.0)
                else:
                    seen_lots.add(lot_id)

            if is_first_check:
                print(f"[{now_str}] [ℹ️ Первичная проверка] Нативно получено {len(p_lots)} товаров с https://playerok.com/roblox/accounts?games=bedwars.")
                is_first_check = False
            else:
                if new_count > 0:
                    print(f"[{now_str}] 🎉 Обработано новых аккаунтов: {new_count}")
                else:
                    print(f"[{now_str}] 🔍 Проверка завершена. Новых аккаунтов не найдено. (Активных товаров в категории: {len(matching_lots)})")

            save_seen_lots(seen_lots)

        except urllib.error.HTTPError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ошибка HTTP Playerok ({e.code}): {e.reason}. Повтор через {check_interval} сек...")
        except urllib.error.URLError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ошибка соединения: {e.reason}. Повтор через {check_interval} сек...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Произошла ошибка: {e}")

        time.sleep(check_interval)


if __name__ == "__main__":
    main()
