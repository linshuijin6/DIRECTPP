# Original=source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_reflow_test or fanhua.ipynb
# original_sha256=d09273e006ccafe9bfe267192192c5b48cd10c34b8da2e22a1c5c37ad3eebcf2; zero_based_cell=3
# 验证训练集
with open(train_json_path, "r") as f:
    train_data = json.load(f)
print(f"Loaded {len(train_data)} training samples.")
print("First training sample:", train_data[0])

# 验证验证集
with open(val_json_path, "r") as f:
    val_data = json.load(f)
print(f"Loaded {len(val_data)} validation samples.")
print("First validation sample:", val_data[0])

