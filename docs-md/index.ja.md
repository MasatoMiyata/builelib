# Builelib: Building Energy-modeling Library

Builelib (Builelib: Building Energy-modeling Library) は 非住宅建築物のエネルギー消費量を計算するためのプログラムです。

- 計算ロジックは建築物省エネ基準に基づくエネルギー消費性能計算プログラム（WEBPRO, [https://building.app.lowenergy.jp/](https://building.app.lowenergy.jp/)）と同じですが、一部、WEBPROにはない機能を追加で実装しています。
- [Builelib インターフェイス](https://builelib.net/) にアクセスし、WEBPRO形式の入力シート（xlsxファイル）をアップロードすれば、ZIPファイル（入力ファイルと計算結果）をダウンロードできます。

Builelib専用の特殊シート（SPシート）を追加することで、一次エネルギー換算係数の変更や空調と照明の連成計算など、より高度な計算を実施することが出来ます。

- SP-CM-1	電力の一次エネルギー換算係数
- SP-CM-2	空調設備と照明設備の連成計算
- SP-CD	気象データ入力シート
- SP-RT-UC	室使用条件入力シート
- SP-RT-CP	カレンダーパターン入力シート
- SP-RT-SD	室スケジュール入力シート
- SP-AC-MD	空調モード入力シート
- SP-AC-ST	日射熱取得率（日別）入力シート
- SP-AC-RL	室負荷（日別）入力シート
- SP-AC-AL	空調負荷（時刻別）入力シート
- SP-AC-HS	熱源機器特性入力シート
- SP-AC-WT	熱源送水温度（日別）入力シート
- SP-AC-CW	熱源冷却水温度（日別）入力シート
- SP-AC-FC	変風量・変流量制御特性入力シート
- SP-V-CL	換気制御効果率入力シート ＜調整中＞
- SP-V-PR	換気代替空調機年間平均負荷率入力シート ＜調整中＞
- SP-L-CL	照明制御効果率（時刻別）入力シート ＜調整中＞
- SP-HW-WS	節湯器具入力シート ＜調整中＞
- SP-HW-IM	配管保温仕様入力シート ＜調整中＞
- SP-EV-CL	速度制御方式入力シート ＜調整中＞
 

!!! Warning
    - 本マニュアルの内容の一部または全部を無断で転載することは禁止とします。
    - 本プログラムの評価結果を建築物省エネ基準の申請等に使用することはできません（申請のためのPDF等は出力されません）。
    - 本プログラムを使用したことに伴っていかなる損害、損失等が生じたとしても、これらについて一切の保証責任及び賠償責任を負いません。

!!! Tip
    - Builelibはpythonでコーディングされています。コマンドラインで実行することも可能です。詳細は [github](https://github.com/MasatoMiyata/builelib)をご覧下さい。