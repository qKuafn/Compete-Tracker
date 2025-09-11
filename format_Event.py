import requests
import json
import os
import re
from datetime import datetime, timezone
from copy import deepcopy
import asyncio

from files import load_json, get_unique_filepath
from tokens import ensure_token
from get_EventData import fetch_EventData
from get_WebData import fetch_WebData
import config
import config2

Eventtype = "second"

async def format_EventData():
    print(f"[INF] FormatEventData 処理開始")
    ensure_token("second")
    EventData = fetch_EventData(type=Eventtype)
    WebData_ja = fetch_WebData(type=Eventtype)
    WebData_en = fetch_WebData("en", Eventtype)
    sent = set()
    content = None

    # === 組み立て開始 ===
    for event in EventData["events"]:
        entry = {}

        eventId = event["eventId"]
        metadata = event.get("metadata")
        platforms = event["platforms"]
        eventWindows = event.get("eventWindows")
        displayDataId = event.get("displayDataId") # WebId
        WebData = None
        square_poster_image = "未設定"
        tournament_view_background_image = "未設定"
        loading_screen_image = "未設定"
        playlist_tile_image = "未設定"

        for key, data in WebData_ja.items():
            if not isinstance(data, dict):
                continue
            if "tournament_info" not in data:
                continue
            if data["tournament_info"]["tournament_display_id"] == displayDataId:
                WebData = data.get("tournament_info")
                break

        if not WebData:
            for key, data in WebData_en.items():
                if not isinstance(data, dict):
                    continue
                if "tournament_info" not in data:
                    continue
                if data["tournament_info"]["tournament_display_id"] == displayDataId:
                    WebData = data.get("tournament_info")
                    break

        if WebData:
            EventName = WebData.get("title_line_1", "なし")
            if WebData.get("title_line_2"):
                EventName += " " + WebData.get("title_line_2")

            square_poster_image = WebData.get("square_poster_image", "未設定")
            tournament_view_background_image = WebData.get("tournament_view_background_image", "未設定")
            loading_screen_image = WebData.get("loading_screen_image", "未設定")
            playlist_tile_image = WebData.get("playlist_tile_image", "未設定")
        else:
            EventName = event.get("displayDataId", "未設定")

        windows_to_display = eventWindows[:2] if len(eventWindows) > 1 else eventWindows

        save_eventId = "_".join(eventId.split("_")[1:-1])

        if save_eventId in sent:
            continue

        output = {
            "EventName": EventName,
            "eventId": eventId,
            "displayDataId": displayDataId,
            "square_poster_image": square_poster_image,
            "tournament_view_background_image": tournament_view_background_image,
            "loading_screen_image": loading_screen_image,
            "playlist_title_image": playlist_tile_image,
            "metadata": metadata,
            "platforms": platforms
        }

        for window in eventWindows:
            scoringrules = {}

            eventWindowId = window["eventWindowId"]
            begin_dt = datetime.strptime(window["beginTime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
            end_dt = datetime.strptime(window["endTime"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)

            round_number = window.get("round", "")

            eventTemplateId = window.get("eventTemplateId")
            matched_template = None
            for template in EventData["templates"]: 
                if template.get("eventTemplateId") == eventTemplateId:
                    matched_template = template
                    break
            if matched_template:
                playlistId = matched_template.get("playlistId")
                matchCap = matched_template.get("matchCap")

            for WindowLocation in EventData["resolvedWindowLocations"][f"Fortnite:{eventId}:{eventWindowId}"]:
                displayWindowLocation = WindowLocation.split(":")[-1]
                if eventId == "epicgames_Dinosauron_Official":
                    print(f"[DBG] 処理中 WindowLocation: {WindowLocation}, displayWindowLocation: {displayWindowLocation}")

                scoringRuleSetId = EventData["scoreLocationScoringRuleSets"][WindowLocation]
                for scoreLocation in window["scoreLocations"]:
                    leaderboardDefId = scoreLocation["leaderboardDefId"]
                    if eventId == "epicgames_Dinosauron_Official":
                        print(f"[DBG] leaderboardDefId: {leaderboardDefId}, displayWindowLocation: {displayWindowLocation}")
                    isMainWindowLeaderboard = scoreLocation["isMainWindowLeaderboard"]
                    for leaderboardDef in EventData["leaderboardDefs"]:
                        raw_format = leaderboardDef["leaderboardInstanceIdFormat"]
                        pattern = re.sub(r"\$\{.*?\}", r"[^:]+", raw_format)
                        raw_format = leaderboardDef["leaderboardInstanceIdFormat"]  # "${something}_CumulativeLeaderboard"

                        def resolve_format(raw_format, vars_dict):
                            def replacer(match):
                                key = match.group(1)
                                return vars_dict.get(key, f"${{{key}}}")
                            return re.sub(r"\$\{(.*?)\}", replacer, raw_format)
                        vars_dict = {"eventId": eventId, "windowId": eventWindowId, "round": str(round_number) if round_number is not None else ""}
                        pattern = resolve_format(raw_format, vars_dict)

                        if pattern == displayWindowLocation and leaderboardDef["leaderboardDefId"] == leaderboardDefId:
                            useIndividualScores = leaderboardDef["useIndividualScores"]
                            onlyScoreTopN = leaderboardDef.get("onlyScoreTopN", -1)

                            if leaderboardDefId not in scoringrules:
                                scoringrules[leaderboardDefId] = {
                                    "scoringRuleSetId": scoringRuleSetId,
                                    "WindowLocation": displayWindowLocation,
                                    "isMainWindowLeaderboard": isMainWindowLeaderboard,
                                    "useIndividualScores": useIndividualScores,
                                    "onlyScoreTopN": onlyScoreTopN,
                                    "payouts": []
                                }

            for item in EventData["resolvedWindowLocations"][f"Fortnite:{eventId}:{eventWindowId}"]:
                WindowLocation = item.split(":", 1)[-1]
                displayWindowLocation = WindowLocation.split(":")[-1]
                if eventId == "epicgames_Dinosauron_Official":
                    print(f"[DBG] 処理中 WindowLocation: {WindowLocation}")

                for key, value in EventData["scoreLocationPayoutTables"].items():
                    if key == f"Fortnite:{eventId}:{WindowLocation}" or key == f"Fortnite:{WindowLocation}":
                        Payouts_key = value
                        payout_table = EventData["payoutTables"][Payouts_key]
                        for entry in payout_table:
                            scoringType = entry.get("scoringType")
                            ranks = entry.get("ranks", [])
                            for rank in ranks:
                                threshold = rank.get("threshold")
                                for payout in rank.get("payouts", []):
                                    payouts = {
                                        "scoreId": entry.get("scoreId") if entry.get("scoreId") else "",
                                        "scoringType": scoringType,
                                        "threshold": threshold,
                                        "rewardType": payout.get("rewardType"),
                                        "quantity": payout.get("quantity"),
                                        "value": payout.get("value")
                                    }

                                    for leaderboardDefId, scoringrule in scoringrules.items():
                                        if scoringrule["WindowLocation"] == displayWindowLocation:
                                            scoringrule["payouts"].append(payouts)

            beginTime_UNIX = int(begin_dt.timestamp())
            endTime_UNIX = int(end_dt.timestamp())

            output[eventWindowId] = {
                "beginTime_UNIX": beginTime_UNIX,
                "beginTime_JST": begin_dt.astimezone(config.JST).strftime("%Y-%m-%d %H:%M:%S"),
                "endTime_UNIX": endTime_UNIX,
                "endTime_JST": end_dt.astimezone(config.JST).strftime("%Y-%m-%d %H:%M:%S"),
                "playlistId": playlistId,
                "matchCap": matchCap,
                "additionalRequirements": window.get("additionalRequirements", []),
                "requireAllTokens": window.get("requireAllTokens", []),
                "requireAllTokensCaller": window.get("requireAllTokensCaller", []),
                "requireAnyTokens": window.get("requireAnyTokens", []),
                "requireAnyTokensCaller": window.get("requireAnyTokensCaller", []),
                "requireNoneTokensCaller": window.get("requireNoneTokensCaller", []),
                "ScoringRules": scoringrules
            }

        print (f" [INF] 比較開始 : {save_eventId}")

        filepath = os.path.join(config2.TOURNAMENT_DIR, f"{save_eventId}.json")
        new_data = output
        before_data = load_json(filepath) if os.path.exists(filepath) else None

        eventname   = new_data["EventName"]
        before_root = before_data if before_data else {}
        after_root  = new_data
        if before_data != new_data:

            # === 保存 ===
            if before_data is None:
                print(f"   [INF] 🟢 新規トーナメント : {save_eventId}")
                config.tags.append(f"{save_eventId} (New)")
                config.added_Tournaments.append(save_eventId)
            elif new_data != before_data:
                print(f"   [INF] 🟢 トーナメント更新 : {save_eventId}")
                config.tags.append(f"{save_eventId} (Upd)")
                config.updated_Tournaments.append(save_eventId)
            
            #if config2.test is False:
            #    with open(get_unique_filepath(config2.TOURNAMENT_ARCHIVE_DIR, save_eventId), "w", encoding="utf-8") as f:
            #        json.dump(new_data, f, ensure_ascii=False, indent=2)
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)

            new_data = load_json(filepath)
            # dict等の順番を揃える

        # === Discord Embed送信のためのEmbed組み立て ===
        if before_data is None or new_data != before_data:
            image_section = []
            try:
                image_section = (
                    f"-# - Square    ：{square_poster_image}\n"
                    f"-# - Background：{tournament_view_background_image}\n"
                    f"-# - Playlist  ：{playlist_tile_image}\n"
                    f"-# - Loading   ：{loading_screen_image}"
                )
            except Exception as e:
                print (f"  [ERR] ❌️ 画像URL一覧の組み立て失敗 {e}")
                image_section = "🖼️ **画像URL一覧**\nエラー"

        
        if before_data is None:
            embeds=[]
            date_section = []
            mode_section = []
            match_section = []
            token_section = []
            payout_section = []

            total_length = 0

            for eventWindow in windows_to_display:
                eventWindowId = eventWindow["eventWindowId"]

                try:
                    begin = new_data[eventWindowId]["beginTime_UNIX"]
                    end = new_data[eventWindowId]["endTime_UNIX"]
                    date_section.append({
                        "name":  eventWindowId,
                        "value": f"<t:{begin}:F>\n～<t:{end}:F>",
                        "inline": True
                    })
                except Exception as e:
                    print(f"  [ERR] ❌️ 日付の解析に失敗: {e}")
                    date_section.append({
                        "name":  eventWindowId,
                        "value": "エラー",
                        "inline": True
                    })

                try:
                    playlist = new_data[eventWindowId]["playlistId"]
                    mode_section.append({
                        "name":  eventWindowId,
                        "value": f"`{playlist}`",
                        "inline": True
                    })
                except Exception as e:
                    print(f"  [ERR] ❌️ モードの解析に失敗: {e}")
                    mode_section.append({
                        "name":  eventWindowId,
                        "value": "エラー",
                        "inline": True
                    })

                try:
                    matchCap = new_data[eventWindowId]["matchCap"]
                    if matchCap == 0:
                        matchCap = "無制限"
                    match_section.append({
                        "name":  eventWindowId,
                        "value": str(matchCap),
                        "inline": True
                    })
                except Exception as e:
                    print(f"  [ERR] ❌️ マッチキャップの解析に失敗: {e}")
                    match_section.append({
                        "name":  eventWindowId,
                        "value": "エラー",
                        "inline": True
                    })

                try:
                    eligibility = {
                        "minimumAccountLevel": metadata.get("minimumAccountLevel", "30"),
                        "additionalRequirements":  new_data[eventWindowId]["additionalRequirements"],
                        "requireAllTokens":        new_data[eventWindowId]["requireAllTokens"],
                        "requireAllTokensCaller":  new_data[eventWindowId]["requireAllTokensCaller"],
                        "requireAnyTokens":        new_data[eventWindowId]["requireAnyTokens"],
                        "requireAnyTokensCaller":  new_data[eventWindowId]["requireAnyTokensCaller"],
                        "requireNoneTokensCaller": new_data[eventWindowId]["requireNoneTokensCaller"]
                    }
                    eligibility = json.dumps(eligibility, indent=2, ensure_ascii=False)
                    token_section.append({
                        "name":  eventWindowId,
                        "value": f"```json\n{eligibility}\n```",
                        "inline": False
                    })
                except Exception as e:
                    print(f"  [ERR] ❌️ 参加資格の解析に失敗: {e}")
                    token_section.append({
                        "name":  eventWindowId,
                        "value": "エラー",
                        "inline": False
                    })

                try:
                    first_key = next(iter(new_data[eventWindowId]["ScoringRules"]))
                    payouts_list = new_data[eventWindowId]["ScoringRules"][first_key]["payouts"]

                    for i, payout in enumerate(payouts_list, 1):
                        json_text = json.dumps(payout, ensure_ascii=False, indent=2)
                        wrapped_text = f"```json\n{json_text}\n```"

                        if len(wrapped_text) > 1024:
                            wrapped_text = f"```json\n{json.dumps(payout, ensure_ascii=False)}\n```"

                        payout_section.append({
                            "name": f"{eventWindowId}",
                            "value": wrapped_text,
                            "inline": False
                        })

                except Exception as e:
                    print(f"  [ERR] ❌️ 賞金の解析に失敗: {e}")
                    payout_section.append({
                        "name": eventWindowId,
                        "value": "エラー",
                        "inline": False
                    })

            embed_date = {
                "title": "📅 **開催日時**",
                "fields": date_section,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer":{
                    "text": "FNLive",
                    "icon_url": "https://media.discordapp.net/attachments/1398826721129791509/1398826776544940212/VLtjyUF.png?ex=6886c674&is=688574f4&hm=178dda435ced5653551856f935321e4dcd5de6fde7829046f841ca44343f2d64&=&format=webp&quality=lossless&width=320&height=320"
                }
            }
            embed_mode = {
                "title": "🎮 **モード**",
                "fields": mode_section,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer":{
                    "text": "FNLive",
                    "icon_url": "https://media.discordapp.net/attachments/1398826721129791509/1398826776544940212/VLtjyUF.png?ex=6886c674&is=688574f4&hm=178dda435ced5653551856f935321e4dcd5de6fde7829046f841ca44343f2d64&=&format=webp&quality=lossless&width=320&height=320"
                }
            }
            embed_match = {
                "title": "⚔️ **試合数**",
                "fields": match_section,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer":{
                    "text": "FNLive",
                    "icon_url": "https://media.discordapp.net/attachments/1398826721129791509/1398826776544940212/VLtjyUF.png?ex=6886c674&is=688574f4&hm=178dda435ced5653551856f935321e4dcd5de6fde7829046f841ca44343f2d64&=&format=webp&quality=lossless&width=320&height=320"
                }
            }
            embed_token = {
                "title": "🔑 **参加資格**",
                "fields": token_section,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer":{
                    "text": "FNLive",
                    "icon_url": "https://media.discordapp.net/attachments/1398826721129791509/1398826776544940212/VLtjyUF.png?ex=6886c674&is=688574f4&hm=178dda435ced5653551856f935321e4dcd5de6fde7829046f841ca44343f2d64&=&format=webp&quality=lossless&width=320&height=320"
                }
            }
            embed_payout = {
                "title": "💰 **賞金 (省略の可能性あり)**",
                "fields": payout_section,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "footer":{
                    "text": "FNLive",
                    "icon_url": "https://media.discordapp.net/attachments/1398826721129791509/1398826776544940212/VLtjyUF.png?ex=6886c674&is=688574f4&hm=178dda435ced5653551856f935321e4dcd5de6fde7829046f841ca44343f2d64&=&format=webp&quality=lossless&width=320&height=320"
                }
            }
            embeds = [embed_date, embed_mode, embed_match, embed_token, embed_payout]
            content = (
                f"-# <@&1372839358591139840><@&1359477859764273193>\n"
                f"### 🆕 新規追加 : {eventname}\n"
                f"{image_section}\n"
            )
            send_discord(content, embeds, filepath, save_eventId, sent)

        elif new_data != before_data:
            embeds = []
            
            diffs = find_diffs(before_root, after_root, eventname)
            for path, change in diffs.items():
                changes_section = []

                path = " > ".join(path.split(" > ")[1:])

                old_value = tuple_to_dict(change.get("old"))
                new_value = tuple_to_dict(change.get("new"))

                old_str = shorten_json(old_value, 512)
                new_str = shorten_json(new_value, 512)

                changes_section.append({
                    "name": "過去データ",
                    "value": f"```json\n{old_str}\n```",
                    "inline": all(len(line) <= 26 for line in str(old_str).splitlines())
                })
                changes_section.append({
                    "name": "新データ",
                    "value": f"```json\n{new_str}\n```",
                    "inline": all(len(line) <= 26 for line in str(new_str).splitlines())
                })
                embed_changes = {
                        "title": path,
                        "fields": changes_section,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "footer":{
                            "text": "FNLive",
                            "icon_url": "https://media.discordapp.net/attachments/1398826721129791509/1398826776544940212/VLtjyUF.png?ex=6886c674&is=688574f4&hm=178dda435ced5653551856f935321e4dcd5de6fde7829046f841ca44343f2d64&=&format=webp&quality=lossless&width=320&height=320"
                        }
                    }
                embeds.append (embed_changes)
                content = (
                    f"-# <@&1372839358591139840><@&1359477859764273193>\n"
                    f"### 🔄 更新 : {eventname}\n"
                    f"{image_section}\n"
                )
            if content:
                send_discord(content, embeds, filepath, save_eventId, sent)
            else:
                print (  f"   [INF] 順番のみが変更された可能性があります。更新通知はスキップします。")

    current_event_ids = set()
    for event in EventData["events"]:
        save_eventId = "_".join(event["eventId"].split("_")[1:-1])
        current_event_ids.add(save_eventId)

    for filename in os.listdir(config2.TOURNAMENT_DIR):
        if not filename.endswith(".json"):
            continue
        file_eventId = filename.replace(".json", "")
        filepath = os.path.join(config2.TOURNAMENT_DIR, filename)

        if file_eventId not in current_event_ids:
            print(f"   [INF] 🔴 トーナメント削除 : {file_eventId}")
            try:
                os.remove(filepath)
                config.tags.append(f"{file_eventId} (Del)")
                config.deleted_Tournaments.append(file_eventId)
            except Exception as e:
                print(f"   [ERR] 削除失敗 : {file_eventId} ({e})")

    if not config.added_Tournaments and not config.updated_Tournaments and not config.deleted_Tournaments:
        print(" [INF] ✅️ 変更なし")

