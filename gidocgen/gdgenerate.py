# SPDX-FileCopyrightText: 2021 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import argparse
import jinja2
import markdown
import os
import re
import shutil
import sys

from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from typogrify.filters import typogrify

from . import config, gir, log


HELP_MSG = "Generates the reference"

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

TRANSFER_MODES = {
    'none': 'Ownership is not transferred',
    'container': 'Ownership of the container type is transferred, but not of the data',
    'full': 'Ownership of the data is transferred',
    'floating': 'Data has a floating reference',
}

DIRECTION_MODES = {
    'in': 'in',
    'inout': 'in-out',
    'out': 'out',
}

SCOPE_MODES = {
    'none': '-',
    'call': 'Arguments are valid during the call',
    'notified': 'Arguments are valid until the notify function is called',
    'async': 'Arguments are valid until the call is completed',
}

MD_EXTENSIONS = [
    'def_list',
    'fenced_code',
    'tables',
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


def preprocess_gtkdoc(text):
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
            code_block_text += [line]
        else:
            processed_line = line
            processed_line = re.sub(r'#([A-Z][A-Za-z0-9:]+)', r'<code>\1</code>', processed_line)
            processed_line = re.sub(r'@(\w+)', r'<code>\1</code>', processed_line)
            processed_line = re.sub(r'%([A-Za-z0-9_]+)', r'<code>\1</code>', processed_line)
            processed_line = re.sub(r'#+\s+([\w\-_\s]+)(#+\s+[\w\{\}#-_]+)?', r'##### \1', processed_line)
            processed_text += [processed_line]

    text = markdown.markdown("\n".join(processed_text), extensions=MD_EXTENSIONS)
    return typogrify(text)


class TemplateConstant:
    def __init__(self, namespace, const):
        self.name = const.name
        self.value = const.value
        self.identifier = const.ctype
        self.type_cname = const.target.ctype
        self.description = "No description available."
        if const.doc is not None:
            self.description = preprocess_gtkdoc(const.doc.content)

        self.stability = const.stability or "stable"
        self.annotations = const.annotations
        self.available_since = const.available_since or namespace.version
        self.deprecated_since = const.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

    @property
    def c_decl(self):
        return f"#define {self.identifier} {self.value}"


class TemplateProperty:
    def __init__(self, namespace, cls, prop):
        self.name = prop.name
        self.type_name = prop.target.name
        self.type_cname = prop.target.ctype
        self.description = "No description available."
        self.readable = prop.readable
        self.writable = prop.writable
        self.construct = prop.construct
        self.construct_only = prop.construct_only
        if prop.doc is not None:
            self.description = preprocess_gtkdoc(prop.doc.content)

        self.stability = prop.stability or "stable"
        self.annotations = prop.annotations
        self.available_since = prop.available_since or namespace.version
        self.deprecated_since = prop.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)


class TemplateArgument:
    def __init__(self, call, argument):
        self.name = argument.name
        self.type_name = argument.target.name
        self.type_cname = argument.target.ctype
        self.transfer = TRANSFER_MODES[argument.transfer]
        self.direction = DIRECTION_MODES[argument.direction]
        self.nullable = argument.nullable
        self.scope = SCOPE_MODES[argument.scope or 'none']
        if argument.closure != -1:
            self.closure = call.parameters[argument.closure]
        else:
            self.closure = None
        self.description = "No description available."
        if argument.doc is not None:
            self.description = preprocess_gtkdoc(argument.doc.content)

    @property
    def is_pointer(self):
        return '*' in self.type_cname


class TemplateReturnValue:
    def __init__(self, call, retval):
        self.name = retval.name
        self.type_name = retval.target.name
        self.type_cname = retval.target.ctype
        self.transfer = TRANSFER_MODES[retval.transfer or 'none']
        self.nullable = retval.nullable
        self.description = "No description available."
        if retval.doc is not None:
            self.description = preprocess_gtkdoc(retval.doc.content)

    @property
    def is_pointer(self):
        return '*' in self.type_cname


