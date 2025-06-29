This section explains the calculation method of primary energy consumption in Builelib.  
While the calculation logic of Builelib is based on the Japanese Energy Efficiency Standards for non-residential buildings, it includes various original calculations.  
Therefore, please note that the results may differ from those obtained using the official energy efficiency standards program.

The following constants are commonly used across the calculations for all building systems.

<div style="text-align: center; margin-bottom: 0.01em;">Table 1. Common Constants</div>
<table border="1" style="margin-top: 0.01;">
  <colgroup>
    <col style="width: 20%;">
    <col style="width: 50%;">
    <col style="width: 15%;">
    <col style="width: 15%;">
  </colgroup>
  <tr>
    <th>Constant</th> <th>Description</th> <th>Value</th> <th>Unit</th>
  </tr>
  <tr>
    <td>$f_{prim,e}$</td ><td>Conversion factor from 1 kWh of electricity to heat energy</td> <td>9760</td> <td>kJ/kWh</td>
  </tr>
  <tr>
    <td>$C_{a}$</td> <td>Specific heat capacity of dry air at constant pressure</td> <td>1.006</td> <td>kJ⁄(kg·K)</td>
  </tr>
  <tr>
    <td>$C_{wv}$</td> <td>Specific heat capacity of water vapor at constant pressure</td> <td>1.805</td> <td>kJ⁄(kg·K)</td>
  </tr>
  <tr>
    <td>$C_{w}$</td> <td>Specific heat capacity of water at constant pressure</td> <td>4.186</td> <td>kJ⁄(kg·K)</td>
  </tr>
  <tr>
    <td>$L_{w}$</td> <td>Latent heat of vaporization of water</td> <td>2502</td> <td>kJ⁄(kg·K)</td>
  </tr>
  <tr>
    <td>$\rho_{w}$</td> <td>Density of water (at atmospheric pressure, 7°C)</td> <td>1000</td> <td>kg⁄$m^{3}$</td>
  </tr>
  <tr>
    <td>$\alpha_{o}$</td> <td>Total heat transfer coefficient on the exterior side</td> <td>1/0.04</td> <td>W/($m^{2}$·K)</td>
  </tr>
  <tr>
    <td>$\alpha_{i}$</td> <td>Total heat transfer coefficient on the interior side</td> <td>1/0.11</td> <td>W/($m^{2}$·K)</td>
  </tr>
  <tr>
    <td>$f_{fan,heat}$</td> <td>Heat generation ratio of fans</td> <td>0.84</td> <td>-</td>
  </tr>
  <tr>
    <td>$f_{pump,heat}$</td> <td>Heat generation ratio of pumps</td> <td>0.84</td> <td>-</td>
  </tr>
  <tr>
    <td>$f_{ref,ts,loss}$</td> <td>Heat loss factor of thermal storage tanks</td> <td>0.03</td> <td>-</td>
  </tr>
</table>


## Chapter 1: Method for Calculating the Design Primary Energy Consumption

This chapter describes the method for calculating the design primary energy consumption.  
The design primary energy consumption $E_{T}$ [GJ/year] is calculated using the following equation, and the result is rounded up to the second decimal place.

---
$$
E_{T} = (E_{AC} + E_{V} + E_{L} + E_{HW} + E_{EV} - E_{PV} - E_{CGS} + E_{M}) \times 10^{-3}
$$
---

- $E_{AC}$ is the design primary energy consumption of the air-conditioning system [MJ/year], described in Chapter 2.  
- $E_{V}$ is the design primary energy consumption of the mechanical ventilation system [MJ/year], described in Chapter 3.  
- $E_{L}$ is the design primary energy consumption of the lighting system [MJ/year], described in Chapter 4.  
- $E_{HW}$ is the design primary energy consumption of the hot water supply system [MJ/year], described in Chapter 5.  
- $E_{EV}$ is the design primary energy consumption of elevators [MJ/year], described in Chapter 6.  
- $E_{PV}$ is the reduction in primary energy consumption due to photovoltaic (PV) systems [MJ/year], described in Chapter 7.  
- $E_{CGS}$ is the reduction in primary energy consumption due to cogeneration systems [MJ/year], described in Chapter 8.  
- $E_{M}$ is the primary energy consumption from other sources [MJ/year], described in Chapter 9.

## Chapter 2: Evaluation of Air-Conditioning Systems

[Link to Chapter 2](./Reference/EngineeringReference_chapter02-en.html)

## Chapter 3: Evaluation of Mechanical Ventilation Systems

[Link to Chapter 3](./Reference/EngineeringReference_chapter03-en.html)

## Chapter 4: Evaluation of Lighting Systems

[Link to Chapter 4](./Reference/EngineeringReference_chapter04-en.html)

## Chapter 5: Evaluation of Hot Water Supply Systems

[Link to Chapter 5](./Reference/EngineeringReference_chapter05-en.html)

## Chapter 6: Evaluation of Elevators

[Link to Chapter 6](./Reference/EngineeringReference_chapter06-en.html)

