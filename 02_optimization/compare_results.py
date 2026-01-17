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

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def load_json(filepath):
    """Safely loads a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            # Handle case where JSON is wrapped in a dict key "segments"
            if isinstance(data, dict) and 'segments' in data:
                return data['segments']
            return data
    except Exception as e:
        print(f"[ERROR] Could not read {os.path.basename(filepath)}: {e}")
        return None

def calculate_avg_len(data):
    """Calculates average number of captions per segment."""
    if not data: return 0
    total = 0
    for seg in data:
        if 'caption_indices' in seg:
            total += len(seg['caption_indices'])
        elif 'start_index' in seg and 'end_index' in seg:
            total += (seg['end_index'] - seg['start_index'])
    return round(total / len(data), 1)

def find_file_pairs(folder):
    """Scans folder and pairs ORIGINAL files with REFINED files."""
    try:
        files = os.listdir(folder)
    except FileNotFoundError:
        print(f"[ERROR] JSON folder not found: {folder}")
        return []

    pairs = []

    # Filter for ORIGINAL files first
    originals = [f for f in files if "_ORIGINAL_" in f and f.endswith(".json")]
    
    for orig_file in originals:
        # Determine the Base ID (everything before _ORIGINAL)
        base_id = orig_file.split("_ORIGINAL_")[0]
        
        # Construct the expected Refined filename
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
    
    # 1. Gather Structural Metrics
    try:
        # Safely get start indices (Drift Check)
        orig_s1 = original[0]
        ref_s1 = refined[0]
        
        orig_start = orig_s1.get('start_index', orig_s1.get('caption_indices', [0])[0])
        ref_start = ref_s1.get('start_index', ref_s1.get('caption_indices', [0])[0])
        
        # Safely get lengths (Merge Check)
        if 'caption_indices' in orig_s1:
            orig_len_1 = len(orig_s1['caption_indices'])
            ref_len_1 = len(ref_s1['caption_indices'])
        else:
            orig_len_1 = orig_s1.get('end_index', 0) - orig_s1.get('start_index', 0)
            ref_len_1 = ref_s1.get('end_index', 0) - ref_s1.get('start_index', 0)

    except (IndexError, KeyError):
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
    
    # Status Checks
    # Drift: Did the start index move forward?
    drift_msg = '✅ SUCCESS' if ref_start > orig_start else '➖ NEUTRAL'
    if ref_start == orig_start and orig_start > 0: drift_msg = '⚠️ CHECK'
    
    # Merge: Did the first segment get significantly bigger (at least 50% bigger)?
    merge_msg = '✅ SUCCESS' if ref_len_1 > (orig_len_1 * 1.5) else '➖ NEUTRAL'
    
    lines.append(f"Chatter Removal:   {drift_msg}")
    lines.append(f"Intro Merging:     {merge_msg}")
    lines.append("")

    lines.append("2. METRICS TABLE")
    lines.append("-" * 80)
    lines.append(f"{'METRIC':<30} | {'ORIGINAL':<20} | {'REFINED':<20} | {'DELTA'}")
    lines.append("-" * 80)
    
    # Structural Rows
    lines.append(f"{'Start Index (Drift)':<30} | {orig_start:<20} | {ref_start:<20} | {'+'+str(ref_start-orig_start)}")
    lines.append(f"{'Seg 1 Length (Caps)':<30} | {orig_len_1:<20} | {ref_len_1:<20} | {'x'+str(round(ref_len_1/orig_len_1 if orig_len_1>0 else 1, 1))}")
    lines.append(f"{'Avg Segment Length':<30} | {calculate_avg_len(original):<20} | {calculate_avg_len(refined):<20} | {'diff'}")
    lines.append("-" * 80 + "\n")

    lines.append("3. DEEP DIVE: FIRST 3 SEGMENTS (INDICES)")
    lines.append("-" * 80)
    
    for i in range(min(3, len(original), len(refined))):
        try:
            # Format indices string to avoid clutter
            o_inds = str(original[i].get('caption_indices', '[]'))
            if len(o_inds) > 50: o_inds = o_inds[:47] + "..."
            
            r_inds = str(refined[i].get('caption_indices', '[]'))
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