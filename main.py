import requests
import time
import subprocess
from datetime import datetime, timedelta
import asyncio

from tokens import ensure_token
from get_EventData import fetch_EventData
from get_WebData import fetch_WebData, fetch_ScoreInfo, fetch_LeadInfo
from Playlist import fetch_Playlist
from format_Event import format_EventData
from hotfix import fetch_and_store_hotfix
import config
import config2

async def main(Actions=False):

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
    
    await format_EventData()

    await asyncio.gather(*(asyncio.to_thread(fetch_EventData, region) for region in config2.Regions))

    for lang in config2.Lang:
        fetch_WebData(lang)
    for lang in config2.Lang:
        fetch_ScoreInfo(lang)
    for lang in config2.Lang:
        fetch_LeadInfo(lang)

    await fetch_and_store_hotfix(Actions)

    fetch_Playlist()

    subprocess.run(["git", "add", "."], check=True)
    git_diff = subprocess.run(["git", "diff", "--cached", "--quiet"])
    should_push = git_diff.returncode != 0
    if should_push is True:
        print(f"[DBG] 🟢 should_push = {should_push}")
    else:
        print(f"[DBG] should_push = {should_push}")

    if should_push:
        if not config.tags:
            config.tags.append("ファイル関連")

        print(f"[DBG] タグ一覧 : {config.tags}")

        if not config2.test:
            timestampA = datetime.now(config.JST).strftime("%m/%d %H:%M:%S")
            message = f"更新 : {', '.join(config.tags)} ({timestampA})"
            if Actions:
                message = message + " - GitHubActions"

            subprocess.run(['git', 'pull'])

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

            if "ASIA" in config.tags or "ja" in config.tags or config.added_Tournaments or config.updated_Tournaments or config.playlist_tags:
                content = f"## [更新 : {', '.join(config.tags)}](<{commit_url}>) <@&1372839358591139840>"
            else:
                content = f"## [更新 : {', '.join(config.tags)}](<{commit_url}>)"

            payload = {
                "username": "GitHub",
                "content": content
            }

            res = requests.post(config.GitHub_Webhook_URL, json=payload)
            if res.status_code == 204 or res.status_code == 200:
                print("[Discord] 通知を送信")
            if not (res.status_code == 204 or res.status_code == 200):
                print (f"[Discord] Discord通知失敗 : {res.status_code} {res.text}")

    # タグの初期化
    config.tags = []
    config.updated_regions = []
    config.playlist_tags = []
    config.added_Tournaments = []
    config.updated_Tournaments = []

# === 実行 ===
if __name__ == "__main__":
    ensure_token()
    ensure_token("second")
    ensure_token(grant_type="client_credentials")
    while True:
        if config.mac:
            Actions = True
        else:
            Actions = False
        asyncio.run(main(Actions))
        print(f"[INF] ⏳ 40秒待機中... ({datetime.now(config.JST).strftime('%H:%M:%S')} ～ {(datetime.now(config.JST) + timedelta(seconds=40)).strftime('%H:%M:%S')})")
        time.sleep(40)