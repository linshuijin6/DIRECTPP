# 3003 筛选与评分填补代码恢复

**已找回核心筛选、去重和评分填补代码，并与当前 1857 人 filled 表逐项核对。** 关键代码没有保存在现存 notebook 中，而是位于 `3003:/home/data/liutuo/.ipython/profile_default/history.sqlite` 的 **session 373，inputs 17–29**。session 373 的开始时间字段为 `2025-03-29 12:01:24.503055`；它不是每条输入的精确执行时间。

本次只读查询历史库、读取源码及 CSV，未执行历史代码、未重跑随机填补、未修改远端文件。历史输入证明存在并提交过这些代码；不单独证明每条历史输入均成功结束。下文将代码事实与当前文件的复核结果结合解释。

## 核心筛选逻辑

[session 373 / input 20 原代码摘录](history_session373_input020.py) 的步骤是：

1. 对 `/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/mri_strip` 调用 `os.listdir`。
2. 只取以 `_MRI.nii.gz` 结尾的文件，将后缀去掉作为 Subject ID。没有先排序。
3. 在 `ADNI MRI and FDG and AV45 csv.csv` 中查找相同 Subject ID。
4. 直接取该被试在当前 CSV 顺序中的 **第一条记录**：

```python
matched_rows = df[df['Subject ID'].astype(str) == file_name]
if not matched_rows.empty:
    unique_subjects[file_name] = matched_rows.iloc[0].to_dict()
```

5. 将结果写为 `filtered_subjects.csv`。字典保留遍历插入顺序，所以输出顺序跟随 MRI 目录枚举顺序。

**这一步没有使用年龄、评分阈值、PET 是否存在、扫描日期、MRI–PET 时间间隔或影像质量指标作为进一步纳入排除条件。** 年龄和评分来自被试第一条源记录，而不是代码按临床条件挑选出来的。`iloc[0]` 仅表示 CSV 第一条，不能改写为“最早扫描”“基线扫描”“最近 MRI”或“质量最好”。

该规则以已经存在的 `mri_strip` 文件为起点，不能解释更早的原始下载、DICOM/NIfTI 选择和去颅骨处理为什么最终得到这些文件。

## 评分填补链

- [input 21](history_session373_input021.py) 尝试从原表回填缺失 MMSE，但仍只看该被试原表第一条记录，不搜索后面的非缺失观测。按 input 20 的取首行逻辑和当前源表，这一步可额外回填的 MMSE 数为 0。
- [input 22](history_session373_input022.py) 重新读取 `filtered_subjects.csv`，对缺失 MMSE 按 Research Group 随机填值，写出 `filtered_subjects_filled.csv`。
- [input 23](history_session373_input023.py) 填补缺失 GDSCALE。
- [input 24](history_session373_input024.py) 填补缺失 Global CDR。
- [input 25](history_session373_input025.py) 填补缺失 FAQ。
- [input 26](history_session373_input026.py) 填补缺失 NPI-Q。
- inputs 23–26 均读写同一个 filled 文件；原本非缺失的相应评分保持不变。

代码中的缺失值规则如下。大括号表示随机选择集合，范围表示包含端点的随机整数；单值是固定赋值。

| 评分 | CN | EMCI | MCI | LMCI | AD |
|---|---|---|---|---|---|
| MMSE | {29,30} | {27,28} | {26,27} | {24,25} | {19,20,21} |
| GDSCALE | 0 | 1 | 2 | 3 | 5 |
| Global CDR | 0 | 0 或 0.5，概率 0.7/0.3 | 0 或 0.5，概率 0.3/0.7 | 0.5 | 1 |
| FAQ | {0,1} | 3–5 | 4–7 | 7–11 | 17–24 |
| NPI-Q | 0 | 1 | 3 | 4 | 5 |

没有将这些固定值称为“组均值”。本次未重新抽样，也未恢复原始随机状态；当前值落在代码允许的集合内，并不能证明已复现当年的具体随机序列或 CDR 抽样概率。

## 当前文件的逐项核对

| 核查项 | 结果 |
|---|---:|
| 当前 `mri_strip` 的 `_MRI.nii.gz` 文件数 | 1857 |
| 与 filled 被试集合一致 | 1857 / 1857 |
| 当前目录枚举顺序与 filled 行顺序一致 | 1857 / 1857 |
| filled 人口学字段与被试原表第一条记录相符 | 1857 / 1857 |
| 所选第一条记录中原本非缺失的五项评分 | 1751 个单元格，全部与 filled 一致 |
| 所选第一条记录中原本缺失的五项评分 | 7534 个单元格，现有值全部符合对应诊断组填补规则 |

| 评分 | 所选第一条源记录有观测 | 所选第一条源记录缺失，filled 有值 |
|---|---:|---:|
| MMSE | 464 | 1393 |
| GDSCALE | 462 | 1395 |
| Global CDR | 464 | 1393 |
| FAQ | 183 | 1674 |
| NPI-Q | 178 | 1679 |

这比单纯“字段相似”提供了更直接的流程依据。上一轮保留的多候选及冲突没有被删除；其中非首行的记录不再作为这次临床源记录选择的结果。不能因此认定其他访视或其他影像记录的评分有误。

## 按找回规则补全 1857 人的源信息

