```text
R3-10 对比方法、临床条件与实现证据核查
核查日期：2026-10-20（Asia/Shanghai）
范围：原稿六个生成基线；代码只读；未执行 notebook、训练、推理或修改稿件。

结论

不能认定“所有对比方法都没有使用临床信息”。
可以核实 Swin 候选预测分支没有消费临床 embedding；已恢复的条件扩散/DDIM、单示踪剂 RF 候选则确实存在患者 description → BiomedCLIP → cross-attention 的通路。
DIReCT 原论文摘要也明确包含个体临床信息。因此，把六个 baseline 全写为 MRI-only 会与现有证据冲突。
但是：上述候选尚未与 Fig.2 的逐方法 checkpoint、测试名单、逐人输出和汇总数值绑定，不能据此声称论文比较已满足 same-clinical-input fairness。
Fig.2 绘图入口的 cell 9–11 直接写入各方法的数值数组；这些单元未从逐人结果重新计算指标。它们能定位绘图输入，不能独立证明各基线的输入条件、测试划分或数值来源。
CycleGAN、SegGuidedDiff、plain 3D RF 的最终运行实现仍有缺口。SegGuidedDiff 原方法是 2D，不等于本项目实际运行也是 2D。

证据标记
VERIFIED：本轮直接核实的文稿、源码或原论文事实，仅适用于所指对象。
CODE-ONLY：已核实候选代码怎样传递输入/计算损失；未证明它产生了论文中该方法的结果。
UNRESOLVED：不足以判断最终论文运行设置。未检出不等于不存在。

一、文稿中的六个基线及逐项判断

1. CycleGAN
文稿：BMEF_main.tex:310，引用 Zhu et al. 2017，定位为 unpaired/cycle-consistent 对照。
临床信息：UNRESOLVED。文稿没有足够的逐方法输入说明；本轮限定源码检索仅命中绘图标签及数值，未恢复生成器、判别器、数据加载与训练损失。
实现：只能确认文稿宣称采用 CycleGAN，无法确认本项目是 2D/3D、是否附加 paired L1/MSE、是否使用 identity loss、临床支路或各损失权重。
公平性解释：配对数据可以用于 CycleGAN 的两个域，但 cycle/adversarial 目标本身不利用逐对 MRI–PET 对应。是否加入监督回归项必须看实际实现。可保留为传统 GAN 参考；仅此不足以回应“强 paired MRI-to-PET baseline”的要求。
不能写：“代码证实 CycleGAN 不用临床信息”或“已公平优化 paired CycleGAN”。

2. 文稿称 Swin-UNet，恢复代码实际为 3D SwinUNETR
证据 S（swin_* 提取文件）：
  原件 source_archive/vscode-3002/home/ssddata/liutuo/mri2pet swinunet useful.ipynb
  cell 3 L94–100：从每人的 description 计算 desc_text_features。
  cell 10 L1–5、24–25：把 description embedding 与 tracer embedding 合成 mri_index/pet_index，并交给数据变换。
  cell 12 L12–22：MONAI SwinUNETR，输入/输出各 1 通道，feature_size=48，Adam lr=1e-5。
  cell 13 L54–65：仅取 data['mri'] 和 data['pet']，model(images)，F.mse_loss(targets, prediction)。
  cell 13 L83–89：预测调用同样没有临床参数。
  归档 MONAI monai/networks/nets/swin_unetr.py:77 的 spatial_dims 默认值为 3。
临床信息：CODE-ONLY，无临床信息进入所核实的预测支路。生成过 embedding 不等于模型使用了 embedding。
任务适配：把原分割网络作为连续 PET 强度回归器，1 通道 PET 输出，配对 MSE 监督；并非仍在训练离散分割任务。
命名：Swin-UNet（Cao）与 SwinUNETR 不是同一个实现名称，不能混写。最终若确认该代码是论文运行，应改名并核对实际引用。
参数：体积 160×192×160；batch=1；n_epochs=800；每 10 epoch 验证。cell 12 另有 max_epochs=500，但真正循环读取的是 cell 13 的 n_epochs，不能把闲置变量当作训练预算。
另一个靠近 Fig.2 的实例：figure2 cell 6–7，同为 SwinUNETR、MSE、MRI-only；训练目标是 fdg（虽文件名含 AV45），n_epochs=13。不能仅凭文件名推断 AV45 训练或最终训练轮数。
最终 Fig.2 的 Swin 运行绑定：UNRESOLVED。

3. SegGuidedDiff
文稿：BMEF_main.tex:314，引用 Konz et al.，称 segmentation-guided PET synthesis。
原论文 VERIFIED：研究为 breast MRI 和 CT organ 的 2D 切片生成；图像为 256×256；把 anatomical mask 与 noisy image 按通道拼接，每步去噪均提供 mask，使用 DDIM 采样。原文结论把 image translation 和 3D extension 列为后续工作。
原方法的 mask 是解剖条件；不能把它与患者年龄/量表等临床变量视为同一种条件。
本项目运行：UNRESOLVED。限定代码检索只命中 Fig.2 标签/数组，没有恢复该基线的本地训练和推理实现。
必须回收：2D/2.5D/3D 网络、MRI 是否直接进入网络、mask 来源/类别/处理、MRI/PET/mask 对齐、切片方向与重建方式、采样步数、checkpoint、评价名单。
若 mask 来自 MRI，在可获得输入层面通常仍属 MRI 派生信息；若来自目标 PET 或额外人工标注，必须另行披露。这是待核实项，不是已发现的目标信息使用。
不能用“原方法是 2D”直接回答“我们跑的是 2D”，也不能用其他扩散代码的 spatial_dims=3 证明它是 3D。

4. 3D DDIM
临床信息：CODE-ONLY，已恢复候选含 description 条件；不能断言论文 DDIM 是无临床基线，也不能断言 Fig.2 DDIM 一定使用了这些条件。
证据 D（diffusion_*）：
  source_archive/vscode-3003/home/data/liutuo/code/mri2pet _add pretrained commom clip_concat-ddpm.ipynb
  cell 3 L94–100：患者 description → BiomedCLIP get_text_features。
  cell 10 L4–5：pet_index = cat([patient_description_embedding, c_pet], token维)。
  cell 16 L8–17：DiffusionModelUNet，spatial_dims=3，in_channels=2，out_channels=1，with_conditioning=True，cross_attention_dim=512。
  cell 18 L35–50：noisy_pet = add_noise(real_pet, noise, t)；输入 cat([MRI,noisy_pet], channel维)；model_1(...,context=pet_index)；回归 scheduler 的 velocity target，MSE 训练。
  cell 30 L8–28：另一个 DDIM 设置，1000 训练时间步、20 推理步、Adam lr=2.5e-5，num_channels=(32,64,64,128)。
  cell 31 L22–38：采样时每一步拼 MRI 与当前 PET，context=pet_index。
  注意：cell 16–18 与 cell 30 的 channel配置不同，不能拼成一份已确认的最终训练配方。
证据 DP（ddim_personal_*）：
  source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-ddpm ddim.ipynb
  cell 10 L4–5：同一 patient description + tracer condition。
  cell 12 L8–27：3D、2→1 通道、512维 cross-attention。
  cell 13：DDIM 10步；加载 epoch40 名称 checkpoint；传入 context=pet_index。
  cell 29–30：DDIM 20步；加载 epoch200 名称 checkpoint；同样传入患者条件。
这些细节证明“存在有患者文本条件的 DDIM 实现”，不是“最终论文 DDIM 的真实参数已全部恢复”。
训练 description 引自 ADNI1/2_baseline 两份 CSV，当前检索未恢复这两份原表；不能证明与 DIReCT++ 的八项字段、取值、填补、prompt 和时间点完全相同。
另有 3014 playground/method-two 的 with_conditioning=False 的扩散候选，因此同名/同类扩散实现确有多个版本，必须绑定最终运行。
文稿引文 Graf2023 是 MRI→CT 应用来源；它不能单独证明本项目 MRI→PET 适配、临床输入或最终 DDIM 设置。

5. 3D Rectified Flow（plain 3D RF）
文稿：BMEF_main.tex:318 称“不含 domain-informed conditioning”，并称可隔离 BiomedCLIP 贡献。
临床信息和实际实现：UNRESOLVED。未恢复可明确归属于 Fig.2 “Rectified Flow”的无临床 RF 训练/推理路径。
特别避免误认：single_flow 候选虽是 3D RF，但包含 description + tracer cross-attention，不能因为文件名有 flow 就把它当成文稿所称 plain RF。
若以后确认 plain RF 为 MRI-only，理论流程可为 x_t=(1-t)MRI+t PET、target_velocity=PET−MRI、vθ(x_t,t)；但这在当前只是待验证的实现描述，不能当作历史运行事实。
“只去掉 BiomedCLIP”的严格消融也未成立：输入、通道、训练日程、采样、tracer组织等差异必须逐项控制。

6. DIReCT（Ours(single)）
原方法 VERIFIED：IPMI 2025 DIReCT 摘要明确使用 BiomedCLIP，结合 common imaging knowledge 与 individualized clinical information。
单示踪剂 RF 候选 SF：
  source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow.ipynb
  cell 3 L94–100：患者 description → BiomedCLIP。
  cell 10 L4–5：患者 embedding 与 PET tracer embedding 拼接。
  cell 12：3D DiffusionModelUNet，1→1 通道，(32,64,64,128)，512维 cross-attention，Adam lr=2.5e-5。
  cell 13 L50–72：x_t=t PET+(1-t)MRI，target=PET−MRI；model(x_t,t,context=pet_index)，MSE。
  cell 13 L55–56：epoch>=140 后设时间为 0；L91–104：MRI 起点，N_sample=1 的 Euler 更新。
临床信息：原论文层面“使用”已核实；所恢复的单示踪剂候选也使用患者 description（CODE-ONLY）。
但该候选与 Fig.2 Ours(single) 的绑定、确切临床字段及一致性未核实，不能直接写“最终 single 与 ++ 已获得完全相同临床变量”。

二、DIReCT++ 的条件通路及公平比较真正需要核实的内容

已恢复主代码（directpp_*）：
  cell 2 L72–85：description → 冻结 BiomedCLIP text feature。
  cell 4 L11–15：cat([patient_embedding, optimized_tracer_embedding], token维)。
  cell 8：3D U-Net，1→1 通道，with_conditioning=True，cross_attention_dim=512。
  cell 9 L77–88：共享网络分别传 FDG/AV45 context，分别预测 velocity，再加权合并 loss。
这不是把八个原始标量直接拼到图像通道，也不是本代码中一个 forward 同时输出两个 PET 通道。
临床模板（prompt cell 6 L4–24）：age、sex、weight、Global CDR、MMSE、GDS、FAQ、NPI-Q，共八项；未直接插入 Research Group 或 Logical Memory II。
旧 ADNI1/2_baseline description 不能自动与这个模板等同；“都有512维 embedding”也不能证明信息相同。

要回应审稿人，需要同时区分：
  A. 相同变量/同一数据来源/同一就诊时间/同一缺失处理（信息是否相同）；
  B. VLM text、numeric MLP、FiLM/cross-attention 等编码方式（如何使用相同信息）；
  C. 实际 checkpoint、测试 cohort 和预测文件（论文结果是否真的用了该配置）。
当前只在部分候选代码上恢复了 B，A 和 C 尚不完整。

三、“optimized to their reported best configurations”目前不能怎样证明

文稿原句在 BMEF_main.tex:307。
固定 lr/epoch/scheduler 的赋值，只证明某候选选择了这些参数，不证明搜索过、更不证明选得最佳。
本次限定搜索未找到上述方法的完整超参数候选表、独立验证选择记录、搜索预算或最终配置到结果的收据；自动调参工具名称的缺失本身也不能排除人工调参。
不能将不同 notebook 里的10/20/1000步、13/200/800epoch拼成一次有记录的统一优化过程。

还存在影响“验证集选最佳”的源码风险（CODE-ONLY）：
  swin cell 13 L83–85：for step,batch in val_loader，但读取 data 而不是 batch，复用此前训练循环变量。
  single_flow cell 13 L85–88：MRI/PET 取 data_val，但 pet_index 取训练 data，可能使用错配临床条件。
这些是所见代码缺陷，不能据此断定论文最终运行也含同一缺陷；却足以说明不能直接拿这些循环的输出认证调参和验证流程。

建议最终补充表逐方法列明：
  实现来源/commit或源文件SHA；2D/3D；输入图像/解剖先验/临床字段；目标tracer；
  回归/对抗/流或扩散loss及权重；preprocessing；subject split；batch；optimizer/lr/schedule；
  更新数/epoch/算力预算；训练和推理时间步；候选搜索范围、试验次数；
  验证选择指标及方向、checkpoint选择规则、随机种子；最终checkpoint与逐人指标路径。
预算应透明、可比较，并允许方法需要的差异；相同epoch本身不等于公平。
只在验证集选择配置，保留测试集；若历史调参记录无法恢复，应删除“optimized/best”的未经支撑表述，诚实列出能恢复的固定设置和缺口。也不能未经证据改写为“官方推荐配置”。

四、直接相关 MRI→PET 方法及 R3-10 回复边界

按提交 PDF 的实际编号，refs.11–14 是：
  11 Xie et al. 2024，Joint Diffusion Attention，MRI→PET。
  12 Chen et al. 2025，Multi-view diffusion，T1WI→FDG。
  13 Theodorou et al. 2025，MRI2PET。
  14 Wang et al. 2025，UniSyn。
它们在 Introduction 被引用，但没有以对应名称出现在六个基线列表中。DIReCT 是 ref.15。
这支持“相关方法未列入比较”的文字层面判断，不代表已经评估它们的可复现性、资源需求或代码可用性。本轮不启动复现。

可直接用于内部回复草稿的已核实表述（不是宣称已完成修订的正式 response）：
“The statement that all comparators were image-only is too broad. The original DIReCT method incorporates individualized clinical information, and recovered conditional diffusion and single-tracer flow code paths also pass subject-description embeddings to the generator. However, these candidate implementations have not yet been conclusively linked to the reported baseline results, so identical clinical inputs across the reported comparisons cannot currently be claimed.”

SegGuidedDiff 的回复只能分两层：
“The cited Seg-Diff work uses 2D slices. The dimensionality and MRI-to-PET adaptation of our reported implementation require confirmation from the actual training configuration and checkpoint.”
这句话保留事实缺口，不能直接作为“我们已澄清为2D”的最终答复。

对审稿意见的实质判断：
“所有基线无临床”的概括过强，可以用 DIReCT 原文和候选条件通路作精确澄清；但这并不能解除对公平比较的主要质疑。
即使最终确认 single DIReCT 使用相同临床变量，它仍是同一方法家族；补一个相同 MRI+clinical 的独立强回归基线，更有助于区分输入信息收益与VLM/flow架构收益。

建议后续最小方案（设计建议，未实现、未训练、未授权为新增实验）：
  3D paired regression U-Net，MRI 主干；同八项原始临床字段经 MLP 编码，在 bottleneck 用 FiLM 或特征融合接入；连续 PET 输出和配对回归loss。
  同时保留 MRI-only 版本与 MRI+clinical 版本，固定同一 cohort、折名单、preprocessing、缺失规则、验证选择及测试评价；明确单/双tracer组织。
  字段标准化/填补仅在训练折拟合；不用诊断标签或按诊断组填补。避免把“同变量”误写成“同编码”。
  数值条件 U-Net 可对应 R3-10，也有助于 R3-12；与 DIReCT++ 的架构差异仍须公开，不能称单变量消融。
  还需单独评估至少一个 refs.11–14 的直接 MRI→PET 方法；这与 matched-clinical regression baseline 回应的是不同要求，后者不能自动代替前者。
当前 E1 Full/No-Scores 不是这个独立基线；No-Scores 仍保留人口学条件，也不能作为 MRI-only。

五、检索范围、证据保存与限制

先读 CORE_CODE.md、核心索引与 R3-10 原文；优先核实索引指定 Swin、扩散、主生成及 Fig.2 绘图文件。
缺失方法定位后，限定读取以下四处的直接子级 notebook 代码单元，共66个（不含输出）：
  source_archive/vscode-3002/home/ssddata/liutuo
  source_archive/vscode-3003/home/data/liutuo/code
  source_archive/vscode-3014/mnt/ssd/liutuo
  source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/Github/train
bounded_search.json 保存具体源文件SHA、查询式和命中；19处命中主要是绘图标签及早期无文本条件的扩散/ControlNet候选，不构成 plain RF/SegGuidedDiff 的最终运行证据。
未遍历执行历史 notebook、未扫描影像和权重内容、未追查全库泄露；未重启或终止任何已有实验。
source_extracts/ 仅为所核实代码单元的带行号派生副本，文件头记录原路径、原件SHA和零起算cell；不得把派生副本当作新的独立实现。
source_manifest.csv 记录逐提取文件原件及派生SHA，便于复核。原始稿件、归档、provenance及已有未提交修改均未改写。
本轮结论为方法实现/来源核查，不是对历史数值或全部baseline公平性的科学认证。
```

核查原文：[DIReCT 出版商摘要](https://link.springer.com/chapter/10.1007/978-3-031-96628-6_15)明确描述个体临床条件；[Seg-Diff 原文](https://arxiv.org/html/2402.05210v2)的 Sections 2–3 与 Conclusion 说明其 2D 切片实验及未来 3D/translation 扩展；[官方代码](https://github.com/mazurowski-lab/segmentation-guided-diffusion)用于核对原方法入口，均不能代替本项目运行收据。
