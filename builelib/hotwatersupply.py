# %%
import sys
import json
import jsonschema
import numpy as np
import math

if 'ipykernel' in sys.modules:
    import builelib_common as bc
    import climate
    import shading
elif __name__ == '__main__':
    import builelib_common as bc
    import climate
    import shading
else:
    import builelib.builelib_common as bc
    import bulielib.climate as climate
    import builelib.shading as shading

if __name__ == '__main__':
    import builelib_common as bc
else:
    import builelib.builelib_common as bc

if 'ipykernel' in sys.modules:
    directory = "./database/"
else:
    directory = "./builelib/database/"


filename = '../sample/給湯のサンプル.json'

DEBUG = True


# %%
# ----------------------------------------------------------------------------------
# 入力ファイル（jsonファイル）の指定
# ----------------------------------------------------------------------------------

# 入力データ（json）の読み込み
with open(filename, 'r') as f:
    inputdata = json.load(f)



# %%
# ----------------------------------------------------------------------------------
# 解説書 D.6 日平均給水温度
# ----------------------------------------------------------------------------------

# 地域別データの読み込み
with open(directory + 'AREA.json', 'r') as f:
    Area = json.load(f)

# 外気温データ（DAT形式）読み込み ＜365の行列＞
Toa_ave = climate.readDatClimateData(directory + "climatedata/" +
                                Area[inputdata["Building"]["Region"]+"地域"]["気象データファイル名（給湯）"])

_, _, Iod, Ios, Inn = climate.readHaspClimateData(directory + "climatedata/C1_" +
                                Area[inputdata["Building"]["Region"]+"地域"]["気象データファイル名"])


# 空調運転モード
with open(directory + 'ACoperationMode.json', 'r') as f:
    ACoperationMode = json.load(f)

# 各日の冷暖房期間の種類（冷房期、暖房期、中間期）（365×1の行列）
ac_mode = ACoperationMode[Area[inputdata["Building"]["Region"]+"地域"]["空調運転モードタイプ"]]

if inputdata["Building"]["Region"] == '1' or inputdata["Building"]["Region"] == '2':
    TWdata = 0.6639*Toa_ave + 3.466
elif inputdata["Building"]["Region"] == '3' or inputdata["Building"]["Region"] == '4':
    TWdata = 0.6054*Toa_ave + 4.515
elif inputdata["Building"]["Region"] == '5':
    TWdata = 0.8660*Toa_ave + 1.665
elif inputdata["Building"]["Region"] == '6':
    TWdata = 0.8516*Toa_ave + 2.473
elif inputdata["Building"]["Region"] == '7':
    TWdata = 0.9223*Toa_ave + 2.097
elif inputdata["Building"]["Region"] == '8':
    TWdata = 0.6921*Toa_ave + 7.167



# %%
for unit_name in inputdata["HotwaterSupplySystems"]:

    for unit_id, unit_configure in enumerate(inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"]):

        # 加熱能力 kW/台 × 台
        inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedCapacity_total"] = \
            unit_configure["RatedCapacity"] * unit_configure["Number"]

        # 消費エネルギー kW/台 × 台
        inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedEnergyConsumption_total"] = \
            unit_configure["RatedPowerConsumption"] * unit_configure["Number"] * 9760/3600 + \
            unit_configure["RatedFuelConsumption"] * unit_configure["Number"]

        # 機器効率
        inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedEfficiency"] = \
            inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedCapacity_total"] / \
            inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedEnergyConsumption_total"]

        if DEBUG:
            print(f'機器名称 {unit_name} の {unit_id+1} 台目')
            print(f'  - 給湯機器の効率 {inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"][unit_id]["RatedEfficiency"]}')


# 機器全体の合計加熱能力と重み付け平均効率
for unit_name in inputdata["HotwaterSupplySystems"]:

    # 合計加熱能力 [kW]
    inputdata["HotwaterSupplySystems"][unit_name]["RatedCapacity_total"] = 0

    tmp_Capacity_efficiency = 0

    for unit_id, unit_configure in enumerate(inputdata["HotwaterSupplySystems"][unit_name]["HeatSourceUnit"]):

        # 加熱能力の合計
        inputdata["HotwaterSupplySystems"][unit_name]["RatedCapacity_total"] += \
            unit_configure["RatedCapacity_total"]

        # 加熱能力 × 効率
        tmp_Capacity_efficiency += \
            unit_configure["RatedCapacity_total"] * \
            unit_configure["RatedEfficiency"]

    # 加熱能力で重み付けした平均効率 [-]
    inputdata["HotwaterSupplySystems"][unit_name]["RatedEfficiency_total"] = \
        tmp_Capacity_efficiency / \
        inputdata["HotwaterSupplySystems"][unit_name]["RatedCapacity_total"]

