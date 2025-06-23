# Builelib: Building Energy-modeling Library

Builelib (Builelib: Building Energy-modeling Library) は 非住宅建築物のエネルギー消費量を計算するためのプログラムです。

- Builelib: [https://builelib.net/](https://builelib.net/)
  
計算ロジックは建築物省エネ基準に基づくエネルギー消費性能計算プログラム（WEBPRO）と同じですが、一部、WEBPROにはない機能を追加で実装しています。

- 建築物省エネ基準に基づく「建築物のエネルギー消費量計算プログラム（非住宅版）」（WEBPRO）  
[https://building.app.lowenergy.jp/](https://building.app.lowenergy.jp/)


WEBPROの入力シート（xlsxファイル）をアップロードすれば、ZIPファイル（入力ファイルと計算結果）をダウンロードできます。

Builelib用の特殊シート（SPシート）を追加することで、一次エネルギー換算係数の変更や空調と照明の連成計算など、より高度な計算を実施することが出来ます。
 
!!! Warning
    - 本マニュアルの内容の一部または全部を無断で転載することは禁止とします。
    - 本プログラムの評価結果を建築物省エネ基準の申請等に使用することはできません（申請のためのPDF等は出力されません）。
    - 本プログラムを使用したことに伴っていかなる損害、損失等が生じたとしても、これらについて一切の保証責任及び賠償責任を負いません。

!!! Tip
    - Builelibはpythonでコーディングされています。コマンドラインで実行することも可能です。詳細は [github](https://github.com/MasatoMiyata/builelib)をご覧下さい。