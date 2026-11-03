# Derived source excerpt; historical code was not executed.
# Original: 3003:/home/data/liutuo/.ipython/profile_default/history.sqlite
# Original file SHA-256: ed3b8a2582984ed63dc619765b6cd3139a4b13b79177d1874d7a2c96ca5951c0
# IPython session 287, input 19.
# Source SHA-256: c18bb9c657fea5a1ea5ea4f9283ca1b420d7d8b3fbb9c4787bf513463753081b

import os
import re

def remove_fixed_and_dynamic_subpath_from_all_files(directory, fixed_subpath, subpath_pattern):
    """
    批量处理目录中的所有文件，去除路径中固定部分和动态时间戳部分。
    :param directory: 目标目录
    :param fixed_subpath: 固定的路径部分
    :param subpath_pattern: 动态部分的正则模式（如时间戳）
    :return: 处理后的文件路径列表
    """
    # 获取目录下所有文件
    all_files = []
    for root, dirs, files in os.walk(directory):
        for file in files:
            file_path = os.path.join(root, file)
            # 先移除固定的路径部分
            cleaned_path = file_path.replace(fixed_subpath, '')
            # 使用正则表达式删除动态的时间戳部分
            cleaned_path = re.sub(subpath_pattern, '', cleaned_path)
            all_files.append(cleaned_path)
                
    return all_files

# 输入的根目录
base_directory = '/home/data/liutuo/code/liutuo_data/ADNI - av45'

# 固定的路径部分
fixed_subpath = '/ADNI_Brain_PET__Raw_AV45'

# 匹配时间戳的正则模式
subpath_pattern = r'/\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2}\.0'

# 获取处理后的路径列表
processed_files = remove_fixed_and_dynamic_subpath_from_all_files(base_directory, fixed_subpath, subpath_pattern)

# 将处理后的路径保存到文件中
with open('processed_files.txt', 'w') as f:
    for file in processed_files:
        f.write(file + '\n')

print("Processed file paths have been saved to 'processed_files.txt'")