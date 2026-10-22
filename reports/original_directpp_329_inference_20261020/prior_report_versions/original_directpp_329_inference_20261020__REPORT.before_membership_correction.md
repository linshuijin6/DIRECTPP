```text
原作者DIReCT++权重在固定329人名单上的原始代码回放
日期：2026-10-20（Asia/Shanghai）
状态：运行中；不能将本文件当成完成报告。

关于一人名单的简要核实
test/test1示例单元确实加载已有checkpoint，调用model.eval()、torch.no_grad()，没有optimizer.step/backward。
即使变量叫train_loader，该次执行也只是推理；这支持用户对这些示例的解释。
但不能把所有test_size=1都解释成仅推理：原作者session77也先用1856/1的loader再执行加载154的续训单元。
名称、某个单元的用途和整个notebook的用途须分开。

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
329人均位于165既有训练名单，本次只作为权重/代码回放诊断，不称独立测试性能，也不认证论文完整OOF。

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
```
