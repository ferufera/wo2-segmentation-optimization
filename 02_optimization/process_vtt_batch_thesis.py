import os
import glob
import re
import sys

# ==============================================================================
# CONFIGURATION
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(current_dir, '..', 'data', 'vtt_files')
OUTPUT_DIR = os.path.join(current_dir, '..', 'results', 'ready_prompts_thesis')

# ==============================================================================
# LOCAL IMPORTS
# ==============================================================================
sys.path.append(current_dir)

try:
    from models import Caption

    from original_prompts_archive import _build_segment_prompt as build_original
    from refined_prompts import _build_segment_prompt as build_refined
    from thesis_prompts import _build_segment_prompt as build_thesis

    print("Success: Loaded original, refined, and thesis prompt logic.")

except ImportError as e:
    print("\n[CRITICAL ERROR] Missing required files.")
    print(f"Details: {e}")
    sys.exit(1)

# ==============================================================================
# HELPERS
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

    pattern = re.compile(
        r'((?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3}) --> ((?:\d{2}:)?\d{2}:\d{2}[\.,]\d{3}).*?\n(.*?)(?=\n\n|\Z)',
        re.DOTALL
    )

    for match in pattern.finditer(content):
        text_content = match.group(3).strip().replace('\n', ' ')
        if text_content:
            captions.append(Caption(
                start=parse_vtt_time(match.group(1)),
                end=parse_vtt_time(match.group(2)),
                text=text_content
            ))
    return captions

# ==============================================================================
# MAIN
# ==============================================================================
def process_batch():
    if not os.path.exists(DATA_DIR):
        print(f"[ERROR] Data folder not found at: {os.path.abspath(DATA_DIR)}")
        return

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    vtt_files = glob.glob(os.path.join(DATA_DIR, "*.vtt"))

    if not vtt_files:
        print("[WARNING] No .vtt files found in data folder.")
        return

    print(f"Processing {len(vtt_files)} files (Generating Original / Refined / Thesis prompts)...")

    for filepath in vtt_files:
        filename = os.path.basename(filepath)
        print(f"  > {filename}")

        captions = parse_vtt_file(filepath)
        if captions:
            try:
                prompt_old = build_original(captions)
                path_old = os.path.join(OUTPUT_DIR, filename.replace('.vtt', '_ORIGINAL.txt'))
                with open(path_old, 'w', encoding='utf-8') as f:
                    f.write(prompt_old)

                prompt_refined = build_refined(captions)
                path_refined = os.path.join(OUTPUT_DIR, filename.replace('.vtt', '_REFINED.txt'))
                with open(path_refined, 'w', encoding='utf-8') as f:
                    f.write(prompt_refined)

                prompt_thesis = build_thesis(captions)
                path_thesis = os.path.join(OUTPUT_DIR, filename.replace('.vtt', '_THESIS.txt'))
                with open(path_thesis, 'w', encoding='utf-8') as f:
                    f.write(prompt_thesis)

            except Exception as e:
                print(f"    [!] Error processing {filename}: {e}")
        else:
            print("    [!] No captions found.")

    print(f"\nDone! Prompt files saved to: {os.path.abspath(OUTPUT_DIR)}")

if __name__ == "__main__":
    process_batch()