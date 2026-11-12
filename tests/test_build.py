"""Build the sample document with the Word builder and check the .docx package."""

import glob
import io
import os
import re
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET

import pytest
from sphinx.application import Sphinx

HERE = os.path.dirname(os.path.abspath(__file__))
SAMPLE = os.path.join(HERE, "sample")
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
M = "{http://schemas.openxmlformats.org/officeDocument/2006/math}"


def build_sample(out, **overrides):
    # Most tests check the file as sphinx2word writes it, without the optional update of the fields in Word.
    overrides.setdefault("word_update_fields", "prompt")
    warnings = io.StringIO()
    app = Sphinx(SAMPLE, SAMPLE, str(out), str(out / ".doctrees"), "word", status=None, warning=warnings,
                 freshenv=True, confoverrides=overrides)
    app.build()
    files = glob.glob(str(out / "*.docx"))
    assert len(files) == 1
    return zipfile.ZipFile(files[0]), warnings.getvalue()


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    return build_sample(tmp_path_factory.mktemp("word"))


@pytest.fixture(scope="module")
def built_sphinx_numbers(tmp_path_factory):
    """Captions numbered the Sphinx way: numfig_format and chapter numbers."""
    return build_sample(tmp_path_factory.mktemp("word_sphinx"), word_caption_numbering="sphinx")


def test_no_warnings(built):
    _, warnings = built
    assert warnings.strip() == ""


def test_all_parts_are_well_formed(built):
    z, _ = built
    for name in z.namelist():
        if name.endswith(".xml") or name.endswith(".rels"):
            ET.fromstring(z.read(name))


def test_content(built):
    z, _ = built
    doc = ET.fromstring(z.read("word/document.xml"))
    body = doc.find(W + "body")
    assert len(body.findall(".//" + W + "tbl")) >= 8          # tables, numbered equations, admonitions
    assert len(list(body.iter(M + "oMath"))) >= 20
    assert len(list(body.iter(M + "eqArr"))) >= 3
    # 5 images (one chosen from figures/bigsat_patch.*), a graphviz and an inheritance diagram, and a figure in the
    # appendix
    assert len(list(body.iter(W + "drawing"))) == 8
    text = "".join(t.text or "" for t in body.iter(W + "t"))
    for expected in ("Figure 1: ", "Table 2: ", "Listing 1: ", "(1)", "(4)", "sample_module.",
                     "convolve", "Term one", "Line two", "Spanning cells"):
        assert expected in text, expected


def test_internal_links_have_bookmarks(built):
    z, _ = built
    xml = z.read("word/document.xml").decode("utf-8")
    bookmarks = set(re.findall(r'w:bookmarkStart w:id="\d+" w:name="([^"]+)"', xml))
    anchors = set(re.findall(r'w:hyperlink w:anchor="([^"]+)"', xml))
    assert anchors <= bookmarks, anchors - bookmarks
    refs = set(re.findall(r"REF (_Ref\d+) ", xml))
    assert refs, "expected REF fields"
    assert refs <= bookmarks, refs - bookmarks
    # every bookmark that is started is also ended
    starts = re.findall(r'<w:bookmarkStart w:id="(\d+)"', xml)
    ends = re.findall(r'<w:bookmarkEnd w:id="(\d+)"', xml)
    assert sorted(starts) == sorted(ends)
    assert len(starts) == len(set(starts))


def field_codes(xml):
    return [c.strip() for c in re.findall(r'<w:instrText xml:space="preserve">([^<]*)</w:instrText>', xml)]