class TemplateSignal:
    def __init__(self, namespace, cls, signal):
        self.name = signal.name
        self.class_type_cname = cls.type_cname
        self.description = "No description available."
        self.identifier = signal.name.replace("-", "_")

        if signal.doc is not None:
            self.description = preprocess_gtkdoc(signal.doc.content)

        self.arguments = []
        for arg in signal.parameters:
            self.arguments.append(TemplateArgument(signal, arg))

        self.return_value = None
        if not isinstance(signal.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(signal, signal.return_value)

        self.stability = signal.stability or "stable"
        self.annotations = signal.annotations
        self.available_since = signal.available_since or namespace.version
        self.deprecated_since = signal.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

    @property
    def c_decl(self):
        res = []
        if self.return_value is None:
            res += ["void"]
        else:
            res += [f"{self.return_value.type_cname}"]
        res += [f"{self.identifier} ("]
        res += [f"  {self.class_type_cname} self,"]
        for arg in self.arguments:
            res += [f"  {arg.type_cname} {arg.name},"]
        res += ["  gpointer user_data"]
        res += [")"]
        return "\n".join(res)


class TemplateMethod:
    def __init__(self, namespace, cls, method):
        self.name = method.name
        self.identifier = method.identifier
        self.description = "No description available."

        if method.doc is not None:
            self.description = preprocess_gtkdoc(method.doc.content)

        self.instance_parameter = TemplateArgument(method, method.instance_param)

        self.arguments = []
        for arg in method.parameters:
            self.arguments.append(TemplateArgument(method, arg))

        self.return_value = None
        if not isinstance(method.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(method, method.return_value)

        self.stability = method.stability or "stable"
        self.annotations = method.annotations
        self.available_since = method.available_since or namespace.version
        self.deprecated_since = method.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

    @property
    def c_decl(self):
        res = []
        if self.return_value is None:
            res += ["void"]
        else:
            res += [f"{self.return_value.type_cname}"]
        res += [f"{self.identifier} ("]
        n_args = len(self.arguments)
        if n_args == 0:
            res += [f"  {self.instance_parameter.type_cname} self"]
        else:
            res += [f"  {self.instance_parameter.type_cname} self,"]
            for (idx, arg) in enumerate(self.arguments):
                if idx < n_args - 1:
                    res += [f"  {arg.type_cname} {arg.name},"]
                else:
                    res += [f"  {arg.type_cname} {arg.name}"]
        res += [")"]
        return "\n".join(res)


class TemplateClassMethod:
    def __init__(self, namespace, cls, method):
        self.name = method.name
        self.identifier = method.identifier
        self.class_type_cname = cls.class_struct.type_struct
        self.description = "No description available."

        if method.doc is not None:
            self.description = preprocess_gtkdoc(method.doc.content)

        self.arguments = []
        for arg in method.parameters:
            self.arguments.append(TemplateArgument(method, arg))

        self.return_value = None
        if not isinstance(method.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(method, method.return_value)

    @property
    def c_decl(self):
        res = []
        if self.return_value is None:
            res += ["void"]
        else:
            res += [f"{self.return_value.type_cname}"]
        res += [f"{self.identifier} ("]
        n_args = len(self.arguments)
        if n_args == 1:
            res += [f"  {self.class_type_cname}* self"]
        else:
            res += [f"  {self.class_type_cname}* self,"]
            for (idx, arg) in enumerate(self.arguments, start=1):
                if idx < n_args - 1:
                    res += [f"  {arg.type_cname} {arg.name},"]
                else:
                    res += [f"  {arg.type_cname} {arg.name}"]
        res += [")"]
        return "\n".join(res)


class TemplateFunction:
    def __init__(self, namespace, func):
        self.name = func.name
        self.identifier = func.identifier
        self.description = "No description available."
        if func.doc is not None:
            self.description = preprocess_gtkdoc(func.doc.content)

        self.arguments = []
        for arg in func.parameters:
            self.arguments.append(TemplateArgument(func, arg))

        self.return_value = None
        if not isinstance(func.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(func, func.return_value)

        self.stability = func.stability or "stable"
        self.annotations = func.annotations
        self.available_since = func.available_since or namespace.version
        self.deprecated_since = func.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

    @property
    def c_decl(self):
        res = []
        if self.return_value is None:
            res += ["void"]
        else:
            res += [f"{self.return_value.type_cname}"]
        res += [f"{self.identifier} ("]
        n_args = len(self.arguments)
        if n_args == 0:
            res += ["  void"]
        else:
            for (idx, arg) in enumerate(self.arguments):
                if idx < n_args - 1:
                    res += [f"  {arg.type_cname} {arg.name},"]
                else:
                    res += [f"  {arg.type_cname} {arg.name}"]
        res += [")"]
        return "\n".join(res)


class TemplateCallback:
    def __init__(self, namespace, cb):
        self.name = cb.name
        self.description = "No description available."
        self.identifier = cb.name.replace("-", "_")
        if cb.doc is not None:
            self.description = preprocess_gtkdoc(cb.doc.content)

        self.arguments = []
        for arg in cb.parameters:
            self.arguments.append(TemplateArgument(cb, arg))

        self.return_value = None
        if not isinstance(cb.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(cb, cb.return_value)

        self.stability = cb.stability or "stable"
        self.annotations = cb.annotations
        self.available_since = cb.available_since or namespace.version
        self.deprecated_since = cb.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

    @property
    def c_decl(self):
        res = []
        if self.return_value is None:
            res += ["void"]
        else:
            res += [f"{self.return_value.type_cname}"]
        res += [f"{self.identifier} ("]
        n_args = len(self.arguments)
        if n_args == 0:
            res += ["void"]
        else:
            for (idx, arg) in enumerate(self.arguments):
                if idx < n_args - 1:
                    res += [f"  {arg.type_cname} {arg.name},"]
                else:
                    res += [f"  {arg.type_cname} {arg.name}"]
        res += [")"]
        return "\n".join(res)


class TemplateField:
    def __init__(self, field):
        self.name = field.name
        self.type_name = field.target and field.target.name or 'none'
        self.type_cname = field.target and field.target.ctype or 'none'
        self.private = field.private
        self.description = "No description available."
        if field.doc is not None:
            self.description = preprocess_gtkdoc(field.doc.content)


class TemplateInterface:
    def __init__(self, namespace, iface_name):
        interface = namespace.find_interface(iface_name)
        if interface is None:
            self.name = iface_name
            self.requires = "GObject.Object"
            self.link_prefix = "iface"
            self.description = "No description available."
            return

        self.name = interface.name
        self.requires = interface.prerequisite
        if self.requires is None:
            self.requires = "GObject.Object"

        self.symbol_prefix = f"{namespace.symbol_prefix}_{interface.symbol_prefix}"
        self.type_cname = interface.ctype

        self.link_prefix = "iface"

        self.description = "No description available."
        if interface.doc is not None:
            self.description = preprocess_gtkdoc(interface.doc.content)

        self.stability = interface.stability or "stable"
        self.annotations = interface.annotations
        self.available_since = interface.available_since or namespace.version
        self.deprecated_since = interface.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

        self.class_name = interface.type_struct

        self.class_struct = namespace.find_record(interface.type_struct)
        if self.class_struct is not None:
            self.class_fields = []
            self.class_methods = []

            for field in self.class_struct.fields:
                if not field.private:
                    self.class_fields.append(TemplateField(field))

            for meth in self.class_struct.methods:
                self.class_methods.append(TemplateClassMethod(namespace, self, meth))

        if len(interface.properties) != 0:
            self.properties = []
            for prop in interface.properties:
                self.properties.append(TemplateProperty(namespace, self, prop))

        if len(interface.signals) != 0:
            self.signals = []
            for sig in interface.signals:
                self.signals.append(TemplateSignal(namespace, self, sig))

        if len(interface.methods) != 0:
            self.methods = []
            for meth in interface.methods:
                self.methods.append(TemplateMethod(namespace, self, meth))

        if len(interface.virtual_methods) != 0:
            self.virtual_methods = []
            for vfunc in self.virtual_methods:
                self.virtual_methods.append(TemplateMethod(namespace, self, vfunc))

    @property
    def c_decl(self):
        return f"interface {self.type_cname} : {self.requires}"


class TemplateClass:
    def __init__(self, namespace, cls):
        self.name = cls.name
        self.symbol_prefix = f"{namespace.symbol_prefix}_{cls.symbol_prefix}"
        self.type_cname = cls.ctype
        self.link_prefix = "class"

        self.description = "No description available."
        if cls.parent is None:
            self.parent = 'GObject.TypeInstance'
        elif '.' in cls.parent:
            self.parent = cls.parent
        else:
            self.parent = f"{namespace.name}.{cls.parent}"

        if cls.doc is not None:
            self.description = preprocess_gtkdoc(cls.doc.content)

        self.stability = cls.stability or "stable"
        self.annotations = cls.annotations
        self.available_since = cls.available_since or namespace.version
        self.deprecated_since = cls.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

        self.fields = []
        for field in cls.fields:
            if not field.private:
                self.fields.append(TemplateField(field))

        if len(cls.properties) != 0:
            self.properties = []
            for prop in cls.properties:
                self.properties.append(TemplateProperty(namespace, self, prop))

        if len(cls.signals) != 0:
            self.signals = []
            for sig in cls.signals:
                self.signals.append(TemplateSignal(namespace, self, sig))

        if len(cls.constructors) != 0:
            self.ctors = []
            for ctor in cls.constructors:
                self.ctors.append(TemplateFunction(namespace, ctor))

        if len(cls.methods) != 0:
            self.methods = []
            for meth in cls.methods:
                self.methods.append(TemplateMethod(namespace, self, meth))

        self.class_name = cls.type_struct

        self.instance_struct = None
        if len(cls.fields) != 0:
            self.instance_struct = self.class_name

        self.class_struct = namespace.find_record(cls.type_struct)
        if self.class_struct is None:
            return

        if self.class_struct:
            self.class_fields = []
            self.class_methods = []

            for field in self.class_struct.fields:
                if not field.private:
                    self.class_fields.append(TemplateField(field))

            for meth in self.class_struct.methods:
                self.class_methods.append(TemplateClassMethod(namespace, self, meth))

        if len(cls.implements) != 0:
            self.interfaces = []
            for iface in cls.implements:
                self.interfaces.append(TemplateInterface(namespace, iface))

        if len(cls.virtual_methods) != 0:
            self.virtual_methods = []
            for vfunc in cls.virtual_methods:
                self.virtual_methods.append(TemplateMethod(namespace, self, vfunc))

        if len(cls.functions) != 0:
            self.type_funcs = []
            for func in cls.functions:
                self.type_funcs.append(TemplateFunction(namespace, func))

    @property
    def c_decl(self):
        if not self.class_struct or not self.instance_struct:
            res = [f"final class {self.type_cname} : {self.parent} {{"]
        else:
            res = [f"class {self.type_cname} : {self.parent} {{"]
        n_fields = len(self.fields)
        if n_fields > 0:
            for (idx, field) in enumerate(self.fields):
                if idx < n_fields - 1:
                    res += [f"  {field.name}: {field.type_cname},"]
                else:
                    res += [f"  {field.name}: {field.type_cname}"]
        else:
            res += ["  /* No available fields */"]
        res += ["}"]
        return "\n".join(res)


class TemplateRecord:
    def __init__(self, namespace, record):
        self.name = record.name
        self.symbol_prefix = f"{namespace.symbol_prefix}_{record.symbol_prefix}"
        self.type_cname = record.ctype
        self.link_prefix = "struct"

        self.description = "No description available."
        if record.doc is not None:
            self.description = preprocess_gtkdoc(record.doc.content)

        self.stability = record.stability or "stable"
        self.annotations = record.annotations
        self.available_since = record.available_since or namespace.version
        self.deprecated_since = record.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

        self.fields = []
        for field in record.fields:
            if not field.private:
                self.fields.append(TemplateField(field))

        if len(record.constructors) != 0:
            self.ctors = []
            for ctor in record.constructors:
                self.ctors.append(TemplateFunction(namespace, ctor))

        if len(record.methods) != 0:
            self.methods = []
            for meth in record.methods:
                self.methods.append(TemplateMethod(namespace, self, meth))

        if len(record.functions) != 0:
            self.type_funcs = []
            for func in record.functions:
                self.type_funcs.append(TemplateFunction(namespace, func))

    @property
    def c_decl(self):
        res = [f"struct {self.type_cname} {{"]
        n_fields = len(self.fields)
        if n_fields > 0:
            for (idx, field) in enumerate(self.fields):
                if idx < n_fields - 1:
                    res += [f"  {field.name}: {field.type_cname},"]
                else:
                    res += [f"  {field.name}: {field.type_cname}"]
        else:
            res += ["  /* No available fields */"]
        res += ["}"]
        return "\n".join(res)


class TemplateUnion:
    def __init__(self, namespace, union):
        self.name = union.name
        self.symbol_prefix = f"{namespace.symbol_prefix}_{union.symbol_prefix}"
        self.type_cname = union.ctype
        self.link_prefix = "union"

        self.description = "No description available."
        if union.doc is not None:
            self.description = preprocess_gtkdoc(union.doc.content)

        self.stability = union.stability or "stable"
        self.annotations = union.annotations
        self.available_since = union.available_since or namespace.version
        self.deprecated_since = union.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

        self.fields = []
        for field in union.fields:
            if not field.private:
                self.fields.append(TemplateField(field))

        if len(union.constructors) != 0:
            self.ctors = []
            for ctor in union.constructors:
                self.ctors.append(TemplateFunction(namespace, ctor))

        if len(union.methods) != 0:
            self.methods = []
            for meth in union.methods:
                self.methods.append(TemplateMethod(namespace, self, meth))

        if len(union.functions) != 0:
            self.type_funcs = []
            for func in union.functions:
                self.type_funcs.append(TemplateFunction(namespace, func))

    @property
    def c_decl(self):
        res = [f"union {self.type_cname} {{"]
        n_fields = len(self.fields)
        if n_fields > 0:
            for (idx, field) in enumerate(self.fields):
                if idx < n_fields - 1:
                    res += [f"  {field.name}: {field.type_cname},"]
                else:
                    res += [f"  {field.name}: {field.type_cname}"]
        else:
            res += ["  /* No available fields */"]
        res += ["}"]
        return "\n".join(res)


class TemplateAlias:
    def __init__(self, namespace, alias):
        self.name = alias.name
        self.type_cname = alias.ctype
        self.target_ctype = alias.target.ctype
        self.link_prefix = "alias"

        self.description = "No description available."
        if alias.doc is not None:
            self.description = preprocess_gtkdoc(alias.doc.content)

        self.stability = alias.stability or "stable"
        self.annotations = alias.annotations
        self.available_since = alias.available_since or namespace.version
        self.deprecated_since = alias.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

    @property
    def c_decl(self):
        return f"typedef {self.target_ctype} {self.type_cname}"


class TemplateMember:
    def __init__(self, enum, member):
        self.name = member.identifier
        self.nick = member.nick
        self.value = member.value
        self.description = "No description available."
        if member.doc is not None:
            self.description = preprocess_gtkdoc(member.doc.content)


class TemplateEnum:
    def __init__(self, namespace, enum):
        self.name = enum.name
        self.symbol_prefix = None
        self.type_cname = enum.ctype
        self.bitfield = False
        self.error = False
        self.domain = None

        self.description = "No description available."
        if enum.doc is not None:
            self.description = preprocess_gtkdoc(enum.doc.content)

        self.stability = enum.stability or "stable"
        self.annotations = enum.annotations
        self.available_since = enum.available_since or namespace.version
        self.deprecated_since = enum.deprecated_since
        if self.deprecated_since is not None:
            msg = self.deprecated_since[1]
            self.deprecated_since[1] = preprocess_gtkdoc(msg)

        if isinstance(enum, gir.BitField):
            self.link_prefix = "flags"
            self.bitfield = True
        elif isinstance(enum, gir.ErrorDomain):
            self.link_prefix = "error"
            self.error = True
            self.domain = enum.domain
        else:
            self.link_prefix = "enum"

        if len(enum.members) != 0:
            self.members = []
            for member in enum.members:
                self.members.append(TemplateMember(enum, member))

        if len(enum.functions) != 0:
            self.type_funcs = []
            for func in enum.functions:
                self.type_funcs.append(TemplateFunction(namespace, func))


class TemplateNamespace:
    def __init__(self, namespace):
        self.name = namespace.name
        self.version = namespace.version
        self.prefix = f"{namespace.symbol_prefix}"


def _gen_classes(config, theme_config, output_dir, jinja_env, namespace, all_classes):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    class_tmpl = jinja_env.get_template(theme_config.class_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    property_tmpl = jinja_env.get_template(theme_config.property_template)
    signal_tmpl = jinja_env.get_template(theme_config.signal_template)
    class_method_tmpl = jinja_env.get_template(theme_config.class_method_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)
    vfunc_tmpl = jinja_env.get_template(theme_config.vfunc_template)

    for cls in all_classes:
        class_file = os.path.join(ns_dir, f"class.{cls.name}.html")
        log.info(f"Creating class file for {namespace.name}.{cls.name}: {class_file}")

        tmpl = TemplateClass(namespace, cls)

        with open(class_file, "w") as out:
            content = class_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'class': tmpl,
            })

            out.write(content)

        for ctor in getattr(tmpl, 'ctors', []):
            ctor_file = os.path.join(ns_dir, f"ctor.{cls.name}.{ctor.name}.html")
            log.debug(f"Creating ctor file for {namespace.name}.{cls.name}.{ctor.name}: {ctor_file}")

            with open(ctor_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': ctor,
                }))

        for method in getattr(tmpl, 'methods', []):
            method_file = os.path.join(ns_dir, f"method.{cls.name}.{method.name}.html")
            log.debug(f"Creating method file for {namespace.name}.{cls.name}.{method.name}: {method_file}")

            with open(method_file, "w") as out:
                out.write(method_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'method': method,
                }))

        for prop in getattr(tmpl, 'properties', []):
            prop_file = os.path.join(ns_dir, f"property.{cls.name}.{prop.name}.html")
            log.debug(f"Creating property file for {namespace.name}.{cls.name}.{prop.name}: {prop_file}")

            with open(prop_file, "w") as out:
                out.write(property_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'property': prop,
                }))

        for signal in getattr(tmpl, 'signals', []):
            signal_file = os.path.join(ns_dir, f"signal.{cls.name}.{signal.name}.html")
            log.debug(f"Creating signal file for {namespace.name}.{cls.name}.{signal.name}: {signal_file}")

            with open(signal_file, "w") as out:
                out.write(signal_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'signal': signal,
                }))

        for cls_method in getattr(tmpl, 'class_methods', []):
            cls_method_file = os.path.join(ns_dir, f"class_method.{cls.name}.{cls_method.name}.html")
            log.debug(f"Creating class method file for {namespace.name}.{cls.name}.{cls_method.name}: {cls_method_file}")

            with open(cls_method_file, "w") as out:
                out.write(class_method_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'class_method': cls_method,
                }))

        for vfunc in getattr(tmpl, 'virtual_methods', []):
            vfunc_file = os.path.join(ns_dir, f"vfunc.{cls.name}.{vfunc.name}.html")
            log.debug(f"Creating vfunc file for {namespace.name}.{cls.name}.{vfunc.name}: {vfunc_file}")

            with open(vfunc_file, "w") as out:
                out.write(vfunc_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'vfunc': vfunc,
                }))

        for type_func in getattr(tmpl, 'type_funcs', []):
            type_func_file = os.path.join(ns_dir, f"type_func.{cls.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{cls.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': type_func,
                }))


