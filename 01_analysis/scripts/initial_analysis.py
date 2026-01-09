import json
import os
import pandas as pd
from collections import Counter
import glob

# ==========================================
# CONFIGURATION
# ==========================================
# Update these paths to match your actual folder structure
ENRICHED_SEGMENTS_DIR = 'enriched_segments'
VALIDATIONS_DIR = 'validations'

# ==========================================
# STEP 1 & 2: DATA LOADING
# ==========================================

def load_enriched_segments(directory):
    """
    Loads enriched segment metadata into a hashmap keyed by segment_id.
    """
    enriched_map = {}
    file_pattern = os.path.join(directory, '*.json')
    files = glob.glob(file_pattern)
    
    print(f"Loading {len(files)} enriched segment files...")
    
    for filepath in files:
        filename = os.path.basename(filepath)
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                segments = json.load(f)
                # Handle case where file contains a single object instead of list
                if isinstance(segments, dict):
                    segments = [segments]
                    
                for seg in segments:
                    if 'segment_id' in seg:
                        # Add source filename to metadata
                        seg['source_filename'] = filename
                        enriched_map[seg['segment_id']] = seg
            except json.JSONDecodeError:
                print(f"Error decoding JSON: {filename}")
                
    return enriched_map

def load_validations(directory):
    """
    Loads validations into a hashmap keyed by segment_id.
    Value is a list of validations (since multiple users might validate one segment).
    """
    validation_map = {}
    file_pattern = os.path.join(directory, '*.json')
    files = glob.glob(file_pattern)
    
    print(f"Loading {len(files)} validation files...")
    
    for filepath in files:
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                val = json.load(f)
                seg_id = val.get('segment_id')
                
                if seg_id:
                    if seg_id not in validation_map:
                        validation_map[seg_id] = []
                    validation_map[seg_id].append(val)
            except json.JSONDecodeError:
                print(f"Error decoding JSON: {filepath}")
                
    return validation_map

# ==========================================
# STEP 3: DATA CLEANUP (FILTERING)
# ==========================================

def is_validation_clean(val):
    """
    Returns True if the validation is a perfect 'approve' 
    (no edits, no removals, no removed concepts, no comments).
    """
    # Check simple fields
    if val.get('remove_fragment') is True:
        return False
    if val.get('title_validation', {}).get('decision') != 'approve':
        return False
    if val.get('start_time_validation', {}).get('decision') != 'approve':
        return False
    if val.get('end_time_validation', {}).get('decision') != 'approve':
        return False
        
    # Check concepts
    if 'concept_validation' in val:
        for concept in val['concept_validation']:
            if concept.get('action') != 'keep':
                return False
                
    # Check comments (ignore empty strings)
    comment = val.get('comment', '')
    if comment and str(comment).strip():
        return False
        
    return True

# ==========================================
# STEP 4: ANALYSIS
# ==========================================

def analyze_discrepancies(enriched_map, validation_map):
    """
    Analyzes validations that are NOT clean to develop hypotheses.
    """
    data_rows = []
    
    # Iterate through all segments that have validations
    for seg_id, validations in validation_map.items():
        segment_meta = enriched_map.get(seg_id)
        
        if not segment_meta:
            continue # Skip if we don't have the original metadata
            
        for val in validations:
            # Step 3 Filter: Skip clean validations
            if is_validation_clean(val):
                continue
                
            # Categorize the "Non-Acceptance" Reason
            issues = []
            if val.get('remove_fragment'):
                issues.append('FRAGMENT_REMOVED')
            if val.get('title_validation', {}).get('decision') == 'edit':
                issues.append('TITLE_EDIT')
            if val.get('start_time_validation', {}).get('decision') == 'edit':
                issues.append('START_TIME_EDIT')
            if val.get('end_time_validation', {}).get('decision') == 'edit':
                issues.append('END_TIME_EDIT')
            
            removed_concepts = []
            if 'concept_validation' in val:
                for c in val['concept_validation']:
                    if c.get('action') == 'remove':
                        issues.append('CONCEPT_REMOVED')
                        removed_concepts.append(c.get('uri', 'unknown'))

            # Compile row for DataFrame
            data_rows.append({
                'segment_id': seg_id,
                'user_id': val.get('user_id'),
                'issues': issues,
                'comment': val.get('comment', ''),
                'segment_text_len': len(segment_meta.get('text', '')),
                'segment_duration': segment_meta.get('end', 0) - segment_meta.get('start', 0),
                'removed_concepts': removed_concepts,
                'original_text': segment_meta.get('text', '')[:100] + "..." # Snippet
            })

    return pd.DataFrame(data_rows)

