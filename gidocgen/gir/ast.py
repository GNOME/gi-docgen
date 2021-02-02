# SPDX-FileCopyrightText: 2020 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import typing as T


class Doc:
    """A documentation node, pointing to the source code"""
    def __init__(self, content: str, filename: str, line: int, version: str = None, stability: str = None):
        self.content = content
        self.filename = filename
        self.line = line
        self.version = version
        self.stability = stability

    def __str__(self):
        return self.content


class SourcePosition:
    """A location inside the source code"""
    def __init__(self, filename: str, line: int):
        self.filename = filename
        self.line = line

    def __str__(self):
        return f'{self.filename}:{self.line}'


class Annotation:
    """A user-defined annotation"""
    def __init__(self, name: str, value: T.Optional[str]):
        self.name = name
        self.value = value


class CInclude:
    """A C include header"""
    def __init__(self, name: str):
        self.name = name


class Include:
    """A GIR include"""
    def __init__(self, name: str, version: str = None):
        self.name = name
        self.version = version

    def __str__(self):
        if self.version is not None:
            return f"{self.name}-{self.version}"
        return f"{self.name}"

    def girfile(self) -> str:
        if self.version is not None:
            return f"{self.name}-{self.version}.gir"
        return f"{self.name}.gir"


class Package:
    """Pkg-config containing the library"""
    def __init__(self, name: str):
        self.name = name


class Info:
    """Base information for most types"""
    def __init__(self, introspectable: bool = True, deprecated: str = None, deprecated_version: str = None,
                 version: str = None, stability: str = None):
        self.introspectable = introspectable
        self.deprecated = deprecated
        self.deprecated_version = deprecated_version
        self.version = version
        self.stability = stability
        self.annotations: T.List[Annotation] = []
        self.doc: T.Optional[Doc] = None
        self.source_position: T.Optional[SourcePosition] = None

    def add_annotation(self, annotation: Annotation) -> None:
        self.annotations.append(annotation)


class GIRElement:
    """Base type for elements inside the GIR"""
    def __init__(self, name: str = None):
        self.name = name
        self.info = Info()

    def set_introspectable(self, introspectable: bool) -> None:
        """Set whether the symbol is introspectable"""
        self.info.introspectable = introspectable

    @property
    def introspectable(self):
        return self.info.introspectable

    def set_version(self, version: str) -> None:
        """Set the version of the symbol"""
        self.info.version = version

    def set_stability(self, stability: str) -> None:
        """Set the stability of the symbol"""
        self.info.stability = stability

    @property
    def stability(self):
        return self.info.stability

    def set_doc(self, doc: Doc) -> None:
        """Set the documentation for the element"""
        self.info.doc = doc

    @property
    def doc(self):
        return self.info.doc

    def set_source_position(self, pos: SourcePosition) -> None:
        """Set the position in the source code for the element"""
        self.info.source_position = pos

    def set_deprecated(self, doc: str = None, since_version: str = None) -> None:
        """Set the deprecation annotations for the element"""
        self.info.deprecated = doc
        self.info.deprecated_version = since_version

    def add_annotation(self, name: str, value: T.Optional[str] = None) -> None:
        """Add an annotation to the symbol"""
        self.info.add_annotation(Annotation(name, value))


class Type(GIRElement):
    """Base class for all Type nodes"""
    def __init__(self, name: str, ctype: str = None):
        super().__init__(name)
        self.ctype = ctype

    def __eq__(self, other):
        if isinstance(other, Type):
            return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        else:
            return False

    def __cmp__(self, other):
        return self.name == other.name

    def __repr__(self):
        return f"Type({self.name}, {self.ctype})"


class ArrayType(GIRElement):
    """Base class for Array nodes"""
    def __init__(self, name: str, value_type: Type, ctype: str = None, zero_terminated: bool = False,
                 fixed_size: int = -1, length: int = -1):
        super().__init__(name)
        self.ctype = ctype
        self.zero_terminated = zero_terminated
        self.fixed_size = fixed_size
        self.length = length
        self.value_type = value_type


