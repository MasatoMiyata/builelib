# builelib_run.py
# -----------------------------------------------------------------------------
# builelibをコマンドラインで実行するファイル
# -----------------------------------------------------------------------------

import json
import numpy as np
import os
import zipfile
import math
import sys
import time

from builelib.make_inputdata import make_jsondata_from_Ver2_sheet
from builelib import (
    airconditioning_zebopt,
    climate,
    ventilation,
    lighting,
    hotwatersupply,
    elevator,
    photovoltaic,
    other_energy,
    cogeneration,
)

start_time = time.time()

# コマンドライン引数から入力ファイル名を取得
if len(sys.argv) > 1:
    inputfile_name = sys.argv[1]  # ユーザーが指定したファイル名
else:
    inputfile_name = "./sample/WEBPRO_inputSheet_sample.xlsm"  # デフォルトのファイル名

inputdata, validation = make_jsondata_from_Ver2_sheet(inputfile_name)


# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/builelib/database/"
# 流量制御
with open(database_directory + "FLOWCONTROL.json", "r", encoding="utf-8") as f:
    FLOWCONTROL = json.load(f)
# 熱源機器特性
with open(
    database_directory + "HeatSourcePerformance.json", "r", encoding="utf-8"
) as f:
    HeatSourcePerformance = json.load(f)
# 地域別データの読み込み
with open(database_directory + "AREA.json", "r", encoding="utf-8") as f:
    Area = json.load(f)
# 空調運転モード
with open(database_directory + "ACoperationMode.json", "r", encoding="utf-8") as f:
    ACoperationMode = json.load(f)
# 標準入力法建材データの読み込み
with open(
    database_directory + "HeatThermalConductivity.json", "r", encoding="utf-8"
) as f:
    HeatThermalConductivity = json.load(f)
# モデル建物法建材データの読み込み
with open(
    database_directory + "HeatThermalConductivity_model.json", "r", encoding="utf-8"
) as f:
    HeatThermalConductivity_model = json.load(f)
# 地中熱オープンループの地盤特性の読み込み
with open(database_directory + "AC_gshp_openloop.json", "r", encoding="utf-8") as f:
    AC_gshp_openloop = json.load(f)

# 気象データファイルの保存場所
climatedata_directory = (
    os.path.dirname(os.path.abspath(__file__)) + "/builelib/climatedata/"
)
ClimateData = climate.readHaspClimateData(
    climatedata_directory
    + "C1_"
    + Area[inputdata["Building"]["Region"] + "地域"]["気象データファイル名"]
)

