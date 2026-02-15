import json
import os
import re

OUTPUT_DIR = "epub_chapterize/output"

def normalize_text(text):
    return " ".join(text.split())

def find_sentence_index_in_file(file_path, target_sentence):
    if not os.path.exists(file_path):
        return -1
        
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Matches logic in extract_previews.py for splitting blocks
        pattern = re.compile(r'<start>\s*(.*?)\s*<end>', re.DOTALL)
        matches = pattern.findall(content)
        
        target_clean = normalize_text(target_sentence)
        
        for i, text in enumerate(matches):
            if target_clean in normalize_text(text):
                return i
                
        return -1
    except Exception:
        return -1

def update_json_with_sentence_indices():
    json_path = 'book_previews.json'
    if not os.path.exists(json_path):
        print(f"{json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    updated_count = 0
    
    for entry in data:
        title = entry.get('title')
        chapter = entry.get('chapter')
        sentence = entry.get('sentence')
        
        # If we already have a valid sentence index, skip (unless we want to verify)
        # But user says output only has chapter index currently.
        
        if not title or not chapter or not sentence:
            continue
            
        # Construct path to the text file
        # OUTPUT_DIR / Title / Chapter
        file_path = os.path.join(OUTPUT_DIR, title, chapter)
        
        sentence_index = find_sentence_index_in_file(file_path, sentence)
        
        entry['sentence_index'] = sentence_index
        updated_count += 1
        
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Updated {updated_count} entries with sentence indices in {json_path}")

if __name__ == "__main__":
    update_json_with_sentence_indices()