class GType:
    """Base class for GType information"""
    def __init__(self, type_name: str, get_type: str, type_struct: T.Optional[str] = None):
        self.type_name = type_name
        self.get_type = get_type
        self.type_struct = type_struct


class VoidType(Type):
    def __init__(self):
        super().__init__(name='none', ctype='void')

    def __str__(self):
        return "void"


class VarArgs(Type):
    def __init__(self):
        super().__init__(name='none', ctype='')

    def __str__(self):
        return "..."


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
    def __init__(self, name: str, direction: str, transfer: str, target: Type = None, caller_allocates: bool = False,
                 optional: bool = False, nullable: bool = False, closure: int = -1, destroy: int = -1,
                 scope: str = None):
        super().__init__(name)
        self.direction = direction
        self.transfer = transfer
        self.caller_allocates = caller_allocates
        self.optional = optional
        self.nullable = nullable
        self.scope = scope
        self.closure = closure
        self.destroy = destroy
        if target is None:
            self.target: Type = VoidType()
        else:
            self.target = target


class ReturnValue(GIRElement):
    """A callable's return value"""
    def __init__(self, transfer: str, target: Type, nullable: bool = False, closure: int = -1, destroy: int = -1, scope: str = None):
        super().__init__()
        self.transfer = transfer
        self.nullable = nullable
        self.scope = scope
        self.closure = closure
        self.destroy = destroy
        if target is None:
            self.target: Type = VoidType()
        else:
            self.target = target


class Callable(GIRElement):
    """A callable symbol: function, method, function-macro, ..."""
    def __init__(self, name: str, identifier: T.Optional[str]):
        super().__init__(name)
        self.identifier = identifier
        self.parameters: T.List[Parameter] = []
        self.return_value: T.Optional[ReturnValue] = None

    def add_parameter(self, param: Parameter) -> None:
        self.parameters.append(param)

    def set_parameters(self, params: T.List[Parameter]) -> None:
        self.parameters.extend(params)

    def set_return_value(self, res: ReturnValue) -> None:
        self.return_value = res

    def __contains__(self, param):
        if isinstance(param, str):
            for p in self.parameters:
                if p.name == param:
                    return True
        elif isinstance(param, Parameter):
            return param in self.parameters
        elif isinstance(param, ReturnValue):
            return param == self.return_value
        return False


class FunctionMacro(Callable):
    def __init__(self, name: str, identifier: str):
        super().__init__(name, identifier)


class Function(Callable):
    def __init__(self, name: str, identifier: str):
        super().__init__(name, identifier)


class Method(Callable):
    def __init__(self, name: str, identifier: str, instance_param: Parameter):
        super().__init__(name, identifier)
        self.instance_param = instance_param

    def __contains__(self, param):
        if isinstance(param, Parameter) and param == self.instance_param:
            return True
        return super().__contains__(self, param)


class VirtualMethod(Callable):
    def __init__(self, name: str, identifier: str, invoker: str, instance_param: Parameter):
        super().__init__(name, identifier)
        self.instance_param = instance_param
        self.invoker = invoker

    def __contains__(self, param):
        if isinstance(param, Parameter) and param == self.instance_param:
            return True
        return super().__contains__(self, param)


class Callback(Callable):
    def __init__(self, name: str, ctype: str, throws: bool):
        super().__init__(name, None)
        self.ctype = ctype
        self.throws = throws


class Member(GIRElement):
    """A member in an enumeration, error domain, or bitfield"""
    def __init__(self, name: str, value: str, identifier: str, nick: str):
        super().__init__(name)
        self.value = value
        self.identifier = identifier
        self.nick = nick


