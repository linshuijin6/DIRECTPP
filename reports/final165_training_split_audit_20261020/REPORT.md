```text
first_part_165.pth：训练/验证名单、原始划分代码与执行历史核查
日期：2026-10-20（Asia/Shanghai）
口径更正：有关1856人实际训练归属的判断已收窄；见../original_directpp_329_inference_20261020/membership_semantics_correction.json。
目标SHA256：fa43adae089aefbe66df8d1f196a618662b75dbdc880cce10923dd22b844165e

结论
1. 找到名为train_data_1856_first_part_165.json和val_data_1_first_part_165.json的1856/1对应文件；val文件仅含011_S_4105（CN）。
   2026-10-20口径更正：文件名、准备源码和推理loader身份不等于实际训练队列；当前不能据此单独认证165曾用完整1856人训练。
   这不是只按人数或文件名猜测：你在2026-10-16提供过这两份165对应名单；本轮复核了原始对话来源。
   提供文件、DIRECTPP原始归档、原3002当前文件三方SHA完全一致，且原始划分算法能逐条、按完整顺序重建它们。
2. 原始notebook每次重执行“数据准备/划分cell”会重新计算并无条件覆盖JSON；seed固定42，目录先排序。
   同一候选被试集合、排序、test_size和实现条件下，重复执行得到同一名单，不是每次随机换一批人。
   单独重跑训练/续训cell不会再次划分；训练cell直接使用已建立的train_loader/val_loader。
3. 找到原作者3002的真实IPython输入历史：session77先执行同版划分、名单读取、loader构建，随后执行加载154的续训源码。
   这些源码与new-final notebook对应cell逐字一致（忽略首尾空白），明显强于只看当前notebook文件。
4. 你自己的3002执行历史独立记录了先使用test_size=1、随后改成约10%验证集的过程，与本轮补充说明一致。
   1672/185是这次test_size变化能够确定性重建的另一分支，不能替换原165的1856/1对应名单。
5. 原始代码在这里定义的是train/val，没有独立test名单。不能把1人val称为另有一套大规模test队列。
目前所有必要文件均可读，未使用sudo。

一、对应名单与实物权重
权重项目入口：
results/checkpoints/vscode-3002/home/ssddata/liutuo/checkpoint/mri2pet _two trace_add clip_flow_noHistogramNormalized/first_part_165.pth
原3002：/home/ssddata/liutuo/checkpoint/mri2pet _two trace_add clip_flow_noHistogramNormalized/first_part_165.pth
原节点当前SHA与归档一致，内部epoch=164，保留model/optimizer/epoch三项。

此前由你提供的对应名单，现保留于：
appendix/legacy_only/5_data_splits/train_data_1856_first_part_165.json
appendix/legacy_only/5_data_splits/val_data_1_first_part_165.json
train SHA：cb21eeabd8b0513ee15ebd183eb14b88abef9d89788b1ce5ff007c1fea079103
val SHA：3c9ea3b9e3afaa3aca66fcda8eee7626519f6edde5bc6c476febf518cee47e9b
train：1856条、1856个唯一PTID；val：1条、1个PTID；交集0；合并完整覆盖指定CSV的1857人。
本报告另存supplied_train_1856.json、supplied_val_1.json、train_val_membership.csv，未修改原件。

2026-10-16的final165_split_receipt.json明确记录用户提供对应关系及目标checkpoint SHA。
本轮复核原对话：你回答final checkpoint名单查询时，提供了原5_data_splits下的这两条路径。
来源说明是外部证据，不是checkpoint内嵌manifest；上一轮报告漏读了它，导致对应关系被描述得过于不确定。

二、原始划分源码：何时重分、如何保持确定性
原件：source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb
原件SHA：6ce109159da4b04758146170d0968e2b42d5f2cd79a03192da8de11f0a5edd1f
以下cell均为零起算。

cell2 L22–24：mri/AV45/FDG目录分别sorted(os.listdir(...))。
cell2 L26–49：取文件名前三个片段为PTID，按MRI字典次序匹配两个PET目录并生成paired_data。
cell2 L52–55：给paired_data写入fdg_index和av45_index。
cell2 L89：
    train_data, val_data = train_test_split(paired_data, test_size=1, random_state=42)
cell2 L95–99：
    with open(train_json_path, "w") as f:
        json.dump(train_data, f, indent=4)
    with open(val_json_path, "w") as f:
        json.dump(val_data, f, indent=4)
这里没有“文件已存在就跳过”的判断。每次运行cell2都会重算并覆盖这两个JSON。
但random_state=42固定，排序后的输入不变时，重算结果不变。

cell3读取刚写出的JSON并打印人数及首条记录。
cell4 L26–34再次从JSON读取；L98–102构建CacheDataset和两个loader。
train_loader的shuffle=True只改变训练访问顺序，不改变train/val成员。
已建好的loader不会因磁盘JSON被另一个cell改写而自动更新；要使用改后的名单还须重新构建loader。
cell9初训循环和cell10续训循环都没有train_test_split，也没有重新调用cell2。
所以“每次重启完整准备流程都会计算划分”成立，“每个epoch/只续训一次就随机换成员”没有对应源码。
修改test_size、seed、可配对文件集合，或未保持原来的输入次序，才可能改变成员。

三、确定性重建：不执行历史notebook，不读影像数据
只读取原3002的_original目录文件名，按原cell2的排序/PTID匹配规则重新组织输入。
三种模态目录各1857个文件；每模态PTID无重复，匹配得到1857人。
用test_size=1、random_state=42进行纯名单重建，结果：
train=1856、val=011_S_4105。
1856条train的完整顺序与用户提供JSON一致，val顺序也一致。
两个列表所有fdg_index/av45_index均与原始paired_data位置一致；1857条description均与指定CSV一致。
这不是只比较集合或第一名被试；本次比较了全部顺序和索引。
重建工具环境sklearn=1.7.2；已存原始目录文件名清单，结果可在不访问服务器和影像的情况下复核。
见deterministic_reconstruction.json及reconstruct_splits.py。
复核命令（只读、仅名单运算）：
/home/data/linshuijin/.conda/envs/xiaochou/bin/python reports/final165_training_split_audit_20261020/reconstruct_splits.py

notebook cell3留存输出的首条train=021_S_4924（index450），val=011_S_4105（index233）。
PTID、描述、索引、影像文件名与对应JSON一致。
完整字典的路径前缀并不相同：输出是ADNI1234_mri_fdg_av45，存活JSON是ADNI1234_mri_fdg_av45_original。
本轮明确记录这个差异，没有将其宣称为原始路径逐字匹配或忽略它来认证影像内容。

四、原作者的执行历史和165续训源码
原始数据库：3002 /home/ssddata/liutuo/.ipython/profile_default/history.sqlite（只读查询，未使用sudo）。
数据库SHA：85be4f4fa1affc1d26d1c398fbe56f7796e650853740408cb3ef58aeef3b32e6。
按目标关键词及相关运行上下文定位117条输入，均保存为有来源/session/input_line/SHA的派生源码。
SQLite session时间字符串不带时区，以下按原存储值显示，不强行当成UTC或北京时间。

session77 start_as_stored=2025-04-23 08:55:00.460977：
input3 = notebook cell2：数据准备和固定seed的1856/1划分。
input4 = notebook cell3：读取名单与人数检查。
input5 = notebook cell4：读取同路径JSON，建立train_loader/val_loader。
input8 = notebook cell8：模型和Adam初始化。
input9 = notebook cell10：加载first_part_154.pth、恢复model和optimizer，继续训练。
上述源码对应关系逐字匹配（忽略首尾空白）；见source_manifest.json和execution_sources/author3002_session77_line*.py。

cell10 L22–26：加载noHistogramNormalized目录下first_part_154.pth；起点为其内部epoch+1。
cell10 L29–31：new_epochs=140、val_interval=5。
cell10 L43–46：for epoch in range(start_epoch,total_epochs)，使用已经建立的train_loader。
cell10 L114：使用同一个val_loader验证。
cell10 L175–181：写model/optimizer/epoch到first_part_{epoch+1}.pth。
notebook留存输出记录155/160/165的Validation loss和Saved all parameters。
实物165内部epoch164，原节点mtime为2025-04-23 17:37:04.764482+08:00。
165在此是保存编号；源码没有将165设置为这次续训的计划停止epoch。

同目录更早的输入历史还记录40→50→80→120→140→154等命名checkpoint的续训引用。
这是提交过的代码序列，不等于对每个历史epoch的完成状态或每次运行成功逐一认证。
first_part_154.pth当前未在原目录或本轮归档索引中找到；其本体和当时冻结名单仍有缺口。
历史输入本身也不是训练完成日志；本轮结合当前165实物、notebook保存输出及用户提供的对应名单判断。

原训练配置的相关源码点：
cell4：batch_size=1；cell8：3D U-Net，1→1通道，(32,64,64,128)，context维512，Adam lr=2.5e-5。
cell10：分别预测FDG/AV45 velocity并组合损失；实际续训代码epoch>=120时设timestep=0。
注意：cell9初训版的阈值是140；不将两份代码拼成同一训练日程。
cell11明确加载first_part_165.pth，并在L44遍历train_loader做推理。
因此该cell不是一份独立test名单的推理入口；不能据此替代完整论文OOF/测试结果来源判断。

五、你本人“先复用、后修改”的证据
3002 /home/ssddata/linshuijin/.ipython/profile_default/history.sqlite：
session4（2025-10-14，按数据库存储日期）input3–9多次保留test_size=1、random_state=42；期间修改CSV/JSON/base_dir路径。
session5 input2、5仍为test_size=1；input8、13改为int(len(paired_data)*0.1)，seed仍42。
session9 input3继续使用这一10%版本。
3003自己的2025-10-15输入历史也保留10%版本，并把base_dir改为NFS ADNILT路径。
纯名单重建这个10%版本：test_size=185，train=1672、val=185，完整顺序与先前找回的本人分支JSON一致。
所以你先复用原始划分、随后修改的说法得到独立代码历史佐证。
但IPython输入记录包含尝试和失败，不能仅凭它证明某一早期完整重训已结束、权重保存成功或归属当前liutuo的165。
本轮不再把1672/185直接称为你第一次原样复现的划分。

六、证据强度与边界
VERIFIED：165原/归档文件同SHA；用户曾提供对应1856/1名单；三方名单同SHA；全顺序/索引重建一致；原作者和本人历史源码已回收。
SUPPORTED ASSOCIATION：1856/1文件与165相关推理输出/准备源码之间有关联；实际训练用途与推理时重新准备名单的可能性仍须区分。
原作者session77保留加载154续训的输入，但尚不能仅凭输入记录和可复用notebook输出，证明成功更新或绑定到现存165。
UNRESOLVED：checkpoint仍无内嵌manifest；154之前每个epoch的数据状态未被不可变记录逐步绑定；不能据此认证整个论文两折实验。
原节点名单mtime为2025-05-08，晚于165文件mtime；它是存活的后续名单文件，而非声称发现了4月23日创建的冻结manifest。
这些时间信息与“同一算法反复覆盖但产生相同划分”相容，但mtime本身不证明历史划分未变。
没有发现必须依赖sudo才能继续核实的权限阻碍；没有训练、推理或修改原文件。

可复制的主要产物
train_val_membership.csv、supplied_train_1856.json、supplied_val_1.json：对应名单。
source_extracts/original_final_cell{2,3,4,8,9,10,11}.py：原notebook源码的带来源提取件，供阅读，不执行。
execution_sources/author3002_session77_line{3,4,5,8,9}.py：与原notebook匹配的历史实际输入。
execution_source_manifest.json：你本人14条3002输入和6条3003输入的代码版本索引。
author_training_timeline.json：原作者续训引用的逐条来源；author_execution_manifest.json：117条相关输入索引。
code_evidence_index.csv、source_manifest.json：原件和派生文件对应关系。
```
