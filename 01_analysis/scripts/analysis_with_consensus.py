import json
import os
import pandas as pd
from collections import Counter
import glob

# ==========================================
# CONFIGURATION
# ==========================================
ENRICHED_SEGMENTS_DIR = 'enriched_segments'
VALIDATIONS_DIR = 'validations'

# QUORUM SETTINGS
# Percentage of users that must agree to form a consensus (e.g., 0.6 = 60%)
CONSENSUS_THRESHOLD = 0.6 

# ==========================================
# STEP 1: DATA LOADING
# ==========================================

def load_data_maps(enriched_dir, val_dir):
    """
    Loads enriched segments and validations into dictionaries.
    Returns (enriched_map, validation_map)
    """
    enriched_map = {}
    validation_map = {}
    
    # Load Enriched Segments
    enriched_files = glob.glob(os.path.join(enriched_dir, '*.json'))
    print(f"Loading {len(enriched_files)} enriched segment files...")
    for filepath in enriched_files:
        filename = os.path.basename(filepath)
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                segments = data if isinstance(data, list) else [data]
                for seg in segments:
                    if 'segment_id' in seg:
                        seg['source_file'] = filename
                        enriched_map[seg['segment_id']] = seg
        except Exception as e:
            print(f"Skipping {filename}: {e}")

    # Load Validations
    val_files = glob.glob(os.path.join(val_dir, '*.json'))
    print(f"Loading {len(val_files)} validation files...")
    for filepath in val_files:
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                val = json.load(f)
                seg_id = val.get('segment_id')
                if seg_id:
                    if seg_id not in validation_map:
                        validation_map[seg_id] = []
                    validation_map[seg_id].append(val)
        except Exception as e:
            print(f"Skipping validation {filepath}: {e}")
            
    return enriched_map, validation_map

# ==========================================
# STEP 2: QUORUM MECHANISM
# ==========================================

def is_clean_validation(val):
    """Checks if a single validation is a perfect 'Approve'."""
    # Logic: No removal, 'approve' on time/title, no concept removals
    if val.get('remove_fragment') is True: return False
    if val.get('title_validation', {}).get('decision') != 'approve': return False
    if val.get('start_time_validation', {}).get('decision') != 'approve': return False
    if val.get('end_time_validation', {}).get('decision') != 'approve': return False
    
    # Check concept removals
    if 'concept_validation' in val:
        if any(c.get('action') != 'keep' for c in val['concept_validation']): 
            return False
            
    return True

def determine_consensus(validations):
    """
    Analyzes a list of validations for a single segment to determine group consensus.
    """
    total = len(validations)
    if total == 0:
        return {'status': 'NO_DATA', 'issues': [], 'comments': []}

    # Count votes
    clean_votes = sum(1 for v in validations if is_clean_validation(v))
    reject_votes = total - clean_votes
    
    clean_ratio = clean_votes / total
    reject_ratio = reject_votes / total
    
    # Collect all issues and comments for analysis regardless of consensus
    all_issues = []
    all_comments = []
    
    for v in validations:
        if v.get('comment'):
            all_comments.append(v['comment'])
        
        if not is_clean_validation(v):
            if v.get('remove_fragment'): all_issues.append('REMOVE_FRAGMENT')
            if v.get('title_validation', {}).get('decision') == 'edit': all_issues.append('EDIT_TITLE')
            if v.get('start_time_validation', {}).get('decision') == 'edit': all_issues.append('EDIT_START')
            if v.get('end_time_validation', {}).get('decision') == 'edit': all_issues.append('EDIT_END')
            if any(c.get('action') == 'remove' for c in v.get('concept_validation', [])):
                all_issues.append('REMOVE_CONCEPT')

    # Determine Status
    if clean_ratio >= CONSENSUS_THRESHOLD:
        status = 'ACCEPTED'
    elif reject_ratio >= CONSENSUS_THRESHOLD:
        status = 'REJECTED'
    else:
        status = 'CONFLICT' # Users disagree (e.g., 50/50 split)

    return {
        'status': status,
        'vote_split': f"{clean_votes} vs {reject_votes}",
        'total_votes': total,
        'dominant_issues': [k for k, v in Counter(all_issues).items() if v >= (reject_votes * 0.5)], # Issues raised by majority of dissenters
        'all_issues': all_issues,
        'comments': all_comments
    }

