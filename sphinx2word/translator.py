"""
A docutils visitor that turns a Sphinx doctree into WordprocessingML.

The translator walks the single, fully resolved doctree assembled by :class:`sphinx2word.builder.WordBuilder` and
appends XML strings to a list of block level elements. Paragraph content (runs, equations, bookmarks, hyperlinks) is
collected in a :class:`Paragraph` object until the paragraph is closed.

Composite blocks (tables, admonitions, numbered equations, footnotes) are rendered by walking their children into a
separate block list (:meth:`WordTranslator.render_blocks`) and wrapping the result.
"""

from __future__ import annotations

import hashlib
import io
import os
import re
import struct
import subprocess
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional, Tuple
from xml.sax.saxutils import escape, quoteattr

from docutils import nodes
from sphinx import addnodes
from sphinx.locale import _, admonitionlabels
from sphinx.util import logging

from .docx_package import DocxPackage, EMU_PER_INCH, FRONT_MATTER_END, SECTION_END, TWIPS_PER_INCH, list_indent
from .git_history import change_record_from_git, normalise_change_record
from .labels import ENGLISH, default_labels
from .latex2omml import LatexMathError, latex_to_omml, omml_as_text, parse_mathjax_macros

logger = logging.getLogger(__name__)

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
M_NS = "http://schemas.openxmlformats.org/officeDocument/2006/math"
# Where a prefilled TOC field goes; replaced at the end of the document, when the headings and captions are known
TOC_MARKER = "<!--sphinx2word:toc-field:{}-->"
TOC_MARKER_RE = re.compile(r"<!--sphinx2word:toc-field:(\d+)-->")
# .. raw:: latex that only breaks the page
RAW_LATEX_PAGE_BREAK = re.compile(r"\s*(\\(newpage|clearpage|cleardoublepage|pagebreak)\s*)+")

_ILLEGAL_XML = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff]")

# Inline classes used by roles such as :red:`text` and their colours.
CLASS_COLOURS = {"red": "C00000", "green": "00B050", "orange": "ED7D31", "blue": "0070C0", "purple": "7030A0",
                 "gray": "808080", "grey": "808080"}

ADMONITION_COLOURS = {"note": "4472C4", "seealso": "4472C4", "hint": "70AD47", "tip": "70AD47",
                      "important": "ED7D31", "attention": "ED7D31", "caution": "ED7D31", "warning": "C00000",
                      "danger": "C00000", "error": "C00000", "todo_node": "7F7F7F", "admonition": "4472C4"}

# Headings and column titles of the front matter of a contract report (word_front_matter_labels overrides them).
FRONT_MATTER_LABELS = {"contributors": "Contributor List", "prepared_by": "Prepared By", "reviewed_by": "Reviewed By",
                       "name": "Name", "function": "Function", "distribution": "Distribution List",
                       "company": "Company", "changes": "Change Record", "issue": "ISS", "revision": "REV",
                       "date": "Date", "pages": "Affected Pages", "description": "Description"}

# A 1x1 transparent PNG used as the fallback image for SVG files when no rasteriser is available.
_TRANSPARENT_PNG = bytes.fromhex(
    "89504e470d0a1a0a0000000d4948445200000001000000010806000000"
    "1f15c4890000000d49444154789c6360000002000154a24f5d0000000049454e44ae426082")


def find_all(node: nodes.Node, cls) -> list:
    """All descendants (and the node itself) of a type; ``findall`` only exists in docutils >= 0.18."""
    finder = getattr(node, "findall", None) or node.traverse
    return list(finder(cls))


def xml_text(text: str) -> str:
    return escape(_ILLEGAL_XML.sub("", text))


# ----------------------------------------------------------------------------------------------------------------------
#   Paragraph
# ----------------------------------------------------------------------------------------------------------------------

class Paragraph:
    """An open ``<w:p>`` that collects runs."""

    def __init__(self, style: Optional[str] = None, indent: int = 0, hanging: int = 0, jc: Optional[str] = None,
                 num: Optional[Tuple[int, int]] = None, keep_next: bool = False, page_break_before: bool = False,
                 spacing: Optional[str] = None):
        self.style = style
        self.indent = indent
        self.hanging = hanging
        self.jc = jc
        self.num = num
        self.keep_next = keep_next
        self.page_break_before = page_break_before
        self.spacing = spacing
        self.content: List[str] = []
        self.links: List[Tuple[int, str]] = []    # (start index in content, opening tag)

    def add(self, xml: str):
        self.content.append(xml)

    @property
    def is_empty(self) -> bool:
        return not any(("<w:r>" in c or "<m:oMath" in c or "<w:r " in c) for c in self.content)

    def start_link(self, tag: str):
        self.links.append((len(self.content), tag))

    def end_link(self):
        if not self.links:
            return
        start, tag = self.links.pop()
        inner = "".join(self.content[start:])
        del self.content[start:]
        if inner:
            self.content.append(f"{tag}{inner}</w:hyperlink>")

    def to_xml(self) -> str:
        while self.links:
            self.end_link()
        ppr = []
        if self.style:
            ppr.append(f'<w:pStyle w:val="{self.style}"/>')
        if self.keep_next:
            ppr.append("<w:keepNext/>")
        if self.page_break_before:
            ppr.append("<w:pageBreakBefore/>")
        if self.num:
            ppr.append(f'<w:numPr><w:ilvl w:val="{self.num[1]}"/><w:numId w:val="{self.num[0]}"/></w:numPr>')
        if self.spacing:
            ppr.append(self.spacing)
        if self.indent or self.hanging:
            hang = f' w:hanging="{self.hanging}"' if self.hanging else ""
            ppr.append(f'<w:ind w:left="{self.indent}"{hang}/>')
        if self.jc:
            ppr.append(f'<w:jc w:val="{self.jc}"/>')
        ppr_xml = f"<w:pPr>{''.join(ppr)}</w:pPr>" if ppr else ""
        content = "".join(self.content)
        if "<m:oMath>" in content and "<m:oMathPara" not in content and "<w:t" not in content:
            # Word shows an equation that is alone in its paragraph as a centred display equation. A zero-width
            # space keeps inline math (e.g. a number in a table cell) inline.
            content += '<w:r><w:t>​</w:t></w:r>'
        return f"<w:p>{ppr_xml}{content}</w:p>"


class XrefTarget:
    """Something a Word REF field can point at: a caption or equation number, or a heading."""

    def __init__(self, kind: str, bookmark: str, number: Optional[Tuple[int, ...]] = None, figtype: str = "",
                 text: str = ""):
        self.kind = kind              # "number" (figure, table, code-block, equation) or "section"
        self.bookmark = bookmark      # hidden Word bookmark (_Ref...) around the number or the heading text
        self.number = number
        self.figtype = figtype
        self.text = text              # heading text, for sections
        self.word_number: Optional[Tuple[int, ...]] = None   # the number Word gives it, if Word numbers captions
        self.label_bookmark = ""      # bookmark around "Figure 3" (label and number), as Word's own captions

    @property
    def number_text(self) -> str:
        """Sphinx's number, as in the reference texts Sphinx wrote."""
        return ".".join(map(str, self.number)) if self.number else ""

    @property
    def shown_number(self) -> Tuple[int, ...]:
        """The number shown in the Word document."""
        return self.word_number or self.number or ()

    @property
    def shown_text(self) -> str:
        return ".".join(map(str, self.shown_number))


class ListState:
    def __init__(self, num_id: int, level: int):
        self.num_id = num_id
        self.level = level
        self.first_paragraph = False


# ----------------------------------------------------------------------------------------------------------------------
#   Translator
# ----------------------------------------------------------------------------------------------------------------------

