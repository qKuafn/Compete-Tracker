import requests
from collections import defaultdict
from datetime import datetime
import os
import io
import json
import difflib
import asyncio
import aiohttp

from tokens import ensure_token
from files import load_ini, get_unique_filepath, sanitize_filename, format_number
from dillyapis import fetch_export_data, fetch_export_data_async, get_loc_data
from create_weap_img import create_image
import config
import config2

base_name = ".DefaultGame"

def fetch_hotfix_uniqueFilename():
    ensure_token()
    print (f"[INF] Hotfix 取得開始")
    headers = {"Authorization": f"{config.token_type} {config.access_token}"}
    res = requests.get(config.CloudStrage_URL, headers=headers)
    if res.status_code == 200:
        data = res.json()
        for item in data:
            if item.get("filename") == "DefaultGame.ini":
                uniqueFilename = item.get("uniqueFilename")
                return uniqueFilename
    else:
        print(f"  [ERR] ❌️ CloudStrage 取得失敗 : {res.status_code} {res.text}")
        return None

async def fetch_and_store_hotfix(Actions):
    async with aiohttp.ClientSession() as session:
        uniqueFilename = fetch_hotfix_uniqueFilename()
        if not uniqueFilename:
            print("  [ERR]  🔴 DefaultGame.iniに対応するUniqueFileNameがありません")
            return

        url = config.Hotfix_URL.format(UniqueFileName=uniqueFilename)
        headers = {"Authorization": f"{config.token_type} {config.access_token}"}
        res = requests.get(url, headers=headers)
        if res.status_code == 200:
            filepath = os.path.join(config2.RESPONSE_DIR, f"{base_name}.ini")
            new_data = res.text
            if os.path.exists(filepath):
                try:
                    old_data = load_ini(filepath)
                except Exception as e:
                    print(f"  [ERR] ❌️ 旧ファイルの取得に失敗 : {e}")
            if new_data != old_data or old_data is None:
                config.tags.append("Hotfix")
                try:
                    #if config2.test is False:
                    #    with open(get_unique_filepath(config2.ARCHIVE_DIR, f"{base_name}", "ini"), "w", encoding="utf-8") as f:
                    #        f.write(new_data)
                    with open(filepath, "w", encoding="utf-8") as f:
                        f.write(new_data)
                    print(f"  [INF] 🟢 変更あり")
                except Exception as e:
                    print(f"  [ERR] ❌️ ファイルの保存に失敗 : {e}")
                    return
            elif new_data == old_data:
                print("  [INF] ✅️ 変更なし")
                return
        else:
            print(f"  [ERR] ❌️ DefaultGame.ini 取得失敗 : {res.status_code} {res.text}")
            return

        await load_changes(session, old_data, new_data, Actions)

async def load_changes(session, old_data, new_data, Actions):
    old_lines = old_data.splitlines()
    new_lines = new_data.splitlines()
    diff = difflib.ndiff(old_lines, new_lines)
    changes = []
    for line in diff:
        if line.startswith('+ ') or line.startswith('- '):
            content = line.replace(" +", "")
            if content != "":
                changes.append(content)
    if changes:
        diff_text = "\n".join(changes) + "\n"

    # === Discord通知 ===
        diff_file = io.BytesIO(diff_text.encode("utf-8"))
        files = {"file": ("hotfix.diff", diff_file, "text/plain")}
        data = {
            "content": "Hotfixを検出",
            "username": "Hotfix Tracker",
        }
        if config2.Hotfix_Webhook is True:
            response = requests.post(config.Hotfix_Webhook_URL, data=data, files=files)
            if response.status_code == 204 or response.status_code == 200:
                print("    [INF] ⭕️ diffのDiscord通知成功")
            else:
                print(f"    [ERR] 🔴 diffのDiscord通知失敗 : {response.status_code} {response.text}")
        if config2.Log_Webhook is True:
            response = requests.post(config.Log_Webhook_URL, data=data, files=files)
            if response.status_code == 204 or response.status_code == 200:
                print("    [INF] ⭕️ diffのDiscord通知成功")
            else:
                print(f"    [ERR] 🔴 diffのDiscord通知失敗 : {response.status_code} {response.text}")

    await parse_hotfix(session, new_data, diff_text, Actions)

