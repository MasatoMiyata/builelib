import json
import numpy as np
import os
import zipfile
import math

from builelib.make_inputdata import make_jsondata_from_Ver2_sheet
from builelib import airconditioning_webpro, ventilation, lighting, hotwatersupply, elevator, photovoltaic, other_energy, cogeneration

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


def builelib_run(exec_calculation, inputfile_name):
    """Builelibを実行するプログラム
    Args:
        exec_calculation (str): 計算の実行 （True: 計算も行う、 False: 計算は行わない）
        inputfile_name (str): 入力ファイルの名称
    """

    #------------------------------------
    # 引数の受け渡し
    #------------------------------------
    exec_calculation = bool(exec_calculation)  # 計算の実行 （True: 計算も行う、 False: 計算は行わない）
    inputfile_name   = str(inputfile_name)     # 入力ファイルの名称

    #------------------------------------
    # 出力ファイルの定義
    #------------------------------------
    calc_reuslt = {
        "設計一次エネルギー消費量[MJ]" : 0,
        "基準一次エネルギー消費量[MJ]" : 0, 
        "設計一次エネルギー消費量（その他除き）[MJ]" : 0,
        "基準一次エネルギー消費量（その他除き）[MJ]" : 0, 
        "BEI": "",
        "設計一次エネルギー消費量（再エネ、その他除き）[MJ]" : 0,
        "BEI（再エネ除き）": "",
        "設計一次エネルギー消費量（空調）[MJ]": 0,
        "基準一次エネルギー消費量（空調）[MJ]": 0,
        "BEI_AC": "-",   # BEI（空調）
        "設計一次エネルギー消費量（換気）[MJ]": 0, 
        "基準一次エネルギー消費量（換気）[MJ]": 0,
        "BEI_V": "-",    # BEI（換気）
        "設計一次エネルギー消費量（照明）[MJ]": 0,
        "基準一次エネルギー消費量（照明）[MJ]": 0,
        "BEI_L": "-",    # BEI（照明）
        "設計一次エネルギー消費量（給湯）[MJ]": 0,
        "基準一次エネルギー消費量（給湯）[MJ]": 0, 
        "BEI_HW": "-",   # BEI（給湯）
        "設計一次エネルギー消費量（昇降機）[MJ]": 0, 
        "基準一次エネルギー消費量（昇降機）[MJ]": 0, 
        "BEI_EV": "-",   # BEI（昇降機）
        "その他一次エネルギー消費量[MJ]" : 0,
        "創エネルギー量（太陽光）[MJ]": 0, 
        "創エネルギー量（コジェネ）[MJ]": 0, 
    }

    # CGSの計算に必要となる変数
    resultJson_for_CGS = {
        "AC":{},
        "V":{},
        "L":{},
        "HW":{},
        "EV":{},
        "PV":{},
        "OT":{},
    }

    # 設計一次エネルギー消費量[MJ]
    energy_consumption_design = 0
    # 基準一次エネルギー消費量[MJ]
    energy_consumption_standard = 0

    #------------------------------------
    # 入力ファイルの読み込み
    #------------------------------------
    inputdata = {}
    validation = {}

    # 渡されたファイルの拡張子を確認
    inputfile_name_split = os.path.splitext(inputfile_name)

    if inputfile_name_split[-1] == ".xlsm" or inputfile_name_split[-1] == ".xlsx":

        # jsonファイルの生成
        try:
            inputdata, validation = make_jsondata_from_Ver2_sheet(inputfile_name)

        except:
            validation = {
                "error": "入力シートの読み込み時に予期せぬエラーが発生しました。"
            }
            exec_calculation = False  # 計算は行わない。

    else:

        validation = {
            "error": "入力シートの拡張子が不正です。"
        }
        exec_calculation = False  # 計算は行わない。


    # エラーが発生したら計算は行わない。
    if len(validation["error"]) > 0:
        exec_calculation = False


    # 出力
    with open(inputfile_name_split[0] + "_input.json",'w', encoding='utf-8') as fw:
        json.dump(inputdata, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # 空気調和設備の計算の実行
    #------------------------------------

    # 実行
    resultdata_AC = {}

    if exec_calculation:
        
        try:
            if inputdata["AirConditioningZone"]:   # AirConditioningZone が 空 でなければ

                resultdata_AC = airconditioning_webpro.calc_energy(inputdata, debug = False, output_dir=inputfile_name_split[0])

                # CGSの計算に必要となる変数
                resultJson_for_CGS["AC"] = resultdata_AC["for_CGS"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += resultdata_AC["設計一次エネルギー消費量[MJ/年]"]
                energy_consumption_standard += resultdata_AC["基準一次エネルギー消費量[MJ/年]"]
                calc_reuslt["設計一次エネルギー消費量（空調）[MJ]"] = resultdata_AC["設計一次エネルギー消費量[MJ/年]"]
                calc_reuslt["基準一次エネルギー消費量（空調）[MJ]"] = resultdata_AC["基準一次エネルギー消費量[MJ/年]"]
                calc_reuslt["BEI_AC"] = math.ceil(resultdata_AC["BEI/AC"] * 100) / 100

            else:
                resultdata_AC = {
                    "message": "空気調和設備はありません。"
                }

        except:
            resultdata_AC = {
                "error": "空気調和設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        resultdata_AC = {
            "error": "空気調和設備の計算は実行されませんでした。"
        }

    # 出力
    with open(inputfile_name_split[0] + "_result_AC.json",'w', encoding='utf-8') as fw:
        json.dump(resultdata_AC, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # 機械換気設備の計算の実行
    #------------------------------------

    # 実行
    resultdata_V = {}
    if exec_calculation:

        try:
            if inputdata["VentilationRoom"]:   # VentilationRoom が 空 でなければ

                resultdata_V = ventilation.calc_energy(inputdata, DEBUG = False, output_dir=inputfile_name_split[0])

                # CGSの計算に必要となる変数
                resultJson_for_CGS["V"] = resultdata_V["for_CGS"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += resultdata_V["設計一次エネルギー消費量[MJ/年]"]
                energy_consumption_standard += resultdata_V["基準一次エネルギー消費量[MJ/年]"]
                calc_reuslt["設計一次エネルギー消費量（換気）[MJ]"] = resultdata_V["設計一次エネルギー消費量[MJ/年]"]
                calc_reuslt["基準一次エネルギー消費量（換気）[MJ]"] = resultdata_V["基準一次エネルギー消費量[MJ/年]"]
                calc_reuslt["BEI_V"] = math.ceil(resultdata_V["BEI/V"] * 100) / 100

            else:
                resultdata_V = {
                    "message": "機械換気設備はありません。"
                }

        except:
            resultdata_V = {
                "error": "機械換気設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        resultdata_V = {
            "error": "機械換気設備の計算は実行されませんでした。"
        }

    # 出力
    with open(inputfile_name_split[0] + "_result_V.json",'w', encoding='utf-8') as fw:
        json.dump(resultdata_V, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # 照明設備の計算の実行
    #------------------------------------

    # 実行
    resultdata_L = {}
    if exec_calculation:

        try:
            if inputdata["LightingSystems"]:   # LightingSystems が 空 でなければ

                resultdata_L = lighting.calc_energy(inputdata, DEBUG = False, output_dir=inputfile_name_split[0])

                # CGSの計算に必要となる変数
                resultJson_for_CGS["L"] = resultdata_L["for_CGS"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += resultdata_L["E_lighting"]
                energy_consumption_standard += resultdata_L["Es_lighting"]
                calc_reuslt["設計一次エネルギー消費量（照明）[MJ]"] = resultdata_L["E_lighting"]
                calc_reuslt["基準一次エネルギー消費量（照明）[MJ]"] = resultdata_L["Es_lighting"]
                calc_reuslt["BEI_L"] = math.ceil(resultdata_L["BEI_L"] * 100) / 100

            else:
                resultdata_L = {
                    "message": "照明設備はありません。"
                }

        except:
            resultdata_L = {
                "error": "照明設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        resultdata_L = {
            "error": "照明設備の計算は実行されませんでした。"
        }

    # 出力
    with open(inputfile_name_split[0] + "_result_L.json",'w', encoding='utf-8') as fw:
        json.dump(resultdata_L, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # 給湯設備の計算の実行
    #------------------------------------

    # 実行
    resultdata_HW = {}

    if exec_calculation:

        try:
            if inputdata["HotwaterRoom"]:   # HotwaterRoom が 空 でなければ
            
                resultdata_HW = hotwatersupply.calc_energy(inputdata, DEBUG = False, output_dir=inputfile_name_split[0])
        
                # CGSの計算に必要となる変数
                resultJson_for_CGS["HW"] = resultdata_HW["for_CGS"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += resultdata_HW["設計一次エネルギー消費量[MJ/年]"]
                energy_consumption_standard += resultdata_HW["基準一次エネルギー消費量[MJ/年]"]
                calc_reuslt["設計一次エネルギー消費量（給湯）[MJ]"] = resultdata_HW["設計一次エネルギー消費量[MJ/年]"]
                calc_reuslt["基準一次エネルギー消費量（給湯）[MJ]"] = resultdata_HW["基準一次エネルギー消費量[MJ/年]"]
                calc_reuslt["BEI_HW"] = math.ceil(resultdata_HW["BEI/HW"] * 100) / 100
            
            else:
                resultdata_HW = {
                    "message": "給湯設備はありません。"
                }

        except:
            resultdata_HW = {
                "error": "給湯設備の計算時に予期せぬエラーが発生しました。"
            }

    else:
        resultdata_HW = {
            "error": "給湯設備の計算は実行されませんでした。"
        }

    # 出力
    with open(inputfile_name_split[0] + "_result_HW.json",'w', encoding='utf-8') as fw:
        json.dump(resultdata_HW, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # 昇降機の計算の実行
    #------------------------------------

    # 実行
    resultdata_EV = {}
    if exec_calculation:

        try:
            if inputdata["Elevators"]:   # Elevators が 空 でなければ

                resultdata_EV = elevator.calc_energy(inputdata, DEBUG = False, output_dir=inputfile_name_split[0])

                # CGSの計算に必要となる変数
                resultJson_for_CGS["EV"] = resultdata_EV["for_CGS"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design += resultdata_EV["E_elevator"]
                energy_consumption_standard += resultdata_EV["Es_elevator"]
                calc_reuslt["設計一次エネルギー消費量（昇降機）[MJ]"] = resultdata_EV["E_elevator"]
                calc_reuslt["基準一次エネルギー消費量（昇降機）[MJ]"] = resultdata_EV["Es_elevator"]
                calc_reuslt["BEI_EV"] = math.ceil(resultdata_EV["BEI_EV"] * 100) / 100

            else:
                resultdata_EV = {
                    "message": "昇降機はありません。"
                }

        except:
            resultdata_EV = {
                "error": "昇降機の計算時に予期せぬエラーが発生しました。"
            }

    else:
        resultdata_EV = {
            "error": "昇降機の計算は実行されませんでした。"
        }

    # 出力
    with open(inputfile_name_split[0] + "_result_EV.json",'w', encoding='utf-8') as fw:
        json.dump(resultdata_EV, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # 太陽光発電の計算の実行
    #------------------------------------

    # 実行
    resultdata_PV = {}
    if exec_calculation:

        try:
            if inputdata["PhotovoltaicSystems"]:   # PhotovoltaicSystems が 空 でなければ

                resultdata_PV = photovoltaic.calc_energy(inputdata, DEBUG = False, output_dir=inputfile_name_split[0])

                # CGSの計算に必要となる変数
                resultJson_for_CGS["PV"] = resultdata_PV["for_CGS"]

                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design -= resultdata_PV["E_photovoltaic"]
                calc_reuslt["創エネルギー量（太陽光）[MJ]"] = resultdata_PV["E_photovoltaic"]

            else:
                resultdata_PV = {
                    "message": "太陽光発電設備はありません。"
                }
        except:
            resultdata_PV = {
                "error": "太陽光発電設備の計算時に予期せぬエラーが発生しました。"
            }
    else:
        resultdata_PV = {
            "error": "太陽光発電設備の計算は実行されませんでした。"
        }

    # 出力
    with open(inputfile_name_split[0] + "_result_PV.json",'w', encoding='utf-8') as fw:
        json.dump(resultdata_PV, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # その他の計算の実行
    #------------------------------------

    # 実行
    resultdata_OT = {}
    if exec_calculation:

        try:
            if inputdata["Rooms"]:   # Rooms が 空 でなければ

                resultdata_OT = other_energy.calc_energy(inputdata, DEBUG = False, output_dir=inputfile_name_split[0])

                # CGSの計算に必要となる変数
                resultJson_for_CGS["OT"] = resultdata_OT["for_CGS"]
                calc_reuslt["その他一次エネルギー消費量[MJ]"] = resultdata_OT["E_other"]

            else:
                resultdata_OT = {
                    "message": "その他一次エネルギー消費量は0です。"
                }
        except:
            resultdata_OT = {
                "error": "その他一次エネルギー消費量の計算時に予期せぬエラーが発生しました。"
            }
    else:
        resultdata_OT = {
            "error": "その他一次エネルギー消費量の計算は実行されませんでした。"
        }

    # 出力
    with open(inputfile_name_split[0] + "_result_Other.json",'w', encoding='utf-8') as fw:
        json.dump(resultdata_OT, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # コジェネの計算の実行
    #------------------------------------

    # 実行
    resultdata_CGS = {}
    if exec_calculation:

        try:
            if inputdata["CogenerationSystems"]:   # CogenerationSystems が 空 でなければ
                resultdata_CGS = cogeneration.calc_energy(inputdata, resultJson_for_CGS, DEBUG = False, output_dir=inputfile_name_split[0])
                # 設計一次エネ・基準一次エネに追加
                energy_consumption_design -= resultdata_CGS["年間一次エネルギー削減量"] * 1000
                calc_reuslt["創エネルギー量（コジェネ）[MJ]"] = resultdata_CGS["年間一次エネルギー削減量"] * 1000

            else:
                resultdata_CGS = {
                    "message": "コージェネレーション設備はありません。"
                }
        except:
            resultdatresultdata_CGSa_OT = {
                "error": "コージェネレーション設備の計算時に予期せぬエラーが発生しました。"
            }
    else:
        resultdata_CGS = {
            "error": "コージェネレーション設備の計算は実行されませんでした。"
        }

    # 出力
    with open(inputfile_name_split[0] + "_result_CGS.json",'w', encoding='utf-8') as fw:
        json.dump(resultdata_CGS, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # BEIの計算
    #------------------------------------

    if energy_consumption_standard  != 0:

        calc_reuslt["設計一次エネルギー消費量（その他除き）[MJ]"] = energy_consumption_design
        calc_reuslt["基準一次エネルギー消費量（その他除き）[MJ]"] = energy_consumption_standard

        calc_reuslt["BEI"] = energy_consumption_design / energy_consumption_standard 
        calc_reuslt["BEI"] = math.ceil(calc_reuslt["BEI"] * 100) / 100

        calc_reuslt["設計一次エネルギー消費量（再エネ、その他除き）[MJ]"] = energy_consumption_design + calc_reuslt["創エネルギー量（太陽光）[MJ]"]

        calc_reuslt["BEI（再エネ除き）"] = calc_reuslt["設計一次エネルギー消費量（再エネ、その他除き）[MJ]"] / calc_reuslt["基準一次エネルギー消費量（その他除き）[MJ]"] 
        calc_reuslt["BEI（再エネ除き）"] = math.ceil(calc_reuslt["BEI（再エネ除き）"] * 100) / 100

        # 設計一次エネ・基準一次エネにその他を追加
        if "E_other" in resultdata_OT:
            calc_reuslt["設計一次エネルギー消費量[MJ]"] = energy_consumption_design + resultdata_OT["E_other"]
            calc_reuslt["基準一次エネルギー消費量[MJ]"] = energy_consumption_standard + resultdata_OT["E_other"]


    #------------------------------------
    # 計算結果ファイルの出力
    #------------------------------------

    with open(inputfile_name_split[0] + "_result.json",'w', encoding='utf-8') as fw:
        json.dump(calc_reuslt, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # バリデーションファイルの出力
    #------------------------------------

    with open(inputfile_name_split[0] + "_validation.json",'w', encoding='utf-8') as fw:
        json.dump(validation, fw, indent=4, ensure_ascii=False, cls = MyEncoder)


    #------------------------------------
    # zipファイルの作成
    #------------------------------------

    with zipfile.ZipFile(inputfile_name_split[0]+".zip", 'w', compression=zipfile.ZIP_DEFLATED) as new_zip:

        files_to_add = [
            (inputfile_name_split[0] + "_input.json", 'builelib_input.json'),
            (inputfile_name_split[0] + "_validation.json", 'builelib_validation.json'),
            (inputfile_name_split[0] + "_result.json", 'builelib_result.json'),
            (inputfile_name_split[0] + "_result_AC.json", 'builelib_result_AC.json'),
            (inputfile_name_split[0] + "_result_V.json", 'builelib_result_V.json'),
            (inputfile_name_split[0] + "_result_L.json", 'builelib_result_L.json'),
            (inputfile_name_split[0] + "_result_HW.json", 'builelib_result_HW.json'),
            (inputfile_name_split[0] + "_result_EV.json", 'builelib_result_EV.json'),
            (inputfile_name_split[0] + "_result_PV.json", 'builelib_result_PV.json'),
            (inputfile_name_split[0] + "_result_CGS.json", 'builelib_result_CGS.json'),
            (inputfile_name_split[0] + "_result_Other.json", 'builelib_result_Other.json'),
            (inputfile_name_split[0] + "_result_AC_ROOM_daily.csv", 'builelib_result_AC_ROOM_daily.csv'),
            (inputfile_name_split[0] + "_result_AC_Qroom.csv", 'builelib_result_AC_Qroom.csv'),
            (inputfile_name_split[0] + "_result_AC_AHU_daily.csv", 'builelib_result_AC_AHU_daily.csv'),
            (inputfile_name_split[0] + "_result_AC_AHU.csv", 'builelib_result_AC_AHU.csv'),
            (inputfile_name_split[0] + "_result_AC_PUMP_daily.csv", 'builelib_result_AC_PUMP_daily.csv'),
            (inputfile_name_split[0] + "_result_AC_PUMP.csv", 'builelib_result_AC_PUMP.csv'),
            (inputfile_name_split[0] + "_result_AC_REF_daily.csv", 'builelib_result_AC_REF_daily.csv'),
            (inputfile_name_split[0] + "_result_AC_REF.csv", 'builelib_result_AC_REF.csv'),
            (inputfile_name_split[0] + "_result_AC_Energy_daily.csv", 'builelib_result_AC_Energy_daily.csv'),
            (inputfile_name_split[0] + "_result_V_Energy_daily.csv", 'builelib_result_V_Energy_daily.csv'),
            (inputfile_name_split[0] + "_result_L_Energy_daily.csv", 'builelib_result_L_Energy_daily.csv'),
            (inputfile_name_split[0] + "_result_L_room.csv", 'builelib_result_L_room.csv'),
            (inputfile_name_split[0] + "_result_HW_Energy_daily.csv", 'builelib_result_HW_Energy_daily.csv'),
            (inputfile_name_split[0] + "_result_PV_Energy_daily.csv", 'builelib_result_PV_Energy_daily.csv'),
            (inputfile_name_split[0] + "_result_EV_Energy_daily.csv", 'builelib_result_EV_Energy_daily.csv'),
            (inputfile_name_split[0] + "_result_OT_Energy_daily.csv", 'builelib_result_OT_Energy_daily.csv')
        ]

        for file_path, arcname in files_to_add:
            if os.path.exists(file_path):
                new_zip.write(file_path, arcname=arcname)


    # ファイル削除
    # これを有効にするとブラウザで結果が表示されなくなるので注意
    # os.remove( inputfile_name_split[0] + "_input.json" )
    # os.remove( inputfile_name_split[0] + "_result_AC.json" )
    # os.remove( inputfile_name_split[0] + "_result_V.json" )
    # os.remove( inputfile_name_split[0] + "_result_L.json" )
    # os.remove( inputfile_name_split[0] + "_result_HW.json" )
    # os.remove( inputfile_name_split[0] + "_result_EV.json" )
    # os.remove( inputfile_name_split[0] + "_result_PV.json" )
    # os.remove( inputfile_name_split[0] + "_result_CGS.json" )
    # os.remove( inputfile_name_split[0] + "_result_Other.json" )


def builelib_run_AC(inputfile_name):
    """空調のみ実行するプログラム（計算過程を全て出力）
    Args:
        inputfile_name (str): 入力ファイルの名称
    """

    inputfile_name   = str(inputfile_name)     # 入力ファイルの名称
    inputfile_name_split = os.path.splitext(inputfile_name)  
    
    # jsonファイルの生成
    inputdata, validation = make_jsondata_from_Ver2_sheet(inputfile_name)

    print(validation)

    # 計算の実行（デバッグモードON）
    resultJson_webpro = airconditioning_webpro.calc_energy(inputdata, debug=True)

    print( f'BEI/AC: {resultJson_webpro["BEI/AC"]}')        
    print( f'設計一次エネルギー消費量 全体: {resultJson_webpro["設計一次エネルギー消費量[MJ/年]"]}')
    print( f'設計一次エネルギー消費量 空調ファン: {resultJson_webpro["年間エネルギー消費量"]["空調機群ファン[GJ]"]}')
    print( f'設計一次エネルギー消費量 空調全熱交換器: {resultJson_webpro["年間エネルギー消費量"]["空調機群全熱交換器[GJ]"]}')
    print( f'設計一次エネルギー消費量 二次ポンプ: {resultJson_webpro["年間エネルギー消費量"]["二次ポンプ群[GJ]"]}')
    print( f'設計一次エネルギー消費量 熱源主機: {resultJson_webpro["年間エネルギー消費量"]["熱源群熱源主機[GJ]"]}')
    print( f'設計一次エネルギー消費量 熱源補機: {resultJson_webpro["年間エネルギー消費量"]["熱源群熱源補機[GJ]"]}')
    print( f'設計一次エネルギー消費量 一次ポンプ: {resultJson_webpro["年間エネルギー消費量"]["熱源群一次ポンプ[GJ]"]}')
    print( f'設計一次エネルギー消費量 冷却塔ファン: {resultJson_webpro["年間エネルギー消費量"]["熱源群冷却塔ファン[GJ]"]}')
    print( f'設計一次エネルギー消費量 冷却水ポンプ: {resultJson_webpro["年間エネルギー消費量"]["熱源群冷却水ポンプ[GJ]"]}')

    # 結果の出力
    with open(inputfile_name_split[0] + "_input.json",'w', encoding='utf-8') as fw:
        json.dump(inputdata, fw, indent=4, ensure_ascii=False, cls = MyEncoder)
    with open(inputfile_name_split[0] + "_resultJson_AC.json",'w', encoding='utf-8') as fw:
        json.dump(resultJson_webpro, fw, indent=4, ensure_ascii=False, cls = MyEncoder)

if __name__ == '__main__':
    
    # file_name = "/usr/src/data/WEBPRO_inputSheet_sample.xlsm"
    file_name = "./sample/Builelib_inputSheet_sample_002.xlsx"

    builelib_run(True, file_name)
    # builelib_run_AC(file_name)