#
#%%
#----------------------------------------------------------------------------------
# 解説書 D.5 給湯配管の線熱損失係数
#----------------------------------------------------------------------------------

# 給湯配管の線熱損失係数の読み込み
with open(directory + 'ThermalConductivityPiping.json', 'r') as f:
    thermal_conductivity_dict = json.load(f)

for unit_name in inputdata["HotwaterSupplySystems"]:

    # 接続口径の種類
    if inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 13:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "13A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 20:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "20A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 25:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "25A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 30:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "30A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 40:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "40A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 50:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "50A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 60:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "60A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 75:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "75A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 80:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "80A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 100:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "100A以下"
    elif inputdata["HotwaterSupplySystems"][unit_name]["PipeSize"] <= 125:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "125A以下"
    else:
        inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"] = "125Aより大きい"

    # 線熱損失係数
    inputdata["HotwaterSupplySystems"][unit_name]["heatloss_coefficient"] = \
        thermal_conductivity_dict[inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"]][inputdata["HotwaterSupplySystems"][unit_name]["InsulationType"]]

    if DEBUG:
        print(f'機器名称 {unit_name}')
        print(f'  - 配管接続口径 {inputdata["HotwaterSupplySystems"][unit_name]["PipeSizeType"]}')
        print(f'  - 線熱損失係数 {inputdata["HotwaterSupplySystems"][unit_name]["heatloss_coefficient"]}')


#%%
#----------------------------------------------------------------------------------
# 解説書 5.2 日積算湯使用量
#----------------------------------------------------------------------------------

for room_name in inputdata["HotwaterRoom"]:

    hotwater_demand, hotwater_demand_washroom, hotwater_demand_shower, hotwater_demand_kitchen, hotwater_demand_other = \
        bc.get_roomHotwaterDemand(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"])

    # 日積算給湯量参照値 [L/day]
    inputdata["HotwaterRoom"][room_name]["hotwater_demand"] = hotwater_demand * inputdata["Rooms"][room_name]["roomArea"]
    inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom"] = hotwater_demand_washroom * inputdata["Rooms"][room_name]["roomArea"]
    inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower"]   = hotwater_demand_shower * inputdata["Rooms"][room_name]["roomArea"]
    inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen"]  = hotwater_demand_kitchen * inputdata["Rooms"][room_name]["roomArea"]
    inputdata["HotwaterRoom"][room_name]["hotwater_demand_other"]    = hotwater_demand_other * inputdata["Rooms"][room_name]["roomArea"]

    # 各室のカレンダーパターン
    roomScheduleRoom, _, _, _, _ = \
        bc.get_roomUsageSchedule(inputdata["Rooms"][room_name]["buildingType"], inputdata["Rooms"][room_name]["roomType"])

    inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"] = np.zeros(365)
    inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"][ np.sum(roomScheduleRoom,1) > 0 ] = 1

    # 日別の給湯量 [L/day] (365×1)
    inputdata["HotwaterRoom"][room_name]["hotwater_demand_daily"] = \
        inputdata["HotwaterRoom"][room_name]["hotwater_demand"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

    inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] = \
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

    inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"] = \
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

    inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"] = \
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

    inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"] = \
        inputdata["HotwaterRoom"][room_name]["hotwater_demand_other"] * inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"]

    if DEBUG:
        print(f'室名称 {room_name}')
        print(f'  - 給湯使用量参照値 L/day {inputdata["HotwaterRoom"][room_name]["hotwater_demand"]}')
        print(f'  - 給湯日数 {np.sum(inputdata["HotwaterRoom"][room_name]["hotwaterSchedule"])}')
        print(f'  - 日別給湯使用量 {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_daily"])}')
        print(f'  - 日別給湯使用量（手洗い） {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"])}')
        print(f'  - 日別給湯使用量（シャワー） {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"])}')
        print(f'  - 日別給湯使用量（厨房） {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"])}')
        print(f'  - 日別給湯使用量（その他） {np.sum(inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"])}')


#%% 各室熱源の容量比を求める。

for room_name in inputdata["HotwaterRoom"]:

    inputdata["HotwaterRoom"][room_name]["RatedCapacity_All"] = 0

    for unit_id, unit_configure in enumerate(inputdata["HotwaterRoom"][room_name]["HotwaterSystem"]):

        inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["RatedCapacity_total"] = \
            inputdata["HotwaterSupplySystems"][ unit_configure["SystemName"] ]["RatedCapacity_total"]

        inputdata["HotwaterRoom"][room_name]["RatedCapacity_All"] += \
            inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["RatedCapacity_total"]

# 各室の熱源の容量比
for room_name in inputdata["HotwaterRoom"]:
    for unit_id, unit_configure in enumerate(inputdata["HotwaterRoom"][room_name]["HotwaterSystem"]):

        inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["roomPowerRatio"] = \
            inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["RatedCapacity_total"] / \
            inputdata["HotwaterRoom"][room_name]["RatedCapacity_All"]

        if DEBUG:
            print(f'熱源比率 {inputdata["HotwaterRoom"][room_name]["HotwaterSystem"][unit_id]["roomPowerRatio"]}')



#%% 機器のエネルギー消費量計算

for unit_name in inputdata["HotwaterSupplySystems"]:

    inputdata["HotwaterSupplySystems"][unit_name]["Qsr_eqp_daily"] = np.zeros(365)
    inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] = np.zeros(365)

    for room_name in inputdata["HotwaterRoom"]:
        for unit_id, unit_configure in enumerate(inputdata["HotwaterRoom"][room_name]["HotwaterSystem"]):
            if unit_name == unit_configure["SystemName"]:

                # 標準日積算給湯量 [L/day] →　配管長さ算出に必要
                inputdata["HotwaterSupplySystems"][unit_name]["Qsr_eqp_daily"] += \
                    inputdata["HotwaterRoom"][room_name]["hotwater_demand_daily"] * unit_configure["roomPowerRatio"]

                # 節湯効果を加味した日積算給湯量 [L/day]
                if unit_configure["HotWaterSavingSystem"] == "無":

                    inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] += \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] * 1.0 * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"]   * 1.0 * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"]  * 1.0 * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"]    * 1.0 * unit_configure["roomPowerRatio"]

                elif unit_configure["HotWaterSavingSystem"] == "自動給湯栓":

                    inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] += \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] * 0.6 * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"]   * 1.0 * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"]  * 1.0 * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"]    * 1.0 * unit_configure["roomPowerRatio"]

                elif unit_configure["HotWaterSavingSystem"] == "節湯B1":

                    inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] += \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_washroom_daily"] * 1.0  * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_shower_daily"]   * 0.75 * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_kitchen_daily"]  * 1.0  * unit_configure["roomPowerRatio"] + \
                        inputdata["HotwaterRoom"][room_name]["hotwater_demand_other_daily"]    * 1.0  * unit_configure["roomPowerRatio"]


    if DEBUG:
        print(f'機器名称 {unit_name}')
        print(f'  - 標準日積算給湯量 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qsr_eqp_daily"])}')
        print(f'  - 標準日積算給湯量（節湯込み） {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"])}')