class WordTranslator(nodes.NodeVisitor):

    def __init__(self, document: nodes.document, builder, package: DocxPackage):
        super().__init__(document)
        self.builder = builder
        self.config = builder.config
        self.env = builder.env
        self.pkg = package

        self.blocks_stack: List[List[str]] = [[]]
        self.para: Optional[Paragraph] = None
        self.para_style_stack: List[Optional[str]] = [None]
        self.indent_stack: List[int] = [0]
        self.width_stack: List[int] = [package.text_width_twips]
        self.lists: List[ListState] = []
        self.fmt_stack: List[Dict[str, Any]] = [{}]
        self.literal_depth = 0

        self.section_level = 0
        self.title_mode = False                 # the master document has a single root section used as the title
        self.title_page_done = False
        self.docname_stack: List[str] = [self.config.master_doc]
        self.pending_ids: List[str] = []
        self.bookmark_names: Dict[str, str] = {}
        self.bookmarks_emitted: set = set()
        self.bookmark_counter = 0
        self.drawing_counter = 0
        self.footnote_ids: Dict[str, int] = {}
        self.pending_footnote_ref = False
        self.pending_prefix: List[str] = []     # runs to insert at the start of the next paragraph
        self.pending_hanging = 0                # hanging indent of the next paragraph (bibliography entries)
        self.param_first: List[bool] = []
        self.unknown_nodes: set = set()
        self.node_ids: Dict[str, nodes.Element] = {}
        self.math_errors = 0
        self.pending_xe: List[str] = []          # index entries (XE fields) for the next paragraph
        self.index_entries = 0
        self.pending_page_break = False          # the next paragraph or block starts a new page
        self.landscape_node: Optional[nodes.Element] = None

        # Word fields for captions and cross-references
        self.xref_targets: Dict[str, XrefTarget] = {}        # node id -> target
        self.element_targets: Dict[int, XrefTarget] = {}     # id(element) -> target
        self.ref_bookmark_counter = 0
        self.seq_counts: Dict[str, int] = {}                 # simulated values of Word's SEQ fields
        self.seq_reset_level: Dict[str, int] = {}
        self.heading_counts = [0] * 9                        # simulated Word heading numbers
        self.heading_mismatch_warned = False
        self.heading_bookmark_ends: List[str] = []
        # Default labels in the project's language (word_translate_labels), then the user's caption labels
        self.labels = default_labels(self.config.language, bool(self.config.word_translate_labels), _)
        labels = {key: self.labels[key] for key in ("figure", "table", "code-block")}
        labels["displaymath"] = "Equation"          # only the name of the SEQ field; the number shows as (1)
        labels.update(getattr(self.config, "word_caption_labels", None) or {})
        self.caption_labels = labels
        self.in_appendix = False
        # Entries of the prefilled contents and lists (see add_toc_field)
        self.toc_fields: List[Tuple[str, str, str]] = []          # (instruction, what, "contents" or caption type)
        self.toc_entries: List[Tuple[int, str, str, list, str]] = []   # level, number, separator, pieces, anchor
        self.caption_entries: Dict[str, List[Tuple[str, list, str]]] = {}   # type -> (prefix, pieces, anchor)
        self.appendix_counts = [0, 0, 0]
        self.module_targets: Dict[str, str] = {}             # node id of a Python module -> module name
        self.module_entries = 0

        macros = {}
        mathjax_cfg = getattr(self.config, "mathjax3_config", None) or {}
        if isinstance(mathjax_cfg, dict):
            macros.update(parse_mathjax_macros(mathjax_cfg.get("tex", {}).get("macros", {})))
        macros.update(parse_mathjax_macros(self.config.word_math_macros or {}))
        self.math_macros = macros

    # ================================================================================================= utilities
    def label(self, setting: str, key: str) -> str:
        """The text of a label setting: translated if it was left at its English default (word_translate_labels)."""
        value = getattr(self.config, setting)
        if value == ENGLISH.get(key):
            return self.labels[key]
        return value

    @property
    def blocks(self) -> List[str]:
        return self.blocks_stack[-1]

    @property
    def docname(self) -> str:
        return self.docname_stack[-1]

    def body_xml(self) -> str:
        self.close_paragraph()
        return "".join(self.blocks_stack[0])

    def current_indent(self) -> int:
        indent = self.indent_stack[-1]
        if self.lists:
            indent += list_indent(self.lists[-1].level)
        return indent

    def available_width(self) -> int:
        """Usable width in twips at the current position."""
        return max(self.width_stack[-1] - self.current_indent(), 1440)

    def add_block(self, xml: str):
        self.close_paragraph()
        if self.pending_page_break:
            # a block that is not a paragraph (a table) after a page break: a tiny paragraph starts the page
            self.pending_page_break = False
            self.blocks.append('<w:p><w:pPr><w:pageBreakBefore/><w:spacing w:before="0" w:after="0" '
                               'w:line="20" w:lineRule="exact"/></w:pPr></w:p>')
        self.blocks.append(xml)

    # ------------------------------------------------------------------------------------------------ paragraphs
    def open_paragraph(self, style: Optional[str] = None, **kwargs) -> Paragraph:
        self.close_paragraph()
        if style is None:
            style = self.para_style_stack[-1]
        if "indent" not in kwargs:
            kwargs["indent"] = self.current_indent()
        # List numbering on the first paragraph of a list item
        if self.lists and self.lists[-1].first_paragraph and "num" not in kwargs:
            lst = self.lists[-1]
            lst.first_paragraph = False
            kwargs["num"] = (lst.num_id, lst.level)
            kwargs["indent"] = list_indent(lst.level) + self.indent_stack[-1]
            kwargs["hanging"] = 360
            if style is None:
                style = "ListParagraph"
        elif self.lists and style is None:
            style = "ListParagraph"
        if self.pending_hanging and "hanging" not in kwargs:
            kwargs["hanging"] = self.pending_hanging      # first paragraph of a bibliography entry
            self.pending_hanging = 0
        if self.pending_page_break:
            self.pending_page_break = False
            kwargs["page_break_before"] = True
        self.para = Paragraph(style=style, **kwargs)
        self.flush_pending_ids()
        if self.pending_xe:
            for xml in self.pending_xe:
                self.para.add(xml)
            self.pending_xe = []
        if self.pending_footnote_ref:
            self.pending_footnote_ref = False
            self.para.add('<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteRef/></w:r>'
                          '<w:r><w:t xml:space="preserve"> </w:t></w:r>')
        if self.pending_prefix:
            for xml in self.pending_prefix:
                self.para.add(xml)
            self.pending_prefix = []
        return self.para

    def ensure_paragraph(self) -> Paragraph:
        if self.para is None:
            self.open_paragraph()
        return self.para

    def close_paragraph(self):
        if self.para is not None:
            para = self.para
            self.para = None
            self.blocks.append(para.to_xml())

    # ------------------------------------------------------------------------------------------------- bookmarks
    def bookmark_name(self, node_id: str) -> str:
        if node_id not in self.bookmark_names:
            name = re.sub(r"[^A-Za-z0-9_]", "_", node_id)
            if not name or not name[0].isalpha():
                name = "b_" + name
            name = name[:36]
            existing = set(self.bookmark_names.values())
            base, k = name, 1
            while name in existing:
                k += 1
                name = f"{base[:33]}_{k}"
            self.bookmark_names[node_id] = name
        return self.bookmark_names[node_id]

    def bookmark_xml(self, node_id: str) -> str:
        name = self.bookmark_name(node_id)
        if name in self.bookmarks_emitted:
            return ""
        self.bookmarks_emitted.add(name)
        self.bookmark_counter += 1
        bid = self.bookmark_counter
        return f'<w:bookmarkStart w:id="{bid}" w:name="{name}"/><w:bookmarkEnd w:id="{bid}"/>'

    def flush_pending_ids(self):
        if self.para is None or not self.pending_ids:
            return
        for node_id in self.pending_ids:
            self.para.add(self.bookmark_xml(node_id))
        self.pending_ids = []

    def take_ids(self, node: nodes.Element):
        self.pending_ids.extend(node.get("ids", []))

    # ------------------------------------------------------------------------------------------------ Word fields
    def new_ref_bookmark(self) -> str:
        """A hidden bookmark name in the style Word uses for its own cross-references."""
        self.ref_bookmark_counter += 1
        return f"_Ref{900000000 + self.ref_bookmark_counter}"

    def bookmark_start(self, name: str) -> str:
        self.bookmark_counter += 1
        self.bookmarks_emitted.add(name)
        return f'<w:bookmarkStart w:id="{self.bookmark_counter}" w:name="{name}"/>'

    def bookmark_span(self, name: str) -> Tuple[str, str]:
        start = self.bookmark_start(name)
        return start, f'<w:bookmarkEnd w:id="{self.bookmark_counter}"/>'

    def field_xml(self, instr: str, result: str, extra: Optional[Dict[str, Any]] = None) -> str:
        """A complex field with a cached result, so the document reads correctly before fields are updated."""
        rpr = self.run_properties(extra)
        return (f'<w:r>{rpr}<w:fldChar w:fldCharType="begin"/></w:r>'
                f'<w:r>{rpr}<w:instrText xml:space="preserve"> {xml_text(instr)} </w:instrText></w:r>'
                f'<w:r>{rpr}<w:fldChar w:fldCharType="separate"/></w:r>'
                f'<w:r>{rpr}<w:t xml:space="preserve">{xml_text(result)}</w:t></w:r>'
                f'<w:r>{rpr}<w:fldChar w:fldCharType="end"/></w:r>')

    def number_fields_xml(self, target: XrefTarget, extra: Optional[Dict[str, Any]] = None) -> str:
        """``{STYLEREF k \\s}.{SEQ Label \\s k}`` (or a plain SEQ field), bookmarked for REF fields.

        Word counts SEQ fields itself when fields are updated. The count is simulated here, and where Word would
        give a different number from Sphinx (for example equations that restart in every file) the field gets a
        ``\\r`` switch that sets the number.
        """
        number = target.shown_number
        label = self.seq_name(target.figtype)
        chapter = number[:-1]
        depth = len(chapter)
        parts = []
        if depth:
            if self.pkg.heading_num_id is not None:
                parts.append(self.field_xml(f"STYLEREF {depth} \\s", ".".join(map(str, chapter)), extra))
            else:
                parts.append(self.run_xml(".".join(map(str, chapter)), extra))
            parts.append(self.run_xml(".", extra))
        count = self.seq_counts.get(label, 0) + 1
        instr = f"SEQ {label} \\* ARABIC"
        if depth and self.pkg.heading_num_id is not None:
            instr += f" \\s {depth}"
            self.seq_reset_level[label] = depth
        else:
            self.seq_reset_level.pop(label, None)
        if count != number[-1]:
            instr += f" \\r {number[-1]}"
            count = number[-1]
        self.seq_counts[label] = count
        parts.append(self.field_xml(instr, str(number[-1]), extra))
        start, end = self.bookmark_span(target.bookmark)
        return start + "".join(parts) + end

    def caption_label(self, figtype: str) -> str:
        return self.caption_labels.get(figtype, figtype.title())

    def seq_name(self, figtype: str) -> str:
        """The SEQ field identifier of a caption label (Word allows letters, digits and underscores)."""
        return re.sub(r"\W", "_", self.caption_label(figtype)) or "Figure"

    @property
    def word_numbers_captions(self) -> bool:
        return str(self.config.word_caption_numbering).lower() != "sphinx"

    def heading_started(self, level: int, number: Optional[Tuple[int, ...]], location: nodes.Node):
        """Follow Word's numbering of headings and SEQ fields, and warn if Word would number a heading differently."""
        for label, reset in self.seq_reset_level.items():
            if level <= reset:
                self.seq_counts[label] = 0
        if self.pkg.heading_num_id is None or not number:
            return
        self.heading_counts[level - 1] += 1
        for i in range(level, 9):
            self.heading_counts[i] = 0
        word = tuple(self.heading_counts[:level])
        if word != tuple(number) and not self.heading_mismatch_warned:
            self.heading_mismatch_warned = True
            logger.warning("sphinx2word: Word will number this heading %s, Sphinx numbers it %s; captions and "
                           "cross-references follow Word's numbers when fields are updated",
                           ".".join(map(str, word)), ".".join(map(str, number)), location=location)

    def collect_targets(self, document: nodes.document):
        """Find every numbered figure, table, code block, equation and section before rendering starts."""
        env = self.env
        fignumbers = getattr(env, "toc_fignumbers", {})
        math_numfig = bool(self.config.math_numfig and self.config.numfig)

        word_counts: Dict[str, int] = {}

        def add(element, target):
            if target.kind == "number" and self.word_numbers_captions:
                # Word's default caption numbering: Figure 1, Figure 2, ... through the whole document
                label = self.seq_name(target.figtype)
                word_counts[label] = word_counts.get(label, 0) + 1
                target.word_number = (word_counts[label],)
                target.label_bookmark = self.new_ref_bookmark()
            self.element_targets[id(element)] = target
            for node_id in element.get("ids", []):
                self.xref_targets.setdefault(node_id, target)

        def walk(node, docname, top_section_seen):
            for child in node.children:
                if not isinstance(child, nodes.Element):
                    continue
                if isinstance(child, addnodes.start_of_file):
                    walk(child, child["docname"], [False])
                    continue
                ids = child.get("ids", [])
                figtype = None
                if isinstance(child, nodes.figure):
                    figtype = "figure"
                elif isinstance(child, nodes.table):
                    figtype = "table"
                elif isinstance(child, nodes.container) and child.get("literal_block"):
                    figtype = "code-block"
                if figtype and ids and self.config.numfig:
                    number = fignumbers.get(docname, {}).get(figtype, {}).get(ids[0])
                    if number:
                        add(child, XrefTarget("number", self.new_ref_bookmark(), tuple(number), figtype))
                elif isinstance(child, nodes.math_block) and child.get("number") is not None:
                    number = None
                    if math_numfig and ids:
                        number = fignumbers.get(docname, {}).get("displaymath", {}).get(ids[0])
                    if not number:
                        try:
                            number = (int(child["number"]),)
                        except (TypeError, ValueError):
                            number = None
                    if number:
                        add(child, XrefTarget("number", self.new_ref_bookmark(), tuple(number), "displaymath"))
                elif isinstance(child, nodes.section) and child.children and isinstance(child[0], nodes.title):
                    number = self.section_number_tuple(child, docname)
                    target = XrefTarget("section", self.new_ref_bookmark(), number or None, "section",
                                        child[0].astext())
                    add(child, target)
                    if not top_section_seen[0]:
                        top_section_seen[0] = True
                        self.xref_targets.setdefault("document-" + docname, target)
                walk(child, docname, top_section_seen)

        walk(document, self.config.master_doc, [False])

    # ----------------------------------------------------------------------------------------------------- runs
    def run_properties(self, extra: Optional[Dict[str, Any]] = None) -> str:
        fmt: Dict[str, Any] = {}
        for f in self.fmt_stack:
            fmt.update(f)
        if extra:
            fmt.update(extra)
        props = []
        if fmt.get("code"):
            props.append('<w:rStyle w:val="SpxCodeInline"/>')
        elif fmt.get("rstyle"):
            props.append(f'<w:rStyle w:val="{fmt["rstyle"]}"/>')
        if fmt.get("bold"):
            props.append("<w:b/><w:bCs/>")
        if fmt.get("italic"):
            props.append("<w:i/><w:iCs/>")
        if fmt.get("strike"):
            props.append("<w:strike/>")
        if fmt.get("color"):
            props.append(f'<w:color w:val="{fmt["color"]}"/>')
        if fmt.get("size"):
            props.append(f'<w:sz w:val="{fmt["size"]}"/><w:szCs w:val="{fmt["size"]}"/>')
        if fmt.get("underline"):
            props.append('<w:u w:val="single"/>')
        if fmt.get("shade"):        # the order of these elements is fixed by the schema: shd before vertAlign
            props.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{fmt["shade"]}"/>')
        if fmt.get("vert"):
            props.append(f'<w:vertAlign w:val="{fmt["vert"]}"/>')
        return f"<w:rPr>{''.join(props)}</w:rPr>" if props else ""

    def run_xml(self, text: str, extra: Optional[Dict[str, Any]] = None) -> str:
        rpr = self.run_properties(extra)
        parts = []
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if i > 0:
                parts.append("<w:br/>")
            segs = line.split("\t")
            for j, seg in enumerate(segs):
                if j > 0:
                    parts.append("<w:tab/>")
                if seg:
                    parts.append(f'<w:t xml:space="preserve">{xml_text(seg)}</w:t>')
        if not parts:
            return ""
        return f"<w:r>{rpr}{''.join(parts)}</w:r>"

    def add_text(self, text: str, extra: Optional[Dict[str, Any]] = None):
        if not text:
            return
        self.ensure_paragraph().add(self.run_xml(text, extra))

    def push_fmt(self, **fmt):
        self.fmt_stack.append(fmt)

    def pop_fmt(self, node=None):
        self.fmt_stack.pop()

    # --------------------------------------------------------------------------------------------- sub-rendering
    def render_blocks(self, children, width: Optional[int] = None, para_style: Optional[str] = None,
                      reset_indent: bool = True) -> List[str]:
        """Render a list of nodes into a separate block list (for table cells, admonitions, footnotes)."""
        # The open paragraph (if any) is kept, not closed: a footnote is rendered from inside its paragraph.
        saved = (self.para, self.lists, self.pending_prefix)
        self.para = None
        self.lists = []
        self.pending_prefix = []
        self.blocks_stack.append([])
        self.para_style_stack.append(para_style)
        self.indent_stack.append(0 if reset_indent else self.indent_stack[-1])
        self.width_stack.append(width if width is not None else self.width_stack[-1])
        try:
            for child in children:
                child.walkabout(self)
            self.close_paragraph()
        finally:
            self.width_stack.pop()
            self.indent_stack.pop()
            self.para_style_stack.pop()
            blocks = self.blocks_stack.pop()
            self.para, self.lists, self.pending_prefix = saved
        return blocks

    # ========================================================================================== document structure
    def visit_document(self, node):
        # document.ids only knows the master file; the included files bring their own ids.
        self.node_ids = {}
        for element in find_all(node, nodes.Element):
            for node_id in element.get("ids", []):
                self.node_ids.setdefault(node_id, element)
        sections = [c for c in node.children if isinstance(c, nodes.section)]
        self.title_mode = len(sections) == 1
        if any(getattr(self.env, "toc_secnumbers", {}).values()):
            self.pkg.number_headings()
        self.collect_targets(node)
        self.collect_modules()

    def depart_document(self, node):
        self.close_paragraph()
        self.write_index()
        self.close_paragraph()
        self.fill_toc_fields()
        if self.unknown_nodes:
            logger.info("sphinx2word: rendered these node types generically: %s",
                        ", ".join(sorted(self.unknown_nodes)))

    def visit_start_of_file(self, node):
        if node.get("word_appendix"):
            self.in_appendix = True         # the appendices come last (word_appendices)
        self.docname_stack.append(node["docname"])
        self.pending_ids.append("document-" + node["docname"])

    def depart_start_of_file(self, node):
        self.docname_stack.pop()

    def visit_section(self, node):
        self.section_level += 1
        self.take_ids(node)

    def depart_section(self, node):
        self.section_level -= 1

    def heading_level(self) -> int:
        """0 for the document title, 1.. for headings."""
        return self.section_level - 1 if self.title_mode else self.section_level

    def section_number_tuple(self, section: nodes.section, docname: str) -> Tuple[int, ...]:
        secnums = getattr(self.env, "toc_secnumbers", {}).get(docname, {})
        if not secnums or not section.get("ids"):
            return ()
        number = secnums.get("#" + section["ids"][0])
        if number is None and isinstance(section.parent, (addnodes.start_of_file, nodes.document)):
            number = secnums.get("")          # the top section of each document uses the empty anchor
        return tuple(number or ())

    def visit_title(self, node):
        parent = node.parent
        if isinstance(parent, nodes.section):
            level = self.heading_level()
            if level <= 0 and not self.title_page_done and self.config.word_title_page:
                self.write_title_page(node)
                raise nodes.SkipNode
            level = max(level, 1)
            style = f"Heading{min(level, 9)}"
            page_break = level == 1 and self.config.word_chapter_page_break and self.title_page_done
            target = self.element_targets.get(id(parent))
            number = self.section_number_tuple(parent, self.docname)
            kwargs = {}
            if self.in_appendix:
                # Appendices: "Appendix A:", A.1, A.1.1 from their own numbering, set on the paragraph
                number = ()
                word_numbered = False
                if level <= 3:
                    appendix_num = self.pkg.number_appendices(self.label("word_appendix_label", "appendix"))
                    kwargs["num"] = (appendix_num, level - 1)
                elif self.pkg.heading_num_id is not None:
                    kwargs["num"] = (0, 0)
            else:
                word_numbered = self.pkg.heading_num_id is not None and len(number) == level <= 9
            if self.pkg.heading_num_id is not None and not word_numbered and "num" not in kwargs:
                kwargs["num"] = (0, 0)               # the heading style is numbered; this heading is not
            self.open_paragraph(style=style, indent=0, page_break_before=page_break, **kwargs)
            self.heading_started(min(level, 9), number if word_numbered else None, node)
            self.record_toc_entry(level, number, word_numbered, node, target)
            if number and not word_numbered:
                self.add_text(".".join(map(str, number)) + "\u2003")
            if target is not None:
                start, end = self.bookmark_span(target.bookmark)
                self.para.add(start)
                self.heading_bookmark_ends.append(end)
            else:
                self.heading_bookmark_ends.append("")
        elif isinstance(parent, nodes.table):
            raise nodes.SkipNode          # handled by visit_table
        elif isinstance(parent, (nodes.Admonition, nodes.topic, nodes.sidebar)):
            self.open_paragraph(style="SpxAdmonitionTitle")
        else:
            self.open_paragraph(style="SpxRubric")

    def record_toc_entry(self, level: int, number: Tuple[int, ...], word_numbered: bool, title: nodes.Element,
                         target: Optional[XrefTarget]):
        """Note a heading for the prefilled table of contents, with the number Word will show for it."""
        pieces = self.inline_pieces(title)
        separator = "tab"
        if self.in_appendix and level <= 3:
            self.appendix_counts[level - 1] += 1
            for i in range(level, 3):
                self.appendix_counts[i] = 0
            letter = chr(ord("A") + self.appendix_counts[0] - 1) if 0 < self.appendix_counts[0] <= 26 else "?"
            if level == 1:
                shown, separator = f'{self.label("word_appendix_label", "appendix")} {letter}:', "space"
            else:
                shown = ".".join([letter] + [str(n) for n in self.appendix_counts[1:level]])
        elif word_numbered:
            shown = ".".join(map(str, self.heading_counts[:level]))
        elif number:
            shown, separator = ".".join(map(str, number)) + " ", "none"     # the number is part of the text
            pieces = [(shown, {})] + pieces
            shown = ""
        else:
            shown = ""
        self.toc_entries.append((level, shown, separator, pieces, target.bookmark if target is not None else ""))

    def depart_title(self, node):
        if isinstance(node.parent, nodes.section) and self.heading_bookmark_ends:
            end = self.heading_bookmark_ends.pop()
            if end and self.para is not None:
                self.para.add(end)
        self.close_paragraph()

    def write_title_page(self, node):
        self.title_page_done = True
        footer = self.config.word_footer_text
        if footer is None and self.config.word_contract:
            footer = self.lines(self.config.word_contract)[0]
        self.pkg.footer_text = footer or ""
        if self.is_report:
            self.write_report_cover(node)
        else:
            self.open_paragraph(style="Title", indent=0)
            for child in node.children:
                child.walkabout(self)
            self.close_paragraph()
            subtitle = []
            if self.config.version:
                subtitle.append(f"Version {self.config.version}")
            if self.config.author:
                subtitle.append(str(self.config.author))
            for line in subtitle:
                self.open_paragraph(style="Subtitle", indent=0)
                self.add_text(line)
                self.close_paragraph()
        if self.config.word_toc:
            depth = int(self.config.word_toc_depth)
            self.add_toc_field(self.label("word_toc_title", "contents"), f'TOC \\o "1-{depth}" \\h \\z \\u',
                               "the table of contents", prefill="contents")
        # Tables of figures, collected by Word from the captions' SEQ fields. Only added if there are captions.
        captioned = {t.figtype for t in self.element_targets.values() if t.kind == "number"}
        for figtype, enabled, title in (("figure", self.config.word_list_of_figures,
                                         self.label("word_list_of_figures_title", "list_of_figures")),
                                        ("table", self.config.word_list_of_tables,
                                         self.label("word_list_of_tables_title", "list_of_tables"))):
            if enabled and figtype in captioned:
                label = re.sub(r"\W", "_", self.caption_labels.get(figtype, figtype.title()))
                self.add_toc_field(title, f'TOC \\h \\z \\c "{label}"', f"the {title.lower()}", prefill=figtype)
        # The body starts on a new page. A section break ends the front matter: it has roman page numbers and the
        # body is numbered from 1.
        self.add_block(FRONT_MATTER_END)

    # ------------------------------------------------------------------------------------------ contract report
    @property
    def is_report(self) -> bool:
        c = self.config
        return any((c.word_contract, c.word_cover_figure, c.word_prepared_by, c.word_reviewed_by,
                    c.word_distribution, c.word_change_record))

    def front_label(self, key: str) -> str:
        labels = dict(FRONT_MATTER_LABELS)
        labels.update(self.config.word_front_matter_labels or {})
        return labels.get(key, key)

    @staticmethod
    def lines(value) -> List[str]:
        if not value:
            return []
        if isinstance(value, str):
            return value.split("\n")
        return [str(v) for v in value]

    def write_report_cover(self, title: nodes.title):
        """Cover page: contract identification, optional figure, document title and the contributor list."""
        for line in self.lines(self.config.word_contract):
            self.open_paragraph(style="SpxCoverTitle", indent=0)
            self.add_text(line)
            self.close_paragraph()
        figure = self.config.word_cover_figure
        if figure:
            path = figure if os.path.isabs(figure) else os.path.join(str(self.builder.confdir), figure)
            if os.path.exists(path):
                image = nodes.image(uri=path, width=self.config.word_cover_figure_width or "")
                drawing = self.image_drawing(path, image)
                if drawing:
                    self.open_paragraph(style="SpxCoverFigure", indent=0)
                    self.para.add(f"<w:r>{drawing}</w:r>")
                    self.close_paragraph()
            else:
                logger.warning("sphinx2word: word_cover_figure not found: %s", path)
        else:
            self.open_paragraph(style="SpxCoverFigure", indent=0)    # space between contract and title
            self.close_paragraph()
        title_lines = self.lines(self.config.word_document_title)
        if title_lines:
            for line in title_lines:
                self.open_paragraph(style="SpxCoverTitle", indent=0)
                self.add_text(line)
                self.close_paragraph()
        else:
            self.open_paragraph(style="SpxCoverTitle", indent=0)
            for child in title.children:
                child.walkabout(self)
            self.close_paragraph()

        prepared = self.config.word_prepared_by or []
        reviewed = self.config.word_reviewed_by or []
        if prepared or reviewed:
            self.front_heading(self.front_label("contributors"))
            for key, people in (("prepared_by", prepared), ("reviewed_by", reviewed)):
                if people:
                    rows = [["", *self.cells(p, 2)] for p in people]
                    self.add_block(self.front_table([self.front_label(key), self.front_label("name"),
                                                     self.front_label("function")], rows, [1, 1, 1]))
                    self.add_block('<w:p><w:pPr><w:spacing w:after="120"/></w:pPr></w:p>')

        distribution = self.config.word_distribution or []
        changes = self.change_record_rows()
        if distribution or changes:
            self.open_paragraph(indent=0)
            self.para.add('<w:r><w:br w:type="page"/></w:r>')
            self.close_paragraph()
            if distribution:
                self.front_heading(self.front_label("distribution"), first=True)
                self.add_block(self.front_table([self.front_label("name"), self.front_label("company")],
                                                [self.cells(p, 2) for p in distribution], [1, 1]))
            if changes:
                self.front_heading(self.front_label("changes"), first=not distribution)
                rows = [[r["issue"], r["revision"], r["date"], r["pages"], r["description"]] for r in changes]
                self.add_block(self.front_table(
                    [self.front_label(k) for k in ("issue", "revision", "date", "pages", "description")],
                    rows, [0.6, 1, 1.1, 1.3, 2.4]))

    @staticmethod
    def cells(entry, n: int) -> List[str]:
        values = [entry] if isinstance(entry, str) else [str(v) for v in entry]
        return (values + [""] * n)[:n]

    def change_record_rows(self) -> List[Dict[str, str]]:
        value = self.config.word_change_record
        if not value:
            return []
        if isinstance(value, str):
            if value.strip().lower() != "git":
                logger.warning("sphinx2word: word_change_record must be 'git' or a list of entries, not %r", value)
                return []
            return change_record_from_git(str(self.env.srcdir), self.config.word_change_record_tags or "*",
                                          self.config.word_change_record_notes or {})
        return normalise_change_record(value)

    def front_heading(self, text: str, first: bool = False):
        spacing = '<w:spacing w:before="0"/>' if first else None
        self.open_paragraph(style="SpxFrontHeading", indent=0, spacing=spacing)
        self.add_text(text)
        self.close_paragraph()

    def front_table(self, header: List[str], rows: List[List[str]], weights: List[float]) -> str:
        """A table in the style of a contract report: bold header with a rule, banded rows, light column lines."""
        width = self.available_width()
        total = sum(weights)
        cols = [int(width * w / total) for w in weights]
        line = '<w:{side} w:val="single" w:sz="4" w:space="0" w:color="A6A6A6"/>'

        def cell(text, w, header_row=False, shade=False):
            borders = "".join(line.format(side=s) for s in ("left", "right")) if not header_row else ""
            if header_row:
                borders += '<w:bottom w:val="single" w:sz="12" w:space="0" w:color="808080"/>'
            else:
                borders += line.format(side="bottom")
            fill = '<w:shd w:val="clear" w:color="auto" w:fill="D9D9D9"/>' if shade else ""
            rpr = "<w:rPr><w:b/><w:bCs/></w:rPr>" if header_row else ""
            run = f'<w:r>{rpr}<w:t xml:space="preserve">{xml_text(text)}</w:t></w:r>' if text else ""
            return (f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:tcBorders>{borders}</w:tcBorders>{fill}'
                    f'</w:tcPr><w:p><w:pPr><w:pStyle w:val="SpxFrontTableText"/></w:pPr>{run}</w:p></w:tc>')

        xml = [f'<w:tbl><w:tblPr><w:tblW w:w="{width}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
               '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
               '<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
               '<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" '
               'w:noHBand="1" w:noVBand="1"/></w:tblPr><w:tblGrid>'
               + "".join(f'<w:gridCol w:w="{w}"/>' for w in cols) + "</w:tblGrid>",
               '<w:tr><w:trPr><w:tblHeader/><w:cantSplit/></w:trPr>'
               + "".join(cell(t, w, header_row=True) for t, w in zip(header, cols)) + "</w:tr>"]
        for i, row in enumerate(rows):
            xml.append("<w:tr><w:trPr><w:cantSplit/></w:trPr>"
                       + "".join(cell(t, w, shade=(i % 2 == 0)) for t, w in zip(row, cols)) + "</w:tr>")
        xml.append("</w:tbl>")
        return "".join(xml)

    def add_toc_field(self, title: str, instr: str, what: str, prefill: Optional[str] = None):
        """A heading on a new page and a TOC field that Word fills in when the document is opened.

        With ``prefill`` ("contents", or a caption type such as "figure"), the field starts out with the entries
        themselves (numbers, titles and links, without page numbers), so the document reads well before Word has
        updated its fields, for example when it was built on Linux. The headings and captions are not known yet:
        a marker is written here and replaced at the end of the document (:meth:`fill_toc_fields`).
        """
        self.open_paragraph(style="TOCHeading", indent=0, page_break_before=True)
        self.add_text(title)
        self.close_paragraph()
        self.pkg.update_fields_on_open = True
        if prefill:
            self.close_paragraph()
            self.toc_fields.append((instr, what, prefill))
            self.blocks.append(TOC_MARKER.format(len(self.toc_fields) - 1))
            return
        self.blocks.append(self.toc_field_xml(instr, what, []))

    def toc_field_xml(self, instr: str, what: str, entries: List[Tuple[str, str, str]]) -> str:
        """The paragraphs of a TOC field: its entries (style, tabs, runs) as the field result, or a placeholder.

        The field is not marked dirty: a dirty field makes Word update every field when the file is opened, which
        is for ``word_update_fields`` (the updateFields setting) to decide. Prefilled entries are shown as they
        are, and Word adds the page numbers when the fields are updated (the prompt, Ctrl+A F9, or printing).
        """
        begin = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
                 f'<w:r><w:instrText xml:space="preserve"> {xml_text(instr)} </w:instrText></w:r>'
                 '<w:r><w:fldChar w:fldCharType="separate"/></w:r>')
        end = '<w:r><w:fldChar w:fldCharType="end"/></w:r>'
        if not entries:
            text = self.run_xml(f"Right-click here and choose Update Field to build {what}.",
                                {"italic": True, "color": "7F7F7F"})
            return f"<w:p>{begin}{text}{end}</w:p>"
        paragraphs = []
        for i, (style, tabs, runs) in enumerate(entries):
            first = begin if i == 0 else ""
            last = end if i == len(entries) - 1 else ""
            paragraphs.append(f'<w:p><w:pPr><w:pStyle w:val="{style}"/>{tabs}</w:pPr>{first}{runs}{last}</w:p>')
        return "".join(paragraphs)

    def pieces_xml(self, pieces: List[Tuple[str, Dict[str, Any]]]) -> str:
        return "".join(self.run_xml(text, fmt) for text, fmt in pieces)

    def fill_toc_fields(self):
        """Replace the markers of the prefilled TOC fields with the fields and their entries."""
        if not self.toc_fields:
            return
        depth = int(self.config.word_toc_depth)
        results = []
        for instr, what, kind in self.toc_fields:
            entries = []
            if kind == "contents":
                for level, number, separator, pieces, anchor in self.toc_entries:
                    if level > depth:
                        continue
                    style = f"TOC{min(level, 6)}"
                    runs = ""
                    tabs = ""
                    if number:
                        runs = self.run_xml(number)
                        if separator == "tab":
                            runs += "<w:r><w:tab/></w:r>"
                            tabs = f'<w:tabs><w:tab w:val="left" w:pos="{440 * level}"/></w:tabs>'
                        else:
                            runs += self.run_xml(" ")
                    runs += self.pieces_xml(pieces)
                    if anchor:
                        runs = f'<w:hyperlink w:anchor="{anchor}" w:history="1">{runs}</w:hyperlink>'
                    entries.append((style, tabs, runs))
            else:
                for prefix, pieces, anchor in self.caption_entries.get(kind, []):
                    runs = self.run_xml(prefix) + self.pieces_xml(pieces)
                    if anchor:
                        runs = f'<w:hyperlink w:anchor="{anchor}" w:history="1">{runs}</w:hyperlink>'
                    entries.append(("TableofFigures", "", runs))
            results.append(self.toc_field_xml(instr, what, entries))
        blocks = self.blocks_stack[0]
        for i, block in enumerate(blocks):
            m = TOC_MARKER_RE.fullmatch(block)
            if m:
                blocks[i] = results[int(m.group(1))]

    def inline_pieces(self, node: nodes.Node) -> List[Tuple[str, Dict[str, Any]]]:
        """The text of a heading or caption as (text, format) pieces, for the entries of the lists: emphasis,
        strong text and simple math (with its sub- and superscripts) keep their format."""
        pieces: List[Tuple[str, Dict[str, Any]]] = []

        def walk(n: nodes.Node, fmt: Dict[str, Any]):
            if isinstance(n, nodes.Text):
                pieces.append((n.astext().replace("\n", " "), fmt))
            elif isinstance(n, nodes.math):
                latex = n.astext()
                try:
                    text = omml_as_text(latex_to_omml(latex, False, self.math_macros))
                except (LatexMathError, RecursionError, IndexError):
                    text = None
                pieces.extend([(t, {**fmt, **f}) for t, f in text] if text else [(latex, fmt)])
            elif isinstance(n, (nodes.footnote_reference, nodes.citation_reference, nodes.target, addnodes.index,
                                nodes.system_message)):
                return
            else:
                extra = {"italic": True} if isinstance(n, nodes.emphasis) else (
                    {"bold": True} if isinstance(n, nodes.strong) else {})
                if isinstance(n, nodes.subscript):
                    extra = {"vert": "subscript"}
                elif isinstance(n, nodes.superscript):
                    extra = {"vert": "superscript"}
                for child in n.children:
                    walk(child, {**fmt, **extra})

        walk(node, {})
        return [(t, f) for t, f in pieces if t]

    def visit_subtitle(self, node):
        self.open_paragraph(style="Subtitle", indent=0)

    def depart_subtitle(self, node):
        self.close_paragraph()

    def visit_rubric(self, node):
        self.take_ids(node)
        self.open_paragraph(style="SpxRubric")

    def depart_rubric(self, node):
        self.close_paragraph()

    def visit_paragraph(self, node):
        self.take_ids(node)
        self.open_paragraph()

    def depart_paragraph(self, node):
        self.close_paragraph()

    def visit_compact_paragraph(self, node):
        self.visit_paragraph(node)

    def depart_compact_paragraph(self, node):
        self.close_paragraph()

    def visit_transition(self, node):
        self.add_block('<w:p><w:pPr><w:pBdr><w:bottom w:val="single" w:sz="6" w:space="1" w:color="A6A6A6"/>'
                       '</w:pBdr></w:pPr></w:p>')
        raise nodes.SkipNode

    # ===================================================================================================== text
    def visit_Text(self, node):
        text = node.astext()
        if not self.literal_depth:
            text = re.sub(r"\s*\n\s*", " ", text)
            if self.para is None and not text.strip():
                return
        self.add_text(text)

    def depart_Text(self, node):
        pass

    # ------------------------------------------------------------------------------------------- inline markup
    def visit_emphasis(self, node):
        self.push_fmt(italic=True)

    depart_emphasis = pop_fmt

    def visit_strong(self, node):
        self.push_fmt(bold=True)

    depart_strong = pop_fmt

    def visit_literal(self, node):
        self.push_fmt(code=True)

    depart_literal = pop_fmt

    def visit_literal_emphasis(self, node):
        self.push_fmt(code=True, italic=True)

    depart_literal_emphasis = pop_fmt

    def visit_literal_strong(self, node):
        self.push_fmt(code=True, bold=True)

    depart_literal_strong = pop_fmt

    def visit_title_reference(self, node):
        self.push_fmt(italic=True)

    depart_title_reference = pop_fmt

    def visit_subscript(self, node):
        self.push_fmt(vert="subscript")

    depart_subscript = pop_fmt

    def visit_superscript(self, node):
        self.push_fmt(vert="superscript")

    depart_superscript = pop_fmt

    def visit_abbreviation(self, node):
        self.push_fmt()

    def depart_abbreviation(self, node):
        self.pop_fmt()
        if node.get("explanation"):
            self.add_text(f" ({node['explanation']})")

    def visit_inline(self, node):
        classes = node.get("classes", [])
        if "viewcode-link" in classes:
            raise nodes.SkipNode
        fmt = {}
        for cls in classes:
            if cls in CLASS_COLOURS:
                fmt["color"] = CLASS_COLOURS[cls]
            elif cls in ("strike", "del", "s"):
                fmt["strike"] = True
            elif cls in ("bold", "b"):
                fmt["bold"] = True
            elif cls in ("italic", "i", "guilabel", "menuselection"):
                fmt["italic"] = True
        if node.get("ids") and self.para is not None:
            for node_id in node["ids"]:
                self.para.add(self.bookmark_xml(node_id))
        self.push_fmt(**fmt)

    depart_inline = pop_fmt

    def visit_problematic(self, node):
        self.push_fmt(color="C00000")

    depart_problematic = pop_fmt

    def visit_generated(self, node):
        pass

    def depart_generated(self, node):
        pass

    # ---------------------------------------------------------------------------------------------- references
    def visit_reference(self, node):
        para = self.ensure_paragraph()
        refuri = node.get("refuri", "")
        refid = node.get("refid")
        if refid:
            anchor = refid
        elif refuri.startswith("#") or ("#" in refuri and "://" not in refuri):
            anchor = refuri.rsplit("#", 1)[1]
        elif refuri.startswith("#document-") or (refuri and "://" not in refuri and not refuri.startswith("mailto:")
                                                 and refuri in self.env.all_docs):
            anchor = "document-" + refuri.lstrip("#").replace("document-", "", 1)
        else:
            anchor = None
        if anchor and self.add_ref_field(node, anchor):
            raise nodes.SkipNode
        if anchor:
            para.start_link(f'<w:hyperlink w:anchor={quoteattr(self.bookmark_name(anchor))} w:history="1">')
        elif refuri:
            rid = self.pkg.add_hyperlink(refuri)
            para.start_link(f'<w:hyperlink r:id="{rid}" w:history="1">')
        else:
            para.start_link("")
        self.push_fmt(rstyle="Hyperlink" if (refuri and not anchor) else None)

    def add_ref_field(self, node: nodes.Element, anchor: str) -> bool:
        """Write a reference to a numbered item or a heading as a Word REF field; False if it is not one.

        ``:numref:`` and ``:eq:`` texts such as "Fig. 3.1" or "(2.4)" become "Fig. " + {REF _Ref... \\h}, so only
        the number is a field and the words around it are the ones Sphinx produced. A ``:ref:`` or ``:doc:`` whose
        text is the heading's title becomes {REF _Ref... \\h} to the heading text, and a ``:numref:`` to a numbered
        heading becomes {REF _Ref... \\w \\h}, its paragraph number.
        """
        target = self.xref_targets.get(anchor)
        if target is None:
            return False
        if any(isinstance(n, (nodes.image, nodes.math, nodes.footnote_reference)) for n in find_all(node, nodes.Node)
               if n is not node):
            return False
        text = node.astext()
        if target.kind == "number":
            number = target.number_text
            fmt = self.config.numfig_format.get(target.figtype, "") if target.figtype != "displaymath" else ""
            try:
                default_text = fmt % number if "%s" in fmt else None
            except TypeError:
                default_text = None
            if target.label_bookmark and default_text and text.strip() == default_text.strip():
                # "Fig. 4.1" written by Sphinx becomes Word's "Figure 7" (label and number, as in the caption)
                before, after = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
                instr = f"REF {target.label_bookmark} \\h"
                result = f"{self.caption_label(target.figtype)} {target.shown_text}"
            elif text.count(number) == 1:
                before, _, after = text.partition(number)
                instr, result = f"REF {target.bookmark} \\h", target.shown_text
            else:
                return False
        else:
            if text.strip() == target.text.strip():
                before, after = text[:len(text) - len(text.lstrip())], text[len(text.rstrip()):]
                instr, result = f"REF {target.bookmark} \\h", target.text.strip()
            elif target.number and self.pkg.heading_num_id is not None and text.count(target.number_text) == 1:
                before, _, after = text.partition(target.number_text)
                instr, result = f"REF {target.bookmark} \\w \\h", target.number_text
            else:
                return False
        # CHARFORMAT: the updated result takes the formatting of the field code (the surrounding text), not of
        # the bookmarked caption label, which is bold.
        instr += " \\* CHARFORMAT"
        self.add_text(before)
        self.ensure_paragraph().add(self.field_xml(instr, result))
        self.add_text(after)
        return True

    def depart_reference(self, node):
        self.pop_fmt()
        if self.para is not None:
            if self.para.links and self.para.links[-1][1] == "":
                self.para.links.pop()
            else:
                self.para.end_link()

    def visit_number_reference(self, node):
        self.visit_reference(node)

    depart_number_reference = depart_reference

    def visit_download_reference(self, node):
        pass

    def depart_download_reference(self, node):
        pass

    def visit_pending_xref(self, node):
        pass

    def depart_pending_xref(self, node):
        pass

    def visit_target(self, node):
        if node.get("ids") and not node.get("refuri"):
            if self.para is not None and isinstance(node.parent, nodes.TextElement):
                for node_id in node["ids"]:
                    self.para.add(self.bookmark_xml(node_id))
            else:
                self.take_ids(node)
        if not node.children:
            raise nodes.SkipNode

    def depart_target(self, node):
        pass

    def visit_footnote_reference(self, node):
        refid = node.get("refid")
        footnote = (self.node_ids.get(refid) or self.document.ids.get(refid)) if refid else None
        if footnote is None:
            self.add_text(f"[{node.astext()}]", {"vert": "superscript"})
            raise nodes.SkipNode
        if refid in self.footnote_ids:
            self.add_text(str(self.footnote_ids[refid]), {"vert": "superscript"})
            raise nodes.SkipNode
        para = self.ensure_paragraph()
        self.pending_footnote_ref = True
        content = [c for c in footnote.children if not isinstance(c, nodes.label)]
        blocks = self.render_blocks(content, para_style="FootnoteText")
        self.pending_footnote_ref = False
        fid = self.pkg.add_footnote("".join(blocks))
        self.footnote_ids[refid] = fid
        para.add(f'<w:r><w:rPr><w:rStyle w:val="FootnoteReference"/></w:rPr><w:footnoteReference w:id="{fid}"/></w:r>')
        raise nodes.SkipNode

    def visit_footnote(self, node):
        raise nodes.SkipNode     # rendered where it is referenced

    def visit_citation_reference(self, node):
        para = self.ensure_paragraph()
        refid = node.get("refid")
        if refid:
            para.start_link(f'<w:hyperlink w:anchor={quoteattr(self.bookmark_name(refid))} w:history="1">')
        self.add_text(f"[{node.astext()}]")
        if refid:
            para.end_link()
        raise nodes.SkipNode

    def visit_citation(self, node):
        self.close_paragraph()
        self.take_ids(node)
        label = node[0].astext() if len(node) and isinstance(node[0], nodes.label) else ""
        # The text of every entry starts at the same place: a hanging indent as wide as the longest label of the
        # bibliography, measured roughly (Word's hanging indent is also the tab stop after the label). Unusually
        # long labels (a bib key used as the label) are left out: their text moves on to the next tab stop.
        labels = [c[0].astext() for c in (node.parent.children if node.parent is not None else [node])
                  if isinstance(c, nodes.citation) and len(c) and isinstance(c[0], nodes.label)]
        lengths = [len(f"[{t}]") for t in labels]
        longest = max([n for n in lengths if n <= 12] or [0])
        width = min(max(567, longest * _TWIPS_PER_CHAR + 200), self.available_width() // 3)
        if label:
            self.pending_prefix.append(self.run_xml(f"[{label}]\t"))
        self.pending_hanging = width
        self.para_style_stack.append("SpxBibliography")
        self.indent_stack.append(self.indent_stack[-1] + width)

    def depart_citation(self, node):
        self.close_paragraph()
        self.pending_hanging = 0
        self.indent_stack.pop()
        self.para_style_stack.pop()

    def visit_label(self, node):
        raise nodes.SkipNode

    # ===================================================================================================== lists
    def visit_bullet_list(self, node):
        self.close_paragraph()
        self.lists.append(ListState(self.pkg.new_list(True), len(self.lists)))

    def depart_bullet_list(self, node):
        self.close_paragraph()
        self.lists.pop()

    def visit_enumerated_list(self, node):
        self.close_paragraph()
        num_id = self.pkg.new_list(False, node.get("enumtype", "arabic"), int(node.get("start", 1)),
                                   node.get("prefix", ""), node.get("suffix", "."))
        self.lists.append(ListState(num_id, len(self.lists)))

    def depart_enumerated_list(self, node):
        self.close_paragraph()
        self.lists.pop()

    def visit_list_item(self, node):
        self.close_paragraph()
        if self.lists:
            self.lists[-1].first_paragraph = True
        self.take_ids(node)

    def depart_list_item(self, node):
        self.close_paragraph()
        if self.lists and self.lists[-1].first_paragraph:
            # an empty item still needs its number
            self.open_paragraph()
            self.close_paragraph()

    def visit_definition_list(self, node):
        self.close_paragraph()

    def depart_definition_list(self, node):
        self.close_paragraph()

    def visit_definition_list_item(self, node):
        self.take_ids(node)

    def depart_definition_list_item(self, node):
        pass

    def visit_term(self, node):
        self.take_ids(node)
        self.open_paragraph(style="SpxDefinitionTerm")

    def depart_term(self, node):
        pass       # classifiers may follow on the same line

    def visit_classifier(self, node):
        self.add_text(" : ")
        self.push_fmt(italic=True)

    def depart_classifier(self, node):
        self.pop_fmt()

    def visit_definition(self, node):
        self.close_paragraph()
        self.indent_stack.append(self.indent_stack[-1] + 567)

    def depart_definition(self, node):
        self.close_paragraph()
        self.indent_stack.pop()

    def visit_field_list(self, node):
        self.close_paragraph()

    def depart_field_list(self, node):
        self.close_paragraph()

    def visit_field(self, node):
        pass

    def depart_field(self, node):
        pass

    def visit_field_name(self, node):
        self.open_paragraph(style="SpxDefinitionTerm")

    def depart_field_name(self, node):
        self.close_paragraph()

    def visit_field_body(self, node):
        self.indent_stack.append(self.indent_stack[-1] + 567)

    def depart_field_body(self, node):
        self.close_paragraph()
        self.indent_stack.pop()

    def visit_option_list(self, node):
        self.close_paragraph()

    def depart_option_list(self, node):
        self.close_paragraph()

    def visit_option_list_item(self, node):
        pass

    def depart_option_list_item(self, node):
        pass

    def visit_option_group(self, node):
        self.open_paragraph(style="SpxDefinitionTerm")
        self.push_fmt(code=True)
        self.option_first = True

    def depart_option_group(self, node):
        self.pop_fmt()
        self.close_paragraph()

    def visit_option(self, node):
        if not getattr(self, "option_first", True):
            self.add_text(", ")
        self.option_first = False

    def depart_option(self, node):
        pass

    def visit_option_string(self, node):
        pass

    def depart_option_string(self, node):
        pass

    def visit_option_argument(self, node):
        self.add_text(node.get("delimiter", " "))

    def depart_option_argument(self, node):
        pass

    def visit_description(self, node):
        self.indent_stack.append(self.indent_stack[-1] + 567)

    def depart_description(self, node):
        self.close_paragraph()
        self.indent_stack.pop()

    def visit_line_block(self, node):
        self.close_paragraph()
        self.indent_stack.append(self.indent_stack[-1] + (360 if isinstance(node.parent, nodes.line_block) else 0))

    def depart_line_block(self, node):
        self.close_paragraph()
        self.indent_stack.pop()

    def visit_line(self, node):
        self.open_paragraph(spacing='<w:spacing w:after="0"/>')

    def depart_line(self, node):
        self.close_paragraph()

    def visit_block_quote(self, node):
        self.close_paragraph()
        self.indent_stack.append(self.indent_stack[-1] + 567)

    def depart_block_quote(self, node):
        self.close_paragraph()
        self.indent_stack.pop()

    def visit_attribution(self, node):
        self.open_paragraph(jc="right")
        self.add_text("\u2014 ")
        self.push_fmt(italic=True)

    def depart_attribution(self, node):
        self.pop_fmt()
        self.close_paragraph()

    def visit_hlist(self, node):
        pass

    def depart_hlist(self, node):
        pass

    def visit_hlistcol(self, node):
        pass

    def depart_hlistcol(self, node):
        pass

    # ====================================================================================================== math
    def math_omml(self, latex: str, display: bool, node: nodes.Node) -> Optional[str]:
        try:
            return latex_to_omml(latex, display, self.math_macros)
        except (LatexMathError, RecursionError, IndexError) as exc:
            self.math_errors += 1
            logger.warning("sphinx2word: cannot convert math to a Word equation (%s): %s", exc, latex.strip(),
                           location=node)
            return None

    def visit_math(self, node):
        latex = node.astext()
        omml = self.math_omml(latex, False, node)
        if omml is None:
            self.add_text(latex, {"code": True, "color": "C00000"})
        elif self.para is not None and self.para.style == "Caption" and omml_as_text(omml) is not None:
            # Word flattens equations when it copies a caption into the table of figures (chi^2 becomes "χ2"), but
            # keeps the formatting of text, so simple math in a caption is written as italic and script text.
            for text, fmt in omml_as_text(omml):
                self.add_text(text, fmt)
        else:
            self.ensure_paragraph().add(omml)
        raise nodes.SkipNode

    def equation_number(self, node) -> str:
        if node.get("number") is None:
            return ""
        number = str(node["number"])
        if self.config.math_numfig and self.config.numfig:
            figtype_numbers = getattr(self.env, "toc_fignumbers", {}).get(node.get("docname", self.docname), {})
            node_id = node["ids"][0] if node.get("ids") else None
            if node_id and node_id in figtype_numbers.get("displaymath", {}):
                number = ".".join(map(str, figtype_numbers["displaymath"][node_id]))
        fmt = self.config.math_eqref_format or "({number})"
        try:
            return fmt.format(number=number)
        except (KeyError, IndexError, ValueError):
            return f"({number})"

    def visit_math_block(self, node):
        self.close_paragraph()
        latex = node.astext()
        if node.get("nowrap"):
            latex = re.sub(r"\\(begin|end)\{(equation|align|gather|eqnarray|multline)\*?\}", "", latex)
        omml = self.math_omml(latex, True, node)
        ids = list(node.get("ids", []))
        self.pending_ids = [i for i in self.pending_ids if i not in ids]
        if omml is None:
            self.open_paragraph(style="SpxCode")
            self.add_text(latex.strip(), {"color": "C00000"})
            for node_id in ids:
                self.para.add(self.bookmark_xml(node_id))
            self.close_paragraph()
            raise nodes.SkipNode
        number = self.equation_number(node)
        width = self.available_width()
        if not number:
            self.open_paragraph(style="SpxEquation")
            for node_id in ids:
                self.para.add(self.bookmark_xml(node_id))
            self.para.add(omml)
            self.close_paragraph()
            raise nodes.SkipNode
        # Numbered equation: a borderless table with the equation centred and the number on the right.
        side = width // 10
        middle = width - 2 * side
        bookmarks = "".join(self.bookmark_xml(i) for i in ids)
        cell = ('<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>{p}</w:tc>')
        empty_p = '<w:p><w:pPr><w:pStyle w:val="SpxEquation"/></w:pPr></w:p>'
        eq_p = f'<w:p><w:pPr><w:pStyle w:val="SpxEquation"/><w:jc w:val="center"/></w:pPr>{omml}</w:p>'
        target = self.element_targets.get(id(node))
        if target is not None and target.number:
            number_xml = self.run_xml("(") + self.number_fields_xml(target) + self.run_xml(")")
        else:
            number_xml = self.run_xml(number)
        num_p = (f'<w:p><w:pPr><w:pStyle w:val="SpxEquation"/><w:jc w:val="right"/></w:pPr>{bookmarks}'
                 f'{number_xml}</w:p>')
        indent = self.current_indent()
        table = (f'<w:tbl><w:tblPr><w:tblW w:w="{width}" w:type="dxa"/><w:tblInd w:w="{indent}" w:type="dxa"/>'
                 '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
                 '<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders><w:tblLayout w:type="fixed"/>'
                 '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
                 '<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" '
                 'w:noHBand="1" w:noVBand="1"/></w:tblPr>'
                 f'<w:tblGrid><w:gridCol w:w="{side}"/><w:gridCol w:w="{middle}"/><w:gridCol w:w="{side}"/></w:tblGrid>'
                 '<w:tr><w:trPr><w:cantSplit/></w:trPr>'
                 + cell.format(w=side, p=empty_p) + cell.format(w=middle, p=eq_p) + cell.format(w=side, p=num_p)
                 + "</w:tr></w:tbl>")
        self.add_block(table)
        raise nodes.SkipNode

    def visit_displaymath(self, node):
        self.visit_math_block(node)

    # ================================================================================================ literals
    def visit_literal_block(self, node):
        self.take_ids(node)
        self.open_paragraph(style="SpxCode", indent=self.current_indent() + 113)
        text = node.astext()
        is_plain = all(isinstance(c, nodes.Text) for c in node.children)
        args = node.get("highlight_args", {}) or {}
        numbered = bool(node.get("linenos"))
        emphasized = set(args.get("hl_lines", []) or [])
        tokens = None
        if is_plain and self.config.word_highlight_code:
            language = node.get("language") or getattr(self.config, "highlight_language", None) or "default"
            tokens = self.highlight_tokens(text, language)
        if is_plain and (tokens is not None or numbered or emphasized):
            if tokens is None:
                tokens = [(text, {})]
            for r in self.code_lines_xml(tokens, numbered, int(args.get("linenostart", 1) or 1), emphasized):
                self.para.add(r)
            self.close_paragraph()
            raise nodes.SkipNode
        self.literal_depth += 1

    def depart_literal_block(self, node):
        self.literal_depth -= 1
        self.close_paragraph()

    def code_lines_xml(self, tokens: List[Tuple[str, Dict[str, Any]]], numbered: bool, first: int,
                       emphasized: set) -> List[str]:
        """Runs of a code block, line by line: grey line numbers (``:linenos:``) and shaded emphasized lines."""
        lines: List[List[Tuple[str, Dict[str, Any]]]] = [[]]
        for value, extra in tokens:
            for i, part in enumerate(value.split("\n")):
                if i:
                    lines.append([])
                if part:
                    lines[-1].append((part, extra))
        if lines and not lines[-1] and len(lines) > 1:
            lines.pop()                      # a final newline does not start a line
        width = len(str(first + len(lines) - 1))
        runs = []
        for n, line in enumerate(lines, 1):
            if n > 1:
                runs.append("<w:r><w:br/></w:r>")
            shade = {"shade": "FFF2A8"} if n in emphasized else {}
            if numbered:
                runs.append(self.run_xml(f"{first + n - 1:>{width}}  ", {"color": "8C8C8C", **shade}))
            if not line and shade:
                runs.append(self.run_xml(" ", shade))
            for value, extra in line:
                runs.append(self.run_xml(value, {**extra, **shade}))
        return [r for r in runs if r]

    def highlight(self, text: str, language: str) -> Optional[List[str]]:
        tokens = self.highlight_tokens(text, language)
        if tokens is None:
            return None
        return [r for r in (self.run_xml(value, extra) for value, extra in tokens) if r]

    def highlight_tokens(self, text: str, language: str) -> Optional[List[Tuple[str, Dict[str, Any]]]]:
        """Pygments tokens of ``text`` with their run format, or None if the language is not coloured."""
        try:
            from pygments import lex
            from pygments.lexers import get_lexer_by_name, guess_lexer
            from pygments.styles import get_style_by_name
            from pygments.util import ClassNotFound
        except ImportError:
            return None
        try:
            if language in ("default", "none", "text", "raw"):
                return None
            if language == "ipython":
                language = "python"
            lexer = get_lexer_by_name(language, stripnl=False, ensurenl=False)
        except Exception:
            return None
        try:
            style = get_style_by_name(self.config.pygments_style or "sphinx")
        except Exception:
            style = get_style_by_name("default")
        tokens = []
        for ttype, value in lex(text, lexer):
            # Some lexers make token types that the style does not list (YAML: Token.Literal.Scalar.Plain); use the
            # nearest parent type that it does, as Pygments' own formatters do.
            while not style.styles_token(ttype) and ttype.parent is not None:
                ttype = ttype.parent
            try:
                s = style.style_for_token(ttype)
            except KeyError:
                s = {}
            extra = {}
            if s.get("color"):
                extra["color"] = s["color"]
            if s.get("bold"):
                extra["bold"] = True
            if s.get("italic"):
                extra["italic"] = True
            tokens.append((value, extra))
        return tokens

    def visit_doctest_block(self, node):
        self.open_paragraph(style="SpxCode", indent=self.current_indent() + 113)
        runs = self.highlight(node.astext(), "pycon") if self.config.word_highlight_code else None
        if runs:
            for r in runs:
                self.para.add(r)
        else:
            self.add_text(node.astext())
        self.close_paragraph()
        raise nodes.SkipNode

    def visit_container(self, node):
        if node.get("literal_block"):
            self.take_ids(node)

    def depart_container(self, node):
        pass

    # ================================================================================================== captions
    def figure_number(self, node: nodes.Element, figtype: str) -> str:
        if not self.config.numfig or not node.get("ids"):
            return ""
        docname = self.docname
        numbers = getattr(self.env, "toc_fignumbers", {}).get(docname, {}).get(figtype, {})
        number = numbers.get(node["ids"][0])
        if number is None:
            return ""
        fmt = self.config.numfig_format.get(figtype, "%s")
        try:
            return fmt % ".".join(map(str, number))
        except TypeError:
            return fmt

    def add_caption_label(self, element: nodes.Element, figtype: str):
        """Write the caption label and number at the start of a caption paragraph.

        By default this is what Word's Insert Caption writes, ``Figure {SEQ Figure \\* ARABIC}``, in the formatting
        of the Caption style, followed by ``word_caption_separator``; Sphinx only gives the caption text. With
        ``word_caption_numbering = "sphinx"`` it is Sphinx's ``numfig_format`` with chapter numbers,
        ``Fig. {STYLEREF 1 \\s}.{SEQ Figure \\s 1}: ``, in bold. Either way the number is a field, so Word's
        cross-reference dialog and table of figures find the caption, and the numbers follow the document when it
        is copied into a larger one.
        """
        target = self.element_targets.get(id(element))
        if target is None or not target.number:
            label = self.figure_number(element, figtype)
            if label:
                self.add_text(label + ": ", {"bold": True})
            return
        caption = next((c for c in element.children if isinstance(c, (nodes.caption, nodes.title))), None)
        pieces = self.inline_pieces(caption) if caption is not None else []
        if target.label_bookmark:
            start, end = self.bookmark_span(target.label_bookmark)
            self.para.add(start)
            self.add_text(self.caption_label(figtype) + " ")
            self.para.add(self.number_fields_xml(target) + end)
            self.add_text(self.config.word_caption_separator)
            prefix = f"{self.caption_label(figtype)} {target.shown_text}{self.config.word_caption_separator}"
            self.caption_entries.setdefault(figtype, []).append((prefix, pieces, target.label_bookmark))
            return
        fmt = self.config.numfig_format.get(figtype, "%s")
        before, _, after = fmt.partition("%s")
        bold = {"bold": True}
        self.add_text(before, bold)
        self.para.add(self.number_fields_xml(target, bold))
        self.add_text(after + ": ", bold)
        prefix = f"{before}{target.shown_text}{after}: "
        self.caption_entries.setdefault(figtype, []).append((prefix, pieces, target.bookmark))

    def visit_caption(self, node):
        parent = node.parent
        self.open_paragraph(style="Caption", indent=0)
        if isinstance(parent, nodes.figure):
            figtype = "figure"
            self.para.jc = {"left": "left", "right": "right"}.get(parent.get("align"), None)
        elif isinstance(parent, nodes.container) and parent.get("literal_block"):
            figtype = "code-block"
            self.para.jc = "left"
            self.para.keep_next = True
        else:
            figtype = ""
        for node_id in parent.get("ids", []):
            self.para.add(self.bookmark_xml(node_id))
        if figtype:
            self.add_caption_label(parent, figtype)

    def depart_caption(self, node):
        self.close_paragraph()

    def visit_legend(self, node):
        self.close_paragraph()

    def depart_legend(self, node):
        self.close_paragraph()

    # =================================================================================================== figures
    def visit_figure(self, node):
        self.close_paragraph()
        self.figure_align = {"left": "left", "right": "right"}.get(node.get("align"), "center")
        # bookmarks go on the caption so that a reference lands on the figure number
        if not any(isinstance(c, nodes.caption) for c in node.children):
            self.take_ids(node)

    def depart_figure(self, node):
        self.close_paragraph()

    def visit_image(self, node):
        uri = node.get("uri", "")
        candidates = node.get("candidates", {})
        if "?" in candidates:
            uri = candidates["?"]
        path = uri if os.path.isabs(uri) else os.path.join(self.env.srcdir, uri)
        inline = isinstance(node.parent, nodes.TextElement) and not isinstance(node.parent, nodes.figure)
        if "://" in uri or not os.path.exists(path):
            logger.warning("sphinx2word: image not found or remote: %s", uri, location=node)
            self.add_text(f"[image: {uri}]", {"color": "C00000"})
            raise nodes.SkipNode
        if not inline and not isinstance(node.parent, nodes.reference):
            if isinstance(node.parent, nodes.figure):
                self.open_paragraph(style="SpxFigure", indent=self.current_indent(), jc=self.figure_align)
            else:
                align = {"left": "left", "right": "right", "center": "center"}.get(node.get("align"), "center")
                self.open_paragraph(style="SpxFigure", indent=self.current_indent(), jc=align)
            self.take_ids(node)
            self.flush_pending_ids()
        drawing = self.image_drawing(path, node)
        if drawing:
            self.ensure_paragraph().add(f"<w:r>{drawing}</w:r>")
        if not inline and isinstance(node.parent, nodes.figure):
            pass   # keep the paragraph open: several images in one figure sit side by side
        elif not inline and not isinstance(node.parent, nodes.reference):
            self.close_paragraph()
        raise nodes.SkipNode

    def image_size(self, path: str) -> Tuple[float, float, float]:
        """Return (width_px, height_px, dpi)."""
        ext = os.path.splitext(path)[1].lower()
        if ext == ".svg":
            return svg_size(path) + (96.0,)
        try:
            from PIL import Image
            with Image.open(path) as im:
                dpi = im.info.get("dpi", (96, 96))[0] or 96
                dpi = float(dpi) if 30 < float(dpi) < 1200 else 96.0
                return float(im.width), float(im.height), dpi
        except Exception:
            pass
        size = png_size(path)
        if size:
            return size[0], size[1], 96.0
        return 400.0, 300.0, 96.0

    def image_drawing(self, path: str, node: nodes.Element) -> Optional[str]:
        width_px, height_px, dpi = self.image_size(path)
        native_w = width_px / dpi * EMU_PER_INCH
        native_h = height_px / dpi * EMU_PER_INCH
        avail = self.available_width() * EMU_PER_INCH // TWIPS_PER_INCH
        w = h = None
        if node.get("width"):
            w = length_to_emu(node["width"], avail)
        if node.get("height"):
            h = length_to_emu(node["height"], self.text_height_emu)
        if w and not h:
            h = w * native_h / native_w
        elif h and not w:
            w = h * native_w / native_h
        elif not w and not h:
            w, h = native_w, native_h
        if node.get("scale"):
            w = w * float(node["scale"]) / 100.0
            h = h * float(node["scale"]) / 100.0
        if w > avail:
            h = h * avail / w
            w = avail
        max_h = self.text_height_emu * 0.9
        if h > max_h:
            w = w * max_h / h
            h = max_h
        w, h = int(w), int(h)

        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as f:
            data = f.read()
        svg_ext = ""
        if ext == ".svg":
            svg_rid = self.pkg.add_image(data, ".svg")
            png = rasterise_svg(data)
            rid = self.pkg.add_image(png or _TRANSPARENT_PNG, ".png")
            svg_ext = ('<a:extLst><a:ext uri="{96DAC541-7B7A-43D3-8B79-37D633B846F1}">'
                       f'<asvg:svgBlip r:embed="{svg_rid}"/></a:ext></a:extLst>')
        elif ext in (".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".emf", ".wmf"):
            rid = self.pkg.add_image(data, ext)
        else:
            logger.warning("sphinx2word: unsupported image type %s", path, location=node)
            return None
        self.drawing_counter += 1
        did = self.drawing_counter
        name = xml_text(os.path.basename(path))
        alt = quoteattr(node.get("alt", ""))
        return (f'<w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{w}" cy="{h}"/>'
                f'<wp:docPr id="{did}" name="Picture {did}" descr={alt}/>'
                '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                f'<pic:pic><pic:nvPicPr><pic:cNvPr id="{did}" name="{name}"/><pic:cNvPicPr/></pic:nvPicPr>'
                f'<pic:blipFill><a:blip r:embed="{rid}">{svg_ext}</a:blip><a:stretch><a:fillRect/></a:stretch>'
                f'</pic:blipFill><pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{w}" cy="{h}"/></a:xfrm>'
                '<a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr></pic:pic></a:graphicData></a:graphic>'
                '</wp:inline></w:drawing>')

    # ==================================================================================================== tables
    def visit_table(self, node):
        self.close_paragraph()
        title = next((c for c in node.children if isinstance(c, nodes.title)), None)
        ids = list(node.get("ids", []))
        if title is not None:
            self.open_paragraph(style="Caption", indent=0, keep_next=True)
            for node_id in ids + self.pending_ids:
                self.para.add(self.bookmark_xml(node_id))
            self.pending_ids = []
            self.add_caption_label(node, "table")
            for child in title.children:
                child.walkabout(self)
            self.close_paragraph()
        else:
            self.pending_ids.extend(ids)
            if self.pending_ids:
                # no caption: put the bookmark in a tiny paragraph before the table
                self.open_paragraph(spacing='<w:spacing w:after="0"/>', keep_next=True)
                self.close_paragraph()
        for tgroup in node.children:
            if isinstance(tgroup, nodes.tgroup):
                self.add_block(self.table_xml(node, tgroup))
        # separate consecutive tables
        self.add_block('<w:p><w:pPr><w:spacing w:after="0" w:line="120" w:lineRule="exact"/></w:pPr></w:p>')
        raise nodes.SkipNode

    def table_xml(self, table: nodes.table, tgroup: nodes.tgroup) -> str:
        colspecs = [c for c in tgroup.children if isinstance(c, nodes.colspec)]
        ncols = len(colspecs) or int(tgroup.get("cols", 1))
        avail = self.available_width()
        def colwidth(c):
            try:
                return float(c.get("colwidth", 1) or 1)
            except (TypeError, ValueError):     # "auto"
                return None

        auto = ("colwidths-auto" in table.get("classes", []) or "colwidths-auto" in tgroup.get("classes", [])
                or any(colwidth(c) is None for c in colspecs))
        total_width = avail
        if table.get("width"):
            total_width = min(int(length_to_emu(table["width"], avail * 635) / 635), avail)
        rel = [colwidth(c) or 1.0 for c in colspecs] or [1.0] * ncols

        thead = [c for c in tgroup.children if isinstance(c, nodes.thead)]
        tbody = [c for c in tgroup.children if isinstance(c, nodes.tbody)]
        header_rows = [r for t in thead for r in t.children if isinstance(r, nodes.row)]
        body_rows = [r for t in tbody for r in t.children if isinstance(r, nodes.row)]
        stub_cols = sum(1 for c in colspecs if c.get("stub"))

        if "colwidths-given" in table.get("classes", []) or "colwidths-given" in tgroup.get("classes", []):
            widths = [int(total_width * r / sum(rel)) for r in rel]
        else:
            # Like Sphinx's HTML output, ignore the character widths of the source table, except as weights:
            # every column is at least as wide as its longest word.
            widths = fit_column_widths(header_rows + body_rows, rel, total_width)

        rows_xml = []
        pending: Dict[int, Tuple[int, int]] = {}     # grid column -> (rows remaining, span)
        for row_index, row in enumerate(header_rows + body_rows):
            is_header = row_index < len(header_rows)
            cells_xml = []
            col = 0
            entries = [e for e in row.children if isinstance(e, nodes.entry)]

            def emit_continuations():
                nonlocal col
                while col in pending:
                    remaining, span = pending[col]
                    w = sum(widths[col:col + span])
                    gs = f'<w:gridSpan w:val="{span}"/>' if span > 1 else ""
                    cells_xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{gs}<w:vMerge/></w:tcPr>'
                                     '<w:p><w:pPr><w:pStyle w:val="SpxTableText"/></w:pPr></w:p></w:tc>')
                    if remaining <= 1:
                        del pending[col]
                    else:
                        pending[col] = (remaining - 1, span)
                    col += span

            for entry in entries:
                emit_continuations()
                span = int(entry.get("morecols", 0)) + 1
                span = max(1, min(span, ncols - col)) if col < ncols else 1
                morerows = int(entry.get("morerows", 0))
                w = sum(widths[col:col + span]) if col < ncols else widths[-1]
                fmt_header = is_header or col < stub_cols
                if fmt_header:
                    self.fmt_stack.append({"bold": True} if not is_header else {})
                blocks = self.render_blocks(entry.children, width=w - 170, para_style="SpxTableText")
                if fmt_header:
                    self.fmt_stack.pop()
                if not blocks or not blocks[-1].startswith("<w:p"):
                    blocks.append('<w:p><w:pPr><w:pStyle w:val="SpxTableText"/></w:pPr></w:p>')
                tcpr = f'<w:tcW w:w="{w}" w:type="dxa"/>'
                if span > 1:
                    tcpr += f'<w:gridSpan w:val="{span}"/>'
                if morerows:
                    tcpr += '<w:vMerge w:val="restart"/>'
                    pending[col] = (morerows, span)
                if col < stub_cols and not is_header:
                    tcpr += '<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/>'
                cells_xml.append(f"<w:tc><w:tcPr>{tcpr}</w:tcPr>{''.join(blocks)}</w:tc>")
                col += span
            emit_continuations()
            # Fill short rows so that Word does not complain about ragged tables
            while col < ncols:
                cells_xml.append(f'<w:tc><w:tcPr><w:tcW w:w="{widths[col]}" w:type="dxa"/></w:tcPr>'
                                 '<w:p><w:pPr><w:pStyle w:val="SpxTableText"/></w:pPr></w:p></w:tc>')
                col += 1
            trpr = "<w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>" if is_header else "<w:trPr><w:cantSplit/></w:trPr>"
            rows_xml.append(f"<w:tr>{trpr}{''.join(cells_xml)}</w:tr>")

        indent = self.current_indent()
        align = table.get("align")
        jc = {"left": "left", "right": "right"}.get(align, "center") if not indent else "left"
        layout = '<w:tblLayout w:type="autofit"/>' if auto else '<w:tblLayout w:type="fixed"/>'
        tblw = '<w:tblW w:w="0" w:type="auto"/>' if auto else f'<w:tblW w:w="{total_width}" w:type="dxa"/>'
        look = ('<w:tblLook w:val="04A0" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" '
                'w:noHBand="0" w:noVBand="1"/>') if header_rows else \
            ('<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" '
             'w:noHBand="1" w:noVBand="1"/>')
        ind = f'<w:tblInd w:w="{indent}" w:type="dxa"/>' if indent else ""
        tblpr = (f'<w:tblPr><w:tblStyle w:val="{self.config.word_table_style}"/>{tblw}<w:jc w:val="{jc}"/>{ind}'
                 f'{layout}{look}</w:tblPr>')
        grid = "<w:tblGrid>" + "".join(f'<w:gridCol w:w="{w}"/>' for w in widths) + "</w:tblGrid>"
        return f"<w:tbl>{tblpr}{grid}{''.join(rows_xml)}</w:tbl>"

    def visit_tabular_col_spec(self, node):
        raise nodes.SkipNode

    def visit_colspec(self, node):
        raise nodes.SkipNode

    # ============================================================================================== admonitions
    def boxed(self, node: nodes.Element, title: Optional[str], colour: str, children) -> str:
        width = self.available_width()
        indent = self.current_indent()
        blocks = []
        bookmarks = "".join(self.bookmark_xml(i) for i in self.pending_ids)
        self.pending_ids = []
        if title or bookmarks:
            blocks.append(f'<w:p><w:pPr><w:pStyle w:val="SpxAdmonitionTitle"/></w:pPr>{bookmarks}'
                          f'{self.run_xml(title or "", {"color": colour})}</w:p>')
        blocks += self.render_blocks(children, width=width - 400)
        if not blocks or not blocks[-1].startswith("<w:p"):
            blocks.append("<w:p/>")
        return (f'<w:tbl><w:tblPr><w:tblW w:w="{width}" w:type="dxa"/><w:tblInd w:w="{indent}" w:type="dxa"/>'
                f'<w:tblBorders><w:top w:val="nil"/><w:left w:val="single" w:sz="24" w:space="0" w:color="{colour}"/>'
                '<w:bottom w:val="nil"/><w:right w:val="nil"/></w:tblBorders><w:tblLayout w:type="fixed"/>'
                '<w:tblCellMar><w:top w:w="85" w:type="dxa"/><w:left w:w="170" w:type="dxa"/>'
                '<w:bottom w:w="57" w:type="dxa"/><w:right w:w="170" w:type="dxa"/></w:tblCellMar></w:tblPr>'
                f'<w:tblGrid><w:gridCol w:w="{width}"/></w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr><w:tc><w:tcPr>'
                f'<w:tcW w:w="{width}" w:type="dxa"/><w:shd w:val="clear" w:color="auto" w:fill="F5F7FA"/></w:tcPr>'
                f'{"".join(blocks)}</w:tc></w:tr></w:tbl>'
                '<w:p><w:pPr><w:spacing w:after="0" w:line="120" w:lineRule="exact"/></w:pPr></w:p>')

    def visit_admonition(self, node):
        self.close_paragraph()
        self.take_ids(node)
        tag = node.tagname
        children = list(node.children)
        if children and isinstance(children[0], nodes.title):
            title = children.pop(0).astext()
        else:
            title = admonitionlabels.get(tag, tag.capitalize())
        self.add_block(self.boxed(node, title, ADMONITION_COLOURS.get(tag, "4472C4"), children))
        raise nodes.SkipNode

    visit_attention = visit_caution = visit_danger = visit_error = visit_hint = visit_admonition
    visit_important = visit_note = visit_tip = visit_warning = visit_seealso = visit_admonition

    def visit_todo_node(self, node):
        if getattr(self.config, "todo_include_todos", False):
            self.visit_admonition(node)
        raise nodes.SkipNode

    def visit_versionmodified(self, node):
        self.close_paragraph()
        self.push_fmt(italic=True)

    def depart_versionmodified(self, node):
        self.close_paragraph()
        self.pop_fmt()

    def visit_topic(self, node):
        if "contents" in node.get("classes", []):
            raise nodes.SkipNode      # Word has its own table of contents
        self.close_paragraph()
        children = list(node.children)
        title = children.pop(0).astext() if children and isinstance(children[0], nodes.title) else None
        self.add_block(self.boxed(node, title, "7F7F7F", children))
        raise nodes.SkipNode

    visit_sidebar = visit_topic

    # ==================================================================================== API documentation (desc)
    def visit_desc(self, node):
        self.close_paragraph()

    def depart_desc(self, node):
        self.close_paragraph()

    def visit_desc_signature(self, node):
        self.take_ids(node)
        # wrapped signature lines hang under the name
        self.open_paragraph(style="SpxSignature", indent=self.current_indent() + 567, hanging=567)

    def depart_desc_signature(self, node):
        self.close_paragraph()

    def visit_desc_signature_line(self, node):
        if self.para is not None and not self.para.is_empty:
            self.para.add("<w:r><w:br/></w:r>")

    def depart_desc_signature_line(self, node):
        pass

    def visit_desc_name(self, node):
        self.push_fmt(bold=True)

    depart_desc_name = pop_fmt

    def visit_desc_addname(self, node):
        self.push_fmt(color="404040")

    depart_desc_addname = pop_fmt

    def visit_desc_type(self, node):
        self.push_fmt()

    depart_desc_type = pop_fmt

    def visit_desc_returns(self, node):
        self.add_text(" \u2192 ")
        self.push_fmt()

    depart_desc_returns = pop_fmt

    def visit_desc_annotation(self, node):
        self.push_fmt(italic=True, color="404040")

    depart_desc_annotation = pop_fmt

    def visit_desc_parameterlist(self, node):
        self.add_text(node.get("open_paren", "("))
        self.param_first.append(True)

    def depart_desc_parameterlist(self, node):
        self.param_first.pop()
        self.add_text(node.get("close_paren", ")"))

    visit_desc_type_parameter_list = visit_desc_parameterlist
    depart_desc_type_parameter_list = depart_desc_parameterlist

    def visit_desc_parameter(self, node):
        if self.param_first and not self.param_first[-1]:
            self.add_text(", ")
        if self.param_first:
            self.param_first[-1] = False
        self.push_fmt(italic=True)

    depart_desc_parameter = pop_fmt
    visit_desc_type_parameter = visit_desc_parameter
    depart_desc_type_parameter = pop_fmt

    def visit_desc_optional(self, node):
        self.add_text("[")

    def depart_desc_optional(self, node):
        self.add_text("]")

    def visit_desc_content(self, node):
        self.close_paragraph()
        self.indent_stack.append(self.indent_stack[-1] + 567)

    def depart_desc_content(self, node):
        self.close_paragraph()
        self.indent_stack.pop()

    def visit_desc_inline(self, node):
        self.push_fmt(code=True)

    depart_desc_inline = pop_fmt

    # ===================================================================================================== index
    @staticmethod
    def xe_text(text: str) -> str:
        """Text for an XE field: backslashes, quotes and colons (Word's level separator) escaped."""
        return text.strip().replace("\\", "\\\\").replace('"', '\\"').replace(":", "\\:")

    def xe_instructions(self, entry) -> List[str]:
        """The XE field instructions of one Sphinx index entry (single, pair, triple, see, seealso)."""
        etype, value = entry[0], entry[1]
        main = len(entry) > 3 and bool(entry[3])
        parts = [self.xe_text(p) for p in value.split(";")]
        parts = [p for p in parts if p]
        if not parts:
            return []
        bold = " \\b" if main else ""
        if etype == "pair" and len(parts) >= 2:
            levels = [[parts[0], parts[1]], [parts[1], parts[0]]]
        elif etype == "triple" and len(parts) >= 3:
            a, b, c = parts[:3]
            levels = [[a, f"{b} {c}"], [b, f"{c}, {a}"], [c, f"{a} {b}"]]
        elif etype in ("see", "seealso") and len(parts) >= 2:
            label = self.labels["see"] if etype == "see" else self.labels["see_also"]
            return [f'XE "{parts[0]}" \\t "{label % parts[1]}"']
        else:
            levels = [parts[:2]]
        return [f'XE "{":".join(lv)}"{bold}' for lv in levels]

    def visit_index(self, node):
        for entry in node.get("entries", []):
            for instr in self.xe_instructions(entry):
                self.index_entries += 1
                self.add_xe(instr)
        raise nodes.SkipNode

    def write_index(self):
        """The indexes at the end of the document: a heading and an INDEX field that Word fills in, for the Python
        modules (the XE fields of entry type "m") and for everything else."""
        self.close_paragraph()
        self.pending_xe = []
        if self.module_entries and self.config.word_module_index:
            self.add_toc_field(self.label("word_module_index_title", "module_index"),
                               'INDEX \\f "m" \\h "A" \\c "1" \\z "1033"', "the module index")
        if self.index_entries and self.config.word_index:
            columns = max(1, int(self.config.word_index_columns or 1))
            self.add_toc_field(self.label("word_index_title", "index"),
                               f'INDEX \\h "A" \\c "{columns}" \\z "1033"', "the index")

    def collect_modules(self):
        """The node ids of the Python modules (``py:module``, ``automodule``), for the module index."""
        try:
            modules = self.env.get_domain("py").data.get("modules", {})
        except Exception:
            return
        for name, entry in modules.items():
            node_id = getattr(entry, "node_id", None) or (entry[1] if len(entry) > 1 else None)
            if node_id:
                self.module_targets[node_id] = name

    def add_xe(self, instr: str):
        xml = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r>'
               f'<w:r><w:instrText xml:space="preserve"> {xml_text(instr)} </w:instrText></w:r>'
               '<w:r><w:fldChar w:fldCharType="end"/></w:r>')
        if self.para is not None:
            self.para.add(xml)
        else:
            self.pending_xe.append(xml)      # an index directive before a paragraph: put it there

    # ========================================================================================== page layout
    def page_break(self):
        """Start the next paragraph (or table) on a new page."""
        self.close_paragraph()
        self.pending_page_break = True

    def visit_raw(self, node):
        formats = node.get("format", "").split()
        text = node.astext()
        if "openxml" in formats:
            # WordprocessingML written as it is: paragraphs or tables as a block, runs inside a paragraph
            try:
                ET.fromstring(f'<root xmlns:w="{W_NS}" xmlns:r="{R_NS}" xmlns:m="{M_NS}">{text}</root>')
            except ET.ParseError as exc:
                logger.warning("sphinx2word: raw openxml is not well-formed XML (%s); it is left out", exc,
                               location=node)
                raise nodes.SkipNode
            if isinstance(node.parent, nodes.TextElement):
                self.ensure_paragraph().add(text)
            else:
                self.add_block(text)
        elif "latex" in formats and RAW_LATEX_PAGE_BREAK.fullmatch(text):
            self.page_break()           # \newpage, \clearpage: the same source breaks the page in PDF and Word
        raise nodes.SkipNode

    def landscape_width(self) -> int:
        w, h = self.pkg.page_size
        return h - 2 * self.pkg.margins

    @property
    def text_height_emu(self) -> int:
        if self.landscape_node is not None:
            w, h = self.pkg.page_size
            return (w - 2 * self.pkg.margins) * EMU_PER_INCH // TWIPS_PER_INCH
        return self.pkg.text_height_emu

    def start_landscape(self, node: nodes.Element):
        self.close_paragraph()
        self.pending_page_break = False         # the section break starts a new page anyway
        self.blocks.append(SECTION_END.format("portrait"))
        self.width_stack.append(self.landscape_width())
        self.landscape_node = node

    def end_landscape(self):
        self.close_paragraph()
        self.blocks.append(SECTION_END.format("landscape"))
        self.width_stack.pop()
        self.landscape_node = None

    def dispatch_visit(self, node):
        # A block with the class "landscape" (.. rst-class:: landscape, or .. container:: landscape) gets its own
        # landscape section. Only at the top level: not inside table cells, admonitions or footnotes.
        if self.module_targets and isinstance(node, nodes.Element):
            for node_id in node.get("ids", []):
                if node_id in self.module_targets:
                    # An entry of the Python module index, at the module's target (docutils moves the ids of a
                    # target to the next element). Entry type "m": the general index leaves it out.
                    self.module_entries += 1
                    self.add_xe(f'XE "{self.xe_text(self.module_targets.pop(node_id))}" \\f "m"')
        started = False
        if (isinstance(node, nodes.Element) and "landscape" in node.get("classes", ())
                and self.landscape_node is None and len(self.blocks_stack) == 1):
            self.start_landscape(node)
            started = True
        try:
            super().dispatch_visit(node)
        except nodes.SkipNode:
            if started:
                self.end_landscape()
            raise

    def dispatch_departure(self, node):
        super().dispatch_departure(node)
        if node is self.landscape_node:
            self.end_landscape()

    # ================================================================================================= graphviz
    def visit_graphviz(self, node):
        self.add_graphviz(node, node["code"], node.get("options", {}), "graphviz")

    def visit_inheritance_diagram(self, node):
        from sphinx.ext.inheritance_diagram import get_graph_hash
        graph = node["graph"]
        name = "inheritance" + get_graph_hash(node)
        generate = getattr(graph, "_generate_dot", None) or graph.generate_dot
        attrs = {"size": '"6.0,6.0"'}
        try:
            code = generate(name, config=self.config, graph_attrs=attrs)
        except TypeError:                       # Sphinx < 7: generate_dot(name, urls, env, graph_attrs, ...)
            code = generate(name, env=self.env, graph_attrs=attrs)
        self.add_graphviz(node, code, {}, "inheritance")

    def add_graphviz(self, node: nodes.Element, code: str, options: Dict[str, Any], prefix: str):
        """Render dot code to SVG with Graphviz and insert it like an image (in a figure if it has a caption)."""
        dot = options.get("graphviz_dot") or getattr(self.config, "graphviz_dot", None) or "dot"
        args = list(getattr(self.config, "graphviz_dot_args", None) or [])
        key = hashlib.sha1((code + str(options) + dot + str(args)).encode("utf-8")).hexdigest()
        outdir = os.path.join(self.builder.doctreedir, "sphinx2word-graphviz")
        out = os.path.join(outdir, f"{prefix}-{key}.svg")
        if not os.path.exists(out):
            os.makedirs(outdir, exist_ok=True)
            docname = options.get("docname", self.docname)
            cwd = os.path.dirname(os.path.join(self.env.srcdir, docname))
            try:
                result = subprocess.run([dot, *args, "-Tsvg", f"-o{out}"], input=code.encode("utf-8"),
                                        cwd=cwd if os.path.isdir(cwd) else None, capture_output=True)
            except OSError as exc:
                logger.warning("sphinx2word: cannot run Graphviz (%s = %r): %s; the diagram is left out",
                               "graphviz_dot", dot, exc, location=node)
                raise nodes.SkipNode
            if result.returncode != 0 or not os.path.exists(out):
                logger.warning("sphinx2word: Graphviz failed: %s", result.stderr.decode("utf-8", "replace").strip(),
                               location=node)
                raise nodes.SkipNode
        image = nodes.image(uri=out, alt=node.get("alt", ""), align=node.get("align", "center"))
        image.parent = node.parent              # placed like an image here: in a figure, or as its own paragraph
        image.document = node.document
        try:
            self.visit_image(image)
        except nodes.SkipNode:
            pass
        raise nodes.SkipNode

    # =========================================================================================== skipped nodes
    def skip(self, node):
        raise nodes.SkipNode

    visit_comment = visit_substitution_definition = visit_meta = skip
    visit_system_message = visit_toctree = visit_highlightlang = visit_pending = skip
    visit_productionlist = skip

    def visit_compound(self, node):
        pass

    def depart_compound(self, node):
        pass

    def visit_only(self, node):
        pass

    def depart_only(self, node):
        pass

    def visit_centered(self, node):
        self.open_paragraph(jc="center")
        self.push_fmt(bold=True)

    def depart_centered(self, node):
        self.pop_fmt()
        self.close_paragraph()

    def visit_acks(self, node):
        pass

    def depart_acks(self, node):
        pass

    def visit_glossary(self, node):
        pass

    def depart_glossary(self, node):
        pass

    def visit_seealso_title(self, node):
        pass

    # ================================================================================== fallbacks for the rest
    def unknown_visit(self, node):
        self.unknown_nodes.add(node.__class__.__name__)

    def unknown_departure(self, node):
        pass


