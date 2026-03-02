#-------------------------------------------------------------------------
# このプログラムは、
# 平成28年省エネルギー基準に準拠したエネルギー消費性能の評価に関する技術情報（住宅）
# https://www.kenken.go.jp/becc/house.html
# の 第九章　自然エネルギー利用設備 第一節　太陽光発電設備 を基に作成しました。
#-------------------------------------------------------------------------
import json
import numpy as np
import os
import math
import pandas as pd

import sys

from builelib import commons as bc
from builelib.climate import climate

# 気象データファイルの保存場所
from builelib.climate import CLIMATEDATA_DIR as climatedata_directory

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/database/"

# 日射地域区分と気象ファイル名の関係
with open(database_directory + "common_annual_solar_level.json", encoding="utf-8") as f:
    _AnnualSolarLevel = json.load(f)


def calc_energy(inputdata, DEBUG = False, output_dir = "", db = None):
    """
    Parameters
    ----------
    inputdata : dict
        入力データ辞書（webproJsonSchema準拠）。
    DEBUG : bool, optional
        デバッグ出力の有無。
    output_dir : str, optional
        出力ディレクトリのパス。
    db : dict, optional
        database_loader.load_all_databases() の戻り値（太陽光発電では未使用）。
    """

    # 一次エネルギー換算係数
    fprime = 9760
    if "CalculationMode" in inputdata:
        if isinstance(inputdata["CalculationMode"]["一次エネルギー換算係数"], (int, float)):
            fprime = inputdata["CalculationMode"]["一次エネルギー換算係数"]

    # 計算結果を格納する変数
    resultJson = {
        "E_photovoltaic": 0,
        "PhotovoltaicSystems": {},
        "for_CGS": {
            "Edesign_MWh_day": np.zeros(365)
        }
    }

    # 地域区分と気象ファイル名の関係
    if db is not None:
        climate_data_file = db["AnnualSolarLevel"]
    else:
        climate_data_file = _AnnualSolarLevel

    for system_name in inputdata["PhotovoltaicSystems"]:

        resultJson["PhotovoltaicSystems"][system_name] = {
            "Ep_kWh": 0,
            "Ep" : np.zeros(8760),
        }

        ##----------------------------------------------------------------------------------
        ## 入力の整理
        ##----------------------------------------------------------------------------------

        # 傾斜面の方位角（南が0°、西が90°、北180°、東270°）
        slope_azimuth= inputdata["PhotovoltaicSystems"][system_name]["Direction"]

        # 傾斜面の傾斜角（水平0°、垂直90°） 一の位を四捨五入
        slope_angle = round(inputdata["PhotovoltaicSystems"][system_name]["Angle"], -1)

        # 90度を超えた場合でも計算できるように調整
        # if slope_angle > 90:
        #     slope_angle = 90

        ##----------------------------------------------------------------------------------
        ## 付録 A 傾斜面における単位面積当たりの平均日射量
        ##----------------------------------------------------------------------------------

        # 任意入力（様式 SP-CD: 気象データ入力シート）
        #  ただし、緯度・経度の入力がある場合のみ読み込む
        if "climate_data" in inputdata["SpecialInputData"] and \
            "latitude" in inputdata["SpecialInputData"]["climate_data"] and "longitude" in inputdata["SpecialInputData"]["climate_data"]:

            # 外気温 [℃]
            Tout = np.array(inputdata["SpecialInputData"]["climate_data"]["Tout"])
            # 法線面直達日射量 [W/m2] ⇒ [MJ/m2h]
            Iod  = np.array(inputdata["SpecialInputData"]["climate_data"]["Iod"]) /1000000*3600
            # 水平面天空日射量 [W/m2] ⇒ [MJ/m2h]
            Ios  = np.array(inputdata["SpecialInputData"]["climate_data"]["Ios"]) /1000000*3600

            Tout = np.array(bc.trans_36524to8760(Tout))
            Iod  = np.array(bc.trans_36524to8760(Iod))
            Ios  = np.array(bc.trans_36524to8760(Ios))

            # 太陽高度 [°], 太陽方位角 [°]
            (sun_altitude, sun_azimuth) = \
                climate.calc_solar_position(
                inputdata["SpecialInputData"]["climate_data"]["latitude"],
                inputdata["SpecialInputData"]["climate_data"]["longitude"],
                inputdata["SpecialInputData"]["climate_data"]["longitude_std"]
                )

        elif climate_data_file[ inputdata["Building"]["AnnualSolarRegion"] ][ inputdata["Building"]["Region"]+"地域" ]:

            # 気象データの読み込み（日射量は MJ/m2h）
            [Tout, Iod, Ios, sun_altitude, sun_azimuth] = \
            climate.readCsvClimateData( climatedata_directory + climate_data_file[ inputdata["Building"]["AnnualSolarRegion"] ][ inputdata["Building"]["Region"]+"地域" ] )
        
        else:
            raise Exception('日射地域区分の指定が不正です')

        # 傾斜面における単位面積あたりの直達・天空日射量 [W/m2]
        Iod_slope = np.zeros(8760)
        Ios_slope = np.zeros(8760)
        sun_altitude_rad = np.zeros(8760)
        sun_azimuth_rad  = np.zeros(8760)
        for hh in range(0,8760):

            sun_altitude_rad[hh] = math.radians(sun_altitude[hh])

            if sun_azimuth[hh] < 0:
                sun_azimuth_rad[hh]  = math.radians(sun_azimuth[hh]+360)
            else:
                sun_azimuth_rad[hh]  = math.radians(sun_azimuth[hh])

            # 傾斜面の単位面積当たりの直達日射量 [W/m2]
            Iod_slope[hh] = Iod[hh] / 3.6 * 10**3 * \
                (math.sin( sun_altitude_rad[hh] ) * math.cos( math.radians(slope_angle) ) + \
                math.cos( sun_altitude_rad[hh] ) * math.sin( math.radians(slope_angle) ) * \
                math.cos( math.radians(slope_azimuth) - sun_azimuth_rad[hh] ))

            # 傾斜面の単位面積当たりの天空日射量 [W/m2]
            Ios_slope[hh] = Ios[hh] / 3.6 * 10**3 * (1 + math.cos( math.radians(slope_angle) )) / 2


        # 傾斜面における単位面積あたりの平均日射量 [W/m2]
        Is_slope  = np.zeros(8760)
        for hh in range(0,8760):
            
            if Iod_slope[hh] >= 0:
                Is_slope[hh] = Iod_slope[hh] + Ios_slope[hh]
            else:
                Is_slope[hh] = Ios_slope[hh]


        # 結果を保存
        resultJson["PhotovoltaicSystems"][system_name]["Tout"] = Tout
        resultJson["PhotovoltaicSystems"][system_name]["Iod_W/m2"] = Iod / 3.6 * 10**3
        resultJson["PhotovoltaicSystems"][system_name]["Ios_W/m2"] = Ios / 3.6 * 10**3
        resultJson["PhotovoltaicSystems"][system_name]["slope_azimuth_rad"] = math.radians(slope_azimuth)
        resultJson["PhotovoltaicSystems"][system_name]["slope_angle_rad"] = math.radians(slope_angle)
        resultJson["PhotovoltaicSystems"][system_name]["sun_altitude_rad"] = sun_altitude_rad
        resultJson["PhotovoltaicSystems"][system_name]["sun_azimuth_rad"] = sun_azimuth_rad
        resultJson["PhotovoltaicSystems"][system_name]["Iod_slope_W/m2"] = Iod_slope
        resultJson["PhotovoltaicSystems"][system_name]["Ios_slope_W/m2"] = Ios_slope
        resultJson["PhotovoltaicSystems"][system_name]["Is_slope_W/m2"] = Is_slope


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
            K_in = 0.927 * 0.97   # デフォルト値変更
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

            # 太陽電池アレイの総合設計係数
            K_pi[hh] = K_hs * K_pd * K_pt[hh] * K_pa * K_pm * K_in


        # 1時間当たりの太陽電池アレイ𝑖の発電量 [kWh]
        Ep   = np.zeros(8760)
        for hh in range(0, 8760):
            Ep[hh] = inputdata["PhotovoltaicSystems"][system_name]["ArrayCapacity"] * \
                (1/1) * Is_slope[hh] * K_pi[hh] * 10**(-3)

        # 結果を保存
        resultJson["PhotovoltaicSystems"][system_name]["Ep"] = Ep
        resultJson["PhotovoltaicSystems"][system_name]["T_cr"] = T_cr   # 太陽電池モジュール温度
        resultJson["PhotovoltaicSystems"][system_name]["K_pt"] = K_pt   # 太陽電池アレイの温度補正係数
        resultJson["PhotovoltaicSystems"][system_name]["K_pi"] = K_pi   # 太陽電池アレイの総合設計係数
        
        # 発電量 [kWh]
        resultJson["PhotovoltaicSystems"][system_name]["Ep_kWh"] = np.sum(resultJson["PhotovoltaicSystems"][system_name]["Ep"],0)

        # 発電量（一次エネ換算） [kWh] * [kJ/kWh] / 1000 = [MJ]
        resultJson["PhotovoltaicSystems"][system_name]["Ep_MJ"] = resultJson["PhotovoltaicSystems"][system_name]["Ep_kWh"] * fprime / 1000

        # 発電量を積算
        resultJson["E_photovoltaic"] += resultJson["PhotovoltaicSystems"][system_name]["Ep_MJ"]

        # 発電量（日積算） [MWh/day]
        for dd in range(0,365):
            for hh in range(0,24):
                tt = 24*dd+hh
                resultJson["for_CGS"]["Edesign_MWh_day"][dd] += resultJson["PhotovoltaicSystems"][system_name]["Ep"][tt] / 1000


    resultJson["E_photovoltaic_GJ"] = resultJson["E_photovoltaic"] /1000


    ##----------------------------------------------------------------------------------
    # CSV出力
    ##----------------------------------------------------------------------------------
    if output_dir != "":
        output_dir = output_dir + "_"

    df_daily_energy = pd.DataFrame({
        '創エネルギー量（太陽光発電設備）[GJ]'  : resultJson["for_CGS"]["Edesign_MWh_day"] * (fprime) /1000,
        '創エネルギー量（太陽光発電設備）[MWh]'  : resultJson["for_CGS"]["Edesign_MWh_day"],
    }, index=bc.date_1year)

    df_daily_energy.to_csv(output_dir + 'result_PV_Energy_daily.csv', index_label="日時", encoding='CP932')


    return resultJson


if __name__ == '__main__':

    # 現在のスクリプトファイルのディレクトリを取得
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # 1つ上の階層のディレクトリパスを取得
    parent_dir = os.path.abspath(os.path.join(current_dir, os.pardir))

    print('----- photovoltaic.py -----')
    # filename = parent_dir + '/sample/sample01_WEBPRO_inputSheet_for_Ver3.6.json'
    filename = './Brunei/Brunei_Office_Building_v3_20251201_input.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        inputdata = json.load(f)

    resultJson = calc_energy(inputdata, DEBUG = True)

    with open("resultJson_PV.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

    for system_name in resultJson["PhotovoltaicSystems"]:
        print(resultJson["PhotovoltaicSystems"][system_name]["Ep_kWh"])