from glob import glob, escape as glob_escape
import os
import posixpath
import re
import unicodedata
from urllib.parse import quote, unquote
import ebooklib
from ebooklib import epub
from bs4 import BeautifulSoup, Tag
import nltk
nltk.download('punkt_tab')
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
    parent_label: str = None

@dataclass
class HeaderMatch:
    header: object
    header_text: str
    nav_item: NavItem

HEADER_TAGS = ['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'hgroup']
# Characters other than letters, digits and -._~ that Readium leaves as they are in a file's URL, as Go's URL paths do
URL_PATH_SAFE_CHARACTERS = "/$&+,:;=@"
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

def get_matched_header_for_nav_item(nav_item: NavItem, book, soups) -> HeaderMatch:
    print(f"Getting matched header for nav item: {nav_item}")
    linked_soup = soups.get(book.get_item_with_href(nav_item.doc_href))
    if not linked_soup:
        return None
    anchor = linked_soup.find(id=nav_item.element_id) if nav_item.element_id else None
    # A contents entry that links to a header, into one, or to a place before one names the first such header,
    # even when its label doesn't match, like "-I- Juanito Santa Cruz -i-" for a heading split over three h2s
    linked_header = anchor and (anchor if anchor.name in HEADER_TAGS else anchor.find_parent(HEADER_TAGS) or anchor.find_next(HEADER_TAGS))
    if linked_header:
        return HeaderMatch(linked_header, linked_header.get_text(' ', strip=True), nav_item)
    pattern = generate_header_pattern(nav_item.nav_label)
    # Otherwise match the label and take the shortest match, as a label like "I" also matches any longer header containing an i
    matches = [HeaderMatch(header, header.get_text(' ', strip=True), nav_item) for header in linked_soup.find_all(HEADER_TAGS)]
    matches = [match for match in matches if pattern.search(match.header_text)]
    print(f"Headers in {nav_item.doc_href} matching {pattern.pattern}: {[match.header_text for match in matches]}")
    return min(matches, key=lambda match: len(match.header_text), default=None)

# EPUB 3 epub:type markers for footnote references, note backlinks and page numbers
APPARATUS_SEMANTICS = {'noteref', 'backlink', 'pagebreak'}
# Classes Project Gutenberg books use for line numbers
APPARATUS_CLASSES = {'linenum', 'side'}

def is_apparatus(element):
    if APPARATUS_SEMANTICS.intersection(element.get('epub:type', '').split()) or APPARATUS_CLASSES.intersection(element.get('class', [])):
        return True
    if element.name == 'a' and element.has_attr('href'):
        # Links that are note markers rather than prose: superscripted, or wrapped in brackets like [1], {a} or [Torna]
        text = element.get_text().strip()
        return (element.find_parent('sup') is not None or element.find('sup') is not None
                or (len(text) > 1 and unicodedata.category(text[0]) == 'Ps' and unicodedata.category(text[-1]) == 'Pe'))
    return False

def get_displayed_text(element):
    # Inline tags join their text directly, line breaks separate it, and apparatus is left out
    parts = []
    for child in element.children:
        if isinstance(child, Tag) and not is_apparatus(child):
            parts.append(' ' if child.name == 'br' else get_displayed_text(child))
        elif type(child) in Tag.MAIN_CONTENT_STRING_TYPES:
            parts.append(str(child))
    return ''.join(parts)

def generate_header_pattern(target_text):
    words = re.findall(r'\w+', target_text.lower())
    pattern = r'.*'.join(re.escape(word) for word in words)
    # DOTALL so the words also match across line breaks inside a header
    return re.compile(pattern, re.IGNORECASE | re.DOTALL)

def get_nav_items_standard_gutenberg_epub3(book) -> list[NavItem]:
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
                    # Links are URLs, while ebooklib's item names are decoded
                    doc_href, _, element_id = map(unquote, content['src'].partition('#'))
                parent = navpoint.find_parent('navPoint')
                parent_label = parent.find('navLabel').find("text").get_text(strip=True) if parent else None
                nav_items.append(NavItem(nav_label, doc_href, element_id or None, parent_label))
    return nav_items

def chapterize(file_path):
    # Unlike the book, the reader keeps the package file's folder
    reader = epub.EpubReader(file_path)
    book = reader.load()
    nav_item_infos = get_nav_items_standard_gutenberg_epub3(book)
    print(f"Number of nav items found: {len(nav_item_infos)}")
    print("Nav Items:")
    for nav_item in nav_item_infos:
        print(f" - {nav_item.nav_label}, href: {nav_item.doc_href}, id: {nav_item.element_id}")

    language = book.get_metadata('DC', 'language')
    language = language[0][0] if language else 'en'

    # Get title and author metadata
    title = book.get_metadata('DC', 'title')
    author = book.get_metadata('DC', 'creator')
    title = title[0][0] if title else "Unknown Title"
    author = author[0][0] if author else "Unknown Author"

    # Extract cover image if available
    cover_image = None
    cover_item = None

    # 1. Try OPF Metadata
    cover_meta = book.get_metadata('OPF', 'cover')
    if cover_meta and len(cover_meta) > 0 and cover_meta[0][1]:
        cover_id = cover_meta[0][1].get('content')
        if cover_id:
            cover_item = book.get_item_with_id(cover_id)

    # Validate if it's an image
    if cover_item and cover_item.get_type() not in [ebooklib.ITEM_IMAGE, ebooklib.ITEM_COVER]:
        cover_item = None

    # 2. Try ITEM_COVER
    if not cover_item:
        cover_items = list(book.get_items_of_type(ebooklib.ITEM_COVER))
        if cover_items:
            cover_item = cover_items[0]

    # 3. Try ITEM_IMAGE with 'cover' in name/id
    if not cover_item:
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_IMAGE:
                if 'cover' in item.get_name().lower() or 'cover' in item.get_id().lower():
                    cover_item = item
                    break

    if cover_item:
        cover_image = cover_item.get_content()

    if language in nlp_models:
        get_sentences = nlp_models[language]
    else:
        get_sentences = get_sent_method(language)
        nlp_models[language] = get_sentences
    chapters = []
    # Parse each document once, so matched headers can be found again by identity; get_body_content() is always UTF-8
    soups = {item: BeautifulSoup(item.get_body_content(), 'html.parser', from_encoding='utf-8') for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT)}
    matched_candidate_headers: list[HeaderMatch] = []
    for nav_item_info in nav_item_infos:
        matched_candidate_headers.append(get_matched_header_for_nav_item(nav_item_info, book, soups))
        print(f"Matched header for nav item '{nav_item_info.nav_label}': {matched_candidate_headers[-1]}")

    matched_candidate_headers = [candidate_header for candidate_header in matched_candidate_headers if candidate_header is not None]

    for matched_header in matched_candidate_headers:
        print(f"Matched Header: {matched_header.header_text}, Nav Label: {matched_header.nav_item.nav_label}")

    spine_ids = [item_id for item_id, _ in book.spine]
    spine_items = [book.get_item_with_id(item_id) for item_id in spine_ids]
    all_items = spine_items + [item for item in book.get_items() if item not in spine_items]
    # Each matched header's contents entries, in contents order
    nav_items_by_header = {}
    for match in matched_candidate_headers:
        nav_items_by_header.setdefault(id(match.header), []).append(match.nav_item)

    # Read the documents in order as one text, so a chapter runs from its header to the next chapter's header even when
    # that is in a later file, but doesn't run on into files outside the reading order
    sections = []
    section = None
    for item in all_items:
        if item not in soups:
            continue
        if item not in spine_items:
            section = None
        # The item's path from the root of the EPUB as a URL, which is how readers such as Readium name it;
        # ebooklib's item names are decoded and relative to the package file
        file = quote(posixpath.normpath(posixpath.join(reader.opf_dir, item.get_name())), safe=URL_PATH_SAFE_CHARACTERS)
        for element in soups[item].find_all(True):
            for nav_item in nav_items_by_header.get(id(element), []):
                section = {'nav_item': nav_item, 'file': file, 'paragraphs': []}
                sections.append(section)
            # A paragraph inside a heading, like the subtitle in <hgroup><h2>I</h2><p>Loomings</p></hgroup>, is part of the heading
            if element.name == 'p' and section and not element.find_parent(HEADER_TAGS):
                # Drop invisible formatting characters, such as the zero-width no-break spaces before em dashes and soft hyphens,
                # which only control line breaking
                paragraph_text = ''.join(char for char in get_displayed_text(element) if unicodedata.category(char) != 'Cf')
                # Collapse all whitespace, including no-break and hair spaces, into ordinary spaces
                section['paragraphs'].append((file, ' '.join(paragraph_text.split())))

    # The parent entries each label appears under; some contents also repeat every entry at the top level, without a parent
    parent_labels = {}
    for nav_item in nav_item_infos:
        if nav_item.parent_label:
            parent_labels.setdefault(nav_item.nav_label, set()).add(nav_item.parent_label)
    sections = [section for section in sections if "THE FULL PROJECT GUTENBERG LICENSE" not in section['nav_item'].nav_label]
    # The title and start of headings without text, which lead into the next chapter
    lead_in = None
    for i, section in enumerate(sections):
        nav_item = section['nav_item']
        # Headings without text only lead into the next chapter's title within their own file
        if i and section['file'] != sections[i - 1]['file']:
            lead_in = None
        lead_in_title, start = lead_in or ('', {'start_file': section['file'], 'start_id': nav_item.element_id})
        label = nav_item.nav_label
        # A label that is only a number, like "2.", or that the contents repeat under different entries, like "Scene II" in every act,
        # is named after its parent entry, unless that entry's heading already leads into this chapter
        is_ambiguous = len(parent_labels.get(label, ())) > 1 or not any(char.isalpha() for char in label)
        if is_ambiguous and nav_item.parent_label and nav_item.parent_label not in lead_in_title:
            label = f'{nav_item.parent_label} {label}'
        chapter_title = (lead_in_title + label).replace('\n', ' ')
        sentences = []
        sentence_files = []
        for paragraph_file, paragraph in section['paragraphs']:
            # Paragraphs without any words, such as * * * scene breaks, are left out
            if not re.search(r'\w', paragraph):
                continue
            paragraph_sentences = []
            for sentence in get_sentences(paragraph):
                sentence = sentence.strip()
                # Keep fragments without words, like an opening »... or a closing …” split off by the tokenizer, with the sentence beside them
                if paragraph_sentences and not (re.search(r'\w', paragraph_sentences[-1]) and re.search(r'\w', sentence)):
                    paragraph_sentences[-1] = f'{paragraph_sentences[-1]} {sentence}'.strip()
                elif sentence:
                    paragraph_sentences.append(sentence)
            if paragraph_sentences and (not sentence_files or sentence_files[-1]['file'] != paragraph_file):
                sentence_files.append({'file': paragraph_file, 'first_sentence': len(sentences)})
            sentences.extend(paragraph_sentences)
        if sentences:
            chapters.append({
                'title': chapter_title,
                'sentences': sentences,
                **start,
                'sentence_files': sentence_files,
            })
            lead_in = None
        else:
            # chapter_title already starts with the earlier empty headings' titles
            lead_in = (chapter_title + ' ', start)

    return chapters, language, title, author, cover_image
    


