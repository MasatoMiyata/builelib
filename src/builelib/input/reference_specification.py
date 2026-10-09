"""Excel・JSONに共通する「基準設定仕様」の展開と検証"""

import copy
from functools import lru_cache
import json
import math
from pathlib import Path

from builelib import commons as bc


# Excelの機器名称にこの文字があると、自動生成の要求として読み取る。
REFERENCE_MARKER = "基準設定仕様"

# 中間JSONでは、生成したい設備をこの配列に1件ずつ記録する。
# 計算に渡す完成JSONからは、この配列を取り除く。
REQUESTS_KEY = "ReferenceSpecificationRequests"

# 基準設定仕様データベース（JSONファイル）
_DATABASE_PATH = Path(__file__).resolve().parents[1] / "database" / "common_reference_specification.json"
_LIGHTING_POWER_KEY = "基準設定消費電力 [W/m2]"
_REQUEST_FIELDS = {
    "照明": {"room"},
    "外壁": {"zone", "wallIndex"},
    "窓": {"zone", "wallIndex", "windowIndex"},
    "換気": {"room", "unitType", "info"},
    "給湯": {"room", "systemIndex", "savingSystem", "info"},
    "昇降機": {"room", "elevatorIndex"},
}


class ReferenceSpecificationError(ValueError):
    """該当する基準設定仕様を適用できないときに知らせるエラー。"""


@lru_cache(maxsize=1)
def _load_database():
    """基準設定仕様のJSONを読み込む。同じ実行中は読み込み結果を再利用する。"""
    try:
        with _DATABASE_PATH.open(encoding="utf-8") as source:
            return json.load(source)
    except (OSError, ValueError) as exc:
        raise ReferenceSpecificationError(f"基準設定仕様データベースを読み込めません: {exc}") from exc


def lighting_rated_power(building_type, room_type, room_area):
    """建物用途・室用途・床面積から、照明1台分の定格消費電力[W]を求める。"""
    if not isinstance(building_type, str) or not isinstance(room_type, str):
        raise ReferenceSpecificationError("照明対象室の建物用途・室用途が不正です。")
    database = _load_database()
    # 共同住宅など、データベースで対象外と定めた建物用途は使用しない。
    if building_type in database.get("metadata", {}).get("unsupported_building_types", ()):
        raise ReferenceSpecificationError(f"建物用途「{building_type}」は基準設定仕様の対象外です。")

    # 換気・照明の表から、建物用途と室用途が両方一致する行を探す。
    rooms = database.get("ventilation_and_lighting", {}).get("rooms", {})
    record = rooms.get(building_type, {}).get(room_type)
    if record is None:
        raise ReferenceSpecificationError(
            f"建物用途「{building_type}」・室用途「{room_type}」の基準設定仕様がありません。"
        )

    lighting = record.get("lighting", {})
    power_per_area = lighting.get(_LIGHTING_POWER_KEY)
    # 「-」は適用不可、「NaN」や空欄は必要な値がないことを表す。
    # JSONへの変換時には、Excelの「NaN」は通常 null（PythonではNone）になる。
    if lighting.get("applicable") is not True or power_per_area in (None, "-", "NaN"):
        raise ReferenceSpecificationError(
            f"建物用途「{building_type}」・室用途「{room_type}」には照明の基準設定仕様を適用できません"
            f"（換気_照明シート {record.get('_source_row', '?')}行目）。"
        )
    # 数値として扱えない値や負数を使うと、誤った電力が生成されるので止める。
    if isinstance(power_per_area, bool) or not isinstance(power_per_area, (int, float)) or not math.isfinite(power_per_area) or power_per_area < 0:
        raise ReferenceSpecificationError(
            f"建物用途「{building_type}」・室用途「{room_type}」の基準設定消費電力が不正です"
            f"（換気_照明シート {record.get('_source_row', '?')}行目）。"
        )

    # Roomsの室面積はExcel・JSON由来なので、文字列の数値も受け入れて検査する。
    try:
        area = float(room_area) if not isinstance(room_area, bool) else math.nan
    except (TypeError, ValueError):
        area = math.nan
    if not math.isfinite(area) or area <= 0:
        raise ReferenceSpecificationError("対象室の床面積（Rooms.roomArea）には正の数値が必要です。")

    # データベースの値[W/m²] × 対象室の床面積[m²] = 定格消費電力[W]。
    return power_per_area * area


