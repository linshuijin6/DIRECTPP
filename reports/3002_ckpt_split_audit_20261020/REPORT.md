```text
3002 三份候选 checkpoint 的 train/val 划分核查
核查日期：2026-10-20（Asia/Shanghai）
范围：01.30_151382、02.03_614278、02.03_1709820；只读核对 checkpoint、日志、配置、Git历史名单与源码。

结论
三份权重的实际日志人数已定位，但不是同一套划分：
01.30_151382/ckpt_epoch200.pt：train=990条、val=109条，合计1099条。
02.03_614278/ckpt_epoch190.pt：train=1224条、val=136条，合计1360条。
02.03_1709820/ckpt_epoch200.pt：train=1224条、val=136条，合计1360条。
这里是样本条目数，不能直接称为独立受试者人数。

从3002仓库Git历史恢复了与人数及train/val首条完整记录均匹配的两套候选名单。
但是三份checkpoint均只含 model、optimizer、epoch、global_step；没有名单、split seed、split hash、JSON路径或Git commit。
运行目录也没有独立划分manifest。日志只打印人数和第一条样本，不记录完整名单。
因此：人数是运行证据已确认；完整逐条名单是高匹配历史候选，尚无运行时完整哈希绑定。

一、逐运行定位

共同的历史读取入口（位于3002）：
/home/ssddata/linshuijin/replicaLT/train_data_with_description.json
/home/ssddata/linshuijin/replicaLT/val_data_with_description.json
这些入口在后来被改写，不能直接使用今天的内容代表上述训练。

A. 01.30_151382
checkpoint：/home/ssddata/linshuijin/replicaLT/runs/01.30_151382/ckpt_epoch200.pt
日志：/home/ssddata/linshuijin/replicaLT/0130.main.log
原始日志第34行：Loaded 990 training samples.
原始日志第36行：Loaded 109 validation samples.
日志train首条：021_S_10774，2025/6/3，MRI I11285144。
日志val首条：037_S_6963，2021/12/17，MRI I1478584。
候选来源：7bc69a2fb5952bcf760dd3c53aba3a2822a68692（2026-01-28）。
同一JSON blob在c478758（2026-01-30）和3484361（2026-02-03）仍可回收。
回收文件：historical_json/7bc69a2__train_data_with_description.json
          historical_json/7bc69a2__val_data_with_description.json
train/val首条全部日志字段均与候选一致，不只是PTID或人数相同。
该候选在运行开始前已经提交；TensorBoard文件名起始时间为2026-01-30 17:43:19 +08:00。
候选独立PTID：train=862、val=109；两边共用32个PTID。
内部epoch=199，global_step=49600；49600/200=248，与ceil(990/4)=248一致。

B. 02.03_614278
checkpoint：/home/ssddata/linshuijin/replicaLT/runs/02.03_614278/ckpt_epoch190.pt
日志：/home/ssddata/linshuijin/replicaLT/0203.me.train.log
原始日志第34行：Loaded 1224 training samples.
原始日志第36行：Loaded 136 validation samples.
日志train首条：082_S_6287，2018-05-15，MRI I998048。
日志val首条：005_S_10100，2024-05-13，MRI I10460270。
候选来源：9ba7133bf2eff9c112aaa439dc19f5223c5bca31（2026-02-05 21:25:54 +08:00）。
回收文件：historical_json/9ba7133__train_data_with_description.json
          historical_json/9ba7133__val_data_with_description.json
train/val首条全部日志字段均与候选一致。
该快照晚于运行开始时间2026-02-03 19:52:18 +08:00，故只能作事后留存的匹配候选。
候选独立PTID：train=845、val=133；两边共用72个PTID。
内部epoch=189，global_step=232560；232560/190=1224，与bs=1及日志人数一致。

C. 02.03_1709820
checkpoint：/home/ssddata/linshuijin/replicaLT/runs/02.03_1709820/ckpt_epoch200.pt
日志：/home/ssddata/linshuijin/replicaLT/0203.LT.main.log
原始日志第7行：Loaded 1224 training samples.
原始日志第9行：Loaded 136 validation samples.
train/val首条完整日志记录均与B相同，且同样匹配9ba7133候选名单。
运行开始时间2026-02-03 23:49:38 +08:00，同样早于候选快照提交。
所以B/C“匹配同一候选名单”，不是已用完整哈希证明B/C历史实际逐条名单完全相同。
内部epoch=199，global_step=214200；214200/200=1071。
候选train1224条中，有TAU或AV45非占位路径的恰为1071条，其余153条两者均缺失。
历史main.py候选源码会在两种目标都为零时continue；该差异与跳过逻辑一致。
候选val136条中，有TAU或AV45非占位路径的为115条。
以上路径可用性仅按None/明确zero占位命名计算，未读取影像以核实其数值；也不把136条val改称115条加载名单。

二、实际划分由什么控制
历史train.py在legacy模式选择根目录上述两个JSON。
c478758:train.py第637行虽然调用train_test_split(..., random_state=42)，
但第642–651行在JSON已经存在时跳过保存，第653–662行随后重新读取既有JSON。
两份legacy日志均出现“JSON files already exist. Skipping save step.”。
因此不能只凭random_state=42，就声称本次运行重新生成了一个seed42划分；实际加载名单由已有JSON控制。
历史main.py直接读取同名根目录JSON，train_test_split部分为注释。
快照代码不是由checkpoint保存的精确源码收据，解释上述执行时同时以实际日志为证据。
未重新运行历史训练脚本，也未为了重建划分执行其数据准备逻辑。

三、候选名单的身份核对（限定这两套名单）
候选版本   train条目/独立PTID   val条目/独立PTID   train∩val PTID   相同PTID+MRI image_id
7bc69a2    990 / 862             109 / 109          32              1
9ba7133    1224 / 845            136 / 133          72              0

两套候选都不满足按PTID互斥，不能把它们描述为subject-disjoint。
7bc69a2中同一MRI身份为127_S_6147、I11175778：
train行798的examdate为2025/3/26，val行97为2025/2/17，但MRI路径相同。
详见shared_mri_records_7bc69a2.csv；它说明仅以examdate不同判断影像不同不可靠。
9ba7133中相同PTID+归一化examdate有30组，但MRI image_id交集为0；不能把同日记录直接当作同一MRI扫描。
逐模态PET身份按(PTID, modality, 文件名末尾PET image_id)比较，剔除明确zero占位路径：
7bc69a2：FDG=0、AV45=0、TAU=1个交集；9ba7133：FDG=2、AV45=8、TAU=26个交集。
这些是候选名单内的交集事实，不扩展为原稿最终运行的整体结论。

四、排除当前名单的混用
3002当前根目录JSON：train=949、val=95，与三份运行日志均不一致。
其身份划分可回查到2bfadb8（2026-03-20），内容后来在3d44206（2026-05-19）添加plasma字段。
当前这套的独立PTID为720/80，PTID交集为0；这是后来的另一套划分，不可追溯替换1–2月运行。
根目录fixed_split.json的mtime为2026-02-26，也不是这三份运行的冻结收据。
adapter_finetune/json历史名单583/64同样与运行日志不匹配；legacy模式也不选择该入口。

五、可复查文件与验证范围
candidate_membership_7bc69a2.csv：990/109候选的逐条split、PTID、日期、MRI/PET路径及模态路径可用性。
candidate_membership_9ba7133.csv：1224/136候选的相同格式逐条清单。
run_summary.csv、run_split_mapping.json：checkpoint → 实际日志人数 → Git候选名单 → 证据等级。
historical_receipts.json：原节点、Git commit/blob、源路径、源SHA256、提取路径和日志首条原始记录。
historical_json/、historical_source/：Git只读导出；未覆盖服务器原名单或源码。
checkpoint_metadata.json：本轮重新CPU weights_only加载的checkpoint元数据，SHA与上一轮一致。
membership_checks.json：PTID、归一化日期、MRI及逐模态PET身份集合核对。
tensorboard_receipts.json：三份事件文件完整TFRecord边界读取，筛查text_summary及常见split名单/hash字段未找到补充文本收据；未解码图像。
recheck_membership.py：只读复核源SHA、名单人数和交集；不访问影像、不导入或执行训练脚本。
计步吻合、首条吻合、完整名单哈希绑定是不同证据强度；本轮保留最后一项缺口。
```