# データ定義セクション
calc_reuslt = {
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
resultJson_for_CGS = {
    "AC": {},
    "V": {},
    "L": {},
    "HW": {},
    "EV": {},
    "PV": {},
    "OT": {},
}

# 結果いれるリスト
resultdata_AC = {}
resultdata_V = {}
resultdata_L = {}
resultdata_HW = {}
resultdata_EV = {}
resultdata_PV = {}
resultdata_OT = {}
resultdata_CGS = {}

end_time_data = time.time()
data_time = end_time_data - start_time
print(f"データロードセクション実行時間: {data_time:.2f} 秒")

# 空調負荷計算セクション---------------------------------------------------------
resultdata_AC = airconditioning_zebopt.calc_energy(
    inputdata,
    FLOWCONTROL,
    HeatSourcePerformance,
    Area,
    ClimateData,
    ACoperationMode,
    HeatThermalConductivity,
    HeatThermalConductivity_model,
    AC_gshp_openloop,
)
# resultdata_AC = airconditioning_webpro.calc_energy(inputdata, debug=False)

end_time_ac = time.time()
ac_time = end_time_ac - end_time_data
print(f"空調負荷計算実行時間: {ac_time:.2f} 秒")

# 機械換気計算セクション---------------------------------------------------------
resultdata_V = ventilation.calc_energy(inputdata, DEBUG=False)

end_time_v = time.time()
v_time = end_time_v - end_time_ac
print(f"機械換気計算実行時間: {v_time:.2f} 秒")

# 照明設備計算セクション---------------------------------------------------------
resultdata_L = lighting.calc_energy(inputdata, DEBUG=False)

end_time_l = time.time()
l_time = end_time_l - end_time_v
print(f"照明計算実行時間: {l_time:.2f} 秒")

# 給湯設備計算セクション---------------------------------------------------------
resultdata_HW = hotwatersupply.calc_energy(inputdata, DEBUG=False)

end_time_hw = time.time()
hw_time = end_time_hw - end_time_l
print(f"給湯計算実行時間: {hw_time:.2f} 秒")

# 昇降設備計算セクション---------------------------------------------------------
resultdata_EV = elevator.calc_energy(inputdata, DEBUG=False)

end_time_ev = time.time()
ev_time = end_time_ev - end_time_hw
print(f"昇降計算実行時間: {ev_time:.2f} 秒")

# 太陽光発電計算セクション---------------------------------------------------------
resultdata_PV = photovoltaic.calc_energy(inputdata, DEBUG=False)

end_time_pv = time.time()
pv_time = end_time_pv - end_time_ev
print(f"太陽光発電計算実行時間: {pv_time:.2f} 秒")

# その他計算セクション---------------------------------------------------------
resultdata_OT = other_energy.calc_energy(inputdata, DEBUG=False)

end_time_ot = time.time()
ot_time = end_time_ot - end_time_pv
print(f"その他計算実行時間: {ot_time:.2f} 秒")

# コジェネ計算セクション---------------------------------------------------------
resultJson_for_CGS["AC"] = resultdata_AC["for_CGS"]
resultJson_for_CGS["V"] = resultdata_V["for_CGS"]
resultJson_for_CGS["L"] = resultdata_L["for_CGS"]
resultJson_for_CGS["HW"] = resultdata_HW["for_CGS"]
resultJson_for_CGS["EV"] = resultdata_EV["for_CGS"]
resultJson_for_CGS["PV"] = resultdata_PV["for_CGS"]
resultJson_for_CGS["OT"] = resultdata_OT["for_CGS"]

resultdata_CGS = cogeneration.calc_energy(inputdata, resultJson_for_CGS, DEBUG=False)

end_time_cgs = time.time()
cgs_time = end_time_cgs - end_time_ot
print(f"コジェネ計算実行時間: {cgs_time:.2f} 秒")

# BEI計算セクション---------------------------------------------------------
# 設計一次エネルギー消費量[MJ]
energy_consumption_design = (
    resultdata_AC["設計一次エネルギー消費量[MJ/年]"]
    + resultdata_V["設計一次エネルギー消費量[MJ/年]"]
    + resultdata_L["E_lighting"]
    + resultdata_HW["設計一次エネルギー消費量[MJ/年]"]
    + resultdata_EV["E_elevator"]
    - resultdata_PV["E_photovoltaic"]
    - resultdata_CGS["年間一次エネルギー削減量"] * 1000
)
# 基準一次エネルギー消費量[MJ]
energy_consumption_standard = (
    resultdata_AC["基準一次エネルギー消費量[MJ/年]"]
    + resultdata_V["基準一次エネルギー消費量[MJ/年]"]
    + resultdata_L["Es_lighting"]
    + resultdata_HW["基準一次エネルギー消費量[MJ/年]"]
    + resultdata_EV["Es_elevator"]
)

BEI = energy_consumption_design / energy_consumption_standard
AC_ratio = (
    resultdata_AC["設計一次エネルギー消費量[MJ/年]"] / energy_consumption_standard
)
V_ratio = resultdata_V["設計一次エネルギー消費量[MJ/年]"] / energy_consumption_standard
L_ratio = resultdata_L["E_lighting"] / energy_consumption_standard
HW_ratio = (
    resultdata_HW["設計一次エネルギー消費量[MJ/年]"] / energy_consumption_standard
)
EV_ratio = resultdata_EV["E_elevator"] / energy_consumption_standard
PV_ratio = resultdata_PV["E_photovoltaic"] / energy_consumption_standard
CGS_ratio = (
    resultdata_CGS["年間一次エネルギー削減量"] * 1000 / energy_consumption_standard
)

print(f"BEI: {BEI:.3f}")
print(f"fraction_AC: {AC_ratio:.3f}")
print(f"fraction_V: {V_ratio:.3f}")
print(f"fraction_L: {L_ratio:.3f}")
print(f"fraction_HW: {HW_ratio:.3f}")
print(f"fraction_EV: {EV_ratio:.3f}")
print(f"fraction_PV: {PV_ratio:.3f}")
print(f"fraction_CGS: {CGS_ratio:.3f}")

end_time = time.time() - start_time
print(f"総実行時間: {end_time:.2f} 秒")