def send_discord(content, embeds, filepath, save_eventId, sent):
    if len(embeds) > 7:
        embeds = embeds[:4]
        
        embeds.append({
            "description": f"8個以上のembedが存在するため省略しました。"
        })

    data = {
        "payload_json": json.dumps({"content": content, "embeds": embeds}, ensure_ascii=False),
    }

    with open(filepath, "rb") as f:
        files = {"file": (os.path.basename(filepath), f, "application/json")}

        if config2.Tournament_Webhook is True:
            try:
                res = requests.post(config.Tournament_Webhook_URL, data=data, files=files)
                if res.status_code in (200, 204):
                    print("   [INF] ⭕️ Discord通知成功")
                else:
                    print (f"   [ERR] 🔴 Discord通知失敗 : {res.status_code} - {res.text}")
            except Exception as e:
                print (f"   [ERR] 🔴 Discord通知失敗 : {e}")

        if config2.Log_Webhook is True:
            try:
                res = requests.post(config.Log_Webhook_URL, data=data, files=files)
                if res.status_code in (200, 204):
                    print("   [INF] ⭕️ Discord通知成功")
                else:
                    print (f"   [ERR] 🔴 Discord通知失敗 : {res.status_code} - {res.text}")
                    print (f"'embeds':{embeds}")
            except Exception as e:
                print (f"   [ERR] 🔴 Discord通知失敗 : {e}")
                print (f"'embeds':{embeds}")
    
    sent.add(save_eventId)

