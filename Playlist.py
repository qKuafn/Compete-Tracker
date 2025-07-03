import requests
import json
import time
import os
from datetime import datetime
from typing import List

from get_token import ensure_token, get_token
from files import *
import config
import pub_config as config2

def fetch_Playlist(tags, version, build, playlist_tags):
    new = []
    delete = []
    update = []
    url = f"{config.PlaylistUpd_URL}/{version}/{build}?appId=Fortnite"
    payload = {
        "FortPlaylistAthena": 0
    }
    for attempt in range(2):
        ensure_token()
        headers = {"Authorization": f"{config.token_type} {config.access_token}"}
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            new_data = res.json()
            filepath = os.path.join(config2.RESPONSE_DIR, f"PlaylistData.json")
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                print("[Playlist] ❌️ 旧ファイルの取得に失敗")
            if new_data != before_data or before_data is None:
                current_id_list = extract_asset_ids(new_data)
                before_id_list = extract_asset_ids(before_data)
                
                # 新しいIDを検出・タグ追加
                new_ids = list(set(current_id_list) - set(before_id_list))
                removed_ids = list(set(before_id_list) - set(current_id_list))
                new_ids_tournament = [id for id in new_ids if "Showdown" in id]
                removed_ids_tournament = [id for id in removed_ids if "Showdown" in id]
                if new_ids_tournament:
                    for ids in new_ids_tournament:
                        tags.append(f"{ids} (New)")
                        playlist_tags.append(ids)
                        new.append(ids)
                if removed_ids_tournament:
                    for ids in removed_ids_tournament:
                        tags.append(f"{ids} (Del)")
                        playlist_tags.append(ids)
                        delete.append(ids)
                else:
                    tags.append("Playlist")

                # 変更されたIDを検出
                changed_ids = detect_changed_ids(current_id_list, new_data, before_data)
                changed_ids_tournament = [id for id in changed_ids if "Showdown" in id]
                if changed_ids_tournament and (not new) and (not delete):
                    for ids in changed_ids_tournament:
                        tags.append(f"{ids} (Upd)")
                        playlist_tags.append(ids)
                        update.append(ids)
                # 保存
                try:
                    if config2.test is False:
                        with open(get_unique_filepath(config2.ARCHIVE_DIR, f"PlaylistData"), "w", encoding="utf-8") as f:
                            json.dump(new_data, f, ensure_ascii=False, indent=2)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(new_data, f, ensure_ascii=False, indent=2)
                    print(f"[Playlist] 🟢 更新あり")
                    if changed_ids_tournament:
                        playlist_send_discord_notify(new, delete, update)
                    return True
                except Exception as e:
                    print(f"[Playlist] ❌️ ファイルの保存に失敗 : {e}")
                    return False
            elif new_data == before_data:
                print ("[Playlist] 更新なし")
                return True
            else:
                return False
        else:
            print(f"[Playlist] ❌️ 取得失敗 : {res.status_code}")
            if attempt == 0:
                print("[Playlist] 🔁 リトライ")
                time.sleep(10)
                get_token()
            else:
                return None

# === 更新が入っているPlaylist Id一覧を取得 ===
def extract_asset_ids(data: dict) -> List[str]:
    return list(data.get("FortPlaylistAthena", {}).get("assets", {}).keys())

# === 更新が入っているPlaylist Id一覧を取得 ===
def detect_changed_ids(current_data: List[str], new_data: dict, old_data: dict) -> List[str]:
    updated_ids = []
    current_assets = new_data.get("FortPlaylistAthena", {}).get("assets", {})
    previous_assets = old_data.get("FortPlaylistAthena", {}).get("assets", {})

    # 最新データのプレイリスト毎に、新・旧の meta > promotedAt を比較
    for key in current_data:
        curr = current_assets.get(key, {}).get("meta", {}).get("promotedAt")
        old = previous_assets.get(key, {}).get("meta", {}).get("promotedAt")

        # promotedAtが変わった場合か、どちらかがNoneの場合にタグに追加
        if curr != old and (not curr is None or not old is None):
            updated_ids.append(key)
    return updated_ids

def playlist_send_discord_notify(new, delete, update):
    fields = []
    if new:
        fields.append({
            "name": "🟢 新規追加",
            "value": "\n".join([f"・`{tag}`" for tag in new]),
            "inline": False
        })
    if delete:
        fields.append({
            "name": "🔴 削除",
            "value": "\n".join([f"・`{tag}`" for tag in delete]),
            "inline": False
        })
    if update:
        fields.append({
            "name": "🟡 更新",
            "value": "\n".join([f"・`{tag}`" for tag in update]),
            "inline": False
        })
    payload = {
        "username": "大会のプレイリスト修理",
        "content": "<@&1372839358591139840><@&1359477859764273193>",
        "embeds": [
            {
                "title": "プレイリスト更新 (トーナメント)",
                "fields": fields,
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer":{
                    "text":"FNLive"
                }
            }
        ]
    }
    if config2.Webhook1 is True:
        res = requests.post(config.Tournament_Webhook_URL, json=payload).raise_for_status()
        if res.status_code == 204 or res.status_code == 200:
            print("[Playlist] 🟢 Discord通知成功")
        else:
            print(f"[Playlist] ❌️ Discord通知失敗 : {res.status_code} {res.text}")
    if config2.Webhook2 is True:
        res = requests.post(config2.Tournament_Webhook_URL2, json=payload).raise_for_status()
        if res.status_code == 204 or res.status_code == 200:
            print("[Playlist] 🟢 Discord通知成功")
        else:
            print(f"[Playlist] ❌️ Discord通知失敗 : {res.status_code} {res.text}")