2026.10.20 - v0.3.2

- Subtitles inside a heading group, like "Loomings" in `<hgroup><h2>I</h2><p>Loomings</p></hgroup>`, are part of the heading, so they no longer repeat the chapter title as its first sentence. Title pages and part headings that only held a subtitle are no longer chapters

2026.10.19 - v0.3.1

- Fixed the `epub-chapterize` command, which pointed at a function that didn't exist. `epub-chapterize book.epub` (or a folder of EPUBs) now writes each book's cover and one numbered text file per chapter to output/<book title>/

2026.10.19 - v0.3.0

- Fixed chapters running on to the end of their file, which repeated every later chapter's text (some books came out several times longer than they are)
- Chapters now continue into the next file, so text at the start of a new file is no longer lost (about 5% more text across the test books)
- Chapters are matched to the table of contents by where its links point, instead of by comparing heading HTML, fixing missing, misplaced and repeated chapters and titles like "II II II II"
- Headings at every level (h1 to h6) are found, and headings outside a div.chapter are no longer dropped
- Sentences read as the book displays them: no space before punctuation after italics, no words split by drop caps, superscripts or page markers, and no footnote markers, page numbers or line numbers
- Invisible characters (such as the zero-width spaces Standard Ebooks put before em dashes) are removed and every kind of space becomes an ordinary space
- Chapter titles that are only a number, or that repeat in different parts of the book, now include their part's name, e.g. "Inferno Canto I"
- Short files are always read as UTF-8, so they are no longer garbled
- Much faster on large books (the slowest took over four minutes; now a few seconds)
- Added tests in test/test_chapterize.py and fixed test/test_import.py

2026.04.19 - v0.2.0

- Fixed bug where chapter titles were being stripped from sentence text, causing missing words at the start of sentences

2026.02.08 - v0.1.9

- Updated package to read in books from https://standardebooks.org/

2026.02.08 

- Updated the cover art logic to support more versions of epub