def next_lighting_name(used_names, start=1):
    """既存の機器名称と重複しない、次の4桁IDの名称を返す。"""
    # 0001から順に調べ、既存の入力や今回生成した名称があれば飛ばす。
    for number in range(start, 10000):
        name = f"基準設定仕様_照明_{number:04d}"
        if name not in used_names:
            return name, number + 1
    # 4桁で表せるIDをすべて使い切った場合は、名称を生成できない。
    raise ReferenceSpecificationError("照明の基準設定仕様に使用できる4桁のIDがありません。")


def _next_name(equipment, used_names, start):
    """設備ごとに0001から始まる、未使用の名称と次の番号を返す。"""
    for number in range(start, 10000):
        name = f"基準設定仕様_{equipment}_{number:04d}"
        if name not in used_names:
            used_names.add(name)
            return name, number + 1
    raise ReferenceSpecificationError(f"{equipment}に使用できる4桁のIDがありません。")


def _room_data(database, rooms, room_key):
    """Roomsから建物用途・室用途を取得し、共通の対象外条件を確認する。"""
    room = rooms.get(room_key)
    if not isinstance(room, dict):
        raise ReferenceSpecificationError(f"対象室「{room_key}」がRoomsにありません。")
    building_type, room_type = room.get("buildingType"), room.get("roomType")
    if not isinstance(building_type, str) or not isinstance(room_type, str):
        raise ReferenceSpecificationError(f"対象室「{room_key}」の建物用途・室用途が不正です。")
    if building_type in database.get("metadata", {}).get("unsupported_building_types", ()):
        raise ReferenceSpecificationError(f"建物用途「{building_type}」は基準設定仕様の対象外です。")
    # 固定値の設備でも、H28表に存在しない用途には基準設定仕様を生成しない。
    ventilation_rooms = database.get("ventilation_and_lighting", {}).get("rooms", {})
    ac_rooms = next(iter(database.get("air_conditioning_by_region", {}).values()), {}).get("rooms", {})
    if room_type not in ventilation_rooms.get(building_type, {}) and room_type not in ac_rooms.get(building_type, {}):
        raise ReferenceSpecificationError(f"建物用途「{building_type}」・室用途「{room_type}」がH28表にありません。")
    return room, building_type, room_type


def _ac_values(database, building_type, room_type, region):
    """地域区分に合う空調表から、外壁・窓の基準値を取得する。"""
    try:
        region_number = int(region)
    except (TypeError, ValueError):
        raise ReferenceSpecificationError("Building.Regionには1～8の地域区分が必要です。") from None
    for sheet in database.get("air_conditioning_by_region", {}).values():
        if region_number in sheet.get("regions", ()):
            record = sheet.get("rooms", {}).get(building_type, {}).get(room_type)
            if record is not None:
                return record
            break
    raise ReferenceSpecificationError(
        f"地域{region_number}の建物用途「{building_type}」・室用途「{room_type}」に空調表の仕様がありません。"
    )


def _required_number(record, key, source_row=None):
    """必須のDB値が欠損・適用不可・数値以外なら、生成せずにエラーにする。"""
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
        row = source_row if source_row is not None else record.get("_source_row", "?")
        raise ReferenceSpecificationError(f"データベースの「{key}」が使用できません（原表 {row}行目）。")
    return value


def _positive_area(value):
    """Excelの文字列数値も含め、正の床面積[m²]だけを通す。"""
    try:
        area = float(value) if not isinstance(value, bool) else math.nan
    except (TypeError, ValueError):
        area = math.nan
    if not math.isfinite(area) or area <= 0:
        raise ReferenceSpecificationError("対象室の床面積には正の数値が必要です。")
    return area


def _indexed_item(items, index, label):
    """中間JSONの位置指定が、存在する配列要素を指しているか確認する。"""
    if not isinstance(items, list) or isinstance(index, bool) or not isinstance(index, int) or not 0 <= index < len(items):
        raise ReferenceSpecificationError(f"{label}の位置指定が不正です。")
    item = items[index]
    if not isinstance(item, dict):
        raise ReferenceSpecificationError(f"{label}の対象データが不正です。")
    return item


