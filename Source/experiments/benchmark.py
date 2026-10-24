"""
Mô tả:
Script này đóng vai trò như một hệ thống kiểm định tự động (Automated Testing & Benchmarking).
Nhiệm vụ chính:
1. Tự động quét và đọc toàn bộ các màn chơi (levels) có trong hệ thống.
2. Cắm lần lượt các thuật toán tìm kiếm (BFS, DFS, UCS, A*) vào từng màn chơi.
3. Ghi nhận 4 chỉ số hiệu suất bắt buộc: Time (s), Memory (KB), Expanded Nodes, và Solution Length.
4. Tổng hợp và xuất ra file results.csv để lấy dữ liệu vẽ biểu đồ vào file Report.pdf.
"""
import os
import sys
import time
import csv
from glob import glob

# Dòng này giúp Python lùi ra ngoài 1 cấp thư mục để nhận diện được package 'game'
# Giải thích cho Nhóm: Vì file benchmark này nằm sâu trong thư mục /experiments/, 
# nên cần sys.path này để Python "nhìn" thấy thư mục /game/ và /solvers/ ở ngoài.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# TODO  Mở comment các import dưới đây khi TV1, TV2, TV3 đã code xong
# from game.level import load_level
# from solvers.bfs import solve as solve_bfs
# from solvers.astar import solve as solve_astar
# 1. HÀM GIẢ LẬP THUẬT TOÁN (MOCK SOLVER)
def mock_solve_bfs(level):
    """Giả lập thuật toán BFS chạy mất 0.5s"""
    time.sleep(0.5)
    return {
        "search_time": 0.521,
        "memory_peak": 1024.5,
        "expanded_nodes": 150,
        "solution_length": 12
    }

def mock_solve_astar(level):
    """Giả lập thuật toán A* chạy mất 0.1s"""
    time.sleep(0.1)
    return {
        "search_time": 0.105,
        "memory_peak": 512.2,
        "expanded_nodes": 45,
        "solution_length": 12
    }

# TDFS và UCS 

# 2. HÀM CHẠY BENCHMARK CHÍNH
def run_benchmark():
    # Tìm tất cả các file JSON màn chơi trong thư mục levels
    # Đường dẫn tương đối từ Source/experiments/ -> ../levels/
    level_files = glob(os.path.join("..", "levels", "*.json"))
    level_files.sort()

    results = []

    print(f"Đã tìm thấy {len(level_files)} màn chơi. Bắt đầu benchmark...\n")

    for file_path in level_files:
        level_name = os.path.basename(file_path)
        print(f"Đang xử lý: {level_name}")
        # level = load_level(file_path) # Load dữ liệu thật khi ghép code

        # Chạy BFS
        stats_bfs = mock_solve_bfs(level_name)  # Truyền level vào khi ghép code thật
        results.append({
            "Level": level_name,
            "Algorithm": "BFS",
            "Time (s)": stats_bfs["search_time"],
            "Memory (KB)": stats_bfs["memory_peak"],
            "Nodes": stats_bfs["expanded_nodes"],
            "Steps": stats_bfs["solution_length"]
        })

        # Chạy A*
        stats_astar = mock_solve_astar(level_name)
        results.append({
            "Level": level_name,
            "Algorithm": "A*",
            "Time (s)": stats_astar["search_time"],
            "Memory (KB)": stats_astar["memory_peak"],
            "Nodes": stats_astar["expanded_nodes"],
            "Steps": stats_astar["solution_length"]
        })

    # 3. XUẤT KẾT QUẢ RA FILE CSV
    csv_file = "results.csv"
    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Level", "Algorithm", "Time (s)", "Memory (KB)", "Nodes", "Steps"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\nĐã xuất kết quả thành công ra file: {csv_file}")

if __name__ == "__main__":
    run_benchmark()