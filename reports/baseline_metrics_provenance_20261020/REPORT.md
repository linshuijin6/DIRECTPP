```text
原论文生成指标、原作者评估代码与被试/结果来源核查
日期：2026-10-20（Asia/Shanghai）
口径更正：有关1856人实际训练归属的判断已收窄；见../original_directpp_329_inference_20261020/membership_semantics_correction.json。
本轮只读原件；没有执行历史notebook、模型推理、GPU实验或修改训练。

一、先列原论文Fig.2的汇总数值
每格依次：SSIM(%) / PSNR / MSE(%) / MAE(%)。
此处保留原表单位；不能把SSIM=89.94与未乘100的0.8994直接比较。

方法             ADNI-FDG                 ADNI-AV45                OASIS-AV45
CycleGAN         67.82/17.26/2.35/6.47     59.56/15.43/3.24/8.39     40.27/12.38/4.86/10.78
Swin-Unet        75.29/19.82/1.27/5.76     69.16/17.54/2.67/7.95     51.34/14.96/3.96/10.16
3D DDIM          82.62/23.09/0.98/3.98     73.37/21.33/1.73/7.01     68.59/17.05/3.48/8.24
SegGuidedDif     84.85/23.76/0.57/3.73     80.29/21.99/1.12/6.92     71.85/19.63/2.51/7.59
Rectified Flow   85.69/24.96/0.53/3.52     85.43/24.74/0.69/4.31     80.44/21.33/1.87/4.29
DIReCT(single)   87.48/26.51/0.43/3.08     87.37/27.11/0.51/3.16     82.66/25.48/1.12/3.55
DIReCT++         89.94/28.72/0.33/2.96     88.21/28.09/0.39/2.73     83.97/26.79/0.94/3.01

数值原件A（原作者3002）：
/home/ssddata/liutuo/liutuo_data/新建 XLS 工作表.xls，Sheet1；Sheet2/3为空。
SHA256：92643950a8408dac3465bf97d65850ac7d1e25c85dfe84256f598dcde8a005df。
已另存original_assets/performance_table.xls及逐格读取的performance_table_extracted.json。
原表明确写OASIS AV45；末行原名Ours(DIReCT+)，这里按论文/绘图对应行标为DIReCT++。

数值原件B（原作者notebook）：
source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_AV45-swin unet or fanhua.ipynb
SHA256：0755c31eeb8f628ec6f73a11e91a75577a8211337e8d5729d3a13deabef59489。
零起算cell9=ADNI-FDG，cell10=ADNI-AV45，cell11=OASIS。
这三个cell直接赋值methods/data数组，再做雷达图归一化；没有在其中读取逐人指标重新求均值。
Excel与这三组数组84/84数值一致，见paper_value_crosscheck.json、paper_figure2_values.csv。
原作者IPython session129 input37/36/35分别与上述三个cell匹配；输入日期按存储值为2025-05-29。
session140 input5/6还保留读取上述xls、转LaTeX表格的原始输入，见history_sources/。
这证明汇总数值确实存在于原始资产和输入历史，不证明它们来自已经找回的某一套逐人评价。

二、本轮最重要的区分
已找到：原汇总数值、165对应的一次1856人生成/评估输出、另一条单示踪剂141的329人四指标评估、示例结果目录。
尚未找到：把Fig.2全部方法84个数值绑定到最终checkpoint、完整测试名单、生成影像和逐人指标的统一计算链。
因此目前可以给出具体评估入口和名单，仍不能把这些不同运行直接拼成论文统一test集。
也不能因某个原始目录叫ddim或seg_guided_diff，就认证其中影像的方法身份。

三、165权重：找回的是train_loader上的1856人输出，不是论文汇总数值
原始训练/生成notebook：
source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb
原件SHA：6ce109159da4b04758146170d0968e2b42d5f2cd79a03192da8de11f0a5edd1f。

零起算cell11：
L12加载/home/ssddata/liutuo/checkpoint/mri2pet _two trace_add clip_flow_noHistogramNormalized/first_part_165.pth。
L22设SSIMMetric(spatial_dims=3,data_range=1.0,kernel_size=7)；L23设PSNRMetric(max_val=1.0)。
L44明确遍历train_loader，MRI+t=0预测velocity，MRI+velocity后clamp到[0,1]。
按tracer有效性判断分别保存NIfTI，并打印每人的SSIM/PSNR；没有在这个cell汇总论文四指标。
cell11完整源码与原作者3002 IPython session78 input14相同（忽略首尾空白）；日期原存储值2025-04-24。

对cell11留存输出进行纯文本解析：
1856个唯一PTID，完整集合等于此前保存的train_data_1856_first_part_165.json；额外0、缺少0。
这里确认的是JSON内容和train_loader输出身份，不能仅凭该文件名或推理输出认证165实际用这1856人训练。
唯一val=011_S_4105不在该输出中。
有效FDG 1597条，AV45 1364条，共2961个唯一(PTID,tracer)指标记录，无重复。
从打印到四位小数的原始指标计算算术均值：
           n      SSIM(%)       PSNR
FDG        1597   95.916675     32.668536
AV45       1364   93.773673     31.260304
论文汇总          89.94/88.21   28.72/28.09（依次FDG/AV45）
两者明显不一致。这份输出不能直接解释成Fig.2的均值。
它也没有打印MSE/MAE，本轮没有用PSNR反算并冒充原始MSE记录。

名单/逐人结果：evaluation_subject_lists.csv中165_train_loader_observed；original165_logged_metrics.csv。
原1856/1完整JSON仍见../final165_training_split_audit_20261020/，未更改原件。
源码与输出摘录：source_extracts/vscode-3002_mri2pet _two trace_new-final_cell11.{py,outputs.txt}。
汇总检查：original165_logged_summary.json；历史输入对应：history_cell_matches.json。

证据边界：这是与加载165代码共同保存、且有同版历史输入佐证的输出路径。
notebook输出不是内嵌checkpoint/名单哈希的不可变运行日志，也可能被副本复用。
本轮确认其逐人名单和数值内容；不将其扩展为整个论文OOF/test来源认证。

四、另外找到的原始评估代码与可回收名单

A. 四指标评估示例：双示踪剂RF，140权重，一名示例被试
原件：source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_reflow_test or fanhua.ipynb。
零起算cell2/3/4读取test1目录的CSV/JSON，固定test_size=1、seed42，建立loader。
原节点test1原始JSON：train=[037_S_0552]，val=[057_S_1269]。
cell7加载noHistogramNormalized/first_part_140.pth，实际遍历train_loader。
SSIM窗口7、data_range=1；PSNR max_val=1，另用MONAI MSEMetric/MAEMetric。
保存输出只有037_S_0552：
FDG  SSIM=0.9215，PSNR=30.5220，MSE=0.0009，MAE=0.0158。
AV45 SSIM=0.8848，PSNR=30.8085，MSE=0.0008，MAE=0.0163。
源码与3002 session130 input17/18一致（2025-05-29，数据库存储日期）。
注意：代码把该RF输出写到test1/ddim/...；目录名ddim不能改变所加载的RF权重身份。
这是四指标计算方法的原始实例，不是论文全test队列，不能替代165或3D DDIM的论文结果。

B. 单示踪剂RF/DIReCT候选：141权重，329人四指标输出，名单可直接回收
原件：source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow.ipynb。
原件SHA：6ad4b83141e67a968f1b64008b9121a594721361186a8062daeb51da2d45107a。
cell3/6读取ADNI1+2_baseline的MRI/PET与两份临床description表；保留1129条配对数据。
cell8使用paired_all_with_desc[:800]训练、[800:]验证；不是1857人CSV的1856/1划分。
cell4/9保留可解析的完整配对/验证字典；cell10建立对应loader。
cell16加载：
/home/data/liutuo/code/checkpoint/mri2pet all data-_add personal clip-_flow/noise2image about mri2pet_method_two_second_part_141.pth。
它使用val_loader、t=0单步生成、clamp[0,1]、SSIM窗口7、PSNR max_val=1、MSE/MAE。
原作者3003 session222 input15与该评估cell一致；日期原存储值2024-11-23。
留存输出329个被试名与cell9验证列表完整顺序相同；也等于cell4全名单的后329个PTID。
cell9字典另外增加了index字段，未宣称原始字典逐字节一致；旧字段全部一致。
直接从逐人输出复算的均值与末尾打印汇总一致：
SSIM=0.8761628166882826，PSNR=23.799274456174903，MSE=0.004468275977887417，MAE=0.031853901641301835。
这些数值不等于论文single在任一组中的整套四指标，不能绑定为Fig.2最终single结果。
当前原3003该目录保留15个权重文件，但未见141这一确切文件名；不以其他epoch替代它。
产物：single_flow_val_from_original_output.json、single_flow_all_from_original_output.json、single_flow141_logged_metrics.csv。

C. Swin：原始评估入口及明确的一人选择，不是完整test均值
原件：source_archive/vscode-3002/home/ssddata/liutuo/mri2pet swinunet useful.ipynb。
3003也保留同族notebook及相同输出，不能当作两次独立结果。
所见实现为MONAI 3D SwinUNETR，1→1强度回归，不是仅凭稿件名称认定另一种Swin-UNet架构。
cell14加载/home/data/liutuo/code/checkpoint/swinunter/swinunter_1.pth。
明确for batch in train_loader，并仅处理022_S_0543；SSIM窗口11、PSNR max_val=1。
留存SSIM=0.7392916679382324、PSNR=19.827280044555664；没有该cell的MSE/MAE。
该PSNR与论文19.82接近，但一个被试的值、不同SSIM值均不足以认证论文均值。
cell13还存在训练/验证汇总输出；验证循环读取训练变量data的风险已在此前R3-10报告登记，不能拿它认证最终验证选择。
原节点swinunter目录为空；3002另有swinunter_fdg目录13个文件，未与Fig.2数值绑定。
旧版800/329候选名单已从cell4/9另存swin_*_from_original_output.json，不能直接当成cell14/论文test名单。

D. 3D DDIM：有原始采样/评价代码，缺少论文最终运行绑定
原件：source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-ddpm ddim.ipynb。
cell13加载concat_final/...second_part_40.pth，DDIM 10步，评价循环遍历train_loader，SSIM窗口11。
cell29/30另一分支为DDIM 20步、加载同目录...second_part_200.pth，亦遍历train_loader并计算SSIM/PSNR。
原3003当前40和200文件名均仍在；这不自动认证论文DDIM行。
cell4的原始输出包含1129条配对字典，cell9输出却只剩一条val记录，显示不能将独立cell现状拼成一套已冻结完整划分。
原始description/临床条件、网络和采样分支与论文最终运行是否一致仍待绑定。
另一个原始扩散候选为：
source_archive/vscode-3003/home/data/liutuo/code/mri2pet _add pretrained commom clip_concat-ddpm.ipynb。
其cell18是训练/验证、cell30/31是20步DDIM候选；不把不同cell的参数拼成同一运行。

E. CycleGAN、SegGuidedDif、plain Rectified Flow
已找回原汇总值与原节点小规模结果影像目录，详见下一节。
在本轮限定原始notebook和历史输入中，仍未恢复可将各自论文行绑定到完整test名单的最终评估/汇总代码。
不能把有临床cross-attention的single flow当成文稿所称无条件plain RF。
不能把test1/ddim中的RF140代码当成DDIM；同理不能按seg_guided_diff目录名认证SegGuidedDif。
原作者3002 session108 input14实际加载clip_flow/first_part_120.pth，做MRI+velocity生成，写入test/seg_guided_diff子目录。
该原始输入已另存history_sources/author3002_session108_input14.py。
这证明目录标签与源码方法身份可能不同；不据此断言当前所有该目录文件均由这次输入生成，或论文全部结果有误。

五、各方法生成结果实物：原作者3002仍在，但主要是少数示例
共同根路径：/home/ssddata/liutuo/liutuo_data/。

test/：输入MRI/FDG/AV45各2个，对应002_S_0295、002_S_5018。
原JSON train=[002_S_0295]、val=[002_S_5018]；不能仅凭test目录名称解释为全论文独立test集。
方法子目录（每个4个NIfTI，两人×两tracer）：
test/cyclegan/
test/swin_unet/
test/ddim/
test/seg_guided_diff/
test/rectified flow/
test/ours single/
test/ours/

test1/：输入各2个，对应037_S_0552、057_S_1269；train/val各1个。
test1/cyclegan/、swin_unet/、ddim/、seg_guided_diff/、rectified flow/、ours single/各有2个顶层结果文件。
其中多份文件名明确为037_S_0552的两tracer；cyclegan/swin_unet仅写0552，不能凭此补造完整PTID绑定。
test1/ours/目前4个文件却是135_S_4676与941_S_1195的两tracer，不同于此目录的输入/GT被试。
因此不能直接按这些目录拼接同一套逐人对比；本轮未移动、改名或改写任何影像。

此外还有大批生成实物：
data_augmentation_fdg_generated/：1598个文件。
data_augmentation_av45_generated/：1365个文件。
data_augmentation_mri/：1857个文件。
对应真实FDG/AV45目录分别1598/1365个文件。
当前basename为PTID.nii.gz，而165留存导出日志使用generated_fdg_/generated_av45_前缀。
当前数量还各比165日志多一人，不能仅凭同目录或总数把全部文件逐一绑定为165输出或论文OOF结果。
oasis_av45fanhua/只有T1.nii、av45RAI.nii.gz两个文件，未找到完整OASIS逐方法评价名单。

完整文件名/路径：generated_file_index.csv；原始遍历收据：3002_original_generated_directories.json。
这里只验证实物文件名和小名单内容，未读取全部影像内容或认证每幅预测的来源权重。
小CSV/JSON原字节副本与SHA：original_assets/test*_*.{csv,json}及small_manifest_copy_receipts.json。

六、先暂存四个疑点；当前代码差异已有部分直接证据
完整登记见OPEN_QUESTIONS.md，不把尚未验证的解释写成结论。

1. test_size=1的动机：代码行为已证实，作者当时为何如此设置仍无原始解释。
2. 当前还原代码比较对象：experiments/e1_clinical_conditioning。
   common.py:new_model与原new-final cell8的全部构造参数相同，且导入同一归档DiffusionModelUNet依赖。
   MRI→PET线性插值、PET−MRI速度MSE、双tracer损失求和及t=0单步推理均保留。
   但不能称同一历史运行的精确复现：恢复的准备源码/JSON为1856/1，E1为两折各928，前者并不单独证明原权重的实际训练队列；
   原cell1直接编码tracer文本，E1另拟合折内adapter；
   原初训cell9从140起t=0，而实际续训cell10使用120；E1配置为140。原165完整先前日程仍有缺口。
3. 指标差距：原165日志均值也高于论文；E1与原165/论文尚未建立同checkpoint、同测试名单、同条件和同聚合口径。
   当前E1 Full的已保存对照为FDG SSIM7=90.9826%、PSNR=27.2318；AV45 SSIM7=86.3928%、PSNR=24.9108。
   不能概括为所有指标都更差，也不能单凭差距归因到Codex还原、训练名单或某一种指标实现。
4. 显存48G与24G：这是用户回忆/观察，本轮没有同口径峰值对照。
   已见直接源码差异：原cell9/10先做FDG和AV45两个前向、相加loss再一次backward；
   E1 run.py:batch_step逐tracer backward累加梯度，两个分支之后才一次optimizer.step。
   后者减少同时保留的激活计算图，可能解释明显显存下降；模型构造参数相同，不支持仅凭显存判断模型规模减半。
   是否恰好解释48→24、是否有其他实现偏差，须另做受控对照；本轮没有启动该实验。

七、核查范围、产物与未解决事项
以CORE_CODE.md/core_code_index.csv为入口，再限定检查原3002、3003、3014归档直接子级及已知GitHub目录，共66本notebook的代码单元。
只在命中评估/绘图单元读取文本输出，不导出图片base64、不执行notebook；保存174个命中cell的来源索引。
追加只读查询原作者3002/3003的IPython输入历史；关键词包括指标API、汇总数组、方法名及明确运行上下文。
3002 output_history表为0行，不能指望从该数据库直接恢复未保存的stdout均值。
另外限定检查4个明确的原始备份/绘图notebook，以及原3002结果目录和原3003明确checkpoint目录。
这不是各服务器全盘搜索；没有命中不等于所有历史介质上不存在。

VERIFIED：Excel/绘图84个数值；原始评估源码及匹配的历史输入；留存输出中的逐人名单/指标；现存文件名与小名单SHA。
SUPPORTED：165代码/历史输入/1856人输出的关联，及single141的329人验证输出关联。
UNRESOLVED：Fig.2各行最终checkpoint与完整test名单、实际预测/GT、有效tracer筛选和聚合协议的完整绑定。
不将本轮单次运行发现替代作者说明的两折生成→三折分类整体设计，也不据此认证或否定整个论文。

主要入口：
paper_figure2_values.csv、original_assets/performance_table.xls：原论文汇总数值。
evaluation_subject_lists.csv：已恢复的评估路径名单，带身份和证据范围。
original165_logged_metrics.csv：165相关输出的2961条SSIM/PSNR。
single_flow141_logged_metrics.csv：另一原始候选329人四指标。
metric_cell_index.json、additional_source_manifest.json、history_cell_matches.json：原件/零起算cell/输入历史/提取件索引。
source_extracts/、history_sources/：带来源的原始代码与相关文本输出，供阅读，不运行历史训练。
OPEN_QUESTIONS.md：四个暂存疑点；architecture_comparison.json：模型构造参数逐项对照。
verification.json：本轮限定检查与产物SHA，不是论文科学有效性的认证。

存储说明：整理过程中NFS报告No space left on device；余下文件先写入本机/tmp隔离目录，再尝试回写。
未清理任何原始资产、未使用sudo、未训练/推理/更改已有队列或稿件。
```
