import json
import pandas as pd
from collections import Counter
import re

# File Paths
ENRICHED_FILE = 'enriched_segments.json'
VALIDATIONS_FILE = 'segment_validations.json'

def load_data():
    """Loads the two consolidated JSON files."""
    try:
        with open(ENRICHED_FILE, 'r', encoding='utf-8') as f:
            enriched_data = json.load(f)
        with open(VALIDATIONS_FILE, 'r', encoding='utf-8') as f:
            validations_data = json.load(f)
        return enriched_data, validations_data
    except FileNotFoundError:
        print("Error: JSON files not found. Make sure enriched_segments.json and segment_validations.json are in the directory.")
        return None, None

def create_lookup_maps(enriched_data):
    """
    Creates a dictionary to look up segment metadata by segment_id.
    Structure: { 'segment_id': { segment_object } }
    """
    segment_map = {}
    for video in enriched_data:
        # Check if 'enriched_segments' is a list or a dict (handling potential variations)
        segments = video.get('enriched_segments', [])
        if isinstance(segments, dict): 
            segments = [segments]
            
        for seg in segments:
            if isinstance(seg, dict) and 'segment_id' in seg:
                segment_map[seg['segment_id']] = seg
    return segment_map

def analyze_validations(enriched_map, validations_data):
    """
    Analyzes validations against the original segments.
    Returns a DataFrame with analysis details for every validation.
    """
    rows = []

    for entry in validations_data:
        val = entry.get('segment_validation', {})
        seg_id = entry.get('segment_id')
        user_id = entry.get('user_id')
        
        # Get original segment metadata
        original_seg = enriched_map.get(seg_id, {})
        original_text = original_seg.get('text', "")
        
        # --- DETECT ISSUES ---
        issues = []
        
        # 1. Fragment Removal
        is_removed = val.get('remove_fragment', False)
        if is_removed:
            issues.append('FRAGMENT_REMOVED')

        # 2. Start Time Edit
        start_decision = val.get('start_time_validation', {}).get('decision')
        if start_decision == 'edit':
            issues.append('START_TIME_EDIT')

        # 3. Title Edit
        title_decision = val.get('title_validation', {}).get('decision')
        if title_decision == 'edit':
            issues.append('TITLE_EDIT')

        # 4. Concept Mismatch (Removed Concepts)
        removed_concepts = []
        added_concepts = [] # Comments might suggest additions, but structured data tracks removals
        if 'concept_validation' in val:
            for c in val['concept_validation']:
                if c.get('action') == 'remove':
                    issues.append('CONCEPT_REMOVED')
                    removed_concepts.append(c.get('uri'))
        
        # 5. Comment Analysis
        comment = val.get('comment', '')
        
        # --- DATA ROW ---
        rows.append({
            'segment_id': seg_id,
            'user_id': user_id,
            'issues': issues,
            'is_rejected': len(issues) > 0 or (len(comment) > 5), # Consider comment as a "soft" rejection or note
            'comment': comment,
            'removed_concepts': removed_concepts,
            'original_text': original_text,
            'original_start': original_seg.get('start'),
            'original_concepts': [c.get('name') for c in original_seg.get('matched_concepts', [])]
        })

    return pd.DataFrame(rows)

def print_hypothesis_report(df):
    """
    Prints a formatted report testing the specific hypotheses.
    """
    print("="*60)
    print(" AUTOMATED SEGMENTATION ANALYSIS REPORT")
    print("="*60)
    
    total = len(df)
    rejected = len(df[df['is_rejected']])
    print(f"\n[OVERALL STATS]")
    print(f"Total Validations: {total}")
    print(f"Non-Acceptance Rate: {rejected/total:.1%} ({rejected}/{total})")

    # --- HYPOTHESIS 1: META-CHATTER (START TIMES) ---
    print(f"\n[HYPOTHESIS 1] Meta-Chatter & Start Times")
    start_edits = df[df['issues'].apply(lambda x: 'START_TIME_EDIT' in x)]
    print(f"  - Start Time Edits: {len(start_edits)}")
    
    # Check for keywords in the *original text* of segments with start edits
    # Keywords: "naam", "geboren", "band loopt" (tape running)
    chatter_keywords = ['naam', 'geboren', 'band loopt', 'snuift', 'vraag']
    correlations = []
    for text in start_edits['original_text']:
        start_snippet = text[:100].lower() # Look at first 100 chars
        found = [k for k in chatter_keywords if k in start_snippet]
        if found:
            correlations.append(found)
            
    if len(correlations) > 0:
        print(f"  - EVIDENCE: {len(correlations)}/{len(start_edits)} start-edited segments contained intro chatter keywords in the first 100 characters.")
        print(f"    Keywords found: {chatter_keywords}")
    else:
        print("  - No direct text correlation found for start times.")

    # --- HYPOTHESIS 2: SPECIFICITY (CONCEPTS) ---
    print(f"\n[HYPOTHESIS 2] Specificity & Named Entities")
    concept_edits = df[df['issues'].apply(lambda x: 'CONCEPT_REMOVED' in x)]
    
    all_removed = [uri for sublist in concept_edits['removed_concepts'] for uri in sublist]
    print(f"  - Total Concepts Removed: {len(all_removed)}")
    
    if all_removed:
        # Check if users are asking for Missing Concepts in comments (e.g., looking for Capitalized words in comments)
        missing_entity_requests = []
        for comment in df['comment']:
            if comment:
                # Rough heuristic: Look for capitalized words that aren't at start of sentence
                potential_entities = re.findall(r'(?<!^)(?<!\. )\b[A-Z][a-z]+\b', comment)
                if potential_entities:
                    missing_entity_requests.extend(potential_entities)
        
        print(f"  - Top Removed URIs: {Counter(all_removed).most_common(3)}")
        if missing_entity_requests:
            print(f"  - Potential Missing Entities requested in comments: {set(missing_entity_requests)}")
            print("    -> Suggests users want specific locations/names added.")

    # --- HYPOTHESIS 3: BIOGRAPHICAL NOISE (REMOVALS) ---
    print(f"\n[HYPOTHESIS 3] Biographical Noise & Fragment Removal")
    removals = df[df['issues'].apply(lambda x: 'FRAGMENT_REMOVED' in x)]
    print(f"  - Fragments Removed: {len(removals)}")
    
    # Check comments for "intro" or "irrelevant"
    intro_keywords = ['introductie', 'intro', 'niets', 'inhoud']
    intro_hits = 0
    for comment in removals['comment']:
        if any(k in comment.lower() for k in intro_keywords):
            intro_hits += 1
            
    if removals.empty:
        print("  - No fragments were completely removed.")
    else:
        print(f"  - EVIDENCE: {intro_hits}/{len(removals)} removal comments mentioned 'intro' or lack of content.")
        print(f"    Sample Comments: {removals['comment'].unique().tolist()}")

    print("="*60)

if __name__ == "__main__":
    enriched, validations = load_data()
    if enriched and validations:
        segment_map = create_lookup_maps(enriched)
        df_results = analyze_validations(segment_map, validations)
        print_hypothesis_report(df_results)