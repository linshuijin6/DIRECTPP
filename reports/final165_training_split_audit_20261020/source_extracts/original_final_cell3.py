# Derived evidence only; original=/mnt/nfsdata/nfsdata/linshuijin/DIRECTPP/source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_new-final.ipynb
# original_sha256=6ce109159da4b04758146170d0968e2b42d5f2cd79a03192da8de11f0a5edd1f; zero_based_cell=3
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

