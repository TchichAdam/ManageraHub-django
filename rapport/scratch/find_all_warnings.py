import re

def find_warnings(log_path):
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()

    current_files = []
    file_open_re = re.compile(r'\(([^()\s]+\.tex|[^()\s]+\.sty|[^()\s]+\.cls|[^()\s]+\.fd|[^()\s]+\.aux)')
    
    # We will scan line by line.
    # We want to match:
    # 1. File openings like (chapters/chapitre1.tex or (main.aux
    # 2. File closings like )
    # 3. Warnings
    
    warnings_found = []
    
    for i, line in enumerate(lines):
        # Clean up line endings
        line_str = line.strip()
        
        # Simple tracking of parenthesis to guess current file
        # Note: LaTeX log file parentheses are notoriously messy, but we can do a decent job:
        # If we see `(chapters/` or similar, it's a file open.
        # Let's search for .tex file names specifically:
        for match in re.finditer(r'\(([^()\s]+\.tex)', line):
            current_files.append(match.group(1))
        
        # If the line ends with ) or has ) preceded by space/newline, it might be a close
        # But to be simple, let's look for known files.
        # If we see a warning like "Overfull \hbox ... at lines X--Y", we print it with the last known .tex file
        if 'Overfull \\hbox' in line or 'Underfull \\hbox' in line or 'Underfull \\vbox' in line:
            active_file = current_files[-1] if current_files else "unknown"
            warnings_found.append((i+1, active_file, line_str))
            # Also capture the next few lines of details
            detail = []
            for k in range(1, 4):
                if i + k < len(lines) and lines[i+k].strip():
                    detail.append(lines[i+k].strip())
            warnings_found[-1] = (i+1, active_file, line_str, " | ".join(detail))

    print(f"Found {len(warnings_found)} warnings:")
    for log_ln, filename, msg, detail in warnings_found:
        print(f"Log L{log_ln} | File: {filename} | {msg}")
        if detail:
            print(f"   Details: {detail}")

if __name__ == '__main__':
    find_warnings(r'C:\Users\adam\Desktop\New folder\ManageraHub\rapport\main.log')
