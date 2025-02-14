# SPDX-FileCopyrightText: 2020 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import os
import typing as T
import xml.etree.ElementTree as ET

from .. import log
from . import ast

GI_NAMESPACES = {
    'core': "http://www.gtk.org/introspection/core/1.0",
    'c': "http://www.gtk.org/introspection/c/1.0",
    'glib': "http://www.gtk.org/introspection/glib/1.0",
}

FUNDAMENTAL_INTEGRAL_TYPES = [
    'gint8', 'guint8', 'int8_t', 'uint8_t',
    'gint16', 'guint16', 'int16_t', 'uint16_t',
    'gint32', 'guint32', 'int32_t', 'uint32_t',
    'gint64', 'guint64', 'int64_t', 'uint64_t',
    'gint', 'int',
    'guint', 'unsigned', 'unsigned int',
    'gfloat', 'float',
    'gdouble', 'double', 'long double',
    'gchar', 'guchar', 'char', 'unsigned char',
    'gshort', 'gushort', 'short', 'unsigned short',
    'glong', 'gulong', 'long', 'unsigned long',
    'gunichar',
    'gsize', 'gssize', 'size_t',
    'gboolean', 'bool',
    'va_list',
]

FUNDAMENTAL_TYPES = FUNDAMENTAL_INTEGRAL_TYPES + [
    'gpointer', 'gconstpointer',
    'gchar*', 'char*', 'guchar*',
    'utf8', 'filename',
]

GLIB_ALIASES = {
    'gchar': 'char',
    'gdouble': 'double',
    'gfloat': 'float',
    'gint': 'int',
    'glong': 'long',
    'gshort': 'short',
}

FUNDAMENTAL_CTYPES = {
    'utf8': 'char*',
    'filename': 'char*',
    'GObject.Object': 'GObject*',
    'GObject.InitiallyUnowned': 'GInitiallyUnowned*',
    'GObject.ParamSpec': 'GObject.ParamSpec*',
}


def _corens(tag: str) -> str:
    return f"{{{GI_NAMESPACES['core']}}}{tag}"


def _glibns(tag: str) -> str:
    return f"{{{GI_NAMESPACES['glib']}}}{tag}"


def _cns(tag: str) -> str:
    return f"{{{GI_NAMESPACES['c']}}}{tag}"


