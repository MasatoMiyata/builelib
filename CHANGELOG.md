# 更新履歴 / Changelog

## Ver.2.3.5（2026.11）

### 機能追加・変更

- 複数室が属する空調ゾーンの入力・計算に対応しました。
- SP-AC-OA（外気補正）シートから、空調機群ごとの日別外気エンタルピー補正値を読み込み、外気負荷計算に反映できるようにしました。外気冷房効果の計算には補正前の外気エンタルピーを使用します。
- SP-AC-RL（室負荷）の日別室負荷は、室負荷の種類を「冷房」「暖房」として指定する方式に変更しました。

### 不具合修正・入力検証の改善

- 様式2-2（外壁構成）と様式2-4（外皮）のシート名は、末尾の空白の有無にかかわらず読み込めるようにしました。
- 対応様式のシート名とA1セルの様式番号の不整合、および同じ様式のシートの重複を入力エラーとして検出するようにしました。
- 室と空調ゾーンの対応、所属室の用途・面積、空調機群名称、外皮の参照先の検証を追加しました。
- 様式2-7（空調機）の「設計最大外気風量」が空欄の場合も計算できるように修正しました。

### New features and changes

- Added input and calculation support for air-conditioning zones containing multiple rooms.
- Added support for daily outdoor-air enthalpy corrections per air-handling unit group through the SP-AC-OA sheet. Corrections apply to outdoor-air load calculations; outdoor-air cooling effects use the uncorrected enthalpy.
- Changed SP-AC-RL daily room load types to `冷房` (cooling) and `暖房` (heating).

### Bug fixes and input validation improvements

- Accepted sheet names for Form 2-2 (wall construction) and Form 2-4 (envelope) with or without trailing spaces.
- Added input errors for mismatches between supported sheet names and form identifiers in cell A1, and for duplicate sheets representing the same form.
- Added validation of room-to-zone membership, member room usage and area, air-handling unit group names, and envelope zone references.
- Fixed calculations when the design maximum outdoor-air volume in Form 2-7 is blank.

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
