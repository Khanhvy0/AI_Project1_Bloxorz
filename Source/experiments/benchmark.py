"""
Mô tả:
Script chạy kiểm định tự động 4 thuật toán (BFS, DFS, UCS, A*) 
tích hợp trực tiếp với cấu trúc EngineGraph và các class solver của nhóm.
Đã tích hợp cơ chế tự động đo thời gian chuẩn xác và bóc tách dữ liệu linh hoạt.
"""

import os
import sys
import time
import csv
from glob import glob

# ==========================================
# CẤU HÌNH ĐƯỜNG DẪN 
# ==========================================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)

from game.level import load_level
from solvers.utils.engine_graph import EngineGraph  # Cầu nối graph của nhóm

# ==========================================
# IMPORT 4 CLASS THUẬT TOÁN TỪ NHÓM
# ==========================================
from solvers.bfs import BFSSovler
from solvers.dfs import DFSSovler
from solvers.ucs import UCSovler
from solvers.astar import AStarSovler

def run_benchmark():
    levels_path = os.path.join(BASE_DIR, "levels", "*.json")
    level_files = glob(levels_path)
    level_files.sort()
    
    results = [] 
    print(f"[INFO] Đã tìm thấy {len(level_files)} màn chơi. Bắt đầu quá trình Benchmark...\n")

    algorithms = [
        ("BFS", BFSSovler),
        ("DFS", DFSSovler),
        ("UCS", UCSovler),
        ("A*", AStarSovler)
    ]

    for file_path in level_files:
        level_name = os.path.basename(file_path)
        print(f"[PROCESS] Đang tiến hành đánh giá dữ liệu trên map: {level_name}")
        
        for alg_name, AlgClass in algorithms:
            try:
                # 1. Load lại map mới hoàn toàn
                level_data = load_level(file_path)

                # 2. Đóng gói level_data thành EngineGraph theo đúng chuẩn kiến trúc
                graph = EngineGraph(level_data)

                # 3. Khởi tạo đối tượng thuật toán với graph đã chuyển đổi
                agent = AlgClass(graph=graph)

                # 4. BẮT ĐẦU TỰ ĐO THỜI GIAN THỰC TẾ BẰNG PERF_COUNTER
                start_time = time.perf_counter()

                # Tự động nhận diện hàm thực thi (.search() hoặc .solve())
                if hasattr(agent, 'search'):
                    stats = agent.search()
                elif hasattr(agent, 'solve'):
                    stats = agent.solve()
                else:
                    raise AttributeError(f"Class {alg_name} không tìm thấy phương thức thực thi (.search lịch .solve)")

                end_time = time.perf_counter()
                elapsed_time = end_time - start_time  # Thời gian thực thi (giây)

                # 5. Trích xuất chỉ số linh hoạt (Hỗ trợ cả Object lẫn Dictionary)
                if isinstance(stats, dict):
                    mem_val = stats.get("memory", stats.get("memory_peak", 0))
                    nodes_val = stats.get("expanded_nodes", stats.get("nodes", 0))
                    # Quét đa dạng các tên biến chứa đường đi do thành viên đặt
                    path_val = stats.get("path", stats.get("actions", stats.get("moves", [])))
                else:
                    mem_val = getattr(stats, "memory", getattr(stats, "memory_peak", 0))
                    nodes_val = getattr(stats, "expanded_nodes", getattr(stats, "nodes", 0))
                    path_val = getattr(stats, "path", getattr(stats, "actions", getattr(stats, "moves", [])))

                # Đảm bảo thời gian hiển thị không bị bằng 0 tuyệt đối nếu chạy quá nhanh
                final_time = elapsed_time if elapsed_time > 0 else 0.0001

                # 6. Ghi kết quả chuẩn hóa vào danh sách
                results.append({
                    "Level": level_name,
                    "Algorithm": alg_name,
                    "Time (s)": round(final_time, 4),                     
                    "Memory (KB)": mem_val,                      
                    "Nodes": nodes_val,                    
                    "Steps": len(path_val) if path_val else 0 
                })
            except Exception as e:
                print(f"    [ERROR] Lỗi thực thi {alg_name} trên {level_name}: {e}")
                results.append({
                    "Level": level_name, 
                    "Algorithm": alg_name,
                    "Time (s)": "Error", 
                    "Memory (KB)": "Error",
                    "Nodes": "Error", 
                    "Steps": "Error"
                })

    # ==========================================
    # XUẤT FILE CSV
    # ==========================================
    csv_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results.csv")
    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["Level", "Algorithm", "Time (s)", "Memory (KB)", "Nodes", "Steps"])
        writer.writeheader()
        writer.writerows(results)

    print(f"\n[SUCCESS] Quá trình Benchmark hoàn tất. Kết quả được xuất tại: {csv_file}")

if __name__ == "__main__":
    run_benchmark()