import os
import json
from datetime import datetime

from pub_config import JST

def get_unique_filepath(base_dir, base_name):
    os.makedirs(base_dir, exist_ok=True)
    date_str = datetime.now(JST).strftime("%m%d")
    counter = 1
    while True:
        path = os.path.join(base_dir, f"{base_name} {date_str}({counter}).json")
        if not os.path.exists(path):
            print(f"　[unique_file] Archiveファイル : {base_name} {date_str}({counter}).json")
            return path
        counter += 1

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            print (f"　[load_json] ⭕️ jsonファイルの読み込みに成功 : {path}")
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"　[load_json] ❌️ jsonデコードエラー : {e}")
        return None
    except Exception as e:
        print(f"　[load_json] ❌️ json読み込みエラー: {e}")
        return None