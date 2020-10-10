#-----------------------------
# builelie 共通関数
#-----------------------------
import sys
import json
import jsonschema
import numpy as np
import os

# 電気の量 1kWh を熱量 kJに換算する係数
fprime = 9760

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"
# テンプレートファイルの保存場所
template_directory =  os.path.dirname(os.path.abspath(__file__)) + "/inputdata/"

# 基準値データベースの読み込み
with open(database_directory + 'ROOM_STANDARDVALUE.json', 'r') as f:
    RoomStandardValue = json.load(f)

# 室使用条件データの読み込み
with open(database_directory + 'RoomUsageSchedule.json', 'r') as f:
    RoomUsageSchedule = json.load(f)

# カレンダーパターンの読み込み
with open(database_directory + 'CALENDAR.json', 'r') as f:
    Calendar = json.load(f)


def air_enenthalpy(Tdb, X):
    """
    空気のエンタルピーを算出する関数
    """
    
    Ca = 1.006  # 乾き空気の定圧比熱 [kJ/kg･K]
    Cw = 1.805  # 水蒸気の定圧比熱 [kJ/kg･K]
    Lw = 2502   # 水の蒸発潜熱 [kJ/kg]

    if len(Tdb) != len(X):
        raise Exception('温度と湿度のリストの長さが異なります。')
    else:
        H = (Ca*Tdb + (Cw*Tdb+Lw)*X)

    return H   


# 発熱量参照値を読み込む関数（空調）
def get_roomOutdoorAirVolume(buildingType, roomType):

    # 外気導入量 [m3/h/m2]
    roomOutdoorAirVolume  = RoomUsageSchedule[buildingType][roomType]["外気導入量"]

    return roomOutdoorAirVolume

# 湯使用量を読み込む関数（給湯）
def get_roomHotwaterDemand(buildingType, roomType):

    # 年間湯使用量
    if RoomUsageSchedule[buildingType][roomType]["年間湯使用量の単位"] == "[L/人日]" or \
        RoomUsageSchedule[buildingType][roomType]["年間湯使用量の単位"] == "[L/床日]":

        hotwater_demand  = RoomUsageSchedule[buildingType][roomType]["年間湯使用量"] \
            * RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"]
        hotwater_demand_washroom = RoomUsageSchedule[buildingType][roomType]["年間湯使用量（洗面）"]\
            * RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"]
        hotwater_demand_shower = RoomUsageSchedule[buildingType][roomType]["年間湯使用量（シャワー）"]\
            * RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"]
        hotwater_demand_kitchen = RoomUsageSchedule[buildingType][roomType]["年間湯使用量（厨房）"]\
            * RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"]
        hotwater_demand_other = RoomUsageSchedule[buildingType][roomType]["年間湯使用量（その他）"]\
            * RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"]
    
    elif RoomUsageSchedule[buildingType][roomType]["年間湯使用量の単位"] == "[L/m2日]":

        hotwater_demand  = RoomUsageSchedule[buildingType][roomType]["年間湯使用量"]
        hotwater_demand_washroom = RoomUsageSchedule[buildingType][roomType]["年間湯使用量（洗面）"]
        hotwater_demand_shower = RoomUsageSchedule[buildingType][roomType]["年間湯使用量（シャワー）"]
        hotwater_demand_kitchen = RoomUsageSchedule[buildingType][roomType]["年間湯使用量（厨房）"]
        hotwater_demand_other = RoomUsageSchedule[buildingType][roomType]["年間湯使用量（その他）"]

    else:

        raise Exception('給湯負荷が設定されていません')

    return hotwater_demand, hotwater_demand_washroom, hotwater_demand_shower, hotwater_demand_kitchen, hotwater_demand_other


# 発熱量参照値を読み込む関数（空調）
def get_roomHeatGain(buildingType, roomType):

    roomHeatGain_Light  = RoomUsageSchedule[buildingType][roomType]["照明発熱参照値"]

    # 人体発熱量参照値 [人/m2 * W/人 = W/m2]
    if RoomUsageSchedule[buildingType][roomType]["作業強度指数"] == 1:
        roomHeatGain_Person = RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"] * 92
    elif RoomUsageSchedule[buildingType][roomType]["作業強度指数"] == 2:
        roomHeatGain_Person = RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"] * 106
    elif RoomUsageSchedule[buildingType][roomType]["作業強度指数"] == 3:
        roomHeatGain_Person = RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"] * 119
    elif RoomUsageSchedule[buildingType][roomType]["作業強度指数"] == 4:
        roomHeatGain_Person = RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"] * 131
    elif RoomUsageSchedule[buildingType][roomType]["作業強度指数"] == 5:
        roomHeatGain_Person = RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"] * 145
    else:
        roomHeatGain_Person = None
    
    roomHeatGain_OAapp  = RoomUsageSchedule[buildingType][roomType]["機器発熱参照値"]

    return roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp


