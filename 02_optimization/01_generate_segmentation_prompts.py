import os
from dataclasses import dataclass

# ==============================================================================
# 1. SETUP & HELPER CLASSES
# ==============================================================================
@dataclass
class Caption:
    index: int
    start: float
    end: float
    text: str

# FIX: Go UP one level ('..') to find the 'data' folder
INPUT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data', 'vtt_files')

# Output path: Go UP one level ('..') to find 'results' folder
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'results', 'generated_prompts', 'step1_segmentation')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ==============================================================================
# 2. IMPORT LOGIC
# ==============================================================================
try:
    from refined_prompts import _build_segment_prompt as refined_seg
    from original_prompts_archive import _build_segment_prompt as original_seg
except ImportError as e:
    print(f"Error importing prompts: {e}")
    exit()

# ==============================================================================
# 3. VTT PARSER
# ==============================================================================
def parse_vtt(vtt_path):
    captions = []
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        blocks = content.split('\n\n')
        for i, block in enumerate(blocks):
            lines = block.strip().split('\n')
            time_line = next((l for l in lines if '-->' in l), None)
            text_lines = [l for l in lines if '-->' not in l and not l.isdigit() and 'WEBVTT' not in l]
            
            if time_line and text_lines:
                start_str = time_line.split('-->')[0].strip()
                parts = start_str.split(':')
                seconds = 0.0
                if len(parts) == 2: seconds = float(parts[0]) * 60 + float(parts[1])
                elif len(parts) == 3: seconds = float(parts[0]) * 3600 + float(parts[1]) * 60 + float(parts[2])
                
                captions.append(Caption(i, seconds, seconds+5.0, " ".join(text_lines)))
        return captions
    except: return []

# ==============================================================================
# 4. MAIN GENERATOR
# ==============================================================================
def generate_step1():
    print(f"Step 1: Generating Segmentation Prompts...")
    print(f"Looking for data in: {os.path.abspath(INPUT_FOLDER)}") # Debug print
    
    if not os.path.exists(INPUT_FOLDER):
        print("\n[ERROR] Still cannot find data folder!")
        print(f"Path looked for: {INPUT_FOLDER}")
        return

    files = [f for f in os.listdir(INPUT_FOLDER) if f.endswith(".vtt")]
    
    if not files:
        print("No VTT files found in data/vtt_files!")
        return

    for filename in files:
        file_id = filename.rsplit('.', 1)[0]
        vtt_path = os.path.join(INPUT_FOLDER, filename)
        captions = parse_vtt(vtt_path)
        if not captions: continue

        # --- REFINED PROMPT ---
        ref_text = f"=== COPY BELOW TO CHATGPT ===\n\n{refined_seg(captions)}\n"
        with open(os.path.join(OUTPUT_FOLDER, f"PROMPT_REFINED_{file_id}.txt"), 'w', encoding='utf-8') as f:
            f.write(ref_text)

        # --- ORIGINAL PROMPT ---
        orig_text = f"=== COPY BELOW TO CHATGPT ===\n\n{original_seg(captions)}\n"
        with open(os.path.join(OUTPUT_FOLDER, f"PROMPT_ORIGINAL_{file_id}.txt"), 'w', encoding='utf-8') as f:
            f.write(orig_text)
            
        print(f"✅ Generated prompts for: {file_id}")
    
    print(f"\nSaved to: {OUTPUT_FOLDER}")
    print("ACTION: Copy these text files into ChatGPT, then save the JSON output to 'results/json_outputs'.")

if __name__ == "__main__":
    generate_step1()