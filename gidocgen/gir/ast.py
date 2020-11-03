# SPDX-FileCopyrightText: 2020 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import typing as T

class Doc:
    """A documentation node, pointing to the source code"""
    def __init__(self, content: str, filename: str, line: int):
        self.content = content
        self.filename = filename
        self.line = line


class SourcePosition:
    """A location inside the source code"""
    def __init__(self, filename: str, line: int):
        self.filename = filename
        self.line = line


class GIRElement:
    """Base type for elements inside the GIR"""
    def __init__(self):
        self.doc = None
        self.source_position = None
        self.deprecated = False
        self.deprecated_doc = None
        self.deprecated_since = None

    def set_doc(self, doc: Doc) -> None:
        """Set the documentation for the element"""
        self.doc = doc

    def set_source_position(self, pos: SourcePosition) -> None:
        """Set the position in the source code for the element"""
        self.source_position = pos

    def set_deprecated(self, doc: str = None, since_version: str = None) -> None:
        self.deprecated = True
        self.deprecated_doc = doc
        self.deprecated_since = since_version


class Type(GIRElement):
    """Base class for all Type nodes"""
    def __init__(self, name: str, ctype: str):
        super().__init__()
        self.name = name
        self.ctype = ctype


class GType:
    """Base class for GType information"""
    def __init__(self, type_name: str, get_type: str, type_struct: str=None):
        self.type_name = type_name
        self.get_type = get_type
        self.type_struct = type_struct


class Alias(Type):
    """Alias to a Type"""
    def __init__(self, name: str, ctype: str, target: Type):
        super().__init__(name, ctype)
        self.target = target


class Constant(Type):
    """A constant"""
    def __init__(self, name: str, ctype: str, target: Type, value: str):
        super().__init__(name, ctype)
        self.target = target
        self.value = value


class Parameter(GIRElement):
    """A callable parameter"""
    def __init__(self, name: str, direction: str, transfer: str, target: Type, caller_allocates: bool = False, callee_allocates: bool = False, optional: bool = False, nullable: bool = False):
        super().__init__()
        self.name = name
        self.direction = direction
        self.transfer = transfer
        self.caller_allocates = caller_allocates
        self.callee_allocates = callee_allocates
        self.optional = optional
        self.nullable = nullable
        if target is None:
            self.target = Type(name='void', ctype='void')
        else:
            self.target = target


class ReturnValue(GIRElement):
    """A callable's return value"""
    def __init__(self, transfer: str, target: Type):
        super().__init__()
        self.transfer = transfer
        if target is None:
            self.target = Type(name='void', ctype='void')
        else:
            self.target = target


class Callable(GIRElement):
    """A callable symbol: function, method, function-macro, ..."""
    def __init__(self, name: str, identifier: str):
        super().__init__()
        self.name = name
        self.identifier = identifier
        self.parameters = []
        self.return_value = None

    def add_parameter(self, param: Parameter) -> None:
        self.parameters.append(param)

    def set_parameters(self, params: T.List[Parameter]) -> None:
        self.parameters.extend(params)

    def set_return_value(self, res: ReturnValue) -> None:
        self.return_value = res


class Function(Callable):
    def __init__(self, name: str, identifier: str):
        super().__init__(name, identifier)


class Method(Callable):
    def __init__(self, name: str, identifier: str, instance_param: Parameter):
        super().__init__(name, identifier)
        self.instance_param = instance_param


class Property(GIRElement):
    def __init__(self, name: str, transfer: str, target: Type, writable: bool = True, readable: bool = True, construct: bool = False, construct_only: bool = False):
        super().__init__()
        self.name = name
        self.transfer = transfer
        self.writable = writable
        self.readable = readable
        self.construct = construct
        self.construct_only = construct_only
        self.target = target


class Signal(GIRElement):
    def __init__(self, name: str, when: str):
        super().__init__()
        self.name = name
        self.when = when
        self.parameters = []
        self.return_value = None

    def set_parameters(self, params: T.List[Parameter]) -> None:
        self.parameters.extend(params)

    def set_return_value(self, res: ReturnValue) -> None:
        self.return_value = res


class Class(Type):
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType, parent: str = 'GObject.Object', abstract: bool = False):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.parent = parent
        self.abstract = abstract
        self.gtype = gtype
        self.constructors = []
        self.methods = []
        self.properties = []
        self.signals = []
        self.functions = []

    def set_constructors(self, ctors: T.List[Function]) -> None:
        self.constructors.extend(ctors)

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_properties(self, properties: T.List[Property]) -> None:
        self.properties.extend(properties)

    def set_signals(self, signals: T.List[Signal]) -> None:
        self.signals.extend(signals)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)


class Interface(Type):
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.methods = []
        self.properties = []
        self.signals = []
        self.functions = []

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_properties(self, properties: T.List[Property]) -> None:
        self.properties.extend(properties)

    def set_signals(self, signals: T.List[Signal]) -> None:
        self.signals.extend(signals)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)


