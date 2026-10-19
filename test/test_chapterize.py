# Run from anywhere with: python test/test_chapterize.py
import contextlib
import io
import itertools
import os
import sys
import tempfile
import unittest

from ebooklib import epub

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from epub_chapterize.chapterize import chapterize


def contents_links(toc, ids=None):
    # toc lists (link, label) contents entries, or (link, label, [child entries]) for nested ones
    ids = ids or itertools.count()
    return [(epub.Link(link, label, f'entry{next(ids)}'), contents_links(children[0], ids)) if children else epub.Link(link, label, f'entry{next(ids)}')
            for link, label, *children in toc]


def write_epub(path, files, toc):
    # files maps file names to body HTML; toc is as for contents_links
    book = epub.EpubBook()
    book.set_identifier('test')
    book.set_title('Test Book')
    book.add_author('Test Author')
    book.set_language('en')
    for name, body in files.items():
        item = epub.EpubHtml(file_name=name, title=name)
        item.content = f'<html><body>{body}</body></html>'
        book.add_item(item)
        book.spine.append(item)
    book.toc = contents_links(toc)
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    epub.write_epub(path, book)


def chapterize_files(files, toc):
    with tempfile.TemporaryDirectory() as directory:
        path = os.path.join(directory, 'test.epub')
        write_epub(path, files, toc)
        with contextlib.redirect_stdout(io.StringIO()):
            chapters, *_ = chapterize(path)
    return [(chapter['title'], chapter['sentences']) for chapter in chapters]


# (paragraph HTML, the text a reader sees), mostly taken from books in books/to_import
PARAGRAPHS = [
    ('<p>The <i epub:type="se:name.vessel.ship">Nellie</i>, a cruising yawl</p>', 'The Nellie, a cruising yawl'),
    ('<p>each other’s yarns\N{ZERO WIDTH NO-BREAK SPACE}—and even convictions</p>', 'each other’s yarns—and even convictions'),
    ('<p class="p0"><span class="initial">D</span>ies Buch</p>', 'Dies Buch'),
    ('<p>M<sup>me</sup> Verdurin</p>', 'Mme Verdurin'),
    ('<p>From Rusticus<a href="endnotes.xhtml#note-6" role="doc-noteref" epub:type="noteref">6</a> I received</p>', 'From Rusticus I received'),
    ('<p>el frío penetrante de la<span class="linenum">5</span><a id="p1l5"></a><br/> madrugada no</p>', 'el frío penetrante de la madrugada no'),
    ('<p>a ragione l’<span xml:lang="de">Ulmann</span><sup><a href="Section0114.xhtml#nota_21">nota 21</a></sup> e il</p>', 'a ragione l’Ulmann e il'),
    ('<p>los españoles,<a href="x.xhtml#p16n3"><sup class="up">[16-3]</sup></a><br/>\n     divididos en dos bandos</p>', 'los españoles, divididos en dos bandos'),
    ('<p>caballero en flaquísimo y<br/>\n<span class="side">05</span>destartalado burro</p>', 'caballero en flaquísimo y destartalado burro'),
    ('<p>The word seems here used. <a href="x.xhtml#noteref-25" role="doc-backlink" epub:type="backlink">↩</a></p>', 'The word seems here used.'),
    ('<p>Text here.<a class="fnanchor" href="x.xhtml#Fussnote_1">[1]</a> More</p>', 'Text here. More'),
    ('<p>grand changement<a href="notes.html#a234"><span class="t9">{1}</span></a> ;</p>', 'grand changement ;'),
    ('<p>Note body <a href="Section0008.xhtml#nota_1_ritorno">[Torna]</a></p>', 'Note body'),
    ('<p>See <a href="book-4.xhtml#book-4-p-21">Book <span epub:type="z3998:roman">IV</span>, ¶21</a>.</p>', 'See Book IV, ¶21.'),
    ('<p>As shown (pag. <a href="x.xhtml#Page_11">11</a>) above</p>', 'As shown (pag. 11) above'),
    ('<p>Visit the <a href="https://standardebooks.org/x#page-scans">Internet Archive</a>.</p>', 'Visit the Internet Archive.'),
    ('<p>1a EDIZIONE ELETTRONICA DEL: 20 giugno 1996<br/>2a EDIZIONE ELETTRONICA DEL: 28 marzo 2018</p>', '1a EDIZIONE ELETTRONICA DEL: 20 giugno 1996 2a EDIZIONE ELETTRONICA DEL: 28 marzo 2018'),
    ('<p>line one<br/>\n\N{NO-BREAK SPACE}\N{NO-BREAK SPACE}\N{NO-BREAK SPACE}line two</p>', 'line one line two'),
    ('<p>«\N{NO-BREAK SPACE}Oui\N{NO-BREAK SPACE}», dit-il\N{NO-BREAK SPACE}!</p>', '« Oui », dit-il !'),
    ('<p>“\N{HAIR SPACE}‘Nellie’ is here,” he said\N{ZERO WIDTH NO-BREAK SPACE}\N{HAIR SPACE}\N{ZERO WIDTH NO-BREAK SPACE}…</p>', '“ ‘Nellie’ is here,” he said …'),
    ('<p>Kunst\N{SOFT HYPHEN}mittel und e<sup>-ix</sup></p>', 'Kunstmittel und e-ix'),
    ('<p>Let me know about the funeral etc<!--sic--> do not know his family at all.</p>', 'Let me know about the funeral etc do not know his family at all.'),
]