def _expand_equipment(result, database, request, used_names, next_ids):
    """設備の生成要求1件を展開し、既存の参照名称も差し替える。"""
    equipment = request["equipment"]

    if equipment == "照明":
        room_key = request.get("room")
        if not isinstance(room_key, str) or not room_key:
            raise ReferenceSpecificationError("対象室をroomに指定してください。")
        room = result["Rooms"].get(room_key)
        if not isinstance(room, dict):
            raise ReferenceSpecificationError(f"対象室「{room_key}」がRoomsにありません。")

        lighting_systems = result["LightingSystems"]
        system = lighting_systems.get(room_key)
        if system is not None and (
            not isinstance(system, dict)
            or ("lightingUnit" in system and not isinstance(system["lightingUnit"], dict))
        ):
            raise ReferenceSpecificationError(f"LightingSystemsの対象室「{room_key}」のlightingUnitが不正です。")

        try:
            power = lighting_rated_power(
                room.get("buildingType"), room.get("roomType"), room.get("roomArea")
            )
            name, next_ids["照明"] = next_lighting_name(used_names["照明"], next_ids["照明"])
        except ReferenceSpecificationError as exc:
            raise ReferenceSpecificationError(f"対象室「{room_key}」: {exc}") from exc

        # JSON入力でLightingSystems自体がない場合も、通常の照明室を作る。
        if system is None:
            system = {
                "roomWidth": None,
                "roomDepth": None,
                "unitHeight": None,
                "roomIndex": None,
                "lightingUnit": {},
            }
            lighting_systems[room_key] = system
        else:
            # 照明計算側が読む寸法などの省略値を補う。
            for key in ("roomWidth", "roomDepth", "unitHeight", "roomIndex"):
                system.setdefault(key, None)
            system.setdefault("lightingUnit", {})

        used_names["照明"].add(name)
        system["lightingUnit"][name] = {
            "RatedPower": power,
            "Number": 1,
            "OccupantSensingCTRL": "無",
            "IlluminanceSensingCTRL": "無",
            "TimeScheduleCTRL": "無",
            "InitialIlluminationCorrectionCTRL": "無",
        }
        return

    room_key = request.get("zone") if equipment in ("外壁", "窓") else request.get("room")
    if not isinstance(room_key, str) or not room_key:
        raise ReferenceSpecificationError("対象室または空調ゾーンの名称が必要です。")
    room, building_type, room_type = _room_data(database, result.get("Rooms", {}), room_key)

    if equipment in ("外壁", "窓"):
        # zoneと配列位置で、様式2-4のどの外壁・窓を置き換えるか特定する。
        envelope = result.get("EnvelopeSet", {}).get(room_key)
        if not isinstance(envelope, dict):
            raise ReferenceSpecificationError(f"空調ゾーン「{room_key}」がEnvelopeSetにありません。")
        wall = _indexed_item(envelope.get("WallList"), request.get("wallIndex"), "WallList")
        ac = _ac_values(database, building_type, room_type, result.get("Building", {}).get("Region"))
        if equipment == "外壁":
            if wall.get("WallSpec") != REFERENCE_MARKER:
                raise ReferenceSpecificationError("指定した外壁名称が「基準設定仕様」ではありません。")
            # 水平方向の外皮には屋根、その他の方位には壁の熱貫流率を使う。
            direction = wall.get("Direction")
            if not isinstance(direction, str) or not direction:
                raise ReferenceSpecificationError("外壁の方位がありません。")
            key = "熱貫流率(屋根)" if direction.startswith("水平") else "熱貫流率(壁)"
            u_value = _required_number(ac, key)
            name, next_ids[equipment] = _next_name(equipment, used_names[equipment], next_ids[equipment])
            result.setdefault("WallConfigure", {})[name] = {
                "wall_type_webpro": "外壁", "structureType": "その他",
                "solarAbsorptionRatio": None, "inputMethod": "熱貫流率を入力",
                "Uvalue": u_value, "Info": None,
            }
            # 生成した仕様を、元の外皮のWallSpecから参照させる。
            wall["WallSpec"] = name
        else:
            window = _indexed_item(wall.get("WindowList"), request.get("windowIndex"), "WindowList")
            if window.get("WindowID") != REFERENCE_MARKER:
                raise ReferenceSpecificationError("指定した開口部名称が「基準設定仕様」ではありません。")
            u_value = _required_number(ac, "熱貫流率(窓)")
            i_value = _required_number(ac, "日射熱取得率(窓)")
            name, next_ids[equipment] = _next_name(equipment, used_names[equipment], next_ids[equipment])
            result.setdefault("WindowConfigure", {})[name] = {
                "windowArea": 1, "windowWidth": None, "windowHeight": None,
                "inputMethod": "性能値を入力", "windowUvalue": u_value,
                "windowIvalue": i_value, "layerType": "単層",
                "glassUvalue": None, "glassIvalue": None, "Info": None,
            }
            # 窓仕様への参照を更新し、仕様書に従ってブラインドを「無」にする。
            window["WindowID"] = name
            window["isBlind"] = "無"
        return

    if equipment == "換気":
        # 換気_照明表でこの室用途に換気仕様があるかを確認する。
        record = database.get("ventilation_and_lighting", {}).get("rooms", {}).get(building_type, {}).get(room_type)
        ventilation = record.get("ventilation", {}) if isinstance(record, dict) else {}
        if ventilation.get("applicable") is not True:
            row = record.get("_source_row", "?") if isinstance(record, dict) else "?"
            raise ReferenceSpecificationError(
                f"建物用途「{building_type}」・室用途「{room_type}」に換気仕様を適用できません"
                f"（換気_照明シート {row}行目）。"
            )
        row = record.get("_source_row")
        air_volume = _required_number(ventilation, "基準設定換気風量[m3/hm2]", row)
        motor_power = _required_number(ventilation, "送風機軸動力[kW/m2]", row)
        area = _positive_area(room.get("roomArea"))
        unit_type = request.get("unitType")
        if not isinstance(unit_type, str) or not unit_type:
            raise ReferenceSpecificationError("換気種類をunitTypeに指定してください。")
        ventilation_rooms = result.setdefault("VentilationRoom", {})
        existing_room = ventilation_rooms.get(room_key)
        if existing_room is not None and (not isinstance(existing_room, dict) or not isinstance(existing_room.get("VentilationUnitRef"), dict)):
            raise ReferenceSpecificationError("VentilationRoomの換気機器参照が不正です。")
        name, next_ids[equipment] = _next_name(equipment, used_names[equipment], next_ids[equipment])
        # 単位面積あたりの風量・軸動力に、対象室の床面積を掛けて1台の送風機を作る。
        result.setdefault("VentilationUnit", {})[name] = {
            "Number": 1, "FanAirVolume": air_volume * area,
            "MoterRatedPower": motor_power * area, "PowerConsumption": None,
            "HighEfficiencyMotor": "無", "Inverter": "無", "AirVolumeControl": "無",
            "VentilationRoomType": None, "AC_CoolingCapacity": None,
            "AC_RefEfficiency": None, "AC_PumpPower": None, "Info": None,
        }
        if existing_room is None:
            existing_room = {"VentilationType": None, "VentilationUnitRef": {}}
            ventilation_rooms[room_key] = existing_room
        # 様式3-1に相当する参照先も、生成した名称に結び付ける。
        existing_room["VentilationUnitRef"][name] = {"UnitType": unit_type, "Info": request.get("info")}
        return

    if equipment == "給湯":
        # Excel由来のsystemIndexがあれば既存の仮名称を置き換える。
        # JSON直接入力で省略されたときは対象室に新しい給湯機器を追加する。
        hotwater_rooms = result.setdefault("HotwaterRoom", {})
        existing_room = hotwater_rooms.get(room_key)
        if existing_room is not None and (not isinstance(existing_room, dict) or not isinstance(existing_room.get("HotwaterSystem"), list)):
            raise ReferenceSpecificationError("HotwaterRoomの給湯機器一覧が不正です。")
        index = request.get("systemIndex")
        if index is not None:
            system = _indexed_item(existing_room["HotwaterSystem"] if existing_room else None, index, "HotwaterSystem")
            if system.get("SystemName") != REFERENCE_MARKER:
                raise ReferenceSpecificationError("指定した給湯機器名称が「基準設定仕様」ではありません。")
        else:
            saving = request.get("savingSystem")
            if not isinstance(saving, str) or not saving:
                raise ReferenceSpecificationError("節湯器具をsavingSystemに指定してください。")
        region = result.get("Building", {}).get("Region")
        try:
            region = int(region)
        except (TypeError, ValueError):
            raise ReferenceSpecificationError("Building.Regionには1～8の地域区分が必要です。") from None
        if region not in range(1, 9):
            raise ReferenceSpecificationError("Building.Regionには1～8の地域区分が必要です。")
        # 仕様書の固定値。8地域のみ熱源効率0.82、他地域は0.80。
        # 計算用JSONは効率ではなく定格燃料消費量を保持するので、10kWを効率で割る。
        efficiency = 0.82 if region == 8 else 0.80
        name, next_ids[equipment] = _next_name(equipment, used_names[equipment], next_ids[equipment])
        result.setdefault("HotwaterSupplySystems", {})[name] = {
            "HeatSourceUnit": [{
                "UsageType": "給湯負荷用", "HeatSourceType": "ガス給湯機",
                "Number": 1, "RatedCapacity": 10.0,
                "RatedPowerConsumption": 0, "RatedFuelConsumption": 10.0 / efficiency,
            }],
            "InsulationType": "保温仕様2", "PipeSize": 40,
            "SolarSystemArea": None, "SolarSystemDirection": None,
            "SolarSystemAngle": None, "Info": None,
        }
        if existing_room is None:
            existing_room = {"HotwaterSystem": []}
            hotwater_rooms[room_key] = existing_room
        if index is not None:
            system["SystemName"] = name
        else:
            existing_room["HotwaterSystem"].append({
                "UsageType": None, "SystemName": name,
                "HotWaterSavingSystem": saving, "Info": request.get("info"),
            })
        return

    if equipment == "昇降機":
        # 給湯と同様に、Excel由来の位置指定なら仮名称の要素を置換する。
        # 位置指定がないJSON要求なら、指定された室へ1件追加する。
        elevators = result.setdefault("Elevators", {})
        existing_room = elevators.get(room_key)
        if existing_room is not None and (not isinstance(existing_room, dict) or not isinstance(existing_room.get("Elevator"), list)):
            raise ReferenceSpecificationError("Elevatorsの機器一覧が不正です。")
        index = request.get("elevatorIndex")
        if index is not None:
            elevator = _indexed_item(existing_room["Elevator"] if existing_room else None, index, "Elevator")
            if elevator.get("ElevatorName") != REFERENCE_MARKER:
                raise ReferenceSpecificationError("指定した昇降機名称が「基準設定仕様」ではありません。")
        name, next_ids[equipment] = _next_name(equipment, used_names[equipment], next_ids[equipment])
        # 台数・積載量・速度・制御方式は、仕様書の仮想的な昇降機の固定値。
        generated = {
            "ElevatorName": name, "Number": 2, "LoadLimit": 1150,
            "Velocity": 120, "TransportCapacityFactor": 1,
            "ControlType": "VVVF(電力回生なし)", "Info": None,
        }
        if existing_room is None:
            existing_room = {"Elevator": []}
            elevators[room_key] = existing_room
        if index is not None:
            existing_room["Elevator"][index] = generated
        else:
            existing_room["Elevator"].append(generated)
        return


