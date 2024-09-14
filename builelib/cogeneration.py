import json
import os
import sys

import numpy as np

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from . import commons as bc

# データベースファイルの保存場所
database_directory = os.path.dirname(os.path.abspath(__file__)) + "/database/"


def perfCURVE(fcgs_e_rated, fcgs_e_75, fcgs_e_50, fcgs_hr_rated, fcgs_hr_75, fcgs_hr_50):
    """    
    Input
    fcgs_e_rated  : CGSの定格発電効率(低位発熱量基準)
    fcgs_e_75     : CGSの負荷率0.75時発電効率(低位発熱量基準)
    fcgs_e_50     : CGSの負荷率0.50時発電効率(低位発熱量基準)
    fcgs_hr_rated : CGSの定格排熱効率(低位発熱量基準)
    fcgs_hr_75    : CGSの負荷率0.75時排熱効率(低位発熱量基準)
    fcgs_hr_50    : CGSの負荷率0.50時排熱効率(低位発熱量基準)
    
    Output
    fe2	 : CGSの発電効率特性式の2次式の係数項
    fe1	 : CGSの発電効率特性式の1次式の係数項
    fe0	 : CGSの発電効率特性式の定数項
    fhr2 : CGSの排熱効率特性式の2次式の係数項
    fhr1 : CGSの排熱効率特性式の1次式の係数項
    fhr0 : CGSの排熱効率特性式の定数項
    """

    fe2 = 8 * (fcgs_e_rated - 2 * fcgs_e_75 + fcgs_e_50)
    fe1 = -2 * (5 * fcgs_e_rated - 12 * fcgs_e_75 + 7 * fcgs_e_50)
    fe0 = 3 * fcgs_e_rated - 8 * fcgs_e_75 + 6 * fcgs_e_50

    fhr2 = 8 * (fcgs_hr_rated - 2 * fcgs_hr_75 + fcgs_hr_50)
    fhr1 = -2 * (5 * fcgs_hr_rated - 12 * fcgs_hr_75 + 7 * fcgs_hr_50)
    fhr0 = 3 * fcgs_hr_rated - 8 * fcgs_hr_75 + 6 * fcgs_hr_50

    return fe2, fe1, fe0, fhr2, fhr1, fhr0


