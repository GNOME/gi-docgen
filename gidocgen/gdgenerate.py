# SPDX-FileCopyrightText: 2021 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import argparse
import concurrent.futures
import jinja2
import markdown
import os
import shutil
import sys

import xml.etree.ElementTree as etree

from markupsafe import Markup

from . import config, gir, log, utils
from . import gdgenindices


class CallableType:
    CALLBACK = 0
    FUNCTION = 1
    METHOD = 2
    CLASS_METHOD = 3
    SIGNAL = 4


HELP_MSG = "Generates the reference"

MISSING_DESCRIPTION = "No description available."

STRING_TYPES = {
    'utf8': 'The value is a NUL terminated UTF-8 string.',
    'filename': 'The value is a platform-native string, using the preferred OS encoding on Unix and UTF-8 on Windows.',
}

STRING_ELEMENT_TYPES = {
    'utf8': 'Each element is a NUL terminated UTF-8 string.',
    'filename': 'Each element is a platform-native string, using the preferred OS encoding on Unix and UTF-8 on Windows.',
}

IN_ARG_TRANSFER_MODES = {
    CallableType.CALLBACK: {
        'none': 'The data is owned by the caller of the function.',
        'container': 'The called function takes ownership of the data container, but not the data inside it.',
        'full': 'The called function takes ownership of the data, and is responsible for freeing it.',
    },
    CallableType.FUNCTION: {
        'none': 'The data is owned by the caller of the function.',
        'container': 'The called function takes ownership of the data container, but not the data inside it.',
        'full': 'The called function takes ownership of the data, and is responsible for freeing it.',
    },
    CallableType.METHOD: {
        'none': 'The data is owned by the caller of the method.',
        'container': 'The instance takes ownership of the data container, but not the data inside it.',
        'full': 'The instance takes ownership of the data, and is responsible for freeing it.',
    },
    CallableType.CLASS_METHOD: {
        'none': 'The data is owned by the caller of the method.',
        'container': 'The class takes ownership of the data container, but not the data inside it.',
        'full': 'The class takes ownership of the data, and is responsible for freeing it.',
    },
    CallableType.SIGNAL: {
        'none': 'The data is owned by the caller of the function.',
        'container': 'The called function takes ownership of the data container, but not the data inside it.',
        'full': 'The called function takes ownership of the data, and is responsible for freeing it.',
    },
}

OUT_ARG_TRANSFER_MODES = {
    CallableType.CALLBACK: {
        'none': 'The returned data is owned by the function.',
        'container': 'The caller of the function takes ownership of the returned data container, but not the data inside it.',
        'full': 'The caller of the function takes ownership of the returned data, and is responsible for freeing it.',
    },
    CallableType.FUNCTION: {
        'none': 'The returned data is owned by the function.',
        'container': 'The caller of the function takes ownership of the returned data container, but not the data inside it.',
        'full': 'The caller of the function takes ownership of the returned data, and is responsible for freeing it.',
    },
    CallableType.METHOD: {
        'none': 'The returned data is owned by the instance.',
        'container': 'The caller of the method takes ownership of the returned data container, but not the data inside it.',
        'full': 'The caller of the method takes ownership of the returned data, and is responsible for freeing it.',
    },
    CallableType.CLASS_METHOD: {
        'none': 'The returned data is owned by the class.',
        'container': 'The caller of the method takes ownership of the returned data container, but not the data inside it.',
        'full': 'The caller of the method takes ownership of the returned data, and is responsible for freeing it.',
    },
    CallableType.SIGNAL: {
        'none': 'The returned data is owned by the function.',
        'container': 'The caller of the function takes ownership of the returned data container, but not the data inside it.',
        'full': 'The caller of the function takes ownership of the returned data, and is responsible for freeing it.',
    },
}

RETURN_TRANSFER_MODES = {
    CallableType.CALLBACK: {
        'none': 'The data is owned by the called function.',
        'container': 'The caller of the function takes ownership of the data container, but not the data inside it.',
        'full': 'The caller of the function takes ownership of the data, and is responsible for freeing it.',
        'floating': 'The returned data has a floating reference.',
    },
    CallableType.FUNCTION: {
        'none': 'The data is owned by the called function.',
        'container': 'The caller of the function takes ownership of the data container, but not the data inside it.',
        'full': 'The caller of the function takes ownership of the data, and is responsible for freeing it.',
        'floating': 'The returned data has a floating reference.',
    },
    CallableType.METHOD: {
        'none': 'The returned data is owned by the instance.',
        'container': 'The caller of the method takes ownership of the returned data container, but not the data inside it.',
        'full': 'The caller of the method takes ownership of the returned data, and is responsible for freeing it.',
        'floating': 'The returned data has a floating reference.',
    },
    CallableType.CLASS_METHOD: {
        'none': 'The returned data is owned by the class.',
        'container': 'The caller of the method takes ownership of the returned data container, but not the data inside it.',
        'full': 'The caller of the method takes ownership of the returned data, and is responsible for freeing it.',
        'floating': 'The returned data has a floating reference.',
    },
    CallableType.SIGNAL: {
        'none': 'The data is owned by the called function.',
        'container': 'The caller of the function takes ownership of the data container, but not the data inside it.',
        'full': 'The caller of the function takes ownership of the data, and is responsible for freeing it.',
        'floating': 'The returned data has a floating reference.',
    },
}

DIRECTION_MODES = {
    'in': '-',
    'inout': 'The argument will be modified by the function.',
    'out': 'The argument will be set by the function.',
}

SCOPE_MODES = {
    'none': '-',
    'call': 'The callback arguments are valid during the call.',
    'notified': 'The callback arguments are valid until the notify function is called.',
    'async': 'The callback arguments are valid until the asynchronous call is completed.',
    'forever': 'The callback arguments are valid until the process is terminated',
}

SIGNAL_WHEN = {
    'first': "The default handler is called before the handlers added via `g_signal_connect()`.",
    'last': "The default handler is called after the handlers added via `g_signal_connect()`.",
    'cleanup': "The default handler is called after the handlers added via `g_signal_connect_after()`.",
}

FRAGMENT = {
    "aliases": "alias",
    "bitfields": "flags",
    "callbacks": "callback",
    "classes": "class",
    "constants": "const",
    "domains": "error",
    "enums": "enum",
    "functions": "func",
    "function_macros": "func",
    "interfaces": "iface",
    "structs": "struct",
    "unions": "union",
}


def type_name_to_cname(fqtn, is_pointer=False):
    res = []
    try:
        ns, name = fqtn.split('.', 1)
        res.append(ns)
        res.append(name)
    except ValueError:
        res.append(fqtn.replace('.', ''))
    if is_pointer:
        res.append('*')
    return "".join(res)


def transfer_note(transfer, direction, method=CallableType.FUNCTION):
    if direction in ['out', 'inout']:
        mode = OUT_ARG_TRANSFER_MODES[method]
    else:
        mode = IN_ARG_TRANSFER_MODES[method]
    return mode.get(transfer)


def gen_index_func(func, namespace, md=None):
    """Generates a dictionary with the callable metadata required by an index template"""
    name = func.name
    if getattr(func, "identifier"):
        identifier = func.identifier
    else:
        identifier = None
    if func.doc is not None:
        summary = utils.preprocess_docs(func.doc.content, namespace, summary=True, md=md)
    else:
        summary = MISSING_DESCRIPTION
    if func.available_since is not None:
        available_since = func.available_since
    else:
        available_since = None
    if func.deprecated:
        (version, msg) = func.deprecated_since
        deprecated_since = version
    else:
        deprecated_since = None
    return {
        "name": name,
        "identifier": identifier,
        "summary": summary,
        "available_since": available_since,
        "deprecated_since": deprecated_since,
    }


def gen_index_property(prop, namespace, md=None):
    name = prop.name
    if prop.doc is not None:
        summary = utils.preprocess_docs(prop.doc.content, namespace, summary=True, md=md)
    else:
        summary = MISSING_DESCRIPTION
    if prop.available_since is not None:
        available_since = prop.available_since
    else:
        available_since = None
    if prop.deprecated:
        (version, msg) = prop.deprecated_since
        deprecated_since = version
    else:
        deprecated_since = None
    return {
        "name": name,
        "summary": summary,
        "available_since": available_since,
        "deprecated_since": deprecated_since,
    }


def gen_index_signal(signal, namespace, md=None):
    name = signal.name
    if signal.doc is not None:
        summary = utils.preprocess_docs(signal.doc.content, namespace, summary=True, md=md)
    else:
        summary = MISSING_DESCRIPTION
    if signal.available_since is not None:
        available_since = signal.available_since
    else:
        available_since = None
    if signal.deprecated:
        (version, msg) = signal.deprecated_since
        deprecated_since = version
    else:
        deprecated_since = None
    return {
        "name": name,
        "summary": summary,
        "available_since": available_since,
        "deprecated_since": deprecated_since,
    }


def gen_index_ancestor(ancestor_type, namespace, config, md=None):
    ancestor_name = ancestor_type.name
    if '.' in ancestor_name:
        ns, ancestor_name = ancestor_name.split('.')
    else:
        ns = ancestor_type.namespace or namespace.name
    res = namespace.repository.find_class(ancestor_name, ns)
    if res is not None:
        ancestor_ns_name = res[0].name
        ancestor_ctype = res[1].base_ctype
        ancestor_ns = res[0]
        ancestor = res[1]
    else:
        ancestor_ns_name = ancestor_type.namespace or namespace.name
        ancestor_ctype = ancestor_type.base_ctype
        ancestor_ns = None
        ancestor = None
    n_methods = 0
    methods = []
    n_properties = 0
    properties = []
    n_signals = 0
    signals = []
    # We don't use real Template objects, here, because it can be
    # extremely expensive, unless we add a cache somewhere
    if ancestor is not None:
        # Set a hard-limit on the number of methods; base types can
        # add *a lot* of them; two dozens feel like a good compromise
        for m in ancestor.methods:
            is_hidden = config.is_hidden(ancestor_name, "method", m.name)
            if not is_hidden:
                n_methods += 1
        if n_methods > 0 and n_methods < 24:
            for m in ancestor.methods:
                if not config.is_hidden(ancestor_name, "method", m.name):
                    methods.append(gen_index_func(m, ancestor_ns, md))
        for p in ancestor.properties.values():
            if not config.is_hidden(ancestor_name, "property", p.name):
                n_properties += 1
                properties.append(gen_index_property(p, ancestor_ns, md))
        for s in ancestor.signals.values():
            if not config.is_hidden(ancestor_name, "signal", s.name):
                n_signals += 1
                signals.append(gen_index_signal(s, ancestor_ns, md))
    return {
        "namespace": ancestor_ns_name,
        "name": ancestor_name,
        "fqtn": f"{ancestor_ns_name}.{ancestor_name}",
        "type_cname": ancestor_ctype,
        "properties": properties,
        "n_properties": n_properties,
        "signals": signals,
        "n_signals": n_signals,
        "methods": methods,
        "n_methods": n_methods,
    }


def gen_index_implements(iface_type, namespace, config, md=None):
    iface_name = iface_type.name
    if '.' in iface_name:
        ns, iface_name = iface_name.split('.')
    else:
        ns = iface_type.namespace or namespace.name
    res = namespace.repository.find_interface(iface_name, ns)
    if res is not None:
        iface_ns_name = res[0].name
        iface_ctype = res[1].base_ctype
        iface_ns = res[0]
        iface = res[1]
    else:
        iface_ns_name = iface_type.namespace or namespace.name
        iface_ctype = iface_type.base_ctype
        iface_ns = None
        iface = None
    n_methods = 0
    methods = []
    n_properties = 0
    properties = []
    n_signals = 0
    signals = []
    if iface is not None:
        # Set a hard-limit on the number of methods; base types can
        # add *a lot* of them; two dozens feel like a good compromise
        for m in iface.methods:
            is_hidden = config.is_hidden(iface_name, "method", m.name)
            if not is_hidden:
                n_methods += 1
        if n_methods > 0 and n_methods < 24:
            for m in iface.methods:
                if not config.is_hidden(iface_name, "method", m.name):
                    methods.append(gen_index_func(m, iface_ns, md))
        for p in iface.properties.values():
            if not config.is_hidden(iface_name, "property", p.name):
                n_properties += 1
                properties.append(gen_index_property(p, iface_ns, md))
        for s in iface.signals.values():
            if not config.is_hidden(iface.name, "signal", s.name):
                n_signals += 1
                signals.append(gen_index_signal(s, iface_ns, md))
    return {
        "namespace": iface_ns_name,
        "name": iface_name,
        "fqtn": f"{iface_ns_name}.{iface_name}",
        "type_cname": iface_ctype,
        "properties": properties,
        "n_properties": n_properties,
        "signals": signals,
        "n_signals": n_signals,
        "methods": methods,
        "n_methods": n_methods,
    }