- [filled_restored_by_historical_selection.csv](filled_restored_by_historical_selection.csv)：1857 行。保留当前 filled 的原 10 列与顺序，恢复所选第一条记录的 Phase、Modality、Description、Imaging Protocol、Image ID，补充原始评分观测/缺失状态及源 CSV 记录号。
- [selected_source_rows.csv](selected_source_rows.csv)：对应的 1857 条源记录，完整保留源表 15 列；其中评分仍是未填补的源表观测。
- [score_value_provenance.csv](score_value_provenance.csv)：9285 条逐单元格证据，包括源值、filled 值、对应规则和历史输入编号。
- [score_provenance_by_group.csv](score_provenance_by_group.csv)：各诊断组的原始观测/缺失数，以及缺失位置当前 filled 值的实际分布。

**此表中的 Image ID 是“被用于抽取临床信息的第一条源记录的 Image ID”，不是已确认的当前 NIfTI Image ID。** 找回的代码按 Subject ID 取首行，并未限定源表记录的 Modality。1857 条所选记录实际包括 **1160 条 MRI、697 条 PET**。不能因为入组起点是 MRI 文件目录，就把所有所选记录的 Image ID 都解释成 MRI 的来源。

新表用 `image_id_scope` 为每行写明这个适用范围；实际 MRI、FDG、AV45 的采集身份和时间间隔仍需文件级对应证据。

用于 ADNI metadata 检索的逗号分隔名单已另存：

- [1857 条临床源记录 Image ID](image_ids_for_adni_metadata.md)：MRI 1160、PET 697，均带 `I` 前缀，按模态分为两个可复制代码块。
- [64510 条已知扩展候选 Image ID](image_ids_all_known_candidates.md)：当前名单在源表中的 MRI 30801、PET 32662，另加历史 AV45 原始影像候选 1047。含不同访视与处理版本，供首行记录不足以定位实际扫描时补查；不等于项目使用了全部这些影像，也不要求重新下载全部影像。

[image_id_lists_provenance.json](image_id_lists_provenance.json) 保存名单来源、范围、分组数量及输入/输出哈希。已检查保存后的 ID 数量、唯一性、`I` 前缀和英文逗号分隔格式。

## 找到的下游代码

[session 373 / input 29](history_session373_input029.py) 将 filled 表逐行转为 `Description` 并写出 `filtered_subjects_with_description.csv`。它与现存 `chu li shu ju.ipynb` 的零起算 cell 6 对应。文本直接编码 filled 中的年龄、性别、体重和五项评分。

`mri2pet _clip_pretrain .ipynb` 零起算 cell 3，以及 `mri2pet _two trace_new.ipynb` 零起算 cell 2，继续消费该描述表并与处理后影像路径配对。这些是下游使用入口，不是产生 1857 人名单的原始筛选实现。本次未将其历史训练划分或运行状态扩展为新的追查任务。

## 尚未找齐的处理步骤

1. input 20 保存的是完整源记录，后续已找回的填补代码也没有删除那五个元数据列；当前 filled 表只有 10 列。**删除 Phase、Modality、Description、Imaging Protocol、Image ID 的具体命令或编辑操作尚未定位。** 不能将这一步虚构进已找到的代码。
2. 更早的原始影像下载、序列选择、重命名、转换及 MRI 去颅骨成功/失败处理，仍未由本次筛选代码解释。
3. 源 CSV 本身没有采集日期或 Series ID，Imaging Protocol 全为空；这些字段不会因为临床首行选择规则找回而自动恢复。
4. 不能仅凭历史输入和当前文件一致，证明原始运行每一步的输出收据、随机状态和后续所有修改均已完整保留。

## `processed_files.txt` 的来源补充

[session 287 / input 19](history_session287_input019.py) 是另一个直接命中的历史输入：它遍历 `ADNI - av45`，对路径字符串执行 `.replace('/ADNI_Brain_PET__Raw_AV45', '')` 和时间戳正则替换，然后把字符串写成 `processed_files.txt`。

因此，该文件是**路径字符串清理结果**的历史线索，不能作为“影像转换或预处理成功日志”使用；其中路径也不一定是未经改变的原始完整路径。文件名中的 Image ID/Series ID 仍可作为候选标识；路径不存在不证明 DICOM 被删除。本次没有将这些路径或日期按 Subject ID 灌入新恢复表。

## 搜索范围与可复查证据

最初检查 CSV 所在目录及父目录没有发现直接附带的筛选脚本。随后检索 `/home/data/liutuo/code` 顶层、`.ipynb_checkpoints` 和相邻 `test` 中 **49 个源码文件、957 个代码单元**；只读取 notebook 代码，不导入输出、图像或训练进度。未扫描整盘、模型依赖库或无关账号资料。

由于现存源码只保留下游读取，进一步对作者账号 IPython 历史库执行与这两份 CSV 名称、列删除操作和 FAQ 规则相关的定向只读查询，最终定位上述输入。数据库以 `mode=ro&immutable=1` 和 `query_only=ON` 打开，检查不存在 WAL，读取前后文件 SHA-256 一致。

- [code_evidence_3003.json](code_evidence_3003.json)：原历史库路径、SHA-256、session 信息、选定历史输入原文、源码清单和哈希、零起算 notebook cell 编号、当前 MRI 目录枚举结果及远端 CSV 哈希。
- [collect_3003_history.py](collect_3003_history.py)：远端只读采集代码。只打印 JSON，不执行摘录代码。
- [reconstruct_selection.py](reconstruct_selection.py)：根据恢复的首行规则检查本地两份 CSV 并生成结果；不执行任何历史代码或随机抽样。
- [summary.json](summary.json)：全部计数、原表哈希、脚本哈希和未解决事项。

`history_session*_input*.py` 和 `notebook_*_cell*.py` 是带原路径、原文件哈希及 source 哈希的**派生源码摘录**，供核验原件。它们不作为独立实现或可直接运行的最终管线。