def calc_energy(input_data, result_json_for_cgs, DEBUG=False):
    result_json = {}

    # CGS系統名の取得
    cgs_name = None
    if len(input_data["cogeneration_systems"]) != 1:
        raise Exception("計算可能なCGS系統は1系統のみです。")
    for cgs_name_list in input_data["cogeneration_systems"]:
        cgs_name = cgs_name_list

    # CGSの発電機容量	kW
    Ecgs_rated = input_data["cogeneration_systems"][cgs_name]["rated_capacity"]
    # CGS設置台数	台
    Ncgs = input_data["cogeneration_systems"][cgs_name]["number"]
    # CGSの定格発電効率(低位発熱量基準)	無次元
    fcgs_e_rated = input_data["cogeneration_systems"][cgs_name]["power_generation_efficiency_100"]
    # CGSの負荷率0.75時発電効率(低位発熱量基準)	無次元
    fcgs_e_75 = input_data["cogeneration_systems"][cgs_name]["power_generation_efficiency_75"]
    # CGSの負荷率0.50時発電効率(低位発熱量基準)	無次元
    fcgs_e_50 = input_data["cogeneration_systems"][cgs_name]["power_generation_efficiency_50"]
    # CGSの定格排熱効率(低位発熱量基準)	無次元
    fcgs_hr_rated = input_data["cogeneration_systems"][cgs_name]["heat_generation_efficiency_100"]
    # CGSの負荷率0.75時排熱効率(低位発熱量基準)	無次元
    fcgs_hr_75 = input_data["cogeneration_systems"][cgs_name]["heat_generation_efficiency_75"]
    # CGSの負荷率0.50時排熱効率(低位発熱量基準)	無次元
    fcgs_hr_50 = input_data["cogeneration_systems"][cgs_name]["heat_generation_efficiency_50"]
    # 排熱利用優先順位(冷熱源)　※1	無次元
    npri_hr_c = input_data["cogeneration_systems"][cgs_name]["heat_recovery_priority_cooling"]
    # 排熱利用優先順位(温熱源) 　※1	無次元
    npri_hr_h = input_data["cogeneration_systems"][cgs_name]["heat_recovery_priority_heating"]
    # 排熱利用優先順位(給湯) 　※1	無次元
    npri_hr_w = input_data["cogeneration_systems"][cgs_name]["heat_recovery_priority_hot_water"]
    # CGS24時間運転の有無　※2	-
    C24ope = input_data["cogeneration_systems"][cgs_name]["24hourOperation"]

    ##----------------------------------------------------------------------------------
    ## 解説書附属書 G.10 
    ##----------------------------------------------------------------------------------

    # 日付dにおける空気調和設備の電力消費量	MWh/日
    if result_json_for_cgs["AC"]:
        EAC_total_d = np.array(result_json_for_cgs["AC"]["electric_power_consumption"])
    else:
        EAC_total_d = np.zeros(365)

    # 日付dにおけるCGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の冷熱源としての主機の一次エネルギー消費量	MJ/日
    if result_json_for_cgs["AC"]:
        EAC_ref_c_d = np.array(result_json_for_cgs["AC"]["e_ref_cgsc_abs_day"])
    else:
        EAC_ref_c_d = np.zeros(365)

    # 日付dにおけるCGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の冷熱源としての負荷率 	無次元
    if result_json_for_cgs["AC"]:
        mx_lAC_ref_c_d = np.array(result_json_for_cgs["AC"]["lt_ref_cgs_c_day"])
    else:
        mx_lAC_ref_c_d = np.zeros(365)

    # 日付dにおけるCGSの排熱利用が可能な温熱源群の主機の一次エネルギー消費量	MJ/日
    if result_json_for_cgs["AC"]:
        EAC_ref_h_hr_d = np.array(result_json_for_cgs["AC"]["e_ref_cgsh_day"])
    else:
        EAC_ref_h_hr_d = np.zeros(365)

    # 日付dにおけるCGSの排熱利用が可能な温熱源群の熱源負荷	MJ/日
    if result_json_for_cgs["AC"]:
        qAC_ref_h_hr_d = np.array(result_json_for_cgs["AC"]["q_ref_cgs_h_day"])
    else:
        qAC_ref_h_hr_d = np.zeros(365)

    # 日付dにおける機械換気設備の電力消費量	MWh/日
    if result_json_for_cgs["V"]:
        EV_total_d = np.array(result_json_for_cgs["V"]["Edesign_MWh_day"])
    else:
        EV_total_d = np.zeros(365)

    # 日付dにおける照明設備の電力消費量	MWh/日
    if result_json_for_cgs["L"]:
        EL_total_d = np.array(result_json_for_cgs["L"]["Edesign_MWh_day"])
    else:
        EL_total_d = np.zeros(365)

    # 日付dにおける給湯設備の電力消費量	MWh/日
    if result_json_for_cgs["HW"]:
        EW_total_d = np.array(result_json_for_cgs["HW"]["edesign_mwh_ele_day"])
    else:
        EW_total_d = np.zeros(365)

    # 日付dにおけるCGSの排熱利用が可能な給湯機(系統)の一次エネルギー消費量	MJ/日
    if result_json_for_cgs["HW"]:
        EW_hr_d = np.array(result_json_for_cgs["HW"]["Edesign_MJ_CGS_day"])
    else:
        EW_hr_d = np.zeros(365)

    # 日付dにおけるCGSの排熱利用が可能な給湯機(系統)の給湯負荷	MJ/日
    if result_json_for_cgs["HW"]:
        qW_hr_d = np.array(result_json_for_cgs["HW"]["Q_eqp_CGS_day"])
    else:
        qW_hr_d = np.zeros(365)

    # 日付dにおける昇降機の電力消費量	MWh/日
    if result_json_for_cgs["EV"]:
        EEV_total_d = np.array(result_json_for_cgs["EV"]["Edesign_MWh_day"])
    else:
        EEV_total_d = np.zeros(365)

    # 日付dにおける効率化設備（太陽光発電）の発電量	MWh/日
    if result_json_for_cgs["PV"]:
        EPV_total_d = np.array(result_json_for_cgs["PV"]["Edesign_MWh_day"])
    else:
        EPV_total_d = np.zeros(365)

    # 日付dにおけるその他の電力消費量	MWh/日
    if result_json_for_cgs["OT"]:
        EM_total_d = np.array(result_json_for_cgs["OT"]["Edesign_MWh_day"])
    else:
        EM_total_d = np.zeros(365)

    # 日付dにおけるCGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の運転時間	h/日
    if result_json_for_cgs["AC"]:
        TAC_c_d = np.array(result_json_for_cgs["AC"]["t_ref_cgs_c_day"])
    else:
        TAC_c_d = np.zeros(365)

    # 日付dにおけるCGSの排熱利用が可能な温熱源群の運転時間	h/日
    if result_json_for_cgs["AC"]:
        TAC_h_d = np.array(result_json_for_cgs["AC"]["t_ref_cgs_h_day"])
    else:
        TAC_h_d = np.zeros(365)

    # 排熱投入型吸収式冷温水機jの定格冷却能力	ｋW/台
    if result_json_for_cgs["AC"]:
        qac_link_c_j_rated = result_json_for_cgs["AC"]["qac_link_c_j_rated"]
    else:
        qac_link_c_j_rated = 0

    # 排熱投入型吸収式冷温水機jの主機定格消費エネルギー ｋW/台
    if result_json_for_cgs["AC"]:
        eac_link_c_j_rated = result_json_for_cgs["AC"]["eac_link_c_j_rated"]
    else:
        eac_link_c_j_rated = 0

    if DEBUG:  # pragma: no cover
        print(f" 2 EAC_total_d : {np.sum(EAC_total_d)}")
        print(f" 7 EAC_ref_c_d : {np.sum(EAC_ref_c_d)}")
        print(f" 8 mx_lAC_ref_c_d : {np.sum(mx_lAC_ref_c_d)}")
        print(f" 9 EAC_ref_h_hr_d : {np.sum(EAC_ref_h_hr_d)}")
        print(f"10 qAC_ref_h_hr_d : {np.sum(qAC_ref_h_hr_d)}")
        print(f"11 EV_total_d : {np.sum(EV_total_d)}")
        print(f"12 EL_total_d : {np.sum(EL_total_d)}")
        print(f"13 EW_total_d : {np.sum(EW_total_d)}")
        print(f"14 EW_hr_d : {np.sum(EW_hr_d)}")
        print(f"15 qW_hr_d : {np.sum(qW_hr_d)}")
        print(f"16 EEV_total_d : {np.sum(EEV_total_d)}")
        print(f"17 EPV_total_d : {np.sum(EPV_total_d)}")
        print(f"18 EM_total_d : {np.sum(EM_total_d)}")
        print(f"19 TAC_c_d : {np.sum(TAC_c_d)}")
        print(f"20 TAC_h_d : {np.sum(TAC_h_d)}")
        print(f"qac_link_c_j_rated : {qac_link_c_j_rated}")
        print(f"eac_link_c_j_rated : {eac_link_c_j_rated}")

    ##----------------------------------------------------------------------------------
    ## 解説書 8.1.6 定数
    ##----------------------------------------------------------------------------------

    # 運転判定基準必要電力比率	無次元
    feopeMn = 0.5
    # 運転判定基準必要排熱比率	無次元
    fhopeMn = 0.5
    # CGS補機動力比率	無次元
    fesub_CGS_wc = 0.06  # 冷却塔がある場合
    fesub_CGS_ac = 0.05  # 冷却塔がない場合
    # ガスの高位発熱量に対する低位発熱量の比率	無次元
    flh = 0.90222
    # 電気の一次エネルギー換算係数	MJ/kWh
    fprime_e = 9.76
    # 排熱投入型吸収式冷温水機の排熱利用時のCOP	無次元
    fCOP_link_hr = 0.75
    # CGSによる電力負荷の最大負担率	無次元
    felmax = 0.95
    # CGSの標準稼働時間 h/日
    Tstn = 14
    # 発電効率補正
    fcgs_e_cor = 0.99
    # 排熱の熱損失率の補正
    fhr_loss = 0.97

    # 排熱を給湯のみに利用する場合のCGSの最小稼働時間 [時間/日] (2020/06/13追加 for Ver3)
    Tstmin_w = 10

    ratio_area_weighted_schedule_AC = result_json_for_cgs["OT"]["ratio_area_weighted_schedule_AC"]
    ratio_area_weighted_schedule_LT = result_json_for_cgs["OT"]["ratio_area_weighted_schedule_LT"]
    ratio_area_weighted_schedule_OA = result_json_for_cgs["OT"]["ratio_area_weighted_schedule_OA"]

    Ee_total_hour = np.zeros((365, 24))

    for dd in range(0, 365):
        for hh in range(0, 24):
            Ee_total_hour[dd][hh] = EAC_total_d[dd] * ratio_area_weighted_schedule_AC[dd][hh] \
                                    + EV_total_d[dd] / 24 \
                                    + EL_total_d[dd] * ratio_area_weighted_schedule_LT[dd][hh] \
                                    + EW_total_d[dd] / 24 \
                                    + EEV_total_d[dd] / 24 \
                                    + EM_total_d[dd] * ratio_area_weighted_schedule_OA[dd][hh]

    feopehi = np.ones(365)

    for dd in range(0, 365):

        # 運転時間 7時から20時までの14時間）
        Eday = np.sum(Ee_total_hour[dd][6:20]) - EPV_total_d[dd]
        Enight = np.sum(Ee_total_hour[dd][0:6]) + np.sum(Ee_total_hour[dd][20:25])

        if Eday < 0:
            feopehi[dd] = 1
        elif Enight == 0:
            feopehi[dd] = 100
        else:
            feopehi[dd] = Eday / Enight

        # 上限・下限
        if feopehi[dd] < 1:
            feopehi[dd] = 1
        elif feopehi[dd] > 100:
            feopehi[dd] = 100

    ##----------------------------------------------------------------------------------
    ## 解説書 8.2 CGS特性式各係数
    ##----------------------------------------------------------------------------------

    fe2, fe1, fe0, fhr2, fhr1, fhr0 = \
        perfCURVE(fcgs_e_rated, fcgs_e_75, fcgs_e_50, fcgs_hr_rated, fcgs_hr_75, fcgs_hr_50)

    ##----------------------------------------------------------------------------------
    ## 解説書 8.3 最大稼働時間
    ##----------------------------------------------------------------------------------

    if C24ope == '有':
        T_ST = 24
    elif C24ope == '無':
        T_ST = Tstn
    else:
        raise Exception("CGS24時間運転の有無　の入力内容が不正です")

    ##----------------------------------------------------------------------------------
    ## 解説書 8.4 電力負荷
    ##----------------------------------------------------------------------------------

    # Ee_total_d : 日付dおける建物の電力消費量 [kWh/day]   
    Ee_total_d = (EAC_total_d + EV_total_d + EL_total_d + EW_total_d + EEV_total_d + EM_total_d - EPV_total_d) * 1000

    ##----------------------------------------------------------------------------------
    ## 解説書 8.5 排熱投入型温水吸収冷温水機の排熱利用可能率
    ##----------------------------------------------------------------------------------

    # flink_d : 日付dにおける排熱投入型吸収式冷温水機の排熱利用可能率

    flink_rated_b = 0.15  # 排熱投入型吸収式冷温水機の定格運転時の排熱投入可能率 [-]
    flink_min_b = 0.30  # 排熱投入型吸収式冷温水機が排熱のみで運転できる最大負荷率 [-]
    flink_down = 0.125  # 排熱温度による排熱投入可能率の低下率 [-]

    flink_rated = flink_rated_b * (1 - flink_down)
    flink_min = flink_min_b - (flink_rated_b - flink_rated)

    mx = np.zeros(365)
    flink_d = np.zeros(365)

    for dd in range(0, 365):

        mx[dd] = mx_lAC_ref_c_d[dd]

        if mx[dd] < flink_min:

            flink_d[dd] = 1.0

        else:

            k = (flink_rated - flink_min) / (1 - flink_min)
            flink_d[dd] = 1 - ((mx[dd] - (k * mx[dd] + flink_rated - k)) / mx[dd])

    ##----------------------------------------------------------------------------------
    ## 解説書 8.6 冷熱源排熱負荷
    ##----------------------------------------------------------------------------------
    # QAC_ref_c_hr_d : 日付dにおけるCGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の冷熱源としての排熱負荷
    # EAC_ref_c_hr_d : 日付dにおけるCGSの排熱利用が可能な排熱投入型吸収式冷温水機(系統)の冷熱源としての主機の一次エネルギー消費量のうち排熱による削減可能量

    if npri_hr_c == None:
        QAC_ref_c_hr_d = np.zeros(365)
        EAC_ref_c_hr_d = np.zeros(365)
    else:
        # ゼロ除算が発生した場合、0とする。
        if eac_link_c_j_rated == 0 or fCOP_link_hr == 0:
            QAC_ref_c_hr_d = 0

        else:
            QAC_ref_c_hr_d = np.nan_to_num(
                EAC_ref_c_d * (np.sum(qac_link_c_j_rated) / np.sum(eac_link_c_j_rated)) * flink_d / fCOP_link_hr)
        
        EAC_ref_c_hr_d = EAC_ref_c_d * flink_d

    ##----------------------------------------------------------------------------------
    ## 解説書 8.7 CGS系統熱負荷
    ##----------------------------------------------------------------------------------
    # qhr_total_d : 日付dにおけるCGS排熱系統の熱負荷

    qhr_ac_c_d = np.zeros(365)  # 日付dにおけるCGS排熱利用が可能な排熱投入型吸収式冷温水器（系統）の排熱負荷 MJ/day
    qhr_ac_h_d = np.zeros(365)  # 日付dにおけるCGS排熱利用が可能な温熱源の排熱負荷 MJ/day
    qhr_total_d = np.zeros(365)  # 日付dにおけるCGS排熱系統の熱負荷 MJ/day

    for dd in range(0, 365):
        if TAC_c_d[dd] > T_ST:
            qhr_ac_c_d[dd] = QAC_ref_c_hr_d[dd] * T_ST / TAC_c_d[dd]
        else:
            qhr_ac_c_d[dd] = QAC_ref_c_hr_d[dd]

        if TAC_h_d[dd] > T_ST:
            qhr_ac_h_d[dd] = qAC_ref_h_hr_d[dd] * T_ST / TAC_h_d[dd]
        else:
            qhr_ac_h_d[dd] = qAC_ref_h_hr_d[dd]

        qhr_total_d[dd] = qhr_ac_c_d[dd] + qhr_ac_h_d[dd] + qW_hr_d[dd]

    ##----------------------------------------------------------------------------------
    ## 解説書 8.8 一日の電力消費量に占める運用時間帯の電力消費量の比率
    ##----------------------------------------------------------------------------------
    # feope_R : 一日の電力消費量に占める運用時間帯の電力消費量の比率

    feope_R = (feopehi * T_ST) / (feopehi * T_ST + (24 - T_ST))

    ##----------------------------------------------------------------------------------
    ## 解説書 8.9 CGS運転時間
    ##----------------------------------------------------------------------------------
    # Tcgs_d : 日付dにおけるCGSの稼働時間 [hour/日]

    Tcgs_d = np.zeros(365)

    # 補機動力比率
    if Ecgs_rated > 50:
        fesub_CGS = fesub_CGS_wc  # 0.06
    else:
        fesub_CGS = fesub_CGS_ac  # 0.05

    for dd in range(0, 365):

        # a*bで電力基準運転時間
        a = qhr_total_d[dd] / (Ecgs_rated * 3.6 * fhopeMn)
        b = fcgs_e_rated / fcgs_hr_rated  # 仕様書では fcgs,h,ratedとなっている。

        # c/dで排熱基準運転時間
        c = Ee_total_d[dd] * feope_R[dd] * (1 + fesub_CGS)
        d = Ecgs_rated * feopeMn

        if npri_hr_c == None and npri_hr_h == None:  # 給湯のみ排熱利用がされる場合（2020/06/13追加）

            if (a * b >= T_ST) and (c / d >= T_ST):

                Tcgs_d[dd] = T_ST

            elif (a * b >= Tstmin_w) and (c / d >= Tstmin_w):

                Tcgs_d[dd] = Tstmin_w

            else:

                Tcgs_d[dd] = 0


        elif TAC_c_d[dd] >= TAC_h_d[dd]:

            if (a * b >= T_ST) and (c / d >= T_ST):

                Tcgs_d[dd] = T_ST

            elif (a * b >= TAC_c_d[dd]) and (c / d >= TAC_c_d[dd]):

                Tcgs_d[dd] = TAC_c_d[dd]

            else:

                Tcgs_d[dd] = 0


        elif TAC_c_d[dd] < TAC_h_d[dd]:

            if (a * b >= T_ST) and (c / d >= T_ST):

                Tcgs_d[dd] = T_ST

            elif (a * b >= TAC_h_d[dd]) and (c / d >= TAC_h_d[dd]):

                Tcgs_d[dd] = TAC_h_d[dd]

            else:

                Tcgs_d[dd] = 0

    ##----------------------------------------------------------------------------------
    ## 解説書 8.10 CGS運転時間における負荷
    ##----------------------------------------------------------------------------------

    Ee_total_on_d = Ee_total_d * feope_R * Tcgs_d / T_ST
    EW_hr_on_d = EW_hr_d
    qW_hr_on_d = qW_hr_d

    EAC_ref_c_hr_on_d = np.zeros(365)
    EAC_ref_h_hr_on_d = np.zeros(365)
    qAC_ref_c_hr_on_d = np.zeros(365)
    qAC_ref_h_hr_on_d = np.zeros(365)
    qtotal_hr_on_d = np.zeros(365)

    for dd in range(0, 365):

        if TAC_c_d[dd] <= Tcgs_d[dd]:
            EAC_ref_c_hr_on_d[dd] = EAC_ref_c_hr_d[dd]
            qAC_ref_c_hr_on_d[dd] = QAC_ref_c_hr_d[dd]
        else:
            EAC_ref_c_hr_on_d[dd] = EAC_ref_c_hr_d[dd] * Tcgs_d[dd] / TAC_c_d[dd]
            qAC_ref_c_hr_on_d[dd] = QAC_ref_c_hr_d[dd] * Tcgs_d[dd] / TAC_c_d[dd]

        if TAC_h_d[dd] <= Tcgs_d[dd]:
            EAC_ref_h_hr_on_d[dd] = EAC_ref_h_hr_d[dd]
            qAC_ref_h_hr_on_d[dd] = qAC_ref_h_hr_d[dd]
        else:
            EAC_ref_h_hr_on_d[dd] = EAC_ref_h_hr_d[dd] * Tcgs_d[dd] / TAC_h_d[dd]
            qAC_ref_h_hr_on_d[dd] = qAC_ref_h_hr_d[dd] * Tcgs_d[dd] / TAC_h_d[dd]

        qtotal_hr_on_d[dd] = qAC_ref_c_hr_on_d[dd] + qAC_ref_h_hr_on_d[dd] + qW_hr_on_d[dd]

    ##----------------------------------------------------------------------------------
    ## 解説書 8.11 CGS最大稼働台数
    ##----------------------------------------------------------------------------------

    Ndash_cgs_on_max_d = np.zeros(365)
    Ncgs_on_max_d = np.zeros(365)
    for dd in range(0, 365):

        if Tcgs_d[dd] == 0:
            Ndash_cgs_on_max_d[dd] = 0
        else:
            Ndash_cgs_on_max_d[dd] = np.ceil(
                qhr_total_d[dd] / (Ecgs_rated * 3.6) * fcgs_e_rated / (fcgs_hr_rated * Tcgs_d[dd]))

        if (Ndash_cgs_on_max_d[dd] >= Ncgs):
            Ncgs_on_max_d[dd] = Ncgs
        else:
            Ncgs_on_max_d[dd] = Ndash_cgs_on_max_d[dd]

    ##----------------------------------------------------------------------------------
    ## 解説書 8.12 発電電力負荷
    ##----------------------------------------------------------------------------------
    # Ee_load_d : 日付dおけるCGSの発電電力負荷 [kWh/day]

    Ee_load_d = Ee_total_on_d * felmax * (1 + fesub_CGS)

    ##----------------------------------------------------------------------------------
    ## 解説書 8.13 運転台数
    ##----------------------------------------------------------------------------------
    # Ndash_cgs_on_d : 日付dおけるCGSの運転台数暫定値 [台]

    Ndash_cgs_on_d = np.zeros(365)
    Ncgs_on_d = np.zeros(365)

    for dd in range(0, 365):

        if Tcgs_d[dd] > 0:

            Ndash_cgs_on_d[dd] = Ee_load_d[dd] / (Ecgs_rated * Tcgs_d[dd])

        elif Tcgs_d[dd] == 0:

            Ndash_cgs_on_d[dd] = 0

        # Ncgs_on_d : 日付dおけるCGSの運転台数 [台]
        if Ndash_cgs_on_d[dd] >= Ncgs_on_max_d[dd]:
            Ncgs_on_d[dd] = Ncgs_on_max_d[dd]
        elif (Ncgs_on_max_d[dd] > Ndash_cgs_on_d[dd]) and (Ndash_cgs_on_d[dd] > 0):
            Ncgs_on_d[dd] = np.ceil(Ndash_cgs_on_d[dd])
        elif Ndash_cgs_on_d[dd] <= 0:
            Ncgs_on_d[dd] = 0

    ##----------------------------------------------------------------------------------
    ## 解説書 8.14 発電負荷率
    ##----------------------------------------------------------------------------------
    # mx_lcgs_d : 日付dにおけるCGSの負荷率 [-]

    mx_lcgs_d = np.zeros(365)

    for dd in range(0, 365):

        if Tcgs_d[dd] > 0 and Ncgs_on_d[dd] > 0:

            mx_lcgs_d[dd] = Ee_load_d[dd] / (Ecgs_rated * Tcgs_d[dd] * Ncgs_on_d[dd])

            if mx_lcgs_d[dd] > 1:
                mx_lcgs_d[dd] = 1

        elif Tcgs_d[dd] == 0 or Ncgs_on_d[dd] == 0:

            mx_lcgs_d[dd] = 0

    ##----------------------------------------------------------------------------------
    ## 解説書 8.15 発電効率、排熱回収効率
    ##----------------------------------------------------------------------------------
    # mxRe_cgs_d : 日付dにおけるCGSの発電効率(低位発熱量基準)
    # mxRhr_cgs_d : 日付dにおけるCGSの発電効率(低位発熱量基準)

    mxRe_cgs_d = fe2 * mx_lcgs_d ** 2 + fe1 * mx_lcgs_d + fe0
    mxRhr_cgs_d = fhr2 * mx_lcgs_d ** 2 + fhr1 * mx_lcgs_d + fhr0

    ##----------------------------------------------------------------------------------
    ## 解説書 8.16 発電量、有効発電量
    ##----------------------------------------------------------------------------------
    # Ee_cgs_d  : 日付dにおけるCGSの発電量 [kWh/day]
    # Eee_cgs_d : 日付dにおけるCGSの有効発電量（補機動力を除く発電量） [kWh/day]

    Ee_cgs_d = Ecgs_rated * Ncgs_on_d * Tcgs_d * mx_lcgs_d
    Eee_cgs_d = Ee_cgs_d / (1 + fesub_CGS)

    ##----------------------------------------------------------------------------------
    ## 解説書 8.17 燃料消費量、排熱回収量
    ##----------------------------------------------------------------------------------
    # Es_cgs_d  : 日付dにおけるCGSの燃料消費量（高位発熱量基準） [MJ/day]
    # qhr_cgs_d : 日付dにおけるCGSの排熱回収量 [MJ/day]

    Es_cgs_d = Ee_cgs_d * 3.6 / (mxRe_cgs_d * fcgs_e_cor * flh)
    qhr_cgs_d = Es_cgs_d * fcgs_e_cor * mxRhr_cgs_d * flh

    ##----------------------------------------------------------------------------------
    ## 解説書 8.18 有効排熱回収量
    ##-------------------------------------------------------------------------------
    # qehr_cgs_d : 日付dにおけるCGSの有効排熱回収量 [MJ/day]

    qehr_cgs_d = np.zeros(365)
    for dd in range(0, 365):

        if qhr_cgs_d[dd] * fhr_loss >= qtotal_hr_on_d[dd]:
            qehr_cgs_d[dd] = qtotal_hr_on_d[dd]
        else:
            qehr_cgs_d[dd] = qhr_cgs_d[dd] * fhr_loss

    ##----------------------------------------------------------------------------------
    ## 解説書 8.19 各用途の排熱利用量
    ##----------------------------------------------------------------------------------

    if npri_hr_c == "1番目":
        qpri1_ehr_on_d = qAC_ref_c_hr_on_d
    elif npri_hr_h == "1番目":
        qpri1_ehr_on_d = qAC_ref_h_hr_on_d
    elif npri_hr_w == "1番目":
        qpri1_ehr_on_d = qW_hr_on_d
    else:
        raise Exception("排熱利用先の設定が不正です")

    if npri_hr_c == "2番目":
        qpri2_ehr_on_d = qAC_ref_c_hr_on_d
    elif npri_hr_h == "2番目":
        qpri2_ehr_on_d = qAC_ref_h_hr_on_d
    elif npri_hr_w == "2番目":
        qpri2_ehr_on_d = qW_hr_on_d
    else:
        qpri2_ehr_on_d = np.zeros(365)

    if npri_hr_c == "3番目":
        qpri3_ehr_on_d = qAC_ref_c_hr_on_d
    elif npri_hr_h == "3番目":
        qpri3_ehr_on_d = qAC_ref_h_hr_on_d
    elif npri_hr_w == "3番目":
        qpri3_ehr_on_d = qW_hr_on_d
    else:
        qpri3_ehr_on_d = np.zeros(365)

    qpri1_ehr_d = np.zeros(365)
    qpri2_ehr_d = np.zeros(365)
    qpri3_ehr_d = np.zeros(365)

    qAC_ref_c_ehr_d = np.zeros(365)
    qAC_ref_h_ehr_d = np.zeros(365)
    qW_ehr_d = np.zeros(365)

    for dd in range(0, 365):

        if qehr_cgs_d[dd] >= qpri1_ehr_on_d[dd]:

            qpri1_ehr_d[dd] = qpri1_ehr_on_d[dd]

            if qehr_cgs_d[dd] - qpri1_ehr_d[dd] >= qpri2_ehr_on_d[dd]:

                qpri2_ehr_d[dd] = qpri2_ehr_on_d[dd]

                if qehr_cgs_d[dd] - qpri1_ehr_d[dd] - qpri2_ehr_d[dd] >= qpri3_ehr_on_d[dd]:

                    qpri3_ehr_d[dd] = qpri3_ehr_on_d[dd]

                elif qehr_cgs_d[dd] - qpri1_ehr_d[dd] - qpri2_ehr_d[dd] < qpri3_ehr_on_d[dd]:

                    qpri3_ehr_d[dd] = qehr_cgs_d[dd] - qpri1_ehr_d[dd] - qpri2_ehr_d[dd]

            elif qehr_cgs_d[dd] - qpri1_ehr_d[dd] < qpri2_ehr_on_d[dd]:

                qpri2_ehr_d[dd] = qehr_cgs_d[dd] - qpri1_ehr_d[dd]
                qpri3_ehr_d[dd] = 0

        elif qehr_cgs_d[dd] < qpri1_ehr_on_d[dd]:

            qpri1_ehr_d[dd] = qehr_cgs_d[dd]
            qpri2_ehr_d[dd] = 0
            qpri3_ehr_d[dd] = 0

        if npri_hr_c == "1番目":
            qAC_ref_c_ehr_d[dd] = qpri1_ehr_d[dd]
        elif npri_hr_c == "2番目":
            qAC_ref_c_ehr_d[dd] = qpri2_ehr_d[dd]
        elif npri_hr_c == "3番目":
            qAC_ref_c_ehr_d[dd] = qpri3_ehr_d[dd]
        else:
            qAC_ref_c_ehr_d[dd] = 0

        if npri_hr_h == "1番目":
            qAC_ref_h_ehr_d[dd] = qpri1_ehr_d[dd]
        elif npri_hr_h == "2番目":
            qAC_ref_h_ehr_d[dd] = qpri2_ehr_d[dd]
        elif npri_hr_h == "3番目":
            qAC_ref_h_ehr_d[dd] = qpri3_ehr_d[dd]
        else:
            qAC_ref_h_ehr_d[dd] = 0

        if npri_hr_w == "1番目":
            qW_ehr_d[dd] = qpri1_ehr_d[dd]
        elif npri_hr_w == "2番目":
            qW_ehr_d[dd] = qpri2_ehr_d[dd]
        elif npri_hr_w == "3番目":
            qW_ehr_d[dd] = qpri3_ehr_d[dd]
        else:
            qW_ehr_d[dd] = 0

    ##----------------------------------------------------------------------------------
    ## 解説書 8.20 各用途の一次エネルギー削減量
    ##----------------------------------------------------------------------------------
    EAC_ref_c_red_d = np.zeros(365)
    EAC_ref_h_red_d = np.zeros(365)
    EW_red_d = np.zeros(365)

    for dd in range(0, 365):

        # EAC_ref_c_red_d : 日付dにおける冷房の一次エネルギー削減量 [MJ/day]
        if qAC_ref_c_hr_on_d[dd] == 0:
            EAC_ref_c_red_d[dd] = 0
        else:
            EAC_ref_c_red_d[dd] = EAC_ref_c_hr_on_d[dd] * qAC_ref_c_ehr_d[dd] / qAC_ref_c_hr_on_d[dd]

        # EAC_ref_h_red_d : 日付dにおける暖房の一次エネルギー削減量 [MJ/day]
        if qAC_ref_h_hr_on_d[dd] == 0:
            EAC_ref_h_red_d[dd] = 0
        else:
            EAC_ref_h_red_d[dd] = EAC_ref_h_hr_on_d[dd] * qAC_ref_h_ehr_d[dd] / qAC_ref_h_hr_on_d[dd]

            # EW_red_d : 日付dにおける給湯の一次エネルギー削減量 [MJ/day]
        if qW_hr_on_d[dd] == 0:
            EW_red_d[dd] = 0
        else:
            EW_red_d[dd] = EW_hr_on_d[dd] * qW_ehr_d[dd] / qW_hr_on_d[dd]

    ##----------------------------------------------------------------------------------
    ## 解説書 8.21 電力の一次エネルギー削減量
    ##----------------------------------------------------------------------------------
    # Ee_red_d : 日付dにおける発電による電力の一次エネルギー削減量 [MJ/day]
    Ee_red_d = Eee_cgs_d * fprime_e

    ##----------------------------------------------------------------------------------
    ## 解説書 8.22 CGSによる一次エネルギー削減量
    ##----------------------------------------------------------------------------------
    # Etotal_cgs_red_d : 日付dにおけるCGSによる一次エネルギー削減量 [MJ/day]

    Etotal_cgs_red_d = EAC_ref_c_red_d + EAC_ref_h_red_d + EW_red_d + Ee_red_d - Es_cgs_d

    # 結果の出力
    result_json["システム名称"] = cgs_name  # 系統名称

    result_json["年間運転時間"] = np.sum(Tcgs_d * Ncgs_on_d)  # 年間運転時間 [時間・台]

    if np.sum(Ncgs_on_d) == 0:
        result_json["年平均負荷率"] = 0
    else:
        result_json["年平均負荷率"] = np.sum(Ncgs_on_d * mx_lcgs_d) / np.sum(Ncgs_on_d)  # 年平均負荷率 [-]

    result_json["年間発電量"] = np.sum(Ee_cgs_d) / 1000  # 年間発電量 [MWh]
    result_json["年間排熱回収量"] = np.sum(qhr_cgs_d) / 1000  # 年間排熱回収量 [GJ]
    result_json["年間ガス消費量"] = np.sum(Es_cgs_d) / 1000  # 年間ガス消費量 [GJ]

    if result_json["年間ガス消費量"] == 0:
        result_json["年間発電効率"] = 0
        result_json["年間排熱回収効率"] = 0
    else:
        result_json["年間発電効率"] = result_json["年間発電量"] * 3.6 / result_json["年間ガス消費量"] * 100  # 年間発電効率 [%]
        result_json["年間排熱回収効率"] = result_json["年間排熱回収量"] / result_json[
            "年間ガス消費量"] * 100  # 年間排熱回収効率 [%]

    result_json["年間有効発電量"] = np.sum(Eee_cgs_d) / 1000  # 年間有効発電量 [%]
    result_json["年間有効排熱回収量"] = np.sum(qehr_cgs_d) / 1000  # 年間有効排熱回収量 [GJ]

    if result_json["年間ガス消費量"] == 0:
        result_json["有効総合効率"] = 0
    else:
        result_json["有効総合効率"] = (result_json["年間有効発電量"] * 3.6 + result_json["年間有効排熱回収量"]) / \
                                      result_json["年間ガス消費量"] * 100  # 有効総合効率 [%]

    result_json["年間一次エネルギー削減量(電力)"] = np.sum(Ee_red_d) / 1000  # 年間一次エネルギー削減量(電力) [GJ]
    result_json["年間一次エネルギー削減量(冷房)"] = np.sum(EAC_ref_c_red_d) / 1000  # 年間一次エネルギー削減量(冷房) [GJ]
    result_json["年間一次エネルギー削減量(暖房)"] = np.sum(EAC_ref_h_red_d) / 1000  # 年間一次エネルギー削減量(暖房) [GJ]
    result_json["年間一次エネルギー削減量(給湯)"] = np.sum(EW_red_d) / 1000  # 年間一次エネルギー削減量(給湯) [GJ]
    result_json["年間一次エネルギー削減量"] = np.sum(Etotal_cgs_red_d) / 1000  # 年間一次エネルギー削減量合計 [GJ]

    if np.isnan(result_json["年間一次エネルギー削減量"]):
        raise Exception("コジェネの計算でエラーが発生しました")

    if DEBUG:  # pragma: no cover
        print(f'年間一次エネルギー削減量 全体 : {result_json["年間一次エネルギー削減量"]} GJ/年')
        result_json["EAC_ref_c_red_d"] = EAC_ref_c_red_d

    return result_json


