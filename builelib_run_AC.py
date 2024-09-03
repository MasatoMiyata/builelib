import json

from builelib import airconditioning_webpro as ac_web
from builelib import commons as bc

# import matplotlib.pyplot as plt

# filename = './sample/ACtest_Case001.json'
# filename = './sample/Case_office_00.json'
# filename = './sample/ACtest_Case033.json'
filename = './sample/WEBPRO_inputSheet_sample.json'

# 入力ファイルの読み込み
with open(filename, 'r', encoding='utf-8') as f:
    input_data = json.load(f)

# 計算の実行
# result_json = ac.calc_energy(input_data, debug=True)

# with open("result_json_AC.json",'w', encoding='utf-8') as fw:
#     json.dump(result_json, fw, indent=4, ensure_ascii=False, cls = bc.MyEncoder)

# print( f'BEI/AC: {result_json["BEI/AC"]}')
# print( f'設計一次エネルギー消費量 全体: {result_json["E_ac"]}')
# print( f'設計一次エネルギー消費量 空調ファン: {result_json["energy"]["E_ahu_fan"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 空調全熱交換器: {result_json["energy"]["E_ahu_aex"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 二次ポンプ: {result_json["energy"]["E_pump"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 熱源主機: {result_json["energy"]["E_ref_main"]}')
# print( f'設計一次エネルギー消費量 熱源補機: {result_json["energy"]["E_ref_sub"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 一次ポンプ: {result_json["energy"]["E_ref_pump"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 冷却塔ファン: {result_json["energy"]["E_ref_ct_fan"] * bc.fprime}')
# print( f'設計一次エネルギー消費量 冷却水ポンプ: {result_json["energy"]["E_ref_ct_pump"] * bc.fprime}')

# 計算の実行(webproモード)
result_json_webpro = ac_web.calc_energy(input_data, debug=True)

with open("result_json_AC.json", 'w', encoding='utf-8') as fw:
    json.dump(result_json_webpro, fw, indent=4, ensure_ascii=False, cls=bc.MyEncoder)

print(f'BEI/AC: {result_json_webpro["BEI/AC"]}')
print(f'設計一次エネルギー消費量 全体: {result_json_webpro["設計一次エネルギー消費量[MJ/年]"]}')
print(f'設計一次エネルギー消費量 空調ファン: {result_json_webpro["年間エネルギー消費量"]["空調機群ファン[GJ]"]}')
print(f'設計一次エネルギー消費量 空調全熱交換器: {result_json_webpro["年間エネルギー消費量"]["空調機群全熱交換器[GJ]"]}')
print(f'設計一次エネルギー消費量 二次ポンプ: {result_json_webpro["年間エネルギー消費量"]["二次ポンプ群[GJ]"]}')
print(f'設計一次エネルギー消費量 熱源主機: {result_json_webpro["年間エネルギー消費量"]["熱源群熱源主機[GJ]"]}')
print(f'設計一次エネルギー消費量 熱源補機: {result_json_webpro["年間エネルギー消費量"]["熱源群熱源補機[GJ]"]}')
print(f'設計一次エネルギー消費量 一次ポンプ: {result_json_webpro["年間エネルギー消費量"]["熱源群一次ポンプ[GJ]"]}')
print(f'設計一次エネルギー消費量 冷却塔ファン: {result_json_webpro["年間エネルギー消費量"]["熱源群冷却塔ファン[GJ]"]}')
print(f'設計一次エネルギー消費量 冷却水ポンプ: {result_json_webpro["年間エネルギー消費量"]["熱源群冷却水ポンプ[GJ]"]}')

# plt.show()