def generate_hypotheses_report(df):
    """
    Prints a report based on the analyzed data.
    """
    if df.empty:
        print("No non-accepted validations found.")
        return

    print("\n" + "="*40)
    print(" ANALYSIS OF SEGMENT REJECTIONS/EDITS")
    print("="*40)
    
    # 1. Frequency of Issues
    all_issues = [issue for sublist in df['issues'] for issue in sublist]
    issue_counts = Counter(all_issues)
    
    print("\n[DATA] Frequency of Edit Types:")
    for issue, count in issue_counts.items():
        print(f"  - {issue}: {count}")

    # 2. Concept Removal Analysis
    print("\n[HYPOTHESIS 1] Concept Relevance")
    print("Are specific types of concepts being removed consistently?")
    all_removed_concepts = [uri for sublist in df['removed_concepts'] for uri in sublist]
    if all_removed_concepts:
        print(f"  Total concepts removed: {len(all_removed_concepts)}")
        print(f"  Top removed URIs: {Counter(all_removed_concepts).most_common(3)}")
    else:
        print("  No concepts were removed in this dataset.")

    # 3. Start Time Analysis
    start_time_edits = df[df['issues'].apply(lambda x: 'START_TIME_EDIT' in x)]
    if not start_time_edits.empty:
        print("\n[HYPOTHESIS 2] Temporal Precision")
        print(f"  {len(start_time_edits)} segments required start time adjustments.")
        print("  Common comments on start time edits:")
        print(start_time_edits['comment'].head(3).to_string(index=False))
        print("  -> Hypothesis: Original segmentation may include pre-interview 'chatter' or silence.")

    # 4. Fragment Removal Analysis
    fragment_removals = df[df['issues'].apply(lambda x: 'FRAGMENT_REMOVED' in x)]
    if not fragment_removals.empty:
        print("\n[HYPOTHESIS 3] Content Value")
        print(f"  {len(fragment_removals)} segments were completely removed.")
        print("  Comments associated with removal:")
        print(fragment_removals['comment'].unique())
        print("  -> Hypothesis: 'Introductory' or 'Setup' segments are viewed as low value.")

    # 5. Comment Sentiment/Keywords
    print("\n[QUALITATIVE] Comment Keyword Scan")
    comments = df['comment'].dropna().str.lower().tolist()
    keywords = ['intro', 'niet relevant', 'onbelangrijk', 'dubbel', 'fout']
    print(f"  Scanning {len(comments)} comments for keywords: {keywords}")
    for k in keywords:
        count = sum(1 for c in comments if k in c)
        if count > 0:
            print(f"  - '{k}' appeared {count} times")

# ==========================================
# EXECUTION
# ==========================================

if __name__ == "__main__":
    # 1. Load
    enriched_data = load_enriched_segments(ENRICHED_SEGMENTS_DIR)
    validation_data = load_validations(VALIDATIONS_DIR)
    
    # 2. Analyze
    if enriched_data and validation_data:
        df_analysis = analyze_discrepancies(enriched_data, validation_data)
        
        # 3. Report
        generate_hypotheses_report(df_analysis)
    else:
        print("Data loading failed or folders are empty.")