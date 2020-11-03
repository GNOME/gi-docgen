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

def _corens(tag):
    return f"{{{GI_NAMESPACES['core']}}}{tag}"


def _glibns(tag):
    return f"{{{GI_NAMESPACES['glib']}}}{tag}"


def _cns(tag):
    return f"{{{GI_NAMESPACES['c']}}}{tag}"


class GirParser:
    def __init__(self, search_paths=[]):
        self._search_paths = search_paths
        self._repositories = []

    def append_search_path(self, path: str) -> None:
        """Append a path to the list of search paths"""
        self._search_paths.append(path)

    def prepend_search_paths(self, path: str) -> None:
        """Prepend a path to the list of search paths"""
        self._search_paths = [path] + self._search_paths

    def parse(self, girfile: str) -> None:
        """Parse @girfile"""
        tree = ET.parse(girfile)
        self._parse_tree(tree.getroot())

    def get_repository(self) -> ast.Repository:
        return self._repositories[0]

    def _parse_tree(self, root):
        assert root.tag == _corens('repository')

        repository = ast.Repository()
        for node in root:
            if node.tag == _corens('include'):
                include = self._parse_include(node)
                repository.includes.append(include)
            elif node.tag == _cns('include'):
                include = self._parse_c_include(node)
                repository.c_includes.append(include)
            elif node.tag == _corens('package'):
                package = self._parse_package(node)
                repository.packages.append(package)

        self._repositories.append(repository)

        ns = root.find(_corens('namespace'))
        assert ns is not None

        identifier_prefixes = ns.attrib.get(_cns('identifier-prefixes'))
        if identifier_prefixes:
            identifier_prefixes = identifier_prefixes.split(',')
        symbol_prefixes = ns.attrib.get(_cns('symbol-prefixes'))
        if symbol_prefixes:
            symbol_prefixes = symbol_prefixes.split(',')

        namespace = ast.Namespace(ns.attrib['name'], ns.attrib['version'], identifier_prefixes, symbol_prefixes)
        shared_libs = ns.attrib.get('shared-library')
        if shared_libs:
            namespace.add_shared_libraries(shared_libs.split(','))

        repository.add_namespace(namespace)

        parse_methods = {
            _corens('alias'): self._parse_alias,
            _glibns('boxed'): self._parse_boxed,
            _corens('class'): self._parse_class,
            _corens('constant'): self._parse_constant,
            _corens('enumeration'): self._parse_enumeration,
            _corens('function'): self._parse_function,
            _corens('interface'): self._parse_interface,
            _corens('record'): self._parse_record,
            _corens('union'): self._parse_union,
        }

        for node in ns:
            parse_method = parse_methods.get(node.tag)
            if parse_method:
                parse_method(node, namespace)

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

        return ast.Doc(content=child.text, filename=child.attrib['filename'], line=child.attrib['line'])

    def _maybe_parse_source_position(self, node: ET.Element) -> T.Optional[ast.SourcePosition]:
        child = node.find('core:source-position', GI_NAMESPACES)
        if child is None:
            return None

        return ast.SourcePosition(filename=child.attrib['filename'], line=child.attrib['line'])

    def _parse_alias(self, node: ET.Element, ns: ast.Namespace) -> None:
        child = node.find('core:type', GI_NAMESPACES)
        assert child is not None

        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))

        alias_type = ast.Type(name=child.attrib['name'], ctype=child.attrib.get(_cns('type')))

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Alias(name=name, ctype=ctype, target=alias_type)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        ns.add_alias(res)

    def _parse_constant(self, node: ET.Element, ns: ast.Namespace) -> None:
        child = node.find('core:type', GI_NAMESPACES)
        assert child is not None

        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))
        value = node.attrib.get('value')

        const_type = ast.Type(name=child.attrib['name'], ctype=child.attrib.get(_cns('type')))

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Constant(name=name, ctype=ctype, value=value, target=const_type)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        ns.add_constant(res)

    def _parse_return_value(self, node: ET.Element) -> ast.ReturnValue:
        transfer = node.attrib.get('transfer-ownership')

        ctype = None
        child = node.find('core:type', GI_NAMESPACES)
        if child is not None:
            ctype = ast.Type(name=child.attrib['name'], ctype=child.attrib.get(_cns('type')))

        return ast.ReturnValue(transfer=transfer, target=ctype) 

    def _parse_parameter(self, node: ET.Element, is_instance_param: bool = False) -> ast.Parameter:
        name = node.attrib.get('name')
        direction = node.attrib.get('direction')
        transfer = node.attrib.get('transfer-ownership')
        nullable = node.attrib.get('nullable') == '1'
        optional = node.attrib.get('optional') == '1'
        caller_allocates = node.attrib.get('caller-allocates') == '1'
        callee_allocates = node.attrib.get('callee-allocates') == '1'

        ctype = None
        child = node.find('core:type', GI_NAMESPACES)
        if child is not None:
            ctype = ast.Type(name=child.attrib['name'], ctype=child.attrib.get(_cns('type')))

        return ast.Parameter(name=name, direction=direction, transfer=transfer, target=ctype,
            optional=optional, nullable=nullable, caller_allocates=caller_allocates,
            callee_allocates=callee_allocates) 

    def _parse_function(self, node: ET.Element, ns: T.Optional[ast.Namespace] = None) -> ast.Function:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Function(name=name, identifier=identifier)
        res.set_return_value(return_value)
        res.set_parameters(params)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        if ns is not None:
            ns.add_function(res)

        return res

    def _parse_method(self, node: ET.Element, cls: T.Optional[ast.Class] = None) -> ast.Method:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        child = node.find('./core:parameters/core:instance-parameter', GI_NAMESPACES)
        instance_param = self._parse_parameter(child, True)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Method(name=name, identifier=identifier, instance_param=instance_param)
        res.set_return_value(return_value)
        res.set_parameters(params)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        if cls is not None:
            cls.add_method(res)

        return res

    def _parse_enum_member(self, node: ET.Element) -> ast.EnumerationMember:
        name = node.attrib.get('name')
        value = node.attrib.get('value')
        identifier = node.attrib.get(_cns("identifier"))
        nick = node.attrib.get(_glibns("nick"))
        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.EnumerationMember(name=name, value=value, identifier=identifier, nick=nick)
        res.set_doc(doc)
        res.set_source_position(source_pos)
        return res

    def _parse_enumeration(self, node: ET.Element, ns: ast.Namespace) -> None:
        children = node.findall('core:member', GI_NAMESPACES)
        if children is None or len(children) == 0:
            return

        members = []
        for child in children:
            members.append(self._parse_enum_member(child))

        children = node.findall('core:function', GI_NAMESPACES)
        functions = []
        for child in children:
            functions.append(self._parse_function(child))

        name = node.attrib.get('name')
        ctype = node.attrib.get('ctype')
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name, get_type)

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = None
        error_domain = node.attrib.get(_glibns('error-domain'))
        if error_domain:
            res = ast.ErrorDomain(name, ctype, gtype, error_domain)
            ns.add_error_domain(res)
        else:
            res = ast.Enumeration(name, ctype, gtype)
            ns.add_enumeration(res)

        res.set_members(members)
        res.set_functions(functions)
        res.set_doc(doc)
        res.set_source_position(source_pos)

    def _parse_property(self, node: ET.Element, cls: T.Optional[ast.Class] = None) -> ast.Property:
        name = node.attrib.get('name')
        writable = node.attrib.get('writable') == '1'
        readable = node.attrib.get('readable') != '0'
        construct_only = node.attrib.get('construct-only') == '1'
        construct = node.attrib.get('construct') == '1'
        transfer = node.attrib.get('transfer-ownership')

        child = node.find('core:type', GI_NAMESPACES)
        if child is not None:
            ctype = ast.Type(name=child.attrib.get('name'), ctype=child.attrib.get(_cns('type')))
        else:
            ctype = ast.Type(name='void', ctype='void')

        return ast.Property(name=name, transfer=transfer, target=ctype,
            writable=writable, readable=readable,
            construct=construct, construct_only=construct_only)

    def _parse_signal(self, node: ET.Element, cls: T.Optional[ast.Class] = None) -> ast.Signal:
        name = node.attrib.get('name')
        when = node.attrib.get('when')

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Signal(name=name, when=when)
        res.set_return_value(return_value)
        res.set_parameters(params)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        if cls is not None:
            cls.add_signal(res)

        return res

    def _parse_class(self, node: ET.Element, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        parent = node.attrib.get('parent')
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))
        abstract = node.attrib.get('abstract') == '1'

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Class(name=name, symbol_prefix=symbol_prefix, ctype=ctype, parent=parent, abstract=abstract, gtype=gtype)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        ctors = []
        children = node.findall('core:constructor', GI_NAMESPACES)
        for child in children:
            ctors.append(self._parse_function(child))

        res.set_constructors(ctors)

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        res.set_methods(methods)

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_function(child))

        res.set_functions(functions)

        properties = []
        children = node.findall('core:property', GI_NAMESPACES)
        for child in children:
            properties.append(self._parse_property(child))

        res.set_properties(properties)

        signals = []
        children = node.findall('glib:signal', GI_NAMESPACES)
        for child in children:
            signals.append(self._parse_signal(child))

        res.set_signals(signals)

        ns.add_class(res)

    def _parse_interface(self, node: ET.Element, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Interface(name=name, symbol_prefix=symbol_prefix, ctype=ctype, gtype=gtype)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        res.set_methods(methods)

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_function(child))

        res.set_functions(functions)

        properties = []
        children = node.findall('core:property', GI_NAMESPACES)
        for child in children:
            properties.append(self._parse_property(child))

        res.set_properties(properties)

        signals = []
        children = node.findall('glib:signal', GI_NAMESPACES)
        for child in children:
            signals.append(self._parse_signal(child))

        res.set_signals(signals)

        ns.add_interface(res)

    def _parse_boxed(self, node: ET.Element, ns: ast.Namespace) -> None:
        name = node.attrib.get(_glibns('name'))
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type)

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Boxed(name=name, symbol_prefix=symbol_prefix, gtype=gtype)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        res.set_methods(methods)

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_function(child))

        res.set_functions(functions)

        ns.add_boxed(res)

    def _parse_record(self, node: ET.Element, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Record(name=name, symbol_prefix=symbol_prefix, ctype=ctype, gtype=gtype)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        ctors = []
        children = node.findall('core:constructor', GI_NAMESPACES)
        for child in children:
            ctors.append(self._parse_function(child))

        res.set_constructors(ctors)

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        res.set_methods(methods)

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_function(child))

        res.set_functions(functions)

        ns.add_record(res)

    def _parse_union(self, node: ET.Element, ns: ast.Namespace) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        doc = self._maybe_parse_doc(node)
        source_pos = self._maybe_parse_source_position(node)

        res = ast.Union(name=name, symbol_prefix=symbol_prefix, ctype=ctype, gtype=gtype)
        res.set_doc(doc)
        res.set_source_position(source_pos)

        ctors = []
        children = node.findall('core:constructor', GI_NAMESPACES)
        for child in children:
            ctors.append(self._parse_function(child))

        res.set_constructors(ctors)

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        res.set_methods(methods)

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_function(child))

        res.set_functions(functions)

        ns.add_union(res)
