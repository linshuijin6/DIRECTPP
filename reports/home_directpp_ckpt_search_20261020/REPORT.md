```text
各节点 home 中 DIRECTPP 复现候选运行与 checkpoint 日志定位
核查日期：2026-10-20（Asia/Shanghai）

结论
已实际访问 3001、3002、3003、3014、3015 的 linshuijin home。
找到有保存记录、且相应权重仍在的训练日志。最值得先回看的，是 3002 的 0130.main.log、0203.me.train.log 和 0203.LT.main.log。
它们不是同一次运行：前两者声明 legacy mode；第三者末尾评估的是 TAU/AV45。不能直接把这些运行认证为原稿 FDG/AV45 最终实验。
本报告定位运行与文件，不将它们绑定到 Fig.2 数值、原稿两折 OOF 或最终论文 cohort。

节点覆盖
3001  192.168.1.3    /mnt/data/linshuijin
      在本轮 home 项目检索范围内，未定位到 DIRECTPP 候选日志或 replicaLT 目录。
3002  192.168.1.4    /home/ssddata/linshuijin
      找到 legacy 多示踪剂候选、TAU/AV45 main 候选、单示踪剂及 plasma 扩展日志和权重。
3003  192.168.1.5    /home/data/linshuijin
      找到 TAU-only legacy 日志、权重和 plasma 扩展；两次 legacy 运行末次保存失败。
3014  192.168.1.14   /mnt/ssd/linshuijin
      replicaLT 保留早期脚本与三本 mri2pet two trace notebook；checkpoint/ 为空，未定位到独立运行 .log。
3015  100.78.249.60，经 3014 ProxyJump；/mnt/ssd/linshuijin
      实际连接使用现有集群密钥成功。旧本地别名指向 192.168.1.13，不能再用它代表本次核查的 3015。
      找到 5 份保存至 epoch200 且文件仍在的 AV45 plasma/clinical 扩展日志，另有 1 份未见保存的启动日志。

优先回看的运行（路径均为对应节点上的绝对路径）

A. 3002：legacy 候选，完整保存到 200
日志：/home/ssddata/linshuijin/replicaLT/0130.main.log
权重：/home/ssddata/linshuijin/replicaLT/runs/01.30_151382/ckpt_epoch200.pt
配置：同运行目录 hparams.json
原始日志第17行声明 legacy mode：context = old_descr + modality_text_optimized。
第487行记录 ckpt_epoch200.pt 保存，第497行记录训练完成；当前该目录保留20份编号权重。
hparams：use_legacy_mode=true，alpha=beta=gamma=1，bs=4，n_epochs=200，val_interval=10。
CPU weights_only 加载通过：内部 epoch=199、global_step=49600，模型286项均为有限值。
这是含 TAU 扩展的多示踪剂候选，不直接等同于原稿 FDG/AV45 两示踪剂协议。

B. 3002：legacy 候选，最后已保存 190
日志：/home/ssddata/linshuijin/replicaLT/0203.me.train.log
权重：/home/ssddata/linshuijin/replicaLT/runs/02.03_614278/ckpt_epoch190.pt
第17行声明同一 legacy 条件方案，第465行记录 epoch190 保存；目录保留19份编号权重。
日志末尾停在 Epoch195 的训练进度，不能写成训练至200完成。
hparams：use_legacy_mode=true，alpha=beta=gamma=1，bs=1；与 A 是不同运行。
CPU 加载通过：内部 epoch=189、global_step=232560，模型参数均有限。

C. 3002：main 候选，完整保存到 200；实际日志包含 TAU/AV45
日志：/home/ssddata/linshuijin/replicaLT/0203.LT.main.log
权重：/home/ssddata/linshuijin/replicaLT/runs/02.03_1709820/ckpt_epoch200.pt
第371行保存 epoch200，第377行记录训练完成；当前目录保留20份编号权重。
末尾明确打印 tau SSIM/PSNR 和 AV45 SSIM/PSNR，不能由文件名推断为原稿 FDG/AV45。
CPU 加载通过：内部 epoch=199、global_step=214200，模型参数均有限。
日志中的单次验证输出不作为整队列正式指标，本轮不重评模型。

D. 3003：TAU-only legacy，完整保存到 200
日志：/home/data/linshuijin/replicaLT/0413.legacy.log
权重：/home/data/linshuijin/replicaLT/runs/04.13_2916235/ckpt_epoch200.pt
第447行保存 epoch200，第453行记录训练完成。
hparams：use_fdg=false、use_av45=false、use_tau=true、use_legacy_mode=true。
目录当前保留3份 pt 文件；日志的20次编号保存不代表当前仍保留20份。
CPU 加载通过：内部 epoch=199、global_step=189800，模型参数均有限。

必须避开的损坏末次文件（3003）
0415.legacy.log：epoch170 写入报错，ckpt_epoch170.pt 只有87,175,168字节，ZIP目录不可读。
  已核实可读的上一份编号权重：
  /home/data/linshuijin/replicaLT/runs/04.15_2005229/ckpt_epoch160.pt
  日志第359行记录成功保存；CPU加载通过，内部epoch=159、global_step=151840。
0417.legacy.log：epoch100 写入报错，ckpt_epoch100.pt 只有13,500,416字节，ZIP目录不可读。
  已核实可读的上一份编号权重：
  /home/data/linshuijin/replicaLT/runs/04.17_136281/ckpt_epoch90.pt
  日志第226行记录成功保存；CPU加载通过，内部epoch=89、global_step=85410。
两者均为TAU-only legacy。未删除或替换损坏文件，未发起恢复训练。

3015 的5份有实物checkpoint的日志（同属后续扩展）
公共根目录：/mnt/ssd/linshuijin/replicaLT
日志名                    运行子目录                              最后编号文件
0519.av45.none.log         runs/plasma_05.19_2280430                ckpt_epoch200.pt
0519.av45.demog.log        runs/plasma_05.19_2279663                ckpt_epoch200.pt
0520.av45.full.log         runs/plasma_05.20_2521583                ckpt_epoch200.pt
0520.av45.tt.log           runs/plasma_05.21_2920336                ckpt_epoch200.pt
0520.av45.t2.log           runs/plasma_05.21_2922034                ckpt_epoch200.pt
五份末次权重均为119,474,618字节，均通过ZIP全成员CRC检查；本轮没有对它们运行torch.load。
配置明确 target_modality=av45、guidance_mode=plasma_emb+modality_text、pet_space=per_volume_norm。
0519.av45.full.log 对应 plasma_05.19_2275614：未见Checkpoint saved，当前无pt；不能与0520.full混为一轮。

3014 notebook 中的保存痕迹
mri2pet _two trace_new-final.ipynb：零起算cell9有10/20/30/40的保存输出；cell10有155/160/165的保存输出。
mri2pet _two trace_new_start.ipynb：cell8有epoch10，cell9有epoch165的保存输出。
但源码保存目标是 /home/ssddata/liutuo/checkpoint/...，不是当前3014用户home；本轮没有核实这些外部权重。
这些notebook可能是带历史输出的副本；仅凭它们位于3014，不能证明输出由3014本地复现产生。

其他已定位线索
3002：0201a.log -> 02.01_1849023/epoch200；0201a1.log -> 02.01_1853357/epoch77；
      0201.log -> 02.01_2344790/epoch84；0202.log -> 02.02_4001386/epoch161。
      这些运行的hparams均声明legacy mode；本轮核实文件存在，没有逐个加载。
3002：av45_legacy.log -> runs/05.02_1189447/ckpt_epoch200.pt（AV45-only）。
3002：0205.LT.main.tau.log -> runs/02.05_1888825/ckpt_epoch200.pt（TAU-only）。
3002：0528.t.log -> runs/plasma_05.28_3715049/ckpt_epoch600.pt（plasma扩展）。
3003：0602.recache.log -> runs/plasma_06.02_591035/ckpt_epoch2580.pt（plasma扩展）。
home/replicaLT/checkpoint 下的first_part文件：3002有60份、3003有258份。
其目录是多个历史运行共用的命名空间；本轮不把这些first_part文件无依据绑定到某一份原稿运行。

证据和边界
focused_runs.csv：23份重点日志的节点、分类、配置、最后成功checkpoint、当前文件数、SHA和验证等级；其中22份有对应实物权重。
*_inventory.json：各节点文件路径、大小、mtime及剪枝/访问错误；*_runs.json和3015_focused_logs_and_runs.json：实际配置与逐权重清单。
*_checkpoint_validation.json及3003_previous_good_checkpoints.json：6份有效CPU加载、2份损坏末次文件、3015的5份ZIP/CRC检查及SHA。
*_raw_newline_evidence.json：上文关键日志的原始换行行号；其他提取文件的line/line_splitlines可能将进度条CR折为逻辑行，不可混作rg行号。
源训练日志及权重均未修改；本次只在独立报告目录写入派生清单，没有训练、推理、改队列或终止既有训练进程。
扫描以home内项目目录为主，剪除环境、软件缓存、影像数据和隐藏工具目录，不跟随目录symlink；具体剪枝见inventory。
因此“未定位”仅限本轮范围，不代表全服务器无文件。未扩展到其他用户home或NFS全盘搜索。
```
