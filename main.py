import requests
import json
import time
import os
import subprocess
from datetime import datetime, timezone, timedelta
from typing import List

from get_token import ensure_token, get_token, get_token_for_format, ensure_token_for_format
import config
import pub_config as config2

# === ファイルパス ===
RESPONSE_DIR = "./response"
ARCHIVE_DIR = "./response/Archive"
TOURNAMENT_DIR = "./Tournament"
TOURNAMENT_ARCHIVE_DIR = "./Tournament/Archive"

Regions = ["ASIA", "EU", "NAC", "NAW", "OCE", "ME", "BR", "ONSITE"]
Lang = ["ja", "en"]

JST = timezone(timedelta(hours=9))
UTC = timezone(timedelta(hours=0))

if config2.test is True:
    config2.Webhook1 = False

# === アーカイブ用の保存先(名前)を指定 ===
def get_unique_filepath(base_dir, base_name):
    os.makedirs(base_dir, exist_ok=True)
    date_str = datetime.now(JST).strftime("%m%d")
    counter = 1
    while True:
        path = os.path.join(base_dir, f"{base_name} {date_str}({counter}).json")
        if not os.path.exists(path):
            return path
        counter += 1

def load_json(path):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as e:
        print(f"[load_json] ❌️ jsonデコードエラー : {e}")
        return None
    except Exception as e:
        print(f"[load_json] ❌️ json読み込みエラー: {e}")
        return None