def gen_type_link(repository, namespace, name, ctype=None):
    res = repository.find_type(name, ns=namespace)
    if res is None:
        if ctype is not None:
            return f"<code>{ctype}</code>"
        elif name in ['utf8', 'filename']:
            return "<code>char*</code>"
        else:
            return f"<code>{name}</code>"

    ns, t = res
    if t.is_fundamental:
        return f"<code>{t.ctype}</code>"

    if isinstance(t, gir.Alias):
        link = f"alias.{name}.html"
    elif isinstance(t, gir.BitField):
        link = f"flags.{name}.html"
    elif isinstance(t, gir.Callback):
        link = f"callback.{name}.html"
    elif isinstance(t, gir.Class):
        link = f"class.{name}.html"
    elif isinstance(t, gir.ErrorDomain):
        link = f"error.{name}.html"
    elif isinstance(t, gir.Enumeration):
        link = f"enum.{name}.html"
    elif isinstance(t, gir.Interface):
        link = f"iface.{name}.html"
    elif isinstance(t, gir.Record):
        link = f"struct.{name}.html"
    elif isinstance(t, gir.Union):
        link = f"union.{name}.html"
    else:
        return f"<code>{t.ctype}</code>"

    text = f"<code>{t.ctype}</code>"
    if ns.name == repository.namespace.name:
        href = f'href="{link}"'
        css_class = ""
        data_link = ""
        data_ns = ""
    else:
        href = 'href="javascript:void(0)"'
        css_class = ' class="external"'
        data_link = f' data-link="{link}"'
        data_ns = f' data-namespace="{ns.name}"'

    return f"<a {href}{data_link}{data_ns}{css_class}>{text}</a>"


