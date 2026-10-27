# 元素默认能量参数与来源

更新日期：2026-10-27。单位均为 eV。

独立添加或切换元素时，现在从同一份 92 元素数据表读取位移、晶格和表面能量建议值。它们是可修改的起始建议，**不是已完整恢复的 SRIM 默认数据库，也不是适用于所有化合物的元素常数**。

完整数值见 [逐元素 CSV](element-defaults.csv)，运行时数据及逐字段来源见 [element_defaults.py](../gsrim/element_defaults.py)。原生桌面可将鼠标停在能量单元格上查看建议来源。

## 1. 数据优先级

| 数据 | 使用办法 | 限制 |
| --- | --- | --- |
| 用户指定的 SRIM-RE / ATOMDATA.csv | 取正值升华热作为表面结合能的初始估计；补齐缺失的元素身份 | 原表没有逐元素位移能和晶格能；升华热为零按缺失处理 |
| 已保存 TRIM 样例 | H 用 10 / 3 / 2；O 用 28 / 3 / 2；Ga 用 25 / 3 / 2.82 | H 来自 O/H 样例，O/Ga 来自 Ga₂O₃ 样例；不宣称是纯元素通用值 |
| SRIM 官方损伤教程 | Si 用 15 / 2 / 4.7 | 是该教程给出的基线，不代表所有版本或 Si 化合物 |
| Konobeyev 等（2017）表 4 | 对其余有数据元素使用取向平均位移阈能，并保留论文不确定度 | 表 4 有 81 种元素条目，包含估计和采用值；不使用表 2 的最小值或表 6 的有效能量 |
| 晶格能缺少逐元素数据 | 除上述有明确记录的项外，暂用 3 eV，并标注为模型假设 | 依据官方说明的典型 1～3 eV 范围选取；不是逐元素实测表 |
| 核对的来源仍缺数值 | 显示空白、提示按具体靶材填写，开始计算时阻止缺失项 | 不回填统一 25 / 3 / 2，不把未知解释成零 |

Si 的论文表 4 平均位移阈能为 37 eV；当前优先采用官方 SRIM 教程的 15 eV，以明确区分“教程基线”和“论文平均值”。两种定义不应无说明地混用。

## 2. 使用行为

- 添加元素：填入该元素的建议；元素范围补齐为 H～U，共 92 种。
- 切换元素：更新原子序数、质量和三个能量建议，保留原子配比。
- 已有项目、断点和结果：保留其中明确保存的数值，不自动迁移到新建议。
- 纯元素字典：与单独添加该元素保持一致。
- 化合物字典：保留原来显式指定的材料参数，避免用纯元素建议覆盖材料设置；原有预设仍需核对来源。
- 可选网页入口：从同一个 Python 数据源取默认值，未知值保持空白。

例如：Si 为 15 / 2 / 4.7，H 为 10 / 3 / 2，Fe 为 40 / 3 / 4.34，W 为 90 / 3 / 8.68。

## 3. 明确缺失的项

位移能尚缺：He、N、F、Ne、Cl、Ar、Kr、Xe、Rn。

表面能尚缺：He、N、F、Ne、Cl、Ar、Br、Kr、Tc、I、Xe、Pm、At、Rn、Fr、Ra、Ac、Pa。

这些元素没有被排除：可继续选择并输入实际材料参数。例如 He 作为入射离子不需要填写靶原子能量；只有作为靶层组分时才需要这些参数。没有证据时，不能用任意数字使不同元素看起来不同。

## 4. 参考与复现

1. ATOMDATA 元素属性导出表与明确标注的材料输入示例。原始文件的指纹和来源标识保留在运行时参数表中。
2. [SRIM：TRIM Setup and Input](https://www.srim.org/SRIM/SRIM%2008.pdf)，Damage Energies of Target Atoms：升华热估计、晶格能典型范围和材料依赖。
3. [SRIM Tutorial 4：Target Damage](https://www.srim.org/SRIM/Tutorials/SRIM%20Tutorial%204%20-%20Target%20Damage.pdf)，Si 示例值。
4. A. Yu. Konobeyev, U. Fischer, Yu. A. Korovin, S. P. Simakov, “Evaluation of effective threshold displacement energies and other data required for the calculation of advanced atomic displacement cross-sections”, Nuclear Energy and Technology 3 (2017), 169–175，**表 4，期刊第 172 页**。[DOI](https://doi.org/10.1016/j.nucet.2017.08.007) · [作者机构存档](https://publikationen.bibliothek.kit.edu/1000076502)。

运行时直接使用随源码提供的预生成建议表，不依赖原始数据目录或论文文件。需要自行重新生成时，向工具明确指定输入：

```powershell
.\.venv\Scripts\python.exe build/generate_element_defaults.py --tables data/element-input --paper-dir data/element-paper
```

其中输入目录应由使用者准备，分别包含 `ATOMDATA.csv` 以及 `Konobeyev-2017.pdf`、以版面模式提取的 `Konobeyev-2017.txt`；生成工具不是运行桌面程序的前置步骤。
