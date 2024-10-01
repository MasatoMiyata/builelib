import json
import math
import os
from dataclasses import dataclass, field
from typing import Literal, List

template_directory = os.path.abspath(os.path.join(os.getcwd(), "../builelib/builelib/inputdata/"))

req = None
with open(template_directory + "/" + 'template.json', 'r', encoding='utf-8') as f:
    req = json.load(f)


@dataclass
class Room:
    is_air_conditioned: bool
    room_type: Literal[
        '事務室', '電子計算機器事務室', '会議室', '喫茶室', '社員食堂', '中央監視室', '更衣室又は倉庫', '廊下', 'ロビー', '便所', '喫煙室', '客室', '客室内の浴室等', '終日利用されるフロント', '終日利用される事務室', '終日利用される廊下', '終日利用されるロビー', '終日利用される共用部の便所', '終日利用される喫煙室', '宴会場', '会議室', '結婚式場', 'レストラン', 'ラウンジ', 'バー', '店舗', '社員食堂', '更衣室又は倉庫', '日中のみ利用されるフロント', '日中のみ利用される事務室', '日中のみ利用される廊下', '日中のみ利用されるロビー', '日中のみ利用される共用部の便所', '日中のみ利用される喫煙室', '病室', '浴室等', '看護職員室', '終日利用される廊下', '終日利用されるロビー', '終日利用される共用部の便所', '終日利用される喫煙室', '診察室', '待合室', '手術室', '検査室', '集中治療室', '解剖室等', 'レストラン', '事務室', '更衣室又は倉庫', '日中のみ利用される廊下', '日中のみ利用されるロビー', '日中のみ利用される共用部の便所', '日中のみ利用される喫煙室', '大型店の売場', '専門店の売場', 'スーパーマーケットの売場', '荷さばき場', '事務室', '更衣室又は倉庫', 'ロビー', '便所', '喫煙室', '小中学校の教室', '高等学校の教室', '職員室', '小中学校又は高等学校の食堂', '大学の教室', '大学の食堂', '事務室', '研究室', '電子計算機器演習室', '実験室', '実習室', '講堂又は体育館', '宿直室', '更衣室又は倉庫', '廊下', 'ロビー', '便所', '喫煙室', 'レストランの客室', '軽食店の客室', '喫茶店の客室', 'バー', 'フロント', '事務室', '更衣室又は倉庫', '廊下', 'ロビー', '便所', '喫煙室', 'アスレチック場の運動室', 'アスレチック場のロビー', 'アスレチック場の便所', 'アスレチック場の喫煙室', '公式競技用スケート場', '公式競技用体育館', '一般競技用スケート場', '一般競技用体育館', 'レクリエーション用スケート場', 'レクリエーション用体育館', '競技場の客席', '競技場のロビー', '競技場の便所', '競技場の喫煙室', '浴場施設の浴室', '浴場施設の脱衣所', '浴場施設の休憩室', '浴場施設のロビー', '浴場施設の便所', '浴場施設の喫煙室', '映画館の客席', '映画館のロビー', '映画館の便所', '映画館の喫煙室', '図書館の図書室', '図書館のロビー', '図書館の便所', '図書館の喫煙室', '博物館の展示室', '博物館のロビー', '博物館の便所', '博物館の喫煙室', '劇場の楽屋', '劇場の舞台', '劇場の客席', '劇場のロビー', '劇場の便所', '劇場の喫煙室', 'カラオケボックス', 'ボーリング場', 'ぱちんこ屋', '競馬場又は競輪場の客席', '競馬場又は競輪場の券売場', '競馬場又は競輪場の店舗', '競馬場又は競輪場のロビー', '競馬場又は競輪場の便所', '競馬場又は競輪場の喫煙室', '社寺の本殿', '社寺のロビー', '社寺の便所', '社寺の喫煙室', '屋内廊下', 'ロビー', '管理人室', '集会室']
    floor_height: float = field(init=False)
    ceiling_height: float = field(init=False)
    area: float = field(init=False)
    zone: str
    model_building_type: str = field(init=False)
    building_group: str
    info: str
    main_building_type: str = field(init=False)
    unit_name: str
    lighting_rated_power: int

    def __init__(self, is_air_conditioned, room_type, unit_name='天井埋込下面ルーバー', lighting_rated_power=0,
                 building_group=None, zone=None, info=None):
        self.is_air_conditioned = is_air_conditioned
        self.room_type = room_type
        self.unit_name = unit_name
        self.lighting_rated_power = lighting_rated_power
        self.building_group = building_group
        self.zone = zone
        self.info = info