def expand_reference_specifications(inputdata):
    """中間JSONの生成要求を通常の設備データへ変換し、(完成JSON, エラー一覧)を返す。

    Excelから作った中間JSONと、利用者が直接作ったJSONの両方で使う。
    元の辞書は書き換えない。エラーがあれば呼び出し元は計算を始めない。

    照明の要求の例::

        {"equipment": "照明", "room": "1F_事務室"}

    照明・換気の床面積はExcel・JSON入力ともRoomsにある室面積を使う。
    """
    if not isinstance(inputdata, dict):
        return inputdata, ["基準設定仕様: 入力JSONの最上位はオブジェクトにしてください。"]

    requests = inputdata.get(REQUESTS_KEY, [])
    if not isinstance(requests, list):
        return inputdata, [f"基準設定仕様: {REQUESTS_KEY}は配列にしてください。"]
    if not requests:
        # 指定がない既存JSONは、従来のデータをそのまま返す。
        # 空の要求配列だけは完成JSONから取り除く。
        if REQUESTS_KEY not in inputdata:
            return inputdata, []
        result = inputdata.copy()
        result.pop(REQUESTS_KEY)
        return result, []

    # 失敗時も呼び出し元の入力が残るよう、生成先は別の辞書にする。
    result = copy.deepcopy(inputdata)
    result.pop(REQUESTS_KEY)
    errors = []
    rooms = result.get("Rooms", {})
    lighting_systems = result.get("LightingSystems", {})
    if not isinstance(rooms, dict) or not isinstance(lighting_systems, dict):
        return result, ["基準設定仕様: RoomsとLightingSystemsはオブジェクトにしてください。"]
    # 展開は通常のスキーマ検証より先なので、参照する大きな項目の型を先に確認する。
    # ここで確認しないと、例えばEnvelopeSetが配列のときに属性エラーになる。
    for key in (
        "EnvelopeSet", "WallConfigure", "WindowConfigure", "VentilationRoom",
        "VentilationUnit", "HotwaterRoom", "HotwaterSupplySystems", "Elevators",
    ):
        if key in result and not isinstance(result[key], dict):
            return result, [f"基準設定仕様: {key}はオブジェクトにしてください。"]
    if "Building" in result and not isinstance(result["Building"], dict):
        return result, ["基準設定仕様: Buildingはオブジェクトにしてください。"]
    result.setdefault("LightingSystems", lighting_systems)

    # 設備ごとに既入力名称を集める。後の行に入力された名称とも衝突しない。
    used_by_equipment = {
        "外壁": set(result.get("WallConfigure", {})),
        "窓": set(result.get("WindowConfigure", {})),
        "換気": set(result.get("VentilationUnit", {})),
        "照明": set(),
        "給湯": set(result.get("HotwaterSupplySystems", {})),
        "昇降機": set(),
    }
    for system in lighting_systems.values():
        if isinstance(system, dict) and isinstance(system.get("lightingUnit"), dict):
            used_by_equipment["照明"].update(system["lightingUnit"])
    for elevator_room in result.get("Elevators", {}).values():
        if isinstance(elevator_room, dict):
            entries = elevator_room.get("Elevator", [])
            if not isinstance(entries, list):
                return result, ["基準設定仕様: Elevatorsの機器一覧は配列にしてください。"]
            used_by_equipment["昇降機"].update(
                entry.get("ElevatorName") for entry in entries
                if isinstance(entry, dict) and isinstance(entry.get("ElevatorName"), str)
            )
    next_ids = {equipment: 1 for equipment in used_by_equipment}
    database = _load_database()

    for number, request in enumerate(requests, start=1):
        # sourceはExcelの行番号など、利用者に示すための任意情報。
        source = request.get("source") if isinstance(request, dict) else None
        location = source if isinstance(source, str) and source else f"基準設定仕様 要求{number}"
        if not isinstance(request, dict):
            errors.append(f"{location}: 生成要求はオブジェクトにしてください。")
            continue
        equipment = request.get("equipment")
        if not isinstance(equipment, str) or equipment not in _REQUEST_FIELDS:
            errors.append(f"{location}: 設備種類「{equipment}」には対応していません。")
            continue
        # キーの書き間違いを見逃すと、意図しない対象や面積で計算されかねない。
        unexpected = set(request) - _REQUEST_FIELDS[equipment] - {"equipment", "source"}
        if unexpected:
            errors.append(f"{location}: 未対応の項目があります: {', '.join(sorted(unexpected))}。")
            continue
        try:
            _expand_equipment(result, database, request, used_by_equipment, next_ids)
        except ReferenceSpecificationError as exc:
            errors.append(f"{location}: 基準設定仕様を展開できません。{exc}")

    # Excel側で「基準設定仕様」だけを指定した室について、展開に失敗した場合は
    # 照明器具0台の空データを計算用JSONに残さない。
    for room_key in {
        r.get("room") for r in requests
        if isinstance(r, dict) and r.get("equipment") == "照明" and isinstance(r.get("room"), str)
    }:
        system = lighting_systems.get(room_key)
        if isinstance(system, dict) and system.get("lightingUnit") == {}:
            del lighting_systems[room_key]

    return result, errors


