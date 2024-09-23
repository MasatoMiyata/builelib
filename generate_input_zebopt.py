# generate_input.py
import math
import os
import json

template_directory = os.getcwd() + "/builelib/inputdata/"

height = 20
width = 40
length = 40
room_number = 2
room_AC_number = 2
floor_number = 2
floor_area = width * length
wall_u_value = 0.5
glass_u_value = 0.5
glass_eta_value = 3
theta = 10
height_ground_wall = 1.0
floor_area_tot = floor_area * floor_number
floor_height = height / floor_number
room_area_ave = floor_area_tot / room_number
window_ratio = 0.2

wall_area_north = (height - height_ground_wall) * (width * math.cos(theta * math.pi / 180) + length * math.sin(theta * math.pi / 180))
wall_area_west = (height - height_ground_wall) * (width * math.sin(theta * math.pi / 180) + length * math.cos(theta * math.pi / 180))
wall_area_east = wall_area_west
wall_area_south = wall_area_north
wall_area_roof = floor_area
ground_wall_area_north = height_ground_wall * (width * math.cos(theta * math.pi / 180) + length * math.sin(theta * math.pi / 180))
ground_wall_area_west = height_ground_wall * (width * math.sin(theta * math.pi / 180) + length * math.cos(theta * math.pi / 180))
ground_wall_area_east = ground_wall_area_west
ground_wall_area_south = ground_wall_area_north
wall_area_tot = (wall_area_north + wall_area_west + wall_area_east + wall_area_south) * (1 - window_ratio)
window_area_tot = wall_area_tot * window_ratio
window_area_north = wall_area_north * window_ratio
window_area_west = wall_area_west * window_ratio
window_area_east = wall_area_east * window_ratio
window_area_south = wall_area_south * window_ratio

main_building_type = "事務所等"
building_type = "事務所等"
room_type = "事務室"
model_building_type = "事務所モデル"
#熱源のパラメータ
Qref_rated_cool = 703 * 2 #熱源の定格冷却能力 703[kW/台]で2ユニット想定，これが熱源のパラメータになる
Qref_rated_heat = 588 * 2
Eref_cool = Qref_rated_cool #熱源の消費エネルギー，冷却は定格能力と同じと仮定
Eref_heat = Qref_rated_heat * 1.5 #散逸があるので定格能力の1.5倍
Eref_sub_cool = Eref_cool * 0.01 #熱源補機の消費エネルギー（これはErefの1%でいいんでない？）
Eref_sub_heat = Eref_heat * 0.01
PrimaryPumpPowerConsumption_total = 7.5 * 2 #熱源一次ポンプの消費電力トータル（ここも2台分）
CoolingTowerFanPowerConsumption_total = 7.5 * 2 #冷却塔ファンの消費電力トータル（ここも2台分）
CoolingTowerPumpPowerConsumption_total = 15 * 2 #冷却塔ポンプの消費電力トータル（ここも2台分），冷却塔ファンの2倍の電力を仮定するでも
CoolingTowerCapacity_total = 1233 * 2
#２次ポンプのパラメータ
TemperatureDifference = 5.0
RatedWaterFlowRate_total = 89.0
RatedPowerConsumption_total = 7.5
#代表的空調機のパラメータ
AirHeatExchangeRateCooling = 52 #定格冷却能力 [kW/台]，今は1台を想定
AirHeatExchangeRateHeating = 29 #定格冷却能力 [kW/台]，今は1台を想定
#代表的換気送風機パラメータ(給気も排気もとりあえず同じ値)
Fan_air_volume = 2500
Motor_rated_power = 0.55
#代表的照明パラメータ
Unit_name = "天井埋込下面ルーバー"
Lighting_rated_power = 88 * 55
#代表的給湯設備パラメータ
Hot_water_rated_capacity = 20.0
Hot_water_efficiency = 0.86
Hot_water_rated_fuel_consumption = Hot_water_rated_capacity / Hot_water_efficiency
#太陽光発電パラメータ
PV_power_conditioner_efficiency = 0.94
PV_array_capacity = 12.2
PV_angle = 30.0

with open(template_directory + 'template.json', 'r', encoding='utf-8') as f:
    data_web = json.load(f)

