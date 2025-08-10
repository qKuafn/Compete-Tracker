import os
from PIL import ImageDraw, ImageFont, Image

from dillyapis import fetch_export_data, get_image, get_loc_data
from files import load_png, sanitize_filename, format_number
import config
import config2

def fetch_data(Weapon_Path, local):
    Weapon_Data = fetch_export_data(Weapon_Path)
    
    WID = Weapon_Data[0].get("Name", "")
    
    Weapon_Name_key = Weapon_Data[0].get("Properties", {}).get("ItemName", {}).get("key", "")
    Request_Weapon_Name_key = Weapon_Name_key if Weapon_Name_key else Weapon_Data[0].get("Properties", {}).get("ItemName", {}).get("localizedString", "")
    Weapon_Name = config.loc_data.get(Request_Weapon_Name_key, "不明")
    
    Description_key = Weapon_Data[0].get("Properties", {}).get("ItemDescription", {}).get("key", "")
    Request_Description_key = Description_key if Description_key else Weapon_Data[0].get("Properties", {}).get("ItemDescription", {}).get("localizedString", "")
    Description_Data = config.loc_data.get(Request_Description_key, "不明")

    Rarity_Row = Weapon_Data[0].get("Properties", {}).get("Rarity", "")
    rarity = Rarity_Row.split("::")[-1]
    if not Rarity_Row:
        weapon_tags = Weapon_Data[0].get("Properties", {}).get("Tags", [])
        rarity_tag = next((tag for tag in weapon_tags if tag.startswith("Rarity.")), None)
        if rarity_tag:
            rarity = rarity_tag.split(".")[-1]
        else:
            rarity = "Uncommon"

    RangedWeapons_Path = None
    RangedWeapons_RowName = None
    RangedWeapons_WeaponData = None
    BulletsPerCartridge = None
    Ammo_Path = None
    Ammo_Data = None
    AmmoType_IconPath = None
    AmmoType_IconImage = None

    Stats_JP_Desc = []
    Stats_Data = []

    WeaponStatHandle = Weapon_Data[0].get("Properties", {}).get("WeaponStatHandle", {})           # Properties > WeaponStatHandle                           (RangedWeaponsの準備)
    RangedWeapons_Path = WeaponStatHandle.get("DataTable", {}).get("ObjectPath")                  # Properties > WeaponStatHandle > DataTable > ObjectPath  (RangedWeaponsのパス)
    RangedWeapons_RowName = WeaponStatHandle.get("RowName")                                       # Properties > WeaponStatHandle > RowName                 (RangedWeaponsのRow)
    Ammo_Path = Weapon_Data[0].get("Properties", {}).get("AmmoData", {}).get("AssetPathName")     # Properties > Ammodata > AssetPathName

    print (f"　      [DBG] 武器のパス : {Weapon_Path}")
    print (f"　      [DBG] 弾薬のパス : {Ammo_Path}")

    if "ConsumableItem" not in Weapon_Data[0].get("Properties", {}).get("CreativeTagsHelper", {}).get("CreativeTags", []):
        if RangedWeapons_Path and RangedWeapons_RowName:
            if RangedWeapons_Path not in config.RangedWeapons_Data_Cache:
                RangedWeapons_Data = fetch_export_data(RangedWeapons_Path)
                config.RangedWeapons_Data_Cache[RangedWeapons_Path] = RangedWeapons_Data
            else:
                print (f"      [INF] キャッシュからRangedWeaponsデータを取得 : {Ammo_Path}")

            RangedWeapons_WeaponData = config.RangedWeapons_Data_Cache.get(RangedWeapons_Path, [{}])[0].get("Rows", {}).get(RangedWeapons_RowName, {})

            if RangedWeapons_WeaponData:
                if any (key in RangedWeapons_WeaponData for key in ["DmgPB", "FiringRate", "ClipSize", "ReloadTime"]):
                    Stats_JP_Desc = [
                        "通常ダメージ",
                        "ヘッドショットダメージ",
                        "連射速度",
                        "マガジンサイズ",
                        "リロード時間"
                    ]
                    BulletsPerCartridge   = RangedWeapons_WeaponData.get("BulletsPerCartridge")         # １撃ごとの発射弾数
                    DamageZone_Critical   = RangedWeapons_WeaponData.get("DamageZone_Critical", 1)      # ヘッドショット時のダメージ倍率
                    MaxDamagePerCartridge = RangedWeapons_WeaponData.get("MaxDamagePerCartridge", -1)   # ダメージ上限

                    
                    DmgPB            = RangedWeapons_WeaponData.get("DmgPB", -1)
                    if BulletsPerCartridge:
                        DmgPB_Calculated = DmgPB * BulletsPerCartridge   # ショットガンは１撃で複数弾撃つ
                    else:
                        DmgPB_Calculated = DmgPB

                    # === ヘッドショットの分岐 ===
                    HeadShot_Normal = DmgPB_Calculated * DamageZone_Critical
                    if MaxDamagePerCartridge not in [0, -1]:
                        HeadShot_Shotgun = MaxDamagePerCartridge
                    elif MaxDamagePerCartridge in [0, -1]:
                        HeadShot_Shotgun = None

                    HeadShot_Dmg = min(HeadShot_Normal, HeadShot_Shotgun) if HeadShot_Shotgun else HeadShot_Normal  # 理論値の最大ダメージかダメージ上限、どちらか多いほう

                    # === 連射速度の分岐 (バースト武器) ===
                    FiringRate_Normal = RangedWeapons_WeaponData.get("FiringRate", -1)
                    CartridgePerFire  = RangedWeapons_WeaponData.get("CartridgePerFire")
                    BurstFiringRate   = RangedWeapons_WeaponData.get("BurstFiringRate")
                    if CartridgePerFire and BurstFiringRate:
                        FiringRate_Burst  = CartridgePerFire / ( (CartridgePerFire - 1) / BurstFiringRate + (1 / FiringRate_Normal) )
                    else:
                        FiringRate_Burst = None

                    FiringRate = FiringRate_Burst if (FiringRate_Burst and FiringRate_Burst != 0) else FiringRate_Normal

                    ClipSize     = RangedWeapons_WeaponData.get("ClipSize", -1)
                    ReloadTime   = RangedWeapons_WeaponData.get("ReloadTime", -1)

                    Stats_Data = [
                        f":  {format_number(DmgPB_Calculated)}",
                        f":  {format_number(HeadShot_Dmg)}",
                        f":  {format_number(FiringRate)}",
                        f":  {format_number(ClipSize)}",
                        f":  {format_number(ReloadTime)}"
                    ]
                else:
                    print (f"      [INF] RangedWeaponsの武器データ内に、適する数値データがありません")
            else:
                print (f"      [INF] RangedWeapons内に、武器に対応するRowがありません : {RangedWeapons_RowName}")
    elif "ConsumableItem" in Weapon_Data[0].get("Properties", {}).get("CreativeTagsHelper", {}).get("CreativeTags", []):
        print (f"      [INF] 消耗品のため、武器データの取得をスキップします")

    # === 弾薬のパスがある場合 (消耗品は、消耗品自身が弾薬として書かれているので除外) ===
    if Ammo_Path and Ammo_Path != Weapon_Path:
        if Ammo_Path in config.AmmoType_IconImage_Cache:
            AmmoType_IconImage = config.AmmoType_IconImage_Cache[Ammo_Path]
            print (f"      [INF] キャッシュから弾薬アイコンを取得 : {Ammo_Path}")
        else:
            Ammo_Data = fetch_export_data(Ammo_Path)
            AmmoType_IconPath = Ammo_Data[0].get("Properties", {}).get("AmmoIconBrush", {}).get("Brush_L", {}).get("ResourceObject", {}).get("ObjectPath", "")
            if AmmoType_IconPath and AmmoType_IconPath != "/Game/UI/Foundation/Textures/Icons/ItemTypes/T-Icon-Blank.0":
                # === 弾薬アイコンが武器名で保存されてしまうので、download=False (関数側のデフォルト) ===
                AmmoType_IconImage = get_image(AmmoType_IconPath)
                config.AmmoType_IconImage_Cache[Ammo_Path] = AmmoType_IconImage
            else:
                print ("      [INF] この弾薬には、弾薬アイコンはありません")
                config.AmmoType_IconImage_Cache[Ammo_Path] = None


    # === 武器が弾薬の場合、Ammo_Pathは取得できない ===
    elif not Ammo_Path:
        AmmoType_IconPath = Weapon_Data[0].get("Properties", {}).get("AmmoIconBrush", {}).get("Brush_L", {}).get("ResourceObject", {}).get("ObjectPath", "")
        if AmmoType_IconPath and AmmoType_IconPath != "/Game/UI/Foundation/Textures/Icons/ItemTypes/T-Icon-Blank.0":
                if AmmoType_IconPath in config.AmmoType_IconImage_Cache:
                    AmmoType_IconImage = config.AmmoType_IconImage_Cache[AmmoType_IconPath]
                    print ("      [INF] キャッシュから弾薬アイコンを取得")
                else:
                    AmmoType_IconImage = get_image(AmmoType_IconPath, Weapon_Name, download=True if local else False)
                    config.AmmoType_IconImage_Cache[AmmoType_IconPath] = AmmoType_IconImage
        else:
            print ("      [INF] この弾薬には、弾薬アイコンはありません")

    WeaponData_DataLists = Weapon_Data[0].get("Properties", {}).get("DataList", [])
    WeaponIcon_Path = None
    
    for DataList in WeaponData_DataLists:
        if "LargeIcon" in DataList:
            WeaponIcon_Path = DataList["LargeIcon"].get("AssetPathName")
            break
    if not WeaponIcon_Path:
        for DataList in WeaponData_DataLists:
            if "Icon" in DataList:
                WeaponIcon_Path = DataList["Icon"].get("AssetPathName")
    
    if local:
        Weapon_IconImage = get_image(WeaponIcon_Path, Weapon_Name, download=True)
    else:
        Weapon_IconImage = get_image(WeaponIcon_Path, Weapon_Name, download=False)

    return Weapon_Name, Description_Data, Stats_JP_Desc, Stats_Data, Weapon_Name, AmmoType_IconImage, Weapon_IconImage, WID, rarity

