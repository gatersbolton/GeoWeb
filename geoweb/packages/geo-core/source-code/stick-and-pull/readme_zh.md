# stick-and-pull 去伪影

用途
- 去除成像数据中的 stick-and-pull 类伪影。

输入
- 图像（PNG/JPG）。如有速度曲线 CSV 也可作为可选输入。

输出
- 去伪影后的图像（PNG）。
- CSV：`row_index`、`depth_norm`、`speed_rel`。

说明
- 参考实现：`fix_stick_pull.py`。
- 默认示例图：`stick_pull.png`。
