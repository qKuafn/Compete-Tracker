import requests
import time

import config

def get_token(type="first"):
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
    if res.status_code == 200:
        print(f"  [INF] ⭕️ トークン取得成功 (Acc:{type})")
        setattr(config, f"access_token{count}", res.json().get("access_token"))
        setattr(config, f"token_type{count}", res.json().get("token_type"))
        setattr(config, f"last_token_time{count}", time.time())
    else:
        print(f"  [ERR] ❌ トークン取得失敗 (Acc:{type}) : {res.status_code} {res.text}")
        setattr(config, f"access_token{count}", None)

def ensure_token(type="first"):
    count = "2" if type == "second" else ""
    access_token = getattr(config, f"access_token{count}")
    last_token_time = getattr(config, f"last_token_time{count}")

    if access_token is None:
        print (f"[INF] トークンを取得 (None) (Acc:{type})")
        get_token(type)
    elif (time.time() - last_token_time) >= config.TOKEN_EXPIRATION:
        print (f"[INF] トークンを取得 (期限切れ) (Acc:{type})")
        get_token(type)

def kill_token(type="first"):
    count = "2" if type == "second" else ""
    token_type = getattr(config, f"token_type{count}")
    access_token = getattr(config, f"access_token{count}")
    headers = {
        "Authorization": f"{token_type} {access_token}"
    }
    try:
        res = requests.delete(f"https://account-public-service-prod.ol.epicgames.com/account/api/oauth/sessions/kill/{access_token}", headers=headers)
        if res.status_code == 204:
            print (f"[INF] ⭕️ トークンの削除に成功 (Acc:{type})")
        else:
            print (f"[ERR] ❌️ トークンの削除に失敗 (Acc:{type}) : {res.status_code} {res.text}")
    except Exception as e:
        print(f"[ERR] ❌ トークンの削除に失敗 (Acc:{type}) : {e}")
        config.access_token = None