if __name__ == '__main__':  # pragma: no cover

    print('----- cogeneration.py -----')
    # filename = './tests/cogeneration/Case_hospital_05.json'
    # filename = './tests/cogeneration/Case_hotel_test.json'
    filename = './tests/cogeneration/Case_office_09.json'
    # filename = './sample/cgs.json'

    # テンプレートjsonの読み込み
    with open(filename, 'r', encoding='utf-8') as f:
        input_data = json.load(f)

    # 各設備の計算
    result_json_for_cgs = {
        "AC": {},
        "V": {},
        "L": {},
        "HW": {},
        "EV": {},
        "PV": {},
        "OT": {},
    }

    import airconditioning
    import ventilation
    import lighting
    import hotwatersupply
    import elevator
    import photovoltaic
    import other_energy

    if input_data["air_conditioning_zone"]:
        result_jsonAC = airconditioning.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["AC"] = result_jsonAC["for_cgs"]
    if input_data["ventilation_room"]:
        result_jsonV = ventilation.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["V"] = result_jsonV["for_cgs"]
    if input_data["lighting_systems"]:
        result_jsonL = lighting.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["L"] = result_jsonL["for_cgs"]
    if input_data["hot_water_room"]:
        result_jsonhW = hotwatersupply.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["HW"] = result_jsonhW["for_cgs"]
    if input_data["elevators"]:
        result_jsonEV = elevator.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["EV"] = result_jsonEV["for_cgs"]
    if input_data["photovoltaic_systems"]:
        result_jsonPV = photovoltaic.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["PV"] = result_jsonPV["for_cgs"]
    if input_data["rooms"]:
        result_jsonOT = other_energy.calc_energy(input_data, DEBUG=False)
        result_json_for_cgs["OT"] = result_jsonOT["for_cgs"]

    result_json = calc_energy(input_data, result_json_for_cgs, DEBUG=True)

    # with open("result_json_for_cgs.json",'w', encoding='utf-8') as fw:
    #     json.dump(result_json_for_cgs, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

    with open("result_json_CGS.json", 'w', encoding='utf-8') as fw:
        json.dump(result_json, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)
