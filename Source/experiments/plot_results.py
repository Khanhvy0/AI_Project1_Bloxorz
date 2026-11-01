import os
 
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
 
BASE = os.path.dirname(os.path.abspath(__file__))
CSV_FILE = os.path.join(BASE, "results.csv")
OUTPUT_DIR = os.path.join(BASE, "charts")
 
# Thứ tự hiển thị; thuật toán nào không có trong CSV sẽ tự bị bỏ qua.
# (DFS giữ lại để đọc được file CSV cũ.)
ALGORITHM_ORDER = ["BFS", "IDS", "DFS", "UCS", "A*"]
METRICS = [
    ("Time (s)", "Thời gian tìm kiếm (giây)", "time"),
    ("Memory (KB)", "Bộ nhớ đỉnh (KB)", "memory"),
    ("Nodes", "Số node đã mở rộng", "nodes"),
    ("Steps", "Độ dài đường đi (số bước)", "steps"),
    ("Cost", "Chi phí đường đi", "cost"),
]
 
 
def load_data(path):
    df = pd.read_csv(path)
    # Các ô "Error" / "Timeout" / rỗng sẽ thành NaN (không có số liệu).
    for column, _, _ in METRICS:
        df[column] = pd.to_numeric(df[column], errors="coerce")
    df["Level"] = pd.to_numeric(
        df["Level"].astype(str).str.replace(".json", "", regex=False), errors="coerce"
    ).astype("Int64")
    df = df.dropna(subset=["Level"])
    df["Level"] = df["Level"].astype(int)
    df.loc[df["Steps"] < 0, "Steps"] = np.nan
    df.loc[df["Cost"] < 0, "Cost"] = np.nan
    return df.sort_values(["Level", "Algorithm"]).reset_index(drop=True)
 
 
def algorithm_order(df):
    present = set(df["Algorithm"])
    return [a for a in ALGORITHM_ORDER if a in present]
 
 
def report_missing(df):
    """In ra các màn không có số liệu (lỗi, timeout, không giải được) của từng thuật toán."""
    print("[INFO] Số liệu thiếu (NaN) theo thuật toán:")
    any_missing = False
    for alg in algorithm_order(df):
        sub = df[df["Algorithm"] == alg]
        levels = sorted(sub.loc[sub["Cost"].isna(), "Level"].tolist())
        if levels:
            any_missing = True
            print(f"  - {alg}: thiếu {len(levels)} màn: {levels}")
    if not any_missing:
        print("  (không thiếu màn nào)")
 
 
def geometric_mean(values):
    values = values.dropna()
    values = values[values > 0]
    return np.exp(np.log(values).mean()) if len(values) else np.nan
 
 
def plot_per_level(df, column, title, name, order):
    levels = sorted(df["Level"].unique())
    data = df.copy()
    data.loc[data[column] <= 0, column] = np.nan   # thang log không vẽ được giá trị <= 0
    fig, ax = plt.subplots(figsize=(max(12, len(levels) * 0.45), 5.5))
    sns.lineplot(data=data, x="Level", y=column, hue="Algorithm", style="Algorithm",
                 hue_order=order, style_order=order,
                 markers=True, dashes=False, ax=ax)
    ax.set_yscale("log")
    ax.set_xticks(levels)
    ax.set_title(f"{title} theo từng màn chơi", fontsize=14, fontweight="bold")
    ax.set_xlabel("Màn chơi")
    ax.set_ylabel(f"{title} (thang log)")
    ax.legend(title="Thuật toán", ncol=len(order), loc="upper left")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, f"{name}_per_level.png"), dpi=300)
    plt.close(fig)
 
 
def plot_summary(df, order):
    # Chỉ so sánh trên các màn mà MỌI thuật toán đều có số liệu cho chỉ số đó,
    # để thuật toán bị timeout/lỗi không làm lệch trung bình.
    fig, axes = plt.subplots(1, len(METRICS), figsize=(4.6 * len(METRICS), 4.5))
    for ax, (column, title, _) in zip(axes, METRICS):
        wide = df.pivot_table(index="Level", columns="Algorithm", values=column)
        wide = wide.reindex(columns=order).dropna()
        summary = wide.apply(geometric_mean)
        sns.barplot(x=summary.index, y=summary.values, hue=summary.index,
                    palette="viridis", legend=False, ax=ax)
        for i, value in enumerate(summary.values):
            if not np.isnan(value):
                ax.text(i, value, f"{value:.3g}", ha="center", va="bottom", fontsize=9)
        ax.set_title(f"{title}\n({len(wide)} màn có đủ số liệu)", fontsize=11, fontweight="bold")
        ax.set_xlabel("")
        ax.set_ylabel("Trung bình nhân")
    fig.suptitle(f"So sánh tổng quát {len(order)} thuật toán", fontsize=15, fontweight="bold")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTPUT_DIR, "summary.png"), dpi=300)
    plt.close(fig)
 
 
def check_optimality(df):
    pivot = df.pivot_table(index="Level", columns="Algorithm", values="Cost")
    if not {"UCS", "A*"}.issubset(pivot.columns) or pivot[["UCS", "A*"]].isna().all().all():
        print("[WARNING] Không có đủ dữ liệu Cost để kiểm tra tính tối ưu.")
        return
    pivot = pivot.sort_index()
    eps = 1e-9
    both = pivot.dropna(subset=["UCS", "A*"])
    bad = both[(both["A*"] - both["UCS"]).abs() > eps]
    others = pivot.drop(columns=["UCS"])
    cheaper = pivot[pivot["UCS"].notna() & (pivot["UCS"] > others.min(axis=1) + eps)]
    print(f"[INFO] So sánh Cost A* và UCS trên {len(both)} màn có đủ số liệu.")
    if bad.empty and cheaper.empty:
        print("[OK] A* và UCS có cùng Cost ở mọi màn; không thuật toán nào rẻ hơn UCS.")
        return
    for level, row in bad.iterrows():
        print(f"[CẢNH BÁO] Màn {level}: A* Cost = {row['A*']} khác UCS Cost = {row['UCS']}")
    for level, row in cheaper.iterrows():
        print(f"[CẢNH BÁO] Màn {level}: UCS Cost = {row['UCS']} nhưng có thuật toán rẻ hơn")
 
 
def main():
    sns.set_theme(style="whitegrid")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    df = load_data(CSV_FILE)
    order = algorithm_order(df)
 
    report_missing(df)
    check_optimality(df)
 
    for column, title, name in METRICS:
        plot_per_level(df, column, title, name, order)
    plot_summary(df, order)
 
    print(f"Đã lưu biểu đồ vào thư mục '{OUTPUT_DIR}'")
 
 
if __name__ == "__main__":
    main()