class TemplateConstant:
    def __init__(self, namespace, const):
        self.value = const.value
        self.identifier = const.ctype
        self.type_name = const.target.name
        self.type_cname = const.target.ctype
        self.namespace = namespace.name
        self.name = const.name
        self.fqtn = f"{namespace.name}.{const.name}"

        if const.doc is not None:
            self.summary = utils.preprocess_docs(const.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(const.doc.content, namespace)
            filename = const.doc.filename
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            line = const.doc.line
            const.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.stability = const.stability
        self.attributes = const.attributes
        self.available_since = const.available_since
        if const.deprecated:
            (version, msg) = const.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        self.introspectable = const.introspectable
        self.hierarchy_svg = None

    @property
    def c_decl(self):
        # String constants are unquoted in the GIR
        if self.type_name in ["utf8", "filename"]:
            return utils.code_highlight(f'#define {self.identifier} "{self.value}"')
        return utils.code_highlight(f"#define {self.identifier} {self.value}")


class TemplateProperty:
    def __init__(self, namespace, type_, prop):
        self.name = prop.name
        self.is_fundamental = prop.target.is_fundamental
        self.is_array = isinstance(prop.target, gir.ArrayType)
        self.is_list = isinstance(prop.target, gir.ListType)
        self.is_list_model = prop.target.name in ['Gio.ListModel', 'GListModel']
        self.readable = prop.readable
        self.writable = prop.writable
        self.construct = prop.construct
        self.construct_only = prop.construct_only
        if self.is_fundamental:
            self.type_name = prop.target.name
            self.type_cname = prop.target.ctype
        elif self.is_array or self.is_list:
            value_type = prop.target.value_type
            if value_type.name in ['utf8', 'filename']:
                self.type_name = "string[]"
                self.type_cname = "char*"
            elif value_type.ctype is not None:
                self.type_name = value_type.name
                self.type_cname = value_type.ctype
            else:
                self.type_name = value_type.name
                self.type_cname = type_name_to_cname(value_type.name, True)
        else:
            self.type_name = prop.target.name
            self.type_cname = prop.target.ctype
        if prop.doc is not None:
            self.summary = utils.preprocess_docs(prop.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(prop.doc.content, namespace)
            filename = prop.doc.filename
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            line = prop.doc.line
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.stability = prop.stability
        self.available_since = prop.available_since
        if prop.deprecated:
            (version, msg) = prop.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        self.introspectable = prop.introspectable

        def transform_set_attribute(namespace, prop, setter_func):
            if setter_func is None:
                log.warning(f"Missing value in the set attribute for {prop.name}")
                return None
            t = namespace.find_symbol(setter_func)
            if t is None:
                log.warning(f"Invalid Property.set attribute for {prop.name}: {setter_func}")
                return setter_func
            if not (isinstance(t, gir.Class) or isinstance(t, gir.Interface)):
                log.warning(f"Invalid setter function {setter_func} for property {namespace.name}.{t.name}:{prop.name}")
                return setter_func
            func_name = setter_func.replace(namespace.symbol_prefix[0] + '_', '')
            func_name = func_name.replace(t.symbol_prefix + '_', '')
            href = f"method.{t.name}.{func_name}.html"
            return Markup(f"<a href=\"{href}\"><code>{setter_func}</code></a>")

        def transform_get_attribute(namespace, prop, getter_func):
            if getter_func is None:
                log.warning(f"Missing value in the get attribute for {prop.name}")
                return None
            t = namespace.find_symbol(getter_func)
            if t is None:
                log.warning(f"Invalid Property.get attribute for {prop.name}: {getter_func}")
                return getter_func
            if not (isinstance(t, gir.Class) or isinstance(t, gir.Interface)):
                log.warning(f"Invalid getter function {getter_func} for property {namespace.name}.{t.name}:{prop.name}")
                return getter_func
            func_name = getter_func.replace(namespace.symbol_prefix[0] + '_', '')
            func_name = func_name.replace(t.symbol_prefix + '_', '')
            href = f"method.{t.name}.{func_name}.html"
            return Markup(f"<a href=\"{href}\"><code>{getter_func}</code></a>")

        def transform_default_attribute(namespace, prop, default_value):
            if default_value is None:
                log.warning(f"Missing value in the default attribute for {prop.name}")
                return None
            return Markup(f"<code>{default_value}</code>")

        ATTRIBUTE_NAMES = {
            "org.gtk.Property.set": {
                "label": "Setter method",
                "transform": transform_set_attribute,
            },
            "org.gtk.Property.get": {
                "label": "Getter method",
                "transform": transform_get_attribute,
            },
            "org.gtk.Property.default": {
                "label": "Default value",
                "transform": transform_default_attribute,
            },
        }

        self.attributes = {}
        for name in (prop.attributes or {}):
            value = prop.attributes[name]
            if name in ATTRIBUTE_NAMES:
                label = ATTRIBUTE_NAMES[name].get("label")
                transform = ATTRIBUTE_NAMES[name].get("transform")
                if transform is not None:
                    self.attributes[label] = transform(namespace, prop, value)
            else:
                self.attributes[name] = value

        def gen_method_link(ns, t, method):
            for m in t.methods:
                if m.name == method:
                    href = f"method.{t.name}.{m.name}.html"
                    return Markup(f'<a href="{href}"><code>{m.identifier}()</code></a>')
            return None

        if prop.setter is not None:
            link = gen_method_link(namespace, type_, prop.setter)
            if link is not None:
                self.attributes["Setter method"] = link
        if prop.getter is not None:
            link = gen_method_link(namespace, type_, prop.getter)
            if link is not None:
                self.attributes["Getter method"] = link

        if prop.default_value is not None:
            self.attributes["Default value"] = prop.default_value

        if self.is_fundamental:
            self.link = f"<code>{self.type_cname}</code>"
        elif self.is_array or self.is_list:
            self.link = f"<code>{self.type_cname}</code>"
        elif prop.target.name is not None:
            name = prop.target.name
            if '.' in name:
                ns, name = name.split('.')
            else:
                ns = namespace.name
            self.link = gen_type_link(namespace.repository, ns, name, self.type_cname)

    @property
    def c_decl(self):
        flags = []
        if self.readable:
            flags += ['read']
        if self.writable:
            flags += ['write']
        if self.construct:
            flags += ['construct']
        if self.construct_only:
            flags += ['construct-only']
        flags = ", ".join(flags)
        return f"property {self.name}: {self.type_name} [ {flags} ]"


class TemplateArgument:
    def __init__(self, namespace, call, argument, callable_type):
        self.name = argument.name
        self.type_name = argument.target.name
        self.is_array = isinstance(argument.target, gir.ArrayType)
        self.is_list = isinstance(argument.target, gir.ListType)
        self.is_map = isinstance(argument.target, gir.MapType)
        self.is_varargs = isinstance(argument.target, gir.VarArgs)
        self.is_macro = isinstance(call, gir.FunctionMacro)
        self.is_list_model = self.type_name in ['Gio.ListModel', 'GListModel']
        self.is_fundamental = argument.target.is_fundamental
        if isinstance(call, gir.FunctionMacro):
            self.type_cname = '-'
        elif self.is_array or self.is_list:
            if argument.target.ctype is None:
                if argument.target.value_type.name in ['utf8', 'filename']:
                    self.type_cname = 'char**'
                elif argument.target.value_type.ctype is not None:
                    self.type_cname = argument.target.value_type.ctype + '*'
                else:
                    self.type_cname = 'gpointer'
            else:
                self.type_cname = argument.target.ctype
        elif self.type_name in ['utf8', 'filename']:
            if argument.target.ctype is None:
                self.type_cname = 'char*'
            else:
                self.type_cname = argument.target.ctype
        elif self.is_fundamental:
            if argument.target.ctype is None:
                self.type_cname = type_name_to_cname(argument.target.name, False)
            else:
                self.type_cname = argument.target.ctype
        else:
            self.type_cname = argument.target.ctype
            if self.type_cname is None:
                self.type_cname = type_name_to_cname(argument.target.name, True)
        self.direction = argument.direction or 'in'
        self.direction_note = DIRECTION_MODES[argument.direction]
        self.transfer = argument.transfer or 'none'
        self.transfer_note = transfer_note(self.transfer, self.direction, callable_type)
        self.optional = argument.optional
        self.nullable = argument.nullable
        self.scope = SCOPE_MODES[argument.scope or 'none']
        self.introspectable = argument.introspectable
        if argument.closure != -1:
            self.closure = call.parameters[argument.closure]
        else:
            self.closure = None
        if self.is_array:
            self.value_type = argument.target.value_type.name
            self.value_type_cname = argument.target.value_type.ctype
            self.fixed_size = argument.target.fixed_size
            self.zero_terminated = argument.target.zero_terminated
            self.len_arg = argument.target.length != -1 and call.parameters[argument.target.length].name
        if self.is_list:
            self.value_type = argument.target.value_type.name
            self.value_type_cname = argument.target.value_type.ctype
        if self.is_list_model:
            self.value_type = argument.attributes.get('element-type', 'GObject')
        if self.type_name in ['utf8', 'filename']:
            self.string_note = STRING_TYPES[self.type_name]
        elif self.is_array or self.is_list:
            if self.value_type in ['utf8', 'filename']:
                self.string_note = STRING_ELEMENT_TYPES[self.value_type]
        if argument.doc is not None:
            self.summary = utils.preprocess_docs(argument.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(argument.doc.content, namespace)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")
        if self.is_array:
            name = self.value_type
        elif self.is_list:
            name = self.value_type
        elif self.type_name is not None:
            name = self.type_name
        else:
            name = None
        if name is not None:
            if self.is_fundamental:
                self.link = f"<code>{self.type_cname}</code>"
            elif self.is_array:
                self.link = f"<code>{self.value_type_cname}</code>"
            elif self.is_list:
                self.link = f"<code>{self.value_type_cname}</code>"
            elif self.is_list_model:
                self.link = f"<code>{self.value_type}</code>"
            else:
                if '.' in name:
                    ns, name = name.split('.')
                else:
                    ns = namespace.name
                self.link = gen_type_link(namespace.repository, ns, name, self.type_cname)

    @property
    def is_pointer(self):
        if self.type_cname is None:
            return False
        if self.direction in ['out', 'inout'] and self.is_fundamental and self.type_cname.count('*') == 1:
            return False
        if self.is_fundamental and self.type_cname in ['gpointer', 'gconstpointer']:
            return True
        return '*' in self.type_cname

    @property
    def c_decl(self):
        if self.is_varargs:
            return "..."
        elif self.is_macro:
            return f"{self.name}"
        else:
            return f"{self.type_cname} {self.name}"


class TemplateReturnValue:
    def __init__(self, namespace, call, retval, callable_type):
        self.name = retval.name
        self.type_name = retval.target.name
        self.type_cname = retval.target.ctype
        self.is_fundamental = retval.target.is_fundamental
        if self.type_cname is None:
            self.type_cname = type_name_to_cname(retval.target.name, True)
        self.is_array = isinstance(retval.target, gir.ArrayType)
        self.is_list = isinstance(retval.target, gir.ListType)
        self.is_list_model = self.type_name in ['Gio.ListModel', 'GListModel']
        self.transfer = retval.transfer or 'none'
        transfer_mode = RETURN_TRANSFER_MODES[callable_type]
        self.transfer_note = transfer_mode.get(self.transfer)
        self.nullable = retval.nullable
        if self.is_array:
            self.value_type = retval.target.value_type.name
            self.value_type_cname = retval.target.value_type.ctype
            self.fixed_size = retval.target.fixed_size
            self.zero_terminated = retval.target.zero_terminated
            self.len_arg = retval.target.length != -1 and call.parameters[retval.target.length].name
        if self.is_list:
            self.value_type = retval.target.value_type.name
            self.value_type_cname = retval.target.value_type.ctype
        if self.is_list_model:
            self.value_type = retval.attributes.get('element-type', 'GObject')
        if self.type_name in ['utf8', 'filename']:
            self.string_note = STRING_TYPES[self.type_name]
        elif self.is_array or self.is_list:
            if self.value_type in ['utf8', 'filename']:
                self.string_note = STRING_ELEMENT_TYPES[self.value_type]
        if retval.doc is not None:
            self.summary = utils.preprocess_docs(retval.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(retval.doc.content, namespace)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")
        self.introspectable = retval.introspectable
        if self.is_array:
            name = self.value_type
        elif self.is_list:
            name = self.value_type
        elif self.is_list_model:
            name = self.value_type
        elif self.type_name is not None:
            name = self.type_name
        else:
            name = None
        if name is not None:
            if self.is_fundamental:
                self.link = f"<code>{self.type_cname}</code>"
            elif self.is_array:
                self.link = f"<code>{self.value_type_cname}</code>"
            elif self.is_list:
                self.link = f"<code>{self.value_type_cname}</code>"
            elif self.is_list_model:
                self.link = f"<code>{self.value_type}</code>"
            else:
                if '.' in name:
                    ns, name = name.split('.')
                else:
                    ns = namespace.name
                self.link = gen_type_link(namespace.repository, ns, name, self.type_cname)

    @property
    def is_pointer(self):
        if self.type_cname is None:
            return False
        elif self.is_fundamental and self.type_cname in ['gpointer', 'gconstpointer']:
            return True
        else:
            return '*' in self.type_cname


class TemplateSignal:
    def __init__(self, namespace, type_, signal):
        self.name = signal.name
        self.type_cname = type_.base_ctype
        self.identifier = signal.name.replace("-", "_")

        if signal.doc is not None:
            self.summary = utils.preprocess_docs(signal.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(signal.doc.content, namespace)
            filename = signal.doc.filename
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            line = signal.doc.line
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.is_detailed = signal.detailed
        self.is_action = signal.action
        self.no_recurse = signal.no_recurse
        self.no_hooks = signal.no_hooks
        if signal.when:
            self.when = utils.preprocess_docs(SIGNAL_WHEN[signal.when], namespace)

        self.arguments = []
        for arg in signal.parameters:
            self.arguments.append(TemplateArgument(namespace, signal, arg, CallableType.SIGNAL))

        self.return_value = None
        if not isinstance(signal.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(namespace, signal, signal.return_value, CallableType.SIGNAL)

        self.stability = signal.stability
        self.attributes = signal.attributes
        self.available_since = signal.available_since
        if signal.deprecated:
            (version, msg) = signal.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        self.introspectable = signal.introspectable

    @property
    def c_decl(self):
        res = []
        if self.return_value is None:
            res += ["void"]
        else:
            res += [f"{self.return_value.type_cname}"]
        res += [f"{self.identifier} ("]
        res += [f"  {self.type_cname}* self,"]
        for arg in self.arguments:
            res += [f"  {arg.c_decl},"]
        res += ["  gpointer user_data"]
        res += [")"]
        return utils.code_highlight("\n".join(res))


class TemplateMethod:
    def __init__(self, namespace, type_, method):
        self.name = method.name
        self.identifier = method.identifier

        if method.doc is not None:
            self.summary = utils.preprocess_docs(method.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(method.doc.content, namespace)
            filename = method.doc.filename
            line = method.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.is_inline = method.inline
        self.throws = method.throws

        if method.instance_param is not None:
            self.instance_parameter = TemplateArgument(namespace, method, method.instance_param, CallableType.METHOD)
        else:
            self.instance_parameter = None

        self.arguments = []
        for arg in method.parameters:
            self.arguments.append(TemplateArgument(namespace, method, arg, CallableType.METHOD))

        self.return_value = None
        if not isinstance(method.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(namespace, method, method.return_value, CallableType.METHOD)

        self.stability = method.stability
        self.available_since = method.available_since
        if method.deprecated:
            (version, msg) = method.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        if method.source_position is not None:
            filename, line = method.source_position
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.source_location = (filename, line)

        self.introspectable = method.introspectable

        self.shadows = method.shadows
        if method.shadows:
            for m in type_.methods:
                if m.name == method.shadows:
                    self.shadows_symbol = m.identifier
                    break
        self.shadowed_by = method.shadowed_by
        if method.shadowed_by:
            for m in type_.methods:
                if m.name == method.shadowed_by:
                    self.shadowed_by_symbol = m.identifier
                    break

        self.finish_func = method.finish_func
        if method.finish_func:
            for m in type_.methods:
                if m.name == method.finish_func:
                    self.finish_func_symbol = m.identifier
                    break

        def transform_property_attribute(namespace, type_, method, value):
            if value in type_.properties:
                text = f"{namespace.name}.{type_.name}:{value}"
                href = f"property.{type_.name}.{value}.html"
                return Markup(f"<a href=\"{href}\"><code>{text}</code></a>")
            log.warning(f"Property {value} linked to method {method.name} not found in {namespace.name}.{type_.name}")
            return value

        def transform_signal_attribute(namespace, type_, method, value):
            if value in type_.signals:
                text = f"{namespace.name}.{type_.name}::{value}"
                href = f"signal.{type_.name}.{value}.html"
                return Markup(f"<a href=\"{href}\"><code>{text}</code></a>")
            log.warning(f"Signal {value} linked to method {method.name} not found in {namespace.name}.{type_.name}")
            return value

        ATTRIBUTE_NAMES = {
            "org.gtk.Method.set_property": {
                "label": "Sets property",
                "transform": transform_property_attribute,
            },
            "org.gtk.Method.get_property": {
                "label": "Gets property",
                "transform": transform_property_attribute,
            },
            "org.gtk.Method.signal": {
                "label": "Emits signal",
                "transform": transform_signal_attribute,
            }
        }

        self.attributes = {}
        for name in (method.attributes or {}):
            value = method.attributes[name]
            if name in ATTRIBUTE_NAMES:
                label = ATTRIBUTE_NAMES[name].get("label")
                transform = ATTRIBUTE_NAMES[name].get("transform")
                if transform is not None:
                    self.attributes[label] = transform(namespace, type_, method, value)
            else:
                self.attributes[name] = value

        def gen_property_link(namespace, t, prop_name):
            if prop_name not in t.properties:
                return None
            prop = t.properties[prop_name]
            text = f"{namespace.name}.{t.name}:{prop.name}"
            href = f"property.{t.name}.{prop.name}.html"
            return Markup(f'<a href="{href}"><code>{text}</code></a>')

        if isinstance(method, gir.Method):
            if method.set_property is not None:
                link = gen_property_link(namespace, type_, method.set_property)
                if link is not None:
                    self.attributes["Sets property"] = link
            if method.get_property is not None:
                link = gen_property_link(namespace, type_, method.get_property)
                if link is not None:
                    self.attributes["Gets property"] = link

    @property
    def c_decl(self):
        res = []
        if self.return_value is None:
            retval = "void"
        else:
            retval = self.return_value.type_cname
        if self.is_inline:
            res += [f"static inline {retval}"]
        else:
            res += [retval]
        if self.identifier is not None:
            res += [f"{self.identifier} ("]
        else:
            res += [f"{self.name} ("]
        n_args = len(self.arguments)
        if n_args == 0:
            if self.instance_parameter is not None:
                res += [f"  {self.instance_parameter.type_cname} {self.instance_parameter.name}"]
            elif not self.throws:
                res += ["   void"]
        else:
            if self.instance_parameter is not None:
                res += [f"  {self.instance_parameter.type_cname} {self.instance_parameter.name},"]
            for (idx, arg) in enumerate(self.arguments):
                if idx == n_args - 1 and not self.throws:
                    res += [f"  {arg.c_decl}"]
                else:
                    res += [f"  {arg.c_decl},"]
        if self.throws:
            res += ["  GError** error"]
        res += [")"]
        return utils.code_highlight("\n".join(res))


class TemplateClassMethod:
    def __init__(self, namespace, cls, method):
        self.name = method.name
        self.identifier = method.identifier
        self.class_type_cname = namespace.identifier_prefix[0] + cls.type_struct

        self.throws = method.throws

        if method.doc is not None:
            self.summary = utils.preprocess_docs(method.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(method.doc.content, namespace)
            filename = method.doc.filename
            line = method.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.instance_parameter = TemplateArgument(namespace, method, method.instance_param, CallableType.CLASS_METHOD)

        self.arguments = []
        for arg in method.parameters:
            self.arguments.append(TemplateArgument(namespace, method, arg, CallableType.CLASS_METHOD))

        self.return_value = None
        if not isinstance(method.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(namespace, method, method.return_value, CallableType.CLASS_METHOD)

        self.stability = method.stability
        self.attributes = method.attributes
        self.available_since = method.available_since
        if method.deprecated:
            (version, msg) = method.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        if method.source_position is not None:
            filename, line = method.source_position
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.source_location = (filename, line)

        self.introspectable = method.introspectable

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
            res += [f"  {self.instance_parameter.type_cname} {self.instance_parameter.name}"]
        else:
            res += [f"  {self.instance_parameter.type_cname} {self.instance_parameter.name},"]
            for (idx, arg) in enumerate(self.arguments):
                if idx == n_args - 1 and not self.throws:
                    res += [f"  {arg.c_decl}"]
                else:
                    res += [f"  {arg.c_decl},"]
        if self.throws:
            res += ["  GError** error"]
        res += [")"]
        return utils.code_highlight("\n".join(res))


class TemplateFunction:
    def __init__(self, namespace, type_, func):
        self.identifier = func.identifier
        self.name = func.name
        self.namespace = namespace.name

        self.is_type_func = type_ is not None
        self.is_macro = isinstance(func, gir.FunctionMacro)
        self.is_inline = func.inline

        self.throws = func.throws

        if func.doc is not None:
            self.summary = utils.preprocess_docs(func.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(func.doc.content, namespace)
            filename = func.doc.filename
            line = func.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.arguments = []
        for arg in func.parameters:
            self.arguments.append(TemplateArgument(namespace, func, arg, CallableType.FUNCTION))

        self.return_value = None
        if not isinstance(func.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(namespace, func, func.return_value, CallableType.FUNCTION)

        self.stability = func.stability
        self.attributes = func.attributes
        self.available_since = func.available_since
        if func.deprecated:
            (version, msg) = func.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        if func.source_position is not None:
            filename, line = func.source_position
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.source_location = (filename, line)

        self.introspectable = func.introspectable

        self.shadows = func.shadows
        if func.shadows:
            f = namespace.find_function(func.shadows)
            if f is not None:
                self.shadows_symbol = f.identifier
        self.shadowed_by = func.shadowed_by
        if func.shadowed_by:
            f = namespace.find_function(func.shadowed_by)
            if f is not None:
                self.shadowed_by_symbol = f.identifier

        self.finish_func = func.finish_func
        if func.finish_func:
            if type_ is not None:
                type_funcs = []
                type_funcs.extend(getattr(type_, 'constructors', []))
                type_funcs.extend(getattr(type_, 'functions', []))
                for f in type_funcs:
                    if f.name == func.finish_func:
                        self.finish_func_symbol = f.identifier
                        break
            else:
                f = namespace.find_function(func.finish_func)
                if f is not None:
                    self.finish_func_symbol = f.identifier

    @property
    def c_decl(self):
        res = []
        if self.is_macro:
            res += [f"#define {self.identifier} ("]
        else:
            if self.return_value is None:
                retval = "void"
            else:
                retval = self.return_value.type_cname
            if self.is_inline:
                res += [f"static inline {retval}"]
            else:
                res += [retval]
            res += [f"{self.identifier} ("]
        n_args = len(self.arguments)
        if n_args == 0 and not self.throws:
            res += ["  void"]
        else:
            for (idx, arg) in enumerate(self.arguments):
                if idx == n_args - 1 and not self.throws:
                    res += [f"  {arg.c_decl}"]
                else:
                    res += [f"  {arg.c_decl},"]
        if self.throws:
            res += ["  GError** error"]
        res += [")"]
        return utils.code_highlight("\n".join(res))


class TemplateCallback:
    def __init__(self, namespace, cb, field=False):
        self.name = cb.name
        self.type_cname = cb.ctype
        self.identifier = cb.name.replace("-", "_")
        self.field = field

        if cb.doc is not None:
            self.summary = utils.preprocess_docs(cb.doc.content, namespace, summary=True)
            self.description = utils.preprocess_docs(cb.doc.content, namespace)
            filename = cb.doc.filename
            line = cb.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.arguments = []
        for arg in cb.parameters:
            self.arguments.append(TemplateArgument(namespace, cb, arg, CallableType.CALLBACK))

        self.return_value = None
        if not isinstance(cb.return_value.target, gir.VoidType):
            self.return_value = TemplateReturnValue(namespace, cb, cb.return_value, CallableType.CALLBACK)

        self.throws = cb.throws

        self.stability = cb.stability
        self.attributes = cb.attributes
        self.available_since = cb.available_since
        if cb.deprecated:
            (version, msg) = cb.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        self.introspectable = cb.introspectable

    @property
    def c_decl(self):
        res = []
        if self.field:
            arg_indent = "    "
        else:
            arg_indent = "  "
        if self.return_value is None:
            retval = "void"
        else:
            retval = f"{self.return_value.type_cname}"
        if self.field:
            res += [f"{retval} (* {self.identifier}) ("]
        else:
            res += [retval]
            res += [f"(* {self.type_cname}) ("]
        n_args = len(self.arguments)
        if n_args == 0:
            res += ["void"]
        else:
            for (idx, arg) in enumerate(self.arguments):
                if idx == n_args - 1 and not self.throws:
                    res += [f"{arg_indent}{arg.type_cname} {arg.name}"]
                else:
                    res += [f"{arg_indent}{arg.type_cname} {arg.name},"]
        if self.throws:
            res += [f"{arg_indent}GError** error"]
        if self.field:
            res += ["  )"]
        else:
            res += [")"]
        if self.field:
            return "\n".join(res)
        else:
            return utils.code_highlight("\n".join(res))


class TemplateField:
    def __init__(self, namespace, field):
        self.name = field.name
        self.is_fundamental = False
        self.is_callback = False
        self.is_array = False
        self.is_map = False
        self.is_list = False
        self.is_list_model = False
        if field.target is not None:
            self.is_fundamental = field.target.is_fundamental
            if isinstance(field.target, gir.Callback):
                self.is_callback = True
                self.type_name = field.target.name
                self.type_cname = TemplateCallback(namespace, field.target, field=True).c_decl
            elif isinstance(field.target, gir.ArrayType):
                self.is_array = True
                self.type_name = field.target.name
                self.type_cname = field.target.value_type.ctype
                self.fixed_size = field.target.fixed_size
                self.zero_terminated = field.target.zero_terminated
                self.value_type = field.target.value_type.name
                self.value_type_cname = field.target.value_type.ctype
            elif isinstance(field.target, gir.ListType):
                self.is_list = True
                self.type_name = field.target.value_type.name
                self.type_cname = field.target.value_type.ctype
                self.value_type = field.target.value_type.name
                self.value_type_cname = field.target.value_type.ctype
            elif field.target.name in ['Gio.ListModel', 'GListModel']:
                self.is_list_model = True
                if field.attributes is not None:
                    self.value_type = field.attributes.get('element-type', 'GObject')
            elif isinstance(field.target, gir.MapType):
                self.is_map = True
            else:
                self.type_name = field.target.name
                self.type_cname = field.target.ctype
        else:
            self.type_name = 'none'
            self.type_cname = 'gpointer'
        self.private = field.private
        self.bits = field.bits
        if field.doc is not None:
            self.description = utils.preprocess_docs(field.doc.content, namespace)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")
        self.introspectable = field.introspectable
        if self.type_name in ['utf8', 'filename']:
            self.string_note = STRING_TYPES[self.type_name]
        elif self.is_array or self.is_list:
            if self.value_type in ['utf8', 'filename']:
                self.string_note = STRING_ELEMENT_TYPES[self.value_type]
        if self.is_array:
            name = self.value_type
        elif self.is_list:
            name = self.value_type
        elif self.is_list_model:
            name = self.value_type
        elif self.type_name is not None:
            name = self.type_name
        else:
            name = None
        if name is not None:
            if self.is_fundamental:
                self.link = f"<code>{self.type_cname}</code>"
            else:
                if '.' in name:
                    ns, name = name.split('.')
                else:
                    ns = namespace.name
                self.link = gen_type_link(namespace.repository, ns, name, self.type_cname)

    @property
    def c_decl(self):
        res = ""
        if self.is_callback:
            res = f"{self.type_cname};"
        elif self.is_array:
            if self.fixed_size > 0:
                res = f"{self.type_cname} {self.name}[{self.fixed_size}]"
            else:
                res = f"{self.type_cname} {self.name}[]"
        elif self.bits > 0:
            res = f"{self.type_cname} {self.name} : {self.bits}"
        else:
            res = f"{self.type_cname} {self.name}"
        return res


class TemplateInterface:
    def __init__(self, namespace, interface, config):
        if isinstance(interface, gir.Interface):
            if '.' in interface.name:
                self.namespace, self.name = interface.name.split('.')
                self.fqtn = interface.name
            else:
                self.namespace = interface.namespace
                self.name = interface.name
                self.fqtn = f"{self.namespace}.{self.name}"
        elif isinstance(interface, gir.Type):
            if '.' in interface.name:
                self.namespace, self.name = interface.name.split('.')
            else:
                self.namespace = interface.namespace or namespace.name
                self.name = interface.name
            self.fqtn = f"{self.namespace}.{self.name}"
            self.requires = "GObject.Object"
            self.link_prefix = "iface"
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")
            return

        md = markdown.Markdown(extensions=utils.MD_EXTENSIONS,
                               extension_configs=utils.MD_EXTENSIONS_CONF)

        requires = interface.prerequisite
        if requires is None:
            self.requires_namespace = "GObject"
            self.requires_name = "Object"
            self.requires_ctype = "GObject"
        elif '.' in requires.name:
            self.requires_namespace, self.requires_name = requires.name.split('.')
            self.requires_ctype = requires.ctype
        else:
            self.requires_namespace = requires.namespace or namespace.name
            self.requires_name = requires.name
            self.requires_ctype = requires.ctype

        self.requires_fqtn = f"{self.requires_namespace}.{self.requires_name}"
        log.debug(f"Preqrequisite for {self.fqtn}: {self.requires_fqtn}")

        def prereq_link_fragment(_ns: gir.Namespace, ns: str, name: str) -> str:
            if _ns.repository.find_class(name, ns) is not None:
                return "class"
            elif _ns.repository.find_interface(name, ns) is not None:
                return "iface"
            else:
                log.error(f"Invalid prerequisite type {ns}.{name}")

        self.requires_link_fragment = prereq_link_fragment(namespace, self.requires_namespace, self.requires_name)

        self.symbol_prefix = f"{namespace.symbol_prefix[0]}_{interface.symbol_prefix}"
        self.type_cname = interface.base_ctype

        self.link_prefix = "iface"

        if interface.doc is not None:
            self.summary = utils.preprocess_docs(interface.doc.content, namespace, summary=True, md=md)
            self.description = utils.preprocess_docs(interface.doc.content, namespace, md=md)
            self.description_toc = md.toc_tokens is not None and md.toc_tokens.copy() or None
            filename = interface.doc.filename
            line = interface.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.stability = interface.stability
        self.attributes = interface.attributes
        self.available_since = interface.available_since
        if interface.deprecated:
            (version, msg) = interface.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        self.introspectable = interface.introspectable

        self.class_name = interface.type_struct

        self.class_struct = namespace.find_record(interface.type_struct)
        if self.class_struct is not None:
            if self.class_struct.doc:
                self.class_description = utils.preprocess_docs(self.class_struct.doc.content, namespace, md=md)
            else:
                self.class_description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")
            self.class_fields = []
            for field in self.class_struct.fields:
                if not field.private:
                    self.class_fields.append(TemplateField(namespace, field))
            self.class_methods = []
            for method in self.class_struct.methods:
                self.class_methods.append(gen_index_func(method, namespace, md))
        else:
            self.class_fields = []
            self.class_methods = []

        self.properties = []
        if len(interface.properties) != 0:
            for pname, prop in interface.properties.items():
                if not config.is_hidden(interface.name, "property", pname):
                    self.properties.append(gen_index_property(prop, namespace, md))

        self.signals = []
        if len(interface.signals) != 0:
            for sname, signal in interface.signals.items():
                if not config.is_hidden(interface.name, "signal", sname):
                    self.signals.append(gen_index_signal(signal, namespace, md))

        self.methods = []
        if len(interface.methods) != 0:
            for method in interface.methods:
                if not config.is_hidden(interface.name, "method", method.name):
                    self.methods.append(gen_index_func(method, namespace, md))

        self.virtual_methods = []
        if len(interface.virtual_methods) != 0:
            for vfunc in interface.virtual_methods:
                self.virtual_methods.append(gen_index_func(vfunc, namespace, md))

        self.type_funcs = []
        if len(interface.functions) != 0:
            for func in interface.functions:
                if not config.is_hidden(interface.name, "function", func.name):
                    self.type_funcs.append(gen_index_func(func, namespace, md))

        self.implementations = []
        if len(interface.implementations) != 0:
            for impl in interface.implementations:
                self.implementations.append({
                    'name': impl.name,
                    'ctype': impl.ctype,
                })

    @property
    def c_decl(self):
        return f"interface {self.fqtn} : {self.requires_fqtn}"


class TemplateClass:
    def __init__(self, namespace, cls, config, recurse=True):
        self.symbol_prefix = f"{namespace.symbol_prefix[0]}_{cls.symbol_prefix}"
        self.type_cname = cls.base_ctype
        self.link_prefix = "class"
        self.fundamental = cls.fundamental
        self.abstract = cls.abstract

        md = markdown.Markdown(extensions=utils.MD_EXTENSIONS,
                               extension_configs=utils.MD_EXTENSIONS_CONF)

        if '.' in cls.name:
            self.namespace = cls.name.split('.')[0]
            self.name = cls.name.split('.')[1]
            self.fqtn = cls.name
        else:
            self.namespace = namespace.name
            self.name = cls.name
            self.fqtn = f"{namespace.name}.{self.name}"

        if cls.parent is None or cls.fundamental:
            self.parent_fqtn = 'GObject.TypeInstance'
            self.parent_cname = 'GTypeInstance*'
            self.parent_name = 'TypeInstance'
            self.parent_namespace = 'GObject'
        elif '.' in cls.parent.name:
            self.parent_fqtn = cls.parent.name
            self.parent_cname = cls.parent.ctype
            self.parent_namespace = self.parent_fqtn.split('.')[0]
            self.parent_name = self.parent_fqtn.split('.')[1]
        else:
            self.parent_cname = cls.parent.ctype
            self.parent_name = cls.parent.name
            self.parent_namespace = cls.parent.namespace or namespace.name
            self.parent_fqtn = f"{self.parent_namespace}.{self.parent_name}"

        self.ancestors = []
        if recurse:
            for ancestor_type in cls.ancestors:
                self.ancestors.append(gen_index_ancestor(ancestor_type, namespace, config, md))

        if cls.descendants:
            self.descendants = []
            for descendant in cls.descendants:
                self.descendants.append({
                    'name': descendant.name,
                    'ctype': descendant.ctype,
                })

        self.class_name = cls.type_struct

        self.instance_struct = None
        if len(cls.fields) != 0:
            self.instance_struct = self.class_name

        if cls.type_struct is not None:
            self.class_struct = namespace.find_record(cls.type_struct)
        else:
            self.class_struct = None

        # "Final", in the absence of an actual flag or annotation,
        # is determined through an heuristic; if either the instance
        # or the class structures are missing or disguised, then the
        # type cannot be derived
        if self.instance_struct is None or self.class_struct is None or self.class_struct.disguised:
            self.final = True
        else:
            self.final = False

        if cls.doc is not None:
            self.summary = utils.preprocess_docs(cls.doc.content, namespace, summary=True, md=md)
            self.description = utils.preprocess_docs(cls.doc.content, namespace, md=md)
            self.description_toc = md.toc_tokens is not None and md.toc_tokens.copy() or None
            filename = cls.doc.filename
            line = cls.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.stability = cls.stability
        self.attributes = cls.attributes
        self.available_since = cls.available_since
        if cls.deprecated:
            (version, msg) = cls.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace, md=md),
            }
        else:
            self.deprecated_since = None

        self.introspectable = cls.introspectable

        self.fields = []
        if len(cls.fields) > 1:
            # The first field is always the parent instance
            for field in cls.fields[1:]:
                if not field.private:
                    self.fields.append(TemplateField(namespace, field))

        self.properties = []
        if len(cls.properties) != 0:
            for pname, prop in cls.properties.items():
                if not config.is_hidden(cls.name, "property", pname):
                    self.properties.append(gen_index_property(prop, namespace, md))

        self.signals = []
        if len(cls.signals) != 0:
            for sname, signal in cls.signals.items():
                if not config.is_hidden(cls.name, "signal", sname):
                    self.signals.append(gen_index_signal(signal, namespace, md))

        self.ctors = []
        if len(cls.constructors) != 0:
            for ctor in cls.constructors:
                if not config.is_hidden(cls.name, "constructor", ctor.name):
                    self.ctors.append(gen_index_func(ctor, namespace, md))

        self.methods = []
        if len(cls.methods) != 0:
            for method in cls.methods:
                if not config.is_hidden(cls.name, "method", method.name):
                    self.methods.append(gen_index_func(method, namespace, md))

        if self.class_struct is not None:
            self.class_ctype = self.class_struct.ctype
            if self.class_struct.doc:
                self.class_description = utils.preprocess_docs(self.class_struct.doc.content, namespace, md=md)
            else:
                self.class_description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")
            self.class_fields = []
            for field in self.class_struct.fields:
                if not field.private:
                    self.class_fields.append(TemplateField(namespace, field))
            self.class_methods = []
            for method in self.class_struct.methods:
                self.class_methods.append(gen_index_func(method, namespace, md))
        else:
            self.class_fields = []
            self.class_methods = []

        self.interfaces = []
        if len(cls.implements) != 0:
            for iface_type in cls.implements:
                self.interfaces.append(gen_index_implements(iface_type, namespace, config, md))

        self.virtual_methods = []
        if len(cls.virtual_methods) != 0:
            for vfunc in cls.virtual_methods:
                self.virtual_methods.append(gen_index_func(vfunc, namespace, md))

        self.type_funcs = []
        if len(cls.functions) != 0:
            for func in cls.functions:
                if not config.is_hidden(cls.name, "function", func.name):
                    self.type_funcs.append(gen_index_func(func, namespace, md))

    @property
    def show_methods(self):
        if len(self.methods) > 0:
            return True
        for ancestor in self.ancestors:
            if ancestor["n_methods"] > 0:
                return True
        for iface in self.interfaces:
            if iface["n_methods"] > 0:
                return True
        return False

    @property
    def show_properties(self):
        if len(self.properties) > 0:
            return True
        for ancestor in self.ancestors:
            if ancestor["n_properties"] > 0:
                return True
        for iface in self.interfaces:
            if iface["n_properties"] > 0:
                return True
        return False

    @property
    def show_signals(self):
        if len(self.signals) > 0:
            return True
        for ancestor in self.ancestors:
            if ancestor["n_signals"] > 0:
                return True
        for iface in self.interfaces:
            if iface["n_signals"] > 0:
                return True
        return False

    @property
    def c_decl(self):
        if self.abstract:
            res = [f"abstract class {self.fqtn} : {self.parent_fqtn}"]
        elif self.final:
            res = [f"final class {self.fqtn} : {self.parent_fqtn}"]
        else:
            res = [f"class {self.fqtn} : {self.parent_fqtn}"]
        n_interfaces = len(self.interfaces)
        if n_interfaces:
            ifaces = [x['fqtn'] for x in self.interfaces]
            ifaces = ", ".join(ifaces)
            res += [f"  implements {ifaces} {{"]
        else:
            res += ["{"]
        n_fields = len(self.fields)
        if n_fields > 0:
            for (idx, field) in enumerate(self.fields):
                if idx < n_fields - 1:
                    res += [f"  {field.c_decl},"]
                else:
                    res += [f"  {field.c_decl}"]
        else:
            res += ["  /* No available fields */"]
        res += ["}"]
        return "\n".join(res)

    @property
    def dot(self):

        def fmt_attrs(attrs):
            return ','.join(f'{k}="{v}"' for k, v in attrs.items())

        def add_link(attrs, other, fragment):
            if other['namespace'] == self.namespace:
                attrs['href'] = f"{fragment}.{other['name']}.html"
                attrs['class'] = 'link'
            else:
                attrs['tooltip'] = other['fqtn']

        ancestors = []
        implements = []
        res = ["graph hierarchy {"]
        res.append("  bgcolor=\"transparent\";")
        node_attrs = {
            'shape': 'box',
            'style': 'rounded',
            'border': 0
        }
        this_attrs = {
            'label': self.type_cname,
            'tooltip': self.type_cname
        }
        this_attrs.update(node_attrs)
        res.append(f"  this [{fmt_attrs(this_attrs)}];")
        for idx, ancestor in enumerate(self.ancestors):
            node_id = f"ancestor_{idx}"
            ancestor_attrs = {
                'label': ancestor['type_cname']
            }
            ancestor_attrs.update(node_attrs)
            add_link(ancestor_attrs, ancestor, 'class')
            res.append(f"  {node_id} [{fmt_attrs(ancestor_attrs)}];")
            ancestors.append(node_id)
        ancestors.reverse()
        for idx, iface in enumerate(getattr(self, "interfaces", [])):
            node_id = f"implements_{idx}"
            iface_attrs = {
                'label': iface['type_cname'],
                'fontname': 'sans-serif',
                'shape': 'box',
            }
            add_link(iface_attrs, iface, 'iface')
            res.append(f"  {node_id} [{fmt_attrs(iface_attrs)}];")
            implements.append(node_id)
        if len(ancestors) > 0:
            res.append("  " + " -- ".join(ancestors) + " -- this;")
        for node in implements:
            res.append(f"  this -- {node} [style=dotted];")
        res.append("}")
        return "\n".join(res)


class TemplateRecord:
    def __init__(self, namespace, record, config):
        self.symbol_prefix = f"{namespace.symbol_prefix[0]}_{record.symbol_prefix}"
        self.type_cname = record.ctype
        self.link_prefix = "struct"

        self.name = record.name
        self.namespace = record.name or namespace.name
        self.fqtn = f"{self.namespace}.{self.name}"

        md = markdown.Markdown(extensions=utils.MD_EXTENSIONS,
                               extension_configs=utils.MD_EXTENSIONS_CONF)

        if record.doc is not None:
            self.summary = utils.preprocess_docs(record.doc.content, namespace, summary=True, md=md)
            self.description = utils.preprocess_docs(record.doc.content, namespace, md=md)
            self.description_toc = md.toc_tokens is not None and md.toc_tokens.copy() or None
            filename = record.doc.filename
            line = record.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.stability = record.stability
        self.attributes = record.attributes
        self.available_since = record.available_since
        if record.deprecated:
            (version, msg) = record.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace, md=md),
            }
        else:
            self.deprecated_since = None

        self.introspectable = record.introspectable

        self.fields = []
        for field in record.fields:
            if not field.private:
                self.fields.append(TemplateField(namespace, field))

        self.ctors = []
        if len(record.constructors) != 0:
            for ctor in record.constructors:
                if not config.is_hidden(record.name, "constructor", ctor.name):
                    self.ctors.append(gen_index_func(ctor, namespace, md))

        self.methods = []
        if len(record.methods) != 0:
            for method in record.methods:
                if not config.is_hidden(record.name, "method", method.name):
                    self.methods.append(gen_index_func(method, namespace, md))

        self.type_funcs = []
        if len(record.functions) != 0:
            for func in record.functions:
                if not config.is_hidden(record.name, "function", func.name):
                    self.type_funcs.append(gen_index_func(func, namespace, md))

    @property
    def c_decl(self):
        res = [f"struct {self.type_cname} {{"]
        n_fields = len(self.fields)
        if n_fields > 0:
            for field in self.fields:
                res += [f"  {field.c_decl};"]
        else:
            res += ["  /* No available fields */"]
        res += ["}"]
        return utils.code_highlight("\n".join(res))


class TemplateUnion:
    def __init__(self, namespace, union, config):
        self.symbol_prefix = f"{namespace.symbol_prefix[0]}_{union.symbol_prefix}"
        self.type_cname = union.ctype
        self.link_prefix = "union"
        self.name = union.name
        self.namespace = union.namespace or namespace.name
        self.fqtn = f"{self.namespace}.{self.name}"

        md = markdown.Markdown(extensions=utils.MD_EXTENSIONS,
                               extension_configs=utils.MD_EXTENSIONS_CONF)

        if union.doc is not None:
            self.summary = utils.preprocess_docs(union.doc.content, namespace, summary=True, md=md)
            self.description = utils.preprocess_docs(union.doc.content, namespace, md=md)
            self.description_toc = md.toc_tokens is not None and md.toc_tokens.copy() or None
            filename = union.doc.filename
            line = union.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.stability = union.stability
        self.attributes = union.attributes
        self.available_since = union.available_since
        if union.deprecated:
            (version, msg) = union.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace, md=md),
            }
        else:
            self.deprecated_since = None

        self.introspectable = union.introspectable

        self.fields = []
        for field in union.fields:
            if not field.private:
                self.fields.append(TemplateField(namespace, field))

        self.ctors = []
        if len(union.constructors) != 0:
            for ctor in union.constructors:
                if not config.is_hidden(union.name, "constructor", ctor.name):
                    self.ctors.append(gen_index_func(ctor, namespace, md))

        self.methods = []
        if len(union.methods) != 0:
            for method in union.methods:
                if not config.is_hidden(union.name, "method", method.name):
                    self.methods.append(gen_index_func(method, namespace, md))

        self.type_funcs = []
        if len(union.functions) != 0:
            for func in union.functions:
                if not config.is_hidden(union.name, "function", func.name):
                    self.type_funcs.append(gen_index_func(func, namespace, md))

    @property
    def c_decl(self):
        res = [f"union {self.type_cname} {{"]
        n_fields = len(self.fields)
        if n_fields > 0:
            for field in self.fields:
                res += [f"  {field.c_decl};"]
        else:
            res += ["  /* No available fields */"]
        res += ["}"]
        return utils.code_highlight("\n".join(res))


class TemplateAlias:
    def __init__(self, namespace, alias):
        self.type_cname = alias.base_ctype
        self.target_ctype = alias.target.ctype
        self.link_prefix = "alias"

        self.namespace = alias.namespace or namespace.name
        self.name = alias.name
        self.fqtn = f"{self.namespace}.{self.name}"

        md = markdown.Markdown(extensions=utils.MD_EXTENSIONS,
                               extension_configs=utils.MD_EXTENSIONS_CONF)

        if alias.doc is not None:
            self.summary = utils.preprocess_docs(alias.doc.content, namespace, summary=True, md=md)
            self.description = utils.preprocess_docs(alias.doc.content, namespace, md=md)
            filename = alias.doc.filename
            line = alias.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.stability = alias.stability
        self.attributes = alias.attributes
        self.available_since = alias.available_since
        if alias.deprecated:
            (version, msg) = alias.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace),
            }
        else:
            self.deprecated_since = None

        self.introspectable = alias.introspectable

    @property
    def c_decl(self):
        return f"typedef {self.target_ctype} {self.type_cname}"


class TemplateMember:
    def __init__(self, namespace, enum, member):
        self.name = member.identifier
        self.girname = member.name
        self.nick = member.nick
        self.value = member.value
        self.available_since = member.available_since or enum.available_since
        if member.doc is not None:
            self.description = utils.preprocess_docs(member.doc.content, namespace)
            filename = member.doc.filename
            line = member.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")


class TemplateEnum:
    def __init__(self, namespace, enum, config):
        self.symbol_prefix = None
        self.type_cname = enum.ctype
        self.bitfield = False
        self.error = False
        self.domain = None

        self.namespace = namespace.name
        self.name = enum.name
        self.fqtn = f"{namespace.name}.{enum.name}"

        md = markdown.Markdown(extensions=utils.MD_EXTENSIONS,
                               extension_configs=utils.MD_EXTENSIONS_CONF)

        if enum.doc is not None:
            self.summary = utils.preprocess_docs(enum.doc.content, namespace, summary=True, md=md)
            self.description = utils.preprocess_docs(enum.doc.content, namespace, md=md)
            filename = enum.doc.filename
            line = enum.doc.line
            if filename.startswith('../'):
                filename = filename.replace('../', '')
            self.docs_location = (filename, line)
        else:
            self.description = Markup(f"<p>{MISSING_DESCRIPTION}</p>")

        self.stability = enum.stability
        self.attributes = enum.attributes
        self.available_since = enum.available_since
        if enum.deprecated:
            (version, msg) = enum.deprecated_since
            self.deprecated_since = {
                "version": version,
                "message": utils.preprocess_docs(msg, namespace, md=md),
            }
        else:
            self.deprecated_since = None

        self.introspectable = enum.introspectable

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
                self.members.append(TemplateMember(namespace, enum, member))

        if len(enum.functions) != 0:
            self.type_funcs = []
            for func in enum.functions:
                if not config.is_hidden(enum.name, "function", func.name):
                    self.type_funcs.append(gen_index_func(func, namespace, md))

    @property
    def c_decl(self):
        if self.error:
            return f"error-domain {self.fqtn}"
        elif self.bitfield:
            return f"flags {self.fqtn}"
        else:
            return f"enum {self.fqtn}"


class TemplateNamespace:
    def __init__(self, namespace):
        self.name = namespace.name
        self.version = namespace.version
        self.symbol_prefix = namespace.symbol_prefix[0]
        self.identifier_prefix = namespace.identifier_prefix[0]


def _gen_classes(config, theme_config, output_dir, jinja_env, repository, all_classes):
    namespace = repository.namespace

    class_tmpl = jinja_env.get_template(theme_config.class_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    property_tmpl = jinja_env.get_template(theme_config.property_template)
    signal_tmpl = jinja_env.get_template(theme_config.signal_template)
    class_method_tmpl = jinja_env.get_template(theme_config.class_method_template)
    ctor_tmpl = jinja_env.get_template(theme_config.ctor_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)
    vfunc_tmpl = jinja_env.get_template(theme_config.vfunc_template)

    template_classes = []

    for cls in all_classes:
        if config.is_hidden(cls.name):
            log.debug(f"Skipping hidden class {cls.name}")
            continue
        class_file = os.path.join(output_dir, f"class.{cls.name}.html")
        log.info(f"Creating class file for {namespace.name}.{cls.name}: {class_file}")

        tmpl = TemplateClass(namespace, cls, config)
        template_classes.append(tmpl)

        if cls.type_struct is not None:
            class_struct = namespace.find_record(cls.type_struct)
            class_methods = class_struct.methods
        else:
            class_methods = []

        sections = [
            {
                "title": "Constructors",
                "symbols": cls.constructors,
                "index": tmpl.ctors,
                "config": "constructor",
                "template_class": TemplateFunction,
                "template_renderer": ctor_tmpl,
                "section_class": "ctor",
                "section_fragment": "ctor",
                "template": "type_func",
            },
            {
                "title": "Functions",
                "symbols": cls.functions,
                "index": tmpl.type_funcs,
                "config": "function",
                "template_class": TemplateFunction,
                "template_renderer": type_func_tmpl,
                "section_class": "func",
                "section_fragment": "type_func",
                "template": "type_func",
            },
            {
                "title": "Instance methods",
                "symbols": cls.methods,
                "index": tmpl.methods,
                "config": "method",
                "template_class": TemplateMethod,
                "template_renderer": method_tmpl,
                "section_class": "method",
                "section_fragment": "method",
                "template": "method",
            },
            {
                "title": "Properties",
                "symbols": cls.properties.values(),
                "index": tmpl.properties,
                "config": "property",
                "template_class": TemplateProperty,
                "template_renderer": property_tmpl,
                "section_class": "property",
                "section_fragment": "property",
                "template": "property",
            },
            {
                "title": "Signals",
                "symbols": cls.signals.values(),
                "index": tmpl.signals,
                "config": "signal",
                "template_class": TemplateSignal,
                "template_renderer": signal_tmpl,
                "section_class": "signal",
                "section_fragment": "signal",
                "template": "signal",
            },
            {
                "title": "Class methods",
                "symbols": class_methods,
                "index": tmpl.class_methods,
                "config": "function",
                "template_class": TemplateClassMethod,
                "template_renderer": class_method_tmpl,
                "section_class": "method",
                "section_fragment": "class_method",
                "template": "class_method",
            },
            {
                "title": "Virtual methods",
                "symbols": cls.virtual_methods,
                "index": tmpl.virtual_methods,
                "config": "method",
                "template_class": TemplateMethod,
                "template_renderer": vfunc_tmpl,
                "section_class": "method",
                "section_fragment": "vfunc",
                "template": "vfunc",
            },
        ]

        if config.show_class_hierarchy:
            tmpl.hierarchy_svg = utils.render_dot(tmpl.dot, output_format="svg")

        with open(class_file, "w", encoding="utf-8") as out:
            content = class_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'class': tmpl,
                'sections': sections,
            })

            out.write(content)

        for section in sections:
            for sym in section['symbols']:
                if config.is_hidden(cls.name, section['config'], sym.name):
                    log.debug(f"Skipping hidden symbol {cls.name}.{sym.name}")
                    continue

                s = section['template_class'](namespace, cls, sym)
                sym_file = os.path.join(output_dir, f"{section['section_fragment']}.{cls.name}.{sym.name}.html")
                log.debug(f"Creating symbol file for {namespace.name}.{cls.name}.{sym.name}: {sym_file}")

                with open(sym_file, "w", encoding="utf-8") as out:
                    out.write(section['template_renderer'].render({
                        'CONFIG': config,
                        'namespace': namespace,
                        'class': tmpl,
                        'sections': sections,
                        section['template']: s,
                    }))

    return template_classes


def _gen_interfaces(config, theme_config, output_dir, jinja_env, repository, all_interfaces):
    namespace = repository.namespace

    iface_tmpl = jinja_env.get_template(theme_config.interface_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    property_tmpl = jinja_env.get_template(theme_config.property_template)
    signal_tmpl = jinja_env.get_template(theme_config.signal_template)
    class_method_tmpl = jinja_env.get_template(theme_config.class_method_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)
    vfunc_tmpl = jinja_env.get_template(theme_config.vfunc_template)

    template_interfaces = []

    for iface in all_interfaces:
        if config.is_hidden(iface.name):
            log.debug(f"Skipping hidden interface {iface.name}")
            continue
        iface_file = os.path.join(output_dir, f"iface.{iface.name}.html")
        log.info(f"Creating interface file for {namespace.name}.{iface.name}: {iface_file}")

        tmpl = TemplateInterface(namespace, iface, config)
        template_interfaces.append(tmpl)

        if iface.type_struct is not None:
            iface_struct = namespace.find_record(iface.type_struct)
            iface_methods = iface_struct.methods
        else:
            iface_methods = []

        sections = [
            {
                "title": "Functions",
                "symbols": iface.functions,
                "index": tmpl.type_funcs,
                "config": "function",
                "template_class": TemplateFunction,
                "template_renderer": type_func_tmpl,
                "section_class": "func",
                "section_fragment": "type_func",
                "template": "type_func",
            },
            {
                "title": "Instance methods",
                "symbols": iface.methods,
                "index": tmpl.methods,
                "config": "method",
                "template_class": TemplateMethod,
                "template_renderer": method_tmpl,
                "section_class": "method",
                "section_fragment": "method",
                "template": "method",
            },
            {
                "title": "Properties",
                "symbols": iface.properties.values(),
                "index": tmpl.properties,
                "config": "property",
                "template_class": TemplateProperty,
                "template_renderer": property_tmpl,
                "section_class": "property",
                "section_fragment": "property",
                "template": "property",
            },
            {
                "title": "Signals",
                "symbols": iface.signals.values(),
                "index": tmpl.signals,
                "config": "signal",
                "template_class": TemplateSignal,
                "template_renderer": signal_tmpl,
                "section_class": "signal",
                "section_fragment": "signal",
                "template": "signal",
            },
            {
                "title": "Interface methods",
                "symbols": iface_methods,
                "index": tmpl.class_methods,
                "config": "function",
                "template_class": TemplateClassMethod,
                "template_renderer": class_method_tmpl,
                "section_class": "method",
                "section_fragment": "class_method",
                "template": "class_method",
            },
            {
                "title": "Virtual methods",
                "symbols": iface.virtual_methods,
                "index": tmpl.virtual_methods,
                "config": "method",
                "template_class": TemplateMethod,
                "template_renderer": vfunc_tmpl,
                "section_class": "method",
                "section_fragment": "vfunc",
                "template": "vfunc",
            },
        ]

        with open(iface_file, "w", encoding="utf-8") as out:
            out.write(iface_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'interface': tmpl,
                'sections': sections,
            }))

        for section in sections:
            for sym in section['symbols']:
                if config.is_hidden(iface.name, section['config'], sym.name):
                    log.debug(f"Skipping hidden symbol {iface.name}.{sym.name}")
                    continue

                s = section['template_class'](namespace, iface, sym)
                sym_file = os.path.join(output_dir, f"{section['section_fragment']}.{iface.name}.{sym.name}.html")
                log.debug(f"Creating symbol file for {namespace.name}.{iface.name}.{sym.name}: {sym_file}")

                with open(sym_file, "w", encoding="utf-8") as out:
                    out.write(section['template_renderer'].render({
                        'CONFIG': config,
                        'namespace': namespace,
                        'class': tmpl,
                        'sections': sections,
                        section['template']: s,
                    }))

    return template_interfaces


def _gen_enums(config, theme_config, output_dir, jinja_env, repository, all_enums):
    namespace = repository.namespace

    enum_tmpl = jinja_env.get_template(theme_config.enum_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    template_enums = []

    for enum in all_enums:
        if config.is_hidden(enum.name):
            log.debug(f"Skipping hidden enum {enum.name}")
            continue
        enum_file = os.path.join(output_dir, f"enum.{enum.name}.html")
        log.info(f"Creating enum file for {namespace.name}.{enum.name}: {enum_file}")

        tmpl = TemplateEnum(namespace, enum, config)
        template_enums.append(tmpl)

        with open(enum_file, "w", encoding="utf-8") as out:
            out.write(enum_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'enum': tmpl,
            }))

        for type_func in enum.functions:
            if config.is_hidden(enum.name, "enum", type_func.name):
                log.debug(f"Skipping hidden symbol {enum.name}.{type_func.name}")
                continue

            f = TemplateFunction(namespace, enum, type_func)
            type_func_file = os.path.join(output_dir, f"type_func.{enum.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{enum.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w", encoding="utf-8") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': f,
                }))

    return template_enums


