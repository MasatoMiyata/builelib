# 平成28年基準における空調設備の基準一次エネルギー消費量を求めるプログラム

import pandas as pd
import numpy as np
import json

from builelib import airconditioning_webpro

# json.dump用のクラス
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, set):
            return list(obj)
        else:
            return super(MyEncoder, self).default(obj)

def convert_heatsource_name(name):
    """熱源機種の読み替え
    Args:
        name: H25基準Webプログラムの機種名
    Returns:
        builelib_name: Builelibの機種名
    """
    if name == "空冷ヒートポンプ（スクロール，圧縮機台数制御）":
        builelib_name = "ウォータチリングユニット(空冷式)"
    elif name == "空冷ヒートポンプ":
        builelib_name = "ウォータチリングユニット(空冷式)"
    elif name == "電気式ビル用マルチ" or name == "ビル用マルチエアコン(電気式)":
        builelib_name = "パッケージエアコンディショナ(空冷式)"
    elif name == "ガス式ビル用マルチ":
        builelib_name = "ガスヒートポンプ冷暖房機(都市ガス)"
    elif name == "FF式暖房機(灯油)" or name == "FF式暖房機（灯油）":
        builelib_name = "FF式石油暖房機"
    else:
        print(name)
        raise Exception("熱源機種名称が不正です")
    
    return builelib_name

def convert_heatsource_energy(name,energy):
    """熱源機種ごとにエネルギー消費量を算出
    Args:
        name: 機種名
        energy: 入力されたエネルギー消費量
    Returns:
        E: 電力消費量
        G: 燃料消費量
    """
    if name == "空冷ヒートポンプ（スクロール，圧縮機台数制御）":
        E = energy
        G = 0
    elif name == "空冷ヒートポンプ":
        E = energy
        G = 0
    elif name == "電気式ビル用マルチ" or name == "ビル用マルチエアコン(電気式)":
        E = energy
        G = 0
    elif name == "ガス式ビル用マルチ":
        E = 0
        G = energy
    elif name == "FF式暖房機(灯油)" or name == "FF式暖房機（灯油）":
        E = 0
        G = energy
    else:
        print(name)
        raise Exception("熱源機種名称が不正です")
    
    return E, G


# 設定ファイル
setting_filename  = "./standard_spec/基準値計算設定ファイル_20150904.xlsx"
# テンプレートファイル
template_filename = "./standard_spec/template.json"


