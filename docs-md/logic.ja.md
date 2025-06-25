Builelib における一次エネルギー消費量の計算方法を解説する。Builelibの計算ロジックは日本の省エネルギー基準（非住宅建築物）をベースとしているが、様々な独自の計算を追加している。
よって、省エネルギー基準のプログラムと同じ結果にならないことに注意が必要である。

全設備の計算において共通で使用する定数を次に示す。

<div style="text-align: center; margin-bottom: 0.01em;">表1. 共通の定数</div>
<table border="1" style="margin-top: 0.01;">
  <colgroup>
    <col style="width: 20%;">
    <col style="width: 50%;">
    <col style="width: 15%;">
    <col style="width: 15%;">
  </colgroup>
  <tr>
    <th>定数名</th> <th>説明</th> <th>値</th> <th>単位</th>
  </tr>
  <tr>
    <td>$f_{prim,e}$</td ><td>電気の量1キロワット時を熱量に換算する係数</td> <td>9760</td> <td>kJ/kWh</td>
  </tr>
  <tr>
    <td>$C_{a}$</td> <td>乾き空気の定圧比熱</td> <td>1.006</td> <td>kJ⁄(kg・K)</td>
  </tr>
  <tr>
    <td>$C_{wv}$</td> <td>水蒸気の定圧比熱</td> <td>1.805</td> <td>kJ⁄(kg・K)</td>
  </tr>
  <tr>
    <td>$C_{w}$</td> <td>水の定圧比熱</td> <td>4.186</td> <td>kJ⁄(kg・K)</td>
  </tr>
  <tr>
    <td>$L_{w}$</td> <td>水の蒸発潜熱</td> <td>2502</td> <td>kJ⁄(kg・K)</td>
  </tr>
  <tr>
    <td>$\rho_{w}$</td> <td>水の密度（大気圧、7度）</td> <td>1000</td> <td>kg⁄$m^{3}$</td>
  </tr>
  <tr>
    <td>$\alpha_{o}$</td> <td>室外側総合熱伝達率</td> <td>1/0.04</td> <td>W/($m^{2}$・K)</td>
  </tr>
  <tr>
    <td>$\alpha_{i}$</td> <td>室内側総合熱伝達率</td> <td>1/0.11</td> <td>W/($m^{2}$・K)</td>
  </tr>
  <tr>
    <td>$f_{fan,heat}$</td> <td>ファンの発熱比率</td> <td>0.84</td> <td>-</td>
  </tr>
  <tr>
    <td>$f_{pump,heat}$</td> <td>ポンプの発熱比率</td> <td>0.84</td> <td>-</td>
  </tr>
  <tr>
    <td>$f_{ref,ts,loss}$</td> <td>蓄熱槽の熱損失係数</td> <td>0.03</td> <td>-</td>
  </tr>
</table>


## 第1章 設計一次エネルギー消費量の算定方法

設計一次エネルギー消費量の算定方法を示す。
設計一次エネルギー消費量 $E_{T}$ [GJ/年] は次式で算出するものとし、小数点第二位を切り上げた数値であるとする。

---
$$
E_{T} = (E_{AC} + E_{V} + E_{L} + E_{HW} + E_{EV} - E_{PV} - E_{CGS} + E_{M}) \times 10^{-3}
$$
---

- $E_{AC}$ は空気調和設備の設計一次エネルギー消費量 [MJ/年] であり、その算出方法は第2章で示す。
- $E_{V}$ は機械換気設備の設計一次エネルギー消費量 [MJ/年] であり、その算出方法は第3章で示す。
- $E_{L}$ は照明設備の設計一次エネルギー消費量 [MJ/年] であり、その算出方法は第4章で示す。
- $E_{HW}$ は給湯設備の設計一次エネルギー消費量 [MJ/年] であり、その算出方法は第5章で示す。
- $E_{EV}$ は昇降機の設計一次エネルギー消費量 [MJ/年] であり、その算出方法は第6章で示す。
- $E_{PV}$ は太陽光発電設備による一次エネルギー消費量の削減量 [MJ/年] であり、その算出方法は第7章で示す。
- $E_{CGS}$ はコージェネレーション設備による一次エネルギー消費量の削減量 [MJ/年] であり、その算出方法は第8章で示す。
- $E_{M}$ はその他一次エネルギー消費量 [MJ/年] であり、その算出方法は第9章で示す。


## 第2章 空気調和設備の評価

[第2章へのリンク](./Reference/EngineeringReference_chapter02.html).

## 第3章 機械換気設備の評価 

[第3章へのリンク](./Reference/EngineeringReference_chapter03.html).

## 第4章 照明設備の評価

[第4章へのリンク](./Reference/EngineeringReference_chapter04.html).

## 第5章 給湯設備の評価 

