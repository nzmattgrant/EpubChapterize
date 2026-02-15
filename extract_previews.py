import os
import re
import json
import unicodedata
import zipfile
import xml.etree.ElementTree as ET

OUTPUT_DIR = "epub_chapterize/output"
IMPORT_DIR = "epub_chapterize/books/to_import"

# Expanded ignore list including foreign variants
IGNORE_TITLES = {
    "imprint", "colophon", "uncopyright", "copyright", "license", 
    "table of contents", "contents", "index", "bibliography", 
    "endnotes", "footnotes", "titlepage", "dedication", "acknowledgments",
    "list of illustrations", "preface", "introduction", "foreword",
    "preface", "prologue", "avant-propos", "einleitung", "vorwort", "prólogo",
    "introduccion", "prefacio", "nota", "note", "advertisement",
    "author", "editor", "publisher", "frontispiece", "cover",
    "zueignung", "informazioni", "inhalt", "liber liber", "prefazione", "proemio",
    "dedica", "al duque", "personaggi", "dramatis personae", "interlocutori", "cast of characters",
    "characters", "scena", "scene", "escena", "l'autore a chi legge", "avvertenza", "al lettore", "aux lecteurs", "au lecteur"
}

# Expanded Fluff phrases
FLUFF_PHRASES = [
    "project gutenberg", "distributed proofreaders", "copyright", 
    "all rights reserved", "created by", "distributed by",
    "introduction", "preface", "foreword", "prologue", "contents",
    "illustrations", "dedicated to", "translator's note", "editor's note",
    "note on the text", "bibliographical note", "chronology", "gutenberg",
    "transcriber's note", "produced by", "prepared by", "digitized by",
    "public domain", "scan", "proofread", "errata", "tasa", "aprobaciones",
    "fee de erratas", "license", "licenza", "creative commons", "ebook",
    "electronic version", "html", "conversion", "encoding", "this edition",
    "college classes", "spanish academy", "vocabulary", "notes and vocabulary",
    "idiomatic commentary", "exercises for translation", "annotated", "footnotes",
    "abbreviations", "printing", "printed in", "copyright", "isbn",
    "library of congress", "publishers", "edited with", "by the same author",
    "list of characters", "dramatis personae", "personaggi", "act one",
    "scene one", "act i", "scene i",
    
    # Don Quijote & Spanish Legal/Academic
    "juan gallo de andrada", "escribano de cámara", "del rey nuestro señor",
    "suma del privilegio", "tasa", "fe de erratas", "testimonio de las erratas",
    "el rey", "yo, el rey", "por mandado del rey", "consejo real",
    "miguel de cervantes", "nos fue fecha relación", "habíades compuesto",
    "don quijote de la mancha", "miguel de cervantes saavedra", 
    "al duque de béjar", "conde de lemos", "príncipe tan inclinado",
    "favorecer las buenas artes", "dedicatoria", "al lector", "prólogo al lector",
    "testimonio de lo haber correcto", "di esta fee", "colegio de la madre de dios",
    "el licenciado francisco murcia", "la presente en valladolid",
    "vi la presente", "no tiene cosa digna", "corresponda a su original",
    
    # Specific academic phrases from Doña Perfecta and Novelas Cortas
    "prepared for the use of college classes", "elements of spanish grammar",
    "practice in reading", "study of the language is begun", "first year's work",
    "the editor has found", "actual experience", "it is safe to undertake",
    "close of the year", "earnest class", "printer's errors", "orthography and accentuation",
    "standard of the last edition", "academy's dictionary", "considerably fuller",
    "college editions", "modern works in foreign languages", "dreadful insufficiency",
    "existing spanish-english dictionaries", "editor's desire", "student some aid",
    "grammatical peculiarities", "text-books", "ramsey's text-book",
    "knapp's grammar", "coester's spanish grammar", "literary genres",
    "member of the spanish academy", "associate professor", "romance languages",
    "university of wisconsin", "the following stories from", "offered to the student",
    "easy style", "interest of the narrative", "incidental sidelights",
    "welcome one", "earlier stages of study", "fully annotated", "real difficulty",
    "passed over", "proper names have been explained", "insignificant to justify comment",
    "idiomatic commentary", "oral drill", "translating the idioms",
    "changes of person, tense", "mastery of the idioms", "exercises for translation",
    "systematic review", "elements of grammar", "labor of adaptation",
    "precise equivalent", "class-room proprieties", "acknowledgment is gratefully made",
    "esteemed colleague", "la buenaventura", "indeed, outside of these two forms",
    "no spaniard has won a literary success", "of the first order",
    "the plan of the edition", "needs no special comment", 
    "giuseppe giusti", "biblioteca italiana", "discorso che prepose",
    
    # Italian/Divine Comedy
    "incomincia la comedia", "ne la quale tratta", "pene e punimenti",
    
    # Names/Short fluff
    "federico zuccari", "gustave doré", "walter scott", 
    "tipografia umberto allegretti",

    # I promessi sposi / The Betrothed
    "dico di te, alessandro mio",
    "quel ramo del lago di como", # Wait, this is the GOOD one. Do not add.
    "l'historia si può veramente deffinire",
    "nè mi sarà imputato a vanità",
    "se empeña don miguel de unamuno",
    "sogliono, el più delle volte",
    "coloro che desiderano acquistare grazia",
    "el señor deán de la catedral",
    "muerto pocos años ha",
    "dejó entre sus papeles",
    "por la cual, por os hacer bien y merced",
    "os damos licencia y facultad",
    "imprimir el dicho libro",
    "intitulado el ingenioso hidalgo",
    "the numerous references in the notes",
    "addressed more particularly to the teachers",
    "noticias más remotas que tengo",
    "me las ha dado jacinto maría villalonga",
    "il venerdì 13 ottobre 1820", # This is actually the start of Le mie prigioni (Memoirs). It IS the book.
    "jonathan harker’s journal", # This is the start of Dracula. It is correct.
    "call me ishmael", # Correct.
    "longtemps, je me suis couché de bonne heure", # Correct.
]

