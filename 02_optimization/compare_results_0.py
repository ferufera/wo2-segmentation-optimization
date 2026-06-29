import json
import os
import datetime

# ==============================================================================
# CONFIGURATION
# ==============================================================================
current_dir = os.path.dirname(os.path.abspath(__file__))
json_folder = os.path.join(current_dir, '..', 'results', 'json_outputs')
report_folder = os.path.join(current_dir, '..', 'results', 'analysis_reports')

# Ensure report folder exists
os.makedirs(report_folder, exist_ok=True)

# Define Files
ORIGINAL_FILE = os.path.join(json_folder, "07_JKKV_Schelvis_ORIGINAL_ChatGPT.json")
REFINED_FILE  = os.path.join(json_folder, "07_JKKV_Schelvis_REFINED_ChatGPT.json")

# Report Filename (Automatic)
REPORT_FILE = os.path.join(report_folder, "Comparison_Report_Schelvis.txt")

CHATTER_INDICES = [0, 1] 

# ==============================================================================
# HELPER FUNCTIONS
# ==============================================================================
def load_json(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        return None

def calculate_avg_len(data):
    """Calculates average number of captions per segment."""
    total_caps = sum([len(seg['caption_indices']) for seg in data])
    return round(total_caps / len(data), 1)

def generate_report_text(original, refined):
    """Generates a detailed text report string."""
    
    # 1. Gather Stats
    orig_start = original[0]['caption_indices'][0]
    ref_start = refined[0]['caption_indices'][0]
    
    orig_len_1 = len(original[0]['caption_indices'])
    ref_len_1 = len(refined[0]['caption_indices'])
    
    # Chatter Logic
    orig_flat = [idx for seg in original for idx in seg['caption_indices']]
    ref_flat = [idx for seg in refined for idx in seg['caption_indices']]
    orig_has_chatter = any(idx in orig_flat for idx in CHATTER_INDICES)
    ref_has_chatter = any(idx in ref_flat for idx in CHATTER_INDICES)
    
    # Build the Report String
    lines = []
    lines.append("================================================================================")
    lines.append(f"A/B TEST REPORT: SEGMENTATION OPTIMIZATION")
    lines.append(f"Date: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("================================================================================\n")
    
    lines.append("1. EXECUTIVE SUMMARY")
    lines.append("-" * 40)
    lines.append(f"Original Segments: {len(original)}")
    lines.append(f"Refined Segments:  {len(refined)}")
    lines.append(f"Chatter Removal:   {'✅ SUCCESS' if not ref_has_chatter else '❌ FAILED'}")
    lines.append(f"Intro Merging:     {'✅ SUCCESS' if ref_len_1 > orig_len_1 * 2 else '❌ FAILED'}\n")

    lines.append("2. DETAILED METRICS COMPARISON")
    lines.append("-" * 80)
    lines.append(f"{'METRIC':<30} | {'ORIGINAL':<20} | {'REFINED':<20} | {'DIFF'}")
    lines.append("-" * 80)
    lines.append(f"{'Start Index (Drift)':<30} | {orig_start:<20} | {ref_start:<20} | {'+'+str(ref_start-orig_start) if ref_start>orig_start else '0'}")
    lines.append(f"{'Seg 1 Length (Captions)':<30} | {orig_len_1:<20} | {ref_len_1:<20} | {'x'+str(round(ref_len_1/orig_len_1,1))}")
    lines.append(f"{'Avg Segment Length':<30} | {calculate_avg_len(original):<20} | {calculate_avg_len(refined):<20} | {'Higher is richer'}")
    lines.append(f"{'Chatter Indices [0,1]':<30} | {'Present' if orig_has_chatter else 'Absent':<20} | {'Present' if ref_has_chatter else 'Absent':<20} | {'Fixed' if not ref_has_chatter else '-'}")
    lines.append("-" * 80 + "\n")

    lines.append("3. DEEP DIVE: THE FIRST 3 SEGMENTS")
    lines.append("(Visualizing how the Refined Prompt merged the content)")
    lines.append("-" * 80)
    
    # Compare first 3 segments side-by-side
    for i in range(3):
        # Original
        try:
            o_inds = str(original[i]['caption_indices'])
            if len(o_inds) > 30: o_inds = o_inds[:27] + "..."
        except: o_inds = "N/A"
        
        # Refined
        try:
            r_inds = str(refined[i]['caption_indices'])
            if len(r_inds) > 30: r_inds = r_inds[:27] + "..."
        except: r_inds = "N/A"

        lines.append(f"Segment {i+1}:")
        lines.append(f"  ORIGINAL: {o_inds}")
        lines.append(f"  REFINED:  {r_inds}")
        lines.append("")

    lines.append("================================================================================")
    lines.append("CONCLUSION:")
    if not ref_has_chatter and ref_start > orig_start:
        lines.append("The Refined prompt successfully eliminated technical chatter/noise.")
    if ref_len_1 > orig_len_1:
        lines.append("The Refined prompt successfully merged the biographical intro with the first story.")
    lines.append("================================================================================")

    return "\n".join(lines)

# ==============================================================================
# MAIN EXECUTION
# ==============================================================================
if __name__ == "__main__":
    print("Loading Data...")
    original = load_json(ORIGINAL_FILE)
    refined = load_json(REFINED_FILE)

    if original and refined:
        # Generate the text
        report = generate_report_text(original, refined)
        
        # 1. Print to Terminal
        print(report)
        
        # 2. Save to File
        with open(REPORT_FILE, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n[SAVED] Report saved to: {os.path.abspath(REPORT_FILE)}")
    else:
        print("[ERROR] Could not load JSON files.")