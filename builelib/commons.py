#-----------------------------
# builelie 共通関数
#-----------------------------
import sys
import json
import jsonschema
import numpy as np
import os
import copy
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


def get_standard_value(special_sheet):
    """基準値を読み込む
    """

    # 基準値データベースの読み込み
    with open(database_directory + 'ROOM_STANDARDVALUE.json', 'r', encoding='utf-8') as f:
        standard_value = json.load(f)
    
    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-UC. 室使用条件入力シート
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "room_usage_condition" in special_sheet:
            for buildling_type in special_sheet["room_usage_condition"]:
                for room_type in special_sheet["room_usage_condition"][buildling_type]:
                    # 新たに作成した室用途については、ベースとする室用途の基準値を呼び出す
                    standard_value[buildling_type][room_type] = copy.deepcopy( standard_value[buildling_type][ special_sheet["room_usage_condition"][buildling_type][room_type]["ベースとする室用途"] ] )
                    
    return standard_value                    


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
        raise Exception('温度と絶対湿度のリストの長さが異なります。')
    else:
        
        H = np.zeros(len(Tdb))
        for i in range(0, len(Tdb)):
            H[i] = (Ca*Tdb[i] + (Cw*Tdb[i]+Lw)*X[i])

    return H   


def air_absolute_humidity(Tdb, H):
    """絶対湿度を計算する関数
    """

    if len(Tdb) != len(H):
        raise Exception('温度と相対湿度のリストの長さが異なります。')
    else:

        X = np.zeros(len(Tdb))

        for i in range(0, len(Tdb)):

            # 絶対温度[K]
            T = Tdb[i] +  273.15

            # 飽和水蒸気分圧 Ps
            term1 = -0.58002206 * 10**4 / T
            term2 = 0.13914993 * 10
            term3 = -0.48640239 * 10**-1 * T
            term4 = 0.41764768 * 10**-4 * T**2
            term5 = -0.14452093 * 10**-7 * T**3
            term6 = 0.65459673 * 10 * math.log(T)
            Pw = math.exp(term1 + term2 + term3 + term4 + term5 + term6) /1000

            # Pw：水蒸気分圧(kPa)
            Pw  = Pw*(H[i]/100)      

            Mw = 18.0153  # 水の分子量 [g/mol]
            Ma = 28.9645  # 空気の分子量 [g/mol]
            P  = 101.325  # 空気の全圧 [kPa]            

            X[i]  = Mw / Ma * Pw / (P-Pw)

    return X


def get_roomOutdoorAirVolume(buildingType, roomType, special_sheet={}):
    """
    外気導入量を読み込む関数（空調）
    """

    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-UC. 室使用条件入力シート
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "room_usage_condition" in special_sheet:
            for buildling_type in special_sheet["room_usage_condition"]:
                for room_type in special_sheet["room_usage_condition"][buildling_type]:
                    RoomUsageSchedule[buildling_type][room_type] = special_sheet["room_usage_condition"][buildling_type][room_type]

    # 外気導入量 [m3/h/m2] 標準室使用条件より取得
    roomOutdoorAirVolume  = RoomUsageSchedule[buildingType][roomType]["外気導入量"]
    

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


def get_roomHeatGain(buildingType, roomType, special_sheet={}):
    """
    発熱量参照値を読み込む関数（空調）
    """

    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-UC. 室使用条件入力シート
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "room_usage_condition" in special_sheet:
            for buildling_type in special_sheet["room_usage_condition"]:
                for room_type in special_sheet["room_usage_condition"][buildling_type]:
                    RoomUsageSchedule[buildling_type][room_type] = special_sheet["room_usage_condition"][buildling_type][room_type]

    roomHeatGain_Light  = RoomUsageSchedule[buildingType][roomType]["照明発熱参照値"]
    roomNumOfPerson     = RoomUsageSchedule[buildingType][roomType]["人体発熱参照値"]
    roomHeatGain_OAapp  = RoomUsageSchedule[buildingType][roomType]["機器発熱参照値"]
    work_load_index     = RoomUsageSchedule[buildingType][roomType]["作業強度指数"]

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