def test_captions_are_numbered_by_word(built):
    """By default the caption number is Word's: "Figure 1" as Insert Caption writes it, not Sphinx's "Fig. 4.1"."""
    z, warnings = built
    codes = field_codes(z.read("word/document.xml").decode("utf-8"))
    assert codes.count(r"SEQ Figure \* ARABIC") == 4
    assert codes.count(r"SEQ Table \* ARABIC") == 3
    assert codes.count(r"SEQ Listing \* ARABIC") == 1
    assert codes.count(r"SEQ Equation \* ARABIC") == 4
    assert not any(c.startswith("STYLEREF") or r"\r " in c for c in codes)
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    captions = []
    for p in body.iter(W + "p"):
        style = p.find(f"{W}pPr/{W}pStyle")
        if style is not None and style.get(W + "val") == "Caption":
            captions.append(p)
            # the Caption style formats the label, nothing is bold
            assert p.find(f".//{W}b") is None
    texts = ["".join(t.text or "" for t in p.iter(W + "t")) for p in captions]
    # the figure of the appendix is not numbered: the appendix is not in the toctree, so Sphinx does not number it
    assert [t.split(":")[0] for t in texts] == ["Listing 1", "Table 1", "Table 2", "Figure 1", "Figure 2",
                                                "Figure 3", "Table 3", "Figure 4", "A figure in an appendix."]


def test_references_follow_word_numbers(built):
    z, _ = built
    xml = z.read("word/document.xml").decode("utf-8")
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    text = "".join(t.text or "" for t in body.iter(W + "t"))
    assert "A cross-reference to Lists and to Figure 1 and to equation (1)." in text
    assert "See Figure 2 and Table 2." in text
    # "Figure 1" is one REF to a bookmark that starts with the caption label and holds the SEQ field
    names = re.findall(r"REF (_Ref\d+) \\h", xml)
    labelled = 0
    for name in names:
        after = xml[xml.index(f'w:name="{name}"/>'):][:3000]
        text_start = re.search(r"<w:t[^>]*>([^<]*)", after).group(1)
        if text_start in ("Figure ", "Table "):
            labelled += 1
            assert "SEQ " in after
    assert labelled == 4


def test_sphinx_caption_numbering(built_sphinx_numbers):
    z, _ = built_sphinx_numbers
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    text = "".join(t.text or "" for t in body.iter(W + "t"))
    for expected in ("Fig. 4.1: ", "Table 3.1: ", "Listing 1.1: ", "(2.1)", "(2.4)",
                     "A cross-reference to Lists and to Fig. 4.1 and to", "equation (2.1)."):
        assert expected in text, expected


def test_captions_and_equations_are_numbered_by_word_fields(built_sphinx_numbers):
    z, _ = built_sphinx_numbers
    codes = field_codes(z.read("word/document.xml").decode("utf-8"))
    assert codes.count(r"SEQ Figure \* ARABIC \s 1") == 4
    assert codes.count(r"SEQ Table \* ARABIC \s 1") == 3
    assert codes.count(r"SEQ Listing \* ARABIC \s 1") == 1
    assert codes.count(r"SEQ Equation \* ARABIC \s 1") == 4
    assert codes.count(r"STYLEREF 1 \s") == 12
    # Word's own count gives the same numbers as Sphinx, so no number had to be forced
    assert not any(r"\r " in c for c in codes)


def test_lists_of_figures_and_tables_follow_the_contents(built):
    z, _ = built
    xml = z.read("word/document.xml").decode("utf-8")
    codes = field_codes(xml)
    assert codes[:3] == [r'TOC \o "1-3" \h \z \u', r'TOC \h \z \c "Figure"', r'TOC \h \z \c "Table"']
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    text = "".join(t.text or "" for t in body.iter(W + "t"))
    assert text.index("Contents") < text.index("List of Figures") < text.index("List of Tables")
    assert 'w:styleId="TableofFigures"' in z.read("word/styles.xml").decode("utf-8")


def test_references_are_ref_fields(built):
    z, _ = built
    xml = z.read("word/document.xml").decode("utf-8")
    refs = [c for c in field_codes(xml) if c.startswith("REF ")]
    assert len(refs) == 6                     # :ref: to a section, :numref: x4, :eq: x1
    assert all(r.endswith(r"\h \* CHARFORMAT") for r in refs)


