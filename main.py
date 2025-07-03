import requests
import time
import subprocess
from datetime import datetime, timedelta

from tokens import *
from files import *
from get_EventData import *
from get_WebData import *
from Playlist import *
from format_Event import *
import config
import pub_config as config2

def main():
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

    for region in config2.Regions:
        fetch_EventData(config2.main_type, region, tags, updated_regions)

    for lang in config2.Lang:
        fetch_WebData(config2.main_type, lang, tags)
    for lang in config2.Lang:
        fetch_ScoreInfo(lang, tags)
    for lang in config2.Lang:
        fetch_LeadInfo(lang, tags)

    fetch_Playlist(tags, config2.version, config2.build, playlist_tags)

    subprocess.run(["git", "add", "."], check=True)
    git_diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    should_push = git_diff.returncode != 0
    if should_push is True:
        print(f"[DEBUG] 🟢 should_push = {should_push}")
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
                repo_url = repo_url.replace("git@github.com:", "[https://github.com/](https://github.com/)") \
                    .removesuffix(".git")
            else:
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

            res = requests.post(config.Webhook_URL, json=payload)
            res.raise_for_status()
            if res.status_code == 204 or res.status_code == 200:
                print("[Discord] 通知を送信")
            if not (res.status_code == 204 or res.status_code == 200):
                print (f"[Discord] Discord通知失敗 : {res.status_code} {res.text}")

# === 実行 ===
if __name__ == "__main__":
    ensure_token()
    ensure_token("second")
    while True:
        main()

        print(f"⏳ 40秒待機中... ({datetime.now(JST).strftime('%H:%M:%S')} ～ {(datetime.now(JST) + timedelta(seconds=40)).strftime('%H:%M:%S')})")
        time.sleep(40)