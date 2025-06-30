import requests
import os
import json
import config
import pub_config as config2

from get_token import *
from files import *

def fetch_EventData(region, tags):
    url = f"{config.TOURNAMENT_URL}?region={region}"
    for attempt in range(2):
        ensure_token()
        headers = {"Authorization": f"{config.token_type} {config.access_token}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            filepath = os.path.join(config2.RESPONSE_DIR, f"EventData_{region}.json")
            new_data = data
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                print("[EventData] ❌️ 旧ファイルの取得に失敗")
            if new_data != before_data or before_data is None:
                try:
                    if config2.test is False:
                        with open(get_unique_filepath(config2.ARCHIVE_DIR, f"EventData_{region}"), "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    tags.append(region)
                    print(f"[EventData] 🟢 {region} : 更新あり")
                    return True
                except Exception as e:
                    print(f"[EventData] ❌️ ファイルの保存に失敗 : {e}")
                    return False
            elif new_data == before_data:
                return True
            else:
                return False
        else:
            print(f"[EventData] ❌️ 取得失敗 ({region}) : {res.status_code}")
            if attempt == 0:
                print("[EventData] 🔁 リトライ")
                get_token()
                time.sleep(10)
            else:
                return None

def fetch_EventData_for_format():
    url = f"{config.TOURNAMENT_URL2}?region=ASIA"
    for attempt in range(2):
        ensure_token_for_format()
        headers = {"Authorization": f"{config.token_type2} {config.access_token2}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            return data
        else:
            print(f"[EventData2] ❌️ 取得失敗 : {res.status_code} {res.text}")
            if attempt == 0:
                print("[EventData2] 🔁 リトライ")
                get_token_for_format()
                time.sleep(10)
            else:
                return None