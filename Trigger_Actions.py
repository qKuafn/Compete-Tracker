import requests
import time
from datetime import datetime, timedelta

import config

owner = "qKuafn"
repo = "Compete-Tracker"
workflow_filename = "auto-fetch.yml"
ref = "main"

url = f"https://api.github.com/repos/{owner}/{repo}/actions/workflows/{workflow_filename}/dispatches"

def trigger_workflow():
    headers = {
        "Accept": "application/vnd.github+json",
        "Authorization": f"Bearer {config.github_token}",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    data = {
        "ref": ref
    }

    response = requests.post(url, json=data, headers=headers)

    if response.status_code == 204:
        print("[INF] ✅️ ワークフローが正常にトリガーされました")
    else:
        print(f"❌ トリガー失敗: {response.status_code}")
        print(response.text)

if __name__ == "__main__":
    while True:
        trigger_workflow()
        print(f"[INF] ⏳ 60秒待機中... ({datetime.now(config.JST).strftime('%H:%M:%S')} ～ {(datetime.now(config.JST) + timedelta(seconds=60)).strftime('%H:%M:%S')})")
        time.sleep(60)