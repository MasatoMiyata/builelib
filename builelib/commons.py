#-----------------------------
# builelie 共通関数
#-----------------------------
import sys
import json
import jsonschema
import numpy as np
import os
# import pandas as pd
import itertools
import math

# 電気の量 1kWh を熱量 kJ に換算する係数
fprime = 9760

# データベースファイルの保存場所
database_directory =  os.path.dirname(os.path.abspath(__file__)) + "/database/"

# テンプレートファイルの保存場所
template_directory =  os.path.dirname(os.path.abspath(__file__)) + "/inputdata/"

# 基準値データベースの読み込み
with open(database_directory + 'ROOM_STANDARDVALUE.json', 'r', encoding='utf-8') as f:
    RoomStandardValue = json.load(f)

# 室使用条件データの読み込み
with open(database_directory + 'RoomUsageSchedule.json', 'r', encoding='utf-8') as f:
    RoomUsageSchedule = json.load(f)

# カレンダーパターンの読み込み
with open(database_directory + 'CALENDAR.json', 'r', encoding='utf-8') as f:
    Calendar = json.load(f)

class MyEncoder(json.JSONEncoder):
    """
    json.dump用のクラス
    """
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


def count_Matrix(x, mxL):
    """
    負荷率 X がマトリックス mxL の何番目（ix）のセルに入るかをカウント
    ＜現在は使用していない＞
    """

    # 初期値
    ix = 0

    # C#の処理に合わせる（代表負荷率にする）
    # 負荷率1.00の場合は x=1.05となるため過負荷判定
    x = math.floor(x*10)/10+0.05

    # 該当するマトリックスを探査
    while x > mxL[ix]:
        ix += 1

        if ix == len(mxL)-1:
            break

    return ix+1


def air_enthalpy(Tdb, X):
    """
    空気のエンタルピーを算出する関数
    """
    
    Ca = 1.006  # 乾き空気の定圧比熱 [kJ/kg･K]
    Cw = 1.86   # 水蒸気の定圧比熱 [kJ/kg･K]
    Lw = 2501   # 水の蒸発潜熱 [kJ/kg]

    if len(Tdb) != len(X):
        raise Exception('温度と湿度のリストの長さが異なります。')
    else:
        
        H = np.zeros(len(Tdb))
        for i in range(0, len(Tdb)):
            H[i] = (Ca*Tdb[i] + (Cw*Tdb[i]+Lw)*X[i])

    return H   


def get_roomOutdoorAirVolume(buildingType, roomType, input_room_usage_condition={}):
    """
    外気導入量を読み込む関数（空調）
    """

    # 外気導入量 [m3/h/m2] 標準室使用条件より取得
    roomOutdoorAirVolume  = RoomUsageSchedule[buildingType][roomType]["外気導入量"]
    
    # SP-9シートによる任意入力があれば上書き
    if buildingType in input_room_usage_condition:
        if roomType in input_room_usage_condition[buildingType]:
            roomOutdoorAirVolume = float( input_room_usage_condition[buildingType][roomType]["外気導入量"] )

    return roomOutdoorAirVolume


def get_roomHotwaterDemand(buildingType, roomType, input_room_usage_condition={}):
    """
    湯使用量（L/m2日）を読み込む関数（給湯）
    """

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


    # SP-9シートによる任意入力があれば上書き（単位は L/m2日 に限定）
    if buildingType in input_room_usage_condition:
        if roomType in input_room_usage_condition[buildingType]:

            # 全て入力されていれば上書き
            if input_room_usage_condition[buildingType][roomType]["年間湯使用量（洗面）"] != "" and \
                input_room_usage_condition[buildingType][roomType]["年間湯使用量（シャワー）"] != "" and \
                input_room_usage_condition[buildingType][roomType]["年間湯使用量（厨房）"] != "" and \
                input_room_usage_condition[buildingType][roomType]["年間湯使用量（その他）"] != "":

                hotwater_demand_washroom = float( input_room_usage_condition[buildingType][roomType]["年間湯使用量（洗面）"])
                hotwater_demand_shower   = float( input_room_usage_condition[buildingType][roomType]["年間湯使用量（シャワー）"])
                hotwater_demand_kitchen  = float( input_room_usage_condition[buildingType][roomType]["年間湯使用量（厨房）"])
                hotwater_demand_other    = float( input_room_usage_condition[buildingType][roomType]["年間湯使用量（その他）"])

                # 湯使用量の合計[L/m2日]
                hotwater_demand  = hotwater_demand_washroom + hotwater_demand_shower + hotwater_demand_kitchen + hotwater_demand_other

    return hotwater_demand, hotwater_demand_washroom, hotwater_demand_shower, hotwater_demand_kitchen, hotwater_demand_other


