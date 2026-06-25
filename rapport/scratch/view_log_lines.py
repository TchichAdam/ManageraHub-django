def view_lines(file_path, start_line, end_line):
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    for i in range(start_line - 1, min(end_line, len(lines))):
        print(f"{i+1}: {lines[i].strip()}")

if __name__ == '__main__':
    view_lines(r'C:\Users\adam\Desktop\New folder\ManageraHub\rapport\main.log', 1000, 1050)