class GirParser:
    def __init__(self, search_paths=[], error=True):
        self._search_paths = search_paths
        self._repository = None
        self._dependencies = {}
        self._seen_types = {}
        self._current_namespace = []
        self._error = error

    def append_search_path(self, path: str) -> None:
        """Append a path to the list of search paths"""
        self._search_paths.append(path)

    def prepend_search_paths(self, path: str) -> None:
        """Prepend a path to the list of search paths"""
        self._search_paths = [path] + self._search_paths

    def parse(self, girfile: T.Union[T.TextIO, str]) -> None:
        """Parse @girfile"""
        log.debug(f"Loading GIR for {girfile}")
        tree = ET.parse(girfile)
        repository = self._parse_tree(tree.getroot())
        if repository is None:
            if self._error:
                log.error(f"Could not parse GIR {girfile}")
            else:
                raise RuntimeError(f"Invalid GIR file {girfile}")
        else:
            if isinstance(girfile, str):
                repository.girfile = girfile
            else:
                repository.girfile = girfile.name
            self._repository = repository
            self._repository.resolve_empty_ctypes(self._seen_types)
            self._repository.resolve_class_ctype()
            self._repository.resolve_class_implements()
            self._repository.resolve_class_ancestors()
            self._repository.resolve_class_descendants()
            self._repository.resolve_interface_requires()
            self._repository.resolve_interface_implementations()
            self._repository.resolve_moved_to()
            self._repository.resolve_symbols()

    def get_repository(self, name: T.Optional[str] = None) -> T.Optional[ast.Repository]:
        if name is None:
            return self._repository
        else:
            return self._dependencies[name]

    def _push_namespace(self, ns: ast.Namespace) -> None:
        assert ns not in self._current_namespace
        self._current_namespace.append(ns)

    def _pop_namespace(self) -> None:
        self._current_namespace.pop()

    def _get_namespace(self) -> T.Optional[ast.Namespace]:
        if len(self._current_namespace) == 0:
            return None
        return self._current_namespace[len(self._current_namespace) - 1]

    def _lookup_type(self, name: str, ctype: T.Optional[str] = None) -> ast.Type:
        """Look up a type, and if not found, register it"""
        is_fundamental = False
        if name in FUNDAMENTAL_TYPES:
            if name in GLIB_ALIASES:
                fqtn = GLIB_ALIASES[name]
            else:
                fqtn = name
            is_fundamental = True
        elif name == 'GType':
            # This is messy, because GType is part of GObject, but GLib ends up
            # registering it first
            fqtn = 'GObject.Type'
            is_fundamental = True
        elif '.' in name:
            fqtn = name
        else:
            ns = self._get_namespace()
            if ns is not None:
                fqtn = f"{ns.name}.{name}"
            else:
                log.debug(f"Unqualified type name {name} found")
                fqtn = name
        if ctype is None and fqtn in FUNDAMENTAL_TYPES:
            for t in FUNDAMENTAL_TYPES:
                if t == fqtn:
                    ctype = t
                    break
        if ctype is None and fqtn in FUNDAMENTAL_CTYPES:
            ctype = FUNDAMENTAL_CTYPES[fqtn]
        found_types = self._seen_types.get(fqtn)
        if found_types is not None:
            if ctype is not None:
                for t in found_types:
                    if t.resolved and t.ctype == ctype:
                        log.debug(f"Found seen type: {t} (with ctype)")
                        return t
                t = ast.Type(name=fqtn, ctype=ctype, is_fundamental=is_fundamental)
                found_types.append(t)
                log.debug(f"Seen new type: {t} (with ctype)")
                return t
            log.debug(f"Found seen type: {found_types[0]}")
            return found_types[0]
        # First time we saw this type
        res = ast.Type(name=fqtn, ctype=ctype, is_fundamental=is_fundamental)
        self._seen_types[fqtn] = [res]
        log.debug(f"Seen new type: {res}")
        return res

    def _parse_dependency(self, include: ast.Include) -> None:
        if self._dependencies.get(include.name, None) is not None:
            log.debug(f"Dependency {include} already parsed")
            return
        found = False
        for base_path in self._search_paths:
            girfile = os.path.join(base_path, f"{include}.gir")
            if os.path.exists(girfile) and os.path.isfile(girfile):
                log.debug(f"Loading GIR for dependency {include} at {girfile}")
                tree = ET.parse(girfile)
                repository = self._parse_tree(tree.getroot())
                if repository is not None:
                    repository.girfile = girfile
                    repository.resolve_moved_to()
                    repository.resolve_symbols()
                    ns = repository.namespace
                    self._dependencies[ns.name] = repository
                    found = True
                    break
        if not found:
            if self._error:
                log.error(f"Could not find GIR dependency in the search paths: {include}")
            else:
                raise RuntimeError(f"No {include} found in search paths {self._search_paths}")

    def _parse_tree(self, root: ET.Element) -> ast.Repository:
        assert root.tag == _corens('repository')

        includes: T.List[ast.Include] = []
        c_includes: T.List[str] = []
        packages: T.List[str] = []

        for node in root:
            if node.tag == _corens('include'):
                includes.append(self._parse_include(node))
            elif node.tag == _cns('include'):
                c_includes.append(self._parse_c_include(node))
            elif node.tag == _corens('package'):
                packages.append(self._parse_package(node))

        ns = root.find(_corens('namespace'))
        assert ns is not None

        identifier_prefixes = ns.attrib.get(_cns('identifier-prefixes'))
        if identifier_prefixes is not None:
            identifier_prefixes = identifier_prefixes.split(',')
        symbol_prefixes = ns.attrib.get(_cns('symbol-prefixes'))
        if symbol_prefixes is not None:
            symbol_prefixes = symbol_prefixes.split(',')

        namespace = ast.Namespace(ns.attrib['name'], ns.attrib['version'], identifier_prefixes, symbol_prefixes)
        shared_libs = ns.attrib.get('shared-library')
        if shared_libs:
            namespace.add_shared_libraries(shared_libs.split(','))

        repository = ast.Repository()
        repository.c_includes = c_includes
        repository.packages = packages

        for include in includes:
            log.debug(f"Parsing dependency {include}")
            self._parse_dependency(include)

        repository.includes = self._dependencies

        repository.add_namespace(namespace)

        parse_sections: T.Mapping[str, T.Callable[[ET.Element, ast.Repository, ast.Namespace], T.Any]] = {
            _corens('alias'): self._parse_alias,
            _corens('bitfield'): self._parse_bitfield,
            _glibns('boxed'): self._parse_boxed,
            _corens('callback'): self._parse_callback,
            _corens('class'): self._parse_class,
            _corens('constant'): self._parse_constant,
            _corens('enumeration'): self._parse_enumeration,
            _corens('function-inline'): self._parse_function_inline,
            _corens('function-macro'): self._parse_function_macro,
            _corens('function'): self._parse_function,
            _corens('interface'): self._parse_interface,
            _corens('record'): self._parse_record,
            _corens('union'): self._parse_union,
        }

        self._push_namespace(namespace)

        for node in ns:
            parser_method = parse_sections.get(node.tag, None)
            if parser_method is not None:
                parser_method(node, repository, namespace)

        self._pop_namespace()

        return repository

    def _parse_include(self, node: ET.Element) -> ast.Include:
        return ast.Include(node.attrib['name'], node.attrib['version'])

    def _parse_c_include(self, node: ET.Element) -> str:
        return node.attrib['name']

    def _parse_package(self, node: ET.Element) -> str:
        return node.attrib['name']

    def _maybe_parse_doc(self, node: ET.Element) -> T.Optional[ast.Doc]:
        child = node.find('core:doc', GI_NAMESPACES)
        if child is None:
            return None

        content = child.text or ""

        return ast.Doc(content=content, filename=child.attrib['filename'], line=int(child.attrib['line']))

    def _maybe_parse_source_position(self, node: ET.Element) -> T.Optional[ast.SourcePosition]:
        child = node.find('core:source-position', GI_NAMESPACES)
        if child is None:
            return None

        return ast.SourcePosition(filename=child.attrib['filename'], line=int(child.attrib['line']))

    def _maybe_parse_deprecated_doc(self, node: ET.Element) -> T.Optional[str]:
        child = node.find('core:doc-deprecated', GI_NAMESPACES)
        if child is None:
            return None

        return "".join(child.itertext())

    def _maybe_parse_attributes(self, node: ET.Element) -> T.Optional[T.Mapping[str, str]]:
        children = node.findall('core:attribute', GI_NAMESPACES)
        if children is None:
            return None

        attrs = {}
        for child in children:
            name = child.attrib.get('name')
            value = child.attrib.get('value')
            if name is not None:
                attrs[name] = value
        return attrs

    def _maybe_parse_docs(self, node: ET.Element, element: ast.GIRElement) -> None:
        doc = self._maybe_parse_doc(node)
        if doc is not None:
            element.set_doc(doc)
        source_pos = self._maybe_parse_source_position(node)
        if source_pos is not None:
            element.set_source_position(source_pos)
        attrs = self._maybe_parse_attributes(node)
        if attrs is not None:
            element.set_attributes(attrs)
        stability = node.attrib.get('stability')
        if stability is not None:
            element.set_stability(stability)
        deprecated = node.attrib.get('deprecated')
        if deprecated is not None:
            deprecated_since = node.attrib.get('deprecated-version')
            deprecated_doc = self._maybe_parse_deprecated_doc(node)
            element.set_deprecated(deprecated_doc, deprecated_since)

    def _parse_array(self, node: ET.Element) -> ast.Type:
        child = node.find('core:array', GI_NAMESPACES)

        array_name = child.attrib.get('name')
        array_type = child.attrib.get(_cns('type'))
        attr_zero_terminated = child.attrib.get('zero-terminated')
        attr_fixed_size = child.attrib.get('fixed-size')
        attr_length = child.attrib.get('length')

        target: T.Optional[ast.Type] = None
        child_type = child.find('core:type', GI_NAMESPACES)
        if child_type is not None:
            ttype = child_type.attrib.get(_cns('type'))
            tname = child_type.attrib.get('name')
            if tname is None and ttype is not None:
                log.debug(f"Unlabeled array element type {ttype}")
                target = ast.Type(name=ttype.replace('*', ''), ctype=ttype)
            if tname == 'none' and ttype == 'void':
                target = ast.VoidType()
            elif ttype == 'gpointer' and tname in FUNDAMENTAL_INTEGRAL_TYPES:
                # API returning a pointer with an overridden fundamental type,
                # like in-out/out signal arguments
                target = self._lookup_type(name=tname, ctype=f"{tname}*")
            elif ttype == 'gpointer' and tname != 'gpointer':
                # API returning gpointer to avoid casting
                target = self._lookup_type(name=tname)
            elif tname:
                target = self._lookup_type(name=tname, ctype=ttype)
            else:
                target = ast.VoidType()
        else:
            target = ast.VoidType()
        # This sort of complete brain damage is par for the course in g-i, sadly; I really
        # need to go into it with a sledgehammer and make the output complete, instead of
        # relying on assumptions made in 2010.
        zero_terminated = False
        fixed_size = -1
        length = -1
        if attr_zero_terminated is not None:
            zero_terminated = bool(attr_zero_terminated == '1')
        else:
            zero_terminated = bool(array_name is None and attr_fixed_size is None and attr_length is None)
        if attr_fixed_size is not None:
            fixed_size = int(attr_fixed_size)
        if attr_length is not None:
            length = int(attr_length)

        return ast.ArrayType(name=array_name, zero_terminated=zero_terminated,
                             fixed_size=fixed_size, length=length,
                             ctype=array_type, value_type=target)

    def _parse_ctype(self, node: ET.Element) -> ast.Type:
        ctype: T.Optional[ast.Type] = None

        child = node.find('core:array', GI_NAMESPACES)
        if child is not None:
            return self._parse_array(node)

        child = node.find('core:type', GI_NAMESPACES)
        if child is not None:
            ttype = child.attrib.get(_cns('type'))
            tname = child.attrib.get('name')
            if tname is None and ttype is None:
                log.debug(f"Found empty type annotation for node {node.tag}")
                ctype = ast.VoidType()
            elif tname is None and ttype is not None:
                log.debug(f"Unnamed type {ttype}")
                ctype = ast.Type(name=ttype.replace('*', ''), ctype=ttype)
            elif tname == 'none' and ttype == 'void':
                ctype = None
            elif tname in ['GLib.List', 'GLib.SList']:
                child_type = child.find('core:type', GI_NAMESPACES)
                if child_type is not None:
                    etname = child_type.attrib.get('name', 'gpointer')
                    etype = self._lookup_type(name=etname)
                    ctype = ast.ListType(name=tname, ctype=ttype, value_type=etype)
                else:
                    ctype = self._lookup_type(name=tname, ctype=ttype)
            elif tname in ['GList.HashTable']:
                child_types = child.findall('core:type', GI_NAMESPACES)
                if child_types is not None and len(child_types) == 2:
                    ktname = child_types[0].attrib.get('name', 'gpointer')
                    vtname = child_types[1].attrib.get('name', 'gpointer')
                    ctype = ast.MapType(name=tname, ctype=ttype,
                                        key_type=ast.Type(ktname),
                                        value_type=ast.Type(vtname))
                else:
                    ctype = self._lookup_type(name=tname, ctype=ttype)
            elif ttype == 'gpointer' and tname in FUNDAMENTAL_INTEGRAL_TYPES:
                # API returning a pointer with an overridden fundamental type,
                # like in-out/out signal arguments
                ctype = self._lookup_type(name=tname, ctype=f"{tname}*")
            elif ttype == 'gpointer' and tname != 'gpointer':
                # API returning gpointer to avoid casting
                ctype = self._lookup_type(name=tname)
            else:
                ctype = self._lookup_type(name=tname, ctype=ttype)
        else:
            child = node.find('core:varargs', GI_NAMESPACES)
            if child is not None:
                ctype = ast.VarArgs()

        if ctype is None:
            ctype = ast.VoidType()

        return ctype

    def _parse_alias(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        child = node.find('core:type', GI_NAMESPACES)
        assert child is not None

        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))

        alias_type = ast.Type(name=child.attrib['name'], ctype=child.attrib.get(_cns('type')))

        res = ast.Alias(name=name, namespace=ns.name, ctype=ctype, target=alias_type)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)

        ns.add_alias(res)

    def _parse_callback_field(self, node: ET.Element) -> ast.Callback:
        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))
        throws = node.attrib.get('throws', '0') == '1'

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.Callback(name=name, namespace=None, ctype=ctype, throws=throws)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        res.set_parameters(params)
        res.set_return_value(return_value)
        self._maybe_parse_docs(node, res)
        return res

    def _parse_callback(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))
        throws = node.attrib.get('throws', '0') == '1'

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.Callback(name=name, namespace=ns.name, ctype=ctype, throws=throws)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        res.set_parameters(params)
        res.set_return_value(return_value)
        self._maybe_parse_docs(node, res)
        ns.add_callback(res)

    def _parse_constant(self, node: ET.Element, repo: ast.Repository, ns: T.Optional[ast.Namespace]) -> None:
        child = node.find('core:type', GI_NAMESPACES)
        assert child is not None

        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))
        value = node.attrib.get('value')

        const_type = ast.Type(name=child.attrib['name'], ctype=child.attrib.get(_cns('type')))

        res = ast.Constant(name=name, namespace=ns.name, ctype=ctype, value=value, target=const_type)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        ns.add_constant(res)

    def _parse_return_value(self, node: ET.Element) -> ast.ReturnValue:
        transfer = node.attrib.get('transfer-ownership', 'none')
        nullable = node.attrib.get('nullable', '0') == '1'
        closure = int(node.attrib.get('closure', -1))
        destroy = int(node.attrib.get('destroy', -1))
        scope = node.attrib.get('scope')

        ctype = self._parse_ctype(node)

        res = ast.ReturnValue(transfer=transfer, target=ctype, nullable=nullable, closure=closure,
                              destroy=destroy, scope=scope)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        return res

    def _parse_parameter(self, node: ET.Element, is_instance_param: bool = False) -> ast.Parameter:
        name = node.attrib.get('name')
        direction = node.attrib.get('direction', 'in')
        transfer = node.attrib.get('transfer-ownership', 'none')
        nullable = node.attrib.get('nullable', '0') == '1'
        optional = node.attrib.get('optional', '0') == '1'
        caller_allocates = node.attrib.get('caller-allocates', '1') == '1'
        closure = int(node.attrib.get('closure', -1))
        destroy = int(node.attrib.get('destroy', -1))
        scope = node.attrib.get('scope')

        ctype = self._parse_ctype(node)

        res = ast.Parameter(name=name, direction=direction, transfer=transfer, target=ctype,
                            optional=optional, nullable=nullable, caller_allocates=caller_allocates,
                            closure=closure, destroy=destroy, scope=scope)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        return res

    def _parse_type_function(self, node: ET.Element, ns: T.Optional[ast.Namespace] = None, inline: bool = False) -> ast.Function:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))
        throws = node.attrib.get('throws', '0') == '1'
        shadows = node.attrib.get('shadows')
        shadowed_by = node.attrib.get('shadowed-by')
        moved_to = node.attrib.get('moved-to')
        async_func = node.attrib.get(_glibns('async-func'))
        sync_func = node.attrib.get(_glibns('sync-func'))
        finish_func = node.attrib.get(_glibns('finish-func'))

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        if ns is not None:
            namespace = ns.name
        else:
            namespace = None

        res = ast.Function(name=name, namespace=namespace, identifier=identifier, throws=throws, inline=inline)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        res.set_return_value(return_value)
        res.set_parameters(params)
        res.set_shadows(shadows)
        res.set_shadowed_by(shadowed_by)
        res.set_moved_to(moved_to)
        res.set_async_func(async_func)
        res.set_sync_func(sync_func)
        res.set_finish_func(finish_func)
        self._maybe_parse_docs(node, res)
        return res

    def _parse_function(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        res = self._parse_type_function(node, ns)
        ns.add_function(res)

    def _parse_function_inline(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        res = self._parse_type_function(node, ns, inline=True)
        ns.add_function(res)

    def _parse_function_macro(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.FunctionMacro(name=name, namespace=ns.name, identifier=identifier)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_parameters(params)
        res.set_return_value(ast.ReturnValue(transfer='none',
                                             target=ast.VoidType(),
                                             nullable=False,
                                             closure=-1, destroy=-1,
                                             scope=None))
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        ns.add_function_macro(res)

    def _parse_method(self, node: ET.Element, inline: bool = False) -> ast.Method:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))
        throws = node.attrib.get('throws', '0') == '1'
        shadows = node.attrib.get('shadows')
        shadowed_by = node.attrib.get('shadowed-by')
        set_property = node.attrib.get(_glibns('set-property'))
        get_property = node.attrib.get(_glibns('get-property'))
        async_func = node.attrib.get(_glibns('async-func'))
        sync_func = node.attrib.get(_glibns('sync-func'))
        finish_func = node.attrib.get(_glibns('finish-func'))

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        child = node.find('./core:parameters/core:instance-parameter', GI_NAMESPACES)
        instance_param = self._parse_parameter(child, True)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.Method(name=name, identifier=identifier, instance_param=instance_param, throws=throws,
                         set_property=set_property, get_property=get_property, inline=inline)
        res.set_return_value(return_value)
        res.set_parameters(params)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_shadows(shadows)
        res.set_shadowed_by(shadowed_by)
        res.set_async_func(async_func)
        res.set_sync_func(sync_func)
        res.set_finish_func(finish_func)
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        return res

    def _parse_virtual_method(self, node: ET.Element) -> ast.VirtualMethod:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))
        invoker = node.attrib.get('invoker')
        throws = node.attrib.get('throws', '0') == '1'
        static = node.attrib.get('static', '0') == '1'

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        child = node.find('./core:parameters/core:instance-parameter', GI_NAMESPACES)
        if child is not None:
            instance_param = self._parse_parameter(child, True)
        else:
            instance_param = None

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.VirtualMethod(name=name, identifier=identifier, invoker=invoker, instance_param=instance_param,
                                throws=throws, static=static)
        res.set_return_value(return_value)
        res.set_parameters(params)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        return res

    def _parse_enum_member(self, node: ET.Element) -> ast.Member:
        name = node.attrib.get('name')
        value = node.attrib.get('value')
        identifier = node.attrib.get(_cns("identifier"))
        nick = node.attrib.get(_glibns("nick"))

        res = ast.Member(name=name, value=value, identifier=identifier, nick=nick)
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        return res

    def _parse_enumeration(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        children = node.findall('core:member', GI_NAMESPACES)
        if children is None or len(children) == 0:
            return

        members = []
        for child in children:
            members.append(self._parse_enum_member(child))

        children = node.findall('core:function', GI_NAMESPACES)
        functions = []
        for child in children:
            functions.append(self._parse_type_function(child))

        name: str = node.attrib['name']
        ctype: str = node.attrib[_cns('type')]
        type_name: T.Optional[str] = node.attrib.get(_glibns('type-name'))
        get_type: T.Optional[str] = node.attrib.get(_glibns('get-type'))
        error_domain: T.Optional[str] = node.attrib.get(_glibns('error-domain'))

        gtype = None
        if type_name is not None and get_type is not None:
            gtype = ast.GType(type_name, get_type)

        if error_domain is not None:
            res: ast.ErrorDomain = ast.ErrorDomain(name=name, namespace=ns.name,
                                                   ctype=ctype, gtype=gtype,
                                                   domain=error_domain)
            ns.add_error_domain(res)
        else:
            res: ast.Enumeration = ast.Enumeration(name=name, namespace=ns.name,
                                                   ctype=ctype, gtype=gtype)
            ns.add_enumeration(res)

        res.set_members(members)
        res.set_functions(functions)
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)

    def _parse_bitfield(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        children = node.findall('core:member', GI_NAMESPACES)
        if children is None or len(children) == 0:
            return

        members = []
        for child in children:
            members.append(self._parse_enum_member(child))

        children = node.findall('core:function', GI_NAMESPACES)
        functions = []
        for child in children:
            functions.append(self._parse_type_function(child))

        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name, get_type)

        res = ast.BitField(name=name, namespace=ns.name, ctype=ctype, gtype=gtype)
        res.set_members(members)
        res.set_functions(functions)
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        ns.add_bitfield(res)

    def _parse_property(self, node: ET.Element) -> ast.Property:
        name = node.attrib.get('name')
        writable = node.attrib.get('writable', '0') == '1'
        readable = node.attrib.get('readable', '1') == '1'
        construct_only = node.attrib.get('construct-only', '0') == '1'
        construct = node.attrib.get('construct', '0') == '1'
        transfer = node.attrib.get('transfer-ownership')
        setter = node.attrib.get('setter')
        getter = node.attrib.get('getter')
        default_value = node.attrib.get('default-value')

        ctype = self._parse_ctype(node)

        res = ast.Property(name=name, transfer=transfer, target=ctype,
                           writable=writable, readable=readable,
                           construct=construct, construct_only=construct_only,
                           setter=setter, getter=getter,
                           default_value=default_value)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        return res

    def _parse_signal(self, node: ET.Element) -> ast.Signal:
        name = node.attrib.get('name')
        when = node.attrib.get('when')
        detailed = node.attrib.get('detailed') == '1'
        action = node.attrib.get('action') == '1'
        no_hooks = node.attrib.get('no-hooks') == '1'
        no_recurse = node.attrib.get('no-recurse') == '1'

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = None
        if child is not None:
            return_value = self._parse_return_value(child)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.Signal(name=name, when=when, detailed=detailed, action=action, no_hooks=no_hooks, no_recurse=no_recurse)
        res.set_parameters(params)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        if return_value is not None:
            res.set_return_value(return_value)
        return res

    def _parse_field(self, node: ET.Element) -> ast.Field:
        name = node.attrib.get('name')
        writable = node.attrib.get('writable', '0') == '1'
        readable = node.attrib.get('readable', '0') == '1'
        private = node.attrib.get('private', '0') == '1'
        bits = int(node.attrib.get('bits', '0'))

        child = node.find('core:callback', GI_NAMESPACES)
        if child is not None:
            ctype = self._parse_callback_field(child)
        else:
            ctype = self._parse_ctype(node)

        if ctype is None:
            ctype = ast.VoidType()

        res = ast.Field(name=name, writable=writable, readable=readable, private=private, bits=bits, target=ctype)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        return res

    def _parse_implements(self, node: ET.Element) -> ast.Interface:
        return self._lookup_type(name=node.attrib['name'])

    def _parse_class(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        parent = node.attrib.get('parent')
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))
        abstract = node.attrib.get('abstract', '0') == '1'
        fundamental = node.attrib.get(_glibns('fundamental'), '0') == '1'
        ref_func = node.attrib.get(_glibns('ref-func'))
        unref_func = node.attrib.get(_glibns('unref-func'))

        parent_type = None
        if parent is not None:
            parent_type = self._lookup_type(name=parent)

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        fields = []
        children = node.findall('core:field', GI_NAMESPACES)
        for child in children:
            fields.append(self._parse_field(child))

        ifaces = []
        children = node.findall('core:implements', GI_NAMESPACES)
        for child in children:
            ifaces.append(self._parse_implements(child))

        ctors = []
        children = node.findall('core:constructor', GI_NAMESPACES)
        for child in children:
            ctors.append(self._parse_type_function(child))

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))
        children = node.findall('core:method-inline', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child, inline=True))

        vmethods = []
        children = node.findall('core:virtual-method', GI_NAMESPACES)
        for child in children:
            vmethods.append(self._parse_virtual_method(child))

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_type_function(child))

        properties = []
        children = node.findall('core:property', GI_NAMESPACES)
        for child in children:
            properties.append(self._parse_property(child))

        signals = []
        children = node.findall('glib:signal', GI_NAMESPACES)
        for child in children:
            signals.append(self._parse_signal(child))

        res = ast.Class(name=name, namespace=ns.name, symbol_prefix=symbol_prefix, ctype=ctype,
                        parent=parent_type, gtype=gtype,
                        abstract=abstract, fundamental=fundamental,
                        ref_func=ref_func, unref_func=unref_func)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        res.set_fields(fields)
        res.set_implements(ifaces)
        res.set_constructors(ctors)
        res.set_methods(methods)
        res.set_virtual_methods(vmethods)
        res.set_functions(functions)
        res.set_properties(properties)
        res.set_signals(signals)
        self._maybe_parse_docs(node, res)
        ns.add_class(res)

    def _parse_interface(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        prerequisite = None
        child = node.find('core:prerequisite', GI_NAMESPACES)
        if child is not None:
            prerequisite = self._lookup_type(name=child.attrib['name'])

        fields = []
        children = node.findall('core:field', GI_NAMESPACES)
        for child in children:
            fields.append(self._parse_field(child))

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        vmethods = []
        children = node.findall('core:virtual-method', GI_NAMESPACES)
        for child in children:
            vmethods.append(self._parse_virtual_method(child))

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_type_function(child))

        properties = []
        children = node.findall('core:property', GI_NAMESPACES)
        for child in children:
            properties.append(self._parse_property(child))

        signals = []
        children = node.findall('glib:signal', GI_NAMESPACES)
        for child in children:
            signals.append(self._parse_signal(child))

        res = ast.Interface(name=name, namespace=ns.name, symbol_prefix=symbol_prefix, ctype=ctype, gtype=gtype)
        res.set_prerequisite(prerequisite)
        res.set_fields(fields)
        res.set_virtual_methods(vmethods)
        res.set_properties(properties)
        res.set_signals(signals)
        res.set_methods(methods)
        res.set_functions(functions)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        self._maybe_parse_docs(node, res)
        ns.add_interface(res)

    def _parse_boxed(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        name = node.attrib.get(_glibns('name'))
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type)

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_type_function(child))

        res = ast.Boxed(name=name, namespace=ns.name, symbol_prefix=symbol_prefix, gtype=gtype)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        res.set_functions(functions)
        self._maybe_parse_docs(node, res)
        ns.add_boxed(res)

    def _parse_record(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        name: str = node.attrib['name']
        symbol_prefix: str = node.attrib.get(_cns('symbol-prefix'), '')
        ctype: str = node.attrib[_cns('type')]
        type_name: T.Optional[str] = node.attrib.get(_glibns('type-name'))
        get_type: T.Optional[str] = node.attrib.get(_glibns('get-type'))
        type_struct: T.Optional[str] = node.attrib.get(_glibns('type-struct'))
        gtype_struct_for: T.Optional[str] = node.attrib.get(_glibns('is-gtype-struct-for'))
        disguised: bool = node.attrib.get('disguised', '0') == '1'

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        fields = []
        children = node.findall('core:field', GI_NAMESPACES)
        for child in children:
            fields.append(self._parse_field(child))

        ctors = []
        children = node.findall('core:constructor', GI_NAMESPACES)
        for child in children:
            ctors.append(self._parse_type_function(child))

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_type_function(child))

        res = ast.Record(name=name, namespace=ns.name, symbol_prefix=symbol_prefix,
                         ctype=ctype, gtype=gtype,
                         struct_for=gtype_struct_for, disguised=disguised)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        res.set_fields(fields)
        res.set_constructors(ctors)
        res.set_methods(methods)
        res.set_functions(functions)
        self._maybe_parse_docs(node, res)
        ns.add_record(res)

    def _parse_union(self, node: ET.Element, repo: ast.Repository, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        fields = []
        children = node.findall('core:field', GI_NAMESPACES)
        for child in children:
            fields.append(self._parse_field(child))

        ctors = []
        children = node.findall('core:constructor', GI_NAMESPACES)
        for child in children:
            ctors.append(self._parse_type_function(child))

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_type_function(child))

        res = ast.Union(name=name, namespace=ns.name, symbol_prefix=symbol_prefix, ctype=ctype, gtype=gtype)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_version(node.attrib.get('version'))
        res.set_fields(fields)
        res.set_constructors(ctors)
        res.set_methods(methods)
        res.set_functions(functions)
        self._maybe_parse_docs(node, res)
        ns.add_union(res)
