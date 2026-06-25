import re

def parse_log(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        content = f.read()

    # Track open files using a stack structure
    file_regex = re.compile(r'(\(([^()]+)\)|(\)))')
    
    # We will step through the log, keeping track of the current file context.
    # A simpler way to get the exact lines of warnings is to print lines around "Overfull \\hbox" or "Underfull \\vbox"
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'Overfull \\hbox' in line:
            print(f"--- Warning at log line {i+1} ---")
            # Print 15 lines before and 5 lines after to see the file context
            start = max(0, i - 12)
            end = min(len(lines), i + 8)
            for j in range(start, end):
                marker = ">>> " if j == i else "    "
                print(f"{marker}{j+1}: {lines[j]}")

if __name__ == '__main__':
    parse_log(r'C:\Users\adam\Desktop\New folder\ManageraHub\rapport\main.log')