# 時刻別のスケジュールを読み込む関数（空調）
def get_roomUsageSchedule(buildingType, roomType):
    
    if RoomUsageSchedule[buildingType][roomType]["空調運転パターン"] == None:  # 非空調であれば

        roomScheduleRoom = None
        roomScheduleLight = None
        roomSchedulePerson = None
        roomScheduleOAapp = None
        roomDayMode = None

    else:

        # 各日の運転パターン（365日分）：　各室のカレンダーパターンから決定
        opePattern_Daily = Calendar[ RoomUsageSchedule[buildingType][roomType]["カレンダーパターン"] ]

        # 各日時における運転状態（365×24の行列）
        roomScheduleRoom = []
        roomScheduleLight = []
        roomSchedulePerson = []
        roomScheduleOAapp = []

        for dd in range(0,len(opePattern_Daily)):  # 日ごとのループ

            # 室の同時使用率
            roomScheduleRoom.append(
                RoomUsageSchedule[buildingType][roomType]["スケジュール"]["室同時使用率"]["パターン" + str(opePattern_Daily[dd])]
            )

            # 照明発熱密度比率
            roomScheduleLight.append(
                RoomUsageSchedule[buildingType][roomType]["スケジュール"]["照明発熱密度比率"]["パターン" + str(opePattern_Daily[dd])]
            )

            # 人体発熱密度比率
            roomSchedulePerson.append(
                RoomUsageSchedule[buildingType][roomType]["スケジュール"]["人体発熱密度比率"]["パターン" + str(opePattern_Daily[dd])]
            )

            # 人体発熱機器発熱密度比率密度比率
            roomScheduleOAapp.append(
                RoomUsageSchedule[buildingType][roomType]["スケジュール"]["機器発熱密度比率"]["パターン" + str(opePattern_Daily[dd])]
            )

        # np.array型に変換（365×24の行列）
        # np.shape(roomScheduleRoom["1F_事務室"]) = (365, 24)
        roomScheduleRoom   = np.array(roomScheduleRoom)
        roomScheduleRoom[(roomScheduleRoom > 0)] = 1    # 同時使用率は考えない
        roomScheduleLight  = np.array(roomScheduleLight)
        roomSchedulePerson = np.array(roomSchedulePerson)
        roomScheduleOAapp  = np.array(roomScheduleOAapp)

        # パターン１で 使用時間帯（１：昼、２：夜、０：終日） を判断
        roomDayMode  = 0
        
        schedule_oneday  = np.array(RoomUsageSchedule[buildingType][roomType]["スケジュール"]["室同時使用率"]["パターン1"])
        schedule_oneday[(schedule_oneday > 0)] = 1

        opetime_oneday = np.sum(schedule_oneday)
        opetime_daytime = np.sum(schedule_oneday[[6,7,8,9,10,11,12,13,14,15,16,17]])
        opetime_night   = np.sum(schedule_oneday[[0,1,2,3,4,5,18,19,20,21,22,23]])

        if opetime_oneday == 24:
            roomDayMode = "終日"
        elif opetime_daytime >= opetime_night:
            roomDayMode = "昼"
        elif opetime_daytime < opetime_night:
            roomDayMode = "夜"
        else:
            raise Exception('室の使用時間帯が特定できませんでした。')

    return roomScheduleRoom, roomScheduleLight, roomSchedulePerson, roomScheduleOAapp, roomDayMode



# 時刻別のスケジュールを読み込む関数（照明器具）
def get_dailyOpeSchedule_lighting(buildingType, roomType):
    
    # 各日の運転パターン（365日分）：　各室のカレンダーパターンから決定
    opePattern_Daily = Calendar[ RoomUsageSchedule[buildingType][roomType]["カレンダーパターン"] ]

    # 各日時における運転状態（365×24の行列）
    opePattern_hourly_lighting = []
    
    if RoomUsageSchedule[buildingType][roomType]["スケジュール"]["室同時使用率"]["パターン1"] == []:  # 非空調室の場合

        # 非空調室は稼働率にする。
        ratio_hourly = RoomUsageSchedule[buildingType][roomType]["年間照明点灯時間"] / 8760

        opePattern_hourly_lighting = np.array( [[ratio_hourly]*24]*365 )

    else:

        for dd in range(0,len(opePattern_Daily)):  # 日ごとのループ

            # 照明器具
            opePattern_hourly_lighting.append(
                RoomUsageSchedule[buildingType][roomType]["スケジュール"]["照明発熱密度比率"]["パターン" + str(opePattern_Daily[dd])]
            )
        
        # np.array型に変換
        opePattern_hourly_lighting = np.array(opePattern_hourly_lighting)
        # 0か1に変換
        opePattern_hourly_lighting = np.where(opePattern_hourly_lighting > 0, 1, 0)

    return opePattern_hourly_lighting


# 入力データのバリデーション
def inputdata_validation(inputdata):

    # スキーマの読み込み
    with open( template_directory + '/webproJsonSchema.json') as f:
        schema_data = json.load(f)    

    # バリデーションの実行
    jsonschema.validate(inputdata, schema_data)

