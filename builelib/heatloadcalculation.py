import json

from heat_load_calculation import Main

# ファイルの読み込み
with open('input_non_residential.json', 'r', encoding='utf-8') as js:
    d = json.load(js)

# 実行
heat_load_sensible_convection, heat_load_sensible_radiation, heat_load_latent = Main.run(d)

# 熱負荷の単純合計
total_heat_load = sum(heat_load_sensible_convection + heat_load_sensible_radiation + heat_load_latent)
print(f'熱負荷の単純合計値 [MWh] {total_heat_load / 1000}')
