# filled 表信息还原结果

已将用户指定的 `filtered_subjects_filled.csv` 全部 1857 人关联回用户指定的源表，恢复可一致确定的元数据，并保留不能唯一确定的全部影像候选。原始两张表未修改；输出不覆盖既有临床重算、队列、影像或实验结果。

**后续证据补充（2026-11-03）：** 已在 3003 的 IPython 历史中找回“按 MRI 文件名名单、每人取原表第一条”的选择代码。本报告及表格保留仅凭字段匹配时的候选结果；按历史规则进一步还原的 1857 条临床源记录和填补核验见[筛选代码恢复报告](../filtering_code_recovery_20261103/REPORT.md)。临床源记录的 Image ID 仍不等于已确认的实际 NIfTI 身份。

## 核心结果

| 核查项 | 结果 |
|---|---:|
| filled 表被试数 / 成功找到人口学锚定记录 | 1857 / 1857 |
| 原表精确人口学锚定记录 | 9864 |
| 已观测评分与 filled 无冲突的候选记录 | 9749，覆盖全部 1857 人 |
| 评分冲突候选 | 115 条，涉及 25 人、167 个评分单元格 |
| 人口学锚定后唯一源表记录 | 9 人 |
| 其余仍有多个 Image ID 候选 | 1848 人 |
| 五项评分全部有源表观测且全部相等 | 29 条源表记录，涉及 6 人 |

**“1857 人全部关联成功”指源表记录的匹配覆盖，不代表 1857 人实际使用的 MRI/PET Image ID 已全部确定。** 特别是 4317 条候选在源表中五项评分全部缺失，仅有人口学字段支持，不应被描述为评分一致验证通过。

## 使用哪个文件

1. [filled_restored.csv](filled_restored.csv)：主表，仍为 **1857 行**，原有 10 列及行顺序逐值保留。增加恢复字段、候选 Image ID 列表、评分证据和歧义状态。
2. [anchor_source_candidates.csv](anchor_source_candidates.csv)：**9864 行**完整源记录；源表全部 15 列逐值保留，并附 filled 记录编号、源记录编号、匹配依据、评分比较状态。用于查看每个 Image ID 对应的原始影像描述和评分。
3. [score_compatible_source_candidates.csv](score_compatible_source_candidates.csv)：**9749 行**评分无冲突候选，作为较窄的检索范围。原表缺失评分视为未知，不是与 filled 相等的观测；存在缺失评分的候选也不会因此被擅自丢弃。
4. [observed_score_conflicts.csv](observed_score_conflicts.csv)：167 条逐单元格差异，保留原始观测、filled 值、Image ID 和源记录定位。
5. [clinical_field_evidence.csv](clinical_field_evidence.csv)：1857×5＝9285 条逐被试/评分证据，区分原表缺失、原表观测与 filled 一致、原表观测与 filled 不同。
6. [unique_source_record_restorations.csv](unique_source_record_restorations.csv)：9 人在给定人口学锚定条件下对应唯一源记录的子表。仍需另证其是否就是实际 NIfTI 的来源。

CSV 使用 UTF-8 BOM。候选列表采用 JSON 数组文本，原表 Image ID 的数字字符串保持原样；用于 IDA 检索时可按平台要求添加 `I` 前缀。`*_csv_record_1based` 是从 1 开始的数据记录编号，不包括表头，也不是 notebook cell 编号。

## 匹配与恢复规则

第一层固定为 **Subject ID + Sex + Weight + Research Group + Age**。数值用 Decimal 精确比较，使 `30` 与 `30.0` 相等；不设年龄/体重容差，不改诊断标签，不跨年龄或阶段借用同一被试其他记录。文本匹配仅去除首尾空白，输出保留输入原字符串。

第二层比较 MMSE、GDSCALE、Global CDR、FAQ、NPI-Q：源记录有观测值时必须与 filled 相等，才进入评分无冲突候选表；源记录评分为空时保留未知，不以 filled 的值反填源记录。所有评分冲突记录仍完整保留在第一层候选表中。未依据“匹配评分个数最多”挑选影像，因为不同模态可能缺失不同评分。

主表中 `Phase`、`Modality`、`Description`、`Imaging Protocol`、`Image ID` 只有在该锚定下所有候选都存在且取值一致时才填写单值，否则留空并通过 `字段名__restoration_status` 标明原因。多个候选 ID 放入 `candidate_image_ids`；它们与具体描述、评分的对应关系以长表为准。

`score_compatible__字段名` 列提供基于评分无冲突候选的相应一致值，是进一步限制后的检索结果，不能替代第一层候选的冲突证据。`source_observed__评分名` 与 `source_evidence__评分名` 表示全部人口学锚定记录中的原始评分证据；filled 本身的五项评分完全不改。