def _gen_interfaces(config, theme_config, output_dir, jinja_env, namespace, all_interfaces):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    iface_tmpl = jinja_env.get_template(theme_config.interface_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    property_tmpl = jinja_env.get_template(theme_config.property_template)
    signal_tmpl = jinja_env.get_template(theme_config.signal_template)
    class_method_tmpl = jinja_env.get_template(theme_config.class_method_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)
    vfunc_tmpl = jinja_env.get_template(theme_config.vfunc_template)

    for iface in all_interfaces:
        iface_file = os.path.join(ns_dir, f"iface.{iface.name}.html")
        log.info(f"Creating interface file for {namespace.name}.{iface.name}: {iface_file}")

        tmpl = TemplateInterface(namespace, iface)

        with open(iface_file, "w") as out:
            out.write(iface_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'interface': tmpl,
            }))

        for method in getattr(tmpl, 'methods', []):
            method_file = os.path.join(ns_dir, f"method.{iface.name}.{method.name}.html")
            log.debug(f"Creating method file for {namespace.name}.{iface.name}.{method.name}: {method_file}")

            with open(method_file, "w") as out:
                out.write(method_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'method': method,
                }))

        for prop in getattr(tmpl, 'properties', []):
            prop_file = os.path.join(ns_dir, f"property.{iface.name}.{prop.name}.html")
            log.debug(f"Creating property file for {namespace.name}.{iface.name}.{prop.name}: {prop_file}")

            with open(prop_file, "w") as out:
                out.write(property_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'property': prop,
                }))

        for signal in getattr(tmpl, 'signals', []):
            signal_file = os.path.join(ns_dir, f"signal.{iface.name}.{signal.name}.html")
            log.debug(f"Creating signal file for {namespace.name}.{iface.name}.{signal.name}: {signal_file}")

            with open(signal_file, "w") as out:
                out.write(signal_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'signal': signal,
                }))

        for cls_method in getattr(tmpl, 'class_methods', []):
            class_method_file = os.path.join(ns_dir, f"class_method.{iface.name}.{cls_method.name}.html")
            log.debug(f"Creating class method file for {namespace.name}.{iface.name}.{cls_method.name}: {class_method_file}")

            with open(class_method_file, "w") as out:
                out.write(class_method_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'class_method': cls_method,
                }))

        for vfunc in getattr(tmpl, 'virtual_methods', []):
            vfunc_file = os.path.join(ns_dir, f"vfunc.{iface.name}.{vfunc.name}.html")
            log.debug(f"Creating vfunc file for {namespace.name}.{iface.name}.{vfunc.name}: {vfunc_file}")

            with open(vfunc_file, "w") as out:
                out.write(vfunc_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'vfunc': vfunc,
                }))

        for type_func in getattr(tmpl, 'type_funcs', []):
            type_func_file = os.path.join(ns_dir, f"type_func.{iface.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{iface.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': type_func,
                }))


