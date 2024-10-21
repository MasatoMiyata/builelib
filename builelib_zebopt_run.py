import json
import math
import os
import time

import numpy as np

from builelib import (
    airconditioning_webpro,
    ventilation,
    lighting,
    hotwatersupply,
    elevator,
    photovoltaic,
    other_energy,
    cogeneration, climate,
)
from builelib.domain.request import AreaByDirection, Room, Building, BuilelibRequest


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


def builelib_run(
        exec_calculation,
        input_data,
        output_base_name,
        flow_control,
        heat_source_performance,
        area,
        ac_operation_mode,
        window_heat_transfer_performance,
        glass2window,
        heat_thermal_conductivity,
        heat_thermal_conductivity_model,
        t_out_all,
        x_out_all,
        iod_all,
        ios_all,
        inn_all,
        q_room_coeffi,
        room_usage_schedule,
        calender,
        lighting_ctrl,
        ventilation_ctrl
):
    """Builelibを実行するプログラム
    Args:
        exec_calculation (str): 計算の実行 （True: 計算も行う、 False: 計算は行わない）
        input_file_name (str): 入力ファイルの名称
    """

    start_time = time.time()

    # ------------------------------------
    # 引数の受け渡し
    # ------------------------------------
    exec_calculation = bool(
        exec_calculation
    )
    # input_file_name = str(input_file_name)

    # ------------------------------------
    # 出力ファイルの定義
    # ------------------------------------
    calc_result = {
        "設計一次エネルギー消費量[MJ]": 0,
        "基準一次エネルギー消費量[MJ]": 0,
        "設計一次エネルギー消費量（その他除き）[MJ]": 0,
        "基準一次エネルギー消費量（その他除き）[MJ]": 0,
        "BEI": "",
        "設計一次エネルギー消費量（再エネ、その他除き）[MJ]": 0,
        "BEI（再エネ除き）": "",
        "設計一次エネルギー消費量（空調）[MJ]": 0,
        "基準一次エネルギー消費量（空調）[MJ]": 0,
        "BEI_AC": "-",  # BEI（空調）
        "設計一次エネルギー消費量（換気）[MJ]": 0,
        "基準一次エネルギー消費量（換気）[MJ]": 0,
        "BEI_V": "-",  # BEI（換気）
        "設計一次エネルギー消費量（照明）[MJ]": 0,
        "基準一次エネルギー消費量（照明）[MJ]": 0,
        "BEI_L": "-",  # BEI（照明）
        "設計一次エネルギー消費量（給湯）[MJ]": 0,
        "基準一次エネルギー消費量（給湯）[MJ]": 0,
        "BEI_HW": "-",  # BEI（給湯）
        "設計一次エネルギー消費量（昇降機）[MJ]": 0,
        "基準一次エネルギー消費量（昇降機）[MJ]": 0,
        "BEI_EV": "-",  # BEI（昇降機）
        "その他一次エネルギー消費量[MJ]": 0,
        "創エネルギー量（太陽光）[MJ]": 0,
        "創エネルギー量（コジェネ）[MJ]": 0,
    }

    # CGSの計算に必要となる変数
    result_json_for_cgs = {
        "AC": {},
        "V": {},
        "L": {},
        "HW": {},
        "EV": {},
        "PV": {},
        "OT": {},
    }

    # 設計一次エネルギー消費量[MJ]
    energy_consumption_design = 0
    # 基準一次エネルギー消費量[MJ]
    energy_consumption_standard = 0

    # ------------------------------------
    # 空気調和設備の計算の実行
    # ------------------------------------

    # 実行
    result_data_AC = {}

    if exec_calculation:

        try:
            if input_data[
                "air_conditioning_zone"
            ]:  # air_conditioning_zone が 空 でなければ

                result_data_AC = airconditioning_webpro.calc_energy(
                    input_data,
                    False,
                    flow_control,
                    heat_source_performance,
                    area,
                    ac_operation_mode,
                    window_heat_transfer_performance,
                    glass2window,
                    str(input_data["building"]["region"]),
                    heat_thermal_conductivity,
                    heat_thermal_conductivity_model,
                    t_out_all,
                    x_out_all,
                    iod_all,
                    ios_all,
                    inn_all,
                    q_room_coeffi,
                    room_usage_schedule,
                    calender
                )

                # CGSの計算に必要となる変数
                result_json_for_cgs["AC"] = result_data_AC["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_AC[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                energy_consumption_standard += result_data_AC[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                calc_result["設計一次エネルギー消費量（空調）[MJ]"] = result_data_AC[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                calc_result["基準一次エネルギー消費量（空調）[MJ]"] = result_data_AC[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                calc_result["BEI_AC"] = math.ceil(result_data_AC["BEI/AC"] * 100) / 100

            else:
                result_data_AC = {"message": "空気調和設備はありません。"}

        except:
            result_data_AC = {
                "error": "空気調和設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        result_data_AC = {"error": "空気調和設備の計算は実行されませんでした。"}

    # 出力
    with open(output_base_name + "_result_AC.json", "w", encoding="utf-8") as fw:
        json.dump(result_data_AC, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    # ------------------------------------
    # 機械換気設備の計算の実行
    # ------------------------------------

    # 実行
    result_data_V = {}
    if exec_calculation:

        try:
            if input_data["ventilation_room"]:  # ventilation_room が 空 でなければ

                result_data_V = ventilation.calc_energy(input_data, ventilation_ctrl, DEBUG=False)

                # CGSの計算に必要となる変数
                result_json_for_cgs["V"] = result_data_V["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_V[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                energy_consumption_standard += result_data_V[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                calc_result["設計一次エネルギー消費量（換気）[MJ]"] = result_data_V[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                calc_result["基準一次エネルギー消費量（換気）[MJ]"] = result_data_V[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                # Modified to avoid error
                if result_data_V.get("BEI/V") is not None:
                    calc_result["BEI_V"] = math.ceil(result_data_V["BEI/V"] * 100) / 100
                else:
                    calc_result["BEI_V"] = 0

            else:
                result_data_V = {"message": "機械換気設備はありません。"}

        except:
            result_data_V = {
                "error": "機械換気設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        result_data_V = {"error": "機械換気設備の計算は実行されませんでした。"}

    # 出力
    with open(output_base_name + "_result_V.json", "w", encoding="utf-8") as fw:
        json.dump(result_data_V, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    # ------------------------------------
    # 照明設備の計算の実行
    # ------------------------------------

    # 実行
    result_data_L = {}
    if exec_calculation:

        try:
            if input_data["lighting_systems"]:  # lighting_systems が 空 でなければ

                result_data_L = lighting.calc_energy(input_data, lighting_ctrl, calender, room_usage_schedule,
                                                     DEBUG=False)
                # CGSの計算に必要となる変数
                result_json_for_cgs["L"] = result_data_L["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_L["E_lighting"]
                energy_consumption_standard += result_data_L["Es_lighting"]
                calc_result["設計一次エネルギー消費量（照明）[MJ]"] = result_data_L[
                    "E_lighting"
                ]
                calc_result["基準一次エネルギー消費量（照明）[MJ]"] = result_data_L[
                    "Es_lighting"
                ]
                calc_result["BEI_L"] = math.ceil(result_data_L["BEI_L"] * 100) / 100

            else:
                result_data_L = {"message": "照明設備はありません。"}

        except:
            result_data_L = {"error": "照明設備の計算時に予期せぬエラーが発生しました。"}

    else:
        result_data_L = {"error": "照明設備の計算は実行されませんでした。"}

    # 出力
    with open(output_base_name + "_result_L.json", "w", encoding="utf-8") as fw:
        json.dump(result_data_L, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    # ------------------------------------
    # 給湯設備の計算の実行
    # ------------------------------------

    # 実行
    result_data_HW = {}

    if exec_calculation:

        try:
            if input_data["hot_water_room"]:  # hot_water_room が 空 でなければ

                result_data_HW = hotwatersupply.calc_energy(input_data, DEBUG=False)

                # CGSの計算に必要となる変数
                result_json_for_cgs["HW"] = result_data_HW["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_HW[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                energy_consumption_standard += result_data_HW[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                calc_result["設計一次エネルギー消費量（給湯）[MJ]"] = result_data_HW[
                    "設計一次エネルギー消費量[MJ/年]"
                ]
                calc_result["基準一次エネルギー消費量（給湯）[MJ]"] = result_data_HW[
                    "基準一次エネルギー消費量[MJ/年]"
                ]
                calc_result["BEI_HW"] = math.ceil(result_data_HW["BEI/hW"] * 100) / 100

            else:
                result_data_HW = {"message": "給湯設備はありません。"}

        except:
            result_data_HW = {
                "error": "給湯設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        result_data_HW = {"error": "給湯設備の計算は実行されませんでした。"}

    # 出力
    with open(output_base_name + "_result_HW.json", "w", encoding="utf-8") as fw:
        json.dump(result_data_HW, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    # ------------------------------------
    # 昇降機の計算の実行
    # ------------------------------------

    # 実行
    result_data_EV = {}
    if exec_calculation:

        try:
            if len(input_data["elevators"]) > 0:
                result_data_EV = elevator.calc_energy(input_data, False, calender, room_usage_schedule)
                # CGSの計算に必要となる変数
                result_json_for_cgs["EV"] = result_data_EV["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += result_data_EV["E_elevator"]
                energy_consumption_standard += result_data_EV["Es_elevator"]
                calc_result["設計一次エネルギー消費量（昇降機）[MJ]"] = result_data_EV[
                    "E_elevator"
                ]
                calc_result["基準一次エネルギー消費量（昇降機）[MJ]"] = result_data_EV[
                    "Es_elevator"
                ]
                calc_result["BEI_EV"] = math.ceil(result_data_EV["BEI_EV"] * 100) / 100

            else:
                result_data_EV = {"message": "昇降機はありません。"}
        except:
            result_data_EV = {"error": "昇降機の計算時に予期せぬエラーが発生しました。"}

    else:
        result_data_EV = {"error": "昇降機の計算は実行されませんでした。"}

    # 出力
    with open(output_base_name + "_result_EV.json", "w", encoding="utf-8") as fw:
        json.dump(result_data_EV, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    # ------------------------------------
    # 太陽光発電の計算の実行
    # ------------------------------------

    # 実行
    result_data_PV = {}
    if exec_calculation:

        try:
            if input_data[
                "photovoltaic_systems"
            ]:  # photovoltaic_systems が 空 でなければ

                result_data_PV = photovoltaic.calc_energy(input_data, DEBUG=False)

                # CGSの計算に必要となる変数
                result_json_for_cgs["PV"] = result_data_PV["for_cgs"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design -= result_data_PV["E_photovoltaic"]
                calc_result["創エネルギー量（太陽光）[MJ]"] = result_data_PV[
                    "E_photovoltaic"
                ]

            else:
                result_data_PV = {"message": "太陽光発電設備はありません。"}
        # except:
        #     result_data_PV = {
        #         "error": "太陽光発電設備の計算時に予期せぬエラーが発生しました。"
        #     }
        except Exception as e:
            # エラー詳細とスタックトレースをキャプチャ
            result_data_PV = {
                "error": "太陽光発電設備の計算時に予期せぬエラーが発生しました。",
                "details": str(e),
                "traceback": traceback.format_exc()  # スタックトレースを追加
            }
    else:
        result_data_PV = {"error": "太陽光発電設備の計算は実行されませんでした。"}

    # 出力
    with open(output_base_name + "_result_PV.json", "w", encoding="utf-8") as fw:
        json.dump(result_data_PV, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    # ------------------------------------
    # その他の計算の実行
    # ------------------------------------

    # 実行
    result_data_OT = {}
    if exec_calculation:

        try:
            if input_data["rooms"]:  # rooms が 空 でなければ

                result_data_OT = other_energy.calc_energy(input_data, DEBUG=False)

                # CGSの計算に必要となる変数
                result_json_for_cgs["OT"] = result_data_OT["for_cgs"]
                calc_result["その他一次エネルギー消費量[MJ]"] = result_data_OT["E_other"]

            else:
                result_data_OT = {"message": "その他一次エネルギー消費量は0です。"}
        except:
            result_data_OT = {
                "error": "その他一次エネルギー消費量の計算時に予期せぬエラーが発生しました。"
            }
    else:
        result_data_OT = {
            "error": "その他一次エネルギー消費量の計算は実行されませんでした。"
        }

    # 出力
    with open(
            output_base_name + "_result_Other.json", "w", encoding="utf-8"
    ) as fw:
        json.dump(result_data_OT, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    # ------------------------------------
    # コジェネの計算の実行
    # ------------------------------------

    # 実行
    result_data_CGS = {}
    if exec_calculation:

        try:
            if input_data[
                "cogeneration_systems"
            ]:  # cogeneration_systems が 空 でなければ
                result_data_CGS = cogeneration.calc_energy(
                    input_data, result_json_for_cgs, DEBUG=False
                )

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design -= (
                        result_data_CGS["年間一次エネルギー削減量"] * 1000
                )
                calc_result["創エネルギー量（コジェネ）[MJ]"] = (
                        result_data_CGS["年間一次エネルギー削減量"] * 1000
                )

            else:
                result_data_CGS = {"message": "コージェネレーション設備はありません。"}
        except:
            result_data_CGSa_OT = {
                "error": "コージェネレーション設備の計算時に予期せぬエラーが発生しました。"
            }
    else:
        result_data_CGS = {
            "error": "コージェネレーション設備の計算は実行されませんでした。"
        }

    # 出力
    with open(
            output_base_name + "_result_CGS.json", "w", encoding="utf-8"
    ) as fw:
        json.dump(result_data_CGS, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    # ------------------------------------
    # BEIの計算
    # ------------------------------------

    if energy_consumption_standard != 0:

        calc_result["設計一次エネルギー消費量（その他除き）[MJ]"] = (
            energy_consumption_design
        )
        calc_result["基準一次エネルギー消費量（その他除き）[MJ]"] = (
            energy_consumption_standard
        )

        calc_result["BEI"] = energy_consumption_design / energy_consumption_standard
        calc_result["BEI"] = math.ceil(calc_result["BEI"] * 100) / 100

        calc_result["設計一次エネルギー消費量（再エネ、その他除き）[MJ]"] = (
                energy_consumption_design + calc_result["創エネルギー量（太陽光）[MJ]"]
        )

        calc_result["BEI（再エネ除き）"] = (
                calc_result["設計一次エネルギー消費量（再エネ、その他除き）[MJ]"]
                / calc_result["基準一次エネルギー消費量（その他除き）[MJ]"]
        )
        calc_result["BEI（再エネ除き）"] = (
                math.ceil(calc_result["BEI（再エネ除き）"] * 100) / 100
        )

        # 設計一次エネ・基準一次エネにその他を追加
        if "E_other" in result_data_OT:
            calc_result["設計一次エネルギー消費量[MJ]"] = (
                    energy_consumption_design + result_data_OT["E_other"]
            )
            calc_result["基準一次エネルギー消費量[MJ]"] = (
                    energy_consumption_standard + result_data_OT["E_other"]
            )

    # ------------------------------------
    # 計算結果ファイルの出力
    # ------------------------------------

    with open(output_base_name + "_result.json", "w", encoding="utf-8") as fw:
        json.dump(calc_result, fw, indent=4, ensure_ascii=False, cls=MyEncoder)

    end_time = time.time() - start_time
    print(f"総実行時間: {end_time:.2f} 秒")


if __name__ == "__main__":
    req = BuilelibRequest(
        height=20,
        rooms=[Room(is_air_conditioned=True, room_type="事務室"), Room(is_air_conditioned=True, room_type="事務室")],
        areas=[AreaByDirection(direction="north", area=1000), AreaByDirection(direction="south", area=1000),
               AreaByDirection(direction="east", area=1000), AreaByDirection(direction="west", area=1000)],
        floor_number=5,
        wall_u_value=0.5,
        glass_u_value=0.5,
        glass_solar_heat_gain_rate=3,
        window_ratio=0.4,
        building_type="事務所等",
        model_building_type="事務所モデル",
        lighting_number=2,
        lighting_power=400,
        elevator_number=2,
        is_solar_power=True,
        building_information=Building(
            name="test",
            prefecture="北海道",
            city="札幌市",
            address="北1条西1丁目",
            region_number=1,
            annual_solar_region="A3"
        ),
        air_heat_exchange_rate_cooling=52,
        air_heat_exchange_rate_heating=29,
    )
    r = req.create_default_json_file()
    # コマンドライン引数からファイル名を取得
    # if len(sys.argv) > 2:
    #     input_filename = sys.argv[1]
    #     output_base_name = sys.argv[2]
    # else:
    #     # デフォルトのファイル名
    output_base_name = 'zebopt'
    #
    # # current directory
    d = os.path.dirname(__file__)
    exp_directory = os.path.join(d, "experiment/")

    database_directory = os.path.dirname(os.path.abspath(__file__)) + "/builelib/database/"
    climate_data_directory = os.path.dirname(os.path.abspath(__file__)) + "/builelib/climatedata/"

    # with open(input_filename, 'w', encoding='utf-8') as json_file:
    #     json.dump(req.create_default_json_file(), json_file, ensure_ascii=False, indent=4)

    # 流量制御
    with open(database_directory + 'flow_control.json', 'r', encoding='utf-8') as f:
        flow_control = json.load(f)

    # 熱源機器特性
    with open(database_directory + "heat_source_performance.json", 'r', encoding='utf-8') as f:
        heat_source_performance = json.load(f)

    # 地域別データの読み込み
    with open(database_directory + 'area.json', 'r', encoding='utf-8') as f:
        area = json.load(f)

    # 空調運転モード
    with open(database_directory + 'ac_operation_mode.json', 'r', encoding='utf-8') as f:
        ac_operation_mode = json.load(f)

    # 窓データの読み込み
    with open(database_directory + 'window_heat_transfer_performance.json', 'r', encoding='utf-8') as f:
        window_heat_transfer_performance = json.load(f)

    with open(database_directory + 'glass2window.json', 'r', encoding='utf-8') as f:
        glass2window = json.load(f)

    # 標準入力法建材データの読み込み
    with open(database_directory + 'heat_thermal_conductivity.json', 'r', encoding='utf-8') as f:
        heat_thermal_conductivity = json.load(f)

    # モデル建物法建材データの読み込み
    with open(database_directory + 'heat_thermal_conductivity_model.json', 'r', encoding='utf-8') as f:
        heat_thermal_conductivity_model = json.load(f)

    # 気象データ（HASP形式）読み込み ＜365×24の行列＞
    [t_out_all, x_out_all, iod_all, ios_all, inn_all] = \
        climate.read_hasp_climate_data(
            climate_data_directory + "/" + area[str(req.building_information.region_number) + "地域"]["気象データファイル名"])

    ## 室負荷計算のための係数（解説書 A.3）
    with open(database_directory + 'qroom_coeffi_area' + str(req.building_information.region_number) + '.json', 'r',
              encoding='utf-8') as f:
        q_room_coeffi = json.load(f)

    # 室使用条件データの読み込み
    with open(database_directory + 'room_usage_schedule.json', 'r', encoding='utf-8') as f:
        room_usage_schedule = json.load(f)

    with open(database_directory + 'lighting_control.json', 'r', encoding='utf-8') as f:
        lighting_ctrl = json.load(f)

    # カレンダーパターンの読み込み
    with open(database_directory + 'calender.json', 'r', encoding='utf-8') as f:
        calender = json.load(f)

    with open(database_directory + '/ventilation_control.json', 'r', encoding='utf-8') as f:
        ventilation_ctrl = json.load(f)

    builelib_run(
        True,
        r,
        output_base_name,
        flow_control,
        heat_source_performance,
        area,
        ac_operation_mode,
        window_heat_transfer_performance,
        glass2window,
        heat_thermal_conductivity,
        heat_thermal_conductivity_model,
        t_out_all,
        x_out_all,
        iod_all,
        ios_all,
        inn_all,
        q_room_coeffi,
        room_usage_schedule,
        calender,
        lighting_ctrl,
        ventilation_ctrl
    )