[第5章へのリンク](./Reference/EngineeringReference_chapter05.html).

## 第6章 昇降機の評価 

[第6章へのリンク](./Reference/EngineeringReference_chapter06.html).

## 第7章 太陽光発電設備の評価方法

太陽光発電設備の評価方法は、エネルギー消費性能計算プログラム（住宅版）の評価方法と同じである [(仕様書)](https://www.kenken.go.jp/becc/documents/house/9-1_191119_v08_PVer0207.pdf)。
ただし、発電した電力を少しでも売電する場合は、当該太陽光発電設備は評価の対象とはしない。
一方、いわゆる「売電」をしない場合は、その発電量を 100%自己消費するものとして、評価の対象とする。
また、当該建築物以外の建築物に設置された太陽光発電設備による発電量についても評価の対象とはしない。


## 第8章 コージェネレーション設備の評価方法

[第8章へのリンク](./Reference/EngineeringReference_chapter08-en.html).

## 第9章 その他一次エネルギー消費量の算定方法

[第9章へのリンク](./Reference/EngineeringReference_chapter09-en.html).

## 第10章 基準一次エネルギー消費量の算定方法

[第10章へのリンク](./Reference/EngineeringReference_chapter10-en.html).


## 計算に使用するデータベース

* [標準室使用条件](https://www.kenken.go.jp/becc/documents/building/Definitions/ROOM_SPEC_H28.zip)
* [標準室使用条件の詳細](https://www.kenken.go.jp/becc/documents/building/Definitions/RoomUsageCondition_20140303.pdf)
* [カレンダーパターン](https://www.kenken.go.jp/becc/documents/building/Definitions/CalenderPattern_20140303.pdf)
* [建材物性値の一覧](https://www.kenken.go.jp/becc/documents/building/Definitions/HeatThermalConductivity.zip)
* [窓性能の一覧](https://www.kenken.go.jp/becc/documents/building/Definitions/WindowHeatTransferPerformance_H30_181005.zip)
* [負荷計算用係数](https://www.kenken.go.jp/becc/documents/building/Definitions/QROOM_COEFFI.zip)
* [熱源機器特性係数](https://www.kenken.go.jp/becc/documents/building/Definitions/REFLIST_H28_REFCURVE_H28.zip)


## 参考資料

* 建築研究資料第201号: 新設地域熱供給プラントの一次エネルギー換算係数に関する研究、R02.09
* 国総研資料第1107号: 非住宅建築物の外皮・設備設計仕様とエネルギー消費性能の実態調査 - 省エネ基準適合性判定プログラムの入出力データの分析 -、R02.03
* 建築研究資料第191号: 業務用コージェネレーション設備の性能評価手法の高度化に関する研究、H31.04
* 建築研究資料第190号: 各種空調設備システムの潜熱負荷処理メカニズムを踏まえたエネルギー消費量評価法に関する検討、H31.04
* 建築研究資料第188号: 太陽光発電設備の年間発電量の推計方法に関する調査、H30.01
* 建築研究資料第187号: 建築物の設備・機器のエネルギー効率に関する既存試験方法の調査、H29.09
* 国総研資料第974号、建築研究資料第183号: 平成28年省エネルギー基準（平成28年1月公布）関係技術資料 モデル建物法入力支援ツール解説、H29.06
* 国総研資料第973号	建築研究資料第182号: 平成28年省エネルギー基準（平成28年1月公布）関係技術資料　エネルギー消費計算プログラム（非住宅版）解説、H29.06
* 建築研究資料第177号: 業務用空調・給湯システムの制御による省エネルギー効果の実証的評価、H28.11
* 建築研究資料第176号: 業務用建築物のエネルギー消費量評価手法に関する基礎的調査、H28.11
* 国総研資料第765号	建築研究資料第152号: 平成25年省エネルギー基準(平成25年9月公布)等関係技術資料 モデル建物法による非住宅建築物の外皮性能及び一次エネルギー消費量評価プログラム解説、H25.11
* 国総研資料第764号	建築研究資料第151号: 平成25年省エネルギー基準(平成25年9月公布)等関係技術資料 主要室入力法による非住宅建築物の一次エネルギー消費量算定プログラム解説、H25.11
* 国総研資料第763号	建築研究資料第150号: 平成25年省エネルギー基準(平成25年9月公布)等関係技術資料 非住宅建築物の外皮性能評価プログラム解説、H25.11
* 国総研資料第762号	建築研究資料第149号: 平成25年省エネルギー基準(平成25年9月公布)等関係技術資料 一次エネルギー消費量算定プログラム解説(非住宅建築物編)、H25.11
* 国総研資料第702号	建築研究資料第140号: 低炭素建築物認定基準(平成24年12月公布)等関係技術資料 一次エネルギー消費量算定プログラム解説(建築物編)、H24.12