def _gen_enums(config, theme_config, output_dir, jinja_env, namespace, all_enums):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    enum_tmpl = jinja_env.get_template(theme_config.enum_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    for enum in all_enums:
        enum_file = os.path.join(ns_dir, f"enum.{enum.name}.html")
        log.info(f"Creating enum file for {namespace.name}.{enum.name}: {enum_file}")

        tmpl = TemplateEnum(namespace, enum)

        with open(enum_file, "w") as out:
            out.write(enum_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'enum': tmpl,
            }))

        for type_func in getattr(tmpl, 'type_funcs', []):
            type_func_file = os.path.join(ns_dir, f"type_func.{enum.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{enum.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': type_func,
                }))


def _gen_bitfields(config, theme_config, output_dir, jinja_env, namespace, all_enums):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    enum_tmpl = jinja_env.get_template(theme_config.flags_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    for enum in all_enums:
        enum_file = os.path.join(ns_dir, f"flags.{enum.name}.html")
        log.info(f"Creating enum file for {namespace.name}.{enum.name}: {enum_file}")

        tmpl = TemplateEnum(namespace, enum)

        with open(enum_file, "w") as out:
            out.write(enum_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'enum': tmpl,
            }))

        for type_func in getattr(tmpl, 'type_funcs', []):
            type_func_file = os.path.join(ns_dir, f"type_func.{enum.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{enum.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': type_func,
                }))