`candidate_image_ids__MRI / PET_AV45 / PET_FDG / PET_TRACER_UNSPECIFIED / PET_MULTIPLE_TOKENS` 等列按源表模态及 Description 中的字面示踪剂词归类。通用 PET 名称不推断为 FDG；同时出现多个示踪剂词的描述保留多词歧义。此归类用于查找候选，不认证当前文件的 radiopharmaceutical。

## 哪些字段已经恢复

| 被删除字段 | 全部人口学锚定候选的恢复结果 | 评分无冲突候选的结果 |
|---|---|---|
| Phase | 1857 人均有唯一一致值 | 同左 |
| Modality | 1830 人一致，27 人有 MRI/PET 多值 | 1853 人一致，4 人仍多值 |
| Description | 10 人一致，1847 人多值 | 同左 |
| Image ID | 9 人唯一，1848 人多值 | 同左 |
| Imaging Protocol | 源表全部为空，无法恢复 | 同左 |

恢复的源记录阶段分布为 ADNI 1：502 人、ADNI GO：130 人、ADNI 2：696 人、ADNI 3：439 人、ADNI 4：90 人。这是 **filled 临床人口学锚定所对应记录的 Phase**，不替代每个实际 MRI/PET 的采集阶段核验。

## 评分交叉证据

| 评分 | 原表有唯一观测且与 filled 一致的人数 | 原表有唯一观测但与 filled 不同的人数 | 原表在该锚定下无观测的人数 |
|---|---:|---:|---:|
| MMSE | 464 | 0 | 1393 |
| GDSCALE | 462 | 0 | 1395 |
| Global CDR | 464 | 0 | 1393 |
| FAQ | 188 | 23 | 1646 |
| NPI-Q | 184 | 15 | 1658 |

FAQ 与 NPI-Q 差异涉及的人群有重叠，合计为 25 人。这里只记录两表的具体差异；不据此断言填补程序、错误原因或哪条影像记录实际被选用。源表没有观察值时，无法从 filled 的结果反向证明它是原始测量，也没有再次填补。

## 一个具体还原例子

filled 中 `002_S_0295`，年龄 84.9、体重 74.5、男性、CN，精确对应原表 **12 条 ADNI 1 MRI 记录**，Image ID 为：

`45111, 45112, 45113, 45114, 45106, 45107, 45108, 45109, 45110, 118671, 474728, 387726`。

这些记录的已观测 MMSE＝28、GDSCALE＝1、CDR＝0 均与 filled 一致，FAQ 和 NPI-Q 在这些源记录中缺失。它们包含多种处理版本；因此主表恢复 `Phase=ADNI 1`、`Modality=MRI`，保留 12 个候选，不将第一条 `45111` 强行认作实际影像。

同一被试在其他年龄/阶段还有 PET 或 MRI 记录，不会被合并到这条临床记录中。这也意味着 **单行 filled 临床人口学资料，不一定足以代表当前 MRI、AV45 和 FDG 的全部采集访视**。当前实体影像与这些候选之间仍需来源映射。

## 无法仅从这两张表恢复的信息

- 原表没有 Series ID、采集日期/时间或访视 ID；这些字段不能凭年龄和评分推算。前一轮从 DICOM 历史日志提取的日期与 Series ID 没有按 Subject ID 直接灌入本次结果，以免把不同扫描相互混配。
- 原表的 Imaging Protocol 全为空；影像描述虽保留 `GradWarp`、`N3m`、`Coreg`、`Uniform Resolution` 等文本，仍不足以恢复完整扫描仪与采集协议。
- 人口学锚定相同、评分也相同的多个处理版本，无法从现有投影唯一反演；独有的一条源记录也不等于实际 NIfTI 已确认。
- 没有将多个候选解释成不同访视，因为缺少采集日期，多个 Image ID 也可能来自同一次采集的不同处理版本。

## 验证与复现

[restore_filled.py](restore_filled.py) 直接读取用户指定的两张 CSV，不依赖历史分析结论、旧观测恢复表或前一轮的源表快照。运行命令（仓库根目录）：

```sh
/mnt/ssd/linshuijin/miniconda3/envs/xiaochou/bin/python reports/adni_image_acquisition_audit/filled_information_restoration_20261103/restore_filled.py
```

检查了全部 1857 行 filled 原值与顺序保持不变、全部 9864 条长表的 15 个源列与源记录逐值一致、源记录编号和被试对应正确、候选 Image ID 无重复、人口学锚定精确相等、全部被试仍有评分无冲突候选。输入文件运行前后 SHA-256 相同。

[summary.json](summary.json) 保存计数、规则、输入及脚本哈希；[validation.json](validation.json) 保存输出哈希和检查结果。这些是信息恢复及工程一致性检查，不是实际影像身份或采集协议的科学认证。
