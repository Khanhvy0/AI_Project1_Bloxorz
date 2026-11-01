from pathlib import Path
import json
import random

def generate_open_level(size: int, name: str) -> dict:
    """Generate a fully connected rectangular level."""

    grid = [
        ["."] * size
        for _ in range(size)
    ]

    grid[0][0] = "S"
    grid[size - 1][size - 1] = "G"

    return {
        "name": name,
        "grid": ["".join(row) for row in grid],
        "bridges": {},
        "switches": []
    }


def generate_barrier_maze(
    size: int,
    name: str,
    wall_spacing: int = 8
) -> dict:
    """
    Generate vertical barriers with alternating
    three-cell-wide passages.
    """

    grid = [
        ["."] * size
        for _ in range(size)
    ]

    wall_index = 0

    for x in range(wall_spacing, size - 1, wall_spacing):
        # Alternate passage positions.
        gap_center = (
            size // 4
            if wall_index % 2 == 0
            else (3 * size) // 4
        )

        gap_start = max(0, gap_center - 1)
        gap_end = min(size, gap_center + 2)

        for y in range(size):
            if not gap_start <= y < gap_end:
                grid[y][x] = "#"

        wall_index += 1

    grid[0][0] = "S"
    grid[size - 1][size - 1] = "G"

    return {
        "name": name,
        "grid": ["".join(row) for row in grid],
        "bridges": {},
        "switches": []
    }


def generate_void_box_level(
    output_dir: str='levels/generate',
    filename: str = "massive_astar_showcase.json",
    rows: int = 40,
    cols: int = 60,
    num_voids: int = 8,
    min_void_size: int = 4,
    max_void_size: int = 15
):
    """
    Generates a large Bloxorz level with multiple void (#) boxes and saves it to JSON.
    """
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    # 1. Initialize an empty grid filled with solid tiles ('o')
    grid = [['o' for _ in range(cols)] for _ in range(rows)]
    
    # 2. Place Start ('S') at the top-left and Goal ('G') at the bottom-right
    start_pos = (2, 2)
    goal_pos = (rows - 3, cols - 3)
    grid[start_pos[0]][start_pos[1]] = 'S'
    grid[goal_pos[0]][goal_pos[1]] = 'G'
    
    # 3. Helper function to ensure we don't drop voids on top of S or G
    def is_safe_zone(r, c):
        # Keep a 4-tile safe radius around Start
        if abs(r - start_pos[0]) <= 4 and abs(c - start_pos[1]) <= 4:
            return False
        # Keep a 4-tile safe radius around Goal
        if abs(r - goal_pos[0]) <= 4 and abs(c - goal_pos[1]) <= 4:
            return False
        return True

    # 4. Carve out random void boxes
    for _ in range(num_voids):
        # Pick random top-left corner for the void
        vr = random.randint(1, rows - min_void_size - 1)
        vc = random.randint(1, cols - min_void_size - 1)
        
        # Pick random dimensions
        vh = random.randint(min_void_size, max_void_size)
        vw = random.randint(min_void_size, max_void_size)
        
        # Apply the void to the grid
        for r in range(vr, min(vr + vh, rows - 1)):
            for c in range(vc, min(vc + vw, cols - 1)):
                if is_safe_zone(r, c):
                    grid[r][c] = '#'
                    
    # 5. Convert 2D list of characters back to a list of strings
    grid_strings = ["".join(row) for row in grid]
    
    # 6. Construct the dictionary expected by MazeGraph
    level_data = {
        "name": "Massive_Random_Maze",
        "grid": grid_strings,
        "bridges": {},
        "switches": []
    }
    
    # 7. Write to JSON
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(level_data, f, indent=2)
        
    print(f"Success! Level generated with size {rows}x{cols} and saved to '{filename}'.")


def generate_test_suite(output_dir="levels/generate"):
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)

    cases = []

    # Open maps
    for size in [20, 50, 100, 200, 500, 800, 1000]:
        cases.append(
            generate_open_level(
                size,
                f"open_{size}x{size}"
            )
        )

    # Obstacle maps
    for size in [50, 100, 500, 800, 1000]:
        cases.append(
            generate_barrier_maze(
                size,
                f"maze_{size}x{size}"
            )
        )

    for level in cases:
        filename = output / f"{level['name']}.json"

        with filename.open("w") as f:
            json.dump(level, f, indent=2)

        print(f"Generated: {filename}")


if __name__ == "__main__":
    generate_test_suite('levels/generate')

    generate_void_box_level(
        filename="levels/generate/massive_void.json",
        rows=1000,
        cols=1000,
        num_voids=10, 
        min_void_size=100,
        max_void_size=200
    )

    generate_void_box_level(
            filename="levels/generate/small_void_but_lot.json",
            rows=1000,
            cols=1000,
            num_voids=100, 
            min_void_size=40,
            max_void_size=80
    )