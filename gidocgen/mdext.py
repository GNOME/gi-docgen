# SPDX-FileCopyrightText: 2021 GNOME Foundation <https://gnome.org>
# SPDX-FileCopyrightText: The Python Markdown Project
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later
# SPDX-License-Identifier: BSD-2-Clause

from markdown.extensions import Extension
from markdown.blockprocessors import BlockProcessor
from markdown.preprocessors import Preprocessor

import xml.etree.ElementTree as etree
import re


SIGNAL_SIGIL_RE = re.compile(r"(^|\W)#([A-Z][A-Za-z0-9]+)::([a-z0-9_-]+)\b")

PROP_SIGIL_RE = re.compile(r"(^|\W)#([A-Z][A-Za-z0-9]+):([a-z0-9_-]+)\b")

TYPE_SIGIL_RE = re.compile(r"(^|\W)#([A-Z][A-Za-z0-9]+)\b")

ARG_SIGIL_RE = re.compile(r"(^|\W)@([A-Za-z0-9_]+)\b")

CONST_SIGIL_RE = re.compile(r"(^|\W)%([A-Z0-9_]+)\b")

FUNCTION_RE = re.compile(r"(^|\s+)([a-z][a-z0-9_]*)\(\)(\s+|$)")


def process_gtkdoc_sigils(line: str) -> str:
    # XXX: The order is important; signals and properties have
    # higher precedence than types
    new_line = line

    # Signal sigil
    new_line = re.sub(SIGNAL_SIGIL_RE, r"\g<1>`\g<2>::\g<3>`", new_line)

    # Property sigil
    new_line = re.sub(PROP_SIGIL_RE, r"\g<1>`\g<2>:\g<3>`", new_line)

    # Type sigil
    new_line = re.sub(TYPE_SIGIL_RE, r"\g<1>`\g<2>`", new_line)

    # Constant sygil
    new_line = re.sub(CONST_SIGIL_RE, r"\g<1>`\g<2>`", new_line)

    # Argument sygil
    new_line = re.sub(ARG_SIGIL_RE, r"\g<1>`\g<2>`", new_line)

    # Function
    new_line = re.sub(FUNCTION_RE, r"\g<1>`\g<2>()`\g<3>", new_line)

    return new_line


class GtkDocPreprocessor(Preprocessor):
    """Remove all gtk-doc sigils from the Markdown text"""
    def run(self, lines):
        new_lines = []
        inside_code_block = False
        for line in lines:
            if line.startswith("```"):
                if not inside_code_block:
                    inside_code_block = True
                else:
                    inside_code_block = False

            new_line = line

            # Never transform code blocks
            if not inside_code_block:
                new_line = process_gtkdoc_sigils(new_line)

            new_lines.append(new_line)
        return new_lines


class GtkDocExtension(Extension):
    """Markdown extension for gtk-doc"""
    def extendMarkdown(self, md):
        """Add extensions"""
        md.preprocessors.register(GtkDocPreprocessor(md), 'gtkdoc', 27)


