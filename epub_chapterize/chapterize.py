from glob import glob
import os
import re
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup
import nltk
nltk.download('punkt_tab')
from lxml import etree
from dataclasses import dataclass
import syntok.segmenter as segmenter
import spacy
import sys
from spacy.util import is_package


def load_model(name="en_core_web_sm"):
    if not is_package(name):
        raise RuntimeError(
            f"SpaCy model '{name}' not installed. Run: python -m spacy download {name}"
        )
    return spacy.load(name)

def get_nlp_model(language_code):
    if language_code == 'en':
        return load_model('en_core_web_trf')
    elif language_code == 'de':
        return load_model('de_dep_news_trf')
    elif language_code == 'it':
        return load_model('it_core_news_trf')
    elif language_code == 'es':
        return load_model('es_dep_news_trf')
    elif language_code == 'fr':
        return load_model('fr_dep_news_trf')
    else:
        return None

nlp_models = {}

@dataclass
class NavItem:
    nav_label: str
    doc_href: str
    element_id: str

@dataclass
class HeaderMatch:
    header: object
    header_text: str
    header_xpath: str
    nav_item: NavItem
sent_method = "nltk"  # Options: "nltk", "spacy", "syntok"

def syntok_segmenter(text):
    sentences = []
    for paragraph in segmenter.process(text):
        for sentence in paragraph:
            sentence = ''.join(token.spacing + token.value for token in sentence)
            sentences.append(sentence)
    return sentences

def get_punkt_tokenizer(langage_code):
    language_tokenizer_map = {
        'en': 'tokenizers/punkt/english.pickle',
        'fr': 'tokenizers/punkt/french.pickle',
        'de': 'tokenizers/punkt/german.pickle',
        'es': 'tokenizers/punkt/spanish.pickle',
        'it': 'tokenizers/punkt/italian.pickle',
        'nl': 'tokenizers/punkt/dutch.pickle',
        'pt': 'tokenizers/punkt/portuguese.pickle',
    }
    return language_tokenizer_map.get(langage_code, 'tokenizers/punkt/english.pickle')

def get_sent_method(language_code):
    if sent_method == "nltk":
        tokenizer = nltk.data.load(get_punkt_tokenizer(language_code))
        def custom_sent_tokenize(text):
            return tokenizer.tokenize(text)
        return custom_sent_tokenize
    elif sent_method == "spacy":
        nlp = get_nlp_model(language_code)
        if nlp:
            return lambda text: [sent.text for sent in nlp(text).sents]
        else:
            raise ValueError(f"Unsupported language code for spaCy: {language_code}")
    elif sent_method == "syntok":
        return lambda text: [sent for sent in syntok_segmenter(text)]
    else:
        raise ValueError(f"Unknown sentence segmentation method: {sent_method}")

def get_matched_header_for_nav_item(nav_item: NavItem, book) -> HeaderMatch:
    nav_label = nav_item.nav_label
    doc_href = nav_item.doc_href
    element_id = nav_item.element_id
    linked_item = book.get_item_with_href(doc_href)
    if linked_item:
        linked_content = linked_item.get_content().decode()
        linked_soup = BeautifulSoup(linked_content, 'html.parser')  # Parse as HTML
        extracted_text = None
        if element_id:
            linked_element = linked_soup.find(id=element_id)
            if linked_element:
                # Extract headers (h1, h2, h3) from the linked content
                h1s = linked_soup.find_all('h1')
                h2s = linked_soup.find_all('h2')
                h3s = linked_soup.find_all('h3')

                # Combine headers into a single list with their tag type
                headers = [(header, 'h1') for header in h1s] + \
                        [(header, 'h2') for header in h2s] + \
                        [(header, 'h3') for header in h3s]
                
                print(f"Found {len(headers)} headers in {doc_href} with element ID: {element_id}")

                best_match = None
                pattern = generate_header_pattern(nav_label)
                print(f"Searching for header matching pattern: {pattern.pattern} in {doc_href} with element ID: {element_id}")
                for header, _ in headers:
                    header_text = header.get_text(' ', strip=True).replace('\n', ' ')
                    print(f"Checking header: {header_text}")
                    if pattern.search(header_text):
                        print(f"Pattern matched in header: {header_text}")
                        if not best_match or len(header_text) < len(best_match.header_text):
                            def get_xpath(element):
                                tree = etree.HTML(str(element))
                                return tree.getroottree().getpath(tree)
                            header_xpath = get_xpath(header)
                            best_match = HeaderMatch(header, header_text, header_xpath, nav_item)
                extracted_text = best_match if best_match else None
        return extracted_text