def normalize_text(text):
    """Normalize text to ascii for easier matching"""
    return unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('utf-8').lower()

def is_ignored_title(filename_part):
    normalized = normalize_text(filename_part)
    for ignored in IGNORE_TITLES:
        if ignored in normalized:
            return True
    return False

def count_fluff_ratio(matches):
    """
    Check the first few paragraphs of a file. If a high percentage are fluff,
    reject the whole file.
    """
    check_limit = min(len(matches), 15) # Check first 15 paragraphs
    if check_limit == 0:
        return 0.0
        
    fluff_count = 0
    checked_count = 0
    
    for i in range(check_limit):
        text = matches[i].strip()
        if not text:
            continue
            
        checked_count += 1
        lower_text = text.lower()
        
        # Check against FLUFF_PHRASES
        is_this_fluff = False
        for phrase in FLUFF_PHRASES:
            if phrase in lower_text:
                is_this_fluff = True
                break
        
        # Also check for chapter headings which we might consider "neutral" but 
        # shouldn't save the file from being condemned if everything else is fluff.
        # Actually, if we see "Chapter 1" that's good. But if we see "Introduction", that's bad.
        # The IS_IGNORED_TITLE check is done on filename, but here we check content.
        
        if is_this_fluff:
            fluff_count += 1
            
    if checked_count == 0:
        return 0.0
        
    return fluff_count / checked_count

