"""
Write a WordprocessingML (.docx) package directly, without Word or COM.

:class:`DocxPackage` collects the parts of the document (body XML, images, hyperlinks, footnotes and list
definitions) and writes the zip file. The styles come from :data:`DEFAULT_STYLES`. If a template ``.docx``/``.dotx``
is given, its ``styles.xml`` and theme are used instead, and any style this package needs but the template lacks is
added from the defaults.
"""

from __future__ import annotations

import datetime
import os
import re
import zipfile
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from xml.sax.saxutils import escape, quoteattr

W_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"

NAMESPACES = (
    'xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" '
    'xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" '
    'xmlns:o="urn:schemas-microsoft-com:office:office" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
    'xmlns:v="urn:schemas-microsoft-com:vml" '
    'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
    'xmlns:w10="urn:schemas-microsoft-com:office:word" '
    'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" '
    'xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" '
    'xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
    'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture" '
    'xmlns:asvg="http://schemas.microsoft.com/office/drawing/2016/SVG/main" '
    'mc:Ignorable="w14"'
)

XML_HEADER = '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
FRONT_MATTER_END = "<!--sphinx2word:front-matter-end-->"     # replaced by a section break when saving
# Ends a section of the body (around landscape pages); the section that ends has this orientation.
SECTION_END = "<!--sphinx2word:section-end:{}-->"
_SECTION_MARKER = re.compile(r"<!--sphinx2word:(front-matter-end|section-end:(portrait|landscape))-->")

EMU_PER_INCH = 914400
TWIPS_PER_INCH = 1440

PAPER_SIZES = {          # width, height in twips
    "letter": (12240, 15840),
    "a4": (11906, 16838),
}

# ----------------------------------------------------------------------------------------------------------------------
#   Default styles. Style ids are the ones Word uses for its built-in styles so that templates map onto them.
# ----------------------------------------------------------------------------------------------------------------------

_HEADING_SIZES = [32, 26, 24, 22, 22, 22, 22, 22, 22]   # half points


def _heading_style(level: int) -> str:
    size = _HEADING_SIZES[level - 1]
    italic = "<w:i/>" if level >= 4 else ""
    before = 360 if level == 1 else 240
    return (
        f'<w:style w:type="paragraph" w:styleId="Heading{level}"><w:name w:val="heading {level}"/>'
        f'<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="9"/><w:qFormat/>'
        f'<w:pPr><w:keepNext/><w:keepLines/><w:spacing w:before="{before}" w:after="120"/>'
        f'<w:outlineLvl w:val="{level - 1}"/></w:pPr>'
        f'<w:rPr><w:rFonts w:ascii="Calibri Light" w:hAnsi="Calibri Light" w:cs="Calibri Light"/><w:b/>{italic}'
        f'<w:color w:val="1F3864"/><w:sz w:val="{size}"/><w:szCs w:val="{size}"/></w:rPr></w:style>'
    )


def _toc_style(level: int) -> str:
    return (f'<w:style w:type="paragraph" w:styleId="TOC{level}"><w:name w:val="toc {level}"/>'
            f'<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/><w:unhideWhenUsed/>'
            f'<w:pPr><w:spacing w:after="60"/><w:ind w:left="{(level - 1) * 220}"/></w:pPr></w:style>')


