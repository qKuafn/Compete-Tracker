import requests
import time

import config

def get_token(type = "first"):
    print(f"[get_token] トークンを取得 ({type})")
    count = "2" if type == "second" else ""
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {config.AUTH_TOKEN}"
    }
    data = {
        "grant_type": "device_auth",
        "account_id": getattr(config, f"ACCOUNT_ID{count}"),
        "device_id": getattr(config, f"DEVICE_ID{count}"),
        "secret": getattr(config, f"SECRET{count}"),
    }
    res = requests.post(config.Token_URL, headers=headers, data=data)
    res.raise_for_status()
    if res.status_code == 200:
        setattr(config, f"access_token{count}", res.json().get("access_token"))
        setattr(config, f"token_type{count}", res.json().get("token_type"))
        setattr(config, f"last_token_time{count}", time.time())
    else:
        print(f"  [get_token{count}] ❌ トークン取得失敗: {res.status_code} {res.text}")
        setattr(config, f"access_token{count}", None)

def ensure_token(type="first"):
    count = "2" if type == "second" else ""
    access_token = getattr(config, f"access_token{count}")
    last_token_time = getattr(config, f"last_token_time{count}")

    if access_token is None:
        print (f"[ensure_token{count}] トークンを取得 (None)")
        get_token(type)
    elif (time.time() - last_token_time) >= config.TOKEN_EXPIRATION:
        print (f"[ensure_token{count}] トークンを取得 (期限切れ)")
        get_token(type)

def kill_token():
    headers = {
        "Authorization": f"{config.token_type} {config.access_token}"
    }
    try:
        res = requests.delete(f"https://account-public-service-prod.ol.epicgames.com/account/api/oauth/sessions/kill/{config.access_token}", headers=headers)
        if res.status_code == 204:
            print ("[kill_token] アカウントトークンの削除に成功")
        else:
            print (f"[kill_token] トークンの削除に失敗: {res.status_code} {res.text}")
    except Exception as e:
        print(f"[kill_token] ❌ トークンの削除に失敗: {e}")
        config.access_token = None
