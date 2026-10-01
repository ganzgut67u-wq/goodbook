import urllib.request
import json
import sys

sys.stdout.reconfigure(encoding='utf-8')

graphql_url = 'https://playerok.com/graphql'
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'Content-Type': 'application/json',
    'Origin': 'https://playerok.com',
    'Referer': 'https://playerok.com/roblox/accounts?games=bedwars'
}

# Known IDs from page:
target_ids = {
    "1f1906d6-a6e8-6920-bc4c-181fee86e951",
    "1f18abf2-94a5-6540-f517-9decbf1427d9",
    "1f189f9d-a797-6150-aa8c-38ef615b805e",
    "1f189867-6d66-60e0-f23f-8d1636732fab"
}

# Test different filter object structures on ItemFilter
filter_candidates = [
    {"status": "APPROVED", "gameCategorySlug": "roblox-accounts"},
    {"status": "APPROVED", "brandSlug": "roblox", "categorySlug": "accounts"},
    {"status": "APPROVED", "gameSlug": "bedwars"},
    {"status": "APPROVED", "gameSlugs": ["bedwars"]},
    {"status": "APPROVED", "games": ["bedwars"]},
    {"status": "APPROVED", "gameCategorySlugs": ["roblox-accounts"]}
]

for flt in filter_candidates:
    payload = {
        "operationName": "items",
        "variables": {
            "pagination": {"first": 20},
            "filter": flt
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
                user { username }
              }
            }
          }
        }
        """
    }
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(graphql_url, data=data, headers=headers, method='POST')
        with urllib.request.urlopen(req) as resp:
            res_json = json.loads(resp.read().decode('utf-8'))
            edges = res_json.get('data', {}).get('items', {}).get('edges', [])
            found_target_count = sum(1 for e in edges if e['node']['id'] in target_ids)
            print(f"[{json.dumps(flt)}] SUCCESS: {len(edges)} total items returned, TARGET MATCHES: {found_target_count}")
            if found_target_count > 0:
                for e in edges:
                    if e['node']['id'] in target_ids:
                        print(f"   MATCH -> ID: {e['node']['id']} | Price: {e['node']['price']} | Title: {e['node']['name']}")
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8')
        if "not defined by type" in body:
            pass
        else:
            print(f"[{json.dumps(flt)}] HTTP Error {e.code}: {body[:200]}")
    except Exception as e:
        print(f"[{json.dumps(flt)}] Exception:", e)