def _gen_domains(config, theme_config, output_dir, jinja_env, namespace, all_enums):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    enum_tmpl = jinja_env.get_template(theme_config.error_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    for enum in all_enums:
        enum_file = os.path.join(ns_dir, f"error.{enum.name}.html")
        log.info(f"Creating enum file for {namespace.name}.{enum.name}: {enum_file}")

        tmpl = TemplateEnum(namespace, enum)

        with open(enum_file, "w") as out:
            out.write(enum_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'enum': tmpl,
            }))

        for type_func in getattr(tmpl, 'type_funcs', []):
            type_func_file = os.path.join(ns_dir, f"type_func.{enum.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{enum.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': type_func,
                }))


def _gen_constants(config, theme_config, output_dir, jinja_env, namespace, all_constants):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    const_tmpl = jinja_env.get_template(theme_config.constant_template)

    for const in all_constants:
        const_file = os.path.join(ns_dir, f"const.{const.name}.html")
        log.info(f"Creating constant file for {namespace.name}.{const.name}: {const_file}")

        tmpl = TemplateConstant(namespace, const)

        with open(const_file, "w") as out:
            out.write(const_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'constant': tmpl,
            }))


def _gen_aliases(config, theme_config, output_dir, jinja_env, namespace, all_aliases):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    alias_tmpl = jinja_env.get_template(theme_config.alias_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    for alias in all_aliases:
        alias_file = os.path.join(ns_dir, f"alias.{alias.name}.html")
        log.info(f"Creating alias file for {namespace.name}.{alias.name}: {alias_file}")

        tmpl = TemplateAlias(namespace, alias)

        with open(alias_file, "w") as out:
            content = alias_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'struct': tmpl,
            })

            out.write(content)

        for ctor in getattr(tmpl, 'ctors', []):
            ctor_file = os.path.join(ns_dir, f"ctor.{alias.name}.{ctor.name}.html")
            log.debug(f"Creating ctor file for {namespace.name}.{alias.name}.{ctor.name}: {ctor_file}")

            with open(ctor_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': ctor,
                }))

        for method in getattr(tmpl, 'methods', []):
            method_file = os.path.join(ns_dir, f"method.{alias.name}.{method.name}.html")
            log.debug(f"Creating method file for {namespace.name}.{alias.name}.{method.name}: {method_file}")

            with open(method_file, "w") as out:
                out.write(method_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'method': method,
                }))

        for type_func in getattr(tmpl, 'type_funcs', []):
            type_func_file = os.path.join(ns_dir, f"type_func.{alias.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{alias.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': type_func,
                }))