DEFAULT_STYLE_DEFINITIONS: Dict[str, str] = {
    "Normal": '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/>'
              '<w:pPr><w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr>'
              '<w:rPr><w:sz w:val="22"/><w:szCs w:val="22"/></w:rPr></w:style>',
    "Title": '<w:style w:type="paragraph" w:styleId="Title"><w:name w:val="Title"/><w:basedOn w:val="Normal"/>'
             '<w:next w:val="Normal"/><w:uiPriority w:val="10"/><w:qFormat/>'
             '<w:pPr><w:spacing w:before="2400" w:after="240"/><w:jc w:val="center"/></w:pPr>'
             '<w:rPr><w:rFonts w:ascii="Calibri Light" w:hAnsi="Calibri Light" w:cs="Calibri Light"/><w:b/><w:color w:val="1F3864"/>'
             '<w:sz w:val="52"/><w:szCs w:val="52"/></w:rPr></w:style>',
    "Subtitle": '<w:style w:type="paragraph" w:styleId="Subtitle"><w:name w:val="Subtitle"/>'
                '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
                '<w:pPr><w:spacing w:after="240"/><w:jc w:val="center"/></w:pPr>'
                '<w:rPr><w:color w:val="595959"/><w:sz w:val="28"/><w:szCs w:val="28"/></w:rPr></w:style>',
    "Caption": '<w:style w:type="paragraph" w:styleId="Caption"><w:name w:val="caption"/>'
               '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="35"/><w:unhideWhenUsed/>'
               '<w:qFormat/><w:pPr><w:spacing w:before="60" w:after="240"/><w:jc w:val="center"/></w:pPr>'
               '<w:rPr><w:i/><w:color w:val="1F3864"/><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>',
    "ListParagraph": '<w:style w:type="paragraph" w:styleId="ListParagraph"><w:name w:val="List Paragraph"/>'
                     '<w:basedOn w:val="Normal"/><w:uiPriority w:val="34"/><w:qFormat/>'
                     '<w:pPr><w:spacing w:after="60"/><w:ind w:left="720"/></w:pPr></w:style>',
    "BlockText": '<w:style w:type="paragraph" w:styleId="BlockText"><w:name w:val="Block Text"/>'
                 '<w:basedOn w:val="Normal"/><w:pPr><w:ind w:left="720" w:right="720"/></w:pPr></w:style>',
    "TOCHeading": '<w:style w:type="paragraph" w:styleId="TOCHeading"><w:name w:val="TOC Heading"/>'
                  '<w:basedOn w:val="Heading1"/><w:next w:val="Normal"/><w:uiPriority w:val="39"/>'
                  '<w:unhideWhenUsed/><w:qFormat/><w:pPr><w:outlineLvl w:val="9"/></w:pPr></w:style>',
    "FootnoteText": '<w:style w:type="paragraph" w:styleId="FootnoteText"><w:name w:val="footnote text"/>'
                    '<w:basedOn w:val="Normal"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/>'
                    '<w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr>'
                    '<w:rPr><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>',
    "FootnoteReference": '<w:style w:type="character" w:styleId="FootnoteReference">'
                         '<w:name w:val="footnote reference"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/>'
                         '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>',
    "Footer": '<w:style w:type="paragraph" w:styleId="Footer"><w:name w:val="footer"/>'
              '<w:basedOn w:val="Normal"/><w:pPr><w:spacing w:after="0"/><w:jc w:val="center"/></w:pPr>'
              '<w:rPr><w:sz w:val="18"/></w:rPr></w:style>',
    "Hyperlink": '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/>'
                 '<w:uiPriority w:val="99"/><w:unhideWhenUsed/>'
                 '<w:rPr><w:color w:val="0563C1"/><w:u w:val="single"/></w:rPr></w:style>',
    "SpxCode": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxCode"><w:name w:val="Spx Code Block"/>'
               '<w:basedOn w:val="Normal"/><w:qFormat/>'
               '<w:pPr><w:pBdr><w:top w:val="single" w:sz="4" w:space="4" w:color="BFBFBF"/>'
               '<w:left w:val="single" w:sz="4" w:space="4" w:color="BFBFBF"/>'
               '<w:bottom w:val="single" w:sz="4" w:space="4" w:color="BFBFBF"/>'
               '<w:right w:val="single" w:sz="4" w:space="4" w:color="BFBFBF"/></w:pBdr>'
               '<w:shd w:val="clear" w:color="auto" w:fill="F8F8F8"/>'
               '<w:spacing w:before="120" w:after="200" w:line="240" w:lineRule="auto"/><w:ind w:left="113" w:right="113"/></w:pPr>'
               '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
               '<w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>',
    "SpxCodeInline": '<w:style w:type="character" w:customStyle="1" w:styleId="SpxCodeInline">'
                     '<w:name w:val="Spx Code Inline"/><w:qFormat/>'
                     '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
                     '<w:color w:val="1F1F1F"/><w:sz w:val="20"/><w:szCs w:val="20"/>'
                     '<w:shd w:val="clear" w:color="auto" w:fill="F2F2F2"/></w:rPr></w:style>',
    "SpxSignature": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxSignature">'
                    '<w:name w:val="Spx API Signature"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
                    '<w:pPr><w:keepNext/><w:pBdr><w:top w:val="single" w:sz="12" w:space="2" w:color="4472C4"/></w:pBdr>'
                    '<w:shd w:val="clear" w:color="auto" w:fill="EAF0FA"/><w:spacing w:before="240" w:after="60"/>'
                    '</w:pPr>'
                    '<w:rPr><w:rFonts w:ascii="Consolas" w:hAnsi="Consolas" w:cs="Consolas"/>'
                    '<w:sz w:val="19"/><w:szCs w:val="19"/></w:rPr></w:style>',
    "SpxDescription": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxDescription">'
                      '<w:name w:val="Spx API Description"/><w:basedOn w:val="Normal"/>'
                      '<w:pPr><w:ind w:left="567"/></w:pPr></w:style>',
    "SpxRubric": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxRubric"><w:name w:val="Spx Rubric"/>'
                 '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:pPr><w:keepNext/><w:spacing w:before="200"/></w:pPr>'
                 '<w:rPr><w:b/><w:color w:val="1F3864"/></w:rPr></w:style>',
    "SpxAdmonitionTitle": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxAdmonitionTitle">'
                          '<w:name w:val="Spx Admonition Title"/><w:basedOn w:val="Normal"/>'
                          '<w:pPr><w:keepNext/><w:spacing w:after="60"/></w:pPr><w:rPr><w:b/></w:rPr></w:style>',
    "SpxTableText": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxTableText">'
                    '<w:name w:val="Spx Table Text"/><w:basedOn w:val="Normal"/>'
                    '<w:pPr><w:spacing w:before="20" w:after="20" w:line="240" w:lineRule="auto"/></w:pPr>'
                    '<w:rPr><w:sz w:val="20"/><w:szCs w:val="20"/></w:rPr></w:style>',
    "SpxFigure": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxFigure"><w:name w:val="Spx Figure"/>'
                 '<w:basedOn w:val="Normal"/><w:next w:val="Caption"/>'
                 '<w:pPr><w:keepNext/><w:spacing w:before="120" w:after="0"/><w:jc w:val="center"/></w:pPr></w:style>',
    "SpxEquation": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxEquation">'
                   '<w:name w:val="Spx Equation"/><w:basedOn w:val="Normal"/>'
                   '<w:pPr><w:spacing w:before="60" w:after="60"/></w:pPr></w:style>',
    "SpxDefinitionTerm": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxDefinitionTerm">'
                         '<w:name w:val="Spx Definition Term"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
                         '<w:pPr><w:keepNext/><w:spacing w:after="0"/></w:pPr><w:rPr><w:b/></w:rPr></w:style>',
    "SpxBibliography": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxBibliography">'
                       '<w:name w:val="Spx Bibliography"/><w:basedOn w:val="Normal"/>'
                       '<w:pPr><w:ind w:left="567" w:hanging="567"/></w:pPr></w:style>',
    # Cover page and front matter of a contract report
    "SpxCoverTitle": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxCoverTitle">'
                     '<w:name w:val="Spx Cover Title"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:qFormat/>'
                     '<w:pPr><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/>'
                     '</w:pPr><w:rPr><w:rFonts w:ascii="Calibri Light" w:hAnsi="Calibri Light" w:cs="Calibri Light"/>'
                     '<w:sz w:val="40"/><w:szCs w:val="40"/></w:rPr></w:style>',
    "SpxCoverFigure": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxCoverFigure">'
                      '<w:name w:val="Spx Cover Figure"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
                      '<w:pPr><w:spacing w:before="240" w:after="240"/><w:jc w:val="center"/></w:pPr></w:style>',
    "SpxFrontHeading": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxFrontHeading">'
                       '<w:name w:val="Spx Front Heading"/><w:basedOn w:val="Normal"/><w:next w:val="Normal"/>'
                       '<w:qFormat/><w:pPr><w:keepNext/><w:spacing w:before="480" w:after="60"/></w:pPr>'
                       '<w:rPr><w:rFonts w:ascii="Calibri Light" w:hAnsi="Calibri Light" w:cs="Calibri Light"/>'
                       '<w:color w:val="2F5496"/><w:sz w:val="32"/><w:szCs w:val="32"/></w:rPr></w:style>',
    "SpxFrontTableText": '<w:style w:type="paragraph" w:customStyle="1" w:styleId="SpxFrontTableText">'
                         '<w:name w:val="Spx Front Table Text"/><w:basedOn w:val="Normal"/>'
                         '<w:pPr><w:spacing w:before="40" w:after="40" w:line="240" w:lineRule="auto"/></w:pPr>'
                         '</w:style>',
    "TableGrid": '<w:style w:type="table" w:styleId="SpxTable"><w:name w:val="Spx Table"/>'
                 '<w:basedOn w:val="TableNormal"/><w:uiPriority w:val="59"/>'
                 '<w:tblPr><w:tblBorders><w:top w:val="single" w:sz="8" w:space="0" w:color="4472C4"/>'
                 '<w:left w:val="nil"/><w:bottom w:val="single" w:sz="8" w:space="0" w:color="4472C4"/>'
                 '<w:right w:val="nil"/><w:insideH w:val="single" w:sz="4" w:space="0" w:color="BFBFBF"/>'
                 '<w:insideV w:val="single" w:sz="4" w:space="0" w:color="D9D9D9"/></w:tblBorders>'
                 '<w:tblCellMar><w:top w:w="29" w:type="dxa"/><w:left w:w="85" w:type="dxa"/>'
                 '<w:bottom w:w="29" w:type="dxa"/><w:right w:w="85" w:type="dxa"/></w:tblCellMar></w:tblPr>'
                 '<w:tblStylePr w:type="firstRow"><w:rPr><w:b/><w:color w:val="FFFFFF"/></w:rPr>'
                 '<w:tcPr><w:shd w:val="clear" w:color="auto" w:fill="4472C4"/></w:tcPr></w:tblStylePr></w:style>',
    "TableNormal": '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/>'
                   '<w:uiPriority w:val="99"/><w:semiHidden/><w:unhideWhenUsed/><w:tblPr><w:tblInd w:w="0" w:type="dxa"/>'
                   '<w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
                   '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>',
    "DefaultParagraphFont": '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont">'
                            '<w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/>'
                            '<w:unhideWhenUsed/></w:style>',
}
for _lvl in range(1, 10):
    DEFAULT_STYLE_DEFINITIONS[f"Heading{_lvl}"] = _heading_style(_lvl)
