import json

import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

# グラフ文字化け対策
mpl.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.linewidth'] = 0.5

# データベースjsonの読み込み
with open('./builelib/database/heat_source_performance.json', 'r', encoding='utf-8') as f:
    db = json.load(f)


# 性能曲線の4次式計算（冷却水温度による変化がない場合）
def calcQuarticCurve(dataSetALL, T, cw):
    # 冷却水温度 cw に該当するパラメータリストのみを抽出する。
    dataSet = list()

    if dataSetALL[0]["冷却水温度下限"] is not None:

        # 下限値の小さい順に並び替え
        dataSetALL = sorted(dataSetALL, key=lambda x: x['冷却水温度下限'], reverse=False)

        for i in range(0, len(dataSetALL)):
            if i == 0 and cw < dataSetALL[0]["冷却水温度下限"]:
                dataSet.append(dataSetALL[0])
            elif dataSetALL[i]["冷却水温度下限"] <= cw and cw < dataSetALL[i]["冷却水温度上限"]:
                dataSet.append(dataSetALL[i])
            elif i == len(dataSetALL) - 1 and dataSetALL[-1]["冷却水温度上限"] <= cw:
                dataSet.append(dataSetALL[-1])

    else:
        # 冷却水温度による条件分けがない機種については、全てを対象とする。
        dataSet = dataSetALL

    # 下限値の小さい順に並び替え
    dataSet = sorted(dataSet, key=lambda x: x['下限'], reverse=False)

    # 条件に応じて複数の係数がある場合、Tの値に基づき、該当する係数を選ぶ。
    paraSet = []
    for i in range(0, len(dataSet)):

        if i == 0 and T < dataSet[0]["下限"]:  # 全ての下限を下回っている場合は、下限が最も小さいパラメータセットを選択。
            paraSet = dataSet[0]
            break
        elif dataSet[i]["下限"] <= T and T < dataSet[i]["上限"]:  # 下限と上限の間にあるパラメータセットを選択。
            paraSet = dataSet[i]
            break
        elif i == len(dataSet) - 1 and dataSet[-1]["上限"] <= T:  # 全ての上限を上回っている場合は、上限が最も大きいパラメータセットを選択。
            paraSet = dataSet[-1]
            break

    # 上限と下限でリミットをかける。
    limit = False
    if T < paraSet["下限"]:
        T = paraSet["下限"]
        limit = True
    elif paraSet["上限"] < T:
        T = paraSet["上限"]
        limit = True

    # ４次式
    y = float(paraSet["係数"]["a4"]) * T ** 4 \
        + float(paraSet["係数"]["a3"]) * T ** 3 \
        + float(paraSet["係数"]["a2"]) * T ** 2 \
        + float(paraSet["係数"]["a1"]) * T \
        + float(paraSet["係数"]["a0"])

    # グラフ描画用 ylimit の定義
    if limit == True:
        # 上限or下限を超えたときには None を代入する。
        ylimit = None
    else:
        ylimit = y

    return y, ylimit


