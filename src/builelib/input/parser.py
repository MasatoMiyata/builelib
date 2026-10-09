"""Excel入力シートを読み取り、計算に使えるデータを返す公開API。"""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from .make_inputdata import make_jsondata_from_Ver2_sheet
from .preparation import prepare_input_data


# 旧読取処理は検証メッセージをモジュール内で共有するため、同時実行を防ぐ。
_PARSE_LOCK = RLock()
_SUPPORTED_SUFFIXES = {".xlsx", ".xlsm"}


@dataclass(frozen=True)
class InputSheetParseResult:
    """完成した入力データと、読取・検証で見つかったメッセージ。"""

    data: dict[str, Any]
    errors: list[str]
    warnings: list[str]


def parse_input_sheet(path: str | Path) -> InputSheetParseResult:
    """WEBPRO入力シートを読み取り、結果を返す。
    """

    # 対応するExcel形式と、指定されたファイルの存在を先に確認する。
    input_path = Path(path)
    if input_path.suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise ValueError("入力ファイルは .xlsx または .xlsm である必要があります。")
    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    with _PARSE_LOCK:

        # 各シートを読み取り、「基準設定仕様」の生成要求を含むJSONを作る。
        data, validation = make_jsondata_from_Ver2_sheet(str(input_path))

        # 基準設定仕様の展開とスキーマ検証：
        data, validation = prepare_input_data(data, validation, from_excel=True)

        return InputSheetParseResult(
            data=copy.deepcopy(data),
            errors=list(validation.get("error", [])),
            warnings=list(validation.get("warning", [])),
        )