def _gen_records(config, theme_config, output_dir, jinja_env, namespace, all_records):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    record_tmpl = jinja_env.get_template(theme_config.record_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    for record in all_records:
        record_file = os.path.join(ns_dir, f"struct.{record.name}.html")
        log.info(f"Creating record file for {namespace.name}.{record.name}: {record_file}")

        tmpl = TemplateRecord(namespace, record)

        with open(record_file, "w") as out:
            content = record_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'struct': tmpl,
            })

            out.write(content)

        for ctor in getattr(tmpl, 'ctors', []):
            ctor_file = os.path.join(ns_dir, f"ctor.{record.name}.{ctor.name}.html")
            log.debug(f"Creating ctor file for {namespace.name}.{record.name}.{ctor.name}: {ctor_file}")

            with open(ctor_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': ctor,
                }))

        for method in getattr(tmpl, 'methods', []):
            method_file = os.path.join(ns_dir, f"method.{record.name}.{method.name}.html")
            log.debug(f"Creating method file for {namespace.name}.{record.name}.{method.name}: {method_file}")

            with open(method_file, "w") as out:
                out.write(method_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'method': method,
                }))

        for type_func in getattr(tmpl, 'type_funcs', []):
            type_func_file = os.path.join(ns_dir, f"type_func.{record.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{record.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': type_func,
                }))


