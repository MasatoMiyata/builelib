from heat_load_calculation import Main
import json

# ファイルの読み込み
with open('input_non_residential.json', 'r', encoding='utf-8') as js:
    d = json.load(js)

# 実行
heatload_sensible_convection, heatload_sensible_radiation, heatload_latent = Main.run(d)

# 熱負荷の単純合計
total_heat_load = sum(heatload_sensible_convection+heatload_sensible_radiation+heatload_latent)
print(f'熱負荷の単純合計値 [MWh] {total_heat_load/1000}')