class AdmonitionProcessor(BlockProcessor):
    """
    The AdmonitionProcessor class from Python-Markdown, modified to
    use a different preamble marker, and with fallback for known
    admonition titles.
    """

    CLASSNAME = 'admonition'
    CLASSNAME_TITLE = 'admonition-title'
    RE = re.compile(r'(?:^|\n)::: ?([\w\-]+(?: +[\w\-]+)*)(?: +"(.*?)")? *(?:\n|$)')
    RE_SPACES = re.compile('  +')
    ADMONITION_TITLE = {
        'note': 'Note',
        'important': 'Important',
        'warning': 'Warning',
        'seealso': 'See also',
        'tip': 'Tip',
        'hint': 'Hint',
    }

    def __init__(self, parser):
        """Initialization."""

        super().__init__(parser)

        self.current_sibling = None
        self.content_indention = 0

    def parse_content(self, parent, block):
        """Get sibling admonition.

        Retrieve the appropriate sibling element. This can get tricky when
        dealing with lists.

        """

        old_block = block
        the_rest = ''

        # We already acquired the block via test
        if self.current_sibling is not None:
            sibling = self.current_sibling
            block, the_rest = self.detab(block, self.content_indent)
            self.current_sibling = None
            self.content_indent = 0
            return sibling, block, the_rest

        sibling = self.lastChild(parent)

        if sibling is None or sibling.tag != 'div' or sibling.get('class', '').find(self.CLASSNAME) == -1:
            sibling = None
        else:
            # If the last child is a list and the content is sufficiently indented
            # to be under it, then the content's sibling is in the list.
            last_child = self.lastChild(sibling)
            indent = 0
            while last_child is not None:
                if (
                    sibling is not None and block.startswith(' ' * self.tab_length * 2)
                    and last_child is not None and last_child.tag in ('ul', 'ol', 'dl')
                ):

                    # The expectation is that we'll find an `<li>` or `<dt>`.
                    # We should get its last child as well.
                    sibling = self.lastChild(last_child)
                    last_child = self.lastChild(sibling) if sibling is not None else None

                    # Context has been lost at this point, so we must adjust the
                    # text's indentation level so it will be evaluated correctly
                    # under the list.
                    block = block[self.tab_length:]
                    indent += self.tab_length
                else:
                    last_child = None

            if not block.startswith(' ' * self.tab_length):
                sibling = None

            if sibling is not None:
                indent += self.tab_length
                block, the_rest = self.detab(old_block, indent)
                self.current_sibling = sibling
                self.content_indent = indent

        return sibling, block, the_rest

    def test(self, parent, block):

        if self.RE.search(block):
            return True
        else:
            return self.parse_content(parent, block)[0] is not None

    def run(self, parent, blocks):
        block = blocks.pop(0)
        m = self.RE.search(block)

        if m:
            if m.start() > 0:
                self.parser.parseBlocks(parent, [block[:m.start()]])
            block = block[m.end():]  # removes the first line
            block, theRest = self.detab(block)
        else:
            sibling, block, theRest = self.parse_content(parent, block)

        if m:
            klass, title = self.get_class_and_title(m)
            div = etree.SubElement(parent, 'div')
            div.set('class', '{} {}'.format(self.CLASSNAME, klass))
            if title:
                p = etree.SubElement(div, 'p')
                p.text = title
                p.set('class', self.CLASSNAME_TITLE)
        else:
            # Sibling is a list item, but we need to wrap it's content should be wrapped in <p>
            if sibling.tag in ('li', 'dd') and sibling.text:
                text = sibling.text
                sibling.text = ''
                p = etree.SubElement(sibling, 'p')
                p.text = text

            div = sibling

        self.parser.parseChunk(div, block)

        if theRest:
            # This block contained unindented line(s) after the first indented
            # line. Insert these lines as the first block of the master blocks
            # list for future processing.
            blocks.insert(0, theRest)

    def get_class_and_title(self, match):
        klass, title = match.group(1).lower(), match.group(2)
        klass = self.RE_SPACES.sub(' ', klass)
        if title is None:
            if klass in self.ADMONITION_TITLE:
                # Use one of the known titles, for consistency
                title = self.ADMONITION_TITLE[klass]
            else:
                # no title was provided, use the capitalized class name as title
                # e.g.: `::: foo` will render
                # `<p class="admonition-title">Foo</p>`
                title = klass.split(' ', 1)[0].capitalize()
        elif title == '':
            # an explicit blank title should not be rendered
            # e.g.: `!!! warning ""` will *not* render `p` with a title
            title = None
        return klass, title


class AdmonitionExtension(Extension):
    """Notice extension"""
    def extendMarkdown(self, md):
        """Add extensions"""
        md.registerExtension(self)
        md.parser.blockprocessors.register(AdmonitionProcessor(md.parser), 'admonition', 105)