def generate_header_pattern(target_text):
    words = re.findall(r'\w+', target_text.lower())
    pattern = r'.*'.join(re.escape(word) for word in words)
    return re.compile(pattern, re.IGNORECASE)

def get_nav_items_standard_gutenberg_epub3(file_path) -> list[NavItem]:
    book = epub.read_epub(file_path)
    nav_items = []

    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_NAVIGATION:
            html_content = item.get_content().decode()
            soup = BeautifulSoup(html_content, 'xml')
            navpoints = soup.find_all('navPoint')
            for navpoint in navpoints:
                nav_label = navpoint.find('navLabel').find("text").get_text(strip=True)
                content = navpoint.find('content')
                doc_href = None
                element_id = None
                if content and content.has_attr('src'):
                    src = content['src']
                    src_parts = src.split('#')
                    doc_href = src_parts[0]
                    element_id = src_parts[1] if len(src_parts) > 1 else None  # ID within the document
                nav_items.append(NavItem(nav_label, doc_href, element_id))
    return nav_items

def filter_by_chapter_class(combined_header_info: list[tuple[any, NavItem]], book) -> list[tuple[any, NavItem]]:
    found_chapter_divs = False
    filtered_header_info = []
    for header, nav_item in combined_header_info:
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_DOCUMENT:
                soup = BeautifulSoup(item.get_body_content(), 'html.parser')
                chapter_divs = soup.find_all('div', class_='chapter')
                if chapter_divs:
                    found_chapter_divs = True
                for chapter_div in chapter_divs:
                    if header in chapter_div.descendants:
                        filtered_header_info.append((header, nav_item))
                        break

    if not found_chapter_divs:
        return combined_header_info
    
    return filtered_header_info

def chapterize(file_path):
    book = epub.read_epub(file_path)
    nav_item_infos = get_nav_items_standard_gutenberg_epub3(file_path)
    language = book.get_metadata('DC', 'language')
    language = language[0][0] if language else 'en'

    # Get title and author metadata
    title = book.get_metadata('DC', 'title')
    author = book.get_metadata('DC', 'creator')
    title = title[0][0] if title else "Unknown Title"
    author = author[0][0] if author else "Unknown Author"

    # Extract cover image if available
    cover_item = book.get_item_with_id('cover')
    cover_image = None
    if cover_item:
        cover_image = cover_item.get_content()

    if language in nlp_models:
        get_sentences = nlp_models[language]
    else:
        get_sentences = get_sent_method(language)
        nlp_models[language] = get_sentences
    chapters = []
    matched_candidate_headers: list[HeaderMatch] = []
    for nav_item_info in nav_item_infos:
        matched_candidate_headers.append(get_matched_header_for_nav_item(nav_item_info, book))
        print(f"Matched header for nav item '{nav_item_info.nav_label}': {matched_candidate_headers[-1]}")

    matched_candidate_headers = [candidate_header for candidate_header in matched_candidate_headers if candidate_header is not None]

    for matched_header in matched_candidate_headers:
        print(f"Matched Header: {matched_header.header_text}, XPath: {matched_header.header_xpath}, Nav Label: {matched_header.nav_item.nav_label}")
    
    for item in book.get_items():
        if item.get_type() == ebooklib.ITEM_DOCUMENT:
            soup = BeautifulSoup(item.get_body_content(), 'html.parser')

            current_document_all_headers = []
            for header_tag in ['h1', 'h2', 'h3']:
                current_document_all_headers.extend(soup.find_all(header_tag))
                
            headers_with_nav_items = []
            for header in current_document_all_headers:
                for header_match in matched_candidate_headers:
                    if str(header_match.header) == str(header):
                        headers_with_nav_items.append((header, header_match.nav_item))

            headers_with_nav_items = filter_by_chapter_class(headers_with_nav_items, book)
            print(f"Number of headers with nav items: {len(headers_with_nav_items)}")

            sections = []
            for i, combined_header in enumerate(headers_with_nav_items):
                header_match = combined_header[0]
                nav_item_info = combined_header[1]
                heading_text = nav_item_info.nav_label
                if "THE FULL PROJECT GUTENBERG LICENSE" in heading_text:
                    continue
                section = {'title': heading_text, 'paragraphs': []}
                next_heading = headers_with_nav_items[i + 1] if i + 1 < len(headers_with_nav_items) else None
                current_element = header_match
                while current_element and current_element != next_heading:
                    if current_element.name == 'p':
                        section['paragraphs'].append(current_element.get_text(separator=" ", strip=True))
                    current_element = current_element.find_next()
                sections.append(section)

            no_sentences_heading = ''
            for section in sections:
                chapter_title = no_sentences_heading + section['title']
                chapter_title = chapter_title.replace('\n', ' ')
                paragraphs = section['paragraphs']
                sentences = []
                for paragraph in paragraphs:
                    # Replace all occurrences of chapter_title and newlines in the paragraph
                    transformed_sentences = get_sentences(paragraph.replace(chapter_title, '').replace('\n', ' '))
                    for sentence in transformed_sentences:
                        stripped_sentence = sentence.strip()
                        if stripped_sentence and not all(char in '.,!?;:"\'-()[]{}' for char in stripped_sentence):  # Check if the sentence is not empty, whitespace, or only punctuation
                            sentences.append(sentence)
                if sentences:
                    chapters.append({
                        'title': chapter_title,
                        'sentences': [s.strip() for s in sentences]
                    })
                    no_sentences_heading = ''
                else:
                    no_sentences_heading += chapter_title + ' '

    return chapters, language, title, author, cover_image
    


