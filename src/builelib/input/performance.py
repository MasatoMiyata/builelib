"""Pure envelope performance helpers for parsed WEBPRO input data."""

from __future__ import annotations

from collections.abc import Mapping
from functools import lru_cache
from typing import Any
import unicodedata

from builelib import database_loader


_FRAME_TYPE_ALIASES = {
    "木製": "木製・樹脂製建具",
    "樹脂製": "木製・樹脂製建具",
    "木製・樹脂製建具": "木製・樹脂製建具",
    "金属木複合製": "金属木複合製・金属樹脂複合製建具",
    "金属樹脂複合製": "金属木複合製・金属樹脂複合製建具",
    "金属木複合製・金属樹脂複合製建具": "金属木複合製・金属樹脂複合製建具",
    "金属製": "金属製建具",
    "金属製建具": "金属製建具",
}


@lru_cache(maxsize=1)
def _envelope_databases() -> dict[str, Any]:
    database = database_loader.load_all_databases()
    return {
        "materials": database["建材の種類"],
        "glass": database["ガラスの種類"],
        "glass_to_window": database["ガラス窓性能変換（建具種類）"],
    }


def _material_name(value: Any) -> str:
    name = unicodedata.normalize("NFKC", str(value)).replace(" ", "")
    return {
        "密閉空気層": "密閉中空層",
        "非密閉空気層": "非密閉中空層",
    }.get(name, name)


def calculate_wall_u_value(
    wall_config: Mapping[str, Any],
    *,
    database: Mapping[str, Any] | None = None,
) -> float:
    """Calculate the wall U-value from a parsed ``WallConfigure`` item."""

    method = wall_config.get("inputMethod")
    if method == "熱貫流率を入力":
        return float(wall_config["Uvalue"])
    if method != "建材構成を入力":
        raise ValueError(f"未対応の外壁入力方法です: {method!r}")

    materials = database or _envelope_databases()["materials"]
    resistance = 0.11 + 0.04
    for layer in wall_config.get("layers", []):
        thickness = layer.get("thickness")
        conductivity = layer.get("conductivity")
        if conductivity is not None:
            if thickness is not None:
                resistance += (float(thickness) / 1000.0) / float(conductivity)
            continue

        name = _material_name(layer.get("materialID"))
        material = materials[name]
        if "熱抵抗値" in material:
            resistance += float(material["熱抵抗値"])
        elif thickness is not None:
            resistance += (float(thickness) / 1000.0) / float(material["熱伝導率"])

    if resistance <= 0:
        raise ValueError("外壁の熱抵抗が0以下です。")
    return 1.0 / resistance


def calculate_window_performance(
    window_config: Mapping[str, Any],
    *,
    glass_database: Mapping[str, Any] | None = None,
    conversion_database: Mapping[str, Any] | None = None,
) -> tuple[float, float]:
    """Return ``(U-value, solar heat gain coefficient)`` for a window."""

    method = window_config.get("inputMethod")
    if method == "性能値を入力":
        return float(window_config["windowUvalue"]), float(window_config["windowIvalue"])
    if method not in {"ガラスの種類を入力", "ガラスの性能を入力"}:
        raise ValueError(f"未対応の窓入力方法です: {method!r}")

    databases = _envelope_databases()
    glass_data = glass_database or databases["glass"]
    conversions = conversion_database or databases["glass_to_window"]

    if method == "ガラスの種類を入力":
        glass = glass_data[window_config["glassID"]]["ガラス単体"]
        glass_u_value = float(glass["熱貫流率"])
        glass_eta_value = float(glass["日射熱取得率"])
    else:
        glass_u_value = float(window_config["glassUvalue"])
        glass_eta_value = float(window_config["glassIvalue"])

    frame_type = _FRAME_TYPE_ALIASES[window_config["frameType"]]
    layer_type = window_config["layerType"]
    conversion = conversions[frame_type][layer_type]
    u_value = float(conversion["ku_a"]) * glass_u_value + float(conversion["ku_b"])
    eta_value = float(conversion["kita"]) * glass_eta_value
    return u_value, eta_value
