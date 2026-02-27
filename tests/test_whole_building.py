import shutil
import pytest

from builelib.runner import calculate
from . import test_utils

SAMPLES = [
    ("Builelib_inputSheet_sample_001"),
    ("Builelib_inputSheet_sample_002"),
    ("sample01_WEBPRO_inputSheet_English"),
    ("sample01_WEBPRO_inputSheet_for_Ver3.8"),
]


@pytest.mark.parametrize("sample", SAMPLES)
def test_calculate(tmp_path, sample):
    """calculate() がサンプルの基準値と一致する結果を返すことを確認する"""

    input_xlsx = test_utils.get_test_file_path(f"whole_building/{sample}.xlsx")
    reference_json = test_utils.get_test_file_path(f"whole_building/{sample}_result.json")
    expected = test_utils.read_json(reference_json)

    # 入力ファイルを一時ディレクトリにコピー（参照JSONを上書きしないため）
    input_copy = tmp_path / f"{sample}.xlsx"
    shutil.copy(input_xlsx, input_copy)

    # 計算実行（結果は tmp_path 内に出力される）
    calculate(str(input_copy))

    # 出力された result.json を読み込む
    result_file = tmp_path / f"{sample}_result.json"
    assert result_file.exists(), "result.json が生成されませんでした"

    result = test_utils.read_json(result_file)

    # 全キーを比較（浮動小数点は相対誤差 0.1% 以内）
    for key, expected_value in expected.items():
        assert key in result, f"キー '{key}' が結果に存在しません"
        if isinstance(expected_value, float):
            assert result[key] == pytest.approx(expected_value, rel=1e-3), (
                f"{key}: 期待値 {expected_value}, 実際値 {result[key]}"
            )
        else:
            assert result[key] == expected_value, (
                f"{key}: 期待値 {expected_value}, 実際値 {result[key]}"
            )
