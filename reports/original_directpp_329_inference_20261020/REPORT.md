```text
原作者DIReCT++权重在固定329人名单上的原始代码回放
日期：2026-10-20（Asia/Shanghai）
状态：全量完成，原始代码进程exit=0；逐人输出与预测文件完整性检查通过。

关于一人名单的简要核实
test/test1示例单元确实加载已有checkpoint，调用model.eval()、torch.no_grad()，没有optimizer.step/backward。
即使变量叫train_loader，该次执行也只是推理；这支持用户对这些示例的解释。
原作者session77的历史输入另包含1856/1准备、loader及加载154的续训源码；输入记录本身不证明成功更新了参数或生成了现存165。
名称、某个单元的用途和整个notebook的用途须分开。
补充独立于变量名的权重计数：140/150Best/165的Adam step为259802/278356/306190，相邻286项模型张量均不同。
增量与每个记录epoch约1856次更新相容；但计数不含PTID，不能认证329人的实际训练归属。详见checkpoint_update_counter_evidence.json。

本次执行范围
使用原作者DIReCT++权重，不使用单示踪剂RF或DDIM对比方法权重。
选择first_part_152best.pth，因为原作者new_start notebook的cell10明确加载这一best文件。
checkpoint SHA256：a57f7e79071baf4661bfe7d853846cf2fe57590de25b26eaf7a90faead634bb6。
内部epoch=151、286项模型张量，CPU weights_only检查全部有限。
固定使用上一轮从单示踪剂notebook输出恢复的329个PTID，顺序不变，不重新划分、不据本次指标选择权重。

明确区分输入口径
本次在原双示踪剂1857人数据中按这329个PTID选取原MRI/FDG/AV45及其description。
沿用原DIReCT++ NIfTI数据、文本编码、条件构造和预处理；不是重放B中单示踪剂的旧.mat输入/六项临床模板。
原new_start cell4含MRI/FDG/AV45的HistogramNormalized；不套用165分支仅MRI histogram的预处理。
329人全部包含在名为train_data_1856_first_part_165.json的文件中；这只证明文件间PTID包含关系，不能单独认证165的实际训练队列。
是否与权重真实训练样本重叠仍待确认；本次不预先归类为训练集性能或独立测试性能，也不认证论文完整OOF。

原始源码
source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new_start.ipynb
SHA256：076c0f6b12fb0d0b020bc78bb166013a16bc75669be8c379ba41ffe62380f55a。
使用零起算cell1（tracer条件）、cell2划分前部分（原1857人排序/患者文本编码）、cell4的val变换和loader、cell7模型构造。
四指标来自原作者mri2pet _two trace_reflow_test or fanhua.ipynb的cell7。
该指标notebook SHA256：d09273e006ccafe9bfe267192192c5b48cd10c34b8da2e22a1c5c37ad3eebcf2。
原始模型依赖、MONAI和原生SSIM均从原归档路径导入；不调用experiments/e1_clinical_conditioning的任何代码或指标加速器。

适配范围与数值环境
仅选取所需原单元，停止在重新划分/写原JSON之前；按固定329名单建立原val_loader，再供原评估循环读取。
替换数据、BiomedCLIP bundle、checkpoint和输出路径；checkpoint映射到隔离GPU，使用weights_only加载。
只增加原指标张量的记录和首个有效被试的原生CPU/GPU SSIM一致性检查，不修改模型、采样、变换或指标公式。
原生FP32推理，关闭TF32，未加入AMP；这是明确记录的当前数值环境，不声称与历史依赖版本逐位一致。
执行前/后的原始单元、修改后单元、SHA及逐项适配保存于artifacts/executed_author_cells和source_receipt.json。

资源和输出
3003，物理GPU5（GPU-138b9a94-aa8c-4ced-3cef-82535dfaa417），batch=1串行推理。
原始预测及真实影像保存到独立/mnt/datas230目录；项目artifacts链接指向该目录。
逐人原始指标：artifacts/per_subject_metrics.csv；实时进度：artifacts/status.json；日志：artifacts/run.log。
启动收据：launch_receipt.json；权重/源码预检：selected_preflight.json。
不训练、不改原CSV/名单/权重、不动其他GPU进程。


全量结果及与原论文的数值比较
每项依次为：原论文 / 本次回放 / 回放−原论文。SSIM、MSE、MAE均按原表乘100。
FDG n=329：
  SSIM: 89.9400 / 96.2076 / +6.2676
  PSNR: 28.7200 / 31.2603 / +2.5403
  MSE: 0.3300 / 0.0768 / -0.2532
  MAE: 2.9600 / 1.3464 / -1.6136
AV45 n=324：
  SSIM: 88.2100 / 93.5184 / +5.3084
  PSNR: 28.0900 / 29.8647 / +1.7747
  MSE: 0.3900 / 0.1090 / -0.2810
  MAE: 2.7300 / 1.5889 / -1.1411
这仅是固定329个PTID、152best及其原预处理下的数值回放；不把数值相近等同于论文协议被复现。
AV45仅n=324，因为5人的原生清单指向_zero.nii.gz全零占位影像；原作者评估单元对这些人只执行FDG。名单：010_S_4442、018_S_4733、109_S_4260、123_S_4362、141_S_4819。
权重实际训练被试归属仍未认证；不能将JSON名为train解释为这329人必然训练过，也不能反向认证为独立测试。
总耗时：41.51分钟；推理峰值allocated=8.57 GiB，reserved=18.77 GiB。
这里是推理峰值，不能与训练显存直接比较。
完整逐人指标和影像仍在artifacts/；对照表paper_comparison.csv，完整性收据verification.json。
本轮没有训练、没有使用E1代码、没有按329人指标挑选权重。
完成时间：2026-10-20T19:59:47.780321+08:00
```
