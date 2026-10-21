# Shri Sahyadri field map

All coordinates live in `src/pdf/layout.py` and are in **template points**,
measured from the top-left of the original 594 x 936 pt page
(`templates/Shri_Sahyadri.pdf`) on a 288-dpi raster. The template is placed
unchanged on A4 (scale 0.8995, centred horizontally).

Measured reference points:

| Element | Position (pt) |
|---|---|
| Name writing line | y = 201.07, x 203.5-432 |
| Date printed `/`, `/20` | x 492-494.75, 520.25-533.5; baseline 207.95 |
| Top rows (birth / rashi / lagna) | 227.75 / 247.75 / 268.0 / 288.0 |
| Label cells | 54-106.25, 228.25-280.25, 402.25-454.25 |
| लग्न printed slashes | x 128.75-133.5 and 152.5-157.25 |
| पत्रिकेतील दोष rows | 296, 318.5, 341.5, 364.5, 385.5 |
| उपाय rows | 385.5, 410.75, 433.75, 456.75, 479.75 |
| Table rows 1-14 | 499.88 ... 813.25 (see `ROW_*` constants) |
| Row 13 printed slashes | 246.5-252, 272-277.5, 385.5-391, 411-416.5 |
| सूचना 6 writing line | y = 865.5, x 98-491 |

Placement rules are described at the top of `layout.py`. The original
template is never edited; printed separators (`/`, `/20`, `दि.`) stay as
they are and values are written around them.
