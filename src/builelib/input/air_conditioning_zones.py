"""室と空調ゾーンの対応付け。既存JSONの同名参照は変更しない。"""

import math


def zone_room_keys(data, zone_name):
    """明示された所属室、または従来の同名室を返す。"""
    zone = data["AirConditioningZone"][zone_name]
    keys = zone.get("roomKeys", [zone_name])
    if not isinstance(keys, list) or not keys:
        raise ValueError("roomKeysには所属室のキーを1件以上指定してください。")
    if any(not isinstance(key, str) or not key for key in keys):
        raise ValueError("roomKeysには空でない文字列を指定してください。")
    if len(set(keys)) != len(keys):
        raise ValueError("roomKeysに同じ室が重複しています。")
    return keys


def zone_properties(data, zone_name):
    """所属室の共通用途と合計面積を返す。Rooms自体は書き換えない。"""
    keys = zone_room_keys(data, zone_name)
    members = []
    for key in keys:
        room = data.get("Rooms", {}).get(key)
        if not isinstance(room, dict):
            raise ValueError(f"所属室「{key}」がRoomsにありません。")
        area = room.get("roomArea")
        if isinstance(area, bool) or not isinstance(area, (int, float)) or not math.isfinite(area) or area <= 0:
            raise ValueError(f"所属室「{key}」の床面積には正の数値が必要です。")
        members.append(room)
    first = members[0]
    usage = (first.get("buildingType"), first.get("roomType"))
    if any(not isinstance(value, str) or not value for value in usage):
        raise ValueError(f"所属室「{keys[0]}」の建物用途・室用途が不正です。")
    if any((room.get("buildingType"), room.get("roomType")) != usage for room in members[1:]):
        raise ValueError("同じ空調ゾーンの所属室は、建物用途・室用途を同じにしてください。")
    return {
        "buildingType": usage[0],
        "roomType": usage[1],
        "zoneArea": sum(room["roomArea"] for room in members),
    }


def _legacy_split(data, zone_name):
    # 室分割の対応拡張は対象外。既存の分割表現に新しい所属制約を適用しない。
    return any(
        isinstance(room, dict) and isinstance(room.get("zone"), dict)
        and any(zone_name == f"{key}_{part}" for part in room["zone"])
        for key, room in data.get("Rooms", {}).items()
    )


def validate_air_conditioning_zones(data, sources=None):
    """Excel生成・JSON読込で共用する参照整合性検証。エラーを一覧で返す。"""
    if not isinstance(data, dict):
        return []  # 最上位の型は既存のスキーマ検証で報告する。
    rooms = data.get("Rooms", {})
    zones = data.get("AirConditioningZone", {})
    if not isinstance(rooms, dict) or not isinstance(zones, dict):
        return ["RoomsとAirConditioningZoneはオブジェクトにしてください。"]
    errors = []
    owners = {}
    for name, zone in zones.items():
        location = f"AirConditioningZone -> {name}"
        prefix = f"{sources[name]}: " if sources and name in sources else ""
        if not isinstance(zone, dict):
            errors.append(f"{prefix}{location}: ゾーンはオブジェクトにしてください。")
            continue
        if "roomKeys" not in zone and name not in rooms and _legacy_split(data, name):
            continue
        try:
            zone_properties(data, name)
            for key in zone_room_keys(data, name):
                if key in owners:
                    raise ValueError(f"所属室「{key}」が空調ゾーン「{owners[key]}」にも重複して所属しています。")
                owners[key] = name
        except ValueError as exc:
            errors.append(f"{prefix}{location}: {exc}")
    envelopes = data.get("EnvelopeSet", {})
    if isinstance(envelopes, dict):
        for name, envelope in envelopes.items():
            # 非空調外皮は空調ゾーンへの参照を必須にしない（既存JSONとの互換性）。
            if isinstance(envelope, dict) and envelope.get("isAirconditioned") == "無":
                continue
            if name not in zones:
                errors.append(f"EnvelopeSet -> {name}: 参照する空調ゾーンがAirConditioningZoneにありません。")
    return errors


def lighting_heat_density(data, zone_name, standard_density):
    """各所属室の器具電力を合算。照明未入力室には標準発熱を用いる。"""
    lighting = data.get("LightingSystems", {})
    keys = zone_room_keys(data, zone_name)
    if all(key not in lighting for key in keys):
        return standard_density
    power = 0
    area = 0
    for key in keys:
        room_area = data["Rooms"][key]["roomArea"]
        area += room_area
        if key in lighting:
            power += sum(unit["RatedPower"] * unit["Number"] for unit in lighting[key]["lightingUnit"].values())
        else:
            power += standard_density * room_area
    return power / area