def test_headings_are_numbered_by_the_heading_styles(built):
    z, _ = built
    styles = z.read("word/styles.xml").decode("utf-8")
    for level in (1, 2, 3):
        style = re.search(rf'<w:style [^>]*w:styleId="Heading{level}".*?</w:style>', styles, re.S).group(0)
        assert f'<w:ilvl w:val="{level - 1}"/>' in style
    toc_heading = re.search(r'<w:style [^>]*w:styleId="TOCHeading".*?</w:style>', styles, re.S).group(0)
    assert '<w:numId w:val="0"/>' in toc_heading
    numbering = z.read("word/numbering.xml").decode("utf-8")
    assert '<w:pStyle w:val="Heading1"/><w:lvlText w:val="%1"/>' in numbering
    # the number is not typed into the heading text
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    for p in body.iter(W + "p"):
        style = p.find(f"{W}pPr/{W}pStyle")
        if style is not None and style.get(W + "val").startswith("Heading"):
            text = "".join(t.text or "" for t in p.iter(W + "t"))
            assert not re.match(r"\d", text), text


def test_template_heading_numbering_is_kept():
    from sphinx2word.docx_package import link_heading_numbering
    own = ('<w:styles><w:style w:type="paragraph" w:styleId="Heading1"><w:pPr><w:numPr><w:numId w:val="7"/>'
           '</w:numPr></w:pPr></w:style><w:style w:type="paragraph" w:styleId="Heading2"><w:rPr/></w:style>'
           '</w:styles>')
    patched = link_heading_numbering(own, 3)
    assert '<w:numId w:val="7"/>' in patched and '<w:numId w:val="3"/>' not in patched.split("Heading2")[0]
    assert '<w:pPr><w:numPr><w:ilvl w:val="1"/><w:numId w:val="3"/></w:numPr></w:pPr><w:rPr/>' in patched


def test_footnotes(built):
    z, _ = built
    notes = z.read("word/footnotes.xml").decode("utf-8")
    assert "first footnote" in notes and "second footnote" in notes
    assert notes.count("<w:footnoteRef/>") == 2
    # every footnote must be referenced from the body, otherwise Word reports the file as corrupt
    body = z.read("word/document.xml").decode("utf-8")
    assert '<w:footnoteReference w:id="1"/>' in body and '<w:footnoteReference w:id="2"/>' in body


def test_images_are_packaged(built):
    z, _ = built
    media = [n for n in z.namelist() if n.startswith("word/media/")]
    assert any(n.endswith(".png") for n in media) and any(n.endswith(".svg") for n in media)
    rels = z.read("word/_rels/document.xml.rels").decode("utf-8")
    for n in media:
        assert n[len("word/"):] in rels


def test_template_styles_are_merged(tmp_path):
    from sphinx2word.docx_package import DocxPackage
    template = tmp_path / "template.docx"
    styles = ('<w:styles xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
              '<w:style w:type="paragraph" w:styleId="Heading1"><w:name w:val="heading 1"/>'
              '<w:rPr><w:color w:val="FF0000"/></w:rPr></w:style></w:styles>')
    with zipfile.ZipFile(template, "w") as t:
        t.writestr("word/styles.xml", styles)
    pkg = DocxPackage(template=str(template))
    out = tmp_path / "out.docx"
    pkg.save(str(out), "<w:p/>")
    merged = zipfile.ZipFile(out).read("word/styles.xml").decode("utf-8")
    assert merged.count('w:styleId="Heading1"') == 1 and "FF0000" in merged     # template style kept
    assert 'w:styleId="SpxCode"' in merged and 'w:styleId="Caption"' in merged   # missing styles added


def test_word_opens_the_file(built, tmp_path):
    """Optional: on Windows with Word installed, check that Word opens the file without reporting damage."""
    pytest.importorskip("win32com.client")
    import sys
    sys.path.insert(0, HERE)
    from render_with_word import docx_to_pdf
    z, _ = built
    try:
        docx_to_pdf(z.filename, str(tmp_path / "sample.pdf"))
    except Exception as exc:          # pragma: no cover - only reached on a machine with Word
        if "Word.Application" in str(exc) or "Invalid class string" in str(exc):
            pytest.skip("Microsoft Word is not installed")
        raise
    assert (tmp_path / "sample.pdf").stat().st_size > 10000