# ----------------------------------------------------------------------------------------------------------------------
#   Table helpers
# ----------------------------------------------------------------------------------------------------------------------

_TWIPS_PER_CHAR = 125        # average width of a character of 10 pt (bold) table text
_CELL_PADDING = 240          # cell margins plus a little room


def fit_column_widths(rows, weights: List[float], total: int) -> List[int]:
    """
    Share ``total`` twips between the columns in proportion to ``weights``, but give every column at least the
    width of its longest word (if that is possible at all).
    """
    ncols = len(weights)
    minimum = [600] * ncols
    for row in rows:
        col = 0
        for entry in row.children:
            if not isinstance(entry, nodes.entry):
                continue
            span = int(entry.get("morecols", 0)) + 1
            if span == 1 and col < ncols and not find_all(entry, nodes.image):
                words = re.split(r"\s+", entry.astext())
                longest = max((len(w) for w in words), default=0)
                minimum[col] = max(minimum[col], min(longest, 30) * _TWIPS_PER_CHAR + _CELL_PADDING)
            col += span
    if sum(minimum) >= total:
        return [int(total * m / sum(minimum)) for m in minimum]
    widths = [0.0] * ncols
    fixed = [False] * ncols
    while True:
        free = total - sum(widths[i] for i in range(ncols) if fixed[i])
        weight = sum(weights[i] for i in range(ncols) if not fixed[i]) or 1.0
        changed = False
        for i in range(ncols):
            if not fixed[i]:
                widths[i] = free * weights[i] / weight
                if widths[i] < minimum[i]:
                    widths[i] = minimum[i]
                    fixed[i] = True
                    changed = True
        if not changed:
            break
    return [int(w) for w in widths]


