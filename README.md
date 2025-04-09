# EpubChapterize
### A tool to split out chapters from ePub documents. Initially just for Project Gutenberg ePub3s.

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

## Notes

- The tool is not perfect and may require manual adjustments to the output.
- It is currently a standalone script but may be packaged in the future.
- Feel free to fork the repository and modify it as needed.

## Contributing

If you encounter any issues, please raise a ticket in the repository. Contributions are welcome!