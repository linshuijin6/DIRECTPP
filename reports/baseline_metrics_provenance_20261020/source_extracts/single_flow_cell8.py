# Original=source_archive/vscode-3003/home/data/liutuo/code/mri2pet all data_add personal clip_flow.ipynb
# original_sha256=6ad4b83141e67a968f1b64008b9121a594721361186a8062daeb51da2d45107a; zero_based_cell=8
train_data = paired_all_with_desc[:800]

val_data = paired_all_with_desc[800:]

# 输出检查
print(f"训练集大小: {len(train_data)}") 
print(f"验证集大小: {len(val_data)}")   
