import requests
import json
import time
import os
import subprocess
from datetime import datetime, timezone, timedelta
from config import *
from pub_config import *
from typing import List

# === ファイルパス ===
RESPONSE_DIR = "./response"
ARCHIVE_DIR = "./response/Archive"
TOURNAMENT_DIR = "./Tournament"
TOURNAMENT_ARCHIVE_DIR = "./Tournament/Archive"

Regions = ["ASIA", "EU", "NAC", "NAW", "OCE", "ME", "BR", "ONSITE"]
Lang = ["ja", "en"]

JST = timezone(timedelta(hours=9))
UTC = timezone(timedelta(hours=0))

# === トークン管理 ===
access_token = None
access_token2 = None
last_token_time = 0
last_token_time2 = 0
TOKEN_EXPIRATION = 120 * 60

def get_unique_filepath(base_dir, base_name):
    os.makedirs(base_dir, exist_ok=True)
    date_str = datetime.now(JST).strftime("%m%d")
    counter = 1
    while True:
        path = os.path.join(base_dir, f"{base_name} {date_str}({counter}).json")
        if not os.path.exists(path):
            return path
        counter += 1
        print(f"　　Archiveの作成に成功 : {base_name} {date_str}({counter}).json")

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            print (f"　　jsonファイルの読み込みに成功 : {path}")
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[load_json] ❌️ jsonデコードエラー : {e}")
        return None
    except Exception as e:
        print(f"[load_json] ❌️ json読み込みエラー: {e}")
        return None

# === API1用 ===
def get_token():
    global access_token, token_type, last_token_time
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {AUTH_TOKEN}"
    }
    data = {
        "grant_type": "device_auth",
        "account_id": ACCOUNT_ID,
        "device_id": DEVICE_ID,
        "secret": SECRET,
    }
    try:
        res = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token", headers=headers, data=data)
        res.raise_for_status()
        access_token = res.json().get("access_token")
        print ("　　アカウントトークンの取得に成功")
        token_type = res.json().get("token_type")
        last_token_time = time.time()
    except Exception as e:
        print(f"[get_token] ❌ トークン取得失敗: {e}")
        access_token = None

def ensure_token():
    if access_token is None :
        print ("　　トークンを取得します (新規)")
        get_token()
    if (time.time() - last_token_time) >= TOKEN_EXPIRATION:
        print ("　　トークンを取得します (期限切れ)")
        get_token()

def kill_token():
    global access_token, token_type
    headers = {
        "Authorization": f"{token_type} {access_token}"
    }
    try:
        res = requests.delete(f"https://account-public-service-prod.ol.epicgames.com/account/api/oauth/sessions/kill/{access_token}", headers=headers)
        if res.status_code == 204:
            print ("[kill_token] アカウントトークンの削除に成功")
        else:
            print (f"[kill_token] トークンの削除に失敗: {res.status_code} {res.text}")
    except Exception as e:
        print(f"[kill_token] ❌ トークンの削除に失敗: {e}")
        access_token = None