for _lvl in range(1, 7):
    DEFAULT_STYLE_DEFINITIONS[f"TOC{_lvl}"] = _toc_style(_lvl)
# Word's built-in style of the entries in a table of figures
DEFAULT_STYLE_DEFINITIONS["TableofFigures"] = (
    '<w:style w:type="paragraph" w:styleId="TableofFigures"><w:name w:val="table of figures"/>'
    '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/>'
    '<w:pPr><w:spacing w:after="60"/></w:pPr></w:style>')
# Word's built-in styles of an index (the INDEX field): letter headings and entries on two levels
DEFAULT_STYLE_DEFINITIONS["IndexHeading"] = (
    '<w:style w:type="paragraph" w:styleId="IndexHeading"><w:name w:val="index heading"/>'
    '<w:basedOn w:val="Normal"/><w:next w:val="Index1"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/>'
    '<w:pPr><w:keepNext/><w:spacing w:before="240" w:after="60"/></w:pPr>'
    '<w:rPr><w:b/><w:bCs/><w:color w:val="1F3864"/></w:rPr></w:style>')
for _lvl in (1, 2, 3):
    DEFAULT_STYLE_DEFINITIONS[f"Index{_lvl}"] = (
        f'<w:style w:type="paragraph" w:styleId="Index{_lvl}"><w:name w:val="index {_lvl}"/>'
        '<w:basedOn w:val="Normal"/><w:next w:val="Normal"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/>'
        f'<w:pPr><w:spacing w:after="0"/><w:ind w:left="{220 * _lvl}" w:hanging="220"/></w:pPr></w:style>')