def create_image(weapon_path, local):
    WeaponName, Description, StatsDesc, Stats, WeaponName, AmmoTypeIcon, WeaponIcon, WID, rarity = fetch_data (weapon_path, local)
    
    try:
        if AmmoTypeIcon:
            BackgroundImage_Path = rf"./Images/{rarity}.png"
            BackgroundImage = load_png(BackgroundImage_Path)
        else:
            BackgroundImage_NoType_Path = rf"./Images/{rarity}_NoType.png"
            BackgroundImage = load_png(BackgroundImage_NoType_Path)

        if isinstance(WeaponIcon, tuple):
            print (WeaponIcon)
        if isinstance(WeaponIcon, Image.Image):
            WeaponIcon = WeaponIcon.resize((800, 800))

        BackgroundImage_width, BackgroundImage_height = BackgroundImage.size

        WeaponIcon_x = BackgroundImage_width - WeaponIcon.width - 80
        WeaponIcon_y = (BackgroundImage_height - WeaponIcon.height) // 2 

        BackgroundImage.paste(WeaponIcon, (WeaponIcon_x, WeaponIcon_y), WeaponIcon)

        font_dir = r"./Images/keifont.ttf"
        WeaponNameFont = ImageFont.truetype(font_dir, 50)
        DescriptionFont = ImageFont.truetype(font_dir, 30)
        StatsFont = ImageFont.truetype(font_dir, 40)
        WIDFont = ImageFont.truetype(font_dir, 35)

        draw = ImageDraw.Draw(BackgroundImage)

        draw.text((50, 50), WeaponName, font = WeaponNameFont, fill = "white")

        if Description:
            TotalLines  = 0         # 行数カウント
            x, y        = 50, 240   # Descriptionの入力開始位置
            MaxWidth    = 960       # Descriptionの横幅
            LineSpacing = 20        # 行間
            for paragraph in Description.split("\n"):
                Lines, LinesCount = wrap_text(draw, paragraph, DescriptionFont, MaxWidth)
                TotalLines += LinesCount
                for Line in Lines:
                    draw.text((x,y), Line, font = DescriptionFont, fill = "lightgray")
                    y += DescriptionFont.getbbox(Line)[3] + LineSpacing
        else:
            TotalLines = 0
        
        if AmmoTypeIcon:
            if isinstance(AmmoTypeIcon, tuple):
                print (AmmoTypeIcon)
            if isinstance(AmmoTypeIcon, Image.Image):
                AmmoTypeIcon = AmmoTypeIcon.resize((80, 80))
            else:
                print("[WRN] AmmoTypeIcon が画像として読み込まれていません")
            BackgroundImage.paste(AmmoTypeIcon, (50, 140), AmmoTypeIcon)

        StatsDesc_x = 50
        Stats_x = 470

        if TotalLines == 0 or TotalLines == 1:
            StatsDesc_y =380
            Stats_y = 380
            
        elif TotalLines ==2:
            StatsDesc_y = 420
            Stats_y = 420
        else:
            StatsDesc_y = 450
            Stats_y = 450
        
        for Row in StatsDesc:
            draw.text((StatsDesc_x, StatsDesc_y), Row, font = StatsFont, fill = "white")
            StatsDesc_y += 110
        
        for Row in Stats:
            draw.text((Stats_x, Stats_y), Row, font = StatsFont, fill = "white")
            Stats_y += 110
        
        Display_WID = f"ID : {WID}"
        WID_Image = Image.new("RGBA", (BackgroundImage_width, 60), (255, 255, 255, 0))
        ImageDraw.Draw(WID_Image).text((50, 0), Display_WID, font=WIDFont, fill="#9d9ca3")
        skewed_WID_Image = WID_Image.transform(WID_Image.size, Image.AFFINE, (1, 0.3, 0, 0, 1, 0), resample = Image.BICUBIC)
        BackgroundImage.paste(skewed_WID_Image, (0, BackgroundImage_height - 51), skewed_WID_Image)

        Save_WeaponName = sanitize_filename(WeaponName)

        if local:
            if rarity == "Transcendent":
                os.makedirs(rf"{config.Weap_dir}\エキゾチック", exist_ok=True)
                save_dir = rf"{config.Weap_dir}\エキゾチック\{Save_WeaponName}.png"
                BackgroundImage.save(save_dir)
                print(f"　  [INF] ⭕️ 合成画像保存完了: {rarity} {Save_WeaponName}")

            elif rarity == "Mythic":
                os.makedirs(rf"{config.Weap_dir}\ミシック", exist_ok=True)
                save_dir = rf"{config.Weap_dir}\ミシック\{Save_WeaponName}.png"
                BackgroundImage.save(save_dir)
                print(f"　  [INF] ⭕️ 合成画像保存完了: {rarity} {Save_WeaponName}")

            else:
                os.makedirs(rf"{config.Weap_dir}\{Save_WeaponName}", exist_ok=True)
                save_dir = rf"{config.Weap_dir}\{Save_WeaponName}\{WID}.png"
                BackgroundImage.save(save_dir)
                print(f"  　[INF] ⭕️ 合成画像保存完了: {rarity} {Save_WeaponName}")
        return BackgroundImage
    except Exception as e:
        print(f"　  [ERR] ❌️ 合成処理失敗: {e}")

