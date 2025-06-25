import requests
import time

import config

def get_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {config.AUTH_TOKEN}"
    }
    data = {
        "grant_type": "device_auth",
        "account_id": config.ACCOUNT_ID,
        "device_id": config.DEVICE_ID,
        "secret": config.SECRET,
    }
    try:
        res = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token", headers=headers, data=data)
        res.raise_for_status()
        config.access_token = res.json().get("access_token")
        config.token_type = res.json().get("token_type")
        config.last_token_time = time.time()
    except Exception as e:
        print(f"[get_token] ❌ トークン取得失敗: {e}")
        config.access_token = None

def ensure_token():
    if config.access_token is None:
        print ("[ensure_token] トークンを取得 (None)")
        get_token()
    if (time.time() - config.last_token_time) >= config.TOKEN_EXPIRATION:
        print ("[ensure_token] トークンを取得 (期限切れ)")
        get_token()

def get_token_for_format():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": f"Basic {config.AUTH_TOKEN}"
    }
    data = {
        "grant_type": "device_auth",
        "account_id": config.SECOND_ACCOUNT_ID,
        "device_id": config.SECOND_DEVICE_ID,
        "secret": config.SECOND_SECRET,
    }
    try:
        res = requests.post("https://account-public-service-prod.ol.epicgames.com/account/api/oauth/token", headers=headers, data=data)
        res.raise_for_status()
        config.access_token2 = res.json().get("access_token")
        config.token_type2 = res.json().get("token_type")
        config.last_token_time2 = time.time()
    except Exception as e:
        print(f"[get_token2] ❌ トークン取得失敗: {e}")
        config.access_token2 = None

def ensure_token_for_format():
    if config.access_token2 is None:
        print ("[ensure2] トークンを取得 (None)")
        get_token_for_format()
    if (time.time() - config.last_token_time2) >= config.TOKEN_EXPIRATION:
        print ("[ensure2] トークンを取得 (期限切れ)")
        get_token_for_format()