def _gen_unions(config, theme_config, output_dir, jinja_env, namespace, all_unions):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    union_tmpl = jinja_env.get_template(theme_config.union_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    for union in all_unions:
        union_file = os.path.join(ns_dir, f"union.{union.name}.html")
        log.info(f"Creating union file for {namespace.name}.{union.name}: {union_file}")

        tmpl = TemplateUnion(namespace, union)

        with open(union_file, "w") as out:
            content = union_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'struct': tmpl,
            })

            out.write(content)

        for ctor in getattr(tmpl, 'ctors', []):
            ctor_file = os.path.join(ns_dir, f"ctor.{union.name}.{ctor.name}.html")
            log.debug(f"Creating ctor file for {namespace.name}.{union.name}.{ctor.name}: {ctor_file}")

            with open(ctor_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': ctor,
                }))

        for method in getattr(tmpl, 'methods', []):
            method_file = os.path.join(ns_dir, f"method.{union.name}.{method.name}.html")
            log.debug(f"Creating method file for {namespace.name}.{union.name}.{method.name}: {method_file}")

            with open(method_file, "w") as out:
                out.write(method_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'method': method,
                }))

        for type_func in getattr(tmpl, 'type_funcs', []):
            type_func_file = os.path.join(ns_dir, f"type_func.{union.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{union.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': type_func,
                }))


def _gen_functions(config, theme_config, output_dir, jinja_env, namespace, all_functions):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    func_tmpl = jinja_env.get_template(theme_config.func_template)

    for func in all_functions:
        func_file = os.path.join(ns_dir, f"func.{func.name}.html")
        log.info(f"Creating function file for {namespace.name}.{func.name}: {func_file}")

        tmpl = TemplateFunction(namespace, func)

        with open(func_file, "w") as out:
            content = func_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'func': tmpl,
            })

            out.write(content)


def _gen_callbacks(config, theme_config, output_dir, jinja_env, namespace, all_callbacks):
    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")

    func_tmpl = jinja_env.get_template(theme_config.func_template)

    for func in all_callbacks:
        func_file = os.path.join(ns_dir, f"callback.{func.name}.html")
        log.info(f"Creating callback file for {namespace.name}.{func.name}: {func_file}")

        tmpl = TemplateCallback(namespace, func)

        with open(func_file, "w") as out:
            content = func_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'func': tmpl,
            })

            out.write(content)


def _gen_content_files(config, content_dir, output_dir):
    content_files = []

    for (file_name, content_title) in config.content_files:
        content_file = file_name.replace('.md', '.html')
        infile = os.path.join(content_dir, file_name)
        outfile = os.path.join(output_dir, content_file)
        log.debug(f"Adding extra content file: {infile} -> {outfile} ('{content_title}')")
        content_files += [(infile, outfile, content_file, content_title)]

    return content_files


def _gen_content_images(config, content_dir, output_dir):
    content_images = []

    for image_file in config.content_images:
        infile = os.path.join(content_dir, image_file)
        outfile = os.path.join(output_dir, os.path.basename(image_file))
        log.debug(f"Adding extra content image: {infile} -> {outfile}")
        content_images += [(infile, outfile)]

    return content_images