# 様式0 基本情報入力シート相当の箇所
# BL-1	建築物の名称
data_web["building"]["name"] = "国立明石工業高等専門学校"
# BL-2	都道府県 (選択)
data_web["building"]["building_address"]["prefecture"] = "兵庫県"
# BL-3	建築物所在地 市区町村 (選択)
data_web["building"]["building_address"]["city"] = "明石市"
# BL-4	丁目、番地等
data_web["building"]["building_address"]["address"] = "兵庫県明石市魚住町西岡 679-3"
# BL-5	地域の区分	(自動)
data_web["building"]["region"] = "6"
# BL-6	年間日射地域区分 (自動)
data_web["building"]["annual_solar_region"] = "A3"
# BL-7	延べ面積  [㎡]	(数値)
data_web["building"]["building_floor_area"] = floor_area_tot
# BL-8	「他人から供給された熱」	冷熱	(数値)
# BL-9	の一次エネルギー換算係数	温熱	(数値)
data_web["building"]["coefficient_dhc"]["cooling"] = None #今は燃料が電力であると仮定しているので他人から〜は不要
data_web["building"]["coefficient_dhc"]["heating"] = None

# 様式1 室仕様入力シート相当の箇所
for i in range(room_number):
    data_web["rooms"][i] = {
        "main_building_type": main_building_type,
        "building_type": building_type,
        "room_type": room_type,
        "floor_height": floor_height,
        "ceiling_height": floor_height, #現状，階高と天井高を同じで計算
        "room_area": room_area_ave,
        "zone": None,
        "model_building_type": model_building_type,
        "building_group": None,
        "info": None,
    }

# 様式2-1 空調ゾーン入力シート の読み込み相当の箇所，仮想的かつ代表的な空調ユニットHUに全ての空調室の負荷を押し付ける
for i in range(room_AC_number):
    data_web["air_conditioning_zone"][i] = {
        "is_natual_ventilation": "無",
        "is_simultaneous_supply": "無",
        "ahu_cooling_inside_load": "HU",
        "ahu_cooling_outdoor_load": "HU",
        "ahu_heating_inside_load": "HU",
        "ahu_heating_outdoor_load": "HU",
        "info": None,
    }

# 様式2-2 外壁構成入力シート の読み込み相当の箇所
data_web["wall_configure"]["W"] = {
    "wall_type_webpro": "外壁",
    "structure_type": "その他",
    "solar_absorption_ratio": None,
    "input_method": "熱貫流率を入力",
    "u_value": wall_u_value,
    "info": None,
}

data_web["wall_configure"]["FG1"] = {
    "wall_type_webpro": "接地壁",
    "structure_type": "その他",
    "solar_absorption_ratio": None,
    "input_method": "建材構成を入力",
    "layers": [
        {"material_id": "ビニル系床材",
        "conductivity": None,
        "thickness": 3.0,
        "info": None,},
        {"material_id": "セメント・モルタル",
        "conductivity": None,
        "thickness": 27.0,
        "info": None,},
        {"material_id": "コンクリート",
        "conductivity": None,
        "thickness": 150.0,
        "info": None,},
        {"material_id": "土壌",
        "conductivity": None,
        "thickness": 0.0,
        "info": None,}
        ]
}

# 様式2-3 窓仕様入力シート の読み込み相当の箇所,現在はサッシは金属木複合製とする
data_web["window_configure"]["G"] = {
                        "window_area": 1,
                        "window_width": None,
                        "window_height": None,
                        "input_method": "ガラスの性能を入力",
                        "frame_type": "金属木複合製",
                        "layer_type": "単層",
                        "glassu_value": glass_u_value,
                        "glassi_value":glass_eta_value,
                        "info": None,
                    }