# ----------------------------------------------------------------------------------------------------------------------
#   Image helpers
# ----------------------------------------------------------------------------------------------------------------------

def length_to_emu(value: str, reference_emu: float) -> float:
    """Convert a reST length (``10cm``, ``240px``, ``50%``, ``3in``, ``200``) to EMU."""
    m = re.match(r"\s*([0-9.]+)\s*([a-z%]*)\s*$", str(value))
    if not m:
        return reference_emu
    number = float(m.group(1))
    unit = m.group(2) or "px"
    factors = {"px": EMU_PER_INCH / 96, "pt": EMU_PER_INCH / 72, "pc": EMU_PER_INCH / 6, "in": EMU_PER_INCH,
               "cm": 360000, "mm": 36000, "em": EMU_PER_INCH / 6, "ex": EMU_PER_INCH / 12}
    if unit == "%":
        return reference_emu * number / 100.0
    return number * factors.get(unit, EMU_PER_INCH / 96)


def png_size(path: str) -> Optional[Tuple[int, int]]:
    with open(path, "rb") as f:
        head = f.read(24)
    if head[:8] == b"\x89PNG\r\n\x1a\n":
        return struct.unpack(">II", head[16:24])
    return None


def svg_size(path: str) -> Tuple[float, float]:
    try:
        with open(path, "rb") as f:
            text = f.read(4096).decode("utf-8", "ignore")
    except OSError:
        return 400.0, 300.0
    m = re.search(r"<svg[^>]*>", text, re.DOTALL)
    tag = m.group(0) if m else ""

    def attr(name):
        a = re.search(rf'\s{name}="([^"]+)"', tag)
        return a.group(1) if a else None

    width, height = attr("width"), attr("height")
    viewbox = attr("viewBox")
    if width and height and "%" not in width and "%" not in height:
        w = length_to_emu(width, 0) / (EMU_PER_INCH / 96)
        h = length_to_emu(height, 0) / (EMU_PER_INCH / 96)
        if w > 0 and h > 0:
            return w, h
    if viewbox:
        parts = re.split(r"[\s,]+", viewbox.strip())
        if len(parts) == 4:
            return float(parts[2]), float(parts[3])
    return 400.0, 300.0


def rasterise_svg(data: bytes) -> Optional[bytes]:
    """Make a PNG fallback for an SVG if cairosvg is available (Word 2016+ shows the SVG itself)."""
    try:
        import cairosvg
    except Exception:
        return None
    try:
        return cairosvg.svg2png(bytestring=data)
    except Exception:
        return None
