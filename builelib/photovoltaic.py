# -------------------------------------------------------------------------
# このプログラムは、
# 平成28年省エネルギー基準に準拠したエネルギー消費性能の評価に関する技術情報（住宅）
# https://www.kenken.go.jp/becc/house.html
# の 第九章　自然エネルギー利用設備 第一節　太陽光発電設備 を基に作成しました。
# -------------------------------------------------------------------------
import json
import math
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import commons as bc
import climate

# 気象データファイルの保存場所
climate_data_directory = os.path.dirname(os.path.abspath(__file__)) + "/climatedata/"


def calc_energy(input_data, DEBUG=False):
    # 計算結果を格納する変数
    result_json = {
        "E_photovoltaic": 0,
        "photovoltaic_systems": {},
        "for_cgs": {
            "Edesign_MWh_day": np.zeros(365)
        }
    }

    # 地域区分と気象ファイル名の関係
    climate_data_file = {
        "1地域": {
            "A1": "7.csv",
            "A2": "117.csv",
            "A3": "124.csv",
            "A4": None,
            "A5": None
        },
        "2地域": {
            "A1": "49.csv",
            "A2": "63.csv",
            "A3": "59.csv",
            "A4": "59-A4.csv",
            "A5": "59-A5.csv"
        },
        "3地域": {
            "A1": "190.csv",
            "A2": "230.csv",
            "A3": "426.csv",
            "A4": "403.csv",
            "A5": "412.csv"
        },
        "4地域": {
            "A1": "286.csv",
            "A2": "186.csv",
            "A3": "292.csv",
            "A4": "423.csv",
            "A5": "401.csv"
        },
        "5地域": {
            "A1": "593.csv",
            "A2": "542.csv",
            "A3": "495.csv",
            "A4": "473.csv",
            "A5": "420.csv"
        },
        "6地域": {
            "A1": None,
            "A2": "569.csv",
            "A3": "551.csv",
            "A4": "480.csv",
            "A5": "438.csv"
        },
        "7地域": {
            "A1": "819-A1.csv",
            "A2": "819-A2.csv",
            "A3": "819.csv",
            "A4": "798.csv",
            "A5": "797.csv"
        },
        "8地域": {
            "A1": None,
            "A2": None,
            "A3": "826.csv",
            "A4": "836.csv",
            "A5": "842.csv"
        }
    }

    for system_name in input_data["photovoltaic_systems"]:

        result_json["photovoltaic_systems"][system_name] = {
            "Ep_kWh": 0,
            "Ep": np.zeros(8760),
        }

        ##----------------------------------------------------------------------------------
        ## 入力の整理
        ##----------------------------------------------------------------------------------

        # 傾斜面の方位角（南が0°、西が90°、北180°、東270°）
        slope_azimuth = input_data["photovoltaic_systems"][system_name]["direction"]

        # 傾斜面の傾斜角（水平0°、垂直90°） 一の位を四捨五入
        slope_angle = round(input_data["photovoltaic_systems"][system_name]["angle"], -1)

        # 90度を超えた場合でも計算できるように調整
        # if slope_angle > 90:
        #     slope_angle = 90

        ##----------------------------------------------------------------------------------
        ## 付録 A 傾斜面における単位面積当たりの平均日射量
        ##----------------------------------------------------------------------------------

        # 気象データの読み込み（日射量は MJ/m2h）
        if climate_data_file[input_data["building"]["region"] + "地域"][
            input_data["building"]["annual_solar_region"]] is not None:
            [tout, iod, ios, sun_altitude, sun_azimuth] = \
                climate.read_csv_climate_data(
                    climate_data_directory + climate_data_file[input_data["building"]["region"] + "地域"][
                        input_data["building"]["annual_solar_region"]])
        else:
            raise Exception('日射地域区分の指定が不正です')

        # 傾斜面における単位面積あたりの直達・天空日射量 [W/m2]
        iod_slope = np.zeros(8760)
        ios_slope = np.zeros(8760)
        sun_altitude_rad = np.zeros(8760)
        sun_azimuth_rad = np.zeros(8760)
        for hh in range(0, 8760):

            sun_altitude_rad[hh] = math.radians(sun_altitude[hh])

            if sun_azimuth[hh] < 0:
                sun_azimuth_rad[hh] = math.radians(sun_azimuth[hh] + 360)
            else:
                sun_azimuth_rad[hh] = math.radians(sun_azimuth[hh])

            # 傾斜面の単位面積当たりの直達日射量 [W/m2]
            iod_slope[hh] = iod[hh] / 3.6 * 10 ** 3 * \
                            (math.sin(sun_altitude_rad[hh]) * math.cos(math.radians(slope_angle)) + \
                             math.cos(sun_altitude_rad[hh]) * math.sin(math.radians(slope_angle)) * \
                             math.cos(math.radians(slope_azimuth) - sun_azimuth_rad[hh]))

            # 傾斜面の単位面積当たりの天空日射量 [W/m2]
            ios_slope[hh] = ios[hh] / 3.6 * 10 ** 3 * (1 + math.cos(math.radians(slope_angle))) / 2

        # 傾斜面における単位面積あたりの平均日射量 [W/m2]
        Is_slope = np.zeros(8760)
        for hh in range(0, 8760):

            if iod_slope[hh] >= 0:
                Is_slope[hh] = iod_slope[hh] + ios_slope[hh]
            else:
                Is_slope[hh] = ios_slope[hh]

        # 結果を保存
        result_json["photovoltaic_systems"][system_name]["tout"] = tout
        result_json["photovoltaic_systems"][system_name]["iod_W/m2"] = iod / 3.6 * 10 ** 3
        result_json["photovoltaic_systems"][system_name]["ios_W/m2"] = ios / 3.6 * 10 ** 3
        result_json["photovoltaic_systems"][system_name]["slope_azimuth_rad"] = math.radians(slope_azimuth)
        result_json["photovoltaic_systems"][system_name]["slope_angle_rad"] = math.radians(slope_angle)
        result_json["photovoltaic_systems"][system_name]["sun_altitude_rad"] = sun_altitude_rad
        result_json["photovoltaic_systems"][system_name]["sun_azimuth_rad"] = sun_azimuth_rad
        result_json["photovoltaic_systems"][system_name]["Is_slope_W/m2"] = Is_slope
        result_json["photovoltaic_systems"][system_name]["iod_slope_W/m2"] = iod_slope
        result_json["photovoltaic_systems"][system_name]["ios_slope_W/m2"] = ios_slope

        ##----------------------------------------------------------------------------------
        ## 第九章 自然エネルギー利用設備　第一節 太陽光発電設備
        ##----------------------------------------------------------------------------------

        # 太陽電池アレイ設置方式によって決まる係数
        if input_data["photovoltaic_systems"][system_name]["array_setup_type"] == "架台設置形":
            fa = 46
            fb = 0.41
        elif input_data["photovoltaic_systems"][system_name]["array_setup_type"] == "屋根置き形":
            fa = 50
            fb = 0.38
        elif input_data["photovoltaic_systems"][system_name]["array_setup_type"] == "その他":
            fa = 57
            fb = 0.33
        else:
            raise Exception("太陽電池アレイの設置方式が不正です")

        # 太陽電池アレイの総合設計係数
        if input_data["photovoltaic_systems"][system_name]["cell_type"] == "結晶系":
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
        if input_data["photovoltaic_systems"][system_name]["power_conditioner_efficiency"] is None:
            K_in = 0.927 * 0.97  # デフォルト値変更
        else:
            K_in = input_data["photovoltaic_systems"][system_name]["power_conditioner_efficiency"] * 0.97

        # 太陽電池アレイ𝑖の温度補正係数
        T_cr = np.zeros(8760)
        K_pt = np.zeros(8760)
        K_pi = np.zeros(8760)
        for hh in range(0, 8760):
            # 太陽電池アレイ𝑖の加重平均太陽電池モジュール温度
            T_cr[hh] = tout[hh] + (fa / (fb * (1.5) ** (0.8) + 1) + 2) * Is_slope[hh] * 10 ** (-3) - 2

            # 太陽電池アレイ𝑖の温度補正係数
            K_pt[hh] = 1 + alpha_p_max * (T_cr[hh] - 25)

            # 太陽電池アレイの総合設計係数
            K_pi[hh] = K_hs * K_pd * K_pt[hh] * K_pa * K_pm * K_in

        # 1時間当たりの太陽電池アレイ𝑖の発電量 [kWh]
        Ep = np.zeros(8760)
        for hh in range(0, 8760):
            Ep[hh] = input_data["photovoltaic_systems"][system_name]["array_capacity"] * \
                     (1 / 1) * Is_slope[hh] * K_pi[hh] * 10 ** (-3)

        # 結果を保存
        result_json["photovoltaic_systems"][system_name]["Ep"] = Ep
        result_json["photovoltaic_systems"][system_name]["T_cr"] = T_cr
        result_json["photovoltaic_systems"][system_name]["K_pi"] = K_pi

        # 発電量 [kWh]
        result_json["photovoltaic_systems"][system_name]["Ep_kWh"] = np.sum(
            result_json["photovoltaic_systems"][system_name]["Ep"], 0)

        # 発電量（一次エネ換算） [kWh] * [kJ/kWh] / 1000 = [MJ]
        result_json["photovoltaic_systems"][system_name]["Ep_MJ"] = result_json["photovoltaic_systems"][system_name][
                                                                      "Ep_kWh"] * bc.fprime / 1000

        # 発電量を積算
        result_json["E_photovoltaic"] += result_json["photovoltaic_systems"][system_name]["Ep_MJ"]

        # 発電量（日積算） [MWh/day]
        for dd in range(0, 365):
            for hh in range(0, 24):
                tt = 24 * dd + hh
                result_json["for_cgs"]["Edesign_MWh_day"][dd] += result_json["photovoltaic_systems"][system_name]["Ep"][
                                                                    tt] / 1000

        result_json["E_photovoltaic_GJ"] = result_json["E_photovoltaic"] / 1000

    return result_json


if __name__ == '__main__':

    print('----- photovoltaic.py -----')
    # filename = './tests/cogeneration/Case_hospital_05.json'
    filename = './sample/Builelib_sample_SP1_input.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    result_json = calc_energy(input_data, DEBUG=True)

    with open("result_json_PV.json", 'w', encoding='utf-8') as fw:
        json.dump(result_json, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)

    for system_name in result_json["photovoltaic_systems"]:
        print(result_json["photovoltaic_systems"][system_name]["Ep_kWh"])