# 様式2-4 外皮入力シート の読み込み相当の箇所，現在，日陰，ブラインドは考慮していない
for i in range(room_AC_number):
    data_web["envelope_set"][i] = {
        "is_airconditioned": "有",
        "wall_list": [
        {
            "direction": "北",
            "envelope_area": wall_area_north/room_AC_number,
            "envelope_width": None,
            "envelope_height": None,
            "wall_spec": "W",
            "wall_type": "日の当たる外壁",
            "window_list": [{
                "window_id": "G",
                "window_number": window_area_north/room_AC_number,
                "is_blind": "無",
                "eaves_id": "無",
                "info": None,
            }]
        },
        {
            "direction": "北",
            "envelope_area": ground_wall_area_north/room_AC_number,
            "envelope_width": None,
            "envelope_height": None,
            "wall_spec": "FG1",
            "wall_type": "地盤に接する外壁",
            "window_list": [{
                "window_id": "無",
                "window_number": None,
                "is_blind": "無",
                "eaves_id": "無",
                "info": None,
            }]
        },
        {
            "direction": "東",
            "envelope_area": wall_area_east/room_AC_number,
            "envelope_width": None,
            "envelope_height": None,
            "wall_spec": "W",
            "wall_type": "日の当たる外壁",
            "window_list": [{
                "window_id": "G",
                "window_number": window_area_east/room_AC_number,
                "is_blind": "無",
                "eaves_id": "無",
                "info": None,
            }]
        },
        {
            "direction": "東",
            "envelope_area": ground_wall_area_east/room_AC_number,
            "envelope_width": None,
            "envelope_height": None,
            "wall_spec": "FG1",
            "wall_type": "地盤に接する外壁",
            "window_list": [{
                "window_id": "無",
                "window_number": None,
                "is_blind": "無",
                "eaves_id": "無",
                "info": None,
            }]
        },
        {
            "direction": "西",
            "envelope_area": wall_area_west/room_AC_number,
            "envelope_width": None,
            "envelope_height": None,
            "wall_spec": "W",
            "wall_type": "日の当たる外壁",
            "window_list": [{
                "window_id": "G",
                "window_number": window_area_west/room_AC_number,
                "is_blind": "無",
                "eaves_id": "無",
                "info": None,
            }]
        },
        {
            "direction": "西",
            "envelope_area": ground_wall_area_west/room_AC_number,
            "envelope_width": None,
            "envelope_height": None,
            "wall_spec": "FG1",
            "wall_type": "地盤に接する外壁",
            "window_list": [{
                "window_id": "無",
                "window_number": None,
                "is_blind": "無",
                "eaves_id": "無",
                "info": None,
            }]
        },
        {
            "direction": "南",
            "envelope_area": wall_area_south/room_AC_number,
            "envelope_width": None,
            "envelope_height": None,
            "wall_spec": "W",
            "wall_type": "日の当たる外壁",
            "window_list": [{
                "window_id": "G",
                "window_number": window_area_south/room_AC_number,
                "is_blind": "無",
                "eaves_id": "無",
                "info": None,
            }]
        },
        {
            "direction": "南",
            "envelope_area": ground_wall_area_south/room_AC_number,
            "envelope_width": None,
            "envelope_height": None,
            "wall_spec": "FG1",
            "wall_type": "地盤に接する外壁",
            "window_list": [{
                "window_id": "無",
                "window_number": None,
                "is_blind": "無",
                "eaves_id": "無",
                "info": None,
            }]
        },
        ]
    }

# 様式2-5 熱源入力シート の読み込みに相当する箇所
unit_spec_cool = {'storage_type': None,
            'storage_size': None,
            'is_staging_control': '有',
            'is_simultaneous_for_ver2': '無',
            'heat_source': [{'heat_source_type': '吸収式冷凍機(一重二重併用形、都市ガス)',
                            'number': 1.0,
                            'supply_water_temp_summer': 7.0,
                            'supply_water_temp_middle': 7.0,
                            'supply_water_temp_winter': 7.0,
                            'heat_source_rated_capacity': Qref_rated_cool,
                            'heat_source_rated_power_consumption': 0,
                            'heat_source_rated_fuel_consumption': Eref_cool,
                            'heat_source_sub_rated_power_consumption': Eref_sub_cool,
                            'primary_pump_power_consumption': PrimaryPumpPowerConsumption_total,
                            'primary_pump_control_type': '無',
                            'cooling_tower_capacity': CoolingTowerCapacity_total,
                            'cooling_tower_fan_power_consumption': CoolingTowerFanPowerConsumption_total,
                            'cooling_tower_pump_power_consumption': CoolingTowerPumpPowerConsumption_total,
                            'cooling_tower_control_type': '無',
                            'info': None}]
            }

