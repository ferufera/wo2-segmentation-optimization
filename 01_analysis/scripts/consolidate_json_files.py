import json
import os
import glob

# ==========================================
# CONFIGURATION
# ==========================================
ENRICHED_DIR = 'enriched_segments'
VALIDATIONS_DIR = 'validations'

OUTPUT_ENRICHED_FILE = 'enriched_segments.json'
OUTPUT_VALIDATIONS_FILE = 'segment_validations.json'

def process_enriched_segments():
    """
    Reads all enriched segment files and consolidates them.
    Video name is derived by removing '.nl_enriched_segments.json' from the filename.
    """
    master_list = []
    
    # Check if directory exists
    if not os.path.exists(ENRICHED_DIR):
        print(f"Directory not found: {ENRICHED_DIR}")
        return

    files = glob.glob(os.path.join(ENRICHED_DIR, '*.json'))
    print(f"Processing {len(files)} enriched segment files...")

    for filepath in files:
        filename = os.path.basename(filepath)
        
        # Derive video_name
        # Assumption: files end in .nl_enriched_segments.json based on description
        # If the suffix varies, we might need a more robust split, e.g., filename.split('.nl_')[0]
        if filename.endswith('.nl_enriched_segments.json'):
            video_name = filename.replace('.nl_enriched_segments.json', '')
        else:
            # Fallback: remove just .json
            video_name = filename.replace('.json', '')
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
            master_list.append({
                "video_name": video_name,
                "enriched_segments": content
            })
        except json.JSONDecodeError:
            print(f"Error decoding JSON in file: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

    # Write to output file
    with open(OUTPUT_ENRICHED_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_list, f, indent=2, ensure_ascii=False)
    
    print(f"Successfully wrote {len(master_list)} entries to {OUTPUT_ENRICHED_FILE}")


def process_validations():
    """
    Reads all validation files and consolidates them.
    Segment_id and User_id are derived by splitting the filename at the last underscore.
    """
    master_list = []
    
    # Check if directory exists
    if not os.path.exists(VALIDATIONS_DIR):
        print(f"Directory not found: {VALIDATIONS_DIR}")
        return

    files = glob.glob(os.path.join(VALIDATIONS_DIR, '*.json'))
    print(f"Processing {len(files)} validation files...")

    for filepath in files:
        filename = os.path.basename(filepath)
        
        # Remove extension
        name_without_ext = os.path.splitext(filename)[0]
        
        # Derive segment_id and user_id
        # Assumption: Format is <segment_id>_<user_id>.json
        # We split from the right once to separate the user hash from the segment ID
        try:
            segment_id, user_id = name_without_ext.rsplit('_', 1)
            
            with open(filepath, 'r', encoding='utf-8') as f:
                content = json.load(f)
                
            master_list.append({
                "segment_id": segment_id,
                "user_id": user_id,
                "segment_validation": content
            })
            
        except ValueError:
            print(f"Skipping file {filename}: Could not parse segment_id and user_id (expected format segment_user.json)")
        except json.JSONDecodeError:
            print(f"Error decoding JSON in file: {filename}")
        except Exception as e:
            print(f"Error processing {filename}: {str(e)}")

    # Write to output file
    with open(OUTPUT_VALIDATIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_list, f, indent=2, ensure_ascii=False)

    print(f"Successfully wrote {len(master_list)} entries to {OUTPUT_VALIDATIONS_FILE}")

if __name__ == "__main__":
    process_enriched_segments()
    print("-" * 30)
    process_validations()