def get_roomUsageSchedule(buildingType, roomType, special_sheet={}):
    """
    時刻別のスケジュールを読み込む関数（空調、その他）
    """

    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-CP: カレンダーパターン
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "calender" in special_sheet:
            for pattern_name in special_sheet["calender"]:
                # データベースに追加
                Calendar[pattern_name] = special_sheet["calender"][pattern_name]


    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-UC. 室使用条件入力シート
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "room_usage_condition" in special_sheet:
            for buildling_type in special_sheet["room_usage_condition"]:
                for room_type in special_sheet["room_usage_condition"][buildling_type]:
                    RoomUsageSchedule[buildling_type][room_type] = special_sheet["room_usage_condition"][buildling_type][room_type]


    if RoomUsageSchedule[buildingType][roomType]["空調運転パターン"] == None:  # 非空調であれば

        roomScheduleRoom = np.zeros((365,24))
        roomScheduleLight = np.zeros((365,24))
        roomSchedulePerson = np.zeros((365,24))
        roomScheduleOAapp = np.zeros((365,24))
        roomDayMode = None

    else:

        # 各日の運転パターン（365日分）： 各室のカレンダーパターンから決定
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


def get_operation_schedule_ventilation(buildingType, roomType, special_sheet={}):
    """
    時刻別のスケジュールを読み込む関数（換気）
    """

    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-CP: カレンダーパターン
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "calender" in special_sheet:
            for pattern_name in special_sheet["calender"]:
                # データベースに追加
                Calendar[pattern_name] = special_sheet["calender"][pattern_name]


    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-UC. 室使用条件入力シート
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "room_usage_condition" in special_sheet:
            for buildling_type in special_sheet["room_usage_condition"]:
                for room_type in special_sheet["room_usage_condition"][buildling_type]:
                    RoomUsageSchedule[buildling_type][room_type] = special_sheet["room_usage_condition"][buildling_type][room_type]


    # 各日時における運転状態（365×24の行列）
    opePattern_hourly_ventilation = []
    
    if RoomUsageSchedule[buildingType][roomType]["スケジュール"]["室同時使用率"]["パターン1"] == []:  # 非空調室の場合

        # 非空調室は、年間一律で運転することにする。
        ratio_hourly = RoomUsageSchedule[buildingType][roomType]["年間換気時間"] / 8760

        # 365×24の行列に変換
        opePattern_hourly_ventilation = np.array( [[ratio_hourly]*24]*365 )

    else:

        # 各日の運転パターン（365日分）： 各室のカレンダーパターンから決定
        opePattern_Daily = Calendar[ RoomUsageSchedule[buildingType][roomType]["カレンダーパターン"] ]

        # 時刻別スケジュールの設定
        if ("年間空調時間" in RoomUsageSchedule[buildingType][roomType]) and  \
            RoomUsageSchedule[buildingType][roomType]["年間換気時間"] == RoomUsageSchedule[buildingType][roomType]["年間空調時間"]:

            for dd in range(0,len(opePattern_Daily)):  # 日ごとのループ
                opePattern_hourly_ventilation.append(
                    RoomUsageSchedule[buildingType][roomType]["スケジュール"]["室同時使用率"]["パターン" + str(opePattern_Daily[dd])]
                )
            # np.array型に変換
            opePattern_hourly_ventilation = np.array(opePattern_hourly_ventilation)
            # 0か1に変換
            opePattern_hourly_ventilation = np.where(opePattern_hourly_ventilation > 0, 1, 0)


        elif ("年間照明点灯時間" in RoomUsageSchedule[buildingType][roomType]) and \
            RoomUsageSchedule[buildingType][roomType]["年間換気時間"] == RoomUsageSchedule[buildingType][roomType]["年間照明点灯時間"]:
        
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

        else:  # SPシートで入力された場合など

            # 非空調室の場合と同じ処理を行う
            ratio_hourly = RoomUsageSchedule[buildingType][roomType]["年間換気時間"] / 8760
            # 365×24の行列に変換
            opePattern_hourly_ventilation = np.array( [[ratio_hourly]*24]*365 )


    return opePattern_hourly_ventilation



