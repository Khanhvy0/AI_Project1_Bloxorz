import os
 
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
 
CSV_FILE = "results.csv"
OUTPUT_DIR = "charts"
ALGORITHM_ORDER = ["BFS", "DFS", "UCS", "A*"]
METRICS = [
    ("Time (s)", "Thời gian tìm kiếm (giây)", "time"),
    ("Memory (KB)", "Bộ nhớ đỉnh (KB)", "memory"),
    ("Nodes", "Số node đã mở rộng", "nodes"),
    ("Steps", "Độ dài đường đi (số bước)", "steps"),
    ("Cost", "Chi phí đường đi", "cost"),
]
 
 
def load_data(path):
    df = pd.read_csv(path)
    for column, _, _ in METRICS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["Level"] = df["Level"].astype(str).str.replace(".json", "", regex=False)
    df.loc[df["Steps"] < 0, "Steps"] = np.nan
    df.loc[df["Cost"] < 0, "Cost"] = np.nan
    return df
 
 
def geometric_mean(values):
    values = values.dropna()
    values = values[values > 0]
    return np.exp(np.log(values).mean()) if len(values) else np.nan
 
 
def plot_per_level(df, column, title, name):
    levels = list(dict.fromkeys(df["Level"]))
    fig, ax = plt.subplots(figsize=(max(12, len(levels) * 0.45), 5.5))
    sns.lineplot(data=df, x="Level", y=column, hue="Algorithm", style="Algorithm",
                 hue_order=ALGORITHM_ORDER, style_order=ALGORITHM_ORDER,
                 markers=True, dashes=False, ax=ax, sort=False)
    ax.set_yscale("log")
    ax.set_title(f"{title} theo từng màn chơi", fontsize=14, fontweight="bold")
    ax.set_xlabel("Màn chơi")
    ax.set_ylabel(f"{title} (thang log)")
    ax.tick_params(axis="x", rotation=0)
    ax.legend(title="Thuật toán", ncol=4, loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, f"{name}_per_level.png"), dpi=300)
    plt.close(fig)
 
 
def plot_summary(df):
    fig, axes = plt.subplots(1, len(METRICS), figsize=(4.6 * len(METRICS), 4.5))
    for ax, (column, title, _) in zip(axes, METRICS):
        summary = (df.groupby("Algorithm")[column].apply(geometric_mean)
                   .reindex(ALGORITHM_ORDER))
        sns.barplot(x=summary.index, y=summary.values, hue=summary.index,
                    palette="viridis", legend=False, ax=ax)
        for i, value in enumerate(summary.values):
            if not np.isnan(value):
                ax.text(i, value, f"{value:.3g}", ha="center", va="bottom", fontsize=9)
        ax.set_title(title, fontsize=12, fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("Trung bình nhân")
    fig.suptitle("So sánh tổng quát bốn thuật toán", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "summary.png"), dpi=300)
    plt.close(fig)
 
 
def check_optimality(df):
    pivot = df.pivot_table(index="Level", columns="Algorithm", values="Cost")
    if not {"UCS", "A*"}.issubset(pivot.columns) or pivot[["UCS", "A*"]].isna().all().all():
        print("[WARNING] Không có đủ dữ liệu Cost để kiểm tra tính tối ưu.")
        return
    pivot.index = pivot.index.astype(int)
    pivot = pivot.sort_index()
    eps = 1e-9
    bad = pivot[pivot["A*"] > pivot["UCS"] + eps]
    worse = pivot[pivot["UCS"] > pivot.drop(columns="UCS").min(axis=1) + eps]
    if bad.empty and worse.empty:
        print("[OK] A* và UCS có cùng Cost ở mọi màn; không thuật toán nào rẻ hơn UCS.")
        return
    for level, row in bad.iterrows():
        print(f"[CẢNH BÁO] Màn {level}: A* Cost = {row['A*']} > UCS Cost = {row['UCS']}")
    for level, row in worse.iterrows():
        print(f"[CẢNH BÁO] Màn {level}: UCS Cost = {row['UCS']} nhưng có thuật toán rẻ hơn")
 
 
def main():
    sns.set_theme(style="whitegrid")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data(CSV_FILE)
    check_optimality(df)
 
    for column, title, name in METRICS:
        plot_per_level(df, column, title, name)
    plot_summary(df)
 
    print(f"Đã lưu biểu đồ vào thư mục '{OUTPUT_DIR}'")
 
 
if __name__ == "__main__":
    main()
 