# === Event Data API ===
def fetch_EventData(region, tags):
    url = f"{config.TOURNAMENT_URL}?region={region}"
    for attempt in range(2):
        ensure_token()
        headers = {"Authorization": f"{config.token_type} {config.access_token}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            data = res.json()
            filepath = os.path.join(RESPONSE_DIR, f"EventData_{region}.json")
            new_data = data
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                print("[EventData] ❌️ 旧ファイルの取得に失敗")
            if new_data != before_data or before_data is None:
                try:
                    if config2.test is False:
                        with open(get_unique_filepath(ARCHIVE_DIR, f"EventData_{region}"), "w", encoding="utf-8") as f:
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

# === Main Web API ===
def fetch_WebData(lang, tags):
    url = f"{config.WEBAPI_URL}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(RESPONSE_DIR, f"WebData_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("[WebData] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                if config2.test is False:
                    with open(get_unique_filepath(ARCHIVE_DIR, f"WebData_{lang}"), "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tags.append(f"Web ({lang})")
                print(f"[WebData] 🟢 {lang} : 更新あり")
            else:
                print(f"[WebData] {lang} : 更新なし")
            return data
        except Exception as e:
            print (f"[WebData] ファイルの保存に失敗 : {e}")
    else:
        print(f"[WebData] ❌️ 取得失敗 ({lang}) : {res.status_code}")
        return None

# === ScoringRule Web API ===
def fetch_ScoreInfo(lang, tags):
    url = f"{config.WEBAPI_URL2}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(RESPONSE_DIR, f"ScoreInfo_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("[ScoreInfo] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                if config2.test is False:
                    with open(get_unique_filepath(ARCHIVE_DIR, f"ScoreInfo_{lang}"), "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tags.append(f"Score ({lang})")
                print(f"[ScoreInfo] 🟢 {lang} : 更新あり")
            else:
                print(f"[ScoreInfo] {lang} : 更新なし")
            return data
        except Exception as e:
            print (f"[ScoreInfo] ファイルの保存に失敗 : {e}")
    else:
        print(f"[ScoreInfo] ❌️ 取得失敗 ({lang}) : {res.status_code}")
        return None

# === Leaderboard Web API ===
def fetch_LeadInfo(lang, tags):
    url = f"{config.WEBAPI_URL3}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(RESPONSE_DIR, f"LeaderboardInfo_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("[LeadInfo] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                if config2.test is False:
                    with open(get_unique_filepath(ARCHIVE_DIR, f"LeaderboardInfo_{lang}"), "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                tags.append(f"Lead ({lang})")
                print(f"[LeadInfo] 🟢 {lang} : 更新あり")
            else:
                print(f"[LeadInfo] {lang} : 更新なし")
            return data
        except Exception as e:
            print (f"[LeadInfo] ファイルの保存に失敗 : {e}")
    else:
        print(f"[LeadInfo] ❌️ 取得失敗 ({lang}) : {res.status_code}")
        return None

# === Playlist API ===
def fetch_Playlist(tags, version, build, playlist_tags):
    new = []
    delete = []
    update = []
    url = f"{config.PlaylistAPI_URL}/{version}/{build}?appId=Fortnite"
    payload = {
        "FortPlaylistAthena": 0
    }
    for attempt in range(2):
        ensure_token()
        headers = {"Authorization": f"{config.token_type} {config.access_token}"}
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            new_data = res.json()
            filepath = os.path.join(RESPONSE_DIR, f"PlaylistData.json")
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
                        with open(get_unique_filepath(ARCHIVE_DIR, f"PlaylistData"), "w", encoding="utf-8") as f:
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
            print(f"[Playlist] ❌️ 取得失敗 ({region}) : {res.status_code}")
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
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
            }
        ]
    }
    if config2.Webhook1 is True:
        try:
            requests.post(config.Tournament_Webhook_URL, json=payload).raise_for_status()
        except Exception as e:
            print (f"[Playlist] ❌️ Discord通知失敗 : {e}")
    if config2.Webhook2 is True:
        try:
            requests.post(config.Tournament_Webhook_URL2, json=payload).raise_for_status()
        except Exception as e:
            print (f"[Playlist] ❌️ Discord通知失敗 : {e}")

# === Eventの更新を詳しく確認 & 整形Jsonを保存 ===
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

def fetch_WebData_for_format(lang):
    url = f"{config.WEBAPI_URL}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        return data
    else:
        print(f"[WebData2] ❌️ 取得失敗 ({lang}) : {res.status_code}")
        return None

def format_EventData(tags, added_Tournaments, updated_Tournaments):

    JST = timezone(timedelta(hours=9))
    event_data = fetch_EventData_for_format()
    webapi_ja = fetch_WebData_for_format("ja")
    webapi_en = fetch_WebData_for_format("en")
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
                "fields": date_section,
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
            }
        except Exception as e:
            print (f"[format_EventData] 🔴 エラー：開催日時の組み立て中 {e}")
            date_section = "エラー"
            embed_date = {
                "title":  "📅 **開催日時**",
                "fields": date_section,
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
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
                "fields": mode_section
            }
        except Exception as e:
            print (f"[format_EventData] 🔴 エラー：モードの組み立て中 {e}")
            mode_section = "エラー"
            embed_mode = {
                "title":  "📍 **モード**",
                "fields": mode_section,
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
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
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
            }
        except Exception as e:
            print (f"[format_EventData] 🔴 エラー：試合数の組み立て中 {e}")
            match_section = "エラー"
            embed_match = {
                "title":  "⚔️ **試合数**",
                "fields": match_section,
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
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
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
            }
        except Exception as e:
            print (f"[format_EventData] 🔴 エラー：参加資格の組み立て中 {e}")
            token_section = "エラー"
            embed_token = {
                "title":  "🔑 **参加資格**",
                "fields": token_section,
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
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
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
            }
        except Exception as e:
            print (f"[format_EventData] 🔴 エラー：賞金の組み立て中 {e}")
            payouts_section = "エラー"
            embed_payout = {
                "title":  "🎁 **賞金 / 賞品**",
                "fields": payouts_section,
                "timestamp": datetime.now(UTC).isoformat(),
                "footer":"FNLive"
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
            print (f"[format_EventData] 🔴 エラー：画像URLの組み立て中 {e}")
            images_section = "エラー"


        # === 変更箇所を確認 ===
        ignore_keys = {"beginTime", "endTime", "beginTime_UNIX", "endTime_UNIX"}
        title_key   = list(new_data[0].keys())[0]
        before_root = before_data[0].get(title_key, {}) if before_data else {}
        after_root  = new_data[0][title_key]
        if before_data != new_data:
            diffs       = find_diffs(before_root, after_root, title_key)
            diffs       = filter_diffs(diffs, ignore_keys)
            path        = get_value_by_path(before_data, new_data, diffs)

        # === 保存 & タグ追加 ===
        if before_data is None:
            print(f"[format_EventData] 🟢 新トーナメント : {display_id}")
            if config2.test is False:
                with open(get_unique_filepath(TOURNAMENT_ARCHIVE_DIR, f"{display_id}"), "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            tags.append(f"{display_id} (New)")
            added_Tournaments.append(display_id)

        elif new_data != before_data:
            print(f"[format_EventData] 🟢 トーナメント更新 : {display_id}")
            if config2.test is False:
                with open(get_unique_filepath(TOURNAMENT_ARCHIVE_DIR, f"{display_id}"), "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            tags.append(f"{display_id} (Upd)")
            updated_Tournaments.append(display_id)

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
                if config2.Webhook1 is True:
                    try:
                        requests.post(
                            config.Tournament_Webhook_URL,data= {"payload_json": json.dumps({"content": content, "embeds": embeds}, ensure_ascii=False)} ,files=files
                            ).raise_for_status()
                    except Exception as e:
                        print (f"[format_EventData] 🔴 エラー：新TournamentのDiscord送信 {e}")
                time.sleep(2)
                if config2.Webhook2 is True:
                    try:
                        requests.post(
                            config.Tournament_Webhook_URL2,
                            data={"payload_json": json.dumps({"content": content, "embeds": embeds}, ensure_ascii=False)},
                            files=files
                        ).raise_for_status()
                    except Exception as e:
                        print (f"[format_EventData] 🔴 エラー：新TournamentのDiscord送信 {e}")
                        print (embeds)
            sent.add(display_id)

        elif new_data != before_data:
            embeds = []
            for path_str, values in path.items():
                display_path = path_str.replace(" > A", "")
                changes_section = []
                new_path  = display_path.split(" > ", 1)[1] if " > " in display_path else display_path

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
                        "timestamp": datetime.now(UTC).isoformat(),
                        "footer":"FNLive"
                    }
                    embeds.append (embed_changes)

            content = (
                f"<@&1372839358591139840><@&1359477859764273193>\n"
                f"{status}\n_ _\n"
                f"{images_section}\n\n"
            )

            payload = {
                "content": content,
                "embeds": embeds
            }

            with open(filepath, "rb") as fp:
                files = {"file": (os.path.basename(filepath), fp, "application/json")}
                if config2.Webhook1 is True:
                    try:
                        requests.post(
                            config.Tournament_Webhook_URL,
                            data={"payload_json": json.dumps(payload, ensure_ascii=False)},
                            files=files
                        ).raise_for_status()
                    except Exception as e:
                        print (f"[format_EventData] 🔴 エラー：Tournament更新のDiscord送信 {e}")
                time.sleep(2)
                if config2.Webhook2 is True:
                    try:
                        requests.post(
                            config.Tournament_Webhook_URL2,
                            data={"payload_json": json.dumps(payload, ensure_ascii=False)},
                            files=files
                        ).raise_for_status()
                    except Exception as e:
                        print (f"[format_EventData] 🔴 エラー：Tournament更新のDiscord送信 {e}")
                        print (embeds)
            sent.add(display_id)

    if not added_Tournaments and not updated_Tournaments:
        print("[format_EventData] 更新なし")

def find_diffs(old, new, path=""):
    diffs = []
    try:
        if isinstance(old, list) and isinstance(new, list):
            length = max(len(old), len(new))
            for i in range(length):
                o = old[i] if i < len(old) else None
                n = new[i] if i < len(new) else None

                if len(old) == 1 and len(new) == 1:
                    subpath = f"{path} > A" if path else "A"
                else:
                    subpath = f"{path} > {i}" if path else str(i)

                sub_diffs = find_diffs(o, n, subpath)
                if sub_diffs:
                    diffs += sub_diffs

        elif isinstance(old, dict) and isinstance(new, dict):
            all_keys = set(old.keys()) | set(new.keys())
            for key in all_keys:
                o = old.get(key)
                n = new.get(key)
                subpath = f"{path} > {key}" if path else key
                sub_diffs = find_diffs(o, n, subpath)
                if sub_diffs:
                    diffs += sub_diffs

            if len(old) != len(new):
                display_path = path or "root"
                diffs.append(f"{display_path}")

        elif old != new:
                print(f"[find_diffs] ❗ 差分検出: {path} | old={old} → new={new}")
                diffs.append(path)

        return diffs
    except Exception as e:
        print(f"[find_diffs] 🔴 エラー：更新の確認中 {path} - {e}")
        return None

def filter_diffs(diffs, ignore_keys):
    filtered = []
    try:
        for d in diffs:
            if not any(d.endswith(k) for k in ignore_keys):
                filtered.append(d)
        shortened = shorten_diff_paths(filtered)
        return shortened
    except Exception as e:
        print(f"[filter_diffs] 🔴 エラー：UNIX,UTCの除外中 {ignore_keys} - {e}")
        return None

def shorten_diff_paths(diffs, max_depth=5):
    result = set()
    try:
        for path in diffs:
            parts = path.split(" > ")
            
            cutoff_index = None
            for i, part in enumerate(parts):
                if part.isdigit():
                    cutoff_index = i
                    break
            
            if cutoff_index is not None:
                shortened = " > ".join(parts[:cutoff_index + 1])
            else:
                if len(parts) <= max_depth:
                    shortened = " > ".join(parts)
                else:
                    shortened = " > ".join(parts[:max_depth])
            
            result.add(shortened)
    except Exception as e:
        print(f"[shorten_diff_paths] 🔴 エラー：パスの修正中 {diffs} - {e}")
    result_list = sorted(result)
    return result_list

def get_value_by_path(before_data, new_data, diffs):
    use_diffs = [f"0 > {d}" for d in diffs]
    if use_diffs:
        def get_nested_value(data, path_str):
            try:
                keys = path_str.split(' > ')
                for i, key in enumerate(keys):
                    if isinstance(data, list):
                        if key == "A":
                            idx = 0
                        elif key.isdigit():
                            idx = int(key)
                        else:
                            return None
                        data = data[idx]
                    elif isinstance(data, dict):
                        data = data[key]
                return data
            except Exception as e:
                print(f"[get_value_by_path] 🔴 エラー：末端のパスの値の確認中 {use_diffs} - {e}")
                return None

        results = {}
        for path_str in use_diffs:
            old_value = get_nested_value(before_data, path_str)
            new_value = get_nested_value(new_data, path_str)
            results[path_str] = {
                "old": old_value,
                "new": new_value
            }
        return results


# === 実行 ===
if __name__ == "__main__":
    ensure_token()
    ensure_token_for_format()
    while True:
        tags = []
        updated_regions = []
        playlist_tags = []
        added_Tournaments = []
        updated_Tournaments = []

        print("🚀 開始")

        if not config2.test:
            result = subprocess.run(['git', 'status', '--porcelain'], capture_output=True, text=True)
            is_clean = result.returncode == 0 and result.stdout.strip() == ''

            if is_clean:
                subprocess.run(['git', 'pull'])
            else:
                subprocess.run(['git', 'stash'])
                subprocess.run(['git', 'pull'])
                subprocess.run(['git', 'stash', 'pop'])
        
        format_EventData(tags, added_Tournaments, updated_Tournaments)

        for region in Regions:
            if fetch_EventData(region, tags):
                updated_regions.append(region)

        if not updated_regions:
            print("[EventData] 更新なし")

        for lang in Lang:
            fetch_WebData(lang, tags)
        for lang in Lang:
            fetch_ScoreInfo(lang, tags)
        for lang in Lang:
            fetch_LeadInfo(lang, tags)

        fetch_Playlist(tags, config2.version, config2.build, playlist_tags)

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

            if not config2.test:
                timestampA = datetime.now(JST).strftime("%m-%d %H:%M:%S")
                message = f"更新 : {', '.join(tags)} ({timestampA})"

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
                    content = f"## 更新 : {', '.join(tags)} <@&1372839358591139840>"
                else:
                    content = f"## 更新 : {', '.join(tags)}"

                payload = {
                    "username": "GitHub",
                    "content": content,
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
                            "color": 0x7289da,
                        }
                    ]
                }

                try:
                    requests.post(config.WEBHOOK_URL, json=payload).raise_for_status()
                    print("[Discord] 通知を送信")
                except Exception as e:
                    print (f"Discord通知失敗 : {e}")

        print(f"⏳ 40秒待機中... ({datetime.now(JST).strftime('%H:%M:%S')} ～ {(datetime.now(JST) + timedelta(seconds=40)).strftime('%H:%M:%S')})")
        time.sleep(40)
