
with open('slide_generator.py', 'r') as f:
    lines = f.readlines()

for i in range(160, 175):
    if i < len(lines):
        line = lines[i]
        print(f"Line {i+1}: {repr(line)}")