def get_operation_schedule_lighting(buildingType, roomType, special_sheet={}):
    """
    時刻別のスケジュールを読み込む関数（照明）
    """

    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-CP: カレンダーパターン
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "calender" in special_sheet:
            for pattern_name in special_sheet["calender"]:
                # データベースに追加
                Calendar[pattern_name] = special_sheet["calender"][pattern_name]


    ##----------------------------------------------------------------------------------
    ## 任意入力 様式 SP-RT-UC. 室使用条件入力シート
    ##----------------------------------------------------------------------------------
    if special_sheet:
        if "room_usage_condition" in special_sheet:
            for buildling_type in special_sheet["room_usage_condition"]:
                for room_type in special_sheet["room_usage_condition"][buildling_type]:
                    RoomUsageSchedule[buildling_type][room_type] = special_sheet["room_usage_condition"][buildling_type][room_type]


    # 各日の運転パターン（365日分）： 各室のカレンダーパターンから決定
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


date_1year = ["1月1日",
    "1月2日",
    "1月3日",
    "1月4日",
    "1月5日",
    "1月6日",
    "1月7日",
    "1月8日",
    "1月9日",
    "1月10日",
    "1月11日",
    "1月12日",
    "1月13日",
    "1月14日",
    "1月15日",
    "1月16日",
    "1月17日",
    "1月18日",
    "1月19日",
    "1月20日",
    "1月21日",
    "1月22日",
    "1月23日",
    "1月24日",
    "1月25日",
    "1月26日",
    "1月27日",
    "1月28日",
    "1月29日",
    "1月30日",
    "1月31日",
    "2月1日",
    "2月2日",
    "2月3日",
    "2月4日",
    "2月5日",
    "2月6日",
    "2月7日",
    "2月8日",
    "2月9日",
    "2月10日",
    "2月11日",
    "2月12日",
    "2月13日",
    "2月14日",
    "2月15日",
    "2月16日",
    "2月17日",
    "2月18日",
    "2月19日",
    "2月20日",
    "2月21日",
    "2月22日",
    "2月23日",
    "2月24日",
    "2月25日",
    "2月26日",
    "2月27日",
    "2月28日",
    "3月1日",
    "3月2日",
    "3月3日",
    "3月4日",
    "3月5日",
    "3月6日",
    "3月7日",
    "3月8日",
    "3月9日",
    "3月10日",
    "3月11日",
    "3月12日",
    "3月13日",
    "3月14日",
    "3月15日",
    "3月16日",
    "3月17日",
    "3月18日",
    "3月19日",
    "3月20日",
    "3月21日",
    "3月22日",
    "3月23日",
    "3月24日",
    "3月25日",
    "3月26日",
    "3月27日",
    "3月28日",
    "3月29日",
    "3月30日",
    "3月31日",
    "4月1日",
    "4月2日",
    "4月3日",
    "4月4日",
    "4月5日",
    "4月6日",
    "4月7日",
    "4月8日",
    "4月9日",
    "4月10日",
    "4月11日",
    "4月12日",
    "4月13日",
    "4月14日",
    "4月15日",
    "4月16日",
    "4月17日",
    "4月18日",
    "4月19日",
    "4月20日",
    "4月21日",
    "4月22日",
    "4月23日",
    "4月24日",
    "4月25日",
    "4月26日",
    "4月27日",
    "4月28日",
    "4月29日",
    "4月30日",
    "5月1日",
    "5月2日",
    "5月3日",
    "5月4日",
    "5月5日",
    "5月6日",
    "5月7日",
    "5月8日",
    "5月9日",
    "5月10日",
    "5月11日",
    "5月12日",
    "5月13日",
    "5月14日",
    "5月15日",
    "5月16日",
    "5月17日",
    "5月18日",
    "5月19日",
    "5月20日",
    "5月21日",
    "5月22日",
    "5月23日",
    "5月24日",
    "5月25日",
    "5月26日",
    "5月27日",
    "5月28日",
    "5月29日",
    "5月30日",
    "5月31日",
    "6月1日",
    "6月2日",
    "6月3日",
    "6月4日",
    "6月5日",
    "6月6日",
    "6月7日",
    "6月8日",
    "6月9日",
    "6月10日",
    "6月11日",
    "6月12日",
    "6月13日",
    "6月14日",
    "6月15日",
    "6月16日",
    "6月17日",
    "6月18日",
    "6月19日",
    "6月20日",
    "6月21日",
    "6月22日",
    "6月23日",
    "6月24日",
    "6月25日",
    "6月26日",
    "6月27日",
    "6月28日",
    "6月29日",
    "6月30日",
    "7月1日",
    "7月2日",
    "7月3日",
    "7月4日",
    "7月5日",
    "7月6日",
    "7月7日",
    "7月8日",
    "7月9日",
    "7月10日",
    "7月11日",
    "7月12日",
    "7月13日",
    "7月14日",
    "7月15日",
    "7月16日",
    "7月17日",
    "7月18日",
    "7月19日",
    "7月20日",
    "7月21日",
    "7月22日",
    "7月23日",
    "7月24日",
    "7月25日",
    "7月26日",
    "7月27日",
    "7月28日",
    "7月29日",
    "7月30日",
    "7月31日",
    "8月1日",
    "8月2日",
    "8月3日",
    "8月4日",
    "8月5日",
    "8月6日",
    "8月7日",
    "8月8日",
    "8月9日",
    "8月10日",
    "8月11日",
    "8月12日",
    "8月13日",
    "8月14日",
    "8月15日",
    "8月16日",
    "8月17日",
    "8月18日",
    "8月19日",
    "8月20日",
    "8月21日",
    "8月22日",
    "8月23日",
    "8月24日",
    "8月25日",
    "8月26日",
    "8月27日",
    "8月28日",
    "8月29日",
    "8月30日",
    "8月31日",
    "9月1日",
    "9月2日",
    "9月3日",
    "9月4日",
    "9月5日",
    "9月6日",
    "9月7日",
    "9月8日",
    "9月9日",
    "9月10日",
    "9月11日",
    "9月12日",
    "9月13日",
    "9月14日",
    "9月15日",
    "9月16日",
    "9月17日",
    "9月18日",
    "9月19日",
    "9月20日",
    "9月21日",
    "9月22日",
    "9月23日",
    "9月24日",
    "9月25日",
    "9月26日",
    "9月27日",
    "9月28日",
    "9月29日",
    "9月30日",
    "10月1日",
    "10月2日",
    "10月3日",
    "10月4日",
    "10月5日",
    "10月6日",
    "10月7日",
    "10月8日",
    "10月9日",
    "10月10日",
    "10月11日",
    "10月12日",
    "10月13日",
    "10月14日",
    "10月15日",
    "10月16日",
    "10月17日",
    "10月18日",
    "10月19日",
    "10月20日",
    "10月21日",
    "10月22日",
    "10月23日",
    "10月24日",
    "10月25日",
    "10月26日",
    "10月27日",
    "10月28日",
    "10月29日",
    "10月30日",
    "10月31日",
    "11月1日",
    "11月2日",
    "11月3日",
    "11月4日",
    "11月5日",
    "11月6日",
    "11月7日",
    "11月8日",
    "11月9日",
    "11月10日",
    "11月11日",
    "11月12日",
    "11月13日",
    "11月14日",
    "11月15日",
    "11月16日",
    "11月17日",
    "11月18日",
    "11月19日",
    "11月20日",
    "11月21日",
    "11月22日",
    "11月23日",
    "11月24日",
    "11月25日",
    "11月26日",
    "11月27日",
    "11月28日",
    "11月29日",
    "11月30日",
    "12月1日",
    "12月2日",
    "12月3日",
    "12月4日",
    "12月5日",
    "12月6日",
    "12月7日",
    "12月8日",
    "12月9日",
    "12月10日",
    "12月11日",
    "12月12日",
    "12月13日",
    "12月14日",
    "12月15日",
    "12月16日",
    "12月17日",
    "12月18日",
    "12月19日",
    "12月20日",
    "12月21日",
    "12月22日",
    "12月23日",
    "12月24日",
    "12月25日",
    "12月26日",
    "12月27日",
    "12月28日",
    "12月29日",
    "12月30日",
    "12月31日"]