#%%
# ----------------------------------------------------------------------------------
# 解説書 5.5 太陽熱利用システムの熱利用量
# ----------------------------------------------------------------------------------

for unit_name in inputdata["HotwaterSupplySystems"]:

    # 太陽熱利用量 [KJ/day]
    inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"] = np.zeros(365)

    if inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemArea"] != None:

        # 日積算日射量 [MJ/m2/day]
        Id, _, Is, _ = climate.solarRadiationByAzimuth( \
            inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemDirection"], \
            inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemAngle"], \
            Area[inputdata["Building"]["Region"]+"地域"]["緯度"], \
            Area[inputdata["Building"]["Region"]+"地域"]["経度"], \
            Iod, Ios, Inn)

        inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"] = \
            (inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemArea"]*0.4*0.85)*\
                (Id + Is)*3600/1000000 * 1000

    if DEBUG:
        print(f'機器名称 {unit_name}')
        print(f'  - 太陽熱利用システムの熱利用量 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"])}')


#%%
#----------------------------------------------------------------------------------
# 解説書 5.2 日積算湯使用量
#----------------------------------------------------------------------------------

for unit_name in inputdata["HotwaterSupplySystems"]:

    inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"] = np.zeros(365)

    if inputdata["HotwaterSupplySystems"][unit_name]["SolarSystemArea"] == None:

        # 太陽熱利用が無い場合
        inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"] = \
            4.2 * inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] * (43-TWdata)

    else:

        # 太陽熱利用がある場合
        tmpQh = 4.2 * inputdata["HotwaterSupplySystems"][unit_name]["Qs_eqp_daily"] * (43-TWdata)

        for dd in range(0,365):
            if (Toa_ave[dd] > 5) and (tmpQh[dd] > 0): # 日平均外気温が５度を超えていれば集熱
            
                if tmpQh[dd]*0.1 > (tmpQh[dd] - inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"][dd]):
                    
                    inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"][dd] = tmpQh[dd]*0.1

                else:
                    inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"][dd] = \
                        tmpQh[dd] - inputdata["HotwaterSupplySystems"][unit_name]["Qs_solargain"][dd]

            else:
                inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"][dd] = tmpQh[dd]


    if DEBUG:
        print(f'機器名称 {unit_name}')
        print(f'  - 日積算湯使用量 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"])}')


#%%
#----------------------------------------------------------------------------------
# 解説書 5.3 配管長さ
#----------------------------------------------------------------------------------

for unit_name in inputdata["HotwaterSupplySystems"]:

    inputdata["HotwaterSupplySystems"][unit_name]["L_eqp"] = \
        np.max(inputdata["HotwaterSupplySystems"][unit_name]["Qsr_eqp_daily"]) * 7 / 1000

    if DEBUG:
        print(f'機器名称 {unit_name}')
        print(f'  - 配管長さ {inputdata["HotwaterSupplySystems"][unit_name]["L_eqp"]}')


#%%
#----------------------------------------------------------------------------------
# 解説書 5.4 年間配管熱損失量
#----------------------------------------------------------------------------------

# 室内設定温度
Troom = np.zeros(365)

for dd in range(0, 365):
    if ac_mode[dd] == "冷房":
        Troom[dd] = 26
    elif ac_mode[dd] == "中間":
        Troom[dd] = 24
    elif ac_mode[dd] == "暖房":
        Troom[dd] = 22


# 配管熱損失 [kJ/day]
for unit_name in inputdata["HotwaterSupplySystems"]:

    inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"] = np.zeros(365)

    for dd in range(0,365):

        if inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"][dd] > 0:

            inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"][dd] = \
                inputdata["HotwaterSupplySystems"][unit_name]["L_eqp"] * \
                inputdata["HotwaterSupplySystems"][unit_name]["heatloss_coefficient"] * \
                ( 60 - (Toa_ave[dd]+Troom[dd])/2 ) * 24 * 3600 * 0.001

    if DEBUG:
        print(f'機器名称 {unit_name}')
        print(f'  - 配管熱損失 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"])}')


#%%
#----------------------------------------------------------------------------------
# 解説書 5.7 給湯設備の設計一次エネルギー消費量
#----------------------------------------------------------------------------------

E_eqpSUM = 0

for unit_name in inputdata["HotwaterSupplySystems"]:

    # 日別給湯負荷 [kJ/day]
    inputdata["HotwaterSupplySystems"][unit_name]["Q_eqp"] = \
        inputdata["HotwaterSupplySystems"][unit_name]["Qh_eqp_daily"] + \
        inputdata["HotwaterSupplySystems"][unit_name]["Qp_eqp"] * 2.5

    # 日別消費エネルギー消費量 [kJ/day]
    inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"] = \
        inputdata["HotwaterSupplySystems"][unit_name]["Q_eqp"] / inputdata["HotwaterSupplySystems"][unit_name]["RatedEfficiency_total"]

    # 設計一次エネルギー消費量 [MJ/day]
    E_eqpSUM += np.sum(inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"])/1000

    if DEBUG:
        print(f'機器名称 {unit_name}')
        print(f'  - 日別給湯負荷 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["Q_eqp"])}')
        print(f'  - 日別消費エネルギー消費量 {np.sum(inputdata["HotwaterSupplySystems"][unit_name]["E_eqp"])}')


if DEBUG:
    print(f'設計一次エネルギー消費量 {E_eqpSUM} MJ/年')

