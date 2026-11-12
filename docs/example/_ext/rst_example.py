"""
A directive that shows reStructuredText and then what it makes.

The example document uses it to show the source of each feature next to the result::

    .. rst-example::

        Some *emphasis* and a footnote [#]_.

        .. [#] The footnote.

The content is shown as an ``rst`` code block and then parsed as normal content, so labels, figures, tables,
equations and footnotes inside it work as usual. It is not needed to use sphinx2word: copy the reST from the code
blocks into your own documents.
"""
from docutils import nodes
from sphinx.util.docutils import SphinxDirective


class RstExample(SphinxDirective):
    has_content = True

    def run(self):
        text = "\n".join(self.content)
        source = nodes.literal_block(text, text, language="rst", classes=["rst-example-source"])
        self.set_source_info(source)
        result = [source]
        # Parse into a plain Element, not a body element such as a container, so topics and sidebars are
        # allowed as they are outside the directive.
        container = nodes.Element()
        self.state.nested_parse(self.content, self.content_offset, container)
        # Return the parsed nodes themselves, not the container, so figures, tables and equations stay at the
        # level of the section, as they would be without the directive.
        result.extend(container.children)
        return result


def setup(app):
    app.add_directive("rst-example", RstExample)
    return {"version": "1.0", "parallel_read_safe": True, "parallel_write_safe": True}
