# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 373, input 16.
# Source SHA-256: 11201be2d8050902347aea93de694268fec097d55685ca31396f7b6efb695245

import os

# 指定目录路径
directory = '/home/data/liutuo/code/liutuo_data/ADNI1234_mri_fdg_av45/mri_strip'

# 获取目录中所有文件的名称
file_names = os.listdir(directory)

# 提取前10位（或前11位）字符并去重
prefixes = set()
for file_name in file_names:
    # 提取前10位
    prefix_10 = file_name[12:]
    prefixes.add(prefix_10)
    

# 打印结果
print("提取的前缀（前10位或前11位）：")
for prefix in sorted(prefixes):
    print(prefix)