def main():
    # epub-chapterize [EPUB FILE OR FOLDER, default books/to_import] writes each book's cover and chapters to output/<book title>/,
    # one numbered text file per chapter, and lists books with no chapters in unable_to_parse.txt next to the input
    path = sys.argv[1] if len(sys.argv) > 1 else "books/to_import"
    file_paths = [path] if path.endswith(".epub") else sorted(glob(os.path.join(path, "**", "*.epub"), recursive=True))
    if not file_paths or not os.path.exists(file_paths[0]):
        sys.exit(f"No EPUB files found at {path}")
    unable_to_parse_file = os.path.join(os.path.dirname(path) if path.endswith(".epub") else path, "unable_to_parse.txt")
    if os.path.exists(unable_to_parse_file):
        os.remove(unable_to_parse_file)
    for file_path in file_paths:
        chapters, _, title, _, cover_image = chapterize(file_path)
        print(f"{file_path}: {len(chapters)} chapters")
        # File names can't contain a slash, which a title can
        book_folder = os.path.join("output", title[:100].replace('/', '-'))
        os.makedirs(book_folder, exist_ok=True)
        # Chapter numbering can change between runs, so clear out the book's earlier chapter files
        for old_chapter_file in glob(os.path.join(glob_escape(book_folder), "*.txt")):
            os.remove(old_chapter_file)
        if cover_image:
            with open(os.path.join(book_folder, "cover.jpg"), "wb") as cover_file:
                cover_file.write(cover_image)
        if not chapters:
            with open(unable_to_parse_file, "a", encoding="utf-8") as unable_file:
                unable_file.write(file_path + "\n")
        for number, chapter in enumerate(chapters, 1):
            with open(os.path.join(book_folder, f"{number} - {chapter['title'][:100].replace('/', '-')}.txt"), "w", encoding="utf-8") as chapter_file:
                chapter_file.write(chapter["title"] + "\n\n")
                chapter_file.write("\n".join(f"<start> {sentence} <end>" for sentence in chapter["sentences"]))


if __name__ == "__main__":
    main()