unit_spec_heat = {'storage_type': None,
            'storage_size': None,
            'is_staging_control': '有',
            'is_simultaneous_for_ver2': '無',
            'heat_source': [{'heat_source_type': '吸収式冷凍機(一重二重併用形、都市ガス)',
                            'number': 1.0,
                            'supply_water_temp_summer': 55.0,
                            'supply_water_temp_middle': 55.0,
                            'supply_water_temp_winter': 55.0,
                            'heat_source_rated_capacity': Qref_rated_heat,
                            'heat_source_rated_power_consumption': 0,
                            'heat_source_rated_fuel_consumption': Eref_heat,
                            'heat_source_sub_rated_power_consumption': Eref_sub_heat,
                            'primary_pump_power_consumption': PrimaryPumpPowerConsumption_total,
                            'primary_pump_control_type': '無',
                            'cooling_tower_capacity': 0,
                            'cooling_tower_fan_power_consumption': 0,
                            'cooling_tower_pump_power_consumption': 0,
                            'cooling_tower_control_type': '無',
                            'info': None}]
            }

data_web["heat_source_system"]["AR"] = {
    "冷房": unit_spec_cool,
    "暖房": unit_spec_heat
}

# 様式2-6 二次ポンプ入力シート の読み込み相当の箇所
unit_spec_secondary = {
    "temperature_difference": TemperatureDifference,
    "is_staging_control": "有",
    "secondary_pump": [
        {
            "number": 1.0,
            "rated_water_flow_rate": RatedWaterFlowRate_total,
            "rated_power_consumption": RatedPowerConsumption_total,
            "control_type": "定流量制御",
            "min_opening_rate": None,
            "info": None,
        }
    ]
}
data_web["secondary_pump_system"]["CHP"] = {
    "冷房": unit_spec_secondary,
    "暖房": unit_spec_secondary
}

# 様式2-7 空調機入力シート の読み込み相当の箇所
data_web["air_handling_system"]["HU"] = {
    "is_economizer": "無",
    "economizer_max_air_volume": None,
    "is_outdoor_air_cut": "無",
    "pump_cooling": "CHP",
    "pump_heating": "CHP",
    "heat_source_cooling": "AR",
    "heat_source_heating": "AR",
    "air_handling_unit": [{
        "type": "空調機",
        "number": 1.0,
        "rated_capacity_cooling": AirHeatExchangeRateCooling,
        "rated_capacity_heating": AirHeatExchangeRateHeating,
        "fan_type": None,
        "fan_air_volume": None,
        "fan_power_consumption": AirHeatExchangeRateCooling / 10, #送風機定格消費電力の和（冷却能力の10%で近似）
        "fan_control_type": "定風量制御",
        "fan_min_opening_rate": None,
        "air_heat_exchange_ratio_cooling": None,
        "air_heat_exchange_ratio_heating": None,
        "air_heat_exchanger_effective_air_volume_ratio": None,
        "air_heat_exchanger_control": "無",
        "air_heat_exchanger_power_consumption": None,
        "info": None,
        "is_air_heat_exchanger": "全熱交換器なし",
        "air_heat_exchanger_name": "無"
        }]
    }

# 様式3-1 換気対象室入力シート の読み込み相当の箇所（空調室の給排気だけ考える）
for i in range(room_AC_number):
    data_web["ventilation_room"][i] = {
        "ventilation_type": None,
        "ventilation_unit_ref": {
            "EF": {
                "unit_type": "排気",
                "info": ""
            },
            "SF": {
                "unit_type": "給気",
                "info": ""
            }
        }
    }

data_web["ventilation_unit"]["EF"] = {
    "number": 1,
    "fan_air_volume": Fan_air_volume,
    "motor_rated_power": Motor_rated_power,
    "power_consumption": None,
    "high_efficiency_motor": "無",
    "inverter": "無",
    "air_volume_control": "無",
    "ventilation_room_type": None,
    "ac_cooling_capacity": None,
    "ac_ref_efficiency": None,
    "ac_pump_power": None,
    "info": "無"
    }
