# SPDX-FileCopyrightText: 2021 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import markdown
import re

from markupsafe import Markup
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from typogrify.filters import typogrify

from . import gir, log, mdext


# The beginning of a gtk-doc code block:
#
# |[ (optional language identifier)
#
CODEBLOCK_START_RE = re.compile(
    r'''
    ^
    \s*
    \|\[
    \s*
    (?P<language>\<\!-- \s* language="\w+" \s* --\>)?
    \s*
    $
    ''',
    re.UNICODE | re.VERBOSE)

# The optional language identifier for a gtk-doc code block:
#
# <!-- language="..." -->
#
LANGUAGE_RE = re.compile(
    r'''
    ^
    \s*
    <!--
    \s*
    language="(?P<language>\w+)"
    \s*
    -->
    \s*
    $
    ''',
    re.UNICODE | re.VERBOSE)

# The ending of a gtk-doc code block:
#
# ]|
#
CODEBLOCK_END_RE = re.compile(
    r'''
    ^
    \s*
    \]\|
    \s*
    $
    ''',
    re.UNICODE | re.VERBOSE)

LINK_RE = re.compile(
    r'''
    \[
    (`)?
    (?P<fragment>alias|class|const|ctor|enum|error|flags|func|id|iface|method|property|signal|struct|vfunc)
    @
    (?P<endpoint>[\w\-_:\.]+)
    (`)?
    \]
    ''',
    re.VERBOSE)

LANGUAGE_MAP = {
    'c': 'c',
    'css': 'css',
    'plain': 'plain',
    'xml': 'xml',
}

MD_EXTENSIONS = [
    # Standard extensions
    'codehilite',
    'def_list',
    'fenced_code',
    'meta',
    'tables',
    'toc',

    # Local extensions
    mdext.GtkDocExtension(),
]

MD_EXTENSIONS_CONF = {
    'codehilite': {'guess_lang': False},
    'toc': {'permalink_class': 'md-anchor', 'permalink': ''},
}


def process_language(lang):
    if lang is None:
        return "plain"

    res = LANGUAGE_RE.match(lang)
    if res:
        language = res.group("language") or "plain"
    else:
        language = "plain"

    return LANGUAGE_MAP[language.lower()]


class LinkParseError(Exception):
    def __init__(self, fragment=None, rest=None, message="Unable to parse link"):
        self.fragment = fragment
        self.rest = rest
        self.message = message
        super().__init__(f"{self.message}: [{self.fragment}@{self.rest}]")