if __name__ == "__main__":

    books_to_add = []
    books_directory = "books"

    all_books = glob(os.path.join(books_directory, "**", "*.epub"), recursive=True)
    individual_book = ["/Users/matthewgrant/Source/EpubChapterize/epub_chapterize/books/to_import/Röschen-Jaköble-und-andere-kleine-Leute-De.epub"]
    for file_path in individual_book:
        if "archive" in file_path:  # Include only files in the archive folder
            continue
        book = epub.read_epub(file_path)
        language = book.get_metadata('DC', 'language')
        language = language[0][0] if language else 'en'
        
        title = book.get_metadata('DC', 'title')
        author = book.get_metadata('DC', 'creator')
        title = title[0][0] if title else "Unknown Title"
        author = author[0][0] if author else "Unknown Author"
        
        books_to_add.append({
            'file_path': os.path.relpath(file_path, books_directory),
            'title': title,
            'author': author
        })

    output_test_files = True
    unable_to_parse_file = os.path.join(books_directory, "unable_to_parse.txt")
    if os.path.exists(unable_to_parse_file):
        os.remove(unable_to_parse_file)
    for book_to_add in books_to_add:
        if len(sys.argv) > 1:
            input_file_path = sys.argv[1]
            if os.path.exists(input_file_path):
                chapters, language, _, _, _ = chapterize(input_file_path)
            else:
                print(f"File {input_file_path} does not exist. Falling back to default behavior.")
                chapters, language, _, _, _ = chapterize(os.path.join(books_directory, book_to_add["file_path"]))
        else:
            chapters, language, _, _, _ = chapterize(os.path.join(books_directory, book_to_add["file_path"]))

        print("Chapters found:", len(chapters))
        if not chapters:
            unable_to_parse_file = os.path.join(books_directory, "unable_to_parse.txt")
            os.makedirs(os.path.dirname(unable_to_parse_file), exist_ok=True)
            with open(unable_to_parse_file, "a", encoding="utf-8") as f:
                f.write(os.path.join(books_directory, book_to_add["file_path"]) + "\n")
        for chapter in chapters:
            print(chapter["title"])
            print(chapter["sentences"][:1])
            if output_test_files:
                book_folder = os.path.join("output", book_to_add["title"][:100])
                os.makedirs(book_folder, exist_ok=True)
                print("Book folder created:", book_folder)
                chapter_number = chapters.index(chapter) + 1
                chapter_file_path = os.path.join(book_folder, f"{chapter_number} - {chapter['title'][:100]}.txt")
                
                with open(chapter_file_path, "w", encoding="utf-8") as chapter_file:
                    chapter_file.write(chapter["title"] + "\n\n")
                    chapter_file.write("\n".join(f"<start> {sentence} <end>" for sentence in chapter["sentences"]))
        


    
