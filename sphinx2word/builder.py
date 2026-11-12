"""
Sphinx builder that writes the whole project as one Word document (``-b word``).

The builder assembles a single doctree from the master document (like the ``singlehtml`` and LaTeX builders),
resolves all references and hands it to :class:`~sphinx2word.translator.WordTranslator`. No Microsoft Word
installation is needed; the ``.docx`` file is written directly.
"""

from __future__ import annotations

import os
from os import path

from docutils import nodes
from sphinx import addnodes
from sphinx.builders import Builder
from sphinx.util import logging
from sphinx.util.console import darkgreen
from sphinx.util.nodes import inline_all_toctrees

from .docx_package import DocxPackage
from .translator import WordTranslator, find_all
from .word_finish import finish_fields

logger = logging.getLogger(__name__)


class WordBuilder(Builder):
    name = "word"
    format = "word"
    epilog = "The Word document is in %(outdir)s."
    out_suffix = ".docx"
    supported_image_types = ["image/svg+xml", "image/png", "image/jpeg", "image/gif", "image/bmp", "image/tiff"]
    supported_remote_images = False
    default_translator_class = WordTranslator

    def init(self):
        pass

    def get_outdated_docs(self):
        return "all documents"

    def get_target_uri(self, docname: str, typ: str = None) -> str:
        # Everything is in one document: point at the bookmark placed at the start of each source file.
        if docname in self.env.all_docs:
            return "#document-" + docname
        return docname

    def get_relative_uri(self, from_: str, to: str, typ: str = None) -> str:
        return self.get_target_uri(to, typ)

    def output_filename(self) -> str:
        name = self.config.word_filename
        if not name:
            name = self.config.project or "document"
            if self.config.version:
                name = f"{name}-{self.config.version}"
        if not name.lower().endswith(".docx"):
            name += ".docx"
        return path.join(self.outdir, name)

    def assemble_doctree(self) -> nodes.document:
        master = self.config.master_doc
        tree = self.env.get_doctree(master)
        tree = inline_all_toctrees(self, set(), master, tree, darkgreen, [master])
        tree["docname"] = master
        self.add_appendices(tree)
        self.env.resolve_references(tree, master, self)
        # Choose a file for each image, as the other builders do: "figures/x.*" becomes the first of
        # supported_image_types that exists (SVG, then PNG, JPEG, ...).
        self.post_process_images(tree)
        return tree

    def add_appendices(self, tree: nodes.document):
        """Put the documents of ``word_appendices`` at the end, marked as appendices (numbered A, B, C).

        A document that the toctree already brought in is moved to the end; any other is added there, as LaTeX's
        ``latex_appendices`` does. They go inside the master document's title section, if it has one, so that their
        titles are headings of level 1 like the chapters.
        """
        appendices = list(self.config.word_appendices or [])
        if not appendices:
            return
        sections = [c for c in tree.children if isinstance(c, nodes.section)]
        container = sections[0] if len(sections) == 1 else tree
        for docname in appendices:
            if docname not in self.env.all_docs:
                logger.warning("sphinx2word: word_appendices: there is no document %r", docname)
                continue
            found = [n for n in find_all(tree, addnodes.start_of_file) if n.get("docname") == docname]
            if found:
                node = found[0]
                node.parent.remove(node)
            else:
                doctree = self.env.get_doctree(docname)
                doctree = inline_all_toctrees(self, set(), docname, doctree, darkgreen, [docname])
                node = addnodes.start_of_file(docname=docname)
                node.extend(doctree.children)
            node["word_appendix"] = True
            container.append(node)

    def prepare_writing(self, docnames):
        pass

    def write_documents(self, docnames):
        # Sphinx >= 7.4 calls write_documents(); older versions call write() (below)
        self._write_word()

    def write(self, *args, **kwargs):
        self._write_word()

    def _write_word(self):
        logger.info("assembling single document... ", nonl=True)
        doctree = self.assemble_doctree()
        logger.info("done")

        template = self.config.word_template
        if template and not path.isabs(template):
            template = path.join(self.confdir, template)
        if template and not path.exists(template):
            logger.warning("sphinx2word: word_template %s does not exist; using the built-in styles", template)
            template = None

        package = DocxPackage(template=template, paper=self.config.word_paper_size,
                              margins_inch=float(self.config.word_margins_inch))
        package.core = {"title": self.config.project or "", "author": str(self.config.author or ""),
                        "version": str(self.config.version or "")}
        translator = WordTranslator(doctree, self, package)
        logger.info("writing Word document... ", nonl=True)
        doctree.walkabout(translator)
        filename = self.output_filename()
        try:
            package.save(filename, translator.body_xml())
        except PermissionError:
            logger.warning("sphinx2word: cannot write %s. Is it open in Word?", filename)
            return
        logger.info("done")
        finish_fields(filename, self.config.word_update_fields, package.update_fields_on_open)
        if translator.math_errors:
            logger.warning("sphinx2word: %d equation(s) could not be converted and are shown as red LaTeX text",
                           translator.math_errors)
        logger.info("sphinx2word: wrote %s", os.path.relpath(filename))

    def finish(self):
        pass
