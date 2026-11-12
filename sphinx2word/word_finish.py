"""
Optional last step on Windows: let Microsoft Word fill in the fields of the finished document.

sphinx2word writes the .docx itself and does not need Word. Only Word can lay out the pages, so the page numbers of
the table of contents and the lists of figures and tables are not known when the file is written. Without this step
the file asks Word to update its fields when it is opened, and Word shows a prompt. With it, Word (if installed, with
``pywin32``) opens the document once in the background, updates every field, saves it, and the update-on-open flag
is removed, so the document opens without a prompt and with a complete table of contents.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
import zipfile

from sphinx.util import logging

logger = logging.getLogger(__name__)


def word_available() -> bool:
    if os.name != "nt":
        return False
    try:
        import win32com.client  # noqa: F401
    except ImportError:
        return False
    return True


def update_fields_in_word(filename: str) -> bool:
    """Open ``filename`` in a hidden Word, update all fields, tables of contents and figures, and save it.

    Returns False (and leaves the file as it was) if Word cannot be started or fails.
    """
    try:
        import pythoncom
        import win32com.client
    except ImportError:
        return False
    path = os.path.abspath(filename)
    pythoncom.CoInitialize()
    word = None
    try:
        word = win32com.client.DispatchEx("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0            # wdAlertsNone
        doc = word.Documents.Open(path, ConfirmConversions=False, ReadOnly=False, AddToRecentFiles=False,
                                  Visible=False, NoEncodingDialog=True)
        try:
            doc.Fields.Update()
            for toc in doc.TablesOfContents:
                toc.Update()
            for tof in doc.TablesOfFigures:
                tof.Update()
            for index in doc.Indexes:
                index.Update()
            # The tables are in the front matter, which has its own page numbers, so the body does not move;
            # update once more so that fields inside the tables (and any REF to them) are current.
            doc.Fields.Update()
            doc.Save()
        finally:
            doc.Close(False)
        return True
    except Exception as exc:          # COM errors have many types
        logger.warning("sphinx2word: Word could not update the fields of %s (%s); Word will ask to update them "
                       "when the document is opened", filename, exc)
        return False
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass
        pythoncom.CoUninitialize()


def remove_update_fields_flag(filename: str):
    """Remove ``<w:updateFields>`` from word/settings.xml, so Word does not prompt when the file is opened."""
    with zipfile.ZipFile(filename) as z:
        if "word/settings.xml" not in z.namelist():
            return
        settings = z.read("word/settings.xml").decode("utf-8")
        if "updateFields" not in settings:
            return
        items = [(info, z.read(info.filename)) for info in z.infolist()]
    settings = re.sub(r"<w:updateFields\b[^>]*/>", "", settings)
    fd, tmp = tempfile.mkstemp(suffix=".docx", dir=os.path.dirname(os.path.abspath(filename)))
    os.close(fd)
    try:
        with zipfile.ZipFile(tmp, "w", zipfile.ZIP_DEFLATED) as out:
            for info, data in items:
                if info.filename == "word/settings.xml":
                    data = settings.encode("utf-8")
                out.writestr(info, data)
        shutil.move(tmp, filename)
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)


def finish_fields(filename: str, mode: str, has_fields: bool):
    """Apply ``word_update_fields``: "auto", "word", "prompt" or "none"."""
    mode = (mode or "auto").lower()
    if not has_fields or mode == "prompt":
        return
    if mode == "none":
        remove_update_fields_flag(filename)
        return
    if not word_available():
        if mode == "word":
            logger.warning("sphinx2word: word_update_fields = 'word' needs Microsoft Word and pywin32 on Windows; "
                           "Word will ask to update the fields when the document is opened")
        else:
            logger.info("sphinx2word: Word is not available, so Word will ask to update the table of contents "
                        "when the document is opened")
        return
    logger.info("sphinx2word: updating the table of contents and page numbers in Word... ", nonl=True)
    if update_fields_in_word(filename):
        remove_update_fields_flag(filename)
        logger.info("done")
