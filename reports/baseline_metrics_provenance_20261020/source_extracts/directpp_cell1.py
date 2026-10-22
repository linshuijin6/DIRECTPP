# Original=source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb
# original_sha256=6ce109159da4b04758146170d0968e2b42d5f2cd79a03192da8de11f0a5edd1f; zero_based_cell=1
import torch
from transformers import AutoProcessor, AutoModel
import torch.nn.functional as F

# 1. 加载 BiomedCLIP 模型和处理器
local_model_path = "/home/ssddata/liutuo/BiomedCLIP"
processor = AutoProcessor.from_pretrained(local_model_path, trust_remote_code=True)
model = AutoModel.from_pretrained(local_model_path, trust_remote_code=True)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)
model.eval()
# 加载优化后的描述
fdg_text_optimized = (
    "FDG PET is a functional brain imaging technique that visualizes the dynamic changes in glucose metabolism, directly linked to neuronal energy demands and synaptic activity. It serves as a tool to assess functional connectivity and energy utilization across brain regions. Areas with decreased metabolic activity, such as those affected by neurodegenerative diseases, should exhibit reduced signal intensity. High-intensity metabolic hotspots in gray matter (e.g., the cerebral cortex and basal ganglia) are key markers of neuronal activity. "
    
)

av45_text_optimized = (
    "AV45 PET is a molecular imaging technique that highlights the static distribution of amyloid-beta plaques, a critical pathological marker of Alzheimer's disease. This imaging modality provides a spatial map of amyloid deposition in cortical regions (e.g., the temporal, parietal, and frontal lobes) and can distinguish amyloid-positive areas from amyloid-negative white matter regions. The primary focus is on identifying amyloid deposition patterns to assess disease progression and pathological burden."
    
)

# 提取特征向量
texts_optimized = [fdg_text_optimized, av45_text_optimized]
inputs_optimized = processor(text=texts_optimized, return_tensors="pt", padding=True).to(device)

with torch.no_grad():
    text_features_optimized = model.get_text_features(**inputs_optimized)

# 计算相似度
fdg_feature_optimized = text_features_optimized[0]
fdg_feature_optimized=fdg_feature_optimized.unsqueeze(0)
av45_feature_optimized = text_features_optimized[1]
av45_feature_optimized =av45_feature_optimized.unsqueeze(0)

cosine_similarity_optimized = F.cosine_similarity(fdg_feature_optimized, av45_feature_optimized).item()

print(f"Cosine similarity between optimized FDG PET and AV45 PET features: {cosine_similarity_optimized:.4f}")
