"""
Developer tool (Windows only): open a .docx in Microsoft Word, save it as PDF and render the pages as PNG images.

sphinx2word does not need Word. This script only exists so that the output can be checked by eye, and so that
we learn early if Word reports a file as damaged. It needs ``pywin32`` and ``pymupdf``.

    python tests/render_with_word.py path/to/file.docx [outdir] [--no-update]
"""

import os
import sys


def docx_to_pdf(docx: str, pdf: str, update: bool = True):
    import pythoncom
    import win32com.client

    pythoncom.CoInitialize()
    word = win32com.client.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = 0
    try:
        doc = word.Documents.Open(os.path.abspath(docx), ConfirmConversions=False, ReadOnly=True,
                                  AddToRecentFiles=False, OpenAndRepair=False, NoEncodingDialog=True)
        try:
            if update:
                doc.Fields.Update()
                for toc in doc.TablesOfContents:
                    toc.Update()
                for index in doc.Indexes:
                    index.Update()
            doc.ExportAsFixedFormat(os.path.abspath(pdf), 17)   # wdExportFormatPDF
        finally:
            doc.Close(False)
    finally:
        word.Quit()


def pdf_to_png(pdf: str, outdir: str, zoom: float = 1.5):
    try:
        import pymupdf as fitz      # PyMuPDF 1.24.3 and later
    except ImportError:
        import fitz

    os.makedirs(outdir, exist_ok=True)
    pages = []
    with fitz.open(pdf) as d:
        for i, page in enumerate(d):
            name = os.path.join(outdir, f"page{i + 1:02d}.png")
            page.get_pixmap(matrix=fitz.Matrix(zoom, zoom)).save(name)
            pages.append(name)
    return pages


if __name__ == "__main__":
    # --no-update: show the document as it is, without updating its fields (as a file built without Word opens
    # when the update is declined, or with word_update_fields = "none")
    args = [a for a in sys.argv[1:] if a != "--no-update"]
    docx = args[0]
    outdir = args[1] if len(args) > 1 else os.path.splitext(docx)[0] + "_pages"
    pdf = os.path.splitext(docx)[0] + ".pdf"
    docx_to_pdf(docx, pdf, update="--no-update" not in sys.argv)
    for p in pdf_to_png(pdf, outdir):
        print(p)