# The dictionary key is the styleId used in the document, except the table style which is stored under TableGrid.
STYLE_IDS = {k: k for k in DEFAULT_STYLE_DEFINITIONS}
STYLE_IDS["TableGrid"] = "SpxTable"


def default_styles_xml(body_font: str = "Calibri", heading_font: str = "Calibri Light") -> str:
    doc_defaults = (
        f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{body_font}" w:eastAsia="{body_font}" '
        f'w:hAnsi="{body_font}" w:cs="{body_font}"/>'
        '<w:sz w:val="22"/><w:szCs w:val="22"/>'
        '<w:lang w:val="en-CA" w:eastAsia="en-US" w:bidi="ar-SA"/></w:rPr></w:rPrDefault>'
        '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="264" w:lineRule="auto"/></w:pPr></w:pPrDefault>'
        '</w:docDefaults>'
    )
    return (XML_HEADER + f'<w:styles xmlns:w="{W_NS}" xmlns:r="{R_NS}">' + doc_defaults
            + "".join(DEFAULT_STYLE_DEFINITIONS.values()) + "</w:styles>")


# ----------------------------------------------------------------------------------------------------------------------
#   Lists
# ----------------------------------------------------------------------------------------------------------------------

_BULLETS = ["•", "◦", "▪", "•", "◦", "▪", "•", "◦", "▪"]
_ENUM_FORMATS = {"arabic": "decimal", "loweralpha": "lowerLetter", "upperalpha": "upperLetter",
                 "lowerroman": "lowerRoman", "upperroman": "upperRoman"}


def _abstract_num(abstract_id: int, bullet: bool, enumtype: str = "arabic", prefix: str = "",
                  suffix: str = ".") -> str:
    levels = []
    for lvl in range(9):
        indent = 360 + 360 * (lvl + 1)
        if bullet:
            levels.append(
                f'<w:lvl w:ilvl="{lvl}"><w:start w:val="1"/><w:numFmt w:val="bullet"/>'
                f'<w:lvlText w:val="{_BULLETS[lvl]}"/><w:lvlJc w:val="left"/>'
                f'<w:pPr><w:ind w:left="{indent}" w:hanging="360"/></w:pPr>'
                f'<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:hint="default"/></w:rPr></w:lvl>')
        else:
            # docutils gives every enumerated list its own type, prefix and suffix, and each list gets its own
            # numbering instance, so all levels use the same format.
            fmt = _ENUM_FORMATS.get(enumtype, "decimal")
            text = f"{escape(prefix)}%{lvl + 1}{escape(suffix)}"
            levels.append(
                f'<w:lvl w:ilvl="{lvl}"><w:start w:val="1"/><w:numFmt w:val="{fmt}"/>'
                f'<w:lvlText w:val="{text}"/><w:lvlJc w:val="left"/>'
                f'<w:pPr><w:ind w:left="{indent}" w:hanging="360"/></w:pPr></w:lvl>')
    kind = "hybridMultilevel"
    return (f'<w:abstractNum w:abstractNumId="{abstract_id}"><w:multiLevelType w:val="{kind}"/>'
            + "".join(levels) + "</w:abstractNum>")


def _heading_abstract_num(abstract_id: int) -> str:
    """Outline numbering 1, 1.1, 1.1.1 ... linked to the Heading 1..9 styles."""
    levels = []
    for lvl in range(9):
        text = ".".join(f"%{i + 1}" for i in range(lvl + 1))
        width = 432 + 144 * lvl
        levels.append(
            f'<w:lvl w:ilvl="{lvl}"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
            f'<w:pStyle w:val="Heading{lvl + 1}"/><w:lvlText w:val="{text}"/><w:lvlJc w:val="left"/>'
            f'<w:pPr><w:ind w:left="{width}" w:hanging="{width}"/></w:pPr></w:lvl>')
    return (f'<w:abstractNum w:abstractNumId="{abstract_id}"><w:multiLevelType w:val="multilevel"/>'
            + "".join(levels) + "</w:abstractNum>")


