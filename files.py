import os
import json
import re
from datetime import datetime
from PIL import Image
import threading

import config

def get_unique_filepath(base_dir, base_name, ext="json"):
    os.makedirs(base_dir, exist_ok=True)
    date_str = datetime.now(config.JST).strftime("%m%d")
    counter = 1
    while True:
        path = os.path.join(base_dir, f"{base_name} {date_str}({counter}).{ext}")
        if not os.path.exists(path):
            safe_print(f"　[INF] ⭕️ Archiveファイル作成に成功 : {base_name} {date_str}({counter}).{ext}")
            return path
        counter += 1

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            safe_print (f"　[INF] ⭕️ jsonファイルの読み込みに成功 : {path}")
            return json.load(f)
    except json.JSONDecodeError as e:
        safe_print(f"　[ERR] ❌️ jsonデコードエラー : {e}")
        return None
    except Exception as e:
        safe_print(f"　[ERR] ❌️ jsonファイル読み込み失敗: {e}")
        return None

def load_ini(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            safe_print (f"　[INF] ⭕️ iniファイル読み込み成功 : {path}")
            return f.read()
    except Exception as e:
        safe_print(f"　[ERR] ❌️ iniファイル読み込み失敗: {e}")
        return None

def load_png(path):
    try:
        with Image.open(path) as f:
            safe_print (f"　    [INF] ⭕️ pngファイル読み込み成功 : {path}")
            return f.convert("RGBA")
    except Exception as e:
        safe_print(f"　    [ERR] ❌️ pngファイル読み込み失敗: {e}")
        return None

def sanitize_filename(name: str) -> str:
    invalid_chars = r'[\\/:*?"<>|]'
    sanitized = re.sub(invalid_chars, ' ', name)
    sanitized = re.sub(r'\s+', ' ', sanitized)
    sanitized = sanitized.strip()
    return sanitized

def format_number(value):
    if isinstance(value, (int, float)):
        num = float(value)
    elif isinstance(value, str) and re.fullmatch(r'-?\d+(\.\d+)?', value.strip()):
        num = float(value.strip())
    else:
        return value

    rounded = round(num, 2)
    if rounded == int(rounded):
        return f"{int(rounded)}.0"
    else:
        return f"{rounded:.2f}".rstrip("0").rstrip(".")

print_lock = threading.Lock()

def safe_print(msg):
    with print_lock:
        print(msg, flush=True)