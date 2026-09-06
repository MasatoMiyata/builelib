import csv
from pathlib import Path

import pytest

from builelib.input import parse_input_sheet
from builelib.runner import calculate_from_json


WEBPRO_EXAMPLES = Path(__file__).resolve().parents[1] / "examples" / "WEBPRO"
WEBPRO_EXPECTED_RESULTS = Path(__file__).resolve().parent / "WEBPRO"
INPUT_SHEETS = sorted(WEBPRO_EXAMPLES.glob("sample*_WEBPRO_inputSheet_for_Ver*.xlsx"))
RESULT_IDS = range(17, 31)

# Builelib returns MJ/year, while WEBPRO's ResultSummary uses GJ/year.
RESULT_KEY_BY_ID = {
    17: "設計一次エネルギー消費量（空調）[MJ]",
    18: "基準一次エネルギー消費量（空調）[MJ]",
    19: "設計一次エネルギー消費量（換気）[MJ]",
    20: "基準一次エネルギー消費量（換気）[MJ]",
    21: "設計一次エネルギー消費量（照明）[MJ]",
    22: "基準一次エネルギー消費量（照明）[MJ]",
    23: "設計一次エネルギー消費量（給湯）[MJ]",
    24: "基準一次エネルギー消費量（給湯）[MJ]",
    25: "設計一次エネルギー消費量（昇降機）[MJ]",
    26: "基準一次エネルギー消費量（昇降機）[MJ]",
    27: "創エネルギー量（太陽光）[MJ]",
    28: "創エネルギー量（コジェネ）[MJ]",
    29: "その他一次エネルギー消費量[MJ]",
    30: "その他一次エネルギー消費量[MJ]",
}


def _read_expected_results(input_sheet: Path) -> dict[int, float]:
    sample_name = input_sheet.name.split("_WEBPRO_", maxsplit=1)[0]
    summary_path = WEBPRO_EXPECTED_RESULTS / (
        f"{sample_name}_WEBPRO_inputSheet_for_Ver3.10_ResultSummary.csv"
    )

    expected = {}
    with summary_path.open(encoding="cp932", newline="") as csv_file:
        for row in csv.reader(csv_file):
            if row and row[0].isdigit():
                result_id = int(row[0])
                if result_id in RESULT_IDS:
                    expected[result_id] = float(row[2])

    assert expected.keys() == RESULT_KEY_BY_ID.keys(), (
        f"ResultSummaryにID 17～30が揃っていません: {summary_path}"
    )
    return expected


@pytest.mark.parametrize("input_sheet", INPUT_SHEETS, ids=lambda path: path.name)
def test_webpro_example_energy_results(input_sheet):
    parsed = parse_input_sheet(input_sheet)
    assert parsed.errors == [], f"入力シートの解析エラー: {parsed.errors}"

    calculation = calculate_from_json(parsed.data)
    assert calculation["errors"] == [], f"設備計算エラー: {calculation['errors']}"

    expected = _read_expected_results(input_sheet)
    result = calculation["result"]
    differences = []

    for result_id, result_key in RESULT_KEY_BY_ID.items():
        actual_gj = float(result[result_key]) / 1000
        expected_gj = expected[result_id]
        if actual_gj != pytest.approx(expected_gj, rel=0.10, abs=1.0):
            differences.append(
                f"ID {result_id}: actual={actual_gj:.2f} GJ/year, "
                f"expected={expected_gj:.2f} GJ/year"
            )

    assert not differences, "\n" + "\n".join(differences)
