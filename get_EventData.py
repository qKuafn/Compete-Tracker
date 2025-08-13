import requests
import os
import json
import asyncio

import config
import config2
from tokens import ensure_token
from files import load_json, get_unique_filepath, safe_print

def fetch_EventData(region="ASIA", type="first"):
    safe_print(f"[INF] EventData 取得開始 : {region} (Acc:{type})")

    count = "2" if type == "second" else ""

    url = getattr(config, f"EventData_URL{count}")
    token_type = getattr(config, f"token_type{count}")
    access_token = getattr(config, f"access_token{count}")

    headers = {
        "Authorization": f"{token_type} {access_token}"
    }
    params = {
        "region": region
    }
    res = requests.get(url, headers=headers, params=params)

    if res.status_code == 200:
        data = res.json()
        if type == "first":
            filepath = os.path.join(config2.RESPONSE_DIR, f"EventData_{region}.json")
            new_data = data
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                safe_print(f"  [ERR] ❌️ 旧ファイルの取得に失敗 : {e}")
            if new_data != before_data or before_data is None:
                try:
                    if config2.test is False:
                        with open(get_unique_filepath(config2.ARCHIVE_DIR, f"EventData_{region}"), "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    config.tags.append(region)
                    config.updated_regions.append(region)
                    safe_print(f"  [INF] 🟢 {region}: 変更あり")
                except Exception as e:
                    safe_print(f"  [INF] ❌️ ファイルの保存に失敗 : {e}")
            elif new_data== before_data:
                safe_print(f"  [INF] ✅️ {region}: 変更なし")
        return data
    else:
        safe_print(f"  [ERR] 🔴 {region} 取得に失敗 : {res.text} {res.status_code}")
        return None

async def run():
    ensure_token()
    await asyncio.gather(*(asyncio.to_thread(fetch_EventData, region) for region in config2.Regions))

if __name__ == "__main__":
    config2.test = True
    asyncio.run(run())