# Original=source_archive/vscode-3002/home/ssddata/liutuo/mri2pet swinunet useful.ipynb
# original_sha256=36b1db9e305c6b05b22f4398129e3ea385e99c5d102a08ebf040db99444fc53e; zero_based_cell=8
train_data = paired_all_with_desc[:800]

val_data = paired_all_with_desc[800:]

# 输出检查
print(f"训练集大小: {len(train_data)}") 
print(f"验证集大小: {len(val_data)}")   