def _gen_bitfields(config, theme_config, output_dir, jinja_env, repository, all_enums):
    namespace = repository.namespace

    enum_tmpl = jinja_env.get_template(theme_config.flags_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    template_bitfields = []

    for enum in all_enums:
        if config.is_hidden(enum.name):
            log.debug(f"Skipping hidden bitfield {enum.name}")
            continue
        enum_file = os.path.join(output_dir, f"flags.{enum.name}.html")
        log.info(f"Creating enum file for {namespace.name}.{enum.name}: {enum_file}")

        tmpl = TemplateEnum(namespace, enum, config)
        template_bitfields.append(tmpl)

        with open(enum_file, "w", encoding="utf-8") as out:
            out.write(enum_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'enum': tmpl,
            }))

        for type_func in enum.functions:
            if config.is_hidden(enum.name, "enum", type_func.name):
                log.debug(f"Skipping hidden symbol {enum.name}.{type_func.name}")
                continue

            f = TemplateFunction(namespace, enum, type_func)
            type_func_file = os.path.join(output_dir, f"type_func.{enum.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{enum.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w", encoding="utf-8") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': f,
                }))

    return template_bitfields


def _gen_domains(config, theme_config, output_dir, jinja_env, repository, all_enums):
    namespace = repository.namespace

    enum_tmpl = jinja_env.get_template(theme_config.error_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    template_domains = []

    for enum in all_enums:
        if config.is_hidden(enum.name):
            log.debug(f"Skipping hidden domain {enum.name}")
            continue
        enum_file = os.path.join(output_dir, f"error.{enum.name}.html")
        log.info(f"Creating enum file for {namespace.name}.{enum.name}: {enum_file}")

        tmpl = TemplateEnum(namespace, enum, config)
        template_domains.append(tmpl)

        with open(enum_file, "w", encoding="utf-8") as out:
            out.write(enum_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'enum': tmpl,
            }))

        for type_func in enum.functions:
            if config.is_hidden(enum.name, "enum", type_func.name):
                log.debug(f"Skipping hidden symbol {enum.name}.{type_func.name}")
                continue

            f = TemplateFunction(namespace, enum, type_func)
            type_func_file = os.path.join(output_dir, f"type_func.{enum.name}.{type_func.name}.html")
            log.debug(f"Creating type func file for {namespace.name}.{enum.name}.{type_func.name}: {type_func_file}")

            with open(type_func_file, "w", encoding="utf-8") as out:
                out.write(type_func_tmpl.render({
                    'CONFIG': config,
                    'namespace': namespace,
                    'class': tmpl,
                    'type_func': f,
                }))

    return template_domains


