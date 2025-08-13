import requests
import os
from io import BytesIO
from PIL import Image

from files import sanitize_filename
import config

def fetch_export_data(data_path):
    path = strip_after_dot(data_path)
    url = f"https://export-service.dillyapis.com/v1/export?Path={path}"
    print(f"      [INF] dillyapi データ取得開始 : {url}")
    try:
        response = requests.get(url)
        json_data = response.json().get("jsonOutput", {})
        return json_data
    except Exception as e:
        print(f"      [INF] ❌️ 取得失敗: {e}")

async def fetch_export_data_async(session, asset_path):
    path = strip_after_dot(asset_path)
    url = f"https://export-service.dillyapis.com/v1/export?Path={path}"
    print(f"      [INF] dillyapi データ取得開始 : {url}")
    try:
        async with session.get(url) as response:
            if response.status == 200:
                json_data = await response.json()
                return json_data.get("jsonOutput", {})
            else:
                print(f"      [INF] ❌️ 取得失敗: {response.status} - {await response.text()}")
    except Exception as e:
        print(f"      [INF] ❌️ 取得失敗: {e}")
        return {}

def get_image(icon_path, name= "", download = False):
    path = strip_after_dot(icon_path)
    url = f"https://export-service.dillyapis.com/v1/export?Path={path}"
    print(f"      [INF] dillyapi 画像取得開始 : {url}")
    try:
        res = requests.get(url)
        img = Image.open(BytesIO(res.content))
        if not download:
            img = img.convert("RGBA")
            return img
        if download:
            try:
                filename = f"{sanitize_filename(name)}.png"
                img_path = os.path.join(config.weapicon_dir, filename)
                img.save(img_path)
                img = img.convert("RGBA")
                return img
            except Exception as e:
                print(f"      [ERR] ❌️ 保存に失敗 : {e}")
                return None
    except Exception as e:
        print(f"      [ERR] ❌️ 取得失敗 : {e}")
        return None

async def get_image_async(session, icon_path, name= "", download = False):
    path = strip_after_dot(icon_path)
    url = f"https://export-service.dillyapis.com/v1/export?Path={path}"
    print(f"      [INF] dillyapi 画像取得開始 : {url}")

    try:
        async with session.get(url) as res:
            if res.status != 200:
                print(f"      [ERR] ❌️ HTTPエラー: {res.status} {url}")
                return None
            data = await res.read()
            img = Image.open(BytesIO(data))
            img = img.convert("RGBA")

            if download:
                try:
                    filename = f"{sanitize_filename(name)}.png"
                    img_path = os.path.join(config.weapicon_dir, filename)
                    img.save(img_path)
                except Exception as e:
                    print(f"      [ERR] ❌️ 保存に失敗 : {e}")
                    return None
            return img

    except Exception as e:
        print(f"      [ERR] ❌️ 取得失敗 : {e}")
        return None

def get_loc_data(key):
    if key and key != "不明" and key != "なし":
        print (key)
        url = "https://export-service.dillyapis.com/v1/export/localize"
        payload = {
            "culture": "ja",
            "ns": "",
            "values": [
                {
                    "key": f"{key}"
                },
                {
                    "ns": "",
                    "key": ""
                }
            ]
        }
        loc_data = requests.post(url, json=payload)
        if loc_data.status_code == 200:
            data = loc_data.json().get("jsonOutput")[0].get("value")
            return data
        else:
            print (f"[ERR] ❌️ 日本語名の取得失敗 : {loc_data.status_code} {loc_data.text}")

def strip_after_dot(path: str) -> str:
    return path.split('.')[0]