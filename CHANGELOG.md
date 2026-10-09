# 更新履歴 / Changelog

## Ver.2.3.4（2026.10）

### 機能追加

- 基準設定仕様の入力を可能としました。

### New feature

- Added support for entering reference specification settings.

## Ver.2.3.3（2026.10）

### 不具合修正

- 窓のガラスの層数に「三層以上の複層」を指定すると、入力検証でエラーになる不具合を修正しました。
- 空調運転モード入力シートで「冷房期」「中間期」「暖房期」と入力した場合も、それぞれ「冷房」「中間」「暖房」として扱えるように修正しました。

### Bug fixes

- Fixed an input validation error when selecting three or more glazing layers (`三層以上の複層`).
- Fixed parsing of the air-conditioning operation mode sheet so that `冷房期`, `中間期`, and `暖房期` are accepted as `冷房`, `中間`, and `暖房`, respectively.

過去のリリース / Previous releases: [GitHub Releases](https://github.com/MasatoMiyata/builelib/releases)