# ==========================================
# STEP 3: ANALYSIS
# ==========================================

def analyze_dataset(enriched_map, validation_map):
    rows = []
    
    for seg_id, validations in validation_map.items():
        meta = enriched_map.get(seg_id, {})
        consensus = determine_consensus(validations)
        
        rows.append({
            'segment_id': seg_id,
            'source_file': meta.get('source_file', 'unknown'),
            'consensus_status': consensus['status'],
            'vote_split': consensus['vote_split'],
            'dominant_issues': ", ".join(consensus['dominant_issues']),
            'comment_text': " | ".join(consensus['comments']),
            'start_time': meta.get('start'),
            'text_snippet': meta.get('text', '')[:50]
        })
        
    return pd.DataFrame(rows)

def generate_hypothesis_report(df):
    print("\n" + "="*50)
    print(" CROWD CONSENSUS ANALYSIS REPORT")
    print("="*50)
    
    # 1. High-Level Stats
    status_counts = df['consensus_status'].value_counts()
    print("\n[Segment Status Distribution]")
    print(status_counts.to_string())
    
    # 2. Deep Dive: REJECTED Segments (High Confidence Errors)
    rejected_df = df[df['consensus_status'] == 'REJECTED'].copy()
    
    if not rejected_df.empty:
        print("\n" + "-"*30)
        print(" ANALYSIS OF REJECTED SEGMENTS (Consensus > {:.0%})".format(CONSENSUS_THRESHOLD))
        print("-"*30)
        
        # Analyze why they were rejected
        all_reasons = []
        for issues in rejected_df['dominant_issues']:
            if issues: all_reasons.extend(issues.split(", "))
            
        print("\n[Primary Reasons for Rejection]")
        if all_reasons:
            for reason, count in Counter(all_reasons).most_common():
                print(f"  - {reason}: {count} segments")
        else:
            print("  (Rejections were miscellaneous, no dominant technical reason)")

        # Correlate specific reasons with comments
        print("\n[Hypothesis Development - Evidence]")
        
        # Case A: Fragment Removal
        removals = rejected_df[rejected_df['dominant_issues'].str.contains('REMOVE_FRAGMENT', na=False)]
        if not removals.empty:
            print(f"\n> HYPOTHESIS: Why are segments being removed? ({len(removals)} cases)")
            print(f"  Sample Comments: {removals['comment_text'].head(3).tolist()}")
        
        # Case B: Start Time Edits
        starts = rejected_df[rejected_df['dominant_issues'].str.contains('EDIT_START', na=False)]
        if not starts.empty:
            print(f"\n> HYPOTHESIS: Why are start times being edited? ({len(starts)} cases)")
            print(f"  Sample Comments: {starts['comment_text'].head(3).tolist()}")
            
    # 3. Deep Dive: CONFLICT Segments (Ambiguity)
    conflict_df = df[df['consensus_status'] == 'CONFLICT']
    if not conflict_df.empty:
        print("\n" + "-"*30)
        print(f" ANALYSIS OF CONFLICT SEGMENTS ({len(conflict_df)} cases)")
        print("-"*30)
        print("Users disagreed on these segments. This often indicates subjective boundaries.")
        print("Sample Conflict Comments:")
        print(conflict_df['comment_text'].head(3).tolist())

if __name__ == "__main__":
    if os.path.exists(ENRICHED_SEGMENTS_DIR) and os.path.exists(VALIDATIONS_DIR):
        enriched, validations = load_data_maps(ENRICHED_SEGMENTS_DIR, VALIDATIONS_DIR)
        df = analyze_dataset(enriched, validations)
        generate_hypothesis_report(df)
    else:
        print("Directories not found. Please check paths.")