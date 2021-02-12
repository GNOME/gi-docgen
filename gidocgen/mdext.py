# SPDX-FileCopyrightText: 2021 GNOME Foundation <https://gnome.org>
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

from markdown.extensions import Extension
from markdown.preprocessors import Preprocessor
from markdown.inlinepatterns import InlineProcessor
import re
import xml.etree.ElementTree as etree


SIGNAL_SIGIL_RE = re.compile(r"(^|\W)#([A-Z][A-Za-z0-9]+)::([a-z0-9_-]+)\b")

PROP_SIGIL_RE = re.compile(r"(^|\W)#([A-Z][A-Za-z0-9]+):([a-z0-9_-]+)\b")

TYPE_SIGIL_RE = re.compile(r"(^|\W)#([A-Z][A-Za-z0-9]+)\b")

ARG_SIGIL_RE = re.compile(r"(^|\W)@([A-Za-z0-9_]+)\b")

CONST_SIGIL_RE = re.compile(r"(^|\W)%([A-Z0-9_]+)\b")


class GtkDocPreprocessor(Preprocessor):
    """Remove all gtk-doc sigils from the Markdown text"""
    def run(self, lines):
        new_lines = []
        for line in lines:
            new_line = line
            # XXX: The order is important; signals and properties have
            # higher precedence than types

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

            new_lines.append(new_line)
        return new_lines


class GtkDocExtension(Extension):
    """Markdown extension for gtk-doc"""
    def extendMarkdown(self, md):
        """Add extensions"""
        md.preprocessors.register(GtkDocPreprocessor(md), 'gtkdoc', 27)


PLAIN_LINK_RE = \
    r'\[(`)?(?P<fragment>alias|class|const|ctor|enum|error|field|flags|func|iface|method|property|struct|vfunc)@(?P<endpoint>[\w\-_:\.]+)(`)?\]'  # noqa: E501


def create_link(href, text):
    a = etree.Element("a")
    a.set("href", href)
    a.text = f"<code>{text}</code>"
    return a


class LinkInlineProcessor(InlineProcessor):
    def _handle_class(self, m, endpoint):
        ns, name = endpoint.split('.')
        return create_link(f"class.{name}.html", f"{ns}{name}")

    def _handle_enum(self, m, endpoint):
        ns, name = endpoint.split('.')
        return create_link(f"enum.{name}.html", f"{ns}{name}")

    def _handle_iface(self, m, endpoint):
        ns, name = endpoint.split('.')
        return create_link(f"iface.{name}.html", f"{ns}{name}")

    def _handle_property(self, m, endpoint):
        ns, rest = endpoint.split('.')
        name, prop_name = rest.split(':')
        return create_link(f"property.{name}.{prop_name}.html", f"{ns}{name}:{prop_name}")

    def _handle_signal(self, m, endpoint):
        ns, rest = endpoint.split('.')
        name, signal_name = rest.split('::')
        return create_link(f"signal.{name}.{signal_name}.html", f"{ns}{name}::{signal_name}")

    def handleMatch(self, m, data):
        fragment = m.group('fragment')
        endpoint = m.group('endpoint')

        fragment_process = {
            'class': self._handle_class,
            'enum': self._handle_enum,
            'iface': self._handle_iface,
            'prop': self._handle_property,
            'signal': self._handle_signal,
        }

        if fragment and endpoint:
            fragment_handler = fragment_process.get(fragment)
            if fragment_handler is not None:
                return fragment_handler(m, endpoint), m.start(0), m.end(0)
        return None, None, None


class LinkExtension(Extension):
    def extendMarkdown(self, md):
        md.inlinePatterns.register(LinkInlineProcessor(PLAIN_LINK_RE, self), 'link', 175)
