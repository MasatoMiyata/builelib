import json
import numpy as np
import os
import math

import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc
import climate

# 気象データファイルの保存場所
climatedata_directory =  os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"


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


def calc_energy(inputdata, DEBUG = False):


    # 計算結果を格納する変数
    resultJson = {
        "E_photovoltaic": 0,
        "PhotovoltaicSystems": {}
    }

    # 地域区分と気象ファイル名の関係
    climate_data_file = {
        "1地域":{
            "A1": "7.csv",
            "A2": "117.csv",
            "A3": "124.csv",
            "A4": None,
            "A5": None
        },
        "2地域":{
            "A1": "49.csv",
            "A2": "63.csv",
            "A3": "59.csv",
            "A4": "59-A4.csv",
            "A5": "59-A5.csv"
        },
        "3地域":{
            "A1": "190.csv",
            "A2": "230.csv",
            "A3": "426.csv",
            "A4": "403.csv",
            "A5": "412.csv"
        },
        "4地域":{
            "A1": "286.csv",
            "A2": "186.csv",
            "A3": "292.csv",
            "A4": "423.csv",
            "A5": "401.csv"
        },
        "5地域":{
            "A1": "593.csv",
            "A2": "542.csv",
            "A3": "495.csv",
            "A4": "473.csv",
            "A5": "420.csv"
        },
        "6地域":{
            "A1": None,
            "A2": "569.csv",
            "A3": "551.csv",
            "A4": "480.csv",
            "A5": "438.csv"
        },
        "7地域":{
            "A1": "819-A1.csv",
            "A2": "819-A2.csv",
            "A3": "819.csv",
            "A4": "798.csv",
            "A5": "797.csv"
        },
        "8地域":{
            "A1": None,
            "A2": None,
            "A3": "826.csv",
            "A4": "836.csv",
            "A5": "842.csv"
        }
    }

    for system_name in inputdata["PhotovoltaicSystems"]:

        resultJson["PhotovoltaicSystems"][system_name] = {
            "Ep" : np.zeros(8760)
        }

        ##----------------------------------------------------------------------------------
        ## 入力の整理
        ##----------------------------------------------------------------------------------

        # 傾斜面の方位角（南が0°、西が90°、北180°、東270°）
        slope_azimuth= inputdata["PhotovoltaicSystems"][system_name]["Direction"]

        # 傾斜面の傾斜角（水平0°、垂直90°） 一の位を四捨五入
        slope_angle = round(inputdata["PhotovoltaicSystems"][system_name]["Angle"], -1)

        if slope_angle > 90:
            slope_angle = 90

        ##----------------------------------------------------------------------------------
        ## 付録 A 傾斜面における単位面積当たりの平均日射量
        ##----------------------------------------------------------------------------------

        # 気象データの読み込み
        if climate_data_file[ inputdata["Building"]["Region"]+"地域" ][ inputdata["Building"]["AnnualSolarRegion"] ] != None:
            [Tout, Iod, Ios, sun_altitude, sun_azimuth] = \
            climate.readCsvClimateData( climatedata_directory + climate_data_file[ inputdata["Building"]["Region"]+"地域" ][ inputdata["Building"]["AnnualSolarRegion"] ] )
        else:
            raise Exception('日射地域区分の指定が不正です')

        # 傾斜面における単位面積あたりの直達・天空日射量 [W/m2]
        Iod_slope = np.zeros(8760)
        Ios_slope = np.zeros(8760)
        for hh in range(0,8760):

            # 傾斜面の単位面積当たりの直達日射量 [W/m2]
            Iod_slope[hh] = Iod[hh] * \
                math.sin( sun_altitude[hh] ) * math.cos( slope_angle ) + \
                math.cos( sun_altitude[hh] ) * math.sin( slope_angle ) * math.cos( slope_azimuth - sun_azimuth[hh] )

            # 傾斜面の単位面積当たりの天空日射量 [W/m2]
            Ios_slope[hh] = Ios[hh] * (1 + math.cos(slope_angle)) / 2


        # 傾斜面における単位面積あたりの平均日射量 [W/m2]
        Is_slope  = np.zeros(8760)
        for hh in range(0,8760):
            
            if Iod_slope[hh] >= 0:
                Is_slope[hh] = Iod_slope[hh] + Ios_slope[hh]
            else:
                Is_slope[hh] = Ios_slope[hh]


        # 結果を保存
        resultJson["PhotovoltaicSystems"][system_name]["Tout"] = Tout
        resultJson["PhotovoltaicSystems"][system_name]["Iod"] = Iod
        resultJson["PhotovoltaicSystems"][system_name]["Ios"] = Ios
        resultJson["PhotovoltaicSystems"][system_name]["Is_slope"] = Is_slope
        resultJson["PhotovoltaicSystems"][system_name]["Iod_slope"] = Iod_slope
        resultJson["PhotovoltaicSystems"][system_name]["Ios_slope"] = Ios_slope


        ##----------------------------------------------------------------------------------
        ## 第九章 自然エネルギー利用設備　第一節 太陽光発電設備
        ##----------------------------------------------------------------------------------
        
        # 太陽電池アレイ設置方式によって決まる係数
        if inputdata["PhotovoltaicSystems"][system_name]["ArraySetupType"] == "架台設置形":
            fa = 46
            fb = 0.41
        elif inputdata["PhotovoltaicSystems"][system_name]["ArraySetupType"] == "屋根置き形":
            fa = 50
            fb = 0.38
        elif inputdata["PhotovoltaicSystems"][system_name]["ArraySetupType"] == "その他":
            fa = 57
            fb = 0.33
        else:
            raise Exception("太陽電池アレイの設置方式が不正です")

        # 太陽電池アレイの総合設計係数
        if inputdata["PhotovoltaicSystems"][system_name]["CellType"] == "結晶系":
            K_hs = 1.00  # 日陰補正係数
            K_pd = 0.96  # 経時変化補正係数
            K_pm = 0.94  # アレイ負荷整合補正係数
            K_pa = 0.97  # アレイ回路補正係数
            alpha_p_max = -0.0041  # 太陽電池アレイの最大出力温度係数
        else:
            K_hs = 1.00  # 日陰補正係数
            K_pd = 0.99  # 経時変化補正係数
            K_pm = 0.94  # アレイ負荷整合補正係数
            K_pa = 0.97  # アレイ回路補正係数
            alpha_p_max = -0.0020  # 太陽電池アレイの最大出力温度係数

        # インバータ回路補正係数
        if inputdata["PhotovoltaicSystems"][system_name]["PowerConditionerEfficiency"] == None:
            # K_in = 0.927 * 0.97
            K_in = 0.928 * 0.97
        else:
            K_in = inputdata["PhotovoltaicSystems"][system_name]["PowerConditionerEfficiency"] * 0.97

        # 太陽電池アレイ𝑖の温度補正係数
        T_cr = np.zeros(8760)
        K_pt = np.zeros(8760)
        K_pi = np.zeros(8760)
        for hh in range(0, 8760):

            # 太陽電池アレイ𝑖の加重平均太陽電池モジュール温度
            T_cr[hh] = Tout[hh] + (fa/( fb * (1.5)**(0.8) + 1 ) + 2) * Is_slope[hh] * 10**(-3) - 2

            # 太陽電池アレイ𝑖の温度補正係数
            K_pt[hh] = 1 + alpha_p_max * (T_cr[hh] - 25)

            K_pi[hh] = K_hs * K_pd * K_pt[hh] * K_pa * K_pm * K_in


        # 1時間当たりの太陽電池アレイ𝑖の発電量 [kWh]
        Ep   = np.zeros(8760)
        for hh in range(0, 8760):
            Ep[hh] = inputdata["PhotovoltaicSystems"][system_name]["ArrayCapacity"] * \
                (1/1) * Is_slope[hh] * K_pi[hh] * 10**(-3)

        # 結果を保存
        resultJson["PhotovoltaicSystems"][system_name]["Ep"] = Ep
        resultJson["PhotovoltaicSystems"][system_name]["T_cr"] = T_cr
        
        # 発電量（一次エネ換算） [kWh] * [kJ/kWh] / 1000 = [MJ]
        resultJson["E_photovoltaic"] += np.sum(resultJson["PhotovoltaicSystems"][system_name]["Ep"],0) * bc.fprime / 1000



    # 発電量


    return resultJson


if __name__ == '__main__':

    print('----- photovoltaic.py -----')
    filename = './sample/sample01_WEBPRO_inputSheet_for_Ver2.5.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = True)
    print(resultJson)

    with open("resultJson.json",'w') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = MyEncoder)