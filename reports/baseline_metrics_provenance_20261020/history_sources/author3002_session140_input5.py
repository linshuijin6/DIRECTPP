# Original=3002 /home/ssddata/liutuo/.ipython/profile_default/history.sqlite
# session=140; input_line=5; source_sha256=8e62505364c1c220567defe703f05e4ae78528a77e537904d419965324f5375d
import pandas as pd
from tabulate import tabulate

# 文件路径
file_path = '/home/ssddata/liutuo/liutuo_data/新建 XLS 工作表.xls'

# 读取 Sheet1
df = pd.read_excel(file_path, sheet_name='Sheet1')

# 删除全空列（例如 Unnamed 列）
df = df.dropna(axis=1, how='all')

# 重命名列名，使其更清晰
df.columns = [
    'Methods', 'FDG-SSIM(%) ↑', 'FDG-PSNR ↑', 'FDG-MSE(%) ↓', 'FDG-MAE(%) ↓',
    'AV45-SSIM(%) ↑', 'AV45-PSNR ↑', 'AV45-MSE(%) ↓', 'AV45-MAE(%) ↓',
    'OASIS-AV45-SSIM(%) ↑', 'OASIS-AV45-PSNR ↑', 'OASIS-AV45-MSE(%) ↓', 'OASIS-AV45-MAE(%) ↓'
]

# 转换为 LaTeX 表格
latex_table = tabulate(df, headers='keys', tablefmt='latex_raw', index=False)

# 打印 LaTeX 表格
print("以下是生成的 LaTeX 表格：\n")
print(latex_table)