def gen_reference(config, options, repository, templates_dir, theme_config, content_dir, output_dir):
    theme_dir = os.path.join(templates_dir, theme_config.name.lower())
    log.debug(f"Loading jinja templates from {theme_dir}")

    fs_loader = jinja2.FileSystemLoader(theme_dir)
    jinja_env = jinja2.Environment(loader=fs_loader, autoescape=jinja2.select_autoescape(['html']))

    namespace = repository.namespace

    symbols = {
        "aliases": sorted(namespace.get_aliases(), key=lambda alias: alias.name.lower()),
        "bitfields": sorted(namespace.get_bitfields(), key=lambda bitfield: bitfield.name.lower()),
        "callbacks": sorted(namespace.get_callbacks(), key=lambda callback: callback.name.lower()),
        "classes": sorted(namespace.get_classes(), key=lambda cls: cls.name.lower()),
        "constants": sorted(namespace.get_constants(), key=lambda const: const.name.lower()),
        "domains": sorted(namespace.get_error_domains(), key=lambda domain: domain.name.lower()),
        "enums": sorted(namespace.get_enumerations(), key=lambda enum: enum.name.lower()),
        "functions": sorted(namespace.get_functions(), key=lambda func: func.name.lower()),
        "interfaces": sorted(namespace.get_interfaces(), key=lambda interface: interface.name.lower()),
        "records": sorted(namespace.get_effective_records(), key=lambda record: record.name.lower()),
        "unions": sorted(namespace.get_unions(), key=lambda union: union.name.lower()),
    }

    all_indices = {
        "aliases": _gen_aliases,
        "bitfields": _gen_bitfields,
        "callbacks": _gen_callbacks,
        "classes": _gen_classes,
        "constants": _gen_constants,
        "domains": _gen_domains,
        "enums": _gen_enums,
        "functions": _gen_functions,
        "interfaces": _gen_interfaces,
        "records": _gen_records,
        "unions": _gen_unions,
    }

    ns_dir = os.path.join(output_dir, f"{namespace.name}", f"{namespace.version}")
    log.debug(f"Creating output path for the namespace: {ns_dir}")
    os.makedirs(ns_dir, exist_ok=True)

    content_files = _gen_content_files(config, content_dir, ns_dir)
    content_images = _gen_content_images(config, content_dir, ns_dir)

    ns_tmpl = jinja_env.get_template(theme_config.namespace_template)
    ns_file = os.path.join(ns_dir, "index.html")
    log.info(f"Creating namespace index file for {namespace.name}.{namespace.version}: {ns_file}")
    with open(ns_file, "w") as out:
        out.write(ns_tmpl.render({
            "CONFIG": config,
            "repository": repository,
            "namespace": namespace,
            "symbols": symbols,
            "content_files": content_files,
        }))

    if options.sections == [] or options.sections == ["all"]:
        gen_indices = list(all_indices.keys())
    else:
        gen_indices = options.sections

    log.info(f"Generating references for: {gen_indices}")

    for section in gen_indices:
        generator = all_indices.get(section, None)
        if generator is None:
            log.debug(f"No generator for section {section}")
            continue

        s = symbols.get(section, [])
        if s is None:
            log.debug(f"No symbols for section {section}")
            continue

        generator(config, theme_config, output_dir, jinja_env, namespace, s)

    if len(content_files) != 0:
        content_tmpl = jinja_env.get_template(theme_config.content_template)
        for (src, dst, filename, title) in content_files:
            log.info(f"Generating content file {filename} for '{title}': {dst}")

            src_data = ""
            with open(src, "r") as infile:
                source = []
                for line in infile:
                    source += [line]
                src_data = "".join(source)

            dst_data = preprocess_gtkdoc(src_data)
            with open(dst, "w") as outfile:
                outfile.write(content_tmpl.render({
                    "CONFIG": config,
                    "namespace": namespace,
                    "symbols": symbols,
                    "content_files": content_files,
                    "content_title": title,
                    "content_data": dst_data,
                }))

    if len(content_images) != 0:
        for (src, dst) in content_images:
            log.info(f"Copying content image {src}: {dst}")
            dst_dir = os.path.dirname(dst)
            os.makedirs(dst_dir, exist_ok=True)
            shutil.copyfile(src, dst)

    if theme_config.css is not None:
        log.info(f"Copying style from {theme_dir} to {ns_dir}")
        style_src = os.path.join(theme_dir, theme_config.css)
        style_dst = os.path.join(ns_dir, theme_config.css)
        shutil.copyfile(style_src, style_dst)

    for extra_file in theme_config.extra_files:
        log.info(f"Copying extra file {extra_file} from {theme_dir} to {ns_dir}")
        src = os.path.join(theme_dir, extra_file)
        dst = os.path.join(ns_dir, extra_file)
        shutil.copyfile(src, dst)


def add_args(parser):
    parser.add_argument("--add-include-path", action="append", dest="include_paths", default=[],
                        help="include paths for other GIR files")
    parser.add_argument("-C", "--config", metavar="FILE", help="the configuration file")
    parser.add_argument("--dry-run", action="store_true", help="parses the GIR file without generating files")
    parser.add_argument("--templates-dir", default=None, help="the base directory with the theme templates")
    parser.add_argument("--content-dir", default=None, help="the base directory with the extra content")
    parser.add_argument("--theme-name", default="basic", help="the theme to use")
    parser.add_argument("--output-dir", default=None, help="the output directory for the index files")
    parser.add_argument("--section", action="append", dest="sections", default=[], help="the sections to generate, or 'all'")
    parser.add_argument("infile", metavar="GIRFILE", type=argparse.FileType('r', encoding='UTF-8'),
                        default=sys.stdin, help="the GIR file to parse")


def run(options):
    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/share:/usr/local/share").split(":")
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

    paths = []
    paths.append(os.getcwd())
    paths.append(os.path.join(xdg_data_home, "gir-1.0"))
    paths.extend([os.path.join(x, "gir-1.0") for x in xdg_data_dirs])

    log.info(f"Loading config file: {options.config}")

    conf = config.GIDocConfig(options.config)

    output_dir = options.output_dir or os.getcwd()
    content_dir = options.content_dir or os.getcwd()

    if options.templates_dir is not None:
        templates_dir = options.templates_dir
    else:
        templates_dir = conf.get_templates_dir()
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

    theme_name = conf.get_theme_name(default=options.theme_name)
    theme_conf = config.GITemplateConfig(templates_dir, theme_name)

    log.debug(f"Search paths: {paths}")
    log.debug(f"Templates directory: {templates_dir}")
    log.info(f"Theme name: {theme_conf.name}")
    log.info(f"Output directory: {output_dir}")

    log.info("Parsing GIR file")
    parser = gir.GirParser(search_paths=paths)
    parser.parse(options.infile)

    if not options.dry_run:
        gen_reference(conf, options, parser.get_repository(), templates_dir, theme_conf, content_dir, output_dir)

    return 0
