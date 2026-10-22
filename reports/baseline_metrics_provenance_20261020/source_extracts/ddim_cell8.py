# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_concat-ddpm ddim.ipynb
# original_sha256=08513920dcb07f4ecfe20f56393afab040fd35cc826b4b3bb55308aff72afbbe; zero_based_cell=8
train_data = paired_all_with_desc[:1128]

val_data = paired_all_with_desc[1128:]

# 输出检查
print(f"训练集大小: {len(train_data)}") 
print(f"验证集大小: {len(val_data)}")   
