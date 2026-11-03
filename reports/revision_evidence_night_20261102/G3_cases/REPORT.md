# R3-11 fixed-rule case figures

selection_manifest_internal.csv在任何图像读取前冻结并记录SHA256。分别在W1 Full e165全体积FDG1598/AV451365逐人SSIM中，按线性经验中位/第10百分位最近者及最低值选择；平局按PTID，不按视觉替换。6张图包含MRI、Real、Syn和绝对误差的三正交中央数组切片。所有PET与误差尺度0–1，单位normalized intensity/arbitrary units；未逐图重拉伸或用预测affine证明物理左右。

两示踪剂最低SSIM均为016_S_4952（FDG.196919、AV45.173244），恰是预先存在的MRI/mask QC失败病例。它在Full全体积指标中保留、在brain-mask分析中按既定规则排除。因此这两张worst-case图主要提示既存QC/配对预处理问题，不能单独归因于生成器典型失败。此处按预先冻结的全体积排序保留它，没有换成更好看的病例，也没有重建mask或重算masked指标。需要在投稿选图时把它明确标为质量核查病例。
