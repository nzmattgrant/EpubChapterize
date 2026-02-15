import json
import os

file_path = '/Users/matthewgrant/Source/EpubChapterize/book_previews.json'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    if 'index' in item:
        item['chapter_index'] = item['index'] - 1
        del item['index']

with open(file_path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("Updated book_previews.json")