def find_diffs(old, new, path=""):
    diffs = {}

    IGNORED_KEYS = {
        "beginTime",
        "beginTime_UNIX",
        "endTime",
        "endTime_UNIX"
    }

    IGNORED_ORDER_KEYS = {
        "platforms",
        "additionalRequirements",
        "requireAllTokens",
        "requireAnyTokens",
        "requireNoneTokensCaller",
        "requireAllTokensCaller",
        "requireAnyTokensCaller"
    }

    key_name = path.split(" > ")[-1]
    if key_name in IGNORED_KEYS:
        return {}

    if isinstance(old, dict) and isinstance(new, dict):
        all_keys = list(old.keys()) + [k for k in new.keys() if k not in old]
        for key in all_keys:
            if key in IGNORED_KEYS:
                continue
            new_path = f"{path} > {key}" if path else key
            diffs.update(find_diffs(old.get(key), new.get(key), new_path))

    elif isinstance(old, list) and isinstance(new, list):
        removed_items = [item for item in old if item not in new]
        added_items = [item for item in new if item not in old]

        if key_name in IGNORED_ORDER_KEYS:
            old_types = set(type(x) for x in old)
            new_types = set(type(x) for x in new)

            if len(old_types) == 1 and len(new_types) == 1 and old_types == new_types:
                for item in removed_items:
                    diffs.setdefault(path, []).append({"old": item, "new": None})
                for item in added_items:
                    diffs.setdefault(path, []).append({"old": None, "new": item})

                try:
                    if sorted(old) != sorted(new):
                        diffs[path] = {"old": old, "new": new}
                except TypeError:
                    diffs[path] = {"old": old, "new": new}
            else:
                if old != new:
                    diffs[path] = {"old": old, "new": new}
        elif key_name == "payouts":
            old_list = old if isinstance(old, list) else []
            new_list = new if isinstance(new, list) else []

            def dict_to_tuple(d):
                if not isinstance(d, dict):
                    return d
                return tuple(sorted(d.items()))

            old_sorted = sorted([dict_to_tuple(d) for d in old_list])
            new_sorted = sorted([dict_to_tuple(d) for d in new_list])

            max_len = max(len(old_sorted), len(new_sorted))
            for i in range(max_len):
                new_path = f"{path} > {i}"
                old_item = old_sorted[i] if i < len(old_sorted) else None
                new_item = new_sorted[i] if i < len(new_sorted) else None
                if old_item != new_item:
                    diffs[new_path] = {"old": old_item, "new": new_item}
        else:
            max_len = max(len(old), len(new))
            for i in range(max_len):
                new_path = f"{path} > {i}"
                diffs.update(find_diffs(
                    old[i] if i < len(old) else None,
                    new[i] if i < len(new) else None,
                    new_path
                ))

    else:
        if old != new:
            diffs[path] = {"old": old, "new": new}

    return diffs

def shorten_json(obj, max_len):
    obj = deepcopy(obj)

    def to_str(o):
        return json.dumps(o, ensure_ascii=False, indent=2)

    s = to_str(obj)
    if len(s) <= max_len:
        return s

    if isinstance(obj, dict):
        keys = list(obj.keys())
        while len(keys) > 0:
            s = to_str(obj)
            if len(s) <= max_len:
                return s
            key_to_remove = keys.pop()
            obj.pop(key_to_remove, None)
        return "{}"

    if isinstance(obj, list):
        while len(obj) > 0:
            s = to_str(obj)
            if len(s) <= max_len:
                return s
            obj.pop()
        return "[]"

    s = str(obj)
    if len(s) > max_len:
        s = s[:max_len] + "…(省略)"
    return s

def tuple_to_dict(obj):
    if isinstance(obj, tuple):
        try:
            if all(isinstance(x, (list, tuple)) and len(x) == 2 for x in obj):
                return {k: v for k, v in obj}
        except Exception:
            pass
    return obj

if __name__ == "__main__":
    config2.test = True
    config2.Tournament_Webhook = False
    asyncio.run(format_EventData())