#---------------------------------------------------------------------
# 計算開始
#---------------------------------------------------------------------
for iRESION in [1,2,3,4,5,6,7,8]:

    if iRESION in [1,2]:
        sheetname = "地域1_2"
    elif iRESION in [3,4]:
        sheetname = "地域3_4"
    elif iRESION in [5,6,7]:
        sheetname = "地域5_6_7"
    elif iRESION in [8]:
        sheetname = "地域8"

    # 設定ファイルの読み込み
    df_spec = pd.read_excel(setting_filename, sheet_name=sheetname, header=0, index_col=0)

    result = []

    for case_id in df_spec:

        df = df_spec[case_id].copy()
        result_room_type = []
            
        for iBLDG in ["中間階", "最上階", "オールインテリア"]:   # 形状（中間階、最上階、オールインテリア）

            for iMODEL in ["5m","10m","20m"]:   # 奥行き（5m, 10m, 20m）
            
                # 床面積 [m2] = 10m×奥行き
                if iMODEL == "5m":
                    Sf =  50
                elif iMODEL == "10m":
                    Sf = 100
                elif iMODEL == "20m":
                    Sf = 200

                # 方位
                for DIRECTION in ["北","東","南","西"]:

                    #---------------------------
                    # テンプレートファイルの読み込み
                    #---------------------------
                    with open(template_filename, 'r', encoding='utf-8') as f:
                        bldgdata = json.load(f)
            
                    #---------------------------
                    # 地域
                    #---------------------------
                    bldgdata["Building"]["Region"] = str(iRESION)

                    #---------------------------
                    # 建物用途・室用途、階高、天井高、床面積
                    #---------------------------
                    bldgdata["Rooms"]["室"]["buildingType"] = df["建物用途大分類"]
                    bldgdata["Rooms"]["室"]["roomType"] = df["建物用途小分類"]
                    bldgdata["Rooms"]["室"]["floorHeight"] = df["階高"]
                    bldgdata["Rooms"]["室"]["ceilingHeight"] = df["階高"]-1
                    bldgdata["Rooms"]["室"]["roomArea"] = Sf

                    #---------------------------
                    # 外皮
                    #---------------------------
                    # 外皮面積[m2] (幅を10mとする)
                    St = 10 * df["階高"]

                    if iBLDG == "中間階":

                        bldgdata["EnvelopeSet"]["室"]["WallList"][0]["Direction"] = DIRECTION
                        bldgdata["EnvelopeSet"]["室"]["WallList"][0]["EnvelopeArea"] = St
                        bldgdata["EnvelopeSet"]["室"]["WallList"][0]["WallSpec"] = df["外壁材質構成（WCON）"]

                        if df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm":
                            Uvalue = 4.11 
                            Mvalue = 0.63
                            layerType = "複層"
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm_ブラインド":
                            Uvalue = 3.68 
                            Mvalue = 0.46
                            layerType = "複層"
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm_lowE":
                            Uvalue = 3.65 
                            Mvalue = 0.32
                            layerType = "複層"
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "単板ガラス":
                            Uvalue = 6.09 
                            Mvalue = 0.70
                            layerType = "単層"
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "単板ガラス_ブラインド":
                            Uvalue = 5.27 
                            Mvalue = 0.50
                            layerType = "単層"

                        bldgdata["WindowConfigure"]["WIND"]= {
                                "windowArea": St * df["窓面積率"],
                                "windowWidth": None,
                                "windowHeight": None,
                                "inputMethod": "性能値を入力",
                                "windowUvalue": Uvalue,
                                "windowIvalue": Mvalue,
                                "layerType": layerType,
                                "glassUvalue": None,
                                "glassIvalue": None,
                                "Info": ""
                            }

                    elif iBLDG == "最上階":

                        bldgdata["EnvelopeSet"]["室"]["WallList"][0]["Direction"] = DIRECTION
                        bldgdata["EnvelopeSet"]["室"]["WallList"][0]["EnvelopeArea"] = St
                        bldgdata["EnvelopeSet"]["室"]["WallList"][0]["WallSpec"] = df["外壁材質構成（WCON）"]

                        if df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm":
                            Uvalue = 4.11 
                            Mvalue = 0.63
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm_ブラインド":
                            Uvalue = 3.68 
                            Mvalue = 0.46
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "複層_空気層6mm_lowE":
                            Uvalue = 3.65 
                            Mvalue = 0.32
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "単板ガラス":
                            Uvalue = 6.09 
                            Mvalue = 0.70
                        elif df["窓ガラス種類、厚さ、ブラインドの有無（WIND）"] == "単板ガラス_ブラインド":
                            Uvalue = 5.27 
                            Mvalue = 0.50

                        bldgdata["WindowConfigure"]["WIND"]= {
                                "windowArea": St * df["窓面積率"],
                                "windowWidth": None,
                                "windowHeight": None,
                                "inputMethod": "性能値を入力",
                                "windowUvalue": Uvalue,
                                "windowIvalue": Mvalue,
                                "layerType": "単層",
                                "glassUvalue": None,
                                "glassIvalue": None,
                                "Info": ""
                            }

                        bldgdata["EnvelopeSet"]["室"]["WallList"].append(
                                {
                                    "Direction": "水平",
                                    "EnvelopeArea": Sf,
                                    "EnvelopeWidth": None,
                                    "EnvelopeHeight": None,
                                    "WallSpec": df["屋根材質構成（WCON）"],
                                    "WallType": "日の当たる外壁",
                                    "WindowList": [
                                    ]
                                }
                            )

                    elif iBLDG == "オールインテリア":
                        bldgdata["EnvelopeSet"]["室"]["WallList"] = []


                    #---------------------------
                    # 熱源仕様（冷熱）
                    #---------------------------
                    if df["台数制御（冷熱）"] == "有":
                        bldgdata["HeatsourceSystem"]["RCH"]["冷房"]["isStagingControl"] = "有"
                    elif df["台数制御（冷熱）"] == "無":
                        bldgdata["HeatsourceSystem"]["RCH"]["冷房"]["isStagingControl"] = "無"

                    if df["一次ポンプWTF（冷熱1台目）"] == 0:
                        PrimaryPumpPowerConsumption =  0
                    else:
                        PrimaryPumpPowerConsumption =  df["床面積あたりの熱源容量（冷熱1台目）"]*Sf / df["一次ポンプWTF（冷熱1台目）"]

                    bldgdata["HeatsourceSystem"]["RCH"]["冷房"]["Heatsource"].append( {
                                "HeatsourceType": convert_heatsource_name(df["熱源種類（冷熱1台目）"]),
                                "Number": 1.0,
                                "SupplyWaterTempSummer": 7,
                                "SupplyWaterTempMiddle": 7,
                                "SupplyWaterTempWinter": 7,
                                "HeatsourceRatedCapacity": df["床面積あたりの熱源容量（冷熱1台目）"]*Sf,
                                "HeatsourceRatedPowerConsumption": convert_heatsource_energy(df["熱源種類（冷熱1台目）"],df["床面積あたりの主機定格エネルギー消費量（冷熱1台目）"]*Sf)[0],
                                "HeatsourceRatedFuelConsumption": convert_heatsource_energy(df["熱源種類（冷熱1台目）"],df["床面積あたりの主機定格エネルギー消費量（冷熱1台目）"]*Sf)[1],
                                "Heatsource_sub_RatedPowerConsumption": df["床面積あたりの補機定格消費電力（冷熱1台目）"]*Sf,
                                "PrimaryPumpPowerConsumption": PrimaryPumpPowerConsumption,
                                "PrimaryPumpContolType": "無",
                                "CoolingTowerCapacity": df["床面積あたりの熱源容量（冷熱1台目）"]*Sf,
                                "CoolingTowerFanPowerConsumption": df["冷却塔ファン定格消費電力（冷熱1台目）"]*Sf,
                                "CoolingTowerPumpPowerConsumption": df["冷却水ポンプ定格消費電力（冷熱1台目）"]*Sf,
                                "CoolingTowerContolType": "無",
                                "Info": ""
                            }
                        )

                    if pd.isna(df["熱源種類（冷熱2台目）"]) == False:

                        if df["一次ポンプWTF（冷熱2台目）"] == 0:
                            PrimaryPumpPowerConsumption =  0
                        else:
                            PrimaryPumpPowerConsumption =  df["床面積あたりの熱源容量（冷熱2台目）"]*Sf / df["一次ポンプWTF（冷熱2台目）"]

                        bldgdata["HeatsourceSystem"]["RCH"]["冷房"]["Heatsource"].append( {
                                    "HeatsourceType": convert_heatsource_name(df["熱源種類（冷熱2台目）"]),
                                    "Number": 1.0,
                                    "SupplyWaterTempSummer": 7,
                                    "SupplyWaterTempMiddle": 7,
                                    "SupplyWaterTempWinter": 7,
                                    "HeatsourceRatedCapacity": df["床面積あたりの熱源容量（冷熱2台目）"]*Sf,
                                "HeatsourceRatedPowerConsumption": convert_heatsource_energy(df["熱源種類（冷熱2台目）"],df["床面積あたりの主機定格エネルギー消費量（冷熱2台目）"]*Sf)[0],
                                "HeatsourceRatedFuelConsumption": convert_heatsource_energy(df["熱源種類（冷熱2台目）"],df["床面積あたりの主機定格エネルギー消費量（冷熱2台目）"]*Sf)[1],
                                    "Heatsource_sub_RatedPowerConsumption": df["床面積あたりの補機定格消費電力（冷熱2台目）"]*Sf,
                                    "PrimaryPumpPowerConsumption": PrimaryPumpPowerConsumption,
                                    "PrimaryPumpContolType": "無",
                                    "CoolingTowerCapacity": df["床面積あたりの熱源容量（冷熱2台目）"]*Sf,
                                    "CoolingTowerFanPowerConsumption": df["冷却塔ファン定格消費電力（冷熱2台目）"]*Sf,
                                    "CoolingTowerPumpPowerConsumption": df["冷却水ポンプ定格消費電力（冷熱2台目）"]*Sf,
                                    "CoolingTowerContolType": "無",
                                    "Info": ""
                                }
                            )

                    if pd.isna(df["熱源種類（冷熱3台目）"]) == False:

                        if df["一次ポンプWTF（冷熱3台目）"] == 0:
                            PrimaryPumpPowerConsumption =  0
                        else:
                            PrimaryPumpPowerConsumption =  df["床面積あたりの熱源容量（冷熱3台目）"]*Sf / df["一次ポンプWTF（冷熱3台目）"]

                        bldgdata["HeatsourceSystem"]["RCH"]["冷房"]["Heatsource"].append( {
                                    "HeatsourceType": convert_heatsource_name(df["熱源種類（冷熱3台目）"]),
                                    "Number": 1.0,
                                    "SupplyWaterTempSummer": 7,
                                    "SupplyWaterTempMiddle": 7,
                                    "SupplyWaterTempWinter": 7,
                                    "HeatsourceRatedCapacity": df["床面積あたりの熱源容量（冷熱3台目）"]*Sf,
                                "HeatsourceRatedPowerConsumption": convert_heatsource_energy(df["熱源種類（冷熱3台目）"],df["床面積あたりの主機定格エネルギー消費量（冷熱3台目）"]*Sf)[0],
                                "HeatsourceRatedFuelConsumption": convert_heatsource_energy(df["熱源種類（冷熱3台目）"],df["床面積あたりの主機定格エネルギー消費量（冷熱3台目）"]*Sf)[1],
                                    "Heatsource_sub_RatedPowerConsumption": df["床面積あたりの補機定格消費電力（冷熱3台目）"]*Sf,
                                    "PrimaryPumpPowerConsumption": PrimaryPumpPowerConsumption,
                                    "PrimaryPumpContolType": "無",
                                    "CoolingTowerCapacity": df["床面積あたりの熱源容量（冷熱3台目）"]*Sf,
                                    "CoolingTowerFanPowerConsumption": df["冷却塔ファン定格消費電力（冷熱3台目）"]*Sf,
                                    "CoolingTowerPumpPowerConsumption": df["冷却水ポンプ定格消費電力（冷熱3台目）"]*Sf,
                                    "CoolingTowerContolType": "無",
                                    "Info": ""
                                }
                            )

                    #---------------------------
                    # 熱源仕様（温熱）
                    #---------------------------
                    if df["台数制御（温熱）"] == "有":
                        bldgdata["HeatsourceSystem"]["RCH"]["暖房"]["isStagingControl"] = "有"
                    elif df["台数制御（温熱）"] == "無":
                        bldgdata["HeatsourceSystem"]["RCH"]["暖房"]["isStagingControl"] = "無"

                    if df["一次ポンプWTF（温熱1台目）"] == 0:
                        PrimaryPumpPowerConsumption =  0
                    else:
                        PrimaryPumpPowerConsumption =  df["床面積あたりの熱源容量（温熱1台目）"]*Sf / df["一次ポンプWTF（温熱1台目）"]

                    bldgdata["HeatsourceSystem"]["RCH"]["暖房"]["Heatsource"].append( {
                                "HeatsourceType": convert_heatsource_name(df["熱源種類（温熱1台目）"]),
                                "Number": 1.0,
                                "SupplyWaterTempSummer": 42,
                                "SupplyWaterTempMiddle": 42,
                                "SupplyWaterTempWinter": 42,
                                "HeatsourceRatedCapacity": df["床面積あたりの熱源容量（温熱1台目）"]*Sf,
                                "HeatsourceRatedPowerConsumption": convert_heatsource_energy(df["熱源種類（温熱1台目）"],df["床面積あたりの主機定格エネルギー消費量（温熱1台目）"]*Sf)[0],
                                "HeatsourceRatedFuelConsumption": convert_heatsource_energy(df["熱源種類（温熱1台目）"],df["床面積あたりの主機定格エネルギー消費量（温熱1台目）"]*Sf)[1],
                                "Heatsource_sub_RatedPowerConsumption": df["床面積あたりの補機定格消費電力（温熱1台目）"]*Sf,
                                "PrimaryPumpPowerConsumption": PrimaryPumpPowerConsumption,
                                "PrimaryPumpContolType": "無",
                                "CoolingTowerCapacity": 0,
                                "CoolingTowerFanPowerConsumption": 0,
                                "CoolingTowerPumpPowerConsumption": 0,
                                "CoolingTowerContolType": "無",
                                "Info": ""
                            }
                        )

                    if pd.isna(df["熱源種類（温熱2台目）"]) == False:

                        if df["一次ポンプWTF（温熱2台目）"] == 0:
                            PrimaryPumpPowerConsumption =  0
                        else:
                            PrimaryPumpPowerConsumption =  df["床面積あたりの熱源容量（温熱2台目）"]*Sf / df["一次ポンプWTF（温熱2台目）"]

                        bldgdata["HeatsourceSystem"]["RCH"]["暖房"]["Heatsource"].append( {
                                    "HeatsourceType": convert_heatsource_name(df["熱源種類（温熱2台目）"]),
                                    "Number": 1.0,
                                    "SupplyWaterTempSummer": 42,
                                    "SupplyWaterTempMiddle": 42,
                                    "SupplyWaterTempWinter": 42,
                                    "HeatsourceRatedCapacity": df["床面積あたりの熱源容量（温熱2台目）"]*Sf,
                                "HeatsourceRatedPowerConsumption": convert_heatsource_energy(df["熱源種類（温熱2台目）"],df["床面積あたりの主機定格エネルギー消費量（温熱2台目）"]*Sf)[0],
                                "HeatsourceRatedFuelConsumption": convert_heatsource_energy(df["熱源種類（温熱2台目）"],df["床面積あたりの主機定格エネルギー消費量（温熱2台目）"]*Sf)[1],
                                    "Heatsource_sub_RatedPowerConsumption": df["床面積あたりの補機定格消費電力（温熱2台目）"]*Sf,
                                    "PrimaryPumpPowerConsumption": PrimaryPumpPowerConsumption,
                                    "PrimaryPumpContolType": "無",
                                    "CoolingTowerCapacity": 0,
                                    "CoolingTowerFanPowerConsumption": 0,
                                    "CoolingTowerPumpPowerConsumption": 0,
                                    "CoolingTowerContolType": "無",
                                    "Info": ""
                                }
                            )

                    if pd.isna(df["熱源種類（温熱3台目）"]) == False:

                        if df["一次ポンプWTF（温熱3台目）"] == 0:
                            PrimaryPumpPowerConsumption =  0
                        else:
                            PrimaryPumpPowerConsumption =  df["床面積あたりの熱源容量（温熱3台目）"]*Sf / df["一次ポンプWTF（温熱3台目）"]

                        bldgdata["HeatsourceSystem"]["RCH"]["暖房"]["Heatsource"].append( {
                                    "HeatsourceType": convert_heatsource_name(df["熱源種類（温熱3台目）"]),
                                    "Number": 1.0,
                                    "SupplyWaterTempSummer": 42,
                                    "SupplyWaterTempMiddle": 42,
                                    "SupplyWaterTempWinter": 42,
                                    "HeatsourceRatedCapacity": df["床面積あたりの熱源容量（温熱3台目）"]*Sf,
                                "HeatsourceRatedPowerConsumption": convert_heatsource_energy(df["熱源種類（温熱3台目）"],df["床面積あたりの主機定格エネルギー消費量（温熱3台目）"]*Sf)[0],
                                "HeatsourceRatedFuelConsumption": convert_heatsource_energy(df["熱源種類（温熱3台目）"],df["床面積あたりの主機定格エネルギー消費量（温熱3台目）"]*Sf)[1],
                                    "Heatsource_sub_RatedPowerConsumption": df["床面積あたりの補機定格消費電力（温熱3台目）"]*Sf,
                                    "PrimaryPumpPowerConsumption": PrimaryPumpPowerConsumption,
                                    "PrimaryPumpContolType": "無",
                                    "CoolingTowerCapacity": 0,
                                    "CoolingTowerFanPowerConsumption": 0,
                                    "CoolingTowerPumpPowerConsumption": 0,
                                    "CoolingTowerContolType": "無",
                                    "Info": ""
                                }
                            )

                    #---------------------------
                    # 二次ポンプ（冷水ポンプ）
                    #---------------------------
                    if df["冷水ポンプ台数"] > 0 or df["温水ポンプ台数"] > 0:
                        bldgdata["SecondaryPumpSystem"]["PCH"] = {}
                        
                    if df["冷水ポンプ台数"] > 0:

                        if df["冷水ポンプ制御方式"] == "VWV":
                            ContolType = "回転数制御"
                            MinOpeningRate = 60
                        else:
                            ContolType = "定流量制御"
                            MinOpeningRate = 100

                        Qpump = df["冷水ポンプ能力"]*Sf

                        SecondaryPump = []
                        for ipump in range(df["冷水ポンプ台数"]):
                            SecondaryPump.append(
                                {
                                    "Number": 1.0,
                                    "RatedWaterFlowRate": 3600*Qpump/(4200*df["冷水ポンプ往還温度差"])/df["冷水ポンプ台数"],
                                    "RatedPowerConsumption": Qpump/df["冷水ポンプWTF"]/df["冷水ポンプ台数"],
                                    "ContolType": ContolType,
                                    "MinOpeningRate": MinOpeningRate,
                                    "Info": ""
                                }
                            )

                        bldgdata["SecondaryPumpSystem"]["PCH"]["冷房"] = {
                                "TemperatureDifference": df["冷水ポンプ往還温度差"],
                                "isStagingControl": df["冷水ポンプ台数制御"],
                                "SecondaryPump": SecondaryPump
                                }

                    #---------------------------
                    # 二次ポンプ（温水ポンプ）
                    #---------------------------                    
                    if df["温水ポンプ台数"] > 0:

                        if df["温水ポンプ制御方式"] == "VWV":
                            ContolType = "回転数制御"
                            MinOpeningRate = 60
                        else:
                            ContolType = "定流量制御"
                            MinOpeningRate = 100

                        Qpump = df["温水ポンプ能力"]*Sf

                        SecondaryPump = []
                        for ipump in range(df["温水ポンプ台数"]):

                            SecondaryPump.append(
                                {
                                    "Number": 1.0,
                                    "RatedWaterFlowRate": 3600*Qpump/(4200*df["温水ポンプ往還温度差"])/df["温水ポンプ台数"],
                                    "RatedPowerConsumption": Qpump/df["温水ポンプWTF"]/df["温水ポンプ台数"],
                                    "ContolType": ContolType,
                                    "MinOpeningRate": MinOpeningRate,
                                    "Info": ""
                                }
                            )

                        bldgdata["SecondaryPumpSystem"]["PCH"]["暖房"] = {
                                "TemperatureDifference": df["温水ポンプ往還温度差"],
                                "isStagingControl": df["温水ポンプ台数制御"],
                                "SecondaryPump": SecondaryPump
                                }

                    #---------------------------
                    # 空調機（1台目）
                    #---------------------------
                    if df["空調機タイプ（１台目）"] == "室内機":
                        if df["冷水ポンプ台数"] == 0:
                            bldgdata["AirHandlingSystem"]["ACP-1"]["Pump_cooling"] = None
                        if df["温水ポンプ台数"] == 0:
                            bldgdata["AirHandlingSystem"]["ACP-1"]["Pump_heating"] = None

                    bldgdata["AirHandlingSystem"]["ACP-1"]["isOutdoorAirCut"] = df["外気カット制御（１台目）"]
                    bldgdata["AirHandlingSystem"]["ACP-1"]["isEconomizer"] = df["外気冷房制御（１台目）"]
                    bldgdata["AirHandlingSystem"]["ACP-1"]["EconomizerMaxAirVolume"] = df["床面積あたりの定格給気風量（１台目）"]*Sf*1000

                    if df["風量制御方式（１台目）"] == "CAV":
                        FanControlType = "無"
                        FanMinOpeningRate = 100
                    elif df["風量制御方式（１台目）"] == "VAV":
                        FanControlType = "回転数制御"
                        FanMinOpeningRate = 65

                    if pd.isna(df["空調機タイプ（2台目）"]) and df["全熱交換機制御"] == "有":
                        AirHeatExchangeRatioCooling = 50
                        AirHeatExchangeRatioHeating = 50
                        AirHeatExchangerControl = "無"
                        AirHeatExchangerPowerConsumption = df["全熱交換機ローター消費電力"]*Sf
                    else:
                        AirHeatExchangeRatioCooling = None
                        AirHeatExchangeRatioHeating = None
                        AirHeatExchangerControl = "無"
                        AirHeatExchangerPowerConsumption = 0

                    bldgdata["AirHandlingSystem"]["ACP-1"]["AirHandlingUnit"].append( {
                            "Type": df["空調機タイプ（１台目）"],
                            "Number": 1.0,
                            "RatedCapacityCooling": df["床面積あたりの定格冷房能力（１台目）"]*Sf,
                            "RatedCapacityHeating": df["床面積あたりの定格暖房能力（１台目）"]*Sf,
                            "FanType": None,
                            "FanAirVolume": df["床面積あたりの定格給気風量（１台目）"]*Sf*1000,
                            "FanPowerConsumption": df["床面積あたりの定格冷房能力（１台目）"]*Sf/ df["給気/排気/外気ファンATF（１台目）"],
                            "FanControlType": FanControlType,
                            "FanMinOpeningRate": FanMinOpeningRate,
                            "AirHeatExchangeRatioCooling": AirHeatExchangeRatioCooling,
                            "AirHeatExchangeRatioHeating": AirHeatExchangeRatioHeating,
                            "AirHeatExchangerEffectiveAirVolumeRatio": None,
                            "AirHeatExchangerControl": AirHeatExchangerControl,
                            "AirHeatExchangerPowerConsumption": AirHeatExchangerPowerConsumption,
                            "Info": ""
                        })
                    
                    #---------------------------
                    # 空調機（2台目）
                    #---------------------------
                    if pd.isna(df["空調機タイプ（2台目）"]) == False:

                        bldgdata["AirHandlingSystem"]["ACP-2"] = {
                                "isEconomizer": "無",
                                "EconomizerMaxAirVolume": None,
                                "isOutdoorAirCut": "無",
                                "Pump_cooling": "PCH",
                                "Pump_heating": "PCH",
                                "HeatSource_cooling": "RCH",
                                "HeatSource_heating": "RCH",
                                "AirHandlingUnit": []
                            }

                        if df["風量制御方式（2台目）"] == "CAV":
                            FanControlType = "無"
                            FanMinOpeningRate = 100
                        elif df["風量制御方式（2台目）"] == "VAV":
                            FanControlType = "回転数制御"
                            FanMinOpeningRate = 65

                        if df["全熱交換機制御"] == "有":
                            AirHeatExchangeRatioCooling = 50
                            AirHeatExchangeRatioHeating = 50
                            AirHeatExchangerControl = "無"
                            AirHeatExchangerPowerConsumption = df["全熱交換機ローター消費電力"]*Sf
                        else:
                            AirHeatExchangeRatioCooling = None
                            AirHeatExchangeRatioHeating = None
                            AirHeatExchangerControl = "無"
                            AirHeatExchangerPowerConsumption = 0

                        if df["空調機タイプ（2台目）"] == "室内機":
                            if df["冷水ポンプ台数"] == 0:
                                bldgdata["AirHandlingSystem"]["ACP-2"]["Pump_cooling"] = None
                            if df["温水ポンプ台数"] == 0:
                                bldgdata["AirHandlingSystem"]["ACP-2"]["Pump_heating"] = None

                        bldgdata["AirHandlingSystem"]["ACP-2"]["isOutdoorAirCut"] = df["外気カット制御（2台目）"]
                        bldgdata["AirHandlingSystem"]["ACP-2"]["isEconomizer"] = df["外気冷房制御（2台目）"]
                        bldgdata["AirHandlingSystem"]["ACP-2"]["EconomizerMaxAirVolume"] = df["床面積あたりの定格給気風量（2台目）"]*Sf*1000

                        if df["空調機タイプ（2台目）"] == "外調機":
                            Type = "空調機"
                        else:
                            Type = df["空調機タイプ（2台目）"]

                        bldgdata["AirHandlingSystem"]["ACP-2"]["AirHandlingUnit"].append({
                                "Type": Type,
                                "Number": 1.0,
                                "RatedCapacityCooling": df["床面積あたりの定格冷房能力（2台目）"]*Sf,
                                "RatedCapacityHeating": df["床面積あたりの定格暖房能力（2台目）"]*Sf,
                                "FanType": None,
                                "FanAirVolume": df["床面積あたりの定格給気風量（2台目）"]*Sf*1000,
                                "FanPowerConsumption": df["床面積あたりの定格冷房能力（2台目）"]*Sf/ df["給気/排気/外気ファンATF（2台目）"],
                                "FanControlType": FanControlType,
                                "FanMinOpeningRate": FanMinOpeningRate,
                                "AirHeatExchangeRatioCooling": AirHeatExchangeRatioCooling,
                                "AirHeatExchangeRatioHeating": AirHeatExchangeRatioHeating,
                                "AirHeatExchangerEffectiveAirVolumeRatio": None,
                                "AirHeatExchangerControl": AirHeatExchangerControl,
                                "AirHeatExchangerPowerConsumption": AirHeatExchangerPowerConsumption,
                                "Info": ""
                            })
                        
                        bldgdata["AirConditioningZone"]["室"]["AHU_cooling_outdoorLoad"] = "ACP-2"
                        bldgdata["AirConditioningZone"]["室"]["AHU_heating_outdoorLoad"] = "ACP-2"

                    #---------------------------
                    # 計算実行
                    #---------------------------
                        
                    is_calc = False
                    # オールインテリアは5m, 北側のみ計算
                    if iBLDG == "オールインテリア":
                        if iMODEL == "5m" and DIRECTION == "北":
                            is_calc = True
                    else:
                        is_calc = True

                    if is_calc:
                            
                        print(f"計算中: {iRESION}地域  {df['建物用途大分類']} - {df['建物用途小分類']}, {iBLDG}, {iMODEL}, {DIRECTION}")

                        # json出力（検証用）
                        # with open("standard_value_input.json",'w', encoding='utf-8') as fw:
                        #     json.dump(bldgdata,fw,indent=4,ensure_ascii=False)
                        
                        # buielib/ACの実行
                        resultdata_AC = airconditioning_webpro.calc_energy(bldgdata, debug = False)
                        
                        # 設計一次エネ・基準一次エネ
                        print(resultdata_AC["設計一次エネルギー消費量[MJ/年]"]/Sf)
                        print(resultdata_AC["基準一次エネルギー消費量[MJ/年]"]/Sf)

                        result_room_type.append(resultdata_AC["設計一次エネルギー消費量[MJ/年]"]/Sf)

        result.append(result_room_type)

    np.savetxt('平成28年基準_基準一次エネルギー再現_'+ str(iRESION) +'地域.csv', result, fmt='%.6f', delimiter=',') 


