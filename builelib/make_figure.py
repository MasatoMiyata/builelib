from datetime import time
from posixpath import normcase
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from . import commons as bc

# グラフ文字化け対策
mpl.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['grid.linestyle']='--'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['font.size'] = 14

def hourlyplot(x, lable_text, color_name, title_text):
    """
    365日×24時間 のデータをグラフ化する関数
    """

    # 8760の行列に変換
    xdata = bc.trans_36524to8760(x)

    fig = plt.figure(figsize=(12,6))
    fig.subplots_adjust(left=0.08, bottom=0.08, right=0.98, top=0.93, wspace=0.27, hspace=0.27)

    ax = fig.add_subplot(2,1,1)
    ax.plot(xdata, '-', label=lable_text, color=color_name)
    ax.set_xticks([0,744,1416,2160,2880,3624,4344,5088,5832,6552,7296,8016,8760]) 
    ax.set_xticklabels(["1/1", "2/1", "3/1", "4/1", "5/1","6/1", "7/1", "8/1", "9/1", "10/1","11/1","12/1","1/1"])
    ax.set_title(title_text)
    ax.legend()
    ax.grid()

    start_num = 96
    ax = fig.add_subplot(2,3,4)
    ax.plot(xdata, '-', label="冬期 1/4", color=color_name)
    ax.set_xlim([start_num,start_num+24]) 
    ax.set_xticks([start_num,start_num+6,start_num+12,start_num+18,start_num+24])
    ax.set_xticklabels(["0:00", "6:00", "12:00", "18:00", "0:00"])
    ax.legend()
    ax.grid()

    start_num = 2448
    ax = fig.add_subplot(2,3,5)
    ax.plot(xdata, '-', label="中間期 4/13", color=color_name)
    ax.set_xlim([start_num,start_num+24]) 
    ax.set_xticks([start_num,start_num+6,start_num+12,start_num+18,start_num+24])
    ax.set_xticklabels(["0:00", "6:00", "12:00", "18:00", "0:00"])
    ax.legend()
    ax.grid()

    start_num = 4824
    ax = fig.add_subplot(2,3,6)
    ax.plot(xdata, '-', label="夏期 7/21", color=color_name)
    ax.set_xlim([start_num,start_num+24]) 
    ax.set_xticks([start_num,start_num+6,start_num+12,start_num+18,start_num+24])
    ax.set_xticklabels(["0:00", "6:00", "12:00", "18:00", "0:00"])
    ax.legend()
    ax.grid()


def matrix_load( load_ratio ):

    if load_ratio > 0:
        if load_ratio <= 0.1:
            matrix_iL = 0
        elif  load_ratio <= 0.2:
            matrix_iL = 1
        elif  load_ratio <= 0.3:
            matrix_iL = 2       
        elif  load_ratio <= 0.4:
            matrix_iL = 3
        elif  load_ratio <= 0.5:
            matrix_iL = 4
        elif  load_ratio <= 0.6:
            matrix_iL = 5
        elif  load_ratio <= 0.7:
            matrix_iL = 6
        elif  load_ratio <= 0.8:
            matrix_iL = 7
        elif  load_ratio <= 0.9:
            matrix_iL = 8
        elif  load_ratio <= 1.0:
            matrix_iL = 9
        else:
            matrix_iL = 10
    else:
        raise Exception("負荷率が負の値です")

    return matrix_iL


