from datetime import timezone, timedelta

RESPONSE_DIR = r"./response"
ARCHIVE_DIR = r"./response/Archive"
TOURNAMENT_DIR = r"./Tournament"
TOURNAMENT_ARCHIVE_DIR = r"./Tournament/Archive"
TEMP_DIR = r"./Temp"

JST = timezone(timedelta(hours=9))
UTC = timezone(timedelta(hours=0))

tags = []
updated_regions = []
playlist_tags = []
added_Tournaments = []
updated_Tournaments = []

Regions = ["ASIA", "EU", "NAC", "NAW", "OCE", "ME", "BR", "ONSITE"]
Lang = ["ja", "en"]

loc_data = {}
RangedWeapons_Data_Cache = {}
AmmoType_IconImage_Cache = {}

Tournament_Webhook = True
Hotfix_Webhook = True
Log_Webhook = True

test = False

if test is True:
    Tournament_Webhook = False
    Hotfix_Webhook = False

version = "++Fortnite+Release-36.20"
build = "43847582"