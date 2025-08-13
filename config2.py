RESPONSE_DIR = r"./response"
ARCHIVE_DIR = r"./response/Archive"
TOURNAMENT_DIR = r"./Tournament"
TOURNAMENT_ARCHIVE_DIR = r"./Tournament/Archive"
TEMP_DIR = r"./Temp"

Regions = ["ASIA", "EU", "NAC", "NAW", "OCE", "ME", "BR", "ONSITE"]
Lang = ["ja", "en"]

Tournament_Webhook = True
Hotfix_Webhook = True
Log_Webhook = True

test = True

if test is True:
    Tournament_Webhook = False
    Hotfix_Webhook = False