def histgram_matrix_ahu(load_ratio, heat_amount, energy):
    """
    空調機群の計算結果をマトリックス表示する関数
    """

    time_cooling   = np.zeros(11)
    energy_cooling = np.zeros(11)
    time_heating   = np.zeros(11)
    energy_heating = np.zeros(11)

    for dd in range(365):
        for hh in range(24):

            if load_ratio[dd][hh] > 0:

                # 負荷率帯の区分
                matrix_iL = matrix_load( load_ratio[dd][hh] )

                if heat_amount[dd][hh] >= 0:
                    time_cooling[matrix_iL] += 1
                    energy_cooling[matrix_iL] += energy[dd][hh]
                else:
                    time_heating[matrix_iL] += 1
                    energy_heating[matrix_iL] += energy[dd][hh]

    print("負荷出現時間[h]のマトリックス")
    print(time_cooling)
    print(time_heating)

    print("消費電力[kW]のマトリックス")
    print(energy_cooling/time_cooling*1000)
    print(energy_heating/time_heating*1000)

    print("電力消費量[MWh]のマトリックス")
    print(energy_cooling)
    print(energy_heating)

    x = [1,2,3,4,5,6,7,8,9,10,11]
    label = ["0〜0.1","0.1〜0.2","0.2〜0.3","0.3〜0.4","0.4〜0.5","0.5〜0.6",
        "0.6〜0.7","0.7〜0.8","0.8〜0.9","0.9〜1.0","1.0〜"]

    fig = plt.figure(figsize=(12,6))
    fig.subplots_adjust(left=0.08, bottom=0.08, right=0.98, top=0.93, wspace=0.27, hspace=0.27)

    ax = fig.add_subplot(2,1,1)
    ax.bar(x, time_cooling, tick_label=label, align="center")
    ax.grid()

    ax = fig.add_subplot(2,1,2)
    ax.bar(x, time_heating, tick_label=label, align="center")
    ax.grid()


def histgram_matrix_pump(load_ratio, number_of_operation, energy_consumption):
    """
    二次ポンプ群の計算結果をマトリックス表示する関数
    """

    time   = np.zeros(11)
    number = np.zeros(11)
    energy = np.zeros(11)

    for dd in range(365):
        for hh in range(24):

            # 負荷率帯の区分
            if load_ratio[dd][hh] > 0:

                # 負荷率帯の区分
                matrix_iL = matrix_load( load_ratio[dd][hh] )

                time[matrix_iL] += 1
                number[matrix_iL] += number_of_operation[dd][hh]
                energy[matrix_iL] += energy_consumption[dd][hh]

    print("負荷出現時間[h]のマトリックス")
    print(time)

    print("運転台数のマトリックス")
    print(number/time)

    print("消費電力[kW]のマトリックス")
    print(energy/time*1000)

    print("電力消費量[MWh]のマトリックス")
    print(energy)

    x = [1,2,3,4,5,6,7,8,9,10,11]
    label = ["0〜0.1","0.1〜0.2","0.2〜0.3","0.3〜0.4","0.4〜0.5","0.5〜0.6",
        "0.6〜0.7","0.7〜0.8","0.8〜0.9","0.9〜1.0","1.0〜"]

    fig = plt.figure(figsize=(12,6))
    fig.subplots_adjust(left=0.08, bottom=0.08, right=0.98, top=0.93, wspace=0.27, hspace=0.27)

    ax = fig.add_subplot(2,1,1)
    ax.bar(x, time, tick_label=label, align="center")
    ax.grid()


def histgram_matrix_ref(load_ratio, number_of_operation, energy_consumption):
    """
    熱源群の計算結果をマトリックス表示する関数
    """

    time   = np.zeros(11)
    number = np.zeros(11)
    energy = np.zeros(11)

    for dd in range(365):
        for hh in range(24):

            # 負荷率帯の区分
            if load_ratio[dd][hh] > 0:

                # 負荷率帯の区分
                matrix_iL = matrix_load( load_ratio[dd][hh] )

                time[matrix_iL] += 1
                number[matrix_iL] += number_of_operation[dd][hh]
                energy[matrix_iL] += energy_consumption[dd][hh]

    print("負荷出現時間[h]のマトリックス")
    print(time)
    print("運転台数のマトリックス")
    print(number/time)
    print("エネルギー消費量[kW]のマトリックス")
    print(energy/time*1000/3600)