class LinkGenerator:
    def __init__(self, **kwargs):
        self._namespace = kwargs.get('namespace')
        self._fragment = kwargs.get('fragment', '')
        self._endpoint = kwargs.get('endpoint', '')
        self._no_link = kwargs.get('no_link', False)

        assert self._namespace is not None

        # Valid links:
        #
        # - [fragment@rest]
        # - [fragment@Namespace.rest]
        # - [fragment@OtherNamespace.res]
        if self._endpoint.startswith(f"{self._namespace.name}."):
            self._ns = self._namespace.name
            self._rest = self._endpoint[len(self._ns) + 1:]
            self._external = False
        elif '.' in self._endpoint:
            self._ns, self._rest = self._endpoint.split('.', maxsplit=1)
            self._external = True
        else:
            self._ns = self._namespace.name
            self._rest = self._endpoint
            self._external = False

        self._ns_lower = self._ns.lower()

        if self._fragment == 'id':
            t = self._namespace.find_symbol(self._endpoint)
            if isinstance(t, gir.Class) or \
               isinstance(t, gir.Interface) or \
               isinstance(t, gir.Record):
                self._fragment = 'method'
                self._func = f"{self._endpoint}()"
                self._name = t.name
                self._func_name = self._endpoint.replace(self._namespace.symbol_prefix[0] + '_', '')
                self._func_name = self._func_name.replace(t.symbol_prefix + '_', '')
            elif isinstance(t, gir.Function):
                self._fragment = 'func'
                self._func = f"{self._endpoint}()"
                self._func_name = self._endpoint.replace(self._namespace.symbol_prefix[0] + '_', '')
            else:
                self._fragment = None
        elif self._fragment in ['alias', 'class', 'const', 'enum', 'error', 'flags', 'iface', 'struct']:
            self._name = self._rest
            t = self._namespace.find_real_type(self._name)
            if t is not None and t.base_ctype is not None:
                self._type = t.base_ctype
            else:
                self._type = f"{self._ns}{self._name}"
        elif self._fragment == 'property':
            try:
                self._name, self._prop_name = self._rest.split(':')
            except ValueError:
                raise LinkParseError(self._fragment, self._rest, "Unable to parse property link")
            t = self._namespace.find_real_type(self._name)
            if t is not None and t.base_ctype is not None:
                self._type = t.base_ctype
            else:
                self._type = f"{self._ns}{self._name}"
        elif self._fragment == 'signal':
            try:
                self._name, self._signal_name = self._rest.split('::')
            except ValueError:
                raise LinkParseError(self._fragment, self._rest, "Unable to parse signal link")
            t = self._namespace.find_real_type(self._name)
            if t is not None and t.base_ctype is not None:
                self._type = t.base_ctype
            else:
                self._type = f"{self._ns}{self._name}"
        elif self._fragment in ['ctor', 'method']:
            try:
                self._name, self._func_name = self._rest.split('.')
            except ValueError:
                raise LinkParseError(self._fragment, self._rest, "Unable to parse method link")
            t = self._namespace.find_real_type(self._name)
            if t is not None:
                self._func = f"{self._namespace.symbol_prefix[0]}_{t.symbol_prefix}_{self._func_name}()"
            else:
                self._func = f"{self._ns_lower}_{self._func_name}()"
        elif self._fragment == 'vfunc':
            try:
                self._name, self._func_name = self._rest.split('.')
            except ValueError:
                raise LinkParseError(self._fragment, self._rest, "Unable to parse vfunc link")
            t = self._namespace.find_real_type(self._name)
            if t is not None and t.base_ctype is not None:
                self._type = t.base_ctype
            else:
                self._type = f"{self._ns}{self._name}"
        elif self._fragment == 'func':
            self._func_name = self._rest
            t = self._namespace.find_function(self._func_name)
            if t is not None:
                self._func = f"{t.identifier}()"
            else:
                self._func = f"{self._ns_lower}_{self._rest}()"
        else:
            log.warning(f"Unknown fragment '{self._fragment}' in link [{self._fragment}@{self._endpoint}]")

    @property
    def text(self):
        if self._fragment in ['alias', 'class', 'const', 'enum', 'error', 'flags', 'iface', 'struct']:
            return f"`{self._type}`"
        elif self._fragment == 'property':
            return f"`{self._type}:{self._prop_name}`"
        elif self._fragment == 'signal':
            return f"`{self._type}::{self._signal_name}`"
        elif self._fragment in ['ctor', 'func', 'method']:
            return f"`{self._func}`"
        elif self._fragment == 'vfunc':
            return f"`{self._type}.{self._func_name}`"
        else:
            return f"`{self._ns}.{self._rest}`"

    @property
    def href(self):
        if self._external:
            return None
        elif self._fragment in ['alias', 'class', 'const', 'enum', 'error', 'flags', 'iface', 'struct']:
            return f"{self._fragment}.{self._name}.html"
        elif self._fragment == 'property':
            return f"property.{self._name}.{self._prop_name}.html"
        elif self._fragment == 'signal':
            return f"signal.{self._name}.{self._signal_name}.html"
        elif self._fragment in ['ctor', 'method', 'vfunc']:
            return f"{self._fragment}.{self._name}.{self._func_name}.html"
        elif self._fragment == 'func':
            return f"func.{self._func_name}.html"
        else:
            return None

    def __str__(self):
        text = self.text
        href = self.href
        if self._no_link or href is None:
            return text
        return f"[{text}]({href})"


def preprocess_docs(text, namespace, summary=False, md=None, extensions=[]):
    processed_text = []

    code_block_text = []
    code_block_language = None
    inside_code_block = False
    for line in text.split("\n"):
        # If we're in "summary" mode, we bail out at the first empty line
        # after a paragraph
        if summary and line == '' and len(processed_text) > 0:
            break

        res = CODEBLOCK_START_RE.match(line)
        if res:
            code_block_language = process_language(res.group("language"))
            inside_code_block = True
            continue

        res = CODEBLOCK_END_RE.match(line)
        if res and inside_code_block:
            if code_block_language == "plain":
                processed_text += ["```"]
                processed_text.extend(code_block_text)
                processed_text += ["```"]
            else:
                lexer = get_lexer_by_name(code_block_language)
                formatter = HtmlFormatter()
                code_block = highlight("\n".join(code_block_text), lexer, formatter)
                processed_text += [""]
                processed_text.extend(code_block.split("\n"))
                processed_text += [""]

            code_block_language = None
            code_block_text = []
            inside_code_block = False
            continue

        if inside_code_block:
            code_block_text.append(line)
        else:
            new_line = []
            idx = 0
            for m in LINK_RE.finditer(line, idx):
                fragment = m.group('fragment')
                endpoint = m.group('endpoint')
                link = LinkGenerator(namespace=namespace, fragment=fragment, endpoint=endpoint, no_link=summary)
                start = m.start()
                end = m.end()
                left_pad = line[idx:start]
                replacement = re.sub(LINK_RE, str(link), line[start:end])
                new_line.append(left_pad)
                new_line.append(replacement)
                idx = end
            new_line.append(line[idx:])

            if len(new_line) == 0:
                processed_text.append(line)
            else:
                processed_text.append("".join(new_line))

    if md is None:
        md_ext = extensions.copy()
        md_ext.extend(MD_EXTENSIONS)
        text = markdown.markdown("\n".join(processed_text),
                                 extensions=md_ext,
                                 extension_configs=MD_EXTENSIONS_CONF)
    else:
        text = md.convert("\n".join(processed_text))

    return Markup(typogrify(text))


def code_highlight(text, language='c'):
    lexer = get_lexer_by_name(language)
    formatter = HtmlFormatter()
    return Markup(highlight(text, lexer, formatter))
