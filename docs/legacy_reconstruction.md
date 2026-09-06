# Legacy reconstruction

## Source materials supplied by the author

| File | Useful evidence recovered |
|---|---|
| `Solar for my house.pptx` | Solar, inverter, panel, battery, grid and monitoring architecture |
| `solar feasibility updated 2015.xls` | Appliance inventories for 3–6 bedroom houses, peak-load calculations, panel/battery/controller/inverter counts, equipment costs and simple payback |
| `Solar biogas hybird system.pptx` | Solar–biogas concept, DC/AC bus architecture, Middle East and camel-waste motivation, 25-year horizon and an early cost breakdown |
| `Solar and Biogas cost.pptx` | 9,000 kWh/day demand, 34.5 tonnes/day manure from 2,300 camels, 35% conversion efficiency, 25-year horizon and separate solar/biogas cost tables |

The uploaded files are not redistributed in this public repository. Only the author’s recovered high-level assumptions and a transparent critique are represented.

## Recovered numerical anchors

- Load: 9,000 kWh/day, or 3,285,000 kWh/year.
- Feedstock: 34.5 tonnes/day wet camel manure.
- Legacy electrical efficiency: 35%.
- Project horizon: 25 years.
- Legacy biogas-system total: AED 57.42 million, combining equipment and 25 years of transport, maintenance and labour.
- Legacy solar total: approximately AED 4.06 million for 1,013 panels and associated equipment/cleaning.

## Corrections made

### Manure-to-methane conversion

The legacy calculation treated 60% methane concentration as if 60% of manure mass became methane. Methane fraction describes the gas mixture, not wet-feedstock mass conversion. The reconstruction therefore separates feedstock mass, specific biogas yield, methane volume fraction, methane energy content and generator efficiency.

### Power versus energy

The house workbook sized panels from coincident appliance watts. Peak power is necessary for inverter sizing but insufficient for annual feasibility. The new model reconciles every representative hour and verifies annual energy.

### Battery operation

Legacy battery counts had no state-of-charge dynamics. The new model enforces energy capacity, power capacity, efficiency, minimum/maximum SOC and daily cyclic balance.

### Lifecycle cost

Initial equipment cost and 25 years of recurring cost were combined in several legacy totals. The reconstruction separates CAPEX, fixed O&M, variable cost, replacement timing and discounting.

## What was not claimed

The original lost optimisation code was not available. This repository is a clean-room reconstruction, not a recovery of the exact program. No reference result is attributed to Yellow Door Energy or represented as a deployed system outcome.
