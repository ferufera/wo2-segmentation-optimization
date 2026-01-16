import json
import os
import datetime

# ==============================================================================
# CONFIGURATION
# ==============================================================================
# 1. Setup Paths
current_dir = os.path.dirname(os.path.abspath(__file__))
json_folder = os.path.join(current_dir, '..', 'results', 'json_outputs')
report_folder = os.path.join(current_dir, '..', 'results', 'analysis_reports')

# Create the report folder if it doesn't exist
os.makedirs(report_folder, exist_ok=True)

# Common chatter indices to check for (Heuristic)
CHATTER_INDICES = [0, 1] 

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def load_json(filepath):
    """Safely loads a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not read {os.path.basename(filepath)}: {e}")
        return None

def calculate_avg_len(data):
    """Calculates average number of captions per segment."""
    if not data: return 0
    total_caps = sum([len(seg['caption_indices']) for seg in data])
    return round(total_caps / len(data), 1)

def find_file_pairs(folder):
    """Scans folder and pairs ORIGINAL files with REFINED files."""
    files = os.listdir(folder)
    pairs = []
    
    # Filter for ORIGINAL files first
    originals = [f for f in files if "_ORIGINAL_" in f and f.endswith(".json")]
    
    for orig_file in originals:
        # Determine the Base ID (everything before _ORIGINAL)
        base_id = orig_file.split("_ORIGINAL_")[0]
        
        # Construct the expected Refined filename
        # Assumes format: [ID]_ORIGINAL_[Model].json -> [ID]_REFINED_[Model].json
        refined_file = orig_file.replace("_ORIGINAL_", "_REFINED_")
        
        if refined_file in files:
            pairs.append({
                "id": base_id,
                "original": os.path.join(folder, orig_file),
                "refined": os.path.join(folder, refined_file)
            })
        else:
            print(f"[WARNING] Found Original for '{base_id}' but missing Refined version.")
            
    return pairs

def generate_report_text(interview_id, original, refined):
    """Generates the content of the comparison report."""
    
    # 1. Gather Metrics
    try:
        orig_start = original[0]['caption_indices'][0]
        ref_start = refined[0]['caption_indices'][0]
        orig_len_1 = len(original[0]['caption_indices'])
        ref_len_1 = len(refined[0]['caption_indices'])
        
        # Flatten lists for chatter check
        orig_flat = [idx for seg in original for idx in seg['caption_indices']]
        ref_flat = [idx for seg in refined for idx in seg['caption_indices']]
        
        orig_has_chatter = any(idx in orig_flat for idx in CHATTER_INDICES)
        ref_has_chatter = any(idx in ref_flat for idx in CHATTER_INDICES)
    except IndexError:
        return "Error: JSON structure seems empty or malformed."

    # 2. Build Report String
    lines = []
    lines.append("="*80)
    lines.append(f"COMPARISON REPORT: {interview_id}")
    lines.append(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("="*80 + "\n")
    
    lines.append("1. EXECUTIVE SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Original Segments: {len(original)}")
    lines.append(f"Refined Segments:  {len(refined)}")
    lines.append(f"Chatter Removal:   {'✅ SUCCESS' if (not ref_has_chatter and orig_has_chatter) else '⚠️ CHECK'}")
    lines.append(f"Intro Merging:     {'✅ SUCCESS' if ref_len_1 > orig_len_1 * 2 else '➖ NEUTRAL'}\n")

    lines.append("2. METRICS TABLE")
    lines.append("-" * 80)
    lines.append(f"{'METRIC':<30} | {'ORIGINAL':<20} | {'REFINED':<20} | {'DELTA'}")
    lines.append("-" * 80)
    lines.append(f"{'Start Index (Drift)':<30} | {orig_start:<20} | {ref_start:<20} | {'+'+str(ref_start-orig_start)}")
    lines.append(f"{'Seg 1 Length (Caps)':<30} | {orig_len_1:<20} | {ref_len_1:<20} | {'x'+str(round(ref_len_1/orig_len_1,1))}")
    lines.append(f"{'Avg Segment Length':<30} | {calculate_avg_len(original):<20} | {calculate_avg_len(refined):<20} | {'diff'}")
    lines.append("-" * 80 + "\n")

    lines.append("3. DEEP DIVE: FIRST 3 SEGMENTS")
    lines.append("-" * 80)
    
    for i in range(min(3, len(original), len(refined))):
        try:
            o_inds = str(original[i]['caption_indices'])
            if len(o_inds) > 50: o_inds = o_inds[:47] + "..."
            r_inds = str(refined[i]['caption_indices'])
            if len(r_inds) > 50: r_inds = r_inds[:47] + "..."
            
            lines.append(f"Segment {i+1}:")
            lines.append(f"  ORIG: {o_inds}")
            lines.append(f"  REF:  {r_inds}")
            lines.append("")
        except: pass

    return "\n".join(lines)

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    print(f"\nScanning folder: {os.path.abspath(json_folder)}")
    
    # 1. Find Pairs
    pairs = find_file_pairs(json_folder)
    
    if not pairs:
        print("[ERROR] No matching ORIGINAL/REFINED pairs found.")
        print("Ensure files are named like: [ID]_ORIGINAL_ChatGPT.json and [ID]_REFINED_ChatGPT.json")
    else:
        print(f"Found {len(pairs)} interview pairs to process.\n")
        print(f"{'INTERVIEW ID':<40} | {'STATUS':<20} | {'SAVED TO'}")
        print("-" * 90)

        # 2. Process Each Pair
        for pair in pairs:
            # Load
            orig_data = load_json(pair['original'])
            ref_data = load_json(pair['refined'])
            
            if orig_data and ref_data:
                # Generate Report
                report_content = generate_report_text(pair['id'], orig_data, ref_data)
                
                # Save Report
                filename = f"Comparison_Report_{pair['id']}.txt"
                save_path = os.path.join(report_folder, filename)
                
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(report_content)
                
                print(f"{pair['id']:<40} | ✅ Done             | {filename}")
            else:
                print(f"{pair['id']:<40} | ❌ JSON Error       | -")

    print("\n" + "="*90)
    print(f"All reports saved in: {os.path.abspath(report_folder)}")