## Chapter 7: Evaluation Method for Photovoltaic Systems

The evaluation method for photovoltaic systems is the same as that used in the residential version of the Energy Performance Calculation Program [(Specification)](https://www.kenken.go.jp/becc/documents/house/9-1_191119_v08_PVer0207.pdf).  
However, if any amount of electricity generated is sold, the PV system is excluded from the evaluation.  
If the generated electricity is used entirely for self-consumption (i.e., not sold), the system is included in the evaluation.  
Additionally, electricity generated by PV systems installed on buildings other than the subject building is not included in the evaluation.

## Chapter 8: Evaluation Method for Cogeneration Systems

[Link to Chapter 8](./Reference/EngineeringReference_chapter08-en.html)

## Chapter 9: Calculation Method for Other Primary Energy Consumption

[Link to Chapter 9](./Reference/EngineeringReference_chapter09-en.html)

## Chapter 10: Method for Calculating the Reference Primary Energy Consumption

[Link to Chapter 10](./Reference/EngineeringReference_chapter10-en.html)


## Databases Used for Calculation

* [Standard Room Usage Conditions](https://www.kenken.go.jp/becc/documents/building/Definitions/ROOM_SPEC_H28.zip)  
* [Details of Standard Room Usage Conditions](https://www.kenken.go.jp/becc/documents/building/Definitions/RoomUsageCondition_20140303.pdf)  
* [Calendar Patterns](https://www.kenken.go.jp/becc/documents/building/Definitions/CalenderPattern_20140303.pdf)  
* [List of Thermal Properties of Building Materials](https://www.kenken.go.jp/becc/documents/building/Definitions/HeatThermalConductivity.zip)  
* [List of Window Thermal Performance](https://www.kenken.go.jp/becc/documents/building/Definitions/WindowHeatTransferPerformance_H30_181005.zip)  
* [Load Calculation Coefficients](https://www.kenken.go.jp/becc/documents/building/Definitions/QROOM_COEFFI.zip)  
* [Performance Coefficients of Heat Source Equipment](https://www.kenken.go.jp/becc/documents/building/Definitions/REFLIST_H28_REFCURVE_H28.zip)  


## References

* Building Research Report No. 201: Study on Primary Energy Conversion Factors for New District Heating and Cooling Plants, Sep. 2020  
* NILIM Report No. 1107: Survey on Building Envelope and Equipment Design Specifications and Actual Energy Performance of Non-Residential Buildings – Analysis of Input/Output Data from the Energy Efficiency Compliance Program –, Mar. 2020  
* Building Research Report No. 191: Study on the Advancement of Performance Evaluation Methods for Commercial Cogeneration Systems, Apr. 2019  
* Building Research Report No. 190: Study on Energy Consumption Evaluation Methods Considering Latent Heat Load Processing Mechanisms of Various HVAC Systems, Apr. 2019  
* Building Research Report No. 188: Study on the Estimation Method of Annual Power Generation from Photovoltaic Systems, Jan. 2018  
* Building Research Report No. 187: Survey on Existing Test Methods for the Energy Efficiency of Building Equipment and Systems, Sep. 2017  
* NILIM Report No. 974 / Building Research Report No. 183: Technical Documentation on the 2016 Energy Efficiency Standards – Guide to the Model Building Method Input Support Tool –, Jun. 2017  
* NILIM Report No. 973 / Building Research Report No. 182: Technical Documentation on the 2016 Energy Efficiency Standards – Guide to the Energy Consumption Calculation Program (Non-residential version) –, Jun. 2017  
* Building Research Report No. 177: Empirical Evaluation of Energy-Saving Effects from Control of Commercial HVAC and Hot Water Systems, Nov. 2016  
* Building Research Report No. 176: Basic Survey on Energy Consumption Evaluation Methods for Commercial Buildings, Nov. 2016  
* NILIM Report No. 765 / Building Research Report No. 152: Technical Documentation on the 2013 Energy Efficiency Standards – Guide to the Envelope Performance and Primary Energy Consumption Evaluation Program using the Model Building Method –, Nov. 2013  
* NILIM Report No. 764 / Building Research Report No. 151: Technical Documentation on the 2013 Energy Efficiency Standards – Guide to the Primary Energy Consumption Calculation Program using the Key Room Input Method –, Nov. 2013  
* NILIM Report No. 763 / Building Research Report No. 150: Technical Documentation on the 2013 Energy Efficiency Standards – Guide to the Building Envelope Performance Evaluation Program for Non-Residential Buildings –, Nov. 2013  
* NILIM Report No. 762 / Building Research Report No. 149: Technical Documentation on the 2013 Energy Efficiency Standards – Guide to the Primary Energy Consumption Calculation Program (Non-Residential Buildings Edition) –, Nov. 2013  
* NILIM Report No. 702 / Building Research Report No. 140: Technical Documentation on the Low-Carbon Building Certification Standards (Announced Dec. 2012) – Guide to the Primary Energy Consumption Calculation Program (Buildings Edition) –, Dec. 2012  


