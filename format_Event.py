import requests
import json
import time
import os
from datetime import datetime, timezone

from files import load_json, get_unique_filepath
from tokens import ensure_token
from get_EventData import fetch_EventData
from get_WebData import fetch_WebData
import config
import config2

type = "second"

def format_EventData():
    print(f"[INF] FormatEventData 処理開始")
    ensure_token("second")
    event_data = fetch_EventData(type=type)
    webapi_ja = fetch_WebData(type=type)
    webapi_en = fetch_WebData("en", type)
    sent = set()
    embeds=[]

    templates = {t["eventTemplateId"]: t for t in event_data.get("templates", []) if "eventTemplateId" in t}
    payouts_by_key = {}
    for k, entries in event_data.get("payoutTables", {}).items():
        for entry in entries:
            for rank in entry.get("ranks", []):
                for payout in rank.get("payouts", []):
                    payouts_by_key.setdefault(k, []).append({
                        "scoringType": entry.get("scoringType"),
                        "threshold": rank.get("threshold"),
                        "rewardType": payout.get("rewardType"),
                        "quantity": payout.get("quantity"),
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
                "beginTime_JST": begin_dt.astimezone(config2.JST).strftime("%Y-%m-%d %H:%M:%S"),
                "endTime": w["endTime"],
                "endTime_UNIX": int(end_dt.timestamp()),
                "endTime_JST": end_dt.astimezone(config2.JST).strftime("%Y-%m-%d %H:%M:%S"),
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
        filepath = os.path.join(config2.TOURNAMENT_DIR, f"{display_id}.json")
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
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer":{
                    "text":"FNLive"
                }
            }
        except Exception as e:
            print (f"  [INF] ❌️ 開催日時の組み立て失敗 : {e}")
            date_section = "エラー"
            embed_date = {
                "title":  "📅 **開催日時**",
                "fields": date_section,
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer":{
                    "text":"FNLive"
                }
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
            print (f"  [ERR] ❌️ モードの組み立て失敗 : {e}")
            mode_section = "エラー"
            embed_mode = {
                "title":  "📍 **モード**",
                "fields": mode_section,
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer":{
                    "text":"FNLive"
                }
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
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer":{
                    "text":"FNLive"
                }
            }
        except Exception as e:
            print (f"  [ERR] ❌️ 試合数の組み立て失敗 : {e}")
            match_section = "エラー"
            embed_match = {
                "title":  "⚔️ **試合数**",
                "fields": match_section,
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer":{
                    "text":"FNLive"
                }
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
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer":{
                    "text":"FNLive"
                }
            }
        except Exception as e:
            print (f"　　[ERR] ❌️ 参加資格の組み立て失敗 : {e}")
            token_section = "エラー"
            embed_token = {
                "title":  "🔑 **参加資格**",
                "fields": token_section,
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer":{
                    "text":"FNLive"
                }
            }

        payouts_section = []
        total_length = 0
        try:
            for w in windows_to_display:
                    key = score_map.get(w["eventWindowId"])
                    payouts_list = payouts_by_key.get(key, [])

                    field_values = []
                    for payout in payouts_list:
                        json_text = json.dumps(payout, ensure_ascii=False, indent=2)
                        wrapped_text = f"```json\n{json_text}\n```"

                        if len(wrapped_text) > 1024:
                            continue

                        # 合計が超える場合は追加をやめる
                        if total_length + len(wrapped_text) > 1024:
                            break

                        field_values.append(payout)
                        total_length += len(wrapped_text)

                    if field_values:
                        payouts_section.append({
                            "name": w['eventWindowId'],
                            "value": f"```json\n{json.dumps(field_values, ensure_ascii=False, indent=2)}\n```",
                            "inline": False
                        })

            embed_payout = {
                "title": "🎁 **賞金 / 賞品 (省略の可能性あり)**",
                "fields": payouts_section,
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer": {
                    "text": "FNLive"
                }
            }
        except Exception as e:
            print(f"　　[ERR] ❌️ 賞金の組み立て失敗 : {e}")
            payouts_section = [
                {
                    "name": "エラー",
                    "value": "賞金データの取得に失敗しました。",
                    "inline": False
                }
            ]
            embed_payout = {
                "title": "🎁 **賞金 / 賞品**",
                "fields": payouts_section,
                "timestamp": datetime.now(config2.UTC).isoformat(),
                "footer": {
                    "text": "FNLive"
                }
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
            print (f"  [ERR] ❌️ 画像URL一覧の組み立て失敗 {e}")
            images_section = "🖼️ **画像URL一覧**\nエラー"


        # === 変更箇所を確認 ===
        print (f" [INF] 比較開始 : {display_id}")
        ignore_keys = {"beginTime", "endTime", "beginTime_UNIX", "endTime_UNIX"}
        eventname   = list(new_data[0].keys())[0]
        before_root = before_data[0].get(eventname, {}) if before_data else {}
        after_root  = new_data[0][eventname]
        if before_data != new_data:
            diffs = find_diffs(before_root, after_root, eventname)
            diffs = filter_diffs(diffs, ignore_keys)
            path  = get_value_by_path(before_data, new_data, diffs)

        # === 保存 & タグ追加 ===
        if before_data is None:
            print(f"   [INF] 🟢 新規トーナメント : {display_id}")
            if config2.test is False:
                with open(get_unique_filepath(config2.TOURNAMENT_ARCHIVE_DIR, f"{display_id}"), "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            config2.tags.append(f"{display_id} (New)")
            config2.added_Tournaments.append(display_id)

        elif new_data != before_data:
            print(f"   [INF] 🟢 トーナメント更新 : {display_id}")
            if config2.test is False:
                with open(get_unique_filepath(config2.TOURNAMENT_ARCHIVE_DIR, f"{display_id}"), "w", encoding="utf-8") as f:
                    json.dump(new_data, f, ensure_ascii=False, indent=2)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            config2.tags.append(f"{display_id} (Upd)")
            config2.updated_Tournaments.append(display_id)

        # === 送信準備 ===
        embeds = [embed_date, embed_mode, embed_match, embed_token, embed_payout]

        status = f"## 🆕 新トーナメント : {title}" if before_data is None else f"## 🔄 トーナメント更新 : {title}"

        if before_data is None:
            content = (
                f"<@&1372839358591139840><@&1359477859764273193>\n"
                f"{status}\n_ _\n"
                f"{images_section}\n\n"
            )
            data = {
                "payload_json": json.dumps ( {"content": content, "embeds": embeds} , ensure_ascii=False )
                }
            with open(filepath, "rb") as fp:
                files = {"file": (os.path.basename(filepath), fp, "application/json")}
                if config2.Tournament_Webhook is True:
                    try:
                        res = requests.post(config.Tournament_Webhook_URL, data=data, files=files)
                        if res.status_code == 200 or res.status_code == 204:
                            print("   [INF] ⭕️ 新トーナメントのDiscord通知成功")
                        else:
                            print (f"   [ERR] 🔴 新トーナメントのDiscord通知失敗 : {res.status_code} - {res.text}")

                    except Exception as e:
                        print (f"   [ERR] 🔴 新トーナメントのDiscord通知失敗 : {res.status_code} {res.text}")
                if config2.Log_Webhook is True:
                    try:
                        res = requests.post(config.Tournament_Webhook_URL, data=data, files=files)
                        if res.status_code == 200 or res.status_code == 204:
                            print("   [INF] ⭕️ 新トーナメントのDiscord通知成功")
                        else:
                            print (f"   [ERR] 🔴 新トーナメントのDiscord通知失敗 : {res.status_code} - {res.text}")
                    except Exception as e:
                        print (f"   [ERR] 🔴 新トーナメントのDiscord通知失敗 : {res.status_code} {res.text}")
                        print (f"'embeds':{embeds}")

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
                        "timestamp": datetime.now(config2.UTC).isoformat(),
                        "footer":{
                            "text":"FNLive"
                        }
                    }
                    embeds.append (embed_changes)

            content = (
                f"<@&1372839358591139840><@&1359477859764273193>\n"
                f"{status}\n_ _\n"
                f"{images_section}\n\n"
            )

            data = {
                "payload_json": json.dumps ( {"content": content, "embeds": embeds} , ensure_ascii=False )
                }

            with open(filepath, "rb") as fp:
                files = {"file": (os.path.basename(filepath), fp, "application/json")}
                if config2.Tournament_Webhook is True:
                    try:
                        res = requests.post(config.Tournament_Webhook_URL, data=data, files=files)
                        if res.status_code == 200 or res.status_code == 204:
                            print("   [INF] ⭕️ トーナメント更新のDiscord通知成功")
                        else:
                            print(f"   [ERR] 🔴 トーナメント更新のDiscord通知失敗 : {res.status_code} - {res.text}")
                    except Exception as e:
                        print (f"   [ERR] 🔴 トーナメント更新のDiscord通知失敗 : {res.status_code} {res.text}")
                if config2.Log_Webhook is True:
                    try:
                        res = requests.post(config.Tournament_Webhook_URL, data=data, files=files)
                        if res.status_code == 200 or res.status_code == 204:
                            print("   [INF] ⭕️ トーナメント更新のDiscord通知成功")
                        else:
                            print(f"   [ERR] 🔴 トーナメント更新のDiscord通知失敗 : {res.status_code} - {res.text}")
                            print (f"'embeds':{embeds}")
                    except Exception as e:
                        print (f"   [ERR] 🔴 トーナメント更新のDiscord通知失敗 : {res.status_code} {res.text}")
                        print (f"'embeds':{embeds}")

            sent.add(display_id)

    if not config2.added_Tournaments and not config2.updated_Tournaments:
        print(" [INF] ✅️ 変更なし")

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
                print(f"  [INF] 差分検出 : {path} | old={old} → new={new}")
                diffs.append(path)

        return diffs
    except Exception as e:
        print(f"  [ERR] ❌️ 更新されたパスの確認に失敗 : {path} - {e}")
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
        print(f"  [ERR] ❌️ UNIX,UTCの除外に失敗 : {ignore_keys} - {e}")
        return None

def shorten_diff_paths(diffs, max_depth=5):
    print(f"  [INF] パス短縮開始 : {diffs}")
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
            print(f"  [INF] パス短縮: {path} → {shortened}")
            result.add(shortened)
    except Exception as e:
        print(f"  [ERR] ❌️ パスの短縮に失敗 : {diffs} - {e}")
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
                print (f"   [INF] ⭕️ 末端のパスの値の確認成功 : {path_str} - {data}")
                return data
            except Exception as e:
                print(f"   [ERR] ❌️ 末端のパスの値の確認に失敗 : {use_diffs} - {e}")
                return None

        results = {}
        for path_str in use_diffs:
            print(f"  [INF] パスの値を確認(過去) : {use_diffs}")
            old_value = get_nested_value(before_data, path_str)
            print(f"  [INF] パスの値を確認(新) : {use_diffs}")
            new_value = get_nested_value(new_data, path_str)
            results[path_str] = {
                "old": old_value,
                "new": new_value
            }
        return results

if __name__ == "__main__":
    config2.test = True
    format_EventData()