# EpubChapterize
### A tool to split out chapters from ePub documents. Initially just for Project Gutenberg ePub3s.

[![PyPI version](https://img.shields.io/pypi/v/epubchapterize.svg)](https://pypi.org/project/epubchapterize/)

## Setup

To set up the project, follow these steps:

1. Clone the repository:
    ```bash
    git clone https://github.com/yourusername/EpubChapterize.git
    cd EpubChapterize
    ```

2. Create a virtual environment:
    ```bash
    python -m venv venv
    ```

3. Activate the virtual environment:
    - On macOS/Linux:
      ```bash
      source venv/bin/activate
      ```
    - On Windows:
      ```bash
      venv\Scripts\activate
      ```

4. Install the required dependencies:
    ```bash
    pip install -r requirements.txt
    ```
5. Install additional language models for spaCy (if needed):

    Depending on the languages you plan to process, you may need to install specific spaCy language models. Use the following commands to install them:

    - For English:
        ```bash
        python -m spacy download en_core_web_trf
        ```
    - For German:
        ```bash
        python -m spacy download de_dep_news_trf
        ```
    - For Italian:
        ```bash
        python -m spacy download it_core_news_trf
        ```
    - For Spanish:
        ```bash
        python -m spacy download es_dep_news_trf
        ```
    - For French:
        ```bash
        python -m spacy download fr_dep_news_trf
        ```

    If you are not using spacy then skip this step

## Usage

This tool is primarily designed to extract chapters from Project Gutenberg ePub3 files. It works by analyzing the navigation structure, matching headers, and attempting to identify chapter divisions. Note that it may also include some preamble content, and its accuracy is not guaranteed.

To use the tool, run:
```bash
python chapterize.py /path/to/your/epub/files/ 
```
or 
```bash
python chapterize.py 
```
which will use the books directory by default

## Example Output

For an input like `bram-stoker_dracula.epub`, the tool creates a folder structure:

```
output/
└── Dracula/
    ├── cover.jpg
    ├── 1 - Jonathan Harker's Journal.txt
    ├── 2 - Jonathan Harker's Journal (Continued).txt
    ├── 3 - Jonathan Harker's Journal (Continued).txt
    ├── ...
    └── 27 - Note left by Van Helsing.txt
```

Each chapter file looks like:

```
Jonathan Harker's Journal

<start> 3 May. Bistritz.—Left Munich at 8:35 P. M., on 1st May, arriving at Vienna early next morning; should have arrived at 6:46, but train was an hour late. <end>
<start> Buda-Pesth seems a wonderful place, from the glimpse which I got of it from the train and the little I could walk through the streets. <end>
<start> I feared to go very far from the station, as we had arrived late and would start as near the correct time as possible. <end>
<start> The impression I had was that we were leaving the West and entering the East; the most western of splendid bridges over the Danube, which is here of noble width and depth, took us among the traditions of Turkish rule. <end>
```

Books processed across multiple languages are placed in the same output directory. Any books that could not be parsed are listed in `books/to_import/unable_to_parse.txt`.

## Notes

- The tool is not perfect and may require manual adjustments to the output.
- It is currently a standalone script but may be packaged in the future.
- Feel free to fork the repository and modify it as needed.

## Contributing

If you encounter any issues, please raise a ticket in the repository. Contributions are welcome!