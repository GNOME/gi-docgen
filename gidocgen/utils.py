# SPDX-FileCopyrightText: 2021 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import markdown
import re

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from typogrify.filters import typogrify

from . import mdext


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

CODEBLOCK_END_RE = re.compile(
    r'''
    ^
    \s*
    \]\|
    \s*
    $
    ''',
    re.UNICODE | re.VERBOSE)

LANGUAGE_MAP = {
    'c': 'c',
    'css': 'css',
    'plain': 'plain',
    'xml': 'xml',
}

MD_EXTENSIONS = [
    # Standard extensions
    'def_list',
    'fenced_code',
    'meta',
    'tables',
    'toc',

    # Local extensions
    mdext.GtkDocExtension(),
    mdext.LinkExtension(),
]


def process_language(lang):
    if lang is None:
        return "plain"

    res = LANGUAGE_RE.match(lang)
    if res:
        language = res.group("language") or "plain"
    else:
        language = "plain"

    return LANGUAGE_MAP[language.lower()]


def preprocess_docs(text, md=None, extensions=[]):
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
            processed_text.append(line)

    if md is None:
        md_ext = extensions.copy()
        md_ext.extend(MD_EXTENSIONS)
        text = markdown.markdown("\n".join(processed_text), extensions=md_ext)
    else:
        text = md.convert("\n".join(processed_text))

    return typogrify(text)