def get_text_segment(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception:
        return None

    # Find text blocks
    pattern = re.compile(r'<start>\s*(.*?)\s*<end>', re.DOTALL)
    matches = pattern.findall(content)
    
    if not matches:
        return None

    # Heuristic: If the file is heavily fluff at the start, skip the whole file
    if count_fluff_ratio(matches) > 0.4: # If > 40% of start is fluff, skip file
        # Check if it might be just skipping a long TOC? 
        # Usually academic intros are dense with fluff.
        return None
    
    filename_base = os.path.basename(filepath)
    clean_filename = normalize_text(filename_base)
    
    # Special handling for Fables: The files are small, sometimes just one fable.
    # We want to skip "Introduction.txt", "Imprint.txt" etc. which are handled by IGNORE_TITLES usually.
    # But "The Fox and the Grapes.txt" is good.
    
    for text in matches:
        clean_text = text.strip()
        if not clean_text:
            continue
            
        # Check against simple fluff phrases in the first 100 chars
        lower_text = clean_text.lower()
        is_fluff = False
        
        # Check explicit fluff phrases
        for phrase in FLUFF_PHRASES: 
             if phrase in lower_text: # Check anywhere in the text block
                 is_fluff = True
                 break
        if is_fluff:
            continue

        # Skip if text is just the filename/chapter title repeated
        # Or if it's just a number
        if len(clean_text) < 100:
            if normalize_text(clean_text) in clean_filename:
                continue
            if re.match(r'^(chapter|chapitre|capitulo|kapitel|part|parte|book|livre)\s+\w+$', lower_text):
                continue
            if re.match(r'^[ivxlcdm\d]+\.?$', lower_text): # Roman numerals or digits only
                continue

        # Special casing for Doctor Dolittle "M.D." fragment breakdown
        if clean_text == '” means that he was a proper doctor and knew a whole lot.':
             continue

        # Stage directions (often in parentheses or italics in source, but here plain text)
        # Heuristic: Start with uppercase, ends with no punctuation or just a dot, but short.
        # "Dämmerung." "Gesang von Aolsharfen begleitet."
        if "faust" in filename_base.lower():
             if lower_text in ["dämmerung.", "nacht.", "offene gegend."]:
                 continue
             if "gesang" in lower_text and len(clean_text) < 50:
                 continue
             if "begleitet" in lower_text and len(clean_text) < 50:
                 continue

        # Must have some punctuation to be a sentence
        if not re.search(r'[.!?”"]', clean_text):
            continue
            
        # Minimal word count check (avoid "El Autor.")
        # "Call me Ishmael." is 3 words.
        if len(clean_text.split()) < 3:
            continue
            
        # Avoid initials or very short acronyms like "B. P. B."
        if len(clean_text) < 10 and clean_text.isupper() and "." in clean_text:
             continue
             
        # Check for English academic text in foreign books
        # Simple heuristic: heavily English words for a Spanish/German book?
        # But we don't know the book language easily without parsing metadata again.
        # We rely on fluff phrases for now.

        # Special check towards "The present edition" style starts
        if lower_text.startswith("the present edition") or lower_text.startswith("this edition"):
            continue
        
        # Return the first good sentence/paragraph
        return clean_text
        
    return None

def extract_author_from_epub(epub_path):
    try:
        with zipfile.ZipFile(epub_path, 'r') as z:
            # Find opf file
            try:
                container = z.read('META-INF/container.xml')
                root = ET.fromstring(container)
                # namespace for container
                ns_container = {'n': 'urn:oasis:names:tc:opendocument:xmlns:container'}
                rootfile = root.find('.//n:rootfile', ns_container)
                if rootfile is None:
                    return None
                opf_path = rootfile.get('full-path')
            except Exception:
                # heuristic: look for .opf
                opf_paths = [n for n in z.namelist() if n.endswith('.opf')]
                if not opf_paths: 
                    return None
                opf_path = opf_paths[0]
            
            opf_content = z.read(opf_path)
            
            # Simple regex search for creator/author to avoid complex XML namespace handling
            # <dc:creator ...>Author Name</dc:creator>
            # OR <dc:creator>Author Name</dc:creator>
            
            match = re.search(rb'<dc:creator.*?>(.*?)</dc:creator>', opf_content, re.IGNORECASE | re.DOTALL)
            if match:
                author_blob = match.group(1).decode('utf-8')
                # Sometimes author is "Last, First" in "file-as" attribute, but text is usually First Last
                return author_blob.strip()
    except Exception:
        pass
    return None

def find_author(book_title):
    normalized_title = normalize_text(book_title).replace(' ', '').replace('_', '')
    
    # Walk import dir
    for root, dirs, files in os.walk(IMPORT_DIR):
        for file in files:
            if file.endswith(".epub"):
                file_decoded = normalize_text(file)
                base_name = file_decoded.replace('.epub', '')
                
                # Check for "Title - Author" format common in the list
                # Or "Author_Title" format
                
                # Try simple containment of title in filename
                normalized_base = base_name.replace(' ', '').replace('_', '').replace('-', '')
                
                # Relaxed matching: check if significant part of book title is in filename
                # e.g. "Faust: Der Tragödie erster Teil" -> "faustdertragodieersterteil"
                # Filename: "faustdertragodieersterteiljohannwolfgangvongoethe"
                
                if normalized_title in normalized_base or (len(normalized_title) > 10 and normalized_title[:15] in normalized_base):
                    # We have a candidate file.
                    # Try to parse author from filename if epub reading fails?
                    # Most filenames are "Title - Author.epub" or "author_title.epub"
                    
                    # Try parsing filename first as it seems reliable for this dataset
                    if ' - ' in file:
                         # Format: Title - Author.epub
                        parts = file.replace('.epub', '').split(' - ')
                        return parts[-1]
                    elif '_' in file:
                        # Format: author_title.epub (Standard Ebooks)
                        parts = file.replace('.epub', '').split('_')
                        # Check which part matches title?
                        # Usually author is first
                        candidate = parts[0]
                        # Remove dashes
                        candidate = candidate.replace('-', ' ').title()
                        return candidate
                        
                    # If filename parsing is ambiguous, try epub metadata
                    epub_path = os.path.join(root, file)
                    author = extract_author_from_epub(epub_path)
                    if author:
                        return author

    return "Unknown Author"

def process_book_dir(book_dir_path):
    book_title = os.path.basename(book_dir_path)
    author = find_author(book_title)
    
    files = []
    
    # Scan all txt files recursively
    for root, dirs, filenames in os.walk(book_dir_path):
        for f in filenames:
            if not f.endswith(".txt"):
                continue
                
            match = re.match(r'^(\d+)\s*-\s*(.*)\.txt$', f)
            if match:
                num = int(match.group(1))
                name = match.group(2)
                # Store full path, but keep name for ignore check
                # We use full path for reading
                files.append((num, name, os.path.join(root, f)))
            
    # Sort by number
    files.sort(key=lambda x: x[0])
    
    # Specific book overrides or logic could go here
    # Start looking from Chapter 1 usually.
    # Some books have "0 - Preface" or "1 - Introduction".
    
    # First pass: try to find first non-ignored chapter with content
    for num, name, full_path in files:
        if is_ignored_title(name):
            continue
        
        # For Don Quijote, blindly skip "TASA", "FEE DE ERRATAS", "APROBACIONES", "EL REY", "DEDICATORIA"
        # The file names are "2 - TASA.txt", "4 - EL REY.txt", "5 - AL DUQUE DE BEJAR,.txt", "6 - PROLOGO.txt"
        # "1 - El ingenioso hidalgo..." has the legal fluff.
        # "14 - Capítulo VII..." might be too late.
        # "8 - Capítulo primero..." parece ser el bueno!
        # "9 - Capítulo II..."
        # Así que los archivos de texto 1-7 son relleno. 1 es Título pero tiene "Yo, Juan Gallo..."
        # Necesitamos detectar "Yo, Juan Gallo" como relleno. Agregado a la lista.
        # También "Al duque de bejar" es una dedicatoria.
        
        sentence = get_text_segment(full_path)
        
        if sentence:
             return {
                "title": book_title,
                "author": author,
                "chapter": os.path.basename(full_path),
                "excerpt": sentence
            }
            
    # Fallback: if all were ignored or empty, look for the first file that has ANY content
    # (Maybe "Chapter 1" was named "Dedication" by mistake? Unlikely)
    return None

def main():
    results = []
    
    if not os.path.exists(OUTPUT_DIR):
        print(f"Output directory {OUTPUT_DIR} not found.")
        return

    # List directories
    book_dirs = [os.path.join(OUTPUT_DIR, d) for d in os.listdir(OUTPUT_DIR) if os.path.isdir(os.path.join(OUTPUT_DIR, d))]
    
    for d in book_dirs:
        info = process_book_dir(d)
        if info:
            results.append(info)
        else:
            # Fallback for books where we couldn't match a sentence
            results.append({
                "title": os.path.basename(d),
                "author": find_author(os.path.basename(d)),
                "chapter": "N/A",
                "excerpt": "No suitable preview found."
            })
            
    # Sort result by title
    results.sort(key=lambda x: x['title'])
    
    with open("book_previews.json", "w", encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
        
    print(f"Generated previews for {len(results)} books in book_previews.json")

if __name__ == "__main__":
    main()