def get_roomHeatGain(buildingType, roomType, input_room_usage_condition={}):
    """
    発熱量参照値を読み込む関数（空調）
    """

    roomHeatGain_Light  = RoomUsageSchedule[buildingType][roomType]["照明発熱参照値"]
    roomNumOfPerson     = RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"]
    roomHeatGain_OAapp  = RoomUsageSchedule[buildingType][roomType]["機器発熱参照値"]
    work_load_index     = RoomUsageSchedule[buildingType][roomType]["作業強度指数"]

    # SP-9シートによる任意入力があれば上書き
    if buildingType in input_room_usage_condition:
        if roomType in input_room_usage_condition[buildingType]:

            if input_room_usage_condition[buildingType][roomType]["照明発熱参照値"] != "":
                roomHeatGain_Light = float(input_room_usage_condition[buildingType][roomType]["照明発熱参照値"])

            if input_room_usage_condition[buildingType][roomType]["人体発熱参照値"] != "":
                roomNumOfPerson = float(input_room_usage_condition[buildingType][roomType]["人体発熱参照値"])
            
            if input_room_usage_condition[buildingType][roomType]["機器発熱参照値"] != "":
                roomHeatGain_OAapp = float(input_room_usage_condition[buildingType][roomType]["機器発熱参照値"])

            if input_room_usage_condition[buildingType][roomType]["作業強度指数"] != "":
                work_load_index = float(input_room_usage_condition[buildingType][roomType]["作業強度指数"])


    # 人体発熱量参照値 [人/m2 * W/人 = W/m2]
    if work_load_index == 1:
        roomHeatGain_Person = roomNumOfPerson * 92
    elif work_load_index == 2:
        roomHeatGain_Person = roomNumOfPerson * 106
    elif work_load_index == 3:
        roomHeatGain_Person = roomNumOfPerson * 119
    elif work_load_index == 4:
        roomHeatGain_Person = roomNumOfPerson * 131
    elif work_load_index == 5:
        roomHeatGain_Person = roomNumOfPerson * 145
    else:
        roomHeatGain_Person = np.nan
    
    return roomHeatGain_Light, roomHeatGain_Person, roomHeatGain_OAapp, roomNumOfPerson


def get_roomUsageSchedule(buildingType, roomType, input_calendar={}):
    """
    時刻別のスケジュールを読み込む関数（空調、その他）
    """

    if RoomUsageSchedule[buildingType][roomType]["空調運転パターン"] == None:  # 非空調であれば

        roomScheduleRoom = np.zeros((365,24))
        roomScheduleLight = np.zeros((365,24))
        roomSchedulePerson = np.zeros((365,24))
        roomScheduleOAapp = np.zeros((365,24))
        roomDayMode = None

    else:

        # 各日の運転パターン（365日分）：　各室のカレンダーパターンから決定
        opePattern_Daily = Calendar[ RoomUsageSchedule[buildingType][roomType]["カレンダーパターン"] ]

        # 入力されたカレンダーパターンを使う場合（上書きする）
        if input_calendar != []:
            if buildingType in input_calendar:
                if roomType in input_calendar[buildingType]:
                    opePattern_Daily = input_calendar[buildingType][roomType]


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

            # 機器発熱密度比率
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

        #--------------------------------------------------------------
        # roomDayMode の決定（WebプログラムとBuilelibで方法が違う）
        #--------------------------------------------------------------

        # Webプログラムの方法：
        # パターン１で 使用時間帯（１：昼、２：夜、０：終日） を判断
        roomDayMode  = "昼"
        
        schedule_oneday  = np.array(RoomUsageSchedule[buildingType][roomType]["スケジュール"]["室同時使用率"]["パターン1"])
        schedule_oneday[(schedule_oneday > 0)] = 1

        # Webプログラムの判断方法（
        if schedule_oneday[0] == 1 and schedule_oneday[23] == 1:   # 日を跨ぐ場合
            roomDayMode = "夜"
        if np.sum(schedule_oneday) == 24:
            roomDayMode = "終日"

        # # builelibの方法：
        # opetime_oneday  = np.sum(schedule_oneday)
        # opetime_daytime = np.sum(schedule_oneday[[6,7,8,9,10,11,12,13,14,15,16,17]])
        # opetime_night   = np.sum(schedule_oneday[[0,1,2,3,4,5,18,19,20,21,22,23]])

        # if opetime_oneday == 24:
        #     roomDayMode = "終日"
        # elif opetime_daytime >= opetime_night:
        #     roomDayMode = "昼"
        # elif opetime_daytime < opetime_night:
        #     roomDayMode = "夜"
        # else:
        #     raise Exception('室の使用時間帯が特定できませんでした。')


    # # CSVファイルに出力（検証用）
    # df = pd.DataFrame()
    # df["roomScheduleRoom"] = list(itertools.chain.from_iterable(roomScheduleRoom))
    # df["roomScheduleLight"] = list(itertools.chain.from_iterable(roomScheduleLight))
    # df["roomSchedulePerson"] = list(itertools.chain.from_iterable(roomSchedulePerson))
    # df["roomScheduleOAapp"] = list(itertools.chain.from_iterable(roomScheduleOAapp))
    # df.to_csv("schedule.csv")

    return roomScheduleRoom, roomScheduleLight, roomSchedulePerson, roomScheduleOAapp, roomDayMode


