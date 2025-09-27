import requests
import os
import json
import asyncio
import time

import config
import config2
from tokens import ensure_token
from files import load_json, get_unique_filepath, safe_print
from format_Event import format_EventData

def fetch_EventData(region="ASIA"):
    safe_print(f"[INF] EventData 取得開始 : {region}")

    ensure_token("first")

    url = config.EventData_URL
    token_type = config.token_type
    access_token = config.access_token

    headers = {
        "Authorization": f"{token_type} {access_token}"
    }
    params = {
        "region": region
    }
    for attempt in range(2):
        try:
            res = requests.get(url, headers=headers, params=params)

            if res.status_code == 200:
                data = res.json()
                filepath = os.path.join(config2.RESPONSE_DIR, f"EventData_{region}.json")
                new_data = data
                try:
                    before_data = load_json(filepath) if os.path.exists(filepath) else None
                except Exception as e:
                    safe_print(f"  [ERR] ❌️ 旧ファイルの取得に失敗 : {e}")
                if new_data != before_data or before_data is None:
                    try:
                        #if config2.test is False:
                        #    with open(get_unique_filepath(config2.ARCHIVE_DIR, f"EventData_{region}"), "w", encoding="utf-8") as f:
                        #       json.dump(data, f, ensure_ascii=False, indent=2)
                        with open(filepath, "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                        config.tags.append(region)
                        config.updated_regions.append(region)
                        safe_print(f"  [INF] 🟢 {region}: 変更あり")
                        if region == "ASIA":
                            format_EventData(data)
                        return
                    except Exception as e:
                        safe_print(f"  [INF] ❌️ ファイルの保存に失敗 : {e}")
                elif new_data== before_data:
                    safe_print(f"  [INF] ✅️ {region}: 変更なし")
                    return
            else:
                safe_print(f"  [ERR] 🔴 {region} 取得に失敗 : {res.text} {res.status_code}")
        except Exception as e:
            safe_print(f"  [ERR] 🔴 {region} 取得中に例外発生 : {e}")

        if attempt < 2 - 1:
            safe_print(f"  [INF] {region} リトライします ({attempt + 1}/{2}) ...")
            ensure_token(type)
            time.sleep(30)
        else:
            safe_print(f"  [ERR] {region} 取得失敗: 最大リトライ回数に達しました")
            return None

async def run():
    ensure_token()
    await asyncio.gather(*(asyncio.to_thread(fetch_EventData, region) for region in config2.Regions))

if __name__ == "__main__":
    config2.test = True
    asyncio.run(run())