# === Tournament Data API ===
def fetch_api1(region, tags):
    print (f"　{region} の更新を確認")
    url = f"{TOURNAMENT_URL}?region={region}"
    for attempt in range(2):
        ensure_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            filepath = os.path.join(RESPONSE_DIR, f"EventData_{region}.json")
            new_data = data
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                print("[fetch_API1] ❌️ 旧ファイルの取得に失敗")
            if new_data != before_data or before_data is None:
                try:
                    with open(get_unique_filepath(ARCHIVE_DIR, f"EventData_{region}"), "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    tags.append(region)
                    print(f"　　　🟢 {region} : 更新あり")
                    return True
                except Exception as e:
                    print(f"[fetch_API1] ❌️ ファイルの保存に失敗 : {e}")
                    return False
            elif new_data == before_data:
                print(f"　　更新なし")
                return True
            else:
                return False
        else:
            print(f"[fetch_API1] ❌️ 取得失敗 ({region}) : {res.status_code}")
            if attempt == 0:
                print("[fetch_API1] リトライ")
                get_token()
                time.sleep(10)
            else:
                return None

# === Main Web API ===
def fetch_api2(lang, tags):
    print(f"　{lang} の更新を確認")
    url = f"{WEBAPI_URL}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(RESPONSE_DIR, f"WebData_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("[fetch_API2] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                with open(get_unique_filepath(ARCHIVE_DIR, f"WebData_{lang}"), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tags.append(f"Web ({lang})")
                print(f"　　🟢 更新あり")
            else:
                print(f"　　更新なし")
            return data
        except Exception as e:
            print (f"[fetch_API2] ❌️ ファイルの保存に失敗 : {e}")
    else:
        print(f"[fetch_API2] ❌️ 取得失敗 ({lang}) : {res.status_code}")
        return None

# === ScoringRule Web API ===
def fetch_api3(lang, tags):
    print(f"　{lang} の更新を確認")
    url = f"{WEBAPI_URL2}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(RESPONSE_DIR, f"ScoreInfo_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("[fetch_API3] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                with open(get_unique_filepath(ARCHIVE_DIR, f"ScoreInfo_{lang}"), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tags.append(f"Score ({lang})")
                print(f"　　🟢 更新あり")
            else:
                print(f"　　更新なし")
            return data
        except Exception as e:
            print (f"[fetch_API3] ❌️ ファイルの保存に失敗 : {e}")
    else:
        print(f"[fetch_API3] ❌️ 取得失敗 ({lang}) : {res.status_code}")
        return None

# === Leaderboard Web API ===
def fetch_api4(lang, tags):
    print(f"　{lang} の更新を確認")
    url = f"{WEBAPI_URL3}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(RESPONSE_DIR, f"LeaderboardInfo_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("[fetch_API4] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                with open(get_unique_filepath(ARCHIVE_DIR, f"LeaderboardInfo_{lang}"), "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tags.append(f"Lead ({lang})")
                print(f"　　🟢 更新あり")
            else:
                print(f"　　更新なし")
            return data
        except Exception as e:
            print (f"[fetch_API4] ❌️ ファイルの保存に失敗 : {e}")
    else:
        print(f"[fetch_API4] ❌️ 取得失敗 ({lang}) : {res.status_code}")
        return None

# === Playlistの更新を確認 ===
def fetch_api5(tags, version, build, playlist_tags):
    new = []
    delete = []
    update = []
    url = f"{PlaylistAPI_URL}/{version}/{build}?appId=Fortnite"
    payload = {
        "FortPlaylistAthena": 0
    }
    for attempt in range(2):
        ensure_token()
        headers = {"Authorization": f"Bearer {access_token}"}
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            new_data = res.json()
            filepath = os.path.join(RESPONSE_DIR, f"PlaylistData.json")
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                print("[fetch_API5] ❌️ 旧ファイルの取得に失敗")
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
                    with open(get_unique_filepath(ARCHIVE_DIR, f"PlaylistData"), "w", encoding="utf-8") as f:
                        json.dump(new_data, f, ensure_ascii=False, indent=2)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(new_data, f, ensure_ascii=False, indent=2)
                    print(f"　　🟢 更新あり")
                    playlist_send_discord_notify(new, delete, update)
                    return True
                except Exception as e:
                    print(f"[fetch_API5] ❌️ ファイルの保存に失敗 : {e}")
                    return False
            elif new_data == before_data:
                print ("[Playlist] 更新なし")
                return True
            else:
                return False
        else:
            print(f"[fetch_API5] ❌️ 取得失敗 : {res.status_code}")
            if attempt == 0:
                print("[fetch_API5] 🔁 リトライ")
                get_token()
                time.sleep(10)
            else:
                return None

def extract_asset_ids(data: dict) -> List[str]:
    return list(data.get("FortPlaylistAthena", {}).get("assets", {}).keys())

# === 更新が入っているPlaylist Id一覧を取得 ===
def detect_changed_ids(current_data: List[str], new_data: dict, old_data: dict) -> List[str]:
    updated_ids = []
    current_assets = new_data.get("FortPlaylistAthena", {}).get("assets", {})
    previous_assets = old_data.get("FortPlaylistAthena", {}).get("assets", {})

    for key in current_data:
        curr = current_assets.get(key, {}).get("meta", {}).get("promotedAt")
        old = previous_assets.get(key, {}).get("meta", {}).get("promotedAt")

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
            "name": "🔴 削除済み",
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
        "content": "<@&1372839358591139840><@&1359477859764273193>",
        "embeds": [
            {
                "title": "プレイリスト更新 (トーナメント)",
                "fields": fields,
                "timestamp": datetime.now(UTC).isoformat()
            }
        ]
    }
    if Webhook1 is True:
        try:
            requests.post(Tournament_Webhook_URL, json=payload).raise_for_status()
        except Exception as e:
            print (f"[playlist_send] ❌️ Discord通知失敗 : {e}")
    if Webhook2 is True:
        try:
            requests.post(Tournament_Webhook_URL2, json=payload).raise_for_status()
        except Exception as e:
            print (f"[playlist_send] ❌️ Discord通知失敗 : {e}")

# === TournamentData ===
def get_token_extract():
    global access_token2, last_token_time2
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {AUTH_TOKEN}"
    }
    data = {
        "grant_type": "device_auth",
        "account_id": SECOND_ACCOUNT_ID,
        "device_id": SECOND_DEVICE_ID,
        "secret": SECOND_SECRET,
    }
    try:
        res = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token", headers=headers, data=data)
        res.raise_for_status()
        access_token2 = res.json().get("access_token")
        last_token_time2 = time.time()
    except Exception as e:
        print(f"❌ トークン取得失敗: {e}")
        access_token2 = None

def ensure_token_extract():
    if access_token2 is None or (time.time() - last_token_time) >= TOKEN_EXPIRATION:
        get_token_extract()

def fetch_api1_extract():
    url = f"{TOURNAMENT_URL2}?region=ASIA"
    for attempt in range(2):
        ensure_token_extract()
        headers = {"Authorization": f"Bearer {access_token2}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            return data
        else:
            print(f"[API1 extract用] ❌️ 取得失敗 : {res.status_code} {res.text}")
            if attempt == 0:
                print("[API1 extract用] リトライ")
                get_token_extract()
                time.sleep(10)
            else:
                return None

def fetch_api2_extract(lang):
    url = f"{WEBAPI_URL}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        return data
    else:
        print(f"[API2 extract用] ❌️ 取得失敗 ({lang}) : {res.status_code}")
        return None

def extract_tournament_data(tags, added_Tournaments, updated_Tournaments):
    print ("[Tournament] 大会のデータ更新の確認を開始")

    JST = timezone(timedelta(hours=9))
    event_data = fetch_api1_extract()
    webapi_ja = fetch_api2_extract("ja")
    webapi_en = fetch_api2_extract("en")
    sent = set()
    updated_Tournaments = []
    added_Tournaments = []
    embeds=[]

    templates = {t["eventTemplateId"]: t for t in event_data.get("templates", []) if "eventTemplateId" in t}
    payouts_by_key = {}
    for k, entries in event_data.get("payoutTables", {}).items():
        for entry in entries:
            for rank in entry.get("ranks", []):
                for payout in rank.get("payouts", []):
                    payouts_by_key.setdefault(k, []).append({
                        "threshold": rank.get("threshold"),
                        "rewardType": payout.get("rewardType"),
                        "quantity": payout.get("quantity", 1),
                        "value": payout.get("value")
                    })
    score_map = {
        k.split(":")[2]: v for k, v in event_data.get("scoreLocationPayoutTables", {}).items()
        if len(k.split(":")) == 3
    }
    def build_webapi_lookup(api_data):
        lookup = {}
        for v in api_data.values():
            if isinstance(v, dict):
                info = v.get("tournament_info", {})
                if "tournament_display_id" in info:
                    lookup[info["tournament_display_id"].lower()] = info
        return lookup

    lookup_ja = build_webapi_lookup(webapi_ja)
    lookup_en = build_webapi_lookup(webapi_en)

    for e in event_data["events"]:
        metadata = e.get("metadata", {})
        windows = e.get("eventWindows", [])
        windows_to_display = windows[:2] if len(windows) > 1 else windows
        display_id = e.get("displayDataId", "").lower()
        webinfo = lookup_ja.get(display_id) or lookup_en.get(display_id) or {}
        title = webinfo.get("long_format_title", e.get("eventId"))

        if display_id in sent:
            continue

        result = {
            title: {
                "displayDataId": display_id,
                "metadata": metadata,
                "loading_screen_image": webinfo.get("loading_screen_image"),
                "playlist_tile_image": webinfo.get("playlist_tile_image"),
                "poster_front_image": webinfo.get("poster_front_image"),
                "tournament_view_background_image": webinfo.get("tournament_view_background_image")
            }
        }

        for w in windows:
            window_id = w["eventWindowId"]
            begin_dt = datetime.strptime(w["beginTime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(w["endTime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            template = templates.get(w.get("eventTemplateId", ""), {})

            entry = {
                "beginTime": w["beginTime"],
                "beginTime_UNIX": int(begin_dt.timestamp()),
                "beginTime_JST": begin_dt.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S"),
                "endTime": w["endTime"],
                "endTime_UNIX": int(end_dt.timestamp()),
                "endTime_JST": end_dt.astimezone(JST).strftime("%Y-%m-%d %H:%M:%S"),
                "playlistId": template.get("playlistId"),
                "matchCap": template.get("matchCap"),
                "additionalRequirements": w.get("additionalRequirements", []),
                "requireAllTokens": w.get("requireAllTokens", []),
                "requireAnyTokens": w.get("requireAnyTokens", []),
                "requireNoneTokensCaller": w.get("requireNoneTokensCaller", []),
                "requireAllTokensCaller": w.get("requireAllTokensCaller", []),
                "requireAnyTokensCaller": w.get("requireAnyTokensCaller", []),
            }

            key = score_map.get(window_id)
            if key in payouts_by_key:
                entry["payouts"] = payouts_by_key[key]

            result[title].setdefault(window_id, []).append(entry)

        # === ファイルの比較 & 保存 ===
        filepath = os.path.join(TOURNAMENT_DIR, f"{display_id}.json")
        new_data = [result]
        before_data = load_json(filepath) if os.path.exists(filepath) else None

        # === とりあえずDiscordに送信できる状態に ===
        date_section = []
        try:
            for w in windows_to_display:
                begin = int(datetime.strptime(w['beginTime'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())
                end = int(datetime.strptime(w['endTime'], '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=timezone.utc).timestamp())
                date_section.append({
                    "name":  w['eventWindowId'],
                    "value": f"<t:{begin}:F>\n～<t:{end}:F>",
                    "inline": True
                })
            embed_date = {
                "title":  "📅 **開催日時**",
                "fields": date_section,\
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            print (f"[Tournament] 🔴エラー：開催日時の組み立て中 {e}")
            date_section = "エラー"
            embed_date = {
                "title":  "📅 **開催日時**",
                "fields": date_section,
                "timestamp": datetime.now(UTC).isoformat()
            }

        mode_section = []
        try:
            for w in windows_to_display:
                playlist = templates.get(w.get('eventTemplateId',''),{}).get('playlistId','Unknown')
                mode_section.append({
                    "name":  w['eventWindowId'],
                    "value": f"`{playlist}`",
                    "inline": True
                })
            embed_mode = {
                "title":  "📍 **モード**",
                "fields": mode_section,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            print (f"[Tournament] 🔴エラー：モードの組み立て中 {e}")
            mode_section = "エラー"
            embed_mode = {
                "title":  "📍 **モード**",
                "fields": mode_section,
                "timestamp": datetime.now(UTC).isoformat()
            }

        match_section = []
        try:
            for w in windows_to_display:
                match_cap = templates.get(w.get('eventTemplateId',''), {}).get('matchCap','Unknown')
                match_section.append({
                    "name":  w['eventWindowId'],
                    "value": str(match_cap),
                    "inline": True
                })
            embed_match = {
                "title":  "⚔️ **試合数**",
                "fields": match_section,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            print (f"[Tournament] 🔴エラー：試合数の組み立て中 {e}")
            match_section = "エラー"
            embed_match = {
                "title":  "⚔️ **試合数**",
                "fields": match_section,
                "timestamp": datetime.now(UTC).isoformat()
            }

        token_section = []
        try:
            for w in windows_to_display:
                eligibility = {
                    "metadata":             metadata,
                    "additionalRequirements":  w.get("additionalRequirements", []),
                    "requireAllTokens":       w.get("requireAllTokens", []),
                    "requireAnyTokens":       w.get("requireAnyTokens", []),
                    "requireNoneTokensCaller": w.get("requireNoneTokensCaller", []),
                    "requireAllTokensCaller":  w.get("requireAllTokensCaller", []),
                    "requireAnyTokensCaller":  w.get("requireAnyTokensCaller", []),
                }
                token_section.append({
                    "name":  w['eventWindowId'],
                    "value": f"```json\n{json.dumps(eligibility, ensure_ascii=False, indent=2)}\n```",
                    "inline": False
                })
            embed_token = {
                "title":  "🔑 **参加資格**",
                "fields": token_section,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            print (f"[Tournament] 🔴エラー：参加資格の組み立て中 {e}")
            token_section = "エラー"
            embed_token = {
                "title":  "🔑 **参加資格**",
                "fields": token_section,
                "timestamp": datetime.now(UTC).isoformat()
            }

        payouts_section = []
        try:
            for w in windows_to_display:
                key = score_map.get(w["eventWindowId"])
                payouts_list = payouts_by_key.get(key, [])
                payouts_section.append({
                    "name":  w['eventWindowId'],
                    "value": f"```json\n{json.dumps(payouts_list, ensure_ascii=False, indent=2)}\n```",
                    "inline": False
                })
            embed_payout = {
                "title":  "🎁 **賞金 / 賞品**",
                "fields": payouts_section,
                "timestamp": datetime.now(UTC).isoformat()
            }
        except Exception as e:
            print (f"[Tournament] 🔴エラー：賞金の組み立て中 {e}")
            payouts_section = "エラー"
            embed_payout = {
                "title":  "🎁 **賞金 / 賞品**",
                "fields": payouts_section,
                "timestamp": datetime.now(UTC).isoformat()
            }

        try:
            images_section = (
                "🖼️ **画像URL一覧**\n"
                f"- Poster    ：{webinfo.get('poster_front_image','未設定')}\n"
                f"- Background：{webinfo.get('tournament_view_background_image','未設定')}\n"
                f"- Playlist  ：{webinfo.get('playlist_tile_image','未設定')}\n"
                f"- Loading   ：{webinfo.get('loading_screen_image','未設定')}\n"
                f"- Square    ：{webinfo.get('square_poster_image','未設定')}"
            )
        except Exception as e:
            print (f"[Tournament] 🔴エラー：画像URLの組み立て中 {e}")
            images_section = "エラー"


        # === 変更箇所を確認 ===
        ignore_keys = {"beginTime", "endTime", "beginTime_UNIX", "endTime_UNIX"}
        title_key   = list(new_data[0].keys())[0]
        before_root = before_data[0].get(title_key, {}) if before_data else {}
        after_root  = new_data[0][title_key]
        diffs       = find_diffs(before_root, after_root, title_key)
        diffs = filter_diffs(diffs, ignore_keys)
        diffs = shorten_diff_paths(diffs, max_depth=2)
        path        = get_value_by_path(before_data, new_data, diffs)

        # === 保存 & タグ追加 ===
        if before_data is None:
            print(f"　　　🟢 新トーナメント : {display_id}")
            with open(get_unique_filepath(TOURNAMENT_ARCHIVE_DIR, f"{display_id}"), "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            tags.append(f"{display_id} (New)")
            added_Tournaments.append(display_id)

        elif new_data != before_data:
            print(f"　　　🟢 トーナメント更新 : {display_id}")
            with open(get_unique_filepath(TOURNAMENT_ARCHIVE_DIR, f"{display_id}"), "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            tags.append(f"{display_id} (Upd)")
            updated_Tournaments.append(display_id)

        else:
            print(f"　　　更新なし : {display_id}")

        # === 送信準備 ===
        embeds = [embed_date, embed_mode, embed_match, embed_token, embed_payout]

        status = f"## 🆕 新トーナメント : {title}" if before_data is None else f"## 🔄 トーナメント更新 : {title}"

        if before_data is None:
            content = (
                f"<@&1372839358591139840><@&1359477859764273193>\n"
                f"{status}\n_ _\n"
                f"{images_section}\n\n"
            )
            with open(filepath, "rb") as fp:
                files = {"file": (os.path.basename(filepath), fp, "application/json")}
                if Webhook1 is True:
                    try:
                        requests.post(
                            Tournament_Webhook_URL,
                            data={"payload_json": json.dumps({"content": content, "embeds": embeds}, ensure_ascii=False)},
                            files=files
                        ).raise_for_status()
                    except Exception as e:
                        print (f"[Tournament] 🔴エラー：新TournamentのDiscord送信 {e}")
                time.sleep(2)
                if Webhook2 is True:
                    try:
                        requests.post(
                            Tournament_Webhook_URL2,
                            data={"payload_json": json.dumps({"content": content, "embeds": embeds}, ensure_ascii=False)},
                            files=files
                        ).raise_for_status()
                    except Exception as e:
                        print (f"[Tournament] 🔴エラー：新TournamentのDiscord送信 {e}")
            sent.add(display_id)

        elif new_data != before_data:
            embeds = []
            for path_str, values in path.items():
                changes_section = []
                new_path  = path_str.split("/", 1)[1] if "/" in path_str else path_str

                old_val = values.get("old", "不明")
                new_val = values.get("new", "不明")

                def format_value(val):
                    if isinstance(val, (dict, list)):
                        return f"```json\n{json.dumps(val, ensure_ascii=False, indent=2)}\n```"
                    return f"```{val}```"
                
                if len(embeds) < 8:
                    changes_section.append({
                        "name": "過去データ" ,
                        "value": format_value(old_val),
                        "inline": not isinstance(old_val, (dict, list))
                    })
                    changes_section.append({
                        "name": "新データ" ,
                        "value": format_value(new_val),
                        "inline": not isinstance(new_val, (dict, list))
                    })
                    embed_changes = {
                        "title": new_path,
                        "fields": changes_section,
                        "timestamp": datetime.now(UTC).isoformat()
                    }
                    embeds.append (embed_changes)

            content = (
                f"<@&1372839358591139840><@&1359477859764273193>\n"
                f"{status}\n_ _\n"
                f"{images_section}\n\n"
            )

            with open(filepath, "rb") as fp:
                files = {"file": (os.path.basename(filepath), fp, "application/json")}
                if Webhook1 is True:
                    try:
                        requests.post(
                            Tournament_Webhook_URL,
                            data={"payload_json": json.dumps({"content": content, "embeds": embeds}, ensure_ascii=False)},
                            files=files
                        ).raise_for_status()
                    except Exception as e:
                        print (f"[Tournament] 🔴エラー：Tournament更新のDiscord送信 {e}")
                time.sleep(2)
                if Webhook2 is True:
                    try:
                        requests.post(
                            Tournament_Webhook_URL2,
                            data={"payload_json": json.dumps({"content": content, "embeds": embeds}, ensure_ascii=False)},
                            files=files
                        ).raise_for_status()
                    except Exception as e:
                        print (f"[Tournament] 🔴エラー：Tournament更新のDiscord送信 {e}")
            sent.add(display_id)

def find_diffs(old, new, path=""):
    diffs = []
    try:
        if isinstance(old, dict) and isinstance(new, dict):
            for key in set(old) & set(new):
                subpath = f"{path}/{key}" if path else key
                diffs += find_diffs(old[key], new[key], subpath)
        elif isinstance(old, list) and isinstance(new, list):
            for i, (o, n) in enumerate(zip(old, new)):
                subpath = f"{path}"
                diffs += find_diffs(o, n, subpath)
            if len(old) != len(new):
                display_path = path or "root"
                diffs.append(f"{display_path}")
        else:
            if old != new:
                diffs.append(path)
    except Exception as e:
        print (f"[Tournament] 🔴エラー：更新の確認中 {path} - {e}")
    return diffs

def filter_diffs(diffs, ignore_keys):
    filtered = []
    try:
        for d in diffs:
            if not any(d.endswith(k) for k in ignore_keys):
                filtered.append(d)
    except Exception as e:
        print (f"[Tournament] 🔴エラー：UNIX,UTCの除外中 {ignore_keys} - {e}")
    return filtered

def shorten_diff_paths(diffs, max_depth=2):
    result = set()
    try:
        for path in diffs:
            parts = path.split(" > ")
            if len(parts) <= max_depth:
                result.add(path)
            else:
                result.add(" > ".join(parts[:max_depth + 1]))
    except Exception as e:
        print (f"[Tournament] 🔴エラー：パスの修正中 {diffs} - {e}")
    return sorted(result)

def get_value_by_path(before_data, new_data, diffs):
    def get_nested_value(data, path_str):
        try:
            keys = path_str.split(' > ')
            for key in keys:
                if isinstance(data, list):
                    data = data[0]
                data = data[key]
            return data
        except (KeyError, IndexError, TypeError) as e:
            print (f"[Tournament] 🔴エラー：末端のパスの値の確認中 {diffs} - {e}")

    results = {}
    for path_str in diffs:
        old_value = get_nested_value(before_data, path_str)
        new_value = get_nested_value(new_data, path_str)
        results[path_str] = {
            "old": old_value,
            "new": new_value
        }

    return results

# === 実行 ===
if __name__ == "__main__":
    tags = []
    updated_regions = []
    playlist_tags = []
    added_Tournaments = []
    updated_Tournaments = []

    print("🚀 開始")

    result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
    is_clean = result.returncode == 0 and result.stdout.strip() == ''

    if is_clean:
        subprocess.run(['git', 'pull'])
    else:
        subprocess.run(['git', 'stash'])
        subprocess.run(['git', 'pull'])
        subprocess.run(['git', 'stash', 'pop'])
    
    extract_tournament_data(tags, added_Tournaments, updated_Tournaments)
    print("=" * 20)

    print("[fetch_API1] EventData の取得を開始")
    for region in Regions:
        fetch_api1(region, tags)
    print("=" * 20)

    print("[fetch_API2] Web Data の取得を開始")
    for lang in Lang:
        fetch_api2(lang, tags)
    print("=" * 20)
    

    print("[fetch_API3] Score Info の取得を開始")
    for lang in Lang:
        fetch_api3(lang, tags)
    print("=" * 20)

    print("[fetch_API4] Leaderboard Info の取得を開始")
    for lang in Lang:
        fetch_api4(lang, tags)
    print("=" * 20)

    print("[fetch_API5] Playlist Data の取得を開始")
    fetch_api5(tags, version, build, playlist_tags)
    print("=" * 20)

    subprocess.run(["git", "add", "."], check=True)
    git_diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    should_push = git_diff.returncode != 0
    if should_push is True:
        print(f"[DEBUG] 🟢 should_push = {should_push}🟢")
    else:
        print(f"[DEBUG] should_push = {should_push}")

    if should_push:
        if not tags:
            tags.append("ファイル関連")

        print(f"[DEBUG] タグ一覧 : {tags}")

        timestampA = datetime.now(JST).strftime("%m-%d %H:%M:%S")
        message = f"更新 : {', '.join(tags)} ({timestampA}) - GitHubActions"

        subprocess.run(["git", "commit", "-m", message], check=True)
        subprocess.run(["git", "push"], check=True)

        commit_hash = subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True
        ).strip()

        repo_url = subprocess.check_output(
            ["git", "config", "--get", "remote.origin.url"], text=True
        ).strip()

        if repo_url.startswith("git@"):
            # git@github.com:owner/repo.git → [https://github.com/owner/repo](https://github.com/owner/repo)
            repo_url = repo_url.replace("git@github.com:", "[https://github.com/](https://github.com/)") \
                .removesuffix(".git")
        else:
            # https://…/repo.git → https://…/repo
            repo_url = repo_url.removesuffix(".git")

        commit_url = f"{repo_url}/commit/{commit_hash}"
        user_name = subprocess.check_output(
            ["git", "config", "user.name"], text=True
        ).strip()

        if "ASIA" in tags or any(tag.endswith("(ja)") for tag in tags) in tags or added_Tournaments or updated_Tournaments or playlist_tags:
            content = f"## 🆕 : {', '.join(tags)} <@&1372839358591139840>"
        else:
            content = f"## 更新 : {', '.join(tags)}"

        payload = {
            "username": "GitHub",
            "content": f"{content}",
            "embeds": [
                {
                    "author":{
                        "name": user_name,
                        "icon_url": f"https://github.com/{user_name}.png",
                        "url": f"https://github.com/{user_name}?tab=repositories"
                    },
                    "title": "[Tournament:main] 1 new commit",
                    "url": commit_url,
                    "description": f"[`{commit_hash}`]({commit_url}) {message}",
                    "color": 0x7289da
                }
            ]
        }

        try:
            requests.post(WEBHOOK_URL, json=payload).raise_for_status()
            print("[Discord] 通知を送信")
        except Exception as e:
            print (f"Discord通知失敗 : {e}")
    
    kill_token()