def get_dailyOpeSchedule_ventilation(buildingType, roomType, input_room_usage_condition={}, input_calendar={}):
    """
    時刻別のスケジュールを読み込む関数（換気）
    """

    # 各日時における運転状態（365×24の行列）
    opePattern_hourly_ventilation = []
    
    if RoomUsageSchedule[buildingType][roomType]["スケジュール"]["室同時使用率"]["パターン1"] == []:  # 非空調室の場合

        # 非空調室は、年間一律で運転することにする。
        ratio_hourly = RoomUsageSchedule[buildingType][roomType]["年間換気時間"] / 8760

        # SP-9シートに入力があれば上書きする。
        if buildingType in input_room_usage_condition:
            if roomType in input_room_usage_condition[buildingType]:
                ratio_hourly = float(input_room_usage_condition[buildingType][roomType]["年間換気時間"]) / 8760

        # 365×24の行列に変換
        opePattern_hourly_ventilation = np.array( [[ratio_hourly]*24]*365 )

    else:

        # 各日の運転パターン（365日分）： 各室のカレンダーパターンから決定
        opePattern_Daily = Calendar[ RoomUsageSchedule[buildingType][roomType]["カレンダーパターン"] ]

        # 入力されたカレンダーパターンを使う場合（上書きする）
        if input_calendar != []:
            if buildingType in input_calendar:
                if roomType in input_calendar[buildingType]:
                    opePattern_Daily = input_calendar[buildingType][roomType]


        # SP-9シートに入力があれば、年間換気運転時間を上書きする。
        if buildingType in input_room_usage_condition:
            if roomType in input_room_usage_condition[buildingType]:
                RoomUsageSchedule[buildingType][roomType]["年間換気時間"] = float(input_room_usage_condition[buildingType][roomType]["年間換気時間"])


        # 時刻別スケジュールの設定
        if RoomUsageSchedule[buildingType][roomType]["年間換気時間"] == RoomUsageSchedule[buildingType][roomType]["年間空調時間"]:

            for dd in range(0,len(opePattern_Daily)):  # 日ごとのループ
                opePattern_hourly_ventilation.append(
                    RoomUsageSchedule[buildingType][roomType]["スケジュール"]["室同時使用率"]["パターン" + str(opePattern_Daily[dd])]
                )
            # np.array型に変換
            opePattern_hourly_ventilation = np.array(opePattern_hourly_ventilation)
            # 0か1に変換
            opePattern_hourly_ventilation = np.where(opePattern_hourly_ventilation > 0, 1, 0)


        elif RoomUsageSchedule[buildingType][roomType]["年間換気時間"] == RoomUsageSchedule[buildingType][roomType]["年間照明点灯時間"]:
        
            for dd in range(0,len(opePattern_Daily)):  # 日ごとのループ
                opePattern_hourly_ventilation.append(
                    RoomUsageSchedule[buildingType][roomType]["スケジュール"]["照明発熱密度比率"]["パターン" + str(opePattern_Daily[dd])]
                )

            # np.array型に変換
            opePattern_hourly_ventilation = np.array(opePattern_hourly_ventilation)
            # 0か1に変換
            opePattern_hourly_ventilation = np.where(opePattern_hourly_ventilation > 0, 1, 0)


        elif RoomUsageSchedule[buildingType][roomType]["年間換気時間"] == 0:

            for dd in range(0,len(opePattern_Daily)):  # 日ごとのループ
                opePattern_hourly_ventilation.append(
                    np.zeros(24)
                )
            
            # np.array型に変換
            opePattern_hourly_ventilation = np.array(opePattern_hourly_ventilation)
            # 0か1に変換
            opePattern_hourly_ventilation = np.where(opePattern_hourly_ventilation > 0, 1, 0)

        else:  # SPシートで入力された場合

            # 非空調室の場合と同じ処理を行う
            ratio_hourly = RoomUsageSchedule[buildingType][roomType]["年間換気時間"] / 8760
            # 365×24の行列に変換
            opePattern_hourly_ventilation = np.array( [[ratio_hourly]*24]*365 )


    return opePattern_hourly_ventilation



