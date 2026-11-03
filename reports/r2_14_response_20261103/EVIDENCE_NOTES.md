# R2-14 回复核对说明

独立英文文本见 [RESPONSE_DRAFT.md](RESPONSE_DRAFT.md)。本次没有修改稿件、rebuttal、历史 notebook 或实验输出，没有新增训练。

## 已核实依据

- 审稿原文：`reports/source_reports/review_comment_register.csv` 的 R2-14，要求维度、PET特征提取、prompt、adapter、τ和优化细节。
- 模型配置：`source_archive/vscode-3002/home/ssddata/liutuo/BiomedCLIP/config.json` 的 `projection_dim=512`；文本、图像隐藏维度768，图像输入224×224、3通道。`modeling_biomed_clip.py` 的 `get_text_features`、`get_image_features` 返回投影后特征；`preprocessor_config.json` 给出图像均值、标准差、resize/center-crop设置。
- 历史适配实现：`source_archive/vscode-3002/home/ssddata/liutuo/liutuo_data/shuijin/Github/clip pretrain/mri2pet _clip_pretrain -github.ipynb`，零起算cell 2、8、9。当前SHA-256为 `435514d807bed6608aadf1e87c725cb9fed387b91999b370f3b470c6051cbd93`。cell 8明确FDG的160切片特征平均；cell 9明确两个scalar+512 bias、逐人平均余弦、100倍双侧平方项、Adam 1e-3和5000次更新。未把整本notebook当作一次完整历史运行证明。
- 两tracer统一提取及折内适配的修稿实现：`experiments/e1_clinical_conditioning/run.py` 的 `biomed()`、`encode()`、`slices()`、`features()`、`adapt()`，配置为 `reports/e1_stage01_20261017/config.json`。回复明确用“fold-specific revision implementation”标注折内名单、seed、两tracer共用特征流程及无padding编码等细节，不反向声称历史所有运行均如此。
- Prompt：tracer全文与 `reports/e1_stage01_20261017/tracer_texts.json`、原生成notebook cell 1一致；FDG缓存字符串末尾有空格，英文引文不把该不可见空格呈现为内容。完整临床模板来自 `source_archive/vscode-3003/home/data/liutuo/code/chu li shu ju.ipynb` 零起算cell 6中的 `generate_description()`；仅阅读源码，没有执行历史notebook。
- 条件上下文：生成实现将clinical和tracer向量叠为2×512；`cross_attention_dim=512`。有无adapter须按具体实现区分，不能由框架示意图推定。
- τ来源：原生成notebook `mri2pet _two trace_new-final.ipynb` cell 1（执行计数2）stdout为0.8205；既有冻结缓存复算0.8205374479的依据见 `experiments/r2_15_tau_adapter_ablation/report.md`。没有作者当时选择动机的直接记录，故回复仅写数值对应，未写“作者因此选定”。
- 已存在的τ敏感性证据：本次只读复核 `experiments/r2_15_tau_adapter_ablation/results.csv` 10行，逐项核对10个embedding及checkpoint SHA-256与收据一致；未重跑拟合。结果仅用于表示层分析的范围说明，不声称生成或临床收益。

## 保留的限制

原生成主入口及GitHub版本存在直接使用raw tracer向量的分支，不能仅凭adapter训练代码存在就证明其被每个历史checkpoint采用。独立回复因此明确适配分支与未适配分支的区别，而不声称所有实验均使用adapter。临床字段上游填补和访视身份的缺口仍保留，不在R2-14回复中自行认证。

英文文本不写“已在某节/某表修改”，也未把当前稿件中的不等式、冻结编码器与fine-tuning措辞混作一致的实现。
