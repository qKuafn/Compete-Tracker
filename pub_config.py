from datetime import timezone, timedelta

RESPONSE_DIR = "./response"
ARCHIVE_DIR = "./response/Archive"
TOURNAMENT_DIR = "./Tournament"
TOURNAMENT_ARCHIVE_DIR = "./Tournament/Archive"

JST = timezone(timedelta(hours=9))
UTC = timezone(timedelta(hours=0))

Regions = ["ASIA", "EU", "NAC", "NAW", "OCE", "ME", "BR", "ONSITE"]
Lang = ["ja", "en"]

Webhook1 = True
Webhook2 = True

Hotfix_Webhook = True

test = True

if test is True:
    Webhook1 = False
    Hotfix_Webhook = False

version = "++Fortnite+Release-36.10"
build = "43713507"

main_type = "first"