def _gen_constants(config, theme_config, output_dir, jinja_env, repository, all_constants):
    namespace = repository.namespace

    const_tmpl = jinja_env.get_template(theme_config.constant_template)

    template_constants = []

    for const in all_constants:
        if config.is_hidden(const.name):
            log.debug(f"Skipping hidden constant {const.name}")
            continue
        const_file = os.path.join(output_dir, f"const.{const.name}.html")
        log.info(f"Creating constant file for {namespace.name}.{const.name}: {const_file}")

        tmpl = TemplateConstant(namespace, const)
        template_constants.append(tmpl)

        with open(const_file, "w", encoding="utf-8") as out:
            out.write(const_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'constant': tmpl,
            }))

    return template_constants


def _gen_aliases(config, theme_config, output_dir, jinja_env, repository, all_aliases):
    namespace = repository.namespace

    alias_tmpl = jinja_env.get_template(theme_config.alias_template)

    template_aliases = []

    for alias in all_aliases:
        if config.is_hidden(alias.name):
            log.debug(f"Skipping hidden alias {alias.name}")
            continue
        alias_file = os.path.join(output_dir, f"alias.{alias.name}.html")
        log.info(f"Creating alias file for {namespace.name}.{alias.name}: {alias_file}")

        tmpl = TemplateAlias(namespace, alias)
        template_aliases.append(tmpl)

        with open(alias_file, "w", encoding="utf-8") as out:
            content = alias_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'struct': tmpl,
            })

            out.write(content)

    return template_aliases


