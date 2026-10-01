#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FunPay BedWars Auto-Notifier Bot for Discord Webhooks
Monitors FunPay Roblox Accounts (#401 & #402).
Supports hosting via .env environment variables.
"""

import os
import sys
import time
import json
import urllib.request
import urllib.parse
import http.cookiejar
import re
from datetime import datetime, timezone
from html.parser import HTMLParser

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

_cookie_jar = http.cookiejar.CookieJar()


def format_proxy_url(raw_proxy):
    if not raw_proxy:
        return None
    raw_proxy = raw_proxy.strip()
    if raw_proxy.startswith("http://") or raw_proxy.startswith("https://") or raw_proxy.startswith("socks5://"):
        return raw_proxy
    parts = raw_proxy.split(":")
    if len(parts) == 4:
        ip, port, user, pwd = parts
        return f"http://{user}:{pwd}@{ip}:{port}"
    elif len(parts) == 2:
        ip, port = parts
        return f"http://{ip}:{port}"
    return f"http://{raw_proxy}"


def get_opener():
    handlers = [urllib.request.HTTPCookieProcessor(_cookie_jar)]
    proxy_str = os.getenv("PROXY_URL", "").strip() or os.getenv("FUNPAY_PROXY", "").strip()
    formatted_proxy = format_proxy_url(proxy_str)
    if formatted_proxy:
        print(f"[🛡️ Proxy] Использование прокси для FunPay: {formatted_proxy.split('@')[-1]} ✅")
        proxy_handler = urllib.request.ProxyHandler({
            'http': formatted_proxy,
            'https': formatted_proxy
        })
        handlers.append(proxy_handler)
    return urllib.request.build_opener(*handlers)


_funpay_opener = get_opener()

# Configuration Files
CONFIG_FILE = "config.json"
SEEN_FILE = "seen_lots.json"

DEFAULT_CONFIG = {
    "discord_webhook_url": os.getenv("DISCORD_WEBHOOK_URL", ""),
    "discord_ping": os.getenv("DISCORD_PING", "@everyone"),
    "proxy_url": os.getenv("PROXY_URL", ""),
    "check_interval_seconds": int(os.getenv("CHECK_INTERVAL_SECONDS", 15)),
    "keywords": ["bedwars", "бедварс", "bed wars", "бед варс"],
    "category_urls": [
        "https://funpay.com/lots/401/",
        "https://funpay.com/lots/402/"
    ],
    "first_run_notify_existing": os.getenv("FIRST_RUN_NOTIFY_EXISTING", "true").lower() == "true",
    "max_price": 0.0,
    "min_price": 0.0,
    "auto_delivery_only": False,
    "accounts_only": True
}

NON_ACCOUNT_TAGS = [
    'gamepass', 'геймпасс', 'предметы', 'услуги', 'валюта', 
    'скины', 'подарю', 'gift', 'гифт', 'кит', 'гайд', 'робуксов', 'робукс', 'подарок'
]


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
                href = 'https://funpay.com/' + href.lstrip('/')

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
            
            if self.current_field == 'price':
                num_match = urllib.parse.unquote(text).replace(',', '.')
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
                for k, v in DEFAULT_CONFIG.items():
                    if k not in cfg or not cfg[k]:
                        cfg[k] = v
                # Always prioritize .env if set
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


def fetch_funpay_lots(category_url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
        'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
        'Cookie': 'locale=ru; cy=rub',
        'Referer': 'https://funpay.com/'
    }
    
    html_content = ""
    try:
        req = urllib.request.Request(category_url, headers=headers)
        with _funpay_opener.open(req, timeout=15) as response:
            html_content = response.read().decode('utf-8', errors='ignore')
    except urllib.error.HTTPError as e:
        if e.code == 404 and '/lots/' in category_url:
            alt_url = category_url.replace('https://funpay.com/lots/', 'https://funpay.com/en/lots/')
            req_alt = urllib.request.Request(alt_url, headers=headers)
            with _funpay_opener.open(req_alt, timeout=15) as response:
                html_content = response.read().decode('utf-8', errors='ignore')
        else:
            raise
    
    parser = FunPayLotParser()
    parser.feed(html_content)
    return parser.items


def is_account_lot(item, cat_url="", accounts_only=True):
    if not accounts_only:
        return True

    if '401' in cat_url:
        return True

    desc_lower = item['desc'].lower()

    if 'аккаунты' in desc_lower or 'аккаунт' in desc_lower or 'акк' in desc_lower or 'acc' in desc_lower:
        if any(tag in desc_lower for tag in ['gamepass', 'геймпасс', 'услуги', 'предметы', 'подарю', 'гайд']) and 'аккаунты' not in desc_lower:
            return False
        return True

    if any(tag in desc_lower for tag in NON_ACCOUNT_TAGS):
        return False

    return True


def send_discord_webhook(webhook_url, lot, ping_text="@everyone"):
    if not webhook_url or not webhook_url.startswith("https://discord.com/api/webhooks/"):
        print("[⚠️ Error] Неверный или отсутствующий Discord Webhook URL!")
        return False

    title_desc = lot['desc']
    if len(title_desc) > 300:
        short_desc = title_desc[:297] + "..."
    else:
        short_desc = title_desc

    embed = {
        "title": "🎮 Roblox BedWars — Аккаунт (FunPay)",
        "url": lot['href'],
        "description": (
            f"📌 **Описание:**\n"
            f"```text\n{short_desc}\n```\n"
            f"👉 **[КУПИТЬ ЛОТ НА FUNPAY]({lot['href']})**"
        ),
        "color": 3447003,
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
                "name": "🆔 ID Лота",
                "value": f"`#{lot['id']}`",
                "inline": True
            }
        ],
        "footer": {
            "text": f"FunPay BedWars Monitor • Ссылка: {lot['href']}",
            "icon_url": "https://funpay.com/img/layout/logo.png"
        },
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    content_message = (
        f"{ping_text} 🚨 **НАЙДЕН АКТИВНЫЙ АККАУНТ BEDWARS НА FUNPAY!**\n🔗 **Прямая ссылка:** {lot['href']}"
        if ping_text else
        f"🚨 **НАЙДЕН АКТИВНЫЙ АККАУНТ BEDWARS НА FUNPAY!**\n🔗 **Прямая ссылка:** {lot['href']}"
    )

    payload = {
        "content": content_message,
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
    print(" 🚀 FunPay BedWars Discord Auto-Notifier Bot v1.0")
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

    keywords = [kw.lower() for kw in config.get("keywords", ["bedwars", "бедварс", "bed wars", "бед варс"])]
    check_interval = max(5, int(config.get("check_interval_seconds", 15)))
    accounts_only = config.get("accounts_only", True)
    
    category_urls = config.get("category_urls", ["https://funpay.com/lots/401/", "https://funpay.com/lots/402/"])
    if isinstance(category_urls, str):
        category_urls = [category_urls]

    ping_text = config.get("discord_ping", "@everyone").strip()
    seen_lots = load_seen_lots()

    print(f"\n[ℹ️ Info] Отслеживаемые категории FunPay: {', '.join(category_urls)}")
    print(f"[ℹ️ Info] Ключевые слова: {', '.join(keywords)}")
    print(f"[ℹ️ Info] Фильтр 'Только Аккаунты': {'Включен ✅' if accounts_only else 'Выключен ❌'}")
    print(f"[ℹ️ Info] Интервал проверки: {check_interval} сек.")
    print(f"[ℹ️ Info] Пинг участников: '{ping_text}'")
    print(f"[ℹ️ Info] Ранее просмотренных лотов в базе: {len(seen_lots)}")
    print("\n[🔄] Бот запущен и отслеживает FunPay...\n")

    is_first_check = True

    while True:
        try:
            now_str = datetime.now().strftime("%H:%M:%S")
            
            matching_lots = []
            total_scanned_lots = 0
            
            for cat_url in category_urls:
                try:
                    lots = fetch_funpay_lots(cat_url)
                    total_scanned_lots += len(lots)
                    for item in lots:
                        desc_lower = item['desc'].lower()
                        if any(kw in desc_lower for kw in keywords):
                            if not is_account_lot(item, cat_url, accounts_only):
                                continue
                            if config.get("min_price", 0) > 0 and item['price_val'] < config["min_price"]:
                                continue
                            if config.get("max_price", 0) > 0 and item['price_val'] > config["max_price"]:
                                continue
                            if config.get("auto_delivery_only") and not item['auto']:
                                continue
                            matching_lots.append(item)
                except Exception as cat_err:
                    print(f"[{now_str}] ⚠️ Ошибка сканирования FunPay ({cat_url}): {cat_err}")

            new_count = 0
            for lot in reversed(matching_lots):
                lot_id = lot['id']
                should_notify = (lot_id not in seen_lots) or (is_first_check and config.get("first_run_notify_existing", True))
                
                if should_notify:
                    seen_lots.add(lot_id)
                    new_count += 1

                    print(f"[{now_str}] ⚡ НАЙДЕН АКТИВНЫЙ АККАУНТ (FunPay)! ID: {lot['id']} | {lot['price']} | {lot['seller']}")
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
                print(f"[{now_str}] [ℹ️ Первичная проверка] Просканировано {total_scanned_lots} лотов FunPay. Найдено {len(matching_lots)} АККАУНТОВ BedWars.")
                is_first_check = False
            else:
                if new_count > 0:
                    print(f"[{now_str}] 🎉 Обработано новых аккаунтов: {new_count}")
                else:
                    print(f"[{now_str}] 🔍 Проверка завершена. Новых аккаунтов не найдено. (Активных аккаунтов: {len(matching_lots)})")

            save_seen_lots(seen_lots)

        except urllib.error.HTTPError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ошибка HTTP ({e.code}): {e.reason}. Повтор через {check_interval} сек...")
        except urllib.error.URLError as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Ошибка соединения: {e.reason}. Повтор через {check_interval} сек...")
        except Exception as e:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ⚠️ Произошла ошибка: {e}")

        time.sleep(check_interval)


if __name__ == "__main__":
    main()
