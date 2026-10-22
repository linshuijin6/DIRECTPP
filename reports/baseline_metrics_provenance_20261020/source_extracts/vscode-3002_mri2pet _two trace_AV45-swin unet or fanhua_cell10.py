# Original=source_archive/vscode-3002/home/ssddata/liutuo/mri2pet _two trace_AV45-swin unet or fanhua.ipynb
# original_sha256=0755c31eeb8f628ec6f73a11e91a75577a8211337e8d5729d3a13deabef59489; zero_based_cell=10
import numpy as np
import matplotlib.pyplot as plt
from math import pi

# 数据定义
methods = ['Cyclegan', 'Swin-Unet', 'DDIM(3D)', 'SegGuidedDif', 'Rectified Flow', 'Ours(single)', 'Ours']
metrics = ['SSIM (%) ↑', 'PSNR ↑', 'MSE (%) ↓', 'MAE (%) ↓']  # 标注方向性
data = [
    [59.56, 15.43, 3.24, 8.39],  # Cyclegan
    [69.16, 17.54, 2.67, 7.95],  # Swin-Unet
    [73.37, 21.33, 1.73, 7.01],  # DDIM(3D)
    [80.29, 21.99, 1.12, 6.92],  # SegGuidedDif
    [85.43, 24.74, 0.69, 4.31],  # Rectified Flow
    [87.37, 27.11, 0.51, 3.16],  # Ours(single)
    [88.21, 28.09, 0.39, 2.73]   # Ours
]

# 数据标准化处理（对于↑指标越大越好，对于↓指标越小越好）
# 数据标准化处理（对于↑指标越大越好，对于↓指标越小越好）
def normalize_data(data):
    normalized_data = []
    for row in data:
        norm_row = []
        for i, value in enumerate(row):
            if "↑" in metrics[i]:  # 越大越好
                norm_row.append(value / max([r[i] for r in data]))
            elif "↓" in metrics[i]:  # 越小越好
                norm_row.append(min([r[i] for r in data]) / value)
        normalized_data.append(norm_row)
    return normalized_data

normalized_data = normalize_data(data)

# 创建雷达图
def plot_radar_chart(methods, metrics, data, save_path=None):
    num_vars = len(metrics)
    angles = np.linspace(0, 2 * pi, num_vars, endpoint=False).tolist()
    angles += angles[:1]  # 闭合图形

    fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

    # 绘制每个方法的线
    colors = plt.cm.tab10.colors  # 使用 tab10 颜色映射
    for i, method in enumerate(methods):
        values = data[i]
        values += values[:1]  # 闭合图形
        linewidth = 2 if method != 'Ours' else 4  # 突出 'Ours'
        ax.plot(angles, values, color=colors[i], label=method, linewidth=linewidth)
        ax.fill(angles, values, color=colors[i], alpha=0.25)

    # 设置标签
    ax.set_theta_offset(pi / 2)
    ax.set_theta_direction(-1)
    ax.set_thetagrids(np.degrees(angles[:-1]), [m.split(" ")[0] for m in metrics], fontsize=12)

    # 增加网格线
    ax.set_rgrids([0.2, 0.4, 0.6, 0.8, 1.0], angle=0, weight='black', fontsize=10)

    # 添加图例和标题
    ax.legend(loc='upper right', bbox_to_anchor=(1.3, 1.1), fontsize=12)
    plt.title("Performance Comparison (Radar Chart)", size=16, y=1.1)

    # 调整布局
    plt.tight_layout()

    # 如果提供了保存路径，则保存图像
    if save_path:
        os.makedirs(os.path.dirname(save_path), exist_ok=True)  # 确保目录存在
        plt.savefig(save_path, dpi=300, bbox_inches='tight')  # 保存图像，设置高分辨率
        print(f"Image saved to {save_path}")

    plt.show()

# 指定保存路径
save_path = "/home/ssddata/liutuo/radar_chartav45.png"

# 调用函数绘制蛛网图并保存
plot_radar_chart(methods, metrics, normalized_data, save_path)