"""
Make the pictures of Word pages shown on example.md (docs/images/example-*.png).

Needs Windows with Word, pywin32 and PyMuPDF (all in the dev group). Builds the example with Word filling in the
fields, saves it as PDF with Word, and saves the pages that show the chosen headings as PNG. Run it after changing
the example, and look at the pictures:

    python docs/make_example_images.py
"""
import os
import subprocess
import sys
import tempfile

import pymupdf
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "tests"))
from render_with_word import docx_to_pdf  # noqa: E402

# Picture name -> text on the page to show (None: the first page, the cover)
PAGES = {"cover": None, "text": "Inline Markup", "math": "Solar Model"}
WIDTH = 900


def main():
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run([sys.executable, "-m", "sphinx", "-b", "word", "-E", "-q", "-D", "word_update_fields=word",
                        os.path.join(HERE, "example"), tmp], check=True)
        pdf = os.path.join(tmp, "bigsat_atbd.pdf")
        docx_to_pdf(os.path.join(tmp, "bigsat_atbd.docx"), pdf)
        os.makedirs(os.path.join(HERE, "images"), exist_ok=True)
        with pymupdf.open(pdf) as document:
            for name, text in PAGES.items():
                # The last page with the text, so a heading is not found in the table of contents
                page = document[0] if text is None else [p for p in document if p.search_for(text)][-1]
                pixmap = page.get_pixmap(matrix=pymupdf.Matrix(2, 2))
                image = Image.frombytes("RGB", (pixmap.width, pixmap.height), pixmap.samples)
                image = image.resize((WIDTH, round(image.height * WIDTH / image.width)), Image.LANCZOS)
                image = image.quantize(colors=128, method=Image.Quantize.MEDIANCUT)
                path = os.path.join(HERE, "images", f"example-{name}.png")
                image.save(path, optimize=True)
                print(f"wrote {path} (page {page.number + 1})")


if __name__ == "__main__":
    main()
