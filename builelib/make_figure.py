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
