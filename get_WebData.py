import requests
import json
import os

from get_token import *
from files import *
import config
import pub_config as config2

# === Main API ===
def fetch_WebData(type, lang, tags=[]):
    count = "2" if type == "second" else ""
    url = getattr(config, f"Web_URL{count}") + f"?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        if type == "first":
            filepath = os.path.join(config2.RESPONSE_DIR, f"WebData_{lang}.json")
            new_data = data
            try:
                before_data = load_json(filepath) if os.path.exists(filepath) else None
            except Exception as e:
                print("[WebData] ❌️ 旧ファイルの取得に失敗")
            try:
                if new_data != before_data or before_data is None:
                    if config2.test is False:
                        with open(get_unique_filepath(config2.ARCHIVE_DIR, f"WebData_{lang}"), "w", encoding="utf-8") as f:
                            json.dump(data, f, ensure_ascii=False, indent=2)
                    with open(filepath, "w", encoding="utf-8") as f:
                        json.dump(data, f, ensure_ascii=False, indent=2)
                    tags.append(f"Web ({lang})")
                    print(f"[WebData] 🟢 {lang} : 更新あり")
                else:
                    print(f"[WebData] {lang} : 更新なし")
            except Exception as e:
                print (f"[WebData] ❌️ ファイルの保存に失敗 : {e}")
                return None
        return data
    
# === ScoringRules API ===
def fetch_ScoreInfo(lang, tags):
    url = f"{config.ScoreRule_URL}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(config2.RESPONSE_DIR, f"ScoreInfo_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("[ScoreInfo] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                if config2.test is False:
                    with open(get_unique_filepath(config2.ARCHIVE_DIR, f"ScoreInfo_{lang}"), "w", encoding="utf-8") as f:
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

# === LeaderboardInfo API ===
def fetch_LeadInfo(lang, tags):
    url = f"{config.LeadInfo_URL}?lang={lang}"
    res = requests.get(url)
    if res.status_code == 200:
        data = res.json()
        filepath = os.path.join(config2.RESPONSE_DIR, f"LeaderboardInfo_{lang}.json")
        new_data = data
        try:
            before_data = load_json(filepath) if os.path.exists(filepath) else None
        except Exception as e:
            print("[LeadInfo] ❌️ 旧ファイルの取得に失敗")
        try:
            if new_data != before_data or before_data is None:
                if config2.test is False:
                    with open(get_unique_filepath(config2.ARCHIVE_DIR, f"LeaderboardInfo_{lang}"), "w", encoding="utf-8") as f:
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