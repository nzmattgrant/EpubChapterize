# EpubChapterize

EpubChapterize is a Python package designed to split EPUB files into chapters programmatically. It provides a simple interface to process EPUB files and extract their chapters for further use. Currently optimized for Project Gutenberg EPUB3s — if it doesn't work for your use case please get in touch.

## Installation

```bash
pip install epubchapterize
```

## Usage

```python
from epub_chapterize import chapterize

chapters, language, title, author, cover_image = chapterize("dracula.epub")

print(title)    # "Dracula"
print(author)   # "Bram Stoker"
print(language) # "en"

for chapter in chapters:
    print(chapter["title"])
    for sentence in chapter["sentences"]:
        print(sentence)
```

### Return values

| Value | Type | Description |
|---|---|---|
| `chapters` | `list[dict]` | List of chapter dicts, each with `"title"`, `"sentences"`, `"start_file"`, `"start_id"` and `"sentence_files"` keys |
| `language` | `str` | BCP 47 language code detected from the EPUB metadata (e.g. `"en"`, `"fr"`) |
| `title` | `str` | Book title from EPUB metadata |
| `author` | `str` | Author name from EPUB metadata |
| `cover_image` | `bytes \| None` | Raw bytes of the cover image, or `None` if not found |

A chapter starts in the file `"start_file"`, at the element whose id is `"start_id"`, which is where the table of contents links to (`None` when it links to the file itself). When headings in the same file with no text of their own lead into a chapter, like a part heading just before its first chapter, the chapter's title starts with theirs and the chapter starts where the first of them does. `"sentence_files"` lists the files its sentences are in, in order, each with the index in `"sentences"` of the first sentence there; the sentences up to the next entry's are in that file. Files are paths from the root of the EPUB written as URLs, which is how readers such as Readium name them.

### Example output

For the Standard Ebooks `dracula.epub` the returned `chapters` list looks like:

```python
[
    {"title": "Imprint", ...},
    {
        "title": "I",
        "sentences": [
            "Jonathan Harker’s Journal.",
            "(Kept in shorthand.)",
            "3 May.",
            ...
        ],
        "start_file": "epub/text/chapter-1.xhtml",
        "start_id": None,
        "sentence_files": [{"file": "epub/text/chapter-1.xhtml", "first_sentence": 0}]
    },
    {
        "title": "II",
        "sentences": [
            "Jonathan Harker’s Journal—continued",
            "5 May.—I must have been asleep, for certainly if I had been fully awake I must have noticed the approach of such a remarkable place.",
            ...
        ],
        "start_file": "epub/text/chapter-2.xhtml",
        "start_id": None,
        "sentence_files": [{"file": "epub/text/chapter-2.xhtml", "first_sentence": 0}]
    },
    ...
]
```

The `cover_image` bytes can be written straight to a file:

```python
if cover_image:
    with open("cover.jpg", "wb") as f:
        f.write(cover_image)
```

## Supported languages

Sentence segmentation is supported for English, French, German, Spanish, Italian, Dutch, and Portuguese via NLTK's Punkt tokenizer (installed automatically). No extra downloads are required unless you switch to the spaCy backend.

## Requirements

- Python 3.13 or higher

## License

MIT — see the LICENSE file for details.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests at [github.com/nzmattgrant/epubchapterize](https://github.com/nzmattgrant/epubchapterize).

## Author

Matthew Grant