data_web["ventilation_unit"]["SF"] = {
    "number": 1,
    "fan_air_volume": Fan_air_volume,
    "motor_rated_power": Motor_rated_power,
    "power_consumption": None,
    "high_efficiency_motor": "無",
    "inverter": "無",
    "air_volume_control": "無",
    "ventilation_room_type": None,
    "ac_cooling_capacity": None,
    "ac_ref_efficiency": None,
    "ac_pump_power": None,
    "info": "無"
    }

# 様式3-3 換気代替空調機入力シート の読み込みはスキップ
# 様式4 照明入力シート の読み込み相当の箇所（空調対象室だけ照明を考えるとする）
for i in range(room_AC_number):
    data_web["lighting_systems"][i] = {
        "room_width": math.sqrt(room_area_ave * room_AC_number / room_number),
        "room_depth": math.sqrt(room_area_ave * room_AC_number / room_number),
        "unit_height": floor_height,
        "room_index": None,
        "lighting_unit": {
            Unit_name: {
                "rated_power": Lighting_rated_power,
                "number": 1, #擬似的に1, rated_powerに押し込める
                "occupant_sensing_ctrl": "無",
                "illuminance_sensing_ctrl": "無",
                "time_schedule_ctrl": "無",
                "initial_illumination_correction_ctrl": "無",
                        }
                    }
                }

# 様式5-1 給湯対象室入力シート の読み込み相当の箇所（ここでは給湯室の寄与のみ考える，便所の消費はほぼない）
for i in range(room_AC_number):
    data_web["hot_water_room"][i] = {
        "hot_water_system": [{
            "usage_type": None,
            "system_name": "EB",
            "hot_water_saving_system": "無",
            "info": None
            }]
            }

# 様式5-2 給湯機器入力シート の読み込み相当の箇所
data_web["hot_water_supply_systems"]["EB"] = {
    "heat_sourceUnit": [{
        "usage_type": "給湯負荷用",
        "heat_source_type": "ガス給湯機",
        "number": 1,
        "rated_capacity": Hot_water_rated_capacity,
        "rated_power_consumption": 0,
        "rated_fuel_consumption": Hot_water_rated_fuel_consumption,
        }],
    "insulation_type": "保温仕様2",
    "pipe_size": 40.0,
    "solar_system_area": None,
    "solar_system_direction": None,
    "solar_system_angle": None,
    "info":None
}

# 様式6 昇降機入力シート の読み込み相当の箇所
for i in range(room_AC_number):
    data_web["elevators"][i] = {
        "elevator": [{
            "elevator_name": "常用",
            "number": 1.0,
            "load_limit": 800.0,
            "velocity": 60.0,
            "transport_capacity_factor": 1.0,
            "control_type": "VVVF(電力回生なし)",
            "info": None
            }]
            }

# 様式7-1 太陽光発電入力シート の読み込み相当の箇所
data_web["photovoltaic_systems"]["PV"] = {
    "power_conditioner_efficiency": PV_power_conditioner_efficiency,
    "cell_type": "結晶系",
    "array_setup_type": "架台設置形",
    "array_capacity": PV_array_capacity,
    "direction": 0.0,
    "angle": PV_angle,
    "info": "0.94"
    }

# 様式7-3 コジェネ入力シート の読み込み相当の箇所
data_web["cogeneration_systems"]["CGS"] = {
    "rated_capacity": 370.0,
    "number": 1.0,
    "power_generation_efficiency_100": 0.405,
    "power_generation_efficiency_75": 0.39,
    "power_generation_efficiency_50": 0.349,
    "heat_generation_efficiency_100": 0.332,
    "heat_generation_efficiency_75": 0.337,
    "heat_generation_efficiency_50": 0.369,
    "heat_recovery_priority_cooling": "3番目",
    "heat_recovery_priority_heating": "2番目",
    "heat_recovery_priority_hot_water": "1番目",
    "24hourOperation": "無",
    "cooling_system": "AR",
    "heating_system": "AR",
    "hot_water_system": "EB",
    "info": None
    }

# json.dump用のクラス
class MyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        elif isinstance(obj, set):
            return list(obj)
        else:
            return super(MyEncoder, self).default(obj)

with open('input_zebopt.json', 'w', encoding='utf-8') as f:
    json.dump(data_web, f, ensure_ascii=False, indent=4, cls=MyEncoder)
