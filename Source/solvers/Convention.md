# Convention Cho Các Class Giải Tìm Đường Đi
Kế thừa từ `class SolverBaseModel`  



# Encoding
## Trạng thái của hình chữ nhật  
Hình chữ nhật trong trò chơi mê cung có 2 trạng thái đó là **Đứng** và **Nằm**, chúng ta quy ước nó có giá trị sau:  
- **Đứng**: int = 0  
- **Nằm**: int  = 1




## Đối với người sử dụng các thuật giải
Khi cần **sử dụng 1 trong 4 thuật giải** tìm kiếm trên cần gọi theo format sau:  
ClassGiai(ma\_trận\_mê\_cung, tọa\_độ\_bắt\_đầu, tọa\_độ\_đích\_đến)


Lưu ý:  
- Đối với các **màn chơi cần phải bắt cầu đi qua** thì nó không thể giải được ngay mà cần phải thiết kế thêm lớp ví dụ như `GameSolver` để xác định các vị trí bắt buộc phải đến để có thể qua màn.  

- Phải encode các ô đi được và không đi được trước khi đưa vào `GraphMaze`, bất cứ ký tự nào không phải là `valid_tile` đều được xem là một `invalid_tile` và không thể đi qua được  


## Đối với người Implement các giải thuật còn lại
Cần **Thêm vào dfs.py, bfd.py** tương tự như giải thuật ở **astar.py và ucs.py**. Đồng thời **hoàn thiện code ở seaches.py** cho 2 thuật toán tìm kiếm trên  

Nếu **sử dụng Coding Agent** thì context cần gửi như sau: **graph.py, searches.py, astar.py( hoặc dfs.py)** để hoàn thiện code