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
| `chapters` | `list[dict]` | List of chapter dicts, each with `"title"` and `"sentences"` keys |
| `language` | `str` | BCP 47 language code detected from the EPUB metadata (e.g. `"en"`, `"fr"`) |
| `title` | `str` | Book title from EPUB metadata |
| `author` | `str` | Author name from EPUB metadata |
| `cover_image` | `bytes \| None` | Raw bytes of the cover image, or `None` if not found |

### Example output

For `dracula.epub` the returned `chapters` list looks like:

```python
[
    {
        "title": "Jonathan Harker's Journal",
        "sentences": [
            "3 May. Bistritz.—Left Munich at 8:35 P. M., on 1st May, arriving at Vienna early next morning; should have arrived at 6:46, but train was an hour late.",
            "Buda-Pesth seems a wonderful place, from the glimpse which I got of it from the train and the little I could walk through the streets.",
            "I feared to go very far from the station, as we had arrived late and would start as near the correct time as possible.",
            "The impression I had was that we were leaving the West and entering the East; the most western of splendid bridges over the Danube, which is here of noble width and depth, took us among the traditions of Turkish rule."
        ]
    },
    {
        "title": "Jonathan Harker's Journal (Continued)",
        "sentences": [
            "5 May.—I must have been asleep, for certainly if I had been fully awake I must have noticed the approach of such a remarkable place.",
            "In the gloom the courtyard looked of considerable size, and as several dark ways led from it under great round arches, it perhaps seemed bigger than it really is.",
            ...
        ]
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