def test_column_widths_fit_the_longest_word():
    from docutils import nodes
    from sphinx2word.translator import fit_column_widths

    def row(*texts):
        r = nodes.row()
        for t in texts:
            r += nodes.entry("", nodes.paragraph(text=t))
        return r

    rows = [row("Calibration", "Yes", "A long description of the issue " * 3)]
    widths = fit_column_widths(rows, [13, 4, 70], 9000)
    assert sum(widths) <= 9000
    assert widths[1] >= 3 * 125            # "Yes" is not squeezed to a letter per line
    assert widths[0] >= 11 * 125           # neither is "Calibration"
    assert widths[2] > widths[0] > widths[1]


def test_bibliography_entries_line_up(built):
    """The text of every entry starts at the hanging indent, which fits the usual labels but not a long bib key."""
    z, _ = built
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    entries = {}
    for p in body.iter(W + "p"):
        style = p.find(f"{W}pPr/{W}pStyle")
        if style is not None and style.get(W + "val") == "SpxBibliography":
            text = "".join(t.text or "" for t in p.iter(W + "t"))
            ind = p.find(f"{W}pPr/{W}ind")
            entries[text.split("]")[0] + "]"] = (int(ind.get(W + "left")), int(ind.get(W + "hanging")))
    assert set(entries) == {"[Lia90]", "[vHDD+18]", "[Chandrasekhar60]"}
    assert len(set(entries.values())) == 1
    left, hanging = entries["[Lia90]"]
    assert left == hanging
    assert 9 * 125 <= hanging <= 9 * 125 + 400        # fits "[vHDD+18]", not "[Chandrasekhar60]"


REPORT = dict(
    word_contract=["BigSat Phase B2/C/D", "Contract No. BS-26-001"],
    word_cover_figure="figures/logo.svg",
    word_document_title=["Algorithm Theoretical Basis Document:", "Sample"],
    word_prepared_by=[("Ada Marsh", "Calibration Scientist"), ("Ben Okafor", "Instrument Engineer")],
    word_reviewed_by=[("Clara Voss", "Principal Investigator")],
    word_distribution=[("J. Smith", "Example Space Agency")],
    word_change_record=[("", "Draft A", "2023/06/16", "All", "CDR draft for review"),
                        {"revision": "Rev 0", "date": "2023/06/28", "pages": "All", "description": "CDR"}],
)


@pytest.fixture(scope="module")
def built_report(tmp_path_factory):
    return build_sample(tmp_path_factory.mktemp("word_report"), **REPORT)


def paragraphs(z):
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    out = []
    for p in body.iter(W + "p"):
        style = p.find(f"{W}pPr/{W}pStyle")
        out.append((style.get(W + "val") if style is not None else "", "".join(t.text or "" for t in p.iter(W + "t"))))
    return out


def test_report_cover_and_front_matter(built_report):
    z, warnings = built_report
    assert "sphinx2word" not in warnings      # (Sphinx itself warns about node classes registered by earlier builds)
    paras = paragraphs(z)
    cover = [t for s, t in paras if s == "SpxCoverTitle"]
    assert cover == ["BigSat Phase B2/C/D", "Contract No. BS-26-001", "Algorithm Theoretical Basis Document:",
                     "Sample"]
    headings = [t for s, t in paras if s == "SpxFrontHeading"]
    assert headings == ["Contributor List", "Distribution List", "Change Record"]
    texts = [t for _, t in paras]
    for row in ("Prepared By", "Ada Marsh", "Instrument Engineer", "Reviewed By", "Clara Voss", "J. Smith",
                "Example Space Agency", "Affected Pages", "Draft A", "2023/06/28", "CDR draft for review"):
        assert row in texts, row
    # the cover figure, the front matter comes before the contents, and the plain title page is not written
    xml = z.read("word/document.xml").decode("utf-8")
    assert xml.index("Change Record") < xml.index("TOC \o")
    assert "SpxCoverFigure" in xml and "<w:drawing>" in xml.split("Algorithm Theoretical")[0]
    assert not any(s == "Title" for s, _ in paras)