def link_heading_numbering(styles_xml: str, num_id: int) -> str:
    """Give the Heading 1..9 styles outline numbering, unless a style already has its own numbering.

    The numbering is part of the styles, not of the paragraphs, so a heading pasted into another document with
    "use destination styles" takes that document's heading numbering.
    """
    def add_numpr(style: str, numpr: str) -> str:
        if "<w:numPr>" in style:
            return style                 # a template's own heading numbering wins
        if "<w:pPr>" in style:
            return style.replace("<w:pPr>", "<w:pPr>" + numpr, 1)
        if "<w:pPr/>" in style:
            return style.replace("<w:pPr/>", f"<w:pPr>{numpr}</w:pPr>", 1)
        # pPr comes before rPr and the table style properties in a style
        m = re.search(r"<w:(rPr|tblPr|trPr|tcPr|tblStylePr)\b", style)
        idx = m.start() if m else style.rfind("</w:style>")
        return style[:idx] + f"<w:pPr>{numpr}</w:pPr>" + style[idx:]

    styles_xml = re.sub(
        r'<w:style\b[^>]*w:styleId="Heading([1-9])"[^>]*>.*?</w:style>',
        lambda m: add_numpr(m.group(0), f'<w:numPr><w:ilvl w:val="{int(m.group(1)) - 1}"/>'
                                        f'<w:numId w:val="{num_id}"/></w:numPr>'),
        styles_xml, flags=re.S)
    # Styles based on a heading (TOC Heading) would inherit the numbering.
    return re.sub(r'<w:style\b[^>]*w:styleId="TOCHeading"[^>]*>.*?</w:style>',
                  lambda m: add_numpr(m.group(0), '<w:numPr><w:numId w:val="0"/></w:numPr>'), styles_xml, flags=re.S)


def list_indent(level: int) -> int:
    """Left indent (twips) of the text of a list item at the given 0-based level."""
    return 360 + 360 * (level + 1)


# ----------------------------------------------------------------------------------------------------------------------
#   Package
# ----------------------------------------------------------------------------------------------------------------------

@dataclass
class ImagePart:
    rid: str
    target: str          # media/image1.png
    content_type: str
    data: bytes


_CONTENT_TYPES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".gif": "image/gif",
                  ".bmp": "image/bmp", ".tif": "image/tiff", ".tiff": "image/tiff", ".svg": "image/svg+xml",
                  ".emf": "image/x-emf", ".wmf": "image/x-wmf"}