def prepare_input_data(data, validation=None, *, from_excel=False, validate_schema=True):
    """基準設定仕様を展開し、計算に渡すJSONと検証結果を返す。

    Excelのセル検査は読み取り側で済ませる。ここではExcel・JSONのどちらも
    同じ展開処理を通し、その後で完成したJSONの構造を確認する。
    """
    # 呼び出し元のエラー一覧は書き換えず、読み取り時のエラーを引き継ぐ。
    validation = validation or {}
    result_validation = {
        "error": list(validation.get("error", [])),
        "warning": list(validation.get("warning", [])),
    }

    # 中間JSONの「基準設定仕様」を通常の設備データに置き換える。
    # 要求に含まれるsource（Excelのシート・行）は展開エラーの先頭に付く。
    prepared, reference_errors = expand_reference_specifications(data)
    result_validation["error"].extend(reference_errors)

    # 展開に失敗したJSONはまだ完成形ではないため、スキーマ検査へ渡さない。
    # Excelの空欄は読み取り時に位置付きで報告済みなので、同じエラーを重ねない。
    if not reference_errors and validate_schema:
        if from_excel:
            result_validation["error"].extend(
                bc.inputdata_validation(prepared, skip_empty_values=True)
            )
        else:
            result_validation["error"].extend(bc.inputdata_validation(prepared))

    return prepared, result_validation