def test_report_page_numbers_and_footer(built_report):
    z, _ = built_report
    xml = z.read("word/document.xml").decode("utf-8")
    sections = re.findall(r"<w:sectPr>.*?</w:sectPr>", xml)
    # front matter, body, a landscape page (tests/sample/layout.rst), and the rest of the body
    assert len(sections) == 4
    assert 'w:fmt="lowerRoman"' in sections[0] and "<w:titlePg/>" in sections[0]
    assert 'w:fmt="decimal" w:start="1"' in sections[1] and "<w:titlePg/>" not in sections[1]
    for section in sections[2:]:          # the page numbers continue
        assert "pgNumType" not in section and "<w:titlePg/>" not in section
    assert ['w:orient="landscape"' in s for s in sections] == [False, False, True, False]
    footer = z.read("word/footer1.xml").decode("utf-8")
    assert "BigSat Phase B2/C/D" in footer and "w:ptab" in footer and " PAGE " in footer


def test_plain_title_page_is_unchanged(built):
    z, _ = built
    paras = paragraphs(z)
    assert paras[0] == ("Title", "sphinx2word Sample Document")
    assert not any(s.startswith("SpxCover") or s == "SpxFrontHeading" for s, _ in paras)
    footer = z.read("word/footer1.xml").decode("utf-8")
    assert "w:ptab" not in footer


def git(repo, *args, date=None):
    env = dict(os.environ, GIT_AUTHOR_NAME="t", GIT_AUTHOR_EMAIL="t@example.com", GIT_COMMITTER_NAME="t",
               GIT_COMMITTER_EMAIL="t@example.com")
    if date:
        env.update(GIT_AUTHOR_DATE=date, GIT_COMMITTER_DATE=date)
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True, env=env)


@pytest.mark.skipif(shutil.which("git") is None, reason="git is not installed")
def test_change_record_from_git(tmp_path):
    from sphinx2word.git_history import change_record_from_git
    git(tmp_path, "init", "-q", "-b", "main")
    (tmp_path / "a.txt").write_text("1")
    git(tmp_path, "add", "a.txt")
    git(tmp_path, "commit", "-q", "-m", "First draft", date="2023-06-16T10:00:00")
    git(tmp_path, "tag", "draft-a")                                                    # lightweight: commit subject
    (tmp_path / "a.txt").write_text("2")
    git(tmp_path, "commit", "-q", "-am", "Review fixes", date="2023-06-28T10:00:00")
    git(tmp_path, "tag", "-a", "rev-0", "-m", "CDR issue", date="2023-06-28T11:00:00")   # annotated: tag message
    git(tmp_path, "checkout", "-q", "-b", "side")
    (tmp_path / "a.txt").write_text("3")
    git(tmp_path, "commit", "-q", "-am", "Not released", date="2023-07-01T10:00:00")
    git(tmp_path, "tag", "side-tag")                                                   # not on main: left out
    rows = change_record_from_git(str(tmp_path))
    assert [(r["revision"], r["date"], r["description"]) for r in rows] == [
        ("draft-a", "2023/06/16", "First draft"), ("rev-0", "2023/06/28", "CDR issue")]
    rows = change_record_from_git(str(tmp_path), pattern="rev-*", notes={"rev-0": {"issue": "1", "pages": "1-5"}})
    assert rows == [{"issue": "1", "revision": "rev-0", "date": "2023/06/28", "pages": "1-5",
                     "description": "CDR issue"}]


def settings_xml(z):
    return z.read("word/settings.xml").decode("utf-8")


def test_prompt_mode_asks_word_to_update_fields(built):
    z, _ = built
    assert '<w:updateFields w:val="true"/>' in settings_xml(z)


