# SPDX-FileCopyrightText: 2021 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import markdown
import re

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
    (?P<fragment>alias|class|const|ctor|enum|error|flags|func|id|iface|method|property|struct|vfunc)
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


class LinkGenerator:
    def __init__(self, **kwargs):
        self._namespace = kwargs.get('namespace')
        self._fragment = kwargs.get('fragment', '')
        self._endpoint = kwargs.get('endpoint', '')

        if '.' in self._endpoint:
            self._ns, self._rest = self._endpoint.split('.', maxsplit=1)
        else:
            self._ns = ''
            self._rest = self._endpoint

        if self._namespace is not None:
            self._ns = self._namespace.name

        if self._fragment == 'id':
            if self._namespace is not None:
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
            else:
                self._fragment = None
        elif self._fragment in ['alias', 'class', 'const', 'enum', 'error', 'flags', 'iface', 'struct']:
            self._name = self._rest
            if self._namespace is not None:
                t = self._namespace.find_real_type(self._name)
                if t is not None:
                    self._type = t.ctype
                else:
                    self._type = f"{self._namespace.identifier_prefix[0]}{self._name}"
            else:
                self._type = f"{self._ns}{self._name}"
        elif self._fragment == 'property':
            self._name, self._prop_name = self._rest.split(':')
            if self._namespace is not None:
                t = self._namespace.find_real_type(self._name)
                if t is not None:
                    self._type = t.ctype
                else:
                    self._type = f"{self._namespace.identifier_prefix[0]}{self._name}"
            else:
                self._type = f"{self._ns}{self._name}"
        elif self._fragment == 'signal':
            self._name, self._signal_name = self._rest.split('::')
            if self._namespace is not None:
                t = self._namespace.find_real_type(self._name)
                if t is not None:
                    self._type = t.ctype
                else:
                    self._type = f"{self._namespace.identifier_prefix[0]}{self._name}"
            else:
                self._type = f"{self._ns}{self._name}"
        elif self._fragment in ['ctor', 'method']:
            self._name, self._func_name = self._rest.split('.')
            if self._namespace is not None:
                t = self._namespace.find_real_type(self._name)
                if t is not None:
                    self._func = f"{self._namespace.symbol_prefix[0]}_{t.symbol_prefix}_{self._func_name}()"
                else:
                    self._func = f"{self._namespace.symbol_prefix[0]}_{self._func_name}()"
            else:
                self._func = "".join([self._ns.lower(), '_', self._name.lower(), '_', self._func_name, '()'])
        elif self._fragment == 'func':
            self._func_name = self._rest
            if self._namespace is not None:
                self._func = f"{self._namespace.symbol_prefix[0]}_{self._rest}()"
            else:
                self._func = "".join([self._ns.lower(), '_', self._rest.lower(), '()'])
        else:
            log.warning(f"Unknown fragment '{self._fragment}' in link [{self._fragment}@{self._endpoint}]")

    def __str__(self):
        if self._fragment in ['alias', 'class', 'const', 'enum', 'error', 'flags', 'iface', 'struct']:
            return f"[`{self._type}`]({self._fragment}.{self._name}.html)"
        elif self._fragment == 'property':
            return f"[`{self._type}:{self._prop_name}`](property.{self._name}.{self._prop_name}.html)"
        elif self._fragment == 'signal':
            return f"[`{self._type}::{self._signal_name}`](signal.{self._name}.{self._signal_name}.html)"
        elif self._fragment in ['ctor', 'method']:
            return f"[`{self._func}`]({self._fragment}.{self._name}.{self._func_name}.html)"
        elif self._fragment == 'func':
            return f"[`{self._func}`](func.{self._func_name}.html)"
        else:
            return f"`{self._ns}.{self._rest}`"


def preprocess_docs(text, namespace=None, md=None, extensions=[]):
    processed_text = []

    code_block_text = []
    code_block_language = None
    inside_code_block = False
    for line in text.split("\n"):
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
                link = LinkGenerator(namespace=namespace, fragment=fragment, endpoint=endpoint)
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

    return typogrify(text)


def code_highlight(text, language='c'):
    lexer = get_lexer_by_name(language)
    formatter = HtmlFormatter()
    return highlight(text, lexer, formatter)