class Boxed(Type):
    def __init__(self, name: str, symbol_prefix: str, gtype: GType):
        super().__init__(name, None)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.methods = []
        self.functions = []

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)


class Record(Type):
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.constructors = []
        self.methods = []
        self.functions = []

    def set_constructors(self, ctors: T.List[Function]) -> None:
        self.constructors.extend(ctors)

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)


class Union(Type):
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.constructors = []
        self.methods = []
        self.functions = []

    def set_constructors(self, ctors: T.List[Function]) -> None:
        self.constructors.extend(ctors)

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)


class EnumerationMember(GIRElement):
    def __init__(self, name: str, value: str, identifier: str, nick: str):
        super().__init__()
        self.name = name
        self.value = value
        self.identifier = identifier
        self.nick = nick


class Enumeration(Type):
    def __init__(self, name: str, ctype: str, gtype: GType):
        super().__init__(name, ctype)
        self.gtype = gtype
        self.members = []
        self.functions = []

    def set_members(self, members: T.List[EnumerationMember]) -> None:
        self.members.extend(members)

    def add_member(self, member: EnumerationMember) -> None:
        self.members.append(member)

    def add_function(self, function: Function) -> None:
        self.functions.append(function)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)


class ErrorDomain(Enumeration):
    def __init__(self, name: str, ctype: str, gtype: GType, domain: str):
        super().__init__(name, ctype, gtype)
        self.domain = domain


class Namespace:
    def __init__(self, name: str, version: str, identifier_prefix=None, symbol_prefix=None):
        self.name = name
        self.version = version
        self.identifier_prefix = identifier_prefix or self.name
        self.symbol_prefix = symbol_prefix or self.name.lower()
        self._shared_libraries = []

        self._aliases = []
        self._boxeds = []
        self._classes = []
        self._constants = []
        self._enumerations = []
        self._error_domains = []
        self._functions = []
        self._interfaces = []
        self._records = []
        self._unions = []

    def __str__(self):
        return f"{self.name}-{self.version}"

    def add_shared_libraries(self, libs: T.List[str]) -> None:
        self._shared_libraries.extend(libs)

    def get_shared_libraries(self) -> T.List[str]:
        return self._shared_libraries

    def add_alias(self, alias: Alias) -> None:
        self._aliases.append(alias)

    def add_enumeration(self, enum: Enumeration) -> None:
        self._enumerations.append(enum)

    def add_error_domain(self, domain: ErrorDomain) -> None:
        self._error_domains.append(domain)

    def add_class(self, cls: Class) -> None:
        self._classes.append(cls)

    def add_constant(self, constant: Constant) -> None:
        self._constants.append(constant)

    def add_interface(self, interface: Interface) -> None:
        self._interfaces.append(interface)

    def add_boxed(self, boxed: Boxed) -> None:
        self._boxeds.append(boxed)

    def add_record(self, record: Record) -> None:
        self._records.append(record)

    def add_union(self, union: Union) -> None:
        self._unions.append(union)

    def add_function(self, function: Function) -> None:
        self._functions.append(function)

    def get_classes(self) -> T.List[Class]:
        return self._classes

    def get_constants(self) -> T.List[Constant]:
        return self._constants

    def get_enumerations(self) -> T.List[Enumeration]:
        return self._enumerations

    def get_error_domains(self) -> T.List[ErrorDomain]:
        return self._error_domains

    def get_aliases(self) -> T.List[Alias]:
        return self._aliases

    def get_interfaces(self) -> T.List[Interface]:
        return self._interfaces

    def get_boxeds(self) -> T.List[Boxed]:
        return self._boxeds

    def get_records(self) -> T.List[Record]:
        return self._records

    def get_unions(self) -> T.List[Union]:
        return self._unions

    def get_functions(self) -> T.List[Function]:
        return self._functions


class Include:
    def __init__(self, name: str, version: str):
        self.name = name
        self.version = version

    def __str__(self):
        return f"{self.name}-{self.version}"

    def girfile(self) -> str:
        return f"{self.name}-{self.version}.gir"


class Repository:
    def __init__(self):
        self.includes = []
        self.packages = []
        self.c_includes = []
        self.namespaces = []

    def add_include(self, name: str, version: str) -> None:
        self.includes.append(Include(name, version))

    def add_package(self, name: str) -> None:
        self.package.append(name)

    def set_c_include(self, name: str) -> None:
        self.c_includes.append(name)

    def add_namespace(self, ns: Namespace) -> None:
        self.namespaces.append(ns)

    def get_includes(self) -> T.List[Include]:
        return self.includes

    def get_c_includes(self) -> T.List[str]:
        return self.c_includes

    def get_packages(self) -> T.List[str]:
        return self.packages

    def get_namespace(self) -> Namespace:
        return self.namespaces[0]