def test_none_mode_does_not_prompt(tmp_path):
    z, _ = build_sample(tmp_path, word_update_fields="none")
    assert "updateFields" not in settings_xml(z)
    # the rest of the package is unchanged and still well-formed
    for name in z.namelist():
        if name.endswith(".xml") or name.endswith(".rels"):
            ET.fromstring(z.read(name))


def test_word_fills_in_the_contents(tmp_path):
    """Optional: on Windows with Word installed, Word fills in the contents and the prompt is removed."""
    pytest.importorskip("win32com.client")
    z, warnings = build_sample(tmp_path, word_update_fields="word")
    if "could not update the fields" in warnings or "needs Microsoft Word" in warnings:
        pytest.skip("Microsoft Word is not installed")
    assert "updateFields" not in settings_xml(z)
    xml = z.read("word/document.xml").decode("utf-8")
    assert "Right-click here and choose Update Field" not in xml
    assert "PAGEREF _Toc" in xml                     # Word wrote the entries of the table of contents


def test_simple_caption_math_is_text(built):
    # Word flattens equations when it copies captions into the table of figures, so simple math in a caption is
    # written as formatted text instead of an equation.
    z, _ = built
    body = ET.fromstring(z.read("word/document.xml")).find(W + "body")
    captions = [p for p in body.iter(W + "p")
                if any(s.get(W + "val") == "Caption" for s in p.iter(W + "pStyle"))]
    texts = {"".join(t.text or "" for t in p.iter(W + "t")): p for p in captions}
    table = next(p for t, p in texts.items() if "Results with math" in t)
    figure = next(p for t, p in texts.items() if "mission patch" in t)
    for p in (table, figure):
        assert p.find(".//" + M + "oMath") is None
    assert "ΔT" in "".join(t.text or "" for t in table.iter(W + "t"))
    assert "λ = 550\u2009nm" in "".join(t.text or "" for t in figure.iter(W + "t"))


def document_xml(built):
    z, _ = built
    return z.read("word/document.xml").decode("utf-8")


def instructions(xml):
    return [i.strip() for i in re.findall(r"<w:instrText[^>]*>([^<]*)</w:instrText>", xml)]


def test_index_entries_and_index(built):
    xml = document_xml(built)
    xe = [i for i in instructions(xml) if i.startswith("XE ")]
    for expected in ('XE "calibration:flat field"', 'XE "detector:dark current"', 'XE "dark current:detector"',
                     'XE "solar:limb darkening"', 'XE "limb:darkening, solar"', 'XE "darkening:solar limb"',
                     r'XE "PRNU" \t "see flat field"', r'XE "detector" \t "see also calibration"',
                     r'XE "gain" \b', 'XE "index role"', r'XE "a term\: with a colon"',
                     'XE "convolve() (in module sample_module)"'):
        assert expected in xe, expected
    assert any(i.startswith("INDEX ") for i in instructions(xml))
    assert xml.rfind("INDEX ") > xml.rfind("XE ")              # the index comes after all the entries


def test_page_break_and_raw_openxml(built):
    xml = document_xml(built)
    paragraph = re.search(r"<w:p>(?:(?!</w:p>).)*This paragraph starts a new page", xml, re.DOTALL).group(0)
    assert "<w:pageBreakBefore/>" in paragraph
    assert "Raw WordprocessingML paragraph" in xml
    assert re.search(r"<w:b/></w:rPr><w:t>bold raw run", xml)


def test_landscape_section(built):
    xml = document_xml(built)
    sizes = re.findall(r"<w:pgSz [^>]*>", xml)
    assert sum("landscape" in s for s in sizes) == 1
    # the landscape section holds the wide table, and the sections around it are portrait
    landscape_end = xml.index('w:orient="landscape"')
    table = xml.index("A wide table on a landscape page")
    portrait_end = xml.rfind("<w:sectPr>", 0, table)
    assert portrait_end < table < landscape_end
    # page numbers start at 1 once, after the front matter, and continue through the landscape section
    assert len(re.findall(r'<w:pgNumType w:fmt="decimal" w:start="1"/>', xml)) == 1


