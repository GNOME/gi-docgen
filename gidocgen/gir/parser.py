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


def _corens(tag: str) -> str:
    return f"{{{GI_NAMESPACES['core']}}}{tag}"


def _glibns(tag: str) -> str:
    return f"{{{GI_NAMESPACES['glib']}}}{tag}"


def _cns(tag: str) -> str:
    return f"{{{GI_NAMESPACES['c']}}}{tag}"


class GirParser:
    def __init__(self, search_paths=[]):
        self._search_paths = search_paths
        self._repository = None
        self._dependencies = {}

    def append_search_path(self, path: str) -> None:
        """Append a path to the list of search paths"""
        self._search_paths.append(path)

    def prepend_search_paths(self, path: str) -> None:
        """Prepend a path to the list of search paths"""
        self._search_paths = [path] + self._search_paths

    def parse(self, girfile: T.TextIO) -> None:
        """Parse @girfile"""
        log.debug(f"Loading GIR for {girfile}")
        tree = ET.parse(girfile)
        repository = self._parse_tree(tree.getroot())
        if repository is None:
            log.error(f"Could not parse GIR {girfile}")
        else:
            self._repository = repository

    def get_repository(self, name: T.Optional[str] = None) -> T.Optional[ast.Repository]:
        if name is None:
            return self._repository
        else:
            return self._dependencies[name]

    def _parse_dependency(self, include: ast.Include) -> None:
        if self._dependencies.get(str(include), None) is not None:
            log.debug(f"Dependency {include} already parsed")
            return
        repository = None
        for base_path in self._search_paths:
            girfile = os.path.join(base_path, f"{include}.gir")
            if os.path.exists(girfile) and os.path.isfile(girfile):
                log.debug(f"Loading GIR for dependency {include} at {girfile}")
                tree = ET.parse(girfile)
                repository = self._parse_tree(tree.getroot())
                break
        if repository is None:
            log.error(f"Could not find GIR dependency in the search paths: {include}")
        else:
            ns = repository.namespace
            self._dependencies[str(ns)] = repository

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

        repository.includes.extend(self._dependencies.values())

        repository.add_namespace(namespace)

        parse_methods: T.Mapping[str, T.Callable[[ET.Element, T.Optional[ast.Namespace]], T.Any]] = {
            _corens('alias'): self._parse_alias,
            _corens('bitfield'): self._parse_bitfield,
            _glibns('boxed'): self._parse_boxed,
            _corens('callback'): self._parse_callback,
            _corens('class'): self._parse_class,
            _corens('constant'): self._parse_constant,
            _corens('enumeration'): self._parse_enumeration,
            _corens('function-macro'): self._parse_function_macro,
            _corens('function'): self._parse_function,
            _corens('interface'): self._parse_interface,
            _corens('record'): self._parse_record,
            _corens('union'): self._parse_union,
        }

        for node in ns:
            parse_method = parse_methods.get(node.tag, None)
            if parse_method is not None:
                parse_method(node, namespace)

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

    def _maybe_parse_docs(self, node: ET.Element, element: ast.GIRElement) -> None:
        doc = self._maybe_parse_doc(node)
        if doc is not None:
            element.set_doc(doc)
        source_pos = self._maybe_parse_source_position(node)
        if source_pos is not None:
            element.set_source_position(source_pos)
        stability = node.attrib.get('stability')
        if stability is not None:
            element.set_stability(stability)
        deprecated = node.attrib.get('deprecated')
        if deprecated is not None:
            deprecated_since = node.attrib.get('deprecated-version')
            deprecated_doc = self._maybe_parse_deprecated_doc(node)
            if deprecated_doc is not None:
                element.set_deprecated(deprecated_doc, deprecated_since)

    def _parse_ctype(self, node: ET.Element) -> ast.Type:
        ctype: T.Optional[ast.Type] = None

        child = node.find('core:array', GI_NAMESPACES)
        if child is not None:
            name = node.attrib.get('name')
            zero_terminated = int(child.attrib.get('zero-terminated', 0))
            fixed_size = int(child.attrib.get('fixed-size', -1))
            length = int(child.attrib.get('length', -1))
            array_type = child.attrib.get(_cns('type'))

            target: T.Optional[ast.Type] = None
            child = node.find('core:type', GI_NAMESPACES)
            if child is not None:
                ttype = child.attrib.get(_cns('type'), 'void')
                tname = child.attrib.get('name', ttype.replace('*', ''))
                if tname == 'none' and ttype == 'void':
                    target = ast.VoidType()
                else:
                    target = ast.Type(name=tname, ctype=ctype)
            else:
                target = ast.VoidType()

            ctype = ast.ArrayType(name=name, zero_terminated=zero_terminated, fixed_size=fixed_size, length=length,
                                  ctype=array_type, value_type=target)
        else:
            child = node.find('core:type', GI_NAMESPACES)
            if child is not None:
                ttype = child.attrib.get(_cns('type'), 'void')
                tname = child.attrib.get('name', ttype.replace('*', ''))
                if tname == 'none' and ttype == 'void':
                    ctype = ast.VoidType()
                else:
                    ctype = ast.Type(name=tname, ctype=ttype)
            else:
                child = node.find('core:varargs', GI_NAMESPACES)
                if child is not None:
                    ctype = ast.VarArgs()

        if ctype is None:
            ctype = ast.VoidType()

        return ctype

    def _parse_alias(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
        child = node.find('core:type', GI_NAMESPACES)
        assert child is not None

        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))

        alias_type = ast.Type(name=child.attrib['name'], ctype=child.attrib.get(_cns('type')))

        res = ast.Alias(name=name, ctype=ctype, target=alias_type)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        ns.add_alias(res)

    def _parse_callback(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.Callback(name=name, ctype=ctype)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_parameters(params)
        res.set_return_value(return_value)
        self._maybe_parse_docs(node, res)

        if ns is not None:
            ns.add_callback(res)

        return res

    def _parse_constant(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
        child = node.find('core:type', GI_NAMESPACES)
        assert child is not None

        name = node.attrib.get('name')
        ctype = node.attrib.get(_cns('type'))
        value = node.attrib.get('value')

        const_type = ast.Type(name=child.attrib['name'], ctype=child.attrib.get(_cns('type')))

        res = ast.Constant(name=name, ctype=ctype, value=value, target=const_type)
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

    def _parse_function(self, node: ET.Element, ns: T.Optional[ast.Namespace] = None) -> ast.Function:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.Function(name=name, identifier=identifier)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_return_value(return_value)
        res.set_parameters(params)
        self._maybe_parse_docs(node, res)

        if ns is not None:
            ns.add_function(res)

        return res

    def _parse_function_macro(self, node: ET.Element, ns: T.Optional[ast.Namespace] = None) -> ast.FunctionMacro:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.FunctionMacro(name=name, identifier=identifier)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        res.set_parameters(params)
        self._maybe_parse_docs(node, res)

        if ns is not None:
            ns.add_function_macro(res)

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

        res = ast.Method(name=name, identifier=identifier, instance_param=instance_param)
        res.set_return_value(return_value)
        res.set_parameters(params)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        if cls is not None:
            cls.methods.append(res)

        return res

    def _parse_virtual_method(self, node: ET.Element, cls: T.Optional[ast.Class] = None) -> ast.VirtualMethod:
        name = node.attrib.get('name')
        identifier = node.attrib.get(_cns('identifier'))
        invoker = node.attrib.get('invoker')

        child = node.find('core:return-value', GI_NAMESPACES)
        return_value = self._parse_return_value(child)

        child = node.find('./core:parameters/core:instance-parameter', GI_NAMESPACES)
        instance_param = self._parse_parameter(child, True)

        children = node.findall('./core:parameters/core:parameter', GI_NAMESPACES)
        params = []
        for child in children:
            params.append(self._parse_parameter(child))

        res = ast.VirtualMethod(name=name, identifier=identifier, invoker=invoker, instance_param=instance_param)
        res.set_return_value(return_value)
        res.set_parameters(params)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        if cls is not None:
            cls.virtual_methods.append(res)

        return res

    def _parse_enum_member(self, node: ET.Element) -> ast.Member:
        name = node.attrib.get('name')
        value = node.attrib.get('value')
        identifier = node.attrib.get(_cns("identifier"))
        nick = node.attrib.get(_glibns("nick"))

        res = ast.Member(name=name, value=value, identifier=identifier, nick=nick)
        self._maybe_parse_docs(node, res)
        return res

    def _parse_enumeration(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
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

        name: str = node.attrib['name']
        ctype: str = node.attrib[_cns('type')]
        type_name: T.Optional[str] = node.attrib.get(_glibns('type-name'))
        get_type: T.Optional[str] = node.attrib.get(_glibns('get-type'))
        error_domain: T.Optional[str] = node.attrib.get(_glibns('error-domain'))

        gtype = None
        if type_name is not None and get_type is not None:
            gtype = ast.GType(type_name, get_type)

        if error_domain is not None:
            res: ast.ErrorDomain = ast.ErrorDomain(name, ctype, gtype, error_domain)
            if ns is not None:
                ns.add_error_domain(res)
        else:
            res: ast.Enumeration = ast.Enumeration(name, ctype, gtype)
            if ns is not None:
                ns.add_enumeration(res)

        res.set_members(members)
        res.set_functions(functions)
        self._maybe_parse_docs(node, res)

    def _parse_bitfield(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
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
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name, get_type)

        res = ast.BitField(name, ctype, gtype)
        ns.add_bitfield(res)

        res.set_members(members)
        res.set_functions(functions)
        self._maybe_parse_docs(node, res)

    def _parse_property(self, node: ET.Element, cls: T.Optional[ast.Class] = None) -> ast.Property:
        name = node.attrib.get('name')
        writable = node.attrib.get('writable', '0') == '1'
        readable = node.attrib.get('readable', '1') == '1'
        construct_only = node.attrib.get('construct-only', '0') == '1'
        construct = node.attrib.get('construct', '0') == '1'
        transfer = node.attrib.get('transfer-ownership')

        ctype = self._parse_ctype(node)

        res = ast.Property(name=name, transfer=transfer, target=ctype,
                           writable=writable, readable=readable,
                           construct=construct, construct_only=construct_only)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        return res

    def _parse_signal(self, node: ET.Element, cls: T.Optional[ast.Class] = None) -> ast.Signal:
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
        self._maybe_parse_docs(node, res)
        if return_value is not None:
            res.set_return_value(return_value)

        if cls is not None:
            cls.signals.append(res)

        return res

    def _parse_field(self, node: ET.Element) -> ast.Field:
        name = node.attrib.get('name')
        writable = node.attrib.get('writable', '0') == '1'
        readable = node.attrib.get('readable', '0') == '1'
        private = node.attrib.get('private', '0') == '1'
        bits = int(node.attrib.get('bits', '0'))

        child = node.find('core:callback', GI_NAMESPACES)
        if child is not None and child.attrib.get(_cns('type'), None) is not None:
            ctype = self._parse_ctype(child)
        else:
            ctype = self._parse_ctype(node)

        if ctype is None:
            ctype = ast.VoidType()

        res = ast.Field(name=name, writable=writable, readable=readable, private=private, bits=bits, target=ctype)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        return res

    def _parse_implements(self, node: ET.Element) -> str:
        return node.attrib['name']

    def _parse_class(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
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

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        res = ast.Class(name=name, symbol_prefix=symbol_prefix, ctype=ctype, parent=parent, gtype=gtype,
                        abstract=abstract, fundamental=fundamental, ref_func=ref_func, unref_func=unref_func)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        fields = []
        children = node.findall('core:field', GI_NAMESPACES)
        for child in children:
            fields.append(self._parse_field(child))

        res.set_fields(fields)

        ifaces = []
        children = node.findall('core:implements', GI_NAMESPACES)
        for child in children:
            ifaces.append(self._parse_implements(child))

        res.set_implements(ifaces)

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

        vmethods = []
        children = node.findall('core:virtual-method', GI_NAMESPACES)
        for child in children:
            vmethods.append(self._parse_virtual_method(child))

        res.set_virtual_methods(vmethods)

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

    def _parse_interface(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        res = ast.Interface(name=name, symbol_prefix=symbol_prefix, ctype=ctype, gtype=gtype)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        child = node.find('core:prerequisite', GI_NAMESPACES)
        if child is not None:
            res.set_prerequisite(child.attrib['name'])

        fields = []
        children = node.findall('core:field', GI_NAMESPACES)
        for child in children:
            fields.append(self._parse_field(child))

        res.set_fields(fields)

        methods = []
        children = node.findall('core:method', GI_NAMESPACES)
        for child in children:
            methods.append(self._parse_method(child))

        res.set_methods(methods)

        vmethods = []
        children = node.findall('core:virtual-method', GI_NAMESPACES)
        for child in children:
            vmethods.append(self._parse_virtual_method(child))

        res.set_virtual_methods(vmethods)

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

    def _parse_boxed(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
        name = node.attrib.get(_glibns('name'))
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type)

        res = ast.Boxed(name=name, symbol_prefix=symbol_prefix, gtype=gtype)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        functions = []
        children = node.findall('core:function', GI_NAMESPACES)
        for child in children:
            functions.append(self._parse_function(child))

        res.set_functions(functions)

        ns.add_boxed(res)

    def _parse_record(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
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

        res = ast.Record(name=name, symbol_prefix=symbol_prefix, ctype=ctype, gtype=gtype,
                         struct_for=gtype_struct_for, disguised=disguised)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        fields = []
        children = node.findall('core:field', GI_NAMESPACES)
        for child in children:
            fields.append(self._parse_field(child))

        res.set_fields(fields)

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

    def _parse_union(self, node: ET.Element, ns: T.Optional[ast.Namespace]) -> None:
        name = node.attrib.get('name')
        symbol_prefix = node.attrib.get(_cns('symbol-prefix'))
        ctype = node.attrib.get(_cns('type'))
        type_name = node.attrib.get(_glibns('type-name'))
        get_type = node.attrib.get(_glibns('get-type'))
        type_struct = node.attrib.get(_glibns('type-struct'))

        gtype = None
        if type_name is not None:
            gtype = ast.GType(type_name=type_name, get_type=get_type, type_struct=type_struct)

        res = ast.Union(name=name, symbol_prefix=symbol_prefix, ctype=ctype, gtype=gtype)
        res.set_introspectable(node.attrib.get('introspectable', '1') != '0')
        self._maybe_parse_docs(node, res)

        fields = []
        children = node.findall('core:field', GI_NAMESPACES)
        for child in children:
            fields.append(self._parse_field(child))

        res.set_fields(fields)

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
