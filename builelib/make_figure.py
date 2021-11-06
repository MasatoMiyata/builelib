import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from . import commons as bc

# グラフ文字化け対策
mpl.rcParams['font.family'] = 'Noto Sans CJK JP'
plt.rcParams['grid.linestyle']='--'
plt.rcParams['grid.linewidth'] = 0.5
plt.rcParams['font.size'] = 14

def hourlyplot(x, lable_text, color_name):
    """
    365日×24時間 のデータをグラフ化する関数
    """

    # 8760の行列に変換
    xdata = bc.trans_36524to8760(x)

    fig = plt.figure(figsize=(12,5))
    fig.subplots_adjust(left=0.06, bottom=0.08, right=0.98, top=0.97, wspace=0.16, hspace=0.27)
    ax = fig.add_subplot(1,1,1)
    ax.plot(xdata, '-', label=lable_text, color=color_name)
    ax.set_xticks([0,744,1416,2160,2880,3624,4344,5088,5832,6552,7296,8016,8760]) 
    ax.set_xticklabels(["1/1", "2/1", "3/1", "4/1", "5/1","6/1", "7/1", "8/1", "9/1", "10/1","11/1","12/1","1/1"])
    ax.legend()
    ax.grid()