def test_code_line_numbers_and_emphasis(built):
    xml = document_xml(built)
    start = xml.index(">10  <")
    block = xml[start:xml.index("</w:p>", start)]
    assert ">11  <" in block and ">12  <" in block
    lines = block.split("<w:br/>")
    assert "FFF2A8" not in lines[0] and "FFF2A8" in lines[1] and "FFF2A8" in lines[2]


def test_graphviz_diagrams_are_pictures(built):
    xml = document_xml(built)
    caption = xml.rindex("A Graphviz diagram")      # the caption, not its entry in the list
    assert "<w:drawing>" in xml[xml.rfind("<w:p>", 0, caption - 2000):caption]
    z, _ = built
    assert sum(name.endswith(".svg") for name in z.namelist()) >= 3     # logo.svg and the two diagrams


def test_appendices(built):
    z, _ = built
    xml = document_xml(built)
    numbering = z.read("word/numbering.xml").decode("utf-8")
    assert 'w:lvlText w:val="Appendix %1:"' in numbering
    appendix_num = re.search(r'<w:num w:numId="(\d+)"><w:abstractNumId w:val="(\d+)"/></w:num>(?!.*<w:num )',
                             numbering, re.S)
    headings = {}
    for title in ("Calibration Data", "Dark Current", "Details"):
        start = xml.rfind("<w:p>", 0, xml.rindex(f">{title}<"))
        headings[title] = re.search(r'<w:ilvl w:val="(\d)"/><w:numId w:val="(\d+)"/>', xml[start:]).groups()
    assert [lvl for lvl, _ in headings.values()] == ["0", "1", "2"]
    assert len({num for _, num in headings.values()}) == 1 and appendix_num is not None
    # the appendix comes after the last chapter and before the indexes
    assert xml.rindex("Layout and Diagrams") < xml.rindex(">Calibration Data<") < xml.index("INDEX ")


def test_module_index(built):
    xml = document_xml(built)
    codes = instructions(xml)
    assert r'XE "sample_module" \f "m"' in codes
    module_index = codes.index(r'INDEX \f "m" \h "A" \c "1" \z "1033"')
    general_index = codes.index(r'INDEX \h "A" \c "2" \z "1033"')
    assert module_index < general_index
    assert ">Python Module Index<" in xml


@pytest.fixture(scope="module")
def built_german(tmp_path_factory):
    return build_sample(tmp_path_factory.mktemp("word_de"), language="de")


@pytest.fixture(scope="module")
def built_german_english_labels(tmp_path_factory):
    return build_sample(tmp_path_factory.mktemp("word_de_en"), language="de", word_translate_labels=False)


def front_headings(xml):
    return re.findall(r'<w:pStyle w:val="TOCHeading"/>.*?<w:t[^>]*>([^<]*)', xml)


def test_labels_in_the_language_of_the_project(built_german):
    z, _ = built_german
    xml = z.read("word/document.xml").decode("utf-8")
    assert front_headings(xml) == ["Inhaltsverzeichnis", "Abbildungsverzeichnis", "Tabellenverzeichnis",
                                   "Python-Modulindex", "Stichwortverzeichnis"]
    codes = instructions(xml)
    assert r"SEQ Abbildung \* ARABIC" in codes and r"SEQ Tabelle \* ARABIC" in codes
    assert r'TOC \h \z \c "Abbildung"' in codes
    assert r'XE "PRNU" \t "siehe flat field"' in codes
    assert 'w:lvlText w:val="Anhang %1:"' in z.read("word/numbering.xml").decode("utf-8")


def test_labels_can_stay_english(built_german_english_labels):
    z, _ = built_german_english_labels
    xml = z.read("word/document.xml").decode("utf-8")
    assert front_headings(xml) == ["Contents", "List of Figures", "List of Tables", "Python Module Index", "Index"]
    assert r"SEQ Figure \* ARABIC" in instructions(xml)


