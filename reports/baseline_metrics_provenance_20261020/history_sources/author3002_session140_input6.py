# Original=3002 /home/ssddata/liutuo/.ipython/profile_default/history.sqlite
# session=140; input_line=6; source_sha256=80683e3e5bb43604c0f6143c6c5a655fcabe52cfff384c9ca47b8f76bdd324c0
import pandas as pd

# 文件路径
file_path = '/home/ssddata/liutuo/liutuo_data/新建 XLS 工作表.xls'

# 读取 Sheet1
df = pd.read_excel(file_path, sheet_name='Sheet1')

# 删除全空列
df = df.dropna(axis=1, how='all')

# 重命名列名
df.columns = [
    'Methods', 'FDG-SSIM(%) ↑', 'FDG-PSNR ↑', 'FDG-MSE(%) ↓', 'FDG-MAE(%) ↓',
    'AV45-SSIM(%) ↑', 'AV45-PSNR ↑', 'AV45-MSE(%) ↓', 'AV45-MAE(%) ↓',
    'OASIS-AV45-SSIM(%) ↑', 'OASIS-AV45-PSNR ↑', 'OASIS-AV45-MSE(%) ↓', 'OASIS-AV45-MAE(%) ↓'
]

# 去除索引，生成 LaTeX 表格
latex_table = df.to_latex(index=False, caption="Performance Comparison of Different Methods on PET Image Synthesis", label="tab:performance")

# 打印 LaTeX 表格
print("以下是生成的 LaTeX 表格：\n")
print(latex_table)