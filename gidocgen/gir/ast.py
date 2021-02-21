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
    def __init__(self, introspectable: bool = True, deprecated: T.Optional[str] = None,
                 deprecated_version: T.Optional[str] = None, version: str = None,
                 stability: str = None):
        self.introspectable = introspectable
        self.deprecated_msg = deprecated
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
    def __init__(self, name: T.Optional[str] = None, namespace: T.Optional[str] = None):
        self.name = name
        self.namespace = namespace
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

    @property
    def source_position(self) -> T.Optional[T.Tuple[str, str]]:
        if self.info.source_position is None:
            return None
        return self.info.source_position.filename, self.info.source_position.line

    def set_deprecated(self, doc: T.Optional[str] = None, since_version: T.Optional[str] = None) -> None:
        """Set the deprecation annotations for the element"""
        self.info.deprecated_msg = doc
        self.info.deprecated_version = since_version

    def add_annotation(self, name: str, value: T.Optional[str] = None) -> None:
        """Add an annotation to the symbol"""
        self.info.add_annotation(Annotation(name, value))

    @property
    def annotations(self) -> T.List[T.Tuple[str, T.Optional[str]]]:
        return self.info.annotations

    @property
    def available_since(self) -> T.Optional[str]:
        return self.info.version

    @property
    def deprecated_since(self) -> T.Optional[T.Tuple[str, str]]:
        if not self.info.deprecated_msg:
            return None
        version = self.info.deprecated_version
        message = self.info.deprecated_msg
        if message is None:
            message = "Please do not use it in newly written code"
        return (version, message)


class Type(GIRElement):
    """Base class for all Type nodes"""
    def __init__(self, name: str, ctype: T.Optional[str] = None):
        super().__init__(name)
        self.ctype = ctype
        self.namespace = None
        if '.' in self.name:
            self.namespace = self.name.split('.')[0]

    def __eq__(self, other):
        if isinstance(other, Type):
            if self.namespace is not None:
                return self.namespace == other.namespace and self.name == self.name
            elif self.ctype is not None:
                return self.name == other.name and self.ctype == other.ctype
            else:
                return self.name == other.name
        elif isinstance(other, str):
            return self.name == other
        else:
            return False

    def __cmp__(self, other):
        if self.ctype is not None:
            return self.name == other.name and self.ctype == other.ctype
        return self.name == other.name

    def __repr__(self):
        return f"Type({self.name}, {self.ctype})"

    @property
    def base_ctype(self):
        if self.ctype is None:
            return None
        return self.ctype.replace('*', '')


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


class ListType(GIRElement):
    """Type class for List nodes"""
    def __init__(self, name: str, value_type: Type, ctype: str = None):
        super().__init__(name)
        self.ctype = ctype
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
    def __init__(self, name: str, identifier: T.Optional[str], throws: bool = False):
        super().__init__(name)
        self.identifier = identifier
        self.parameters: T.List[Parameter] = []
        self.return_value: T.Optional[ReturnValue] = None
        self.throws = throws

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
    def __init__(self, name: str, identifier: str, throws: bool = False):
        super().__init__(name, identifier, throws)


class Method(Callable):
    def __init__(self, name: str, identifier: str, instance_param: Parameter, throws: bool = False):
        super().__init__(name, identifier, throws)
        self.instance_param = instance_param

    def __contains__(self, param):
        if isinstance(param, Parameter) and param == self.instance_param:
            return True
        return super().__contains__(self, param)


class VirtualMethod(Callable):
    def __init__(self, name: str, identifier: str, invoker: str, instance_param: Parameter, throws: bool = False):
        super().__init__(name, identifier, throws)
        self.instance_param = instance_param
        self.invoker = invoker

    def __contains__(self, param):
        if isinstance(param, Parameter) and param == self.instance_param:
            return True
        return super().__contains__(self, param)


class Callback(Callable):
    def __init__(self, name: str, ctype: T.Optional[str], throws: bool = False):
        super().__init__(name=name, identifier=None, throws=throws)
        self.ctype = ctype


class Member(GIRElement):
    """A member in an enumeration, error domain, or bitfield"""
    def __init__(self, name: str, value: str, identifier: str, nick: str):
        super().__init__(name)
        self.value = value
        self.identifier = identifier
        self.nick = nick


class Enumeration(Type):
    """An enumeration type"""
    def __init__(self, name: str, ctype: str, gtype: T.Optional[GType]):
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
    def __init__(self, name: str, ctype: str, gtype: T.Optional[GType]):
        super().__init__(name, ctype, gtype)