class Enumeration(Type):
    """An enumeration type"""
    def __init__(self, name: str, ctype: str, gtype: GType):
        super().__init__(name, ctype)
        self.gtype = gtype
        self.members: T.List[Member] = []
        self.functions: T.List[Function] = []

    def add_member(self, member: Member) -> None:
        self.members.append(member)

    def add_function(self, function: Function) -> None:
        self.functions.append(function)

    def set_members(self, members: T.List[Member]) -> None:
        self.members.extend(members)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)

    def __contains__(self, member):
        if isinstance(member, Member):
            return member in self.members
        return False

    def __iter__(self):
        for member in self.members:
            yield member


class BitField(Enumeration):
    """An enumeration type of bit masks"""
    def __init__(self, name: str, ctype: str, gtype: GType):
        super().__init__(name, ctype, gtype)


class ErrorDomain(Enumeration):
    """An error domain for GError"""
    def __init__(self, name: str, ctype: str, gtype: GType, domain: str):
        super().__init__(name, ctype, gtype)
        self.domain = domain


class Property(GIRElement):
    def __init__(self, name: str, transfer: str, target: Type, writable: bool = True, readable: bool = True, construct: bool = False,
                 construct_only: bool = False):
        super().__init__(name)
        self.transfer = transfer
        self.writable = writable
        self.readable = readable
        self.construct = construct
        self.construct_only = construct_only
        self.target = target


class Signal(GIRElement):
    def __init__(self, name: str, detailed: bool, when: str, action: bool = False, no_hooks: bool = False, no_recurse: bool = False):
        super().__init__(name)
        self.when = when
        self.action = action
        self.no_hooks = no_hooks
        self.no_recurse = no_recurse
        self.parameters: T.List[Parameter] = []
        self.return_value: T.Optional[ReturnValue] = None

    def set_parameters(self, params: T.List[Parameter]) -> None:
        self.parameters.extend(params)

    def set_return_value(self, res: ReturnValue) -> None:
        self.return_value = res


class Field(GIRElement):
    """A field in a struct or union"""
    def __init__(self, name: str, target: Type, writable: bool, readable: bool, private: bool = False, bits: int = 0):
        super().__init__(name)
        self.target = target
        self.writable = writable
        self.readable = readable
        self.private = private
        self.bits = bits


class Interface(Type):
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.methods: T.List[Method] = []
        self.virtual_methods: T.List[VirtualMethod] = []
        self.properties: T.List[Property] = []
        self.signals: T.List[Signal] = []
        self.functions: T.List[Function] = []
        self.fields: T.List[Field] = []
        self.prerequisite: T.Optional[str] = None

    @property
    def type_struct(self) -> T.Optional[str]:
        if self.gtype is not None:
            return self.gtype.type_struct
        return None

    @property
    def type_func(self) -> str:
        return self.gtype.get_type

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_virtual_methods(self, methods: T.List[VirtualMethod]) -> None:
        self.virtual_methods.extend(methods)

    def set_properties(self, properties: T.List[Property]) -> None:
        self.properties.extend(properties)

    def set_signals(self, signals: T.List[Signal]) -> None:
        self.signals.extend(signals)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)

    def set_fields(self, fields: T.List[Field]) -> None:
        self.fields.extend(fields)

    def set_prerequisite(self, prerequisite: str) -> None:
        self.prerequisite = prerequisite


class Class(Type):
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType, parent: str = 'GObject.Object', abstract: bool = False):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.parent = parent
        self.abstract = abstract
        self.gtype = gtype
        self.implements: T.List[str] = []
        self.constructors: T.List[Function] = []
        self.methods: T.List[Method] = []
        self.virtual_methods: T.List[VirtualMethod] = []
        self.properties: T.List[Property] = []
        self.signals: T.List[Signal] = []
        self.functions: T.List[Function] = []
        self.fields: T.List[Field] = []
        self.callbacks: T.List[Callback] = []

    @property
    def type_struct(self) -> T.Optional[str]:
        if self.gtype is not None:
            return self.gtype.type_struct
        return None

    @property
    def type_func(self) -> str:
        return self.gtype.get_type

    def set_constructors(self, ctors: T.List[Function]) -> None:
        self.constructors.extend(ctors)

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_virtual_methods(self, methods: T.List[VirtualMethod]) -> None:
        self.virtual_methods.extend(methods)

    def set_properties(self, properties: T.List[Property]) -> None:
        self.properties.extend(properties)

    def set_signals(self, signals: T.List[Signal]) -> None:
        self.signals.extend(signals)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)

    def set_implements(self, ifaces: T.List[str]) -> None:
        self.implements.extend(ifaces)

    def set_fields(self, fields: T.List[Field]) -> None:
        self.fields.extend(fields)


