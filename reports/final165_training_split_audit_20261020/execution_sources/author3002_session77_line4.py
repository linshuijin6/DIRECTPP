# Original DB=/home/ssddata/liutuo/.ipython/profile_default/history.sqlite
# session=77; line=4; session_start_as_stored=2025-04-23 08:55:00.460977
# source_sha256=62895212f3a14c982f50e044705dee2621267a3d0dcc3cbb75e02a1c5cb3c4c7
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