def test_wildcard_image_gets_a_file(built):
    # "figures/bigsat_patch.*": the builder picks the file, as the other builders do (post_process_images)
    z, warnings = built
    xml = document_xml(built)
    caption = xml.rindex("A figure whose file is chosen by Sphinx")
    figure = xml[xml.rfind("<w:p>", 0, xml.rfind("<w:p>", 0, caption)):caption]
    assert "<w:drawing>" in figure and 'name="bigsat_patch.png"' in figure
    assert "bigsat_patch.*" not in warnings


def test_yaml_code_is_coloured(built):
    # The YAML lexer makes token types that the Pygments style does not list (Token.Literal.Scalar.Plain); they take
    # the colour of the nearest type the style knows, instead of stopping the build.
    xml = document_xml(built)
    start = xml.index("# a YAML block")
    block = xml[xml.rfind("<w:p>", 0, start):xml.index("</w:p>", start)]
    colours = dict((text, colour) for colour, text in
                   re.findall(r'<w:color w:val="(\w+)"/>(?:<w:[ib](?:Cs)?/>)*</w:rPr><w:t[^>]*>([^<]+)<', block))
    assert colours.get("instrument") and colours.get("UV")
    assert colours["instrument"] != colours["UV"]


def toc_field_paragraphs(xml, instruction):
    """The paragraphs of the TOC field whose instruction starts with ``instruction``."""
    start = xml.rfind("<w:p>", 0, xml.index(f"> {instruction}"))
    end_field = xml.index('<w:fldChar w:fldCharType="end"/>', start)
    return re.findall(r"<w:p>.*?</w:p>", xml[start:xml.index("</w:p>", end_field) + 6])


def paragraph_text(paragraph):
    """The text of a paragraph, with its tabs (not the tab stops of its properties)."""
    body = re.sub(r"<w:pPr>.*?</w:pPr>", "", paragraph)
    return "".join("\t" if tab else text for text, tab in re.findall(r"<w:t[^>]*>([^<]*)</w:t>|<w:(tab)/>", body))


def test_contents_are_prefilled(built):
    # Without Word the contents start out with their entries (numbers, titles, links), not a placeholder, so the
    # document reads well before Word updates its fields. The headings stay Word headings: the entries are the
    # field's result, which Word replaces when it updates the field.
    xml = document_xml(built)
    paragraphs = toc_field_paragraphs(xml, r'TOC \o')
    texts = [paragraph_text(p) for p in paragraphs]
    assert texts[:3] == ["1\tText and Lists", "1.1\tLists", "1.2\tCode and Notes"]
    assert "Appendix A: Calibration Data" in texts and "A.1\tDark Current" in texts
    assert all('<w:pStyle w:val="TOC' in p for p in paragraphs)
    bookmarks = set(re.findall(r'w:bookmarkStart w:id="\d+" w:name="([^"]+)"', xml))
    anchors = re.findall(r'<w:hyperlink w:anchor="([^"]+)"', "".join(paragraphs))
    assert len(anchors) == len(paragraphs) and set(anchors) <= bookmarks
    assert "PAGEREF" not in "".join(paragraphs)          # page numbers are left to Word
    assert "w:dirty" not in xml                          # updating is left to word_update_fields


def test_lists_of_figures_and_tables_are_prefilled(built):
    xml = document_xml(built)
    figures = [paragraph_text(p) for p in toc_field_paragraphs(xml, r'TOC \h \z \c "Figure"')]
    tables = [paragraph_text(p) for p in toc_field_paragraphs(xml, r'TOC \h \z \c "Table"')]
    assert figures[0].startswith("Figure 1: The BigSat mission patch.") and len(figures) == 4
    assert [t.split(":")[0] for t in tables] == ["Table 1", "Table 2", "Table 3"]
    # math in a caption keeps its format in the list: Delta T in "Results with math"
    assert tables[0].startswith("Table 1: Results with math ΔT")


def test_indexes_stay_placeholders(built):
    xml = document_xml(built)
    paragraphs = toc_field_paragraphs(xml, r'INDEX \h')
    assert len(paragraphs) == 1 and "Right-click here and choose Update Field" in paragraphs[0]