async def parse_hotfix(session, new_data, diff_text, Actions):
    print("  [INF] 差分の解析開始")
    parsed_hotfix = []
    for line in diff_text.splitlines():
        if "RowUpdate" in line:
            change_type = line[0]
            line = line[1:]
            parts = line.split(";")
            if len(parts) < 5:
                continue
            path = parts[0]
            cleared_path = path[path.find("/"):]
            row = parts[2]
            key = parts[3]
            value = parts[4]
            parsed_hotfix.append({
                "status": "追加" if change_type.startswith("+") else "削除",
                "origin_row": line,     # Hotfix本文
                "path": cleared_path,   # ファイルパスのみ
                "row": row,             # 大きなカテゴリー 例: "WorldList.", "SpawnPercent"
                "key": key,             # 小さなカテゴリー 例: "Weight", timeの"1.0"
                "value": value          # 数値 例: "0.0"
            })
        if "TableUpdate;" in line or "AddRow;" in line:
            print("   [INF] テーブル更新・行追加は無視")
    await check_depth_changes(session, new_data, parsed_hotfix, Actions)

async def check_depth_changes(session, new_data, diff_data, Actions):
    merged = defaultdict(lambda: {"追加" : None, "削除" : None})
    grouped = defaultdict(lambda: defaultdict(list))

    for item in diff_data:
        changed_path = item["path"]
        origin_row = item["origin_row"]
        row = item["row"]
        key = item["key"]
        status = item["status"]
        merged[(changed_path, row, key)][status] = {
            "key": item["key"],
            "value": item["value"],
            "origin_row": item["origin_row"]
        }

    file_data_cache = {}

    for (changed_path, row, key), change in merged.items():
        print(f"    [INF] 解析対象 : path={changed_path}, row={row}")
        added = change["追加"]
        removed = change["削除"]
        if added:
            origin_row = added.get("origin_row")
        elif removed:
            origin_row = removed.get("origin_row")
        try:
            weapon = ""
            weapon_path = ""
            image_path = ""
            default_weight = ""
            # === 戦利品更新の場合、武器名の取得・武器画像パスの取得 ===
            if "LootPackages" in changed_path:

                if not config.loc_data:
                    config.loc_data = await get_loc_list()
                    print(f"    [INF] ⭕️ localization 取得完了（{len(config.loc_data)}件）")

                if changed_path not in file_data_cache:
                    file_data = fetch_export_data(changed_path)
                    file_data_cache[changed_path] = file_data[0].get("Rows", {}) if file_data else {}
                    row_data = file_data_cache[changed_path].get(f"{row}", {})
                else:
                    row_data = file_data_cache[changed_path].get(f"{row}", {})

                # === 競技のLPにデータがない場合、カジュアルから取得 (AddRowの事前対応) ===
                if not row_data and "/LootCurrentSeason/DataTables/Comp/LootCurrentSeasonLootPackages_Client_comp" in changed_path:
                    fallback_path = "/LootCurrentSeason/DataTables/LootCurrentSeasonLootPackages_Client"
                    if fallback_path not in file_data_cache:
                        file_data = fetch_export_data(fallback_path)
                        file_data_cache[fallback_path] = file_data[0].get("Rows", {}) if file_data else {}
                    row_data = file_data_cache[fallback_path].get(f"{row}", {})

                try:
                    new_lines = new_data.splitlines()
                    for line in new_lines:
                        if f"{changed_path};RowUpdate;{row};ItemDefinition;" in line:
                            weapon_path = line.split(";")[-1]
                    if not weapon_path:
                        weapon_path = (row_data.get("ItemDefinition", {}).get("AssetPathName", ""))
                    wid = weapon_path.split('/')[-1].split('.')[0]
                    weapon_data = fetch_export_data(weapon_path)
                except Exception as e:
                    print(f"    [ERR] 🔴 武器のパス取得に失敗 : {e}")
                    weapon_data = []

                try:
                    if weapon_data:
                        weapon_name_key = weapon_data[0].get("Properties", {}).get("ItemName", {}).get("key", "不明")
                        weapon_name = config.loc_data.get(weapon_name_key, "不明")
                    else:
                        weapon_name = ""
                except Exception as e:
                    print(f"    [ERR] 🔴 武器名の取得に失敗 : {e}")
                    weapon_name = ""

                if weapon_data:
                    rarity_data = weapon_data[0].get("Properties", {}).get("Rarity", "Uncommon").split("::")[-1]
                    if rarity_data == "Uncommon":
                        WeaponData_DataLists = weapon_data[0].get("Properties", {}).get("DataList", [])
                        for DataList in WeaponData_DataLists:
                            if "Rarity" in DataList:
                                Rarity_Row = DataList["Rarity"]
                                rarity_data = Rarity_Row.split("::")[-1] if Rarity_Row else "Uncommon"
                                break
                    rarity = "不明"
                    if "Common" in rarity_data:
                        rarity = "白"
                    elif "Uncommon" in rarity_data:
                        rarity = "緑"
                    elif "Rare" in rarity_data:
                        rarity = "青"
                    elif "Epic" in rarity_data:
                        rarity = "紫"
                    elif "Legendary" in rarity_data:
                        rarity = "金"
                    elif "Mythic" in rarity_data:
                        rarity = "ミシック"
                    elif "Transcendent" in rarity_data:
                        rarity = "エキゾチック"
                    weapon = f"{weapon_name} ({rarity})"
                else:
                    weapon = ""

                if wid and weapon_name:
                    sanized_weapon_name = sanitize_filename(weapon_name)
                    if rarity not in ("ミシック", "エキゾチック"):
                        image_path = rf"{config.Weap_dir}\{sanized_weapon_name}\{wid}.png"
                    elif rarity == "ミシック":
                        image_path = rf"{config.Weap_dir}\ミシック\{sanized_weapon_name}.png"
                    elif rarity == "エキゾチック":
                        image_path = rf"{config.Weap_dir}\エキゾチック\{sanized_weapon_name}.png"
                else:
                    image_path = ""

            # === DataTavleの更新は、Rows.row
            elif "DataTable=" in origin_row:
                if changed_path not in file_data_cache:
                    file_data = fetch_export_data(changed_path)
                    file_data_cache[changed_path] = file_data[0].get("Rows", {}) if file_data else {}
                row_data = file_data_cache[changed_path].get(f"{row}", {})

            # CurveTableの更新は、Rows.row.Keys内に "Time": と "Value": がある
            elif "CurveTable=" in origin_row:
                if changed_path not in file_data_cache:
                    export_data = fetch_export_data(changed_path)
                    file_data_cache[changed_path] = export_data[0].get("Rows", {}) if export_data else {}
                row_data = file_data_cache[changed_path].get(f"{row}", {}).get("Keys", [])

        except Exception as e:
            print(f"    [ERR] 🔴 その他データ取得エラー : {e}")

        def find_value_by_time(row_data, target_time):
            if not isinstance(row_data, list):
                return None

            for item in row_data:
                if not isinstance(item, dict):
                    continue  # ← dict 以外は無視

                # time が存在する行だけ扱う
                if "time" not in item:
                    continue

                if item.get("time") == target_time:
                    return item.get("value")

            return None

        # === 戦利品プールの更新のみ有効化・無効化のチェック ===
        # === それ以外は「元 → 更新」をdisplayに追加 ===
        if added and removed:
            display = f"{format_number(removed['value'])} → {format_number(added['value'])}"
            if added['value'] != removed['value']:
                if added.get("key") == "Weight":
                    if format_number(added['value']) == "0.0":
                        display = display + "  (無効化)"
                if removed.get("key") == "Weight":
                    if format_number(removed['value']) == "0.0":
                        display = display + "  (有効化)"
            status = "更新"
            key = added["key"]
        elif added:
            if "CurveTable=" in origin_row:
                default_weight = find_value_by_time(row_data, added["key"])
            elif "DataTable=" in origin_row:
                default_weight = row_data.get(added["key"], "エラー")
                if default_weight == "エラー":
                    default_weight = find_value_by_time(row_data, added["key"])
            display = f"{format_number(default_weight)} → {format_number(added['value'])}"
            if default_weight != added['value']:
                if added.get("key") == "Weight":
                    if format_number(default_weight) == "0.0":
                        display = display + "  (有効化)"
                    if format_number(added['value']) == "0.0":
                        display = display + "  (無効化)"
            status = "追加"
            key = added["key"]
        elif removed:
            if "CurveTable=" in origin_row:
                default_weight = find_value_by_time(row_data, removed["key"])
            elif "DataTable=" in origin_row:
                default_weight = row_data.get(removed["key"], "エラー")
                if default_weight == "エラー":
                    default_weight = find_value_by_time(row_data, removed["key"])
            display = f"{format_number(removed['value'])} → {format_number(default_weight)}"
            if removed['value'] != default_weight:
                if removed.get("key") == "Weight":
                    if format_number(removed['value']) == "0.0":
                        display = display + "  (有効化)"
                    if format_number(default_weight) == "0.0":
                        display = display + "  (無効化)"
            status = "削除"
            key = removed["key"]

        print(f"      [DBG] {status} : row={row}, key={key}, display={display}, image_path = {image_path}")
        grouped[(status, changed_path)][weapon].append({
            "row": row,
            "key": key,
            "display": display,
            "AssetPath": weapon_path,
            "image_path": image_path,
            "filename": os.path.basename(image_path) if image_path else "",
            "weapon": weapon
        })

    # === Embed組み立て ===
    analysis_embeds = []
    for (status, changed_path), weapon_dict in grouped.items():
        all_entries = []
        for entries in weapon_dict.values():
            all_entries.extend(entries)
        lines = [f"- `{e['row']}` : {e['key']} ... {e['display']}" for e in all_entries]

        header = f"```{changed_path}```"  
        embeds = [] 
        current_lines = [header]  
        current_length = len(header) + 1 

        for line in lines:
            line_length = len(line) + 1
            if current_length + line_length > 4096:
                print("     [INF] Embedの文字数制限のため、分割して送信します")
                embeds.append({
                    "title": f"Hotfix{status}",
                    "description": "\n".join(current_lines),
                    "color": 0x2ECC71 if status == "追加" else 0xE74C3C if status == "削除" else 0xF1C40F,
                    "timestamp": datetime.now(config.UTC).isoformat()
                })
                current_lines = [line]
                current_length = line_length
            else:
                current_lines.append(line) 
                current_length += line_length

        if current_lines:
            embeds.append({
                "title": f"Hotfix{status}",
                "description": "\n".join(current_lines),
                "color": 0x2ECC71 if status == "追加" else 0xE74C3C if status == "削除" else 0xF1C40F,
                "timestamp": datetime.now(config.UTC).isoformat()
            })
        
        analysis_embeds.extend(embeds)

    # === 戦利品プール更新の武器画像付きのEmbed組み立て ===
    loot_embeds_files = []  # (embed, files) のタプルを保存
    for (status, changed_path), weapon_dict in grouped.items():
        for weapon, entries in weapon_dict.items():
            if weapon:
                # === image_pathごとに、対応する lines と weapon_path を image_lines_map に保存 ===
                image_lines_map = defaultdict(lambda: {"lines": [], "weapon_path": None})
                for e in entries:
                    image_path = e.get("image_path", "")
                    weapon_path = e.get("AssetPath", "")
                    line = f"- `{e['row']}`\n  - {e['key']} ... {e['display']}"
                    image_lines_map[image_path]["lines"].append(line)
                    if weapon_path:
                        image_lines_map[image_path]["weapon_path"] = weapon_path
                    else:
                        print(f"    [ERR] ❌️ 武器画像のパスがありません。画像生成をスキップします")

                for image_path, data in image_lines_map.items():
                    if changed_path == "/ForbiddenFruitDataTables/DataTables/ForbiddenFruitChapterLootPackages" or changed_path == "/Figment_LootTables/DataTables/FigmentLootPackages" or changed_path == "/BlastBerryLoot/DataTables/BlastBerryLootPackages" or changed_path == "/LootCurrentSeason/DataTables/Delulu/DeluluOverrideLootPackages_Client" or "Juno" in changed_path:
                        Send_LootChange = False
                    else:
                        Send_LootChange = True
                    lines = data["lines"]
                    weapon_path = data["weapon_path"]

                    description_text = f"```{changed_path}```" + "\n" + "\n".join(lines)
                    filename = weapon_path.split('/')[-1].split('.')[0] + ".png"

                    if not Actions and os.path.isfile(image_path):
                        print(f"    [INF] 画像を読み込み : {image_path}")

                    else:
                        # === 武器画像がなく、作れる状態なら作る ===
                        if weapon_path and not os.path.isfile(image_path):
                            print ("=====================================")
                            print(f"    [INF] 画像を生成します : {weapon_path}")
                            # === テスト状態のActions か Actionsじゃない なら、ローカルからの取得・保存を試す ===
                            if (config2.test and Actions) or not Actions:
                                img = await create_image(session, weapon_path, local=True)
                            else:
                                img = await create_image(session, weapon_path, local=False)

                        # === テスト状態のActionsなら、必ず画像を生成 (ローカルで動かしているはずなので) ===
                        if weapon_path and config2.test and Actions:
                            print ("=====================================")
                            print(f"    [INF] Actions デバッグ用 : 画像を生成します : {weapon_path}")
                            img = await create_image(session, weapon_path, local=False)

                    # === Actionsで画像が作られているなら、Tempフォルダに保存 ===
                    # === not os.path.isfile じゃないのは、テスト状態のActionsの可能性を考慮 ===
                    if Actions and img:
                        os.makedirs(config2.TEMP_DIR, exist_ok=True)
                        image_path = os.path.join(config2.TEMP_DIR, filename)
                        try:
                            img.save(image_path, format="png")
                            print(f"    [INF] ⭕️ 画像を一時保存 : {image_path}")
                        except Exception as e:
                            print(f"    [ERR] ❌️ 画像の一時保存に失敗 : {image_path}, {e}")

                    with open(image_path, "rb") as img:
                        files = {
                            "file": (filename, img.read())
                        }
                        embed = {
                            "title": weapon,
                            "description": description_text,
                            "color": 0x2ECC71 if status == "追加" else 0xE74C3C if status == "削除" else 0xF1C40F,
                            "timestamp": datetime.now(config.UTC).isoformat(),
                            "image": {
                                "url": f"attachment://{filename}"
                            },
                            "footer":{
                                "text": "FNLive",
                                "icon_url": "https://media.discordapp.net/attachments/1398826721129791509/1398826776544940212/VLtjyUF.png?ex=6886c674&is=688574f4&hm=178dda435ced5653551856f935321e4dcd5de6fde7829046f841ca44343f2d64&=&format=webp&quality=lossless&width=320&height=320"
                            }
                        }
                        if Send_LootChange:
                            loot_embeds_files.append((embed, files))

    # === 解析通知Embedをまとめて送信 ===
    if analysis_embeds:
        payload = {
            "embeds": analysis_embeds,
            "username": "Hotfix Tracker"
        }
        data = {
            "payload_json": json.dumps(payload, ensure_ascii=False)
        }
        if config2.Hotfix_Webhook:
            response = requests.post(config.Hotfix_Webhook_URL, data=data)
            if response.status_code == 204 or response.status_code == 200:
                print(f"      [INF] ⭕️ Discord通知成功 (解析 {len(analysis_embeds)}件)")
            else:
                print(f"      [ERR] ❌ Discord通知失敗 : {response.status_code} {response.text}")
        if config2.Log_Webhook:
            response = requests.post(config.Log_Webhook_URL, data=data)
            if response.status_code == 204 or response.status_code == 200:
                print(f"      [INF] ⭕️ Discord通知成功 (解析 {len(analysis_embeds)}件)")
            else:
                print(f"      [ERR] ❌ Discord通知失敗 : {response.status_code} {response.text}")

    # === 戦利品通知Embedをまとめて送信 ===
    for embed, files in loot_embeds_files:
        payload = {
            "embeds": [embed],
            "username": "戦利品プール更新"
        }
        data = {
            "payload_json": json.dumps(payload, ensure_ascii=False)
        }
        if config2.Hotfix_Webhook:
            response = requests.post(config.Loot_Webhook_URL, data=data, files=files)
            if response.status_code in (200, 204):
                print(f"    [INF] ⭕️ Discord通知成功 (画像)")
            else:
                print(f"    [ERR] ❌ Discord通知失敗 (画像) : {response.status_code} {response.text}")
        if config2.Log_Webhook:
            response = requests.post(config.Log_Webhook_URL, data=data, files=files)
            if response.status_code in (200, 204):
                print(f"    [INF] ⭕️ Discord通知成功 (画像)")
            else:
                print(f"    [ERR] ❌ Discord通知失敗 (画像) : {response.status_code} {response.text}")

    print ("  [INF] ✅️ Hotfix 処理完了")

