#-----------------------------
# builelie 共通関数
#-----------------------------
import sys
import json
import jsonschema
import numpy as np

# 電気の量 1kWh を熱量に換算する係数
fprime = 9760

if 'ipykernel' in sys.modules:
    directory = "./database/"
else:
    directory = "./builelib/database/"


# 基準値データベースの読み込み
with open(directory + 'ROOM_STANDARDVALUE.json', 'r') as f:
    RoomStandardValue = json.load(f)

# 室使用条件データの読み込み
with open(directory + 'RoomUsageSchedule.json', 'r') as f:
    RoomUsageSchedule = json.load(f)

# カレンダーパターンの読み込み
with open(directory + 'CALENDAR.json', 'r') as f:
    Calendar = json.load(f)


def air_enenthalpy(Tdb, X):
    """
    空気のエンタルピーを算出する関数
    """
    
    Ca = 1.006  # 乾き空気の定圧比熱 [kJ/kg･K]
    Cw = 1.805  # 水蒸気の定圧比熱 [kJ/kg･K]
    Lw = 2502   # 水の蒸発潜熱 [kJ/kg]

    if len(Tdb) != len(X):
        raise Exception('窓面積が外皮面積よりも大きくなっています')
    else:
        H = (Ca*Tdb + (Cw*Tdb+Lw)*X)

    return H   



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
    
    roomHeatGain_OAapp  = RoomUsageSchedule[buildingType][roomType]["機器発熱参照値"]

    return roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp


# 時刻別のスケジュールを読み込む関数（空調）
def get_roomUsageSchedule(buildingType, roomType):
    
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
    roomScheduleLight  = np.array(roomScheduleLight)
    roomSchedulePerson = np.array(roomSchedulePerson)
    roomScheduleOAapp  = np.array(roomScheduleOAapp)

    return roomScheduleRoom, roomScheduleLight, roomSchedulePerson, roomScheduleOAapp



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
    with open('./builelib/inputdata/webproJsonSchema.json') as f:
        schema_data = json.load(f)    

    # バリデーションの実行
    jsonschema.validate(inputdata, schema_data)