class ChapterizeTest(unittest.TestCase):
    def test_paragraph_text_is_what_a_reader_sees(self):
        body = ''.join(f'<h2 id="c{i}">{i}</h2>{html}' for i, (html, _) in enumerate(PARAGRAPHS))
        chapters = chapterize_files({'text.xhtml': body}, [(f'text.xhtml#c{i}', str(i)) for i in range(len(PARAGRAPHS))])
        self.assertEqual(len(chapters), len(PARAGRAPHS))
        for (html, expected), (_, sentences) in zip(PARAGRAPHS, chapters):
            with self.subTest(html=html):
                self.assertEqual(' '.join(sentences), expected)

    def test_contents_entries_find_their_headings_in_a_single_file_book(self):
        # Project Gutenberg style: links to empty anchors just before the chapter headings, numbering that restarts
        # in each part, a label that differs from its heading, and a link without an anchor to a heading on two lines
        body = ('<h1 id="p1">PART ONE</h1>'
                '<p><a id="c1"></a></p><h4>I</h4><p>Alpha one.</p>'
                '<p><a id="c2"></a></p><h4>II</h4><p>Alpha two.</p><p>* * *</p><p>— Not so hard! —</p>'
                '<h1 id="p2">PART TWO</h1>'
                '<p><a id="c3"></a></p><h4>I</h4><p>Beta one.</p>'
                '<p><a id="c4"></a></p><h4>II</h4><p>Beta two.</p>'
                '<h2>Epilogue\nTen Years Later</h2><p>Gamma.</p>')
        toc = [('book.xhtml#p1', 'PART ONE'), ('book.xhtml#c1', 'I'), ('book.xhtml#c2', 'II'),
               ('book.xhtml#p2', 'PART TWO'), ('book.xhtml#c3', 'I. The Storm'), ('book.xhtml#c4', 'II'),
               ('book.xhtml', 'Epilogue: Ten Years Later')]
        self.assertEqual(chapterize_files({'book.xhtml': body}, toc),
                         [('PART ONE I', ['Alpha one.']), ('II', ['Alpha two.', '— Not so hard! —']),
                          ('PART TWO I. The Storm', ['Beta one.']), ('II', ['Beta two.']), ('Epilogue: Ten Years Later', ['Gamma.'])])

    def test_book_title_and_author_come_from_the_metadata(self):
        with tempfile.TemporaryDirectory() as directory:
            path = os.path.join(directory, 'test.epub')
            write_epub(path, {'text.xhtml': '<h2 id="a">Last Chapter</h2><p>Text.</p>'}, [('text.xhtml#a', 'Last Chapter')])
            with contextlib.redirect_stdout(io.StringIO()):
                _, language, title, author, _ = chapterize(path)
        self.assertEqual((language, title, author), ('en', 'Test Book', 'Test Author'))

    def test_chapters_continue_into_the_next_file(self):
        files = {'one.xhtml': '<h2 id="a">I</h2><p>Start of one.</p>',
                 'two.xhtml': '<p>End of one.</p><h2 id="b">II</h2><p>Two.</p>'}
        toc = [('one.xhtml#a', 'I'), ('two.xhtml#b', 'II')]
        self.assertEqual(chapterize_files(files, toc), [('I', ['Start of one.', 'End of one.']), ('II', ['Two.'])])

    def test_labels_repeated_under_different_entries_are_named_after_their_parent(self):
        files = {'one.xhtml': '<h1 id="a">Act One</h1><h2 id="b">Scene One</h2><p>A.</p><h2 id="c">Scene Two</h2><p>B.</p>',
                 'two.xhtml': '<h1 id="d">Act Two</h1><h2 id="e">Scene One</h2><p>C.</p><h2 id="f">Scene Two</h2><p>D.</p>'
                              '<h2 id="g">Finale</h2><p>E.</p><h2 id="h">3.</h2><p>F.</p>'}
        toc = [('one.xhtml#a', 'Act One', [('one.xhtml#b', 'Scene One'), ('one.xhtml#c', 'Scene Two')]),
               ('two.xhtml#d', 'Act Two', [('two.xhtml#e', 'Scene One'), ('two.xhtml#f', 'Scene Two'), ('two.xhtml#g', 'Finale'), ('two.xhtml#h', '3.')])]
        self.assertEqual(chapterize_files(files, toc),
                         [('Act One Scene One', ['A.']), ('Act One Scene Two', ['B.']), ('Act Two Scene One', ['C.']),
                          ('Act Two Scene Two', ['D.']), ('Finale', ['E.']), ('Act Two 3.', ['F.'])])

    def test_headings_without_text_only_join_titles_in_their_own_file(self):
        files = {'title.xhtml': '<h1 id="a">The Book</h1>', 'one.xhtml': '<h2 id="b">I</h2><p>Text.</p>'}
        toc = [('title.xhtml#a', 'The Book'), ('one.xhtml#b', 'I')]
        self.assertEqual(chapterize_files(files, toc), [('I', ['Text.'])])

    def test_headings_without_text_join_the_next_chapter_title_once(self):
        files = {'text.xhtml': '<h1 id="a">Part One</h1><h2 id="b">Book One</h2><h3 id="c">I</h3><p>Text.</p>'}
        toc = [('text.xhtml#a', 'Part One'), ('text.xhtml#b', 'Book One'), ('text.xhtml#c', 'I')]
        self.assertEqual(chapterize_files(files, toc), [('Part One Book One I', ['Text.'])])

    def test_headings_outside_chapter_divs_are_kept(self):
        files = {'one.xhtml': '<div class="chapter"><h2 id="a">One</h2><p>First.</p></div>',
                 'two.xhtml': '<h2 id="b">Two</h2><p>Second.</p>'}
        toc = [('one.xhtml#a', 'One'), ('two.xhtml#b', 'Two')]
        self.assertEqual(chapterize_files(files, toc), [('One', ['First.']), ('Two', ['Second.'])])

    def test_short_documents_are_read_as_utf8(self):
        files = {'text.xhtml': '<h2 id="a">I</h2><p>The <i>Nellie</i>, a yawl\N{ZERO WIDTH NO-BREAK SPACE}—swung.</p>'}
        self.assertEqual(chapterize_files(files, [('text.xhtml#a', 'I')]), [('I', ['The Nellie, a yawl—swung.'])])


if __name__ == '__main__':
    unittest.main()