def _gen_records(config, theme_config, output_dir, jinja_env, repository, all_records):
    namespace = repository.namespace

    record_tmpl = jinja_env.get_template(theme_config.record_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    template_records = []

    for record in all_records:
        if config.is_hidden(record.name):
            log.debug(f"Skipping hidden record {record.name}")
            continue
        record_file = os.path.join(output_dir, f"struct.{record.name}.html")
        log.info(f"Creating record file for {namespace.name}.{record.name}: {record_file}")

        tmpl = TemplateRecord(namespace, record, config)
        template_records.append(tmpl)

        sections = [
            {
                "title": "Constructors",
                "symbols": record.constructors,
                "index": tmpl.ctors,
                "config": "constructor",
                "template_class": TemplateFunction,
                "template_renderer": type_func_tmpl,
                "section_class": "ctor",
                "section_fragment": "ctor",
                "template": "type_func",
            },
            {
                "title": "Functions",
                "symbols": record.functions,
                "index": tmpl.type_funcs,
                "config": "function",
                "template_class": TemplateFunction,
                "template_renderer": type_func_tmpl,
                "section_class": "func",
                "section_fragment": "type_func",
                "template": "type_func",
            },
            {
                "title": "Instance methods",
                "symbols": record.methods,
                "index": tmpl.methods,
                "config": "method",
                "template_class": TemplateMethod,
                "template_renderer": method_tmpl,
                "section_class": "method",
                "section_fragment": "method",
                "template": "method",
            },
        ]

        with open(record_file, "w", encoding="utf-8") as out:
            content = record_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'struct': tmpl,
                'sections': sections,
            })

            out.write(content)

        for section in sections:
            for sym in section['symbols']:
                if config.is_hidden(record.name, section['config'], sym.name):
                    log.debug(f"Skipping hidden symbol {record.name}.{sym.name}")
                    continue

                s = section['template_class'](namespace, record, sym)
                sym_file = os.path.join(output_dir, f"{section['section_fragment']}.{record.name}.{sym.name}.html")
                log.debug(f"Creating symbol file for {namespace.name}.{record.name}.{sym.name}: {sym_file}")

                with open(sym_file, "w", encoding="utf-8") as out:
                    out.write(section['template_renderer'].render({
                        'CONFIG': config,
                        'namespace': namespace,
                        'class': tmpl,
                        'sections': sections,
                        section['template']: s,
                    }))

    return template_records


