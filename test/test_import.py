import os

from epub_chapterize.chapterize import chapterize

print("EpubChapterize package imported successfully.")

books_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "epub_chapterize", "books", "to_import")
print(chapterize(os.path.join(books_directory, "english", "lewis-carroll_alices-adventures-in-wonderland_john-tenniel.epub")))
