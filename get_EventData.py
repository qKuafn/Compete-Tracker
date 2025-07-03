import requests
import os
import json
import config
import pub_config as config2

from tokens import *
from files import *

def fetch_EventData(type, region="ASIA", tags=[], updated_regions = []):
    count = "2" if type == "second" else ""
    print (f"[EventData{count}] 取得開始 : {region}")
    url = getattr(config, f"EventData_URL{count}") + f"?region={region}"
    ensure_token(type)
    headers = {"Authorization": getattr(config, f"token_type{count}") + " " + getattr(config, f"access_token{count}")}
    res = requests.get(url, headers=headers)
    if res.status_code == 200:
        data = res.json()
        if type == "first":
            filepath = os.path.join(config2.RESPONSE_DIR, f"EventData_{region}.json")
            new_data = data
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                print(f"  [EventData{count}] ❌️ 旧ファイルの取得に失敗")
            if new_data != before_data or before_data is None:
                try:
                    if config2.test is False:
                        with open(get_unique_filepath(config2.ARCHIVE_DIR, f"EventData_{region}"), "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    tags.append(region)
                    updated_regions.append(region)
                    print(f"  [EventData{count}] 🟢更新あり")
                except Exception as e:
                    print(f"  [EventData{count}] ❌️ ファイルの保存に失敗 : {e}")
            elif new_data== before_data:
                print(f"  [EventData{count}] 更新なし")
        return data
    else:
        print(f"  [EventData{count}] ❌️ 取得失敗 : {res.text} {res.status_code}")
        return None