def _gen_unions(config, theme_config, output_dir, jinja_env, repository, all_unions):
    namespace = repository.namespace

    union_tmpl = jinja_env.get_template(theme_config.union_template)
    method_tmpl = jinja_env.get_template(theme_config.method_template)
    type_func_tmpl = jinja_env.get_template(theme_config.type_func_template)

    template_unions = []

    for union in all_unions:
        if config.is_hidden(union.name):
            log.debug(f"Skipping hidden union {union.name}")
            continue
        union_file = os.path.join(output_dir, f"union.{union.name}.html")
        log.info(f"Creating union file for {namespace.name}.{union.name}: {union_file}")

        tmpl = TemplateUnion(namespace, union, config)
        template_unions.append(tmpl)

        sections = [
            {
                "title": "Constructors",
                "symbols": union.constructors,
                "index": tmpl.ctors,
                "config": "constructor",
                "template_class": TemplateFunction,
                "template_renderer": type_func_tmpl,
                "section_class": "ctor",
                "section_fragment": "ctor",
                "template": "type_func",
            },
            {
                "title": "Functions",
                "symbols": union.functions,
                "index": tmpl.type_funcs,
                "config": "function",
                "template_class": TemplateFunction,
                "template_renderer": type_func_tmpl,
                "section_class": "func",
                "section_fragment": "type_func",
                "template": "type_func",
            },
            {
                "title": "Instance methods",
                "symbols": union.methods,
                "index": tmpl.methods,
                "config": "method",
                "template_class": TemplateMethod,
                "template_renderer": method_tmpl,
                "section_class": "method",
                "section_fragment": "method",
                "template": "method",
            },
        ]

        with open(union_file, "w", encoding="utf-8") as out:
            content = union_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'struct': tmpl,
                'sections': sections,
            })

            out.write(content)

        for section in sections:
            for sym in section['symbols']:
                if config.is_hidden(union.name, section['config'], sym.name):
                    log.debug(f"Skipping hidden symbol {union.name}.{sym.name}")
                    continue

                s = section['template_class'](namespace, union, sym)
                sym_file = os.path.join(output_dir, f"{section['section_fragment']}.{union.name}.{sym.name}.html")
                log.debug(f"Creating symbol file for {namespace.name}.{union.name}.{sym.name}: {sym_file}")

                with open(sym_file, "w", encoding="utf-8") as out:
                    out.write(section['template_renderer'].render({
                        'CONFIG': config,
                        'namespace': namespace,
                        'class': tmpl,
                        'sections': sections,
                        section['template']: s,
                    }))

    return template_unions


def _gen_functions(config, theme_config, output_dir, jinja_env, repository, all_functions):
    namespace = repository.namespace

    func_tmpl = jinja_env.get_template(theme_config.func_template)

    template_functions = []

    for func in all_functions:
        if config.is_hidden(func.name):
            log.debug(f"Skipping hidden function {func.name}")
            continue
        func_file = os.path.join(output_dir, f"func.{func.name}.html")
        log.info(f"Creating function file for {namespace.name}.{func.name}: {func_file}")

        tmpl = TemplateFunction(namespace, None, func)
        template_functions.append(tmpl)

        with open(func_file, "w", encoding="utf-8") as out:
            content = func_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'func': tmpl,
            })

            out.write(content)

    return template_functions


def _gen_callbacks(config, theme_config, output_dir, jinja_env, repository, all_callbacks):
    namespace = repository.namespace

    func_tmpl = jinja_env.get_template(theme_config.func_template)

    template_callbacks = []

    for func in all_callbacks:
        if config.is_hidden(func.name):
            log.debug(f"Skipping hidden callback {func.name}")
            continue
        func_file = os.path.join(output_dir, f"callback.{func.name}.html")
        log.info(f"Creating callback file for {namespace.name}.{func.name}: {func_file}")

        tmpl = TemplateCallback(namespace, func)
        template_callbacks.append(tmpl)

        with open(func_file, "w", encoding="utf-8") as out:
            content = func_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'func': tmpl,
            })

            out.write(content)

    return template_callbacks


def _gen_function_macros(config, theme_config, output_dir, jinja_env, repository, all_functions):
    namespace = repository.namespace

    func_tmpl = jinja_env.get_template(theme_config.func_template)

    template_functions = []

    for func in all_functions:
        if config.is_hidden(func.name):
            log.debug(f"Skipping hidden macro {func.name}")
            continue
        func_file = os.path.join(output_dir, f"func.{func.name}.html")
        log.info(f"Creating function macro file for {namespace.name}.{func.name}: {func_file}")

        tmpl = TemplateFunction(namespace, None, func)
        template_functions.append(tmpl)

        with open(func_file, "w", encoding="utf-8") as out:
            content = func_tmpl.render({
                'CONFIG': config,
                'namespace': namespace,
                'func': tmpl,
            })

            out.write(content)

    return template_functions


def gen_content_files(config, theme_config, content_dirs, output_dir, jinja_env, namespace):
    content_files = []

    content_tmpl = jinja_env.get_template(theme_config.content_template)
    md = markdown.Markdown(extensions=utils.MD_EXTENSIONS, extension_configs=utils.MD_EXTENSIONS_CONF)

    for file_name in config.content_files:
        src_file = utils.find_extra_content_file(content_dirs, file_name)

        src_data = ""
        with open(src_file, encoding='utf-8') as infile:
            source = []
            for line in infile:
                source.append(line)
            src_data = "".join(source)

        dst_data = utils.preprocess_docs(src_data, namespace, md=md)
        title = "\n".join(md.Meta.get("title", ["Unknown document"]))

        origin = md.Meta.get("origin", file_name)

        content_file = file_name.replace(".md", ".html")
        dst_file = os.path.join(output_dir, content_file)

        content = {
            "abs_input_file": src_file,
            "abs_output_file": dst_file,
            "source_file": origin,
            "output_file": content_file,
            "meta": md.Meta,
            "title": title,
            "toc": md.toc_tokens,
            "data": dst_data,
        }

        log.info(f"Generating content file {file_name}: {dst_file}")
        with open(dst_file, "w", encoding='utf-8') as outfile:
            outfile.write(content_tmpl.render({
                "CONFIG": config,
                "namespace": namespace,
                "content": content,
            }))

        content_files.append({
            "title": title,
            "href": content_file,
        })

        md.reset()

    return content_files


def gen_content_images(config, content_dirs, output_dir):
    content_images = []

    for image_file in config.content_images:
        infile = utils.find_extra_content_file(content_dirs, image_file)
        outfile = os.path.join(output_dir, os.path.basename(image_file))
        log.debug(f"Adding extra content image: {infile} -> {outfile}")
        content_images += [(infile, outfile)]

    return content_images


def gen_types_hierarchy(config, theme_config, output_dir, jinja_env, repository):
    # All GObject sub-types
    objects_tree = repository.get_class_hierarchy(root="GObject.Object")

    # All GTypeInstance sub-types
    typed_tree = repository.get_class_hierarchy()

    if len(objects_tree) == 0 and len(typed_tree) == 0:
        return None

    res = ["<h1>Classes Hierarchy</h1>"]

    def dump_tree(node, out):
        for k in node:
            if '.' in k:
                ns, name = k.split('.', 2)
                data_ns = f'data-namespace="{ns}"'
                data_link = f'data-link="class.{name}.html"'
                href = 'href="javascript:void(0)"'
                css_class = 'class="external"'
                out.append(f'<li class="type"><a {data_ns} {data_link} {href} {css_class}><code>{k}</code></a>')
            else:
                out.append(f'<li class="type"><a href="class.{k}.html"><code>{k}</code></a>')
            if len(node[k]) != 0:
                out.append('<ul class="type">')
                dump_tree(node[k], out)
                out.append("</ul>")
            out.append("</li>")

    if len(objects_tree) != 0:
        res += ["<div class=\"docblock\">"]
        res += ["<ul class=\"type root\">"]
        res += [" <li class=\"type\"><a data-namespace=\"GObject\" data-link=\"class.Object.html\" href=\"javascript:void(0)\" class=\"external\"><code>GObject.Object</code></a></li><ul class=\"type\">"]  # noqa: E501
        dump_tree(objects_tree, res)
        res += [" </ul></li>"]
        res += ["</ul>"]
        res += ["</div>"]

    if len(typed_tree) != 0:
        res += ["<div class=\"docblock\">"]
        res += ["<ul class=\"type root\">"]
        res += [" <li class=\"type\"><a data-namespace=\"GObject\" data-link=\"struct.TypeInstance.html\" href=\"javascript:void(0)\" class=\"external\"><code>GObject.TypeInstance</code></li><ul class=\"type\">"]  # noqa: E501
        dump_tree(typed_tree, res)
        res += [" </ul></li>"]
        res += ["</ul>"]
        res += ["</div>"]

    content = {
        "output_file": "classes_hierarchy.html",
        "meta": {
            "keywords": "types, hierarchy, classes",
        },
        "title": "Classes Hierarchy",
        "data": Markup("\n".join(res)),
    }

    content_tmpl = jinja_env.get_template(theme_config.content_template)

    namespace = repository.namespace

    dst_file = os.path.join(output_dir, content["output_file"])
    log.info(f"Generating type hierarchy file: {dst_file}")
    with open(dst_file, "w", encoding="utf-8") as outfile:
        outfile.write(content_tmpl.render({
            "CONFIG": config,
            "namespace": namespace,
            "content": content,
        }))

    return {
        "title": content["title"],
        "href": content["output_file"],
    }


def gen_opensearch(config, repository, namespace, symbols, content_files):
    desc = etree.Element('OpenSearchDescription')
    desc.set("xmlns", "http://a9.com/-/spec/opensearch/1.1/")
    desc.set("xmlns:moz", "http://www.mozilla.org/2006/browser/search/")
    sub = etree.SubElement(desc, 'ShortName')
    sub.text = f"{namespace.name}"
    sub = etree.SubElement(desc, 'Description')
    sub.text = f"{namespace.name}-{namespace.version} Reference Manual"
    sub = etree.SubElement(desc, 'InputEncoding')
    sub.text = "UTF-8"
    if config.logo_url:
        sub = etree.SubElement(desc, 'Image')
        sub.text = config.logo_url
    sub = etree.SubElement(desc, 'Url', type="text/html")
    sub.set("type", "text/html")
    sub.set("template", f"{config.docs_url}/?q={{searchTerms}}")
    sub = etree.SubElement(desc, 'moz:SearchForm')
    sub.text = f"{config.docs_url}"

    return etree.ElementTree(desc)