def wrap_text(draw, text, font, max_width):
    lines = []
    buffer = ""
    force_wrap_width=860
    for char in text:
        buffer += char
        width = draw.textlength(buffer, font=font)
        if max_width < width <= force_wrap_width:
            punctuation_indices = [
                i for i in range(len(buffer))
                if buffer[i] in "、。!?！？"
                and draw.textlength(buffer[:i+1], font=font) <= force_wrap_width
            ]
            if punctuation_indices:
                split_idx = punctuation_indices[-1] + 1
                if split_idx == 1:
                    for i in range(len(buffer)):
                        if draw.textlength(buffer[:i+1], font=font) > force_wrap_width:
                            split_idx = i
                            break
                line = buffer[:split_idx]
                lines.append(line)
                buffer = buffer[split_idx:]
                continue
        for i in range(len(buffer)):
            if draw.textlength(buffer[:i+1], font=font) > force_wrap_width:
                line = buffer[:i]
                lines.append(line)
                buffer = buffer[i:]
                break
    while buffer:
        if draw.textlength(buffer, font=font) <= force_wrap_width:
            lines.append(buffer)
            buffer = ""
        else:
            for i in range(len(buffer)):
                if draw.textlength(buffer[:i+1], font=font) > force_wrap_width:
                    line = buffer[:i]
                    lines.append(line)
                    buffer = buffer[i:]
                    break

    i = 1
    while i < len(lines):
        if lines[i].startswith(("。", "、", "!", "?", "！", "？")):
            punct = lines[i][0]
            lines[i-1] += punct
            lines[i] = lines[i][1:].lstrip()
            if not lines[i]:
                lines.pop(i)
            else:
                i += 1
        else:
            i += 1
    LinesCount = len(lines)
    return lines, LinesCount

if __name__ == "__main__":
    create_image(weapon_path="", local=True)