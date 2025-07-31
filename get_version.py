import requests
from tokens import ensure_token
import config

def get_version():
    print (f"  [INF] バージョン取得開始")
    ensure_token(grant_type="client_credentials")

    headers = {
        "Authorization": f"{config.token_type3} {config.access_token3}"
    }

    try:
        response = requests.get(config.Build_URL, headers=headers)
        if response.status_code == 200:
            data = response.json()
            version_data = data["elements"][0]["buildVersion"]
            config.version = version_data.split("-CL")[0]
            config.build = version_data.split("-CL-")[1].split("-")[0]
            print (f"    [INF] ⭕️ バージョン取得成功 : {config.version} - {config.build}")
        else:
            print(f"    [ERR] ❌️ バージョン取得失敗 : {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"    [ERR] ❌️ バージョン取得失敗 : {e}")
        return None

if __name__ == "__main__":
    get_version()