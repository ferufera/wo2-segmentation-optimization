import os
import glob
import re
import sys

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# 1. Get current folder (02_optimization)
current_dir = os.path.dirname(os.path.abspath(__file__))

# 2. Define Data Paths (Go up one level '..' to root)
DATA_DIR = os.path.join(current_dir, '..', 'data', 'vtt_files')
OUTPUT_DIR = os.path.join(current_dir, '..', 'results', 'ready_prompts')

# ==============================================================================
# LOCAL IMPORTS
# ==============================================================================
try:
    from models import Caption
    from refined_prompts import _build_segment_prompt
    print("Success: Loaded local modules.")
except ImportError as e:
    print(f"[ERROR] Missing files. Make sure models.py and refined_prompts.py are in {current_dir}")
    print(f"Details: {e}")
    sys.exit(1)

# ==============================================================================
# LOGIC
# ==============================================================================
def parse_vtt_time(timestamp):
    parts = timestamp.replace(',', '.').split(':')
    if len(parts) == 3:
        h, m, s = parts
        return int(h) * 3600 + int(m) * 60 + float(s)
    elif len(parts) == 2:
        m, s = parts
        return int(m) * 60 + float(s)
    return 0.0

def parse_vtt_file(filepath):
    captions = []
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex: (Start) --> (End) \n (Text)
    pattern = re.compile(r'(\d{2}:?\d{2}:\d{2}[\.,]\d{3}) --> (\d{2}:?\d{2}:\d{2}[\.,]\d{3}).*?\n(.*?)(?=\n\n|\Z)', re.DOTALL)
    
    for match in pattern.finditer(content):
        text_content = match.group(3).strip().replace('\n', ' ')
        if text_content:
            captions.append(Caption(
                start=parse_vtt_time(match.group(1)), 
                end=parse_vtt_time(match.group(2)),
                text=text_content
            ))
    return captions

def process_batch():
    # Verify Paths
    if not os.path.exists(DATA_DIR):
        print(f"[ERROR] Data folder not found at: {os.path.abspath(DATA_DIR)}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vtt_files = glob.glob(os.path.join(DATA_DIR, "*.vtt"))
    
    if not vtt_files:
        print("[WARNING] No .vtt files found in data folder.")
        return

    print(f"Processing {len(vtt_files)} files...")
    
    for filepath in vtt_files:
        filename = os.path.basename(filepath)
        print(f"  > {filename}")
        
        captions = parse_vtt_file(filepath)
        if captions:
            try:
                prompt = _build_segment_prompt(captions)
                out_path = os.path.join(OUTPUT_DIR, filename.replace('.vtt', '_prompt.txt'))
                with open(out_path, 'w', encoding='utf-8') as f:
                    f.write(prompt)
            except Exception as e:
                print(f"    [!] Error: {e}")
        else:
            print("    [!] No captions found.")

    print(f"\nDone! Results saved to: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    process_batch()