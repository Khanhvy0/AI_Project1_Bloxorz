import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 1. Đọc dữ liệu từ file CSV mà bạn vừa tạo
df = pd.read_csv('results.csv')

# 2. Thiết lập kiểu dáng biểu đồ
sns.set_theme(style="whitegrid")
fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Biểu đồ 1: Thời gian chạy
sns.barplot(x='Level', y='Time (s)', hue='Algorithm', data=df, ax=axes[0], palette='viridis')
axes[0].set_title('So sánh Thời gian chạy (Search Time)', fontsize=14, fontweight='bold')
axes[0].set_ylabel('Thời gian (giây)')
axes[0].set_xlabel('Màn chơi')
axes[0].tick_params(axis='x', rotation=45)

# Biểu đồ 2: Số node đã duyệt
sns.barplot(x='Level', y='Nodes', hue='Algorithm', data=df, ax=axes[1], palette='magma')
axes[1].set_title('So sánh Số Node đã duyệt (Expanded Nodes)', fontsize=14, fontweight='bold')
axes[1].set_ylabel('Số Node')
axes[1].set_xlabel('Màn chơi')
axes[1].tick_params(axis='x', rotation=45)

plt.tight_layout()

# 3. Lưu thành file ảnh
plt.savefig('benchmark_charts.png', dpi=300)
print("Đã vẽ xong biểu đồ và lưu thành file 'benchmark_charts.png'")