@dataclass
class AreaByDirection:
    area: float
    direction: Literal['north', 'south', 'east', 'west']


@dataclass
class DHC:
    cooling: float
    heating: float

    def __init__(self, cooling=None, heating=None):
        self.cooling = cooling
        self.heating = heating


# todo: implement validation
@dataclass
class Building:
    name: str
    # please generate Japanese prefecture list
    prefecture: Literal['北海道', '青森県', '岩手県', '宮城県', '秋田県', '山形県', '福島県',
    '茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県',
    '新潟県', '富山県', '石川県', '福井県', '山梨県', '長野県', '岐阜県',
    '静岡県', '愛知県', '三重県', '滋賀県', '京都府', '大阪府', '兵庫県', '奈良県',
    '和歌山県', '鳥取県', '島根県', '岡山県', '広島県', '山口県',
    '徳島県', '香川県', '愛媛県', '高知県', '福岡県', '佐賀県', '長崎県',
    '熊本県', '大分県', '宮崎県', '鹿児島県', '沖縄県']
    city: str
    address: str
    region_number: int
    annual_solar_region: Literal['A1', 'A2', 'A3', 'A4', 'A5']
    building_floor_area: float = field(init=False)
    coefficient_dhc: DHC = field(init=False)


@dataclass
class BuilelibRequest:
    height: float
    rooms: List[Room]
    floor_number: int
    wall_u_value: float
    glass_u_value: float
    glass_solar_heat_gain_rate: float
    areas: List[AreaByDirection]
    window_ratio: float
    building_type: Literal['事務所等', 'ホテル等', '病院等', '物販店舗等', '学校等', '飲食店等', '集会所等', '共同住宅']
    model_building_type: Literal[
        '事務所モデル', 'ビジネスホテルモデル', 'シティホテルモデル', '総合病院モデル', 'クリニックモデル', '福祉施設モデル',
        '大規模物販モデル', '小規模物販モデル', '学校モデル', '幼稚園モデル', '大学モデル', '講堂モデル', '飲食店モデル', 'アスレチック',
        '体育館', '公衆浴場', '映画館', '図書館', '博物館', '劇場', 'カラオケボックス', 'ボーリング場', 'ぱちんこ屋', '競馬場又は競輪場',
        '社寺']
    lighting_number: int
    lighting_power: float
    elevator_number: int
    is_solar_power: bool
    building_information: Building
    # デフォルト値が設定されている変数
    inclination: int  # 建物の長手方向と真北方向の間の角度
    height_ground_wall: float  # 地面からの距離
    q_ref_rated_cool: int  # 熱源の定格冷却能力 703[kW/台]で2ユニット想定，これが熱源のパラメータになる
    q_ref_rated_heat: int
    primary_pump_power_consumption_total: float  # 熱源一次ポンプの消費電力トータル（ここも2台分）
    cooling_tower_fan_power_consumption_total: float  # 冷却塔ファンの消費電力トータル（ここも2台分）
    cooling_tower_pump_power_consumption_total: float  # 冷却塔ポンプの消費電力トータル（ここも2台分），冷却塔ファンの2倍の電力を仮定するでも
    cooling_tower_capacity_total: float
    temperature_difference: float  # ２次ポンプのパラメータ
    rated_water_flow_rate_total: float  # ２次ポンプのパラメータ
    rated_power_consumption_total: float  # ２次ポンプのパラメータ
    hot_water_rated_capacity: float
    hot_water_efficiency: float
    fan_air_volume: float
    motor_rated_power: float
    air_heat_exchange_rate_cooling: float
    air_heat_exchange_rate_heating: float
    # 自動で計算される変数
    width: float = field(init=False)
    length: float = field(init=False)
    floor_area: float = field(init=False)
    floor_height: float = field(init=False)
    floor_area_total: float = field(init=False)
    room_area_average: float = field(init=False)
    wall_area_north: float = field(init=False)
    ground_wall_area_north: float = field(init=False)
    window_area_north: float = field(init=False)
    wall_area_south: float = field(init=False)
    ground_wall_area_south: float = field(init=False)
    window_area_south: float = field(init=False)
    wall_area_east: float = field(init=False)
    ground_wall_area_east: float = field(init=False)
    window_area_east: float = field(init=False)
    wall_area_west: float = field(init=False)
    ground_wall_area_west: float = field(init=False)
    window_area_west: float = field(init=False)
    main_building_type: str = field(init=False)
    e_ref_cool: float = field(init=False)
    e_ref_sub_cool: float = field(init=False)
    e_ref_heat: float = field(init=False)
    e_ref_sub_heat: float = field(init=False)
    pv_power_conditioner_efficiency: float = field(init=False, default=0)
    pv_array_capacity: float = field(init=False, default=0)
    pv_angle: float = field(init=False, default=0)
    hot_water_rated_fuel_consumption: float = field(init=False)
    conditioned_room_number: int = field(init=False, default=0)

    def __init__(self, height, rooms, floor_number, wall_u_value, glass_u_value,
                 glass_solar_heat_gain_rate, areas, window_ratio, building_type, model_building_type, lighting_number,
                 lighting_power, elevator_number, is_solar_power, building_information,
                 air_heat_exchange_rate_cooling=52.0, air_heat_exchange_rate_heating=29.0, inclination=10,
                 height_ground_wall=1.0, q_ref_rated_cool=703 * 2, q_ref_rated_heat=588 * 2,
                 primary_pump_power_consumption_total=7.5 * 2,
                 cooling_tower_fan_power_consumption_total=7.5 * 2, cooling_tower_pump_power_consumption_total=15 * 2,
                 cooling_tower_capacity_total=1233 * 2, temperature_difference=5.0, rated_water_flow_rate_total=89.0,
                 rated_power_consumption_total=7.5, hot_water_rated_capacity=20.0, hot_water_efficiency=0.86,
                 fan_air_volume=2500, motor_rated_power=0.55):
        self.height = height
        self.rooms = rooms
        self.floor_number = floor_number
        self.wall_u_value = wall_u_value
        self.glass_u_value = glass_u_value
        self.glass_solar_heat_gain_rate = glass_solar_heat_gain_rate
        self.areas = areas
        self.window_ratio = window_ratio
        self.building_type = building_type
        self.model_building_type = model_building_type
        self.lighting_number = lighting_number
        self.lighting_power = lighting_power
        self.elevator_number = elevator_number
        self.is_solar_power = is_solar_power
        self.building_information = building_information
        self.inclination = inclination
        self.height_ground_wall = height_ground_wall
        self.q_ref_rated_cool = q_ref_rated_cool
        self.q_ref_rated_heat = q_ref_rated_heat
        self.primary_pump_power_consumption_total = primary_pump_power_consumption_total
        self.cooling_tower_fan_power_consumption_total = cooling_tower_fan_power_consumption_total
        self.cooling_tower_pump_power_consumption_total = cooling_tower_pump_power_consumption_total
        self.cooling_tower_capacity_total = cooling_tower_capacity_total
        self.temperature_difference = temperature_difference
        self.rated_water_flow_rate_total = rated_water_flow_rate_total
        self.rated_power_consumption_total = rated_power_consumption_total
        self.hot_water_rated_capacity = hot_water_rated_capacity
        self.hot_water_efficiency = hot_water_efficiency
        self.fan_air_volume = fan_air_volume
        self.motor_rated_power = motor_rated_power
        self.air_heat_exchange_rate_cooling = air_heat_exchange_rate_cooling
        self.air_heat_exchange_rate_heating = air_heat_exchange_rate_heating

    def get_all_wall_area(self):
        return self.wall_area_north + self.wall_area_south + self.wall_area_east + self.wall_area_west

    def get_all_ground_wall_area(self):
        return self.ground_wall_area_north + self.ground_wall_area_south + self.ground_wall_area_east \
            + self.ground_wall_area_west

    def get_all_window_area(self):
        return self.window_area_north + self.window_area_south + self.window_area_east + self.window_area_west

    def insert_default(self):
        # define as default values
        for area in self.areas:
            # Assume that north and south are the same, and east and west are the same
            if area.direction == 'north':
                w_ = area.area / self.height
            elif area.direction == 'east':
                l_ = area.area / self.height
        # Define as width = longer side, length = shorter side
        if w_ > l_:
            self.width = w_
            self.length = l_
        else:
            self.width = l_
            self.length = w_

        self.floor_area = self.width * self.length
        self.floor_height = self.height / self.floor_number
        self.floor_area_total = self.floor_area * self.floor_number
        self.room_area_average = self.floor_area_total / len(self.rooms)
        for area in self.areas:
            if area.direction == 'north':
                self.wall_area_north = (self.height - self.height_ground_wall) * (
                        self.width * math.cos(self.inclination * math.pi / 180) + self.length * math.sin(
                    self.inclination * math.pi / 180))
                self.ground_wall_area_north = self.height_ground_wall * (
                        self.width * math.cos(self.inclination * math.pi / 180) + self.length * math.sin(
                    self.inclination * math.pi / 180))
                self.window_area_north = self.wall_area_north * self.window_ratio
            elif area.direction == 'south':
                self.wall_area_south = self.wall_area_north
                self.ground_wall_area_south = self.ground_wall_area_north
                self.window_area_south = self.window_area_north
            elif area.direction == 'east':
                self.wall_area_east = (self.height - self.height_ground_wall) * (
                        self.width * math.sin(self.inclination * math.pi / 180) + self.length * math.cos(
                    self.inclination * math.pi / 180))
                self.ground_wall_area_east = self.height_ground_wall * (
                        self.width * math.sin(self.inclination * math.pi / 180) + self.length * math.cos(
                    self.inclination * math.pi / 180))
                self.window_area_east = self.wall_area_east * self.window_ratio
            elif area.direction == 'west':
                self.wall_area_west = self.wall_area_east
                self.ground_wall_area_west = self.ground_wall_area_east
                self.window_area_west = self.window_area_east
            else:
                raise ValueError('Invalid direction')

        for i in range(len(self.rooms)):
            self.rooms[i].main_building_type = self.building_type
            self.rooms[i].model_building_type = self.model_building_type
            self.rooms[i].floor_height = self.floor_height
            self.rooms[i].ceiling_height = self.floor_height
            self.rooms[i].area = self.room_area_average
            self.rooms[i].unit_name = "天井埋込下面ルーバー"
            self.rooms[i].lighting_rated_power = self.lighting_power * self.lighting_number
            if self.rooms[i].is_air_conditioned:
                self.conditioned_room_number += 1

        self.e_ref_cool = self.q_ref_rated_cool  # 熱源の消費エネルギー，冷却は定格能力と同じと仮定
        self.e_ref_sub_cool = self.e_ref_cool * 0.01  # 熱源補機の消費エネルギー（これはErefの1%でいいんでない？）
        self.e_ref_heat = self.q_ref_rated_heat * 1.5  # 散逸があるので定格能力の1.5倍
        self.e_ref_sub_heat = self.e_ref_heat * 0.01
        self.hot_water_rated_fuel_consumption = self.hot_water_rated_capacity / self.hot_water_efficiency

        if self.is_solar_power:
            self.pv_power_conditioner_efficiency = 0.94
            self.pv_array_capacity = 12.2
            self.pv_angle = 30.0

        self.building_information.building_floor_area = self.floor_area_total
        self.building_information.coefficient_dhc = DHC()

    def create_default_json_file(self):
        self.insert_default()
        # 建物基本情報
        req["building"] = {
            "name": self.building_information.name,
            "building_address": {
                "prefecture": self.building_information.prefecture,
                "city": self.building_information.city,
                "address": self.building_information.address,
            },
            "region": str(self.building_information.region_number),
            "annual_solar_region": self.building_information.annual_solar_region,
            "building_floor_area": self.floor_area_total,
            "coefficient_dhc": {
                "cooling": self.building_information.coefficient_dhc.cooling,
                "heating": self.building_information.coefficient_dhc.heating
            }
        }

        # 様式1 室仕様入力シート相当の箇所
        for i in range(len(self.rooms)):
            req["rooms"][i] = {
                "main_building_type": self.rooms[i].main_building_type,
                "building_type": self.rooms[i].model_building_type,
                "room_type": self.rooms[i].room_type,
                "floor_height": self.rooms[i].floor_height,
                "ceiling_height": self.rooms[i].ceiling_height,  # 現状，階高と天井高を同じで計算
                "room_area": self.rooms[i].area,
                "zone": self.rooms[i].zone,
                "model_building_type": self.rooms[i].model_building_type,
                "building_group": self.rooms[i].building_group,
                "info": self.rooms[i].info,
            }

        # 様式2-2 外壁構成入力シート の読み込み相当の箇所
        req["wall_configure"]["W"] = {
            "wall_type_webpro": "外壁",
            "structure_type": "その他",
            "solar_absorption_ratio": None,
            "input_method": "熱貫流率を入力",
            "u_value": self.wall_u_value,
            "info": None,
        }

        req["wall_configure"]["FG1"] = {
            "wall_type_webpro": "接地壁",
            "structure_type": "その他",
            "solar_absorption_ratio": None,
            "input_method": "建材構成を入力",
            "layers": [
                {
                    "material_id": "ビニル系床材",
                    "conductivity": None,
                    "thickness": 3.0,
                    "info": None,
                },
                {
                    "material_id": "セメント・モルタル",
                    "conductivity": None,
                    "thickness": 27.0,
                    "info": None,
                },
                {
                    "material_id": "コンクリート",
                    "conductivity": None,
                    "thickness": 150.0,
                    "info": None,
                },
                {
                    "material_id": "土壌",
                    "conductivity": None,
                    "thickness": 0.0,
                    "info": None,
                }
            ]
        }

        # 様式2-3 窓仕様入力シート の読み込み相当の箇所,現在はサッシは金属木複合製とする
        req["window_configure"]["G"] = {
            "window_area": 1,
            "window_width": None,
            "window_height": None,
            "input_method": "ガラスの性能を入力",
            "frame_type": "金属木複合製",
            "layer_type": "単層",
            "glassu_value": self.glass_u_value,
            "glassi_value": self.glass_solar_heat_gain_rate,
            "info": None,
        }

        req["ventilation_unit"]["EF"] = {
            "number": 1,
            "fan_air_volume": self.fan_air_volume,
            "motor_rated_power": self.motor_rated_power,
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

        req["ventilation_unit"]["SF"] = {
            "number": 1,
            "fan_air_volume": self.fan_air_volume,
            "motor_rated_power": self.motor_rated_power,
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

        req["hot_water_supply_systems"]["EB"] = {
            "heat_sourceUnit": [{
                "usage_type": "給湯負荷用",
                "heat_source_type": "ガス給湯機",
                "number": 1,
                "rated_capacity": self.hot_water_rated_capacity,
                "rated_power_consumption": 0,
                "rated_fuel_consumption": self.hot_water_rated_fuel_consumption,
            }],
            "insulation_type": "保温仕様2",
            "pipe_size": 40.0,
            "solar_system_area": None,
            "solar_system_direction": None,
            "solar_system_angle": None,
            "info": None
        }

        for i in range(len(self.rooms)):
            room = self.rooms[i]

            req["envelope_set"][i] = {
                "is_airconditioned": room.is_air_conditioned,
                "wall_list": [
                    {
                        "direction": "北",
                        "envelope_area": self.wall_area_north / len(self.rooms),
                        "envelope_width": None,
                        "envelope_height": None,
                        "wall_spec": "W",
                        "wall_type": "日の当たる外壁",
                        "window_list": [{
                            "window_id": "G",
                            "window_number": self.window_area_north / len(self.rooms),
                            "is_blind": "無",
                            "eaves_id": "無",
                            "info": None,
                        }]
                    },
                    {
                        "direction": "北",
                        "envelope_area": self.ground_wall_area_north / len(self.rooms),
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
                        "envelope_area": self.wall_area_east / len(self.rooms),
                        "envelope_width": None,
                        "envelope_height": None,
                        "wall_spec": "W",
                        "wall_type": "日の当たる外壁",
                        "window_list": [{
                            "window_id": "G",
                            "window_number": self.window_area_east / len(self.rooms),
                            "is_blind": "無",
                            "eaves_id": "無",
                            "info": None,
                        }]
                    },
                    {
                        "direction": "東",
                        "envelope_area": self.ground_wall_area_east / len(self.rooms),
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
                        "envelope_area": self.wall_area_west / len(self.rooms),
                        "envelope_width": None,
                        "envelope_height": None,
                        "wall_spec": "W",
                        "wall_type": "日の当たる外壁",
                        "window_list": [{
                            "window_id": "G",
                            "window_number": self.window_area_west / len(self.rooms),
                            "is_blind": "無",
                            "eaves_id": "無",
                            "info": None,
                        }]
                    },
                    {
                        "direction": "西",
                        "envelope_area": self.ground_wall_area_west / len(self.rooms),
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
                        "envelope_area": self.wall_area_south / len(self.rooms),
                        "envelope_width": None,
                        "envelope_height": None,
                        "wall_spec": "W",
                        "wall_type": "日の当たる外壁",
                        "window_list": [{
                            "window_id": "G",
                            "window_number": self.window_area_south / len(self.rooms),
                            "is_blind": "無",
                            "eaves_id": "無",
                            "info": None,
                        }]
                    },
                    {
                        "direction": "南",
                        "envelope_area": self.ground_wall_area_south / len(self.rooms),
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

            if room.is_air_conditioned:
                req["air_conditioning_zone"][i] = {
                    "is_natual_ventilation": "無",
                    "is_simultaneous_supply": "無",
                    "ahu_cooling_inside_load": "HU",
                    "ahu_cooling_outdoor_load": "HU",
                    "ahu_heating_inside_load": "HU",
                    "ahu_heating_outdoor_load": "HU",
                    "info": None,
                }
                req["ventilation_room"][i] = {
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
                req["lighting_systems"][i] = {
                    "room_width": math.sqrt(room.area * self.conditioned_room_number / len(self.rooms)),
                    "room_depth": math.sqrt(room.area * self.conditioned_room_number / len(self.rooms)),
                    "unit_height": room.floor_height,
                    "room_index": None,
                    "lighting_unit": {
                        room.unit_name: {
                            "rated_power": room.lighting_rated_power,
                            "number": 1,
                            "occupant_sensing_ctrl": "無",
                            "illuminance_sensing_ctrl": "無",
                            "time_schedule_ctrl": "無",
                            "initial_illumination_correction_ctrl": "無",
                        }
                    }
                }

                req["hot_water_room"][i] = {
                    "hot_water_system": [{
                        "usage_type": None,
                        "system_name": "EB",
                        "hot_water_saving_system": "無",
                        "info": None
                    }]
                }

        # 様式6 昇降機入力シート の読み込み相当の箇所
        for i in range(self.elevator_number):
            req["elevators"][i] = {
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

        if self.is_solar_power:
            req["photovoltaic_systems"]["PV"] = {
                "power_conditioner_efficiency": self.pv_power_conditioner_efficiency,
                "cell_type": "結晶系",
                "array_setup_type": "架台設置形",
                "array_capacity": self.pv_array_capacity,
                "direction": 0.0,
                "angle": self.pv_angle,
                "info": "0.94"
            }

        req["cogeneration_systems"]["CGS"] = {
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
                                           'heat_source_rated_capacity': self.q_ref_rated_cool,
                                           'heat_source_rated_power_consumption': 0,
                                           'heat_source_rated_fuel_consumption': self.e_ref_cool,
                                           'heat_source_sub_rated_power_consumption': self.e_ref_sub_cool,
                                           'primary_pump_power_consumption': self.primary_pump_power_consumption_total,
                                           'primary_pump_control_type': '無',
                                           'cooling_tower_capacity': self.cooling_tower_capacity_total,
                                           'cooling_tower_fan_power_consumption': self.cooling_tower_fan_power_consumption_total,
                                           'cooling_tower_pump_power_consumption': self.cooling_tower_pump_power_consumption_total,
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
                                           'heat_source_rated_capacity': self.q_ref_rated_heat,
                                           'heat_source_rated_power_consumption': 0,
                                           'heat_source_rated_fuel_consumption': self.e_ref_heat,
                                           'heat_source_sub_rated_power_consumption': self.e_ref_sub_heat,
                                           'primary_pump_power_consumption': self.primary_pump_power_consumption_total,
                                           'primary_pump_control_type': '無',
                                           'cooling_tower_capacity': 0,
                                           'cooling_tower_fan_power_consumption': self.cooling_tower_fan_power_consumption_total,
                                           'cooling_tower_pump_power_consumption': self.cooling_tower_pump_power_consumption_total,
                                           'cooling_tower_control_type': '無',
                                           'info': None}]
                          }
        req["heat_source_system"]["AR"] = {
            "冷房": unit_spec_cool,
            "暖房": unit_spec_heat
        }
        req["air_handling_system"]["HU"] = {
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
                "rated_capacity_cooling": self.air_heat_exchange_rate_cooling,
                "rated_capacity_heating": self.air_heat_exchange_rate_heating,
                "fan_type": None,
                "fan_air_volume": None,
                "fan_power_consumption": self.air_heat_exchange_rate_cooling / 10,  # 送風機定格消費電力の和（冷却能力の10%で近似）
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

        return req
