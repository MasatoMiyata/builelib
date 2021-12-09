import json
from builelib import commons as bc
from builelib import airconditioning as ac
# from builelib import airconditioning_hourly as ac
import matplotlib.pyplot as plt

print('----- airconditioning.py -----')
# filename = './sample/ACtest_Case001.json'
filename = './sample/Case_office_00.json'
# filename = './sample/ACtest_Case033.json'
# filename = './sample/Builelib_sample_SP10.json'

# 入力ファイルの読み込み
with open(filename, 'r', encoding='utf-8') as f:
    inputdata = json.load(f)

resultJson = ac.calc_energy(inputdata, DEBUG=True)

# 出力
with open("resultJson_AC.json",'w', encoding='utf-8') as fw:
    json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

# print( f'BEI/AC: {resultJson["BEI/AC"]}')        
# print( f'設計一次エネルギー消費量 全体: {resultJson["E_ac"]}')
# print( f'設計一次エネルギー消費量 空調ファン: {resultJson["energy"]["E_ahu_fan"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 空調全熱交換器: {resultJson["energy"]["E_ahu_aex"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 二次ポンプ: {resultJson["energy"]["E_pump"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 熱源主機: {resultJson["energy"]["E_ref_main"]}')
# print( f'設計一次エネルギー消費量 熱源補機: {resultJson["energy"]["E_ref_sub"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 一次ポンプ: {resultJson["energy"]["E_ref_pump"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 冷却塔ファン: {resultJson["energy"]["E_ref_ct_fan"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 冷却水ポンプ: {resultJson["energy"]["E_ref_ct_pump"] * bc.fprime}')
# plt.show()

print( f'BEI/AC: {resultJson["BEI_AC"]}')        
print( f'設計一次エネルギー消費量 全体: {resultJson["E_airconditioning"]}')
print( f'設計一次エネルギー消費量 空調ファン: {resultJson["ENERGY"]["E_fan"] * bc.fprime}')
print( f'設計一次エネルギー消費量 空調全熱交換器: {resultJson["ENERGY"]["E_aex"] * bc.fprime}')
print( f'設計一次エネルギー消費量 二次ポンプ: {resultJson["ENERGY"]["E_pump"] * bc.fprime}')
print( f'設計一次エネルギー消費量 熱源主機: {resultJson["ENERGY"]["E_refsysr"]}')
print( f'設計一次エネルギー消費量 熱源補機: {resultJson["ENERGY"]["E_refac"] * bc.fprime}')
print( f'設計一次エネルギー消費量 一次ポンプ: {resultJson["ENERGY"]["E_pumpP"] * bc.fprime}')
print( f'設計一次エネルギー消費量 冷却塔ファン: {resultJson["ENERGY"]["E_ctfan"] * bc.fprime}')
print( f'設計一次エネルギー消費量 冷却水ポンプ: {resultJson["ENERGY"]["E_ctpump"] * bc.fprime}')
