import json
from builelib import commons as bc
from builelib import airconditioning as ac
from builelib import airconditioning_webpro as ac_web
# import matplotlib.pyplot as plt

# filename = './sample/ACtest_Case001.json'
# filename = './sample/Case_office_00.json'
# filename = './sample/ACtest_Case033.json'
filename = './sample/WEBPRO_inputSheet_sample.json'

# 入力ファイルの読み込み
with open(filename, 'r', encoding='utf-8') as f:
    inputdata = json.load(f)

# 計算の実行
# resultJson = ac.calc_energy(inputdata, debug=True)

# with open("resultJson_AC.json",'w', encoding='utf-8') as fw:
#     json.dump(resultJson, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

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

# 計算の実行(webproモード)
resultJson_webpro = ac_web.calc_energy(inputdata, debug=True)

with open("resultJson_AC.json",'w', encoding='utf-8') as fw:
    json.dump(resultJson_webpro, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

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

# plt.show()