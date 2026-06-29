import os
import json
from dataclasses import dataclass

# ==============================================================================
# 1. SETUP
# ==============================================================================
@dataclass
class Caption:
    index: int
    start: float
    end: float
    text: str

# FIX: Go UP one level ('..') to find data
VTT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'data', 'vtt_files')
JSON_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'results', 'json_outputs')
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'results', 'generated_prompts', 'step2_metadata')
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

# ==============================================================================
# 2. IMPORT LOGIC
# ==============================================================================
try:
    from refined_prompts import (
        _build_segment_title_prompt as refined_title,
        _build_topdown_matching_prompt as refined_concept
    )
    from original_prompts_archive import (
        _build_segment_title_prompt as original_title,
        _build_topdown_matching_prompt as original_concept
    )
except ImportError as e:
    print(f"Error importing prompts: {e}")
    exit()

# ==============================================================================
# 3. HELPER: RE-READ VTT
# ==============================================================================
def parse_vtt(vtt_path):
    captions = []
    try:
        with open(vtt_path, 'r', encoding='utf-8') as f:
            content = f.read()
        blocks = content.split('\n\n')
        for i, block in enumerate(blocks):
            lines = block.strip().split('\n')
            text_lines = [l for l in lines if '-->' not in l and not l.isdigit() and 'WEBVTT' not in l]
            if text_lines:
                captions.append(Caption(i, 0.0, 0.0, " ".join(text_lines)))
        return captions
    except: return []

def get_text(captions, indices):
    parts = []
    valid_indices = [int(i) for i in indices if str(i).isdigit()]
    for cap in captions:
        if cap.index in valid_indices:
            parts.append(cap.text)
    return " ".join(parts)

# ==============================================================================
# 4. MAIN GENERATOR
# ==============================================================================
def generate_step2():
    print(f"Step 2: Generating Metadata Prompts from existing JSONs...")
    
    if not os.path.exists(JSON_FOLDER):
        print(f"Error: JSON folder not found at {JSON_FOLDER}")
        return

    json_files = [f for f in os.listdir(JSON_FOLDER) if f.endswith(".json")]
    
    if not json_files:
        print("No JSON files found! You must finish Step 1 manual processing first.")
        return

    for json_file in json_files:
        # Determine Mode and ID
        if "_REFINED_" in json_file:
            mode = "REFINED"
            file_id = json_file.split("_REFINED_")[0]
            title_fn, concept_fn = refined_title, refined_concept
        elif "_ORIGINAL_" in json_file:
            mode = "ORIGINAL"
            file_id = json_file.split("_ORIGINAL_")[0]
            title_fn, concept_fn = original_title, original_concept
        else:
            continue

        # Fuzzy Match VTT
        vtt_path = None
        id_parts = file_id.lower().replace(' ', '_').split('_')
        for f in os.listdir(VTT_FOLDER):
            if f.endswith('.vtt'):
                fname_lower = f.lower()
                match_count = sum(1 for p in id_parts if p in fname_lower)
                if match_count >= 2:
                    vtt_path = os.path.join(VTT_FOLDER, f)
                    break
        
        if not vtt_path: 
            print(f"Skipping {file_id}: No matching VTT found.")
            continue

        # Load Data
        captions = parse_vtt(vtt_path)
        try:
            with open(os.path.join(JSON_FOLDER, json_file), 'r', encoding='utf-8') as f:
                data = json.load(f)
        except: continue

        segments = data.get('segments', []) if isinstance(data, dict) else data

        # Build Output
        output_lines = []
        output_lines.append(f"=== METADATA PROMPTS FOR {file_id} ({mode}) ===")
        output_lines.append("Instructions: Paste these blocks into ChatGPT to get titles.\n")

        for i, seg in enumerate(segments):
            indices = seg.get('caption_indices', [])
            seg_text = get_text(captions, indices)
            if len(seg_text) < 10: continue

            output_lines.append(f"--- SEGMENT {i+1} ---")
            
            # Title
            seg_obj = {'text': seg_text, 'interviewee_name': "Ooggetuige"}
            t_prompt = title_fn(seg_obj)
            output_lines.append(f"[TITLE PROMPT]\n{t_prompt}\n")

            # Concept
            c_prompt = concept_fn([], seg_text)
            output_lines.append(f"[CONCEPT PROMPT]\n{c_prompt}\n")
            
            output_lines.append("-" * 40)

        # Save
        out_name = f"PROMPT_METADATA_{file_id}_{mode}.txt"
        with open(os.path.join(OUTPUT_FOLDER, out_name), 'w', encoding='utf-8') as f:
            f.write("\n".join(output_lines))
            
        print(f"✅ Generated Step 2 prompts for: {file_id} ({mode})")

    print(f"\nSaved to: {OUTPUT_FOLDER}")

if __name__ == "__main__":
    generate_step2()