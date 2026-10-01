#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunPay BedWars Auto-Notifier Bot for Discord Webhooks
Monitors FunPay Roblox Accounts (Category 401) for BedWars listings.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
from datetime import datetime
from html.parser import HTMLParser

# Reconfigure stdout for Windows console UTF-8 support
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Default Configuration
CONFIG_FILE = "config.json"
SEEN_FILE = "seen_lots.json"

DEFAULT_CONFIG = {
    "discord_webhook_url": "",
    "check_interval_seconds": 15,
    "keywords": ["bedwars", "бедварс", "bed wars", "бед варс"],
    "category_url": "https://funpay.com/lots/401/",
    "first_run_notify_existing": False,  # If False, ignores old lots on startup and only notifies about NEW ones
    "max_price": 0.0,  # 0.0 = no limit
    "min_price": 0.0,  # 0.0 = no limit
    "auto_delivery_only": False
}


class FunPayLotParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []
        self.current_item = None
        self.current_field = None
        self.field_buffer = []

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        cls = attr_dict.get('class', '')

        if tag == 'a' and 'tc-item' in cls:
            href = attr_dict.get('href', '')
            lot_id = attr_dict.get('data-id', '')
            if not lot_id and 'id=' in href:
                lot_id = href.split('id=')[-1]

            if href and not href.startswith('http'):
                href = 'https://funpay.com' + href.lstrip('/')

            self.current_item = {
                'id': lot_id,
                'href': href,
                'desc': '',
                'price': '',
                'price_val': 0.0,
                'seller': '',
                'auto': 'tc-auto' in cls
            }
            self.items.append(self.current_item)

        if self.current_item:
            if 'tc-desc-text' in cls:
                self.current_field = 'desc'
                self.field_buffer = []
            elif 'tc-price' in cls:
                self.current_field = 'price'
                self.field_buffer = []
            elif 'tc-user' in cls or 'media-user-name' in cls:
                self.current_field = 'seller'
                self.field_buffer = []

    def handle_endtag(self, tag):
        if self.current_item and self.current_field:
            text = " ".join("".join(self.field_buffer).split())
            if not self.current_item[self.current_field]:
                self.current_item[self.current_field] = text
            else:
                self.current_item[self.current_field] += " " + text
            
            # Extract numeric value for price
            if self.current_field == 'price':
                num_match = urllib.parse.unquote(text).replace(',', '.')
                import re
                nums = re.findall(r'[\d\.]+', num_match)
                if nums:
                    try:
                        self.current_item['price_val'] = float(nums[0])
                    except ValueError:
                        pass
                        
            self.current_field = None
            self.field_buffer = []

    def handle_data(self, data):
        if self.current_item and self.current_field:
            self.field_buffer.append(data)


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                cfg = json.load(f)
                # Merge with defaults
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg:
                        cfg[k] = v
                return cfg
        except Exception as e:
            print(f"[⚠️ Warn] Ошибка чтения {CONFIG_FILE}: {e}. Используем стандартные настройки.")
    
    # Save default config if not existing
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
        # Keep only the last 2000 seen items to avoid unlimited file growth
        seen_list = list(seen_set)[-2000:]
        with open(SEEN_FILE, 'w', encoding='utf-8') as f:
            json.dump(seen_list, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[⚠️ Warn] Ошибка сохранения {SEEN_FILE}: {e}")


def fetch_funpay_lots(category_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    req = urllib.request.Request(category_url, headers=headers)
    with urllib.request.urlopen(req, timeout=12) as response:
        html_content = response.read().decode('utf-8')
    
    parser = FunPayLotParser()
    parser.feed(html_content)
    return parser.items


def send_discord_webhook(webhook_url, lot):
    if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
        print("[⚠️ Error] Неверный или отсутствующий Discord Webhook URL!")
        return False

    title_desc = lot['desc']
    if len(title_desc) > 250:
        title_desc = title_desc[:247] + "..."

    embed = {
        "title": "🎮 Новое объявление BedWars на FunPay!",
        "url": lot['href'],
        "description": f"**Описание:**\n{title_desc}",
        "color": 3447003,  # Discord Blurple / Vibrant Blue
        "fields": [
            {
                "name": "💰 Цена",
                "value": lot['price'] if lot['price'] else "Не указана",
                "inline": True
            },
            {
                "name": "👤 Продавец",
                "value": lot['seller'] if lot['seller'] else "Неизвестен",
                "inline": True
            },
            {
                "name": "⚡ Автовыдача",
                "value": "✅ Да" if lot['auto'] else "❌ Нет",
                "inline": True
            }
        ],
        "footer": {
            "text": f"FunPay BedWars Monitor • ID Лота: {lot['id']}",
            "icon_url": "https://funpay.com/img/layout/logo.png"
        },
        "timestamp": datetime.utcnow().isoformat() + "Z"
    }

    payload = {
        "username": "FunPay BedWars Bot",
        "avatar_url": "https://funpay.com/img/layout/logo.png",
        "embeds": [embed]
    }

    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={
            'Content-Type': 'application/json',
            'User-Agent': 'FunPayDiscordNotifier/1.0'
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status in (200, 204)
    except urllib.error.HTTPError as e:
        print(f"[❌ Discord API Error] {e.code}: {e.read().decode('utf-8')}")
        return False
    except Exception as e:
        print(f"[❌ Error Sending Webhook] {e}")
        return False


def main():
    print("=" * 65)
    print(" 🚀 FunPay BedWars Discord Auto-Notifier Bot v1.0")
    print("=" * 65)

    config = load_config()

    # Prompt for webhook if empty
    webhook_url = config.get("discord_webhook_url", "").strip()
    if not webhook_url:
        print("\n[👉 Ввод Webhook] Вставьте ваш Discord Webhook URL:")
        webhook_url = input("Webhook URL: ").strip()
        if webhook_url:
            config["discord_webhook_url"] = webhook_url
            save_config(config)
            print("[✅] Webhook URL сохранен в config.json!")
        else:
            print("[❌ Error] Webhook URL обязателен для работы бота. Завершение работы.")
            return

    keywords = [kw.lower() for kw in config.get("keywords", ["bedwars"])]
    check_interval = max(5, int(config.get("check_interval_seconds", 15)))
    category_url = config.get("category_url", "https://funpay.com/lots/401/")
    seen_lots = load_seen_lots()

    print(f"\n[ℹ️ Info] Категория: {category_url}")
    print(f"[ℹ️ Info] Ключевые слова: {', '.join(keywords)}")
    print(f"[ℹ️ Info] Интервал проверки: {check_interval} сек.")
    print(f"[ℹ️ Info] Загружено ранее просмотренных лотов: {len(seen_lots)}")
    print("\n[🔄] Бот запущен и отслеживает новые объявления...\n")

    is_first_run = len(seen_lots) == 0

    while True:
        try:
            now_str = datetime.now().strftime("%H:%M:%S")
            lots = fetch_funpay_lots(category_url)
            
            # Filter lots by keywords
            matching_lots = []
            for item in lots:
                desc_lower = item['desc'].lower()
                if any(kw in desc_lower for kw in keywords):
                    # Check price filters
                    if config.get("min_price", 0) > 0 and item['price_val'] < config["min_price"]:
                        continue
                    if config.get("max_price", 0) > 0 and item['price_val'] > config["max_price"]:
                        continue
                    if config.get("auto_delivery_only") and not item['auto']:
                        continue
                    matching_lots.append(item)

            new_count = 0
            for lot in reversed(matching_lots):  # Oldest to newest
                lot_id = lot['id']
                if lot_id and lot_id not in seen_lots:
                    seen_lots.add(lot_id)
                    new_count += 1
                    
                    if is_first_run and not config.get("first_run_notify_existing", False):
                        # On first run, silently mark existing lots as seen
                        continue

                    print(f"[{now_str}] ⚡ НАЙДЕНО НОВОЕ ОБЪЯВЛЕНИЕ! ID: {lot['id']} | {lot['price']} | {lot['seller']}")
                    print(f"         Заголовок: {lot['desc'][:80]}...")
                    
                    success = send_discord_webhook(webhook_url, lot)
                    if success:
                        print("         [✅] Уведомление успешно отправлено в Discord!")
                    else:
                        print("         [❌] Не удалось отправить уведомление в Discord.")
                    
                    # Small delay between webhook posts to avoid Discord rate-limits
                    time.sleep(1.0)

            if is_first_run:
                print(f"[{now_str}] [ℹ️ Первый запуск] Просканировано {len(lots)} лотов. Найдено {len(matching_lots)} BedWars лотов. Запомнено {len(seen_lots)} ID.")
                is_first_run = False
            else:
                if new_count > 0:
                    print(f"[{now_str}] 🎉 Обработано новых объявлений: {new_count}")
                else:
                    print(f"[{now_str}] 🔍 Проверка завершена. Новых объявлений BedWars не найдено. (Всего активных: {len(matching_lots)})")

            save_seen_lots(seen_lots)

        except urllib.error.HTTPError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ошибка HTTP FunPay ({e.code}): {e.reason}. Повтор через {check_interval} сек...")
        except urllib.error.URLError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ошибка соединения: {e.reason}. Повтор через {check_interval} сек...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Произошла ошибка: {e}")

        time.sleep(check_interval)


if __name__ == "__main__":
    main()