def get_dailyOpeSchedule_lighting(buildingType, roomType, input_calendar={}):
    """
    時刻別のスケジュールを読み込む関数（照明）
    """

    # 各日の運転パターン（365日分）：　各室のカレンダーパターンから決定
    opePattern_Daily = Calendar[ RoomUsageSchedule[buildingType][roomType]["カレンダーパターン"] ]

    # 入力されたカレンダーパターンを使う場合（上書きする）
    if input_calendar != []:
        if buildingType in input_calendar:
            if roomType in input_calendar[buildingType]:
                opePattern_Daily = input_calendar[buildingType][roomType]

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
    with open( template_directory + '/webproJsonSchema.json', encoding='utf-8') as f:
        schema_data = json.load(f)    

    # 任意評定用（SP-1）
    if "SpecialInputData" in inputdata:
        if "flow_control" in inputdata["SpecialInputData"]:
            for control_type_name in inputdata["SpecialInputData"]["flow_control"]:

                # スキーマに追加
                schema_data["definitions"]["AirHandlingSystem"]["properties"]["AirHandlingUnit"]["items"]["properties"]["FanControlType"]["anyOf"].append(
                    {
                        "type": "string",
                        "enum":[
                            control_type_name
                        ]
                    }
                )
                schema_data["definitions"]["SecondaryPump"]["properties"]["SecondaryPump"]["items"]["properties"]["ContolType"]["anyOf"].append(
                    {
                        "type": "string",
                        "enum":[
                            control_type_name
                        ]
                    }
                )

    # バリデーションの実行
    jsonschema.validate(inputdata, schema_data)


def day2month(dd: np.array) -> str:
    """
    日数から月を返す関数
    """
    
    month = str()
    if dd < 31:
        month = "1月"
    elif dd < 59:
        month = "2月"
    elif dd < 90:
        month = "3月"
    elif dd < 120:
        month = "4月"
    elif dd < 151:
        month = "5月"
    elif dd < 181:
        month = "6月"
    elif dd < 212:
        month = "7月"
    elif dd < 243:
        month = "8月"
    elif dd < 273:
        month = "9月"
    elif dd < 304:
        month = "10月"
    elif dd < 334:
        month = "11月"
    elif dd < 365:
        month = "12月"
    else:
        raise Exception("day2month: 日数が範囲外です。")

    return month


def trans_8760to36524(X8760):
    """
    8760行のリストを365行×24列のリストに変形する関数
    """
    X = []
    for dd in range(0,365):
        tmp = []
        for hh in range(0,24):
            tmp.append(X8760[24*dd+hh])
        X.append(tmp)
    return X

def trans_36524to8760(X36524):
    """
    365行×24列のリストを8760行のリストに変形する関数
    """
    X = []
    for dd in range(0,365):
        for hh in range(0,24):
            X.append(X36524[dd][hh])
    return X