async def get_loc_list():
    paths = [
        "FortniteGame/Content/Localization/Fortnite_locchunk10/ja/Fortnite_locchunk10",
        "FortniteGame/Content/Localization/Fortnite_locchunk100/ja/Fortnite_locchunk100",
        "FortniteGame/Content/Localization/Fortnite_locchunk11/ja/Fortnite_locchunk11",
        "FortniteGame/Content/Localization/Fortnite_locchunk13/ja/Fortnite_locchunk13",
        "FortniteGame/Content/Localization/Fortnite_locchunk20/ja/Fortnite_locchunk20",
        "FortniteGame/Content/Localization/Fortnite_locchunk30/ja/Fortnite_locchunk30",
        "FortniteGame/Content/Localization/Fortnite_locchunk32/ja/Fortnite_locchunk32",
        "FortniteGame/Content/Localization/Fortnite_locchunk35/ja/Fortnite_locchunk35",
        "FortniteGame/Content/Localization/Fortnite_locchunk40/ja/Fortnite_locchunk40",
        "FortniteGame/Content/Localization/Fortnite_locchunk50/ja/Fortnite_locchunk50",
        "FortniteGame/Content/Localization/Fortnite_locchunk60/ja/Fortnite_locchunk60",
        "FortniteGame/Content/Localization/Fortnite_locchunk80/ja/Fortnite_locchunk80",
        "FortniteGame/Content/Localization/Fortnite_locchunk85/ja/Fortnite_locchunk85",
        "FortniteGame/Content/Localization/Fortnite_locchunk90/ja/Fortnite_locchunk90"
    ]

    loc_dict = {}
    async with aiohttp.ClientSession() as session:
        for path in paths:
            data = await fetch_export_data_async(session, path)
            await asyncio.sleep(0.5)

            rows = data.get("", {})
            for key, val in rows.items():
                if isinstance(val, str):
                    loc_dict[key] = val

    return loc_dict

if __name__ == "__main__":
    config2.test = True
    config2.Hotfix_Webhook = False
    asyncio.run(fetch_and_store_hotfix(Actions=True))