class Boxed(Type):
    def __init__(self, name: str, symbol_prefix: str, gtype: GType):
        super().__init__(name, None)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.functions: T.List[Function] = []

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)


class Record(Type):
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.constructors: T.List[Function] = []
        self.methods: T.List[Method] = []
        self.functions: T.List[Function] = []
        self.fields: T.List[Field] = []

    @property
    def type_struct(self) -> T.Optional[str]:
        return self.ctype

    @property
    def type_func(self) -> T.Optional[str]:
        if self.gtype is not None:
            return self.gtype.get_type
        return None

    def set_constructors(self, ctors: T.List[Function]) -> None:
        self.constructors.extend(ctors)

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)

    def set_fields(self, fields: T.List[Field]) -> None:
        self.fields.extend(fields)


class Union(Type):
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.constructors: T.List[Function] = []
        self.methods: T.List[Method] = []
        self.functions: T.List[Function] = []
        self.fields: T.List[Field] = []

    def set_constructors(self, ctors: T.List[Function]) -> None:
        self.constructors.extend(ctors)

    def set_methods(self, methods: T.List[Method]) -> None:
        self.methods.extend(methods)

    def set_functions(self, functions: T.List[Function]) -> None:
        self.functions.extend(functions)

    def set_fields(self, fields: T.List[Field]) -> None:
        self.fields.extend(fields)


class Namespace:
    def __init__(self, name: str, version: str, identifier_prefix: T.List[str] = [], symbol_prefix: T.List[str] = []):
        self.name = name
        self.version = version

        self._shared_libraries: T.List[str] = []

        self._aliases: T.List[Alias] = []
        self._bitfields: T.List[BitField] = []
        self._boxeds: T.List[Boxed] = []
        self._classes: T.List[Class] = []
        self._constants: T.List[Constant] = []
        self._enumerations: T.List[Enumeration] = []
        self._error_domains: T.List[ErrorDomain] = []
        self._functions: T.List[Function] = []
        self._function_macros: T.List[FunctionMacro] = []
        self._interfaces: T.List[Interface] = []
        self._records: T.List[Record] = []
        self._unions: T.List[Union] = []

        if identifier_prefix:
            self.identifier_prefix = identifier_prefix
        else:
            self.identifier_prefix = [self.name]
        if symbol_prefix:
            self.symbol_prefix = symbol_prefix
        else:
            self.symbol_prefix = [self.name.lower()]

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

    def add_bitfield(self, bitfield: BitField) -> None:
        self._bitfields.append(bitfield)

    def add_function_macro(self, function: FunctionMacro) -> None:
        self._function_macros.append(function)

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

    def get_bitfields(self) -> T.List[BitField]:
        return self._bitfields

    def get_function_macros(self) -> T.List[FunctionMacro]:
        return self._function_macros

    def find_record(self, record: str) -> T.Optional[Record]:
        for r in self._records:
            if r.name == record:
                return r
        return None

    def find_interface(self, iface: str) -> T.Optional[Interface]:
        for i in self._interfaces:
            if i.name == iface:
                return i
        return None


class Repository:
    def __init__(self):
        self.includes: T.List[Repository] = []
        self.packages: T.List[Package] = []
        self.c_includes: T.List[CInclude] = []
        self._namespaces: T.List[Namespace] = []

    def add_namespace(self, ns: Namespace) -> None:
        self._namespaces.append(ns)

    @property
    def namespace(self) -> T.Optional[Namespace]:
        return self._namespaces[0]