class DocxPackage:
    """Collects document parts and writes the .docx file."""

    def __init__(self, template: Optional[str] = None, paper: str = "letter", margins_inch: float = 1.0):
        self.template = template
        self.paper = paper.lower()
        self.margins = int(margins_inch * TWIPS_PER_INCH)
        self._rels: List[Tuple[str, str, str, bool]] = []       # rid, type, target, external
        self._images: List[ImagePart] = []
        self._image_cache: Dict[Tuple[str, int], ImagePart] = {}
        self._hyperlinks: Dict[str, str] = {}
        self._abstract_nums: List[str] = []
        self._nums: List[str] = []
        self._bullet_abstract: Optional[int] = None
        self.footnotes: List[Tuple[int, str]] = []
        self._next_rid = 10
        self.core: Dict[str, str] = {}
        self.update_fields_on_open = False
        self.heading_num_id: Optional[int] = None
        self.appendix_num_id: Optional[int] = None
        self.footer_text = ""

    # ------------------------------------------------------------------------------------------------ geometry
    @property
    def page_size(self) -> Tuple[int, int]:
        return PAPER_SIZES.get(self.paper, PAPER_SIZES["letter"])

    @property
    def text_width_twips(self) -> int:
        return self.page_size[0] - 2 * self.margins

    @property
    def text_width_emu(self) -> int:
        return self.text_width_twips * EMU_PER_INCH // TWIPS_PER_INCH

    @property
    def text_height_emu(self) -> int:
        return (self.page_size[1] - 2 * self.margins) * EMU_PER_INCH // TWIPS_PER_INCH

    # ---------------------------------------------------------------------------------------------- relationships
    def _new_rid(self) -> str:
        self._next_rid += 1
        return f"rId{self._next_rid}"

    def add_hyperlink(self, url: str) -> str:
        if url not in self._hyperlinks:
            rid = self._new_rid()
            self._hyperlinks[url] = rid
            self._rels.append((rid, f"{R_NS}/hyperlink", url, True))
        return self._hyperlinks[url]

    def add_image(self, data: bytes, ext: str) -> str:
        ext = ext.lower()
        key = (ext, hash(data))
        if key in self._image_cache:
            return self._image_cache[key].rid
        rid = self._new_rid()
        target = f"media/image{len(self._images) + 1}{ext}"
        part = ImagePart(rid, target, _CONTENT_TYPES.get(ext, "application/octet-stream"), data)
        self._images.append(part)
        self._image_cache[key] = part
        self._rels.append((rid, f"{R_NS}/image", target, False))
        return rid

    # ----------------------------------------------------------------------------------------------- numbering
    def new_list(self, bullet: bool, enumtype: str = "arabic", start: int = 1, prefix: str = "",
                 suffix: str = ".") -> int:
        """Create a list instance and return its numId. Each enumerated list restarts at ``start``."""
        if bullet:
            if self._bullet_abstract is None:
                self._bullet_abstract = len(self._abstract_nums)
                self._abstract_nums.append(_abstract_num(self._bullet_abstract, True))
            abstract = self._bullet_abstract
            num_id = len(self._nums) + 1
            self._nums.append(f'<w:num w:numId="{num_id}"><w:abstractNumId w:val="{abstract}"/></w:num>')
            return num_id
        abstract = len(self._abstract_nums)
        self._abstract_nums.append(_abstract_num(abstract, False, enumtype, prefix, suffix))
        num_id = len(self._nums) + 1
        self._nums.append(f'<w:num w:numId="{num_id}"><w:abstractNumId w:val="{abstract}"/>'
                          f'<w:lvlOverride w:ilvl="0"><w:startOverride w:val="{start}"/></w:lvlOverride></w:num>')
        return num_id

    def number_headings(self) -> int:
        """Create the outline numbering of the headings and return its numId."""
        if self.heading_num_id is None:
            abstract = len(self._abstract_nums)
            self._abstract_nums.append(_heading_abstract_num(abstract))
            self.heading_num_id = len(self._nums) + 1
            self._nums.append(f'<w:num w:numId="{self.heading_num_id}"><w:abstractNumId w:val="{abstract}"/></w:num>')
        return self.heading_num_id

    def number_appendices(self, label: str) -> int:
        """Numbering of appendix headings, "Appendix A:", "A.1", "A.1.1", and its numId.

        It is set on the heading paragraphs, not linked to the heading styles, so the chapters keep their numbers
        1, 2, 3 and the appendices count A, B, C on their own.
        """
        if self.appendix_num_id is None:
            abstract = len(self._abstract_nums)
            levels = [f'<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="upperLetter"/>'
                      f'<w:lvlText w:val="{escape(label)} %1:"/><w:lvlJc w:val="left"/><w:suff w:val="space"/>'
                      '<w:pPr><w:ind w:left="0" w:firstLine="0"/></w:pPr></w:lvl>']
            for lvl in (1, 2):
                text = ".".join(f"%{i + 1}" for i in range(lvl + 1))
                width = 432 + 144 * lvl
                levels.append(f'<w:lvl w:ilvl="{lvl}"><w:start w:val="1"/><w:numFmt w:val="decimal"/>'
                              f'<w:lvlText w:val="{text}"/><w:lvlJc w:val="left"/>'
                              f'<w:pPr><w:ind w:left="{width}" w:hanging="{width}"/></w:pPr></w:lvl>')
            self._abstract_nums.append(f'<w:abstractNum w:abstractNumId="{abstract}">'
                                       '<w:multiLevelType w:val="multilevel"/>' + "".join(levels) + "</w:abstractNum>")
            self.appendix_num_id = len(self._nums) + 1
            self._nums.append(f'<w:num w:numId="{self.appendix_num_id}"><w:abstractNumId w:val="{abstract}"/></w:num>')
        return self.appendix_num_id

    def _numbering_xml(self) -> str:
        return (XML_HEADER + f'<w:numbering xmlns:w="{W_NS}">' + "".join(self._abstract_nums)
                + "".join(self._nums) + "</w:numbering>")

    # ----------------------------------------------------------------------------------------------- footnotes
    def add_footnote(self, paragraphs_xml: str) -> int:
        fid = len(self.footnotes) + 1
        self.footnotes.append((fid, paragraphs_xml))
        return fid

    def _footnotes_xml(self) -> str:
        sep = ('<w:footnote w:type="separator" w:id="-1"><w:p><w:pPr><w:spacing w:after="0" w:line="240" '
               'w:lineRule="auto"/></w:pPr><w:r><w:separator/></w:r></w:p></w:footnote>'
               '<w:footnote w:type="continuationSeparator" w:id="0"><w:p><w:pPr><w:spacing w:after="0" '
               'w:line="240" w:lineRule="auto"/></w:pPr><w:r><w:continuationSeparator/></w:r></w:p></w:footnote>')
        notes = "".join(f'<w:footnote w:id="{fid}">{xml}</w:footnote>' for fid, xml in self.footnotes)
        return XML_HEADER + f"<w:footnotes {NAMESPACES}>" + sep + notes + "</w:footnotes>"

    # -------------------------------------------------------------------------------------------------- styles
    def _template_parts(self) -> Dict[str, bytes]:
        if not self.template:
            return {}
        parts = {}
        with zipfile.ZipFile(self.template) as z:
            for name in ("word/styles.xml", "word/theme/theme1.xml", "word/fontTable.xml"):
                if name in z.namelist():
                    parts[name] = z.read(name)
        return parts

    @staticmethod
    def merge_styles(template_styles: str) -> str:
        """Add the styles this writer uses to a template's styles.xml when the template does not define them."""
        present = set(re.findall(r'w:styleId="([^"]+)"', template_styles))
        missing = [xml for key, xml in DEFAULT_STYLE_DEFINITIONS.items() if STYLE_IDS[key] not in present]
        if not missing:
            return template_styles
        idx = template_styles.rfind("</w:styles>")
        return template_styles[:idx] + "".join(missing) + template_styles[idx:]

    # ----------------------------------------------------------------------------------------------- sections
    def section_properties(self, footer_rid: Optional[str], kind: str = "only", orientation: str = "portrait") -> str:
        """Properties of a section.

        ``kind``: "only" (the first section of a document without front matter), "front" (front matter, roman page
        numbers), "body" (the first section of the body, pages from 1) or "next" (a later section, pages
        continue). ``orientation``: "portrait" or "landscape".
        """
        w, h = self.page_size
        m = self.margins
        footer = f'<w:footerReference w:type="default" r:id="{footer_rid}"/>' if footer_rid else ""
        numbering = {"front": '<w:pgNumType w:fmt="lowerRoman" w:start="1"/>',
                     "body": '<w:pgNumType w:fmt="decimal" w:start="1"/>'}.get(kind, "")
        title_page = "<w:titlePg/>" if kind in ("only", "front") else ""     # no footer on the cover page
        size = f'<w:pgSz w:w="{w}" w:h="{h}"/>'
        if orientation == "landscape":
            size = f'<w:pgSz w:w="{h}" w:h="{w}" w:orient="landscape"/>'
        return (f'<w:sectPr>{footer}{size}'
                f'<w:pgMar w:top="{m}" w:right="{m}" w:bottom="{m}" w:left="{m}" w:header="708" w:footer="708" '
                f'w:gutter="0"/>{numbering}<w:cols w:space="708"/>{title_page}<w:docGrid w:linePitch="360"/>'
                '</w:sectPr>')

    def _footer_xml(self) -> str:
        page = ('<w:r><w:fldChar w:fldCharType="begin"/></w:r><w:r><w:instrText xml:space="preserve"> PAGE '
                '</w:instrText></w:r><w:r><w:fldChar w:fldCharType="separate"/></w:r><w:r><w:t>1</w:t></w:r>'
                '<w:r><w:fldChar w:fldCharType="end"/></w:r>')
        if self.footer_text:
            # text on the left, page number on the right margin (an absolute tab ignores the style's tab stops)
            return (XML_HEADER + f"<w:ftr {NAMESPACES}><w:p><w:pPr><w:pStyle w:val=\"Footer\"/>"
                    f'<w:jc w:val="left"/></w:pPr><w:r><w:t xml:space="preserve">{escape(self.footer_text)}</w:t></w:r>'
                    '<w:r><w:ptab w:relativeTo="margin" w:alignment="right" w:leader="none"/></w:r>'
                    f"{page}</w:p></w:ftr>")
        return (XML_HEADER + f"<w:ftr {NAMESPACES}><w:p><w:pPr><w:pStyle w:val=\"Footer\"/></w:pPr>"
                f"{page}</w:p></w:ftr>")

    # ------------------------------------------------------------------------------------------------- writing
    def save(self, filename: str, body_xml: str):
        template = self._template_parts()
        styles = template.get("word/styles.xml")
        styles_xml = self.merge_styles(styles.decode("utf-8")) if styles else default_styles_xml()
        if self.heading_num_id is not None:
            styles_xml = link_heading_numbering(styles_xml, self.heading_num_id)

        footer_rid = self._new_rid()
        self._rels.append((footer_rid, f"{R_NS}/footer", "footer1.xml", False))

        # The translator marks the end of the front matter and of landscape parts; they become section breaks. The
        # front matter has roman page numbers, the body starts at page 1, and later sections continue the numbers.
        has_front = FRONT_MATTER_END in body_xml
        count = [0]

        def kind(i: int) -> str:
            if i == 0:
                return "front" if has_front else "only"
            return "body" if i == 1 and has_front else "next"

        def section_break(m) -> str:
            i = count[0]
            count[0] += 1
            props = self.section_properties(footer_rid, kind(i), m.group(2) or "portrait")
            return f"<w:p><w:pPr>{props}</w:pPr></w:p>"

        body_xml = _SECTION_MARKER.sub(section_break, body_xml)
        last = self.section_properties(footer_rid, kind(count[0]))
        document = (XML_HEADER + f"<w:document {NAMESPACES}><w:body>" + body_xml + last + "</w:body></w:document>")

        theme_present = "word/theme/theme1.xml" in template
        rels = [
            ("rId1", f"{R_NS}/styles", "styles.xml", False),
            ("rId2", f"{R_NS}/settings", "settings.xml", False),
            ("rId3", f"{R_NS}/numbering", "numbering.xml", False),
            ("rId4", f"{R_NS}/footnotes", "footnotes.xml", False),
            ("rId6", f"{R_NS}/fontTable", "fontTable.xml", False),
        ] + self._rels
        if theme_present:
            rels.append(("rId5", f"{R_NS}/theme", "theme/theme1.xml", False))
        rels_xml = XML_HEADER + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
        for rid, typ, target, external in rels:
            mode = ' TargetMode="External"' if external else ""
            rels_xml += f'<Relationship Id="{rid}" Type="{typ}" Target={quoteattr(target)}{mode}/>'
        rels_xml += "</Relationships>"

        defaults = {ext: ct for ext, ct in _CONTENT_TYPES.items() if any(i.target.endswith(ext) for i in self._images)}
        content_types = (
            XML_HEADER + '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            + "".join(f'<Default Extension="{ext[1:]}" ContentType="{ct}"/>' for ext, ct in defaults.items())
            + '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.'
              'wordprocessingml.document.main+xml"/>'
            '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.styles+xml"/>'
            '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.settings+xml"/>'
            '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.numbering+xml"/>'
            '<Override PartName="/word/footnotes.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.footnotes+xml"/>'
            '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.footer+xml"/>'
            + ('<Override PartName="/word/theme/theme1.xml" ContentType="application/vnd.openxmlformats-'
               'officedocument.theme+xml"/>' if theme_present else '')
            +             '<Override PartName="/word/fontTable.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'wordprocessingml.fontTable+xml"/>'
            '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.'
            'core-properties+xml"/>'
            '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.'
            'extended-properties+xml"/>'
            "</Types>")

        root_rels = (
            XML_HEADER + '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            f'<Relationship Id="rId1" Type="{R_NS}/officeDocument" Target="word/document.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/'
            'core-properties" Target="docProps/core.xml"/>'
            f'<Relationship Id="rId3" Type="{R_NS}/extended-properties" Target="docProps/app.xml"/>'
            "</Relationships>")

        update = '<w:updateFields w:val="true"/>' if self.update_fields_on_open else ""
        settings = (XML_HEADER + f'<w:settings xmlns:w="{W_NS}" '
                    'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
                    f'{update}<w:defaultTabStop w:val="720"/><w:characterSpacingControl w:val="doNotCompress"/>'
                    '<w:footnotePr><w:footnote w:id="-1"/><w:footnote w:id="0"/></w:footnotePr>'
                    '<w:compat><w:compatSetting w:name="compatibilityMode" '
                    'w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
                    '<m:mathPr><m:mathFont m:val="Cambria Math"/><m:brkBin m:val="before"/>'
                    '<m:brkBinSub m:val="--"/><m:smallFrac m:val="0"/><m:dispDef/><m:lMargin m:val="0"/>'
                    '<m:rMargin m:val="0"/><m:defJc m:val="centerGroup"/><m:wrapIndent m:val="1440"/>'
                    '<m:intLim m:val="subSup"/><m:naryLim m:val="undOvr"/></m:mathPr>'
                    "</w:settings>")

        font_table = template.get("word/fontTable.xml") or (
            XML_HEADER + f'<w:fonts xmlns:w="{W_NS}"><w:font w:name="Calibri"/><w:font w:name="Cambria Math"/>'
            '<w:font w:name="Consolas"/><w:font w:name="Calibri Light"/></w:fonts>').encode("utf-8")
        theme = template.get("word/theme/theme1.xml")

        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        core = (XML_HEADER + '<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/'
                'core-properties" xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/'
                'terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
                'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
                f'<dc:title>{escape(self.core.get("title", ""))}</dc:title>'
                f'<dc:creator>{escape(self.core.get("author", ""))}</dc:creator>'
                f'<cp:version>{escape(self.core.get("version", ""))}</cp:version>'
                f'<dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
                f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified>'
                "</cp:coreProperties>")
        app = (XML_HEADER + '<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/'
               'extended-properties"><Application>sphinx2word</Application></Properties>')

        os.makedirs(os.path.dirname(os.path.abspath(filename)), exist_ok=True)
        with zipfile.ZipFile(filename, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", content_types)
            z.writestr("_rels/.rels", root_rels)
            z.writestr("docProps/core.xml", core)
            z.writestr("docProps/app.xml", app)
            z.writestr("word/document.xml", document)
            z.writestr("word/_rels/document.xml.rels", rels_xml)
            z.writestr("word/styles.xml", styles_xml)
            z.writestr("word/settings.xml", settings)
            z.writestr("word/numbering.xml", self._numbering_xml())
            z.writestr("word/footnotes.xml", self._footnotes_xml())
            z.writestr("word/footer1.xml", self._footer_xml())
            if theme:
                z.writestr("word/theme/theme1.xml", theme)
            z.writestr("word/fontTable.xml", font_table)
            for img in self._images:
                z.writestr("word/" + img.target, img.data)
