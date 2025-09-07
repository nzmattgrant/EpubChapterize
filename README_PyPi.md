# EpubChapterize

EpubChapterize is a Python package designed to help you split EPUB files into chapters programmatically. It provides a simple interface to process EPUB files and extract their chapters for further use. At the moment this is optimized for Project Gutenberg Epub3s and may not work with other types of Epubs. If it doesn't work then please get in touch with your use case.

## Installation

Install the package using pip:

```bash
pip install epubchapterize
```

## Usage

Here is an example of how to use EpubChapterize:

```python
import epub_chapterize
import os
file_path = os.path.join(os.getcwd(), "Alice-In-Wonderland.epub")
chapters, language, title, author, cover_image = epub_chapterize.chapterize(file_path)
```
### Explanation

1. Import the `epub_chapterize` module.
2. Specify the path to your EPUB file.
3. Use the `chapterize` function to process the file and extract its chapters.

## Requirements

- Python 3.13 or higher
- `epub_chapterize` package installed via pip

## License

This project is licensed under the MIT License. See the LICENSE file for details.

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests to improve the package.

## Author

Matthew Grant  