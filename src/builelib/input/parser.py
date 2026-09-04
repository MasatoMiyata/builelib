"""Public, thread-safe input-sheet parsing API."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Any

from .make_inputdata import make_jsondata_from_Ver2_sheet


_PARSE_LOCK = RLock()
_SUPPORTED_SUFFIXES = {".xlsx", ".xlsm"}


@dataclass(frozen=True)
class InputSheetParseResult:
    """Result returned by :func:`parse_input_sheet`."""

    data: dict[str, Any]
    errors: list[str]
    warnings: list[str]


def parse_input_sheet(path: str | Path) -> InputSheetParseResult:
    """Parse a WEBPRO input sheet without creating intermediate files.

    The legacy parser stores validation messages in a module-global variable.
    Calls are therefore serialized until the legacy implementation can be
    made fully re-entrant.
    """

    input_path = Path(path)
    if input_path.suffix.lower() not in _SUPPORTED_SUFFIXES:
        raise ValueError("入力ファイルは .xlsx または .xlsm である必要があります。")
    if not input_path.is_file():
        raise FileNotFoundError(input_path)

    with _PARSE_LOCK:
        data, validation = make_jsondata_from_Ver2_sheet(str(input_path))
        return InputSheetParseResult(
            data=copy.deepcopy(data),
            errors=list(validation.get("error", [])),
            warnings=list(validation.get("warning", [])),
        )