class ErrorDomain(Enumeration):
    """An error domain for GError"""
    def __init__(self, name: str, ctype: str, gtype: T.Optional[GType], domain: str):
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
        self.detailed = detailed
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
        return self.ctype

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
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: GType, parent: T.Optional[Type] = None, abstract: bool = False,
                 fundamental: bool = False, ref_func: T.Optional[str] = None, unref_func: T.Optional[str] = None):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.parent = parent
        self.abstract = abstract
        self.fundamental = fundamental
        self.ref_func = ref_func
        self.unref_func = unref_func
        self.gtype = gtype
        self.ancestors: T.List[Type] = []
        self.implements: T.List[Type] = []
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
    def type_func(self) -> T.Optional[str]:
        if self.gtype is not None:
            return self.gtype.get_type
        return self.ctype

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

    def set_implements(self, ifaces: T.List[Type]) -> None:
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
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: T.Optional[GType] = None,
                 struct_for: T.Optional[str] = None, disguised: bool = False):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.struct_for = struct_for
        self.disguised = disguised
        self.constructors: T.List[Function] = []
        self.methods: T.List[Method] = []
        self.functions: T.List[Function] = []
        self.fields: T.List[Field] = []

    @property
    def type_struct(self) -> T.Optional[str]:
        if self.gtype is not None:
            return self.gtype.type_struct
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
    def __init__(self, name: str, ctype: str, symbol_prefix: str, gtype: T.Optional[GType]):
        super().__init__(name, ctype)
        self.symbol_prefix = symbol_prefix
        self.gtype = gtype
        self.constructors: T.List[Function] = []
        self.methods: T.List[Method] = []
        self.functions: T.List[Function] = []
        self.fields: T.List[Field] = []

    @property
    def type_struct(self) -> T.Optional[str]:
        if self.gtype is not None:
            return self.gtype.type_struct
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


class Namespace:
    def __init__(self, name: str, version: str, identifier_prefix: T.List[str] = [], symbol_prefix: T.List[str] = []):
        self.name = name
        self.version = version

        self._shared_libraries: T.List[str] = []

        self._aliases: T.Mapping[str, Alias] = {}
        self._bitfields: T.Mapping[str, BitField] = {}
        self._boxeds: T.Mapping[str, Boxed] = {}
        self._callbacks: T.List[Callback] = []
        self._classes: T.Mapping[str, Class] = {}
        self._constants: T.Mapping[str, Constant] = {}
        self._enumerations: T.Mapping[str, Enumeration] = {}
        self._error_domains: T.Mapping[str, ErrorDomain] = {}
        self._functions: T.Mapping[str, Function] = {}
        self._function_macros: T.Mapping[str, FunctionMacro] = {}
        self._interfaces: T.Mapping[str, Interface] = {}
        self._records: T.Mapping[str, Record] = {}
        self._unions: T.Mapping[str, Union] = {}

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
        self._aliases[alias.name] = alias

    def add_enumeration(self, enum: Enumeration) -> None:
        self._enumerations[enum.name] = enum

    def add_error_domain(self, domain: ErrorDomain) -> None:
        self._error_domains[domain.name] = domain

    def add_class(self, cls: Class) -> None:
        self._classes[cls.name] = cls

    def add_constant(self, constant: Constant) -> None:
        self._constants[constant.name] = constant

    def add_interface(self, interface: Interface) -> None:
        self._interfaces[interface.name] = interface

    def add_boxed(self, boxed: Boxed) -> None:
        self._boxeds[boxed.name] = boxed

    def add_record(self, record: Record) -> None:
        self._records[record.name] = record

    def add_union(self, union: Union) -> None:
        self._unions[union.name] = union

    def add_function(self, function: Function) -> None:
        self._functions[function.name] = function

    def add_bitfield(self, bitfield: BitField) -> None:
        self._bitfields[bitfield.name] = bitfield

    def add_function_macro(self, function: FunctionMacro) -> None:
        self._function_macros[function.name] = function

    def add_callback(self, callback: Callback) -> None:
        self._callbacks.append(callback)

    def get_classes(self) -> T.List[Class]:
        return self._classes.values()

    def get_constants(self) -> T.List[Constant]:
        return self._constants.values()

    def get_enumerations(self) -> T.List[Enumeration]:
        return self._enumerations.values()

    def get_error_domains(self) -> T.List[ErrorDomain]:
        return self._error_domains.values()

    def get_aliases(self) -> T.List[Alias]:
        return self._aliases.values()

    def get_interfaces(self) -> T.List[Interface]:
        return self._interfaces.values()

    def get_boxeds(self) -> T.List[Boxed]:
        return self._boxeds.values()

    def get_records(self) -> T.List[Record]:
        return self._records.values()

    def get_effective_records(self) -> T.List[Record]:
        def is_effective(r):
            if "Private" in r.name and r.disguised:
                return False
            if r.struct_for is not None:
                return False
            return True

        return [x for x in self._records.values() if is_effective(x)]

    def get_unions(self) -> T.List[Union]:
        return self._unions.values()

    def get_functions(self) -> T.List[Function]:
        return self._functions.values()

    def get_bitfields(self) -> T.List[BitField]:
        return self._bitfields.values()

    def get_function_macros(self) -> T.List[FunctionMacro]:
        return self._function_macros.values()

    def get_callbacks(self) -> T.List[Callback]:
        return self._callbacks

    def find_class(self, cls: str) -> T.Optional[Class]:
        return self._classes.get(cls)

    def find_record(self, record: str) -> T.Optional[Record]:
        return self._records.get(record)

    def find_interface(self, iface: str) -> T.Optional[Interface]:
        return self._interfaces.get(iface)

    def find_function(self, func: str) -> T.Optional[Function]:
        return self._functions.get(func)

    def find_real_type(self, name: str) -> T.Optional[Type]:
        if name in self._aliases:
            return self._aliases[name]
        if name in self._bitfields:
            return self._bitfields[name]
        if name in self._enumerations:
            return self._enumerations[name]
        if name in self._error_domains:
            return self._error_domains[name]
        if name in self._classes:
            return self._classes[name]
        if name in self._interfaces:
            return self._interfaces[name]
        if name in self._records:
            return self._records[name]
        if name in self._unions:
            return self._unions[name]
        return None

    def find_symbol(self, name: str) -> T.Optional[Type]:
        return self._symbols.get(name)


