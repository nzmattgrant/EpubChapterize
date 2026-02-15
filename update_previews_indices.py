import json
import re
import os

def update_json():
    json_path = 'book_previews.json'
    if not os.path.exists(json_path):
        print(f"{json_path} not found.")
        return

    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    new_data = []
    for entry in data:
        chapter_filename = entry.get('chapter', '')
        # Regex to extract index from "1 - Title.txt"
        # The filename in JSON is usually like "1 - I: Down the Rabbit-Hole.txt"
        match = re.match(r'^(\d+)\s*-\s*(.*)', chapter_filename)
        index = -1
        if match:
            index = int(match.group(1))
        
        # Handle excerpt format
        excerpt = entry.get('excerpt')
        sentence = ""
        if isinstance(excerpt, list) and len(excerpt) > 0:
            sentence = excerpt[0]
        elif isinstance(excerpt, str):
            sentence = excerpt
            
        new_entry = {
            "title": entry.get('title'),
            "author": entry.get('author'),
            "chapter": chapter_filename,
            "index": index,
            "sentence": sentence
        }
        new_data.append(new_entry)
        
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(new_data, f, indent=2, ensure_ascii=False)
    print(f"Updated {len(new_data)} entries in {json_path}")

if __name__ == "__main__":
    update_json()