for typename in db:

    ## 冷房の特性

    if db[typename]["冷房時の特性"]["燃料種類"] != "":

        if db[typename]["冷房時の特性"]["熱源種類"] == "空気" or db[typename]["冷房時の特性"]["熱源種類"] == "不要":
            xlabel = "外気乾球温度[℃]"
            xmin = -10
            xmax = 50
        elif db[typename]["冷房時の特性"]["熱源種類"] == "水":
            xlabel = "冷却水温度[℃]"
            xmin = -10
            xmax = 50
        elif db[typename]["冷房時の特性"]["熱源種類"].startswith("地盤"):
            xlabel = "熱源水温度[℃]"
            xmin = -10
            xmax = 50

        if typename == "ルームエアコンディショナ":
            ymin = 0.6
            ymax = 2.2
        else:
            ymin = 0.2
            ymax = 1.8

        # 冷却水温度
        if typename == "インバータターボ冷凍機":
            cw = [20, 26, 36]
        else:
            cw = 32

        x_capacity_C = np.arange(xmin, xmax + 2.5, 2.5)  # 能力比 冷房
        x_input_C = np.arange(xmin, xmax + 2.5, 2.5)  # 入力比 冷房
        x_load_C = np.arange(0, 1 + 0.05, 0.05)  # 部分負荷率 冷房
        x_supply_C = np.arange(-10, 30 + 0.1, 2.5)  # 送水温度 冷房

        ## 能力比
        y_capacity_C = list()
        y_capacity_C_limit = list()
        for T in x_capacity_C:
            y_capacity_C.append(calcQuarticCurve(db[typename]["冷房時の特性"]["能力比"], T, cw)[0])
            y_capacity_C_limit.append(calcQuarticCurve(db[typename]["冷房時の特性"]["能力比"], T, cw)[1])

        ## 入力比
        y_input_C = list()
        y_input_C_limit = list()
        for T in x_input_C:
            y_input_C.append(calcQuarticCurve(db[typename]["冷房時の特性"]["入力比"], T, cw)[0])
            y_input_C_limit.append(calcQuarticCurve(db[typename]["冷房時の特性"]["入力比"], T, cw)[1])

        ## 部分負荷特性
        if typename == "インバータターボ冷凍機":  # インバータターボ冷凍機のみ場合分け

            y_load_c_low = list()
            y_load_C_mid = list()
            y_load_C_high = list()
            y_load_C_mid_limit = list()
            y_load_C_high_limit = list()
            y_load_c_low_limit = list()
            for T in x_load_C:
                y_load_c_low.append(calcQuarticCurve(db[typename]["冷房時の特性"]["部分負荷特性"], T, cw[0])[0])
                y_load_C_mid.append(calcQuarticCurve(db[typename]["冷房時の特性"]["部分負荷特性"], T, cw[1])[0])
                y_load_C_high.append(calcQuarticCurve(db[typename]["冷房時の特性"]["部分負荷特性"], T, cw[2])[0])
                y_load_c_low_limit.append(calcQuarticCurve(db[typename]["冷房時の特性"]["部分負荷特性"], T, cw[0])[1])
                y_load_C_mid_limit.append(calcQuarticCurve(db[typename]["冷房時の特性"]["部分負荷特性"], T, cw[1])[1])
                y_load_C_high_limit.append(calcQuarticCurve(db[typename]["冷房時の特性"]["部分負荷特性"], T, cw[2])[1])

        else:
            y_load_C = list()
            y_load_C_limit = list()
            for T in x_load_C:
                y_load_C.append(calcQuarticCurve(db[typename]["冷房時の特性"]["部分負荷特性"], T, cw)[0])
                y_load_C_limit.append(calcQuarticCurve(db[typename]["冷房時の特性"]["部分負荷特性"], T, cw)[1])

        ## 送水温度特性
        y_supply_C = list()
        y_supply_C_limit = list()
        for T in x_supply_C:
            if len(db[typename]["冷房時の特性"]["送水温度特性"]) != 0:
                y_supply_C.append(calcQuarticCurve(db[typename]["冷房時の特性"]["送水温度特性"], T, cw)[0])
                y_supply_C_limit.append(calcQuarticCurve(db[typename]["冷房時の特性"]["送水温度特性"], T, cw)[1])
            else:
                y_supply_C.append(None)
                y_supply_C_limit.append(None)

        ## グラフ作成
        fig1 = plt.figure(figsize=(10, 6.5))
        fig1.suptitle(typename + " 冷房")
        fig1.subplots_adjust(left=0.07, bottom=0.09, right=0.98, top=0.92, wspace=0.16, hspace=0.27)

        ax1 = fig1.add_subplot(2, 2, 1)
        ax1.plot(x_capacity_C, y_capacity_C, 'ko', markerfacecolor='w', linestyle="dotted")
        ax1.plot(x_capacity_C, y_capacity_C_limit, 'ko-')
        ax1.set_xlim([xmin, xmax])
        ax1.set_ylim([ymin, ymax])
        ax1.set_xlabel(xlabel)
        ax1.set_ylabel("最大能力比（冷房）[-]")
        ax1.grid()

        ax2 = fig1.add_subplot(2, 2, 2)
        ax2.plot(x_input_C, y_input_C, 'ko', markerfacecolor='w', linestyle="dotted")
        ax2.plot(x_input_C, y_input_C_limit, 'ko-')
        ax2.set_xlim([xmin, xmax])
        ax2.set_ylim([ymin, ymax])
        ax2.set_xlabel(xlabel)
        ax2.set_ylabel("最大入力比（冷房）[-]")
        ax2.grid()

        ax3 = fig1.add_subplot(2, 2, 3)
        if typename == "インバータターボ冷凍機":  # インバータターボ冷凍機のみ場合分け
            ax3.plot(x_load_C, y_load_c_low, 'ko', markerfacecolor='w', linestyle="dotted")
            ax3.plot(x_load_C, y_load_c_low_limit, 'ko-')
            ax3.plot(x_load_C, y_load_C_mid, 'ko', markerfacecolor='w', linestyle="dotted")
            ax3.plot(x_load_C, y_load_C_mid_limit, 'ko-')
            ax3.plot(x_load_C, y_load_C_high, 'ko', markerfacecolor='w', linestyle="dotted")
            ax3.plot(x_load_C, y_load_C_high_limit, 'ko-')
            ax3.text(0.5, 0.3, "冷却水温度 〜24℃")
            ax3.text(0.08, 0.5, "冷却水温度 24〜32℃")
            ax3.text(0.05, 0.58, "冷却水温度 32℃〜")
        else:
            ax3.plot(x_load_C, y_load_C, 'ko', markerfacecolor='w', linestyle="dotted")
            ax3.plot(x_load_C, y_load_C_limit, 'ko-')
        ax3.set_xlim([0, 1.0])
        ax3.set_ylim([0, 1.0])
        ax3.set_xlabel("部分負荷率（冷房）[-]")
        ax3.set_ylabel("入力比（冷房）[-]")
        ax3.grid()

        ax4 = fig1.add_subplot(2, 2, 4)
        ax4.plot(x_supply_C, y_supply_C, 'ko', markerfacecolor='w', linestyle="dotted")
        ax4.plot(x_supply_C, y_supply_C_limit, 'ko-')
        ax4.set_xlim([-10, 30])
        ax4.set_ylim([ymin, ymax])
        ax4.set_xlabel("送水温度 [℃]")
        ax4.set_ylabel("入力比（冷房）[-]")
        ax4.grid()

        fig1.savefig("./tools/figures/" + typename + '_冷房.png')

    ## 暖房のグラフ化
    if db[typename]["暖房時の特性"]["燃料種類"] != "":

        if db[typename]["暖房時の特性"]["熱源種類"] == "空気":
            xlabel = "外気湿球温度[℃]"
            xmin = -20
            xmax = 20
        elif db[typename]["暖房時の特性"]["熱源種類"] == "不要":
            xlabel = "外気乾球温度[℃]"
            xmin = -20
            xmax = 20
        elif db[typename]["暖房時の特性"]["熱源種類"] == "水":
            xlabel = "冷却水温度[℃]"
            xmin = -10
            xmax = 50
        elif db[typename]["暖房時の特性"]["熱源種類"].startswith("地盤"):
            xlabel = "熱源水温度[℃]"
            xmin = -10
            xmax = 50

        if typename == "ルームエアコンディショナ":
            ymin = 0.6
            ymax = 2.2
        else:
            ymin = 0.2
            ymax = 1.8

        # 冷却水温度
        cw = 10

        x_capacity_h = np.arange(xmin, xmax + 2.5, 2.5)  # 能力比 暖房
        x_input_h = np.arange(xmin, xmax + 2.5, 2.5)  # 入力比 暖房
        x_load_h = np.arange(0, 1 + 0.05, 0.05)  # 部分負荷率 暖房
        x_supply_h = np.arange(30, 60 + 1, 2.5)  # 送水温度 暖房

        ## 能力比
        y_capacity_h = list()
        y_capacity_h_limit = list()
        for T in x_capacity_h:
            y_capacity_h.append(calcQuarticCurve(db[typename]["暖房時の特性"]["能力比"], T, cw)[0])
            y_capacity_h_limit.append(calcQuarticCurve(db[typename]["暖房時の特性"]["能力比"], T, cw)[1])

        ## 入力比
        y_input_h = list()
        y_input_h_limit = list()
        for T in x_input_h:
            y_input_h.append(calcQuarticCurve(db[typename]["暖房時の特性"]["入力比"], T, cw)[0])
            y_input_h_limit.append(calcQuarticCurve(db[typename]["暖房時の特性"]["入力比"], T, cw)[1])

        ## 部分負荷特性
        y_load_h = list()
        y_load_h_limit = list()
        for T in x_load_h:
            y_load_h.append(calcQuarticCurve(db[typename]["暖房時の特性"]["部分負荷特性"], T, cw)[0])
            y_load_h_limit.append(calcQuarticCurve(db[typename]["暖房時の特性"]["部分負荷特性"], T, cw)[1])

        ## 送水温度特性
        y_supply_h = list()
        y_supply_h_limit = list()
        for T in x_supply_h:
            if len(db[typename]["暖房時の特性"]["送水温度特性"]) != 0:
                y_supply_h.append(calcQuarticCurve(db[typename]["暖房時の特性"]["送水温度特性"], T, cw)[0])
                y_supply_h_limit.append(calcQuarticCurve(db[typename]["暖房時の特性"]["送水温度特性"], T, cw)[1])
            else:
                y_supply_h.append(None)
                y_supply_h_limit.append(None)

        ## グラフ作成
        fig2 = plt.figure(figsize=(10, 6.5))
        fig2.suptitle(typename + " 暖房")
        fig2.subplots_adjust(left=0.07, bottom=0.09, right=0.98, top=0.92, wspace=0.16, hspace=0.27)

        ax1 = fig2.add_subplot(2, 2, 1)
        ax1.plot(x_capacity_h, y_capacity_h, 'ko', markerfacecolor='w', linestyle="dotted")
        ax1.plot(x_capacity_h, y_capacity_h_limit, 'ko-')
        ax1.set_xlim([xmin, xmax])
        ax1.set_ylim([ymin, ymax])
        ax1.set_xlabel(xlabel)
        ax1.set_ylabel("最大能力比（暖房）[-]")
        ax1.grid()

        ax2 = fig2.add_subplot(2, 2, 2)
        ax2.plot(x_input_h, y_input_h, 'ko', markerfacecolor='w', linestyle="dotted")
        ax2.plot(x_input_h, y_input_h_limit, 'ko-')
        ax2.set_xlim([xmin, xmax])
        ax2.set_ylim([ymin, ymax])
        ax2.set_xlabel(xlabel)
        ax2.set_ylabel("最大入力比（暖房）[-]")
        ax2.grid()

        ax3 = fig2.add_subplot(2, 2, 3)
        ax3.plot(x_load_h, y_load_h, 'ko', markerfacecolor='w', linestyle="dotted")
        ax3.plot(x_load_h, y_load_h_limit, 'ko-')
        ax3.set_xlim([0, 1.0])
        ax3.set_ylim([0, 1.0])
        ax3.set_xlabel("部分負荷率 [-]")
        ax3.set_ylabel("入力比（暖房） [-]")
        ax3.grid()

        ax4 = fig2.add_subplot(2, 2, 4)
        ax4.plot(x_supply_h, y_supply_h, 'ko', markerfacecolor='w', linestyle="dotted")
        ax4.plot(x_supply_h, y_supply_h_limit, 'ko-')
        ax4.set_xlim([30, 60])
        ax4.set_ylim([0.6, 1.8])
        ax4.set_xlabel("送水温度 [℃]")
        ax4.set_ylabel("入力比（暖房） [-]")
        ax4.grid()

        fig2.savefig("./tools/figures/" + typename + '_暖房.png')