def gen_devhelp(config, repository, namespace, symbols, content_files):
    book = etree.Element('book')
    book.set("xmlns", "http://www.devhelp.net/book")
    book.set("title", f"{namespace.name}-{namespace.version} Reference Manual")
    book.set("link", "index.html")
    book.set("author", f"{config.authors}")
    book.set("name", f"{namespace.name}")
    book.set("version", "2")
    book.set("language", "c")
    if config.docs_url:
        book.set("online", f"{config.docs_url}")

    chapters = etree.SubElement(book, 'chapters')

    for f in content_files:
        sub = etree.SubElement(chapters, 'sub')
        sub.set("name", f["title"])
        sub.set("link", f["href"])

    for section, types in symbols.items():
        if len(types) == 0:
            continue

        sub = etree.SubElement(chapters, "sub")
        sub.set("name", section.replace("_", " ").capitalize())
        sub.set("link", f"index.html#{section}")

        for t in types:
            sub_section = etree.SubElement(sub, "sub")
            sub_section.set("name", t.name)
            sub_section.set("link", f"{FRAGMENT[section]}.{t.name}.html")

    functions = etree.SubElement(book, "functions")
    for section, types in symbols.items():
        if len(types) == 0:
            continue

        for t in types:
            if section in ["functions", "function_macros"]:
                keyword = etree.SubElement(functions, "keyword")
                if section == "functions":
                    keyword.set("type", "function")
                else:
                    keyword.set("type", "macro")
                keyword.set("name", t.identifier)
                keyword.set("link", f"func.{t.name}.html")
                if t.available_since is not None:
                    keyword.set("since", t.available_since)
                if t.deprecated_since is not None and t.deprecated_since["version"] is not None:
                    keyword.set("deprecated", t.deprecated_since["version"])
                continue

            if section == "constants":
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "constant")
                keyword.set("name", t.identifier)
                keyword.set("link", f"const.{t.name}.html")
                if t.available_since is not None:
                    keyword.set("since", t.available_since)
                if t.deprecated_since is not None and t.deprecated_since["version"] is not None:
                    keyword.set("deprecated", t.deprecated_since["version"])
                continue

            if section in ["aliases", "bitfields", "classes", "domains", "enums", "interfaces", "structs", "unions"]:
                # Skip anonymous types; e.g. GValue's anonymous union
                if t.type_cname is None:
                    continue
                keyword = etree.SubElement(functions, "keyword")
                if section == "aliases":
                    keyword.set("type", "typedef")
                elif section in ["bitfields", "domains", "enums"]:
                    keyword.set("type", "enum")
                elif section == "unions":
                    keyword.set("type", "union")
                else:
                    keyword.set("type", "struct")
                keyword.set("name", t.type_cname)
                keyword.set("link", f"{FRAGMENT[section]}.{t.name}.html")
                if t.available_since is not None:
                    keyword.set("since", t.available_since)
                if t.deprecated_since is not None and t.deprecated_since["version"] is not None:
                    keyword.set("deprecated", t.deprecated_since["version"])

            for m in getattr(t, "members", []):
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "constant")
                keyword.set("name", m.name)
                keyword.set("link", f"{FRAGMENT[section]}.{t.name}.html")

            for f in getattr(t, "fields", []):
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "member")
                keyword.set("name", f"{t.type_cname}.{f.name}")
                keyword.set("link", f"{FRAGMENT[section]}.{t.name}.html")

            class_struct = getattr(t, "class_struct", None)
            if class_struct is not None:
                for f in getattr(class_struct, "fields", []):
                    keyword = etree.SubElement(functions, "keyword")
                    keyword.set("type", "member")
                    keyword.set("name", f"{t.class_name}.{f.name}")
                    if section == "class":
                        keyword.set("link", f"class.{t.name}.html#class-struct")
                    elif section == "interface":
                        keyword.set("link", f"iface.{t.name}.html#interface-struct")
                    else:
                        keyword.set("link", f"{FRAGMENT[section]}.{t.name}.html")

            for m in getattr(t, "methods", []):
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "function")
                keyword.set("name", m['identifier'])
                keyword.set("link", f"method.{t.name}.{m['name']}.html")
                if m["available_since"] is not None:
                    keyword.set("since", m["available_since"])
                if m["deprecated_since"] is not None:
                    keyword.set("deprecated", m["deprecated_since"])

            for c in getattr(t, "ctors", []):
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "function")
                keyword.set("name", c['identifier'])
                keyword.set("link", f"ctor.{t.name}.{c['name']}.html")
                if c["available_since"] is not None:
                    keyword.set("since", c["available_since"])
                if c["deprecated_since"] is not None:
                    keyword.set("deprecated", c["deprecated_since"])

            for f in getattr(t, "type_funcs", []):
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "function")
                keyword.set("name", f['identifier'])
                keyword.set("link", f"type_func.{t.name}.{f['name']}.html")
                if f["available_since"] is not None:
                    keyword.set("since", f["available_since"])
                if f["deprecated_since"] is not None:
                    keyword.set("deprecated", f["deprecated_since"])

            for m in getattr(t, "class_methods", []):
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "function")
                keyword.set("name", m['identifier'])
                keyword.set("link", f"class_method.{t.name}.{m['name']}.html")
                if m["available_since"] is not None:
                    keyword.set("since", m["available_since"])
                if m["deprecated_since"] is not None:
                    keyword.set("deprecated", m["deprecated_since"])

            for p in getattr(t, "properties", []):
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "property")
                keyword.set("name", f"The {t.type_cname}:{p['name']} property")
                keyword.set("link", f"property.{t.name}.{p['name']}.html")
                if p["available_since"] is not None:
                    keyword.set("since", p["available_since"])
                if p["deprecated_since"] is not None:
                    keyword.set("deprecated", p["deprecated_since"])

            for s in getattr(t, "signals", []):
                keyword = etree.SubElement(functions, "keyword")
                keyword.set("type", "signal")
                keyword.set("name", f"The {t.type_cname}::{s['name']} signal")
                keyword.set("link", f"signal.{t.name}.{s['name']}.html")
                if s["available_since"] is not None:
                    keyword.set("since", s["available_since"])
                if s["deprecated_since"] is not None:
                    keyword.set("deprecated", s["deprecated_since"])

    return etree.ElementTree(book)


def gen_reference(config, options, repository, templates_dir, theme_config, content_dirs, output_dir):
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
        "function_macros": sorted(namespace.get_effective_function_macros(), key=lambda func: func.name.lower()),
        "interfaces": sorted(namespace.get_interfaces(), key=lambda interface: interface.name.lower()),
        "structs": sorted(namespace.get_effective_records(), key=lambda record: record.name.lower()),
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
        "function_macros": _gen_function_macros,
        "interfaces": _gen_interfaces,
        "structs": _gen_records,
        "unions": _gen_unions,
    }

    if options.no_namespace_dir:
        ns_dir = output_dir
    else:
        ns_dir = os.path.join(output_dir, f"{namespace.name}-{namespace.version}")

    log.debug(f"Creating output path for the namespace: {ns_dir}")
    os.makedirs(ns_dir, exist_ok=True)

    content_files = gen_content_files(config, theme_config, content_dirs, ns_dir, jinja_env, namespace)
    content_images = gen_content_images(config, content_dirs, ns_dir)
    types_hierarchy = gen_types_hierarchy(config, theme_config, ns_dir, jinja_env, repository)
    if types_hierarchy:
        content_files.append(types_hierarchy)

    if options.sections == [] or options.sections == ["all"]:
        gen_indices = list(all_indices.keys())
    elif options.sections == ["none"]:
        gen_indices = []
    else:
        gen_indices = options.sections

    log.info(f"Generating references for: {gen_indices}")

    template_symbols = {}

    # Each section is isolated, so we run it into a thread pool
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures_to_section = {}
        for section in gen_indices:
            s = symbols.get(section, [])
            if s is None:
                log.debug(f"No symbols for section {section}")
                continue

            generator = all_indices.get(section, None)
            if generator is None:
                log.debug(f"No generator for section {section}")
                continue

            f = executor.submit(generator, config, theme_config, ns_dir, jinja_env, repository, s)
            futures_to_section[f] = section

        for future in concurrent.futures.as_completed(futures_to_section):
            section = futures_to_section[future]
            try:
                res = future.result()
            except Exception as e:
                if log.log_fatal_warnings:
                    import traceback
                    traceback.print_exc()
                log.warning(f"Section {section} raised {e}")
            else:
                template_symbols[section] = res

    # The concurrent processing introduces non-determinism. Ensure iteration order is reproducible
    # by sorting by key. This has virtually no overhead since the values are not copied.
    template_symbols = dict(sorted(template_symbols.items()))

    ns_tmpl = jinja_env.get_template(theme_config.namespace_template)
    ns_file = os.path.join(ns_dir, "index.html")
    log.info(f"Creating namespace index file for {namespace.name}-{namespace.version}: {ns_file}")
    with open(ns_file, "w", encoding="utf-8") as out:
        out.write(ns_tmpl.render({
            "CONFIG": config,
            "repository": repository,
            "namespace": namespace,
            "symbols": template_symbols,
            "content_files": content_files,
        }))

    if config.devhelp:
        # Devhelp expects the book file to have the same basename as the directory it is in.
        devhelp_file = os.path.join(ns_dir, f"{os.path.basename(ns_dir)}.devhelp2")
        log.info(f"Creating DevHelp file for {namespace.name}-{namespace.version}: {devhelp_file}")
        res = gen_devhelp(config, repository, namespace, template_symbols, content_files)
        res.write(devhelp_file, encoding="UTF-8")

    if config.search_index:
        if config.docs_url:
            opensearch_file = os.path.join(ns_dir, "opensearch.xml")
            log.info(f"Creating OpenSearch file for {namespace.name}-{namespace.version}: {opensearch_file}")
            res = gen_opensearch(config, repository, namespace, template_symbols, content_files)
            res.write(opensearch_file, encoding="UTF-8")
        gdgenindices.gen_indices(config, repository, content_dirs, ns_dir)

    copy_files = []
    if theme_config.css is not None:
        style_src = os.path.join(theme_dir, theme_config.css)
        style_dst = os.path.join(ns_dir, theme_config.css)
        copy_files.append((style_src, style_dst))

    for extra_file in theme_config.extra_files:
        src = os.path.join(theme_dir, extra_file)
        dst = os.path.join(ns_dir, extra_file)
        copy_files.append((src, dst))

    if config.urlmap_file is not None:
        src = utils.find_extra_content_file(content_dirs, config.urlmap_file)
        dst = os.path.join(ns_dir, os.path.basename(config.urlmap_file))
        copy_files.append((src, dst))

    copy_files.extend(content_images)

    def copy_worker(src, dst):
        log.info(f"Copying file {src}: {dst}")
        dst_dir = os.path.dirname(dst)
        os.makedirs(dst_dir, exist_ok=True)
        shutil.copy(src, dst)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        for (src, dst) in copy_files:
            executor.submit(copy_worker, src, dst)


def add_args(parser):
    parser.add_argument("--add-include-path", action="append", dest="include_paths", default=[],
                        help="include paths for other GIR files")
    parser.add_argument("-C", "--config", metavar="FILE", help="the configuration file")
    parser.add_argument("--dry-run", action="store_true", help="parses the GIR file without generating files")
    parser.add_argument("--templates-dir", default=None, help="the base directory with the theme templates")
    parser.add_argument("--content-dir", action="append", dest="content_dirs", default=[],
                        help="the base directories with the extra content")
    parser.add_argument("--theme-name", default="basic", help="the theme to use")
    parser.add_argument("--output-dir", default=None, help="the output directory for the index files")
    parser.add_argument("--no-namespace-dir", action="store_true",
                        help="do not create a namespace directory under the output directory")
    parser.add_argument("--section", action="append", dest="sections", default=[], help="the sections to generate, or 'all'")
    parser.add_argument("infile", metavar="GIRFILE", type=argparse.FileType('r', encoding='UTF-8'),
                        default=sys.stdin, help="the GIR file to parse")


def run(options):
    log.info(f"Loading config file: {options.config}")

    conf = config.GIDocConfig(options.config)

    output_dir = options.output_dir or os.getcwd()

    content_dirs = options.content_dirs
    if content_dirs == []:
        content_dirs = [os.getcwd()]

    if options.templates_dir is not None:
        templates_dir = options.templates_dir
    else:
        templates_dir = conf.get_templates_dir()
        if templates_dir is None:
            templates_dir = os.path.join(os.path.dirname(__file__), 'templates')

    theme_name = conf.get_theme_name(default=options.theme_name)
    theme_conf = config.GITemplateConfig(templates_dir, theme_name)

    log.debug(f"Templates directory: {templates_dir}")
    log.info(f"Theme name: {theme_conf.name}")
    log.info(f"Output directory: {output_dir}")

    paths = []
    paths.extend(options.include_paths)
    paths.extend(utils.default_search_paths())
    log.debug(f"Search paths: {paths}")

    log.info("Parsing GIR file")
    parser = gir.GirParser(search_paths=paths)
    parser.parse(options.infile)

    if not options.dry_run:
        log.checkpoint()
        gen_reference(conf, options, parser.get_repository(), templates_dir, theme_conf, content_dirs, output_dir)

    return 0
