import requests
import json
import os

from files import load_json, get_unique_filepath
import config
import config2

# === Main API ===
def fetch_WebData(lang="ja", type="first"):
    print(f"[INF] WebData 取得開始 : {lang}")
    params = {
        "lang": lang
    }
    res = requests.get(config.Web_URL, params=params)

    if res.status_code == 200:
        data = res.json()
        if type == "first":
            filepath = os.path.join(config2.RESPONSE_DIR, f"WebData_{lang}.json")
            new_data = data
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                print("  [ERR] ❌️ 旧ファイルの取得に失敗")
            try:
                if new_data != before_data or before_data is None:
                    if config2.test is False:
                        with open(get_unique_filepath(config2.ARCHIVE_DIR, f"WebData_{lang}"), "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    config2.tags.append(f"Web ({lang})")
                    print(f"  [INF] 🟢 変更あり")
                else:
                    print(f"  [INF] ✅️ 変更なし")
            except Exception as e:
                print (f"  [ERR] ❌️ ファイルの保存に失敗 : {e}")
        return data
    else:
        print(f"  [ERR] 🔴 取得失敗 : {res.text} {res.status_code}")
        return None

# === ScoringRules API ===
def fetch_ScoreInfo(lang):
    print(f"[INF] ScoreInfo 取得開始 : {lang}")
    params = {
        "lang": lang
    }
    res = requests.get(config.ScoreInfo_URL, params=params)

    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(config2.RESPONSE_DIR, f"ScoreInfo_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("  [ERR] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                if config2.test is False:
                    with open(get_unique_filepath(config2.ARCHIVE_DIR, f"ScoreInfo_{lang}"), "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                config2.tags.append(f"Score ({lang})")
                print(f"  [INF] 🟢 変更あり")
            else:
                print(f"  [INF] ✅️ 変更なし")
        except Exception as e:
            print (f"[INF] ❌️ ファイルの保存に失敗 : {e}")
        return data
    else:
        print(f"  [ERR] 🔴 取得失敗 : {res.text} {res.status_code}")
        return None

# === LeaderboardInfo API ===
def fetch_LeadInfo(lang):
    print(f"[INF] LeadInfo 取得開始 : {lang}")
    params = {
        "lang": lang
    }
    res = requests.get(config.LeadInfo_URL, params=params)

    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(config2.RESPONSE_DIR, f"LeaderboardInfo_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("  [ERR] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                if config2.test is False:
                    with open(get_unique_filepath(config2.ARCHIVE_DIR, f"LeaderboardInfo_{lang}"), "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
                config2.tags.append(f"Lead ({lang})")
                print(f"  [INF] 🟢 変更あり")
            else:
                print(f"  [INF] ✅️ 変更なし")
        except Exception as e:
            print (f"  [ERR] ❌️ ファイルの保存に失敗 : {e}")
        return data
    else:
        print(f"  [ERR] 🔴 取得失敗 : {res.text} {res.status_code}")
        return None

if __name__ == "__main__":
    config2.test = True

    for lang in config2.Lang:
        fetch_WebData(lang)
    for lang in config2.Lang:
        fetch_ScoreInfo(lang)
    for lang in config2.Lang:
        fetch_LeadInfo(lang)