class Repository:
    def __init__(self):
        self.includes: T.Mapping[str, Repository] = {}
        self.packages: T.List[Package] = []
        self.c_includes: T.List[CInclude] = []
        self.types: T.Mapping[str, Type] = {}
        self._namespaces: T.List[Namespace] = []
        self.girfile: T.Optional[str] = None

    def add_namespace(self, ns: Namespace) -> None:
        self._namespaces.append(ns)

    def resolve_empty_ctypes(self):
        def find_real_type(includes, ns, name):
            for repo in self.includes.values():
                if repo.namespace.name != name:
                    continue
                real_type = repo.namespace.find_real_type(name)
                if real_type is not None:
                    return real_type
            return None

        for t in self.types.values():
            if t.ctype is not None:
                continue
            real_type = None
            if '.' in t.name:
                ns, name = t.name.split('.')
                if ns == self.namespace.name:
                    real_type = self.namespace.find_real_type(name)
                else:
                    real_type = find_real_type(self.includes, ns, name)
            else:
                pass
            if real_type is not None:
                t.ctype = real_type.ctype

    def resolve_class_ancestors(self):
        def find_parent_class(includes, ns, name):
            for repo in self.includes.values():
                if repo.namespace.name != name:
                    continue
                parent = repo.namespace.find_class(name)
                if parent is not None:
                    return parent
            return None

        classes = self.namespace.get_classes()
        for cls in classes:
            if cls.parent is None:
                continue
            ancestors = []
            parent = cls.parent
            while parent is not None:
                ancestors.append(parent)
                if '.' in parent.name:
                    ns, name = parent.name.split('.')
                    if ns == self.namespace.name:
                        parent = self.namespace.find_class(name)
                    else:
                        parent = find_parent_class(self.includes, ns, name)
                else:
                    parent = self.namespace.find_class(parent.name)
                if parent is not None:
                    parent = parent.parent
            cls.ancestors = ancestors
            cls.parent = ancestors[0]

    def resolve_symbols(self):
        symbols: T.Mapping[str, Type] = {}
        for func in self.namespace.get_functions():
            symbols[func.identifier] = func
        for cls in self.namespace.get_classes():
            for m in cls.methods:
                symbols[m.identifier] = cls
        for iface in self.namespace.get_interfaces():
            for m in iface.methods:
                symbols[m.identifier] = iface
        for record in self.namespace.get_records():
            for m in record.methods:
                symbols[m.identifier] = record
        for union in self.namespace.get_unions():
            for m in union.methods:
                symbols[m.identifier] = record
        self.namespace._symbols = symbols

    @property
    def namespace(self) -> T.Optional[Namespace]:
        return self._namespaces[0]

    def find_type(self, name: str) -> T.Optional[Type]:
        for (fqtn, ctype) in self._types.keys():
            if fqtn == name:
                return self._types.get((fqtn, ctype))
            return None
