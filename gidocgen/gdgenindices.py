# SPDX-FileCopyrightText: 2020 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import argparse
import json
import os
import sys

from . import config, core, gir, log, utils


HELP_MSG = "Generates the symbol indices for search"

MISSING_DESCRIPTION = "No description available."


def _gen_aliases(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for alias in symbols:
        if config.is_hidden(alias.name):
            log.debug(f"Skipping hidden type {alias.name}")
            continue
        if alias.doc is not None:
            description = alias.doc.content
        else:
            description = MISSING_DESCRIPTION
        if alias.deprecated:
            (deprecated, _) = alias.deprecated_since
        else:
            deprecated = None
        index_symbols.append({
            "type": "alias",
            "name": alias.name,
            "ctype": alias.base_ctype,
            "summary": utils.preprocess_docs(description, repository.namespace, summary=True, plain=True),
            "deprecated": deprecated,
        })


def _gen_bitfields(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for bitfield in symbols:
        if config.is_hidden(bitfield.name):
            log.debug(f"Skipping hidden type {bitfield.name}")
            continue
        if bitfield.doc is not None:
            description = bitfield.doc.content
        else:
            description = MISSING_DESCRIPTION
        if bitfield.deprecated:
            (deprecated, _) = bitfield.deprecated_since
        else:
            deprecated = None
        index_symbols.append({
            "type": "bitfield",
            "name": bitfield.name,
            "ctype": bitfield.base_ctype,
            "summary": utils.preprocess_docs(description, repository.namespace, summary=True, plain=True),
            "deprecated": deprecated,
        })

        for func in bitfield.functions:
            if func.doc is not None:
                func_desc = func.doc.content
            else:
                func_desc = MISSING_DESCRIPTION
            if func.deprecated:
                (func_deprecated, _) = func.deprecated_since
            else:
                func_deprecated = None
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": bitfield.name,
                "ident": func.identifier,
                "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
                "deprecated": func_deprecated,
            })


def _gen_callbacks(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for callback in symbols:
        if config.is_hidden(callback.name):
            log.debug(f"Skipping hidden callback {callback.name}")
            continue
        if callback.doc is not None:
            cb_desc = callback.doc.content
        else:
            cb_desc = MISSING_DESCRIPTION
        if callback.deprecated:
            (cb_deprecated, _) = callback.deprecated_since
        else:
            cb_deprecated = None
        index_symbols.append({
            "type": "callback",
            "name": callback.name,
            "ctype": callback.base_ctype,
            "summary": utils.preprocess_docs(cb_desc, repository.namespace, summary=True, plain=True),
            "deprecated": cb_deprecated,
        })


def _gen_classes(config, index, repository, symbols):
    namespace = repository.namespace
    index_symbols = index["symbols"]

    for cls in symbols:
        if config.is_hidden(cls.name):
            log.debug(f"Skipping hidden type {cls.name}")
            continue
        if cls.doc is not None:
            cls_desc = cls.doc.content
        else:
            cls_desc = MISSING_DESCRIPTION
        if cls.deprecated:
            (cls_deprecated, _) = cls.deprecated_since
        else:
            cls_deprecated = None
        index_symbols.append({
            "type": "class",
            "name": cls.name,
            "ctype": cls.base_ctype,
            "summary": utils.preprocess_docs(cls_desc, repository.namespace, summary=True, plain=True),
            "deprecated": cls_deprecated,
        })

        for ctor in cls.constructors:
            if ctor.doc is not None:
                ctor_desc = ctor.doc.content
            else:
                ctor_desc = MISSING_DESCRIPTION
            if ctor.deprecated:
                (ctor_deprecated, _) = ctor.deprecated_since
            else:
                ctor_deprecated = None
            index_symbols.append({
                "type": "ctor",
                "name": ctor.name,
                "type_name": cls.name,
                "ident": ctor.identifier,
                "summary": utils.preprocess_docs(ctor_desc, repository.namespace, summary=True, plain=True),
                "deprecated": ctor_deprecated,
            })

        for method in cls.methods:
            if method.doc is not None:
                method_desc = method.doc.content
            else:
                method_desc = MISSING_DESCRIPTION
            if method.deprecated:
                (method_deprecated, _) = method.deprecated_since
            else:
                method_deprecated = None
            index_symbols.append({
                "type": "method",
                "name": method.name,
                "type_name": cls.name,
                "ident": method.identifier,
                "summary": utils.preprocess_docs(method_desc, repository.namespace, summary=True, plain=True),
                "deprecated": method_deprecated,
            })

        for func in cls.functions:
            if func.doc is not None:
                func_desc = func.doc.content
            else:
                func_desc = MISSING_DESCRIPTION
            if func.deprecated:
                (func_deprecated, _) = func.deprecated_since
            else:
                func_deprecated = None
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": cls.name,
                "ident": func.identifier,
                "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
                "deprecated": func_deprecated,
            })

        for prop_name, prop in cls.properties.items():
            if config.is_hidden(cls.name, 'property', prop_name):
                log.debug(f"Skipping hidden property {cls.name}.{prop_name}")
                continue
            if prop.doc is not None:
                prop_desc = prop.doc.content
            else:
                prop_desc = MISSING_DESCRIPTION
            if prop.deprecated:
                (prop_deprecated, _) = prop.deprecated_since
            else:
                prop_deprecated = None
            index_symbols.append({
                "type": "property",
                "name": prop.name,
                "type_name": cls.name,
                "summary": utils.preprocess_docs(prop_desc, repository.namespace, summary=True, plain=True),
                "deprecated": prop_deprecated,
            })

        for signal_name, signal in cls.signals.items():
            if config.is_hidden(cls.name, 'signal', signal_name):
                log.debug(f"Skipping hidden signal {cls.name}.{signal_name}")
                continue
            if signal.doc is not None:
                signal_desc = signal.doc.content
            else:
                signal_desc = MISSING_DESCRIPTION
            if signal.deprecated:
                (signal_deprecated, _) = signal.deprecated_since
            else:
                signal_deprecated = None
            index_symbols.append({
                "type": "signal",
                "name": signal.name,
                "type_name": cls.name,
                "summary": utils.preprocess_docs(signal_desc, repository.namespace, summary=True, plain=True),
                "deprecated": signal_deprecated,
            })

        for vfunc in cls.virtual_methods:
            if vfunc.doc is not None:
                vfunc_desc = vfunc.doc.content
            else:
                vfunc_desc = MISSING_DESCRIPTION
            if vfunc.deprecated:
                (vfunc_deprecated, _) = vfunc.deprecated_since
            else:
                vfunc_deprecated = None
            index_symbols.append({
                "type": "vfunc",
                "name": vfunc.name,
                "type_name": cls.name,
                "summary": utils.preprocess_docs(vfunc_desc, repository.namespace, summary=True, plain=True),
                "deprecated": vfunc_deprecated,
            })

        if cls.type_struct is not None:
            cls_struct = namespace.find_record(cls.type_struct)
            for cls_method in cls_struct.methods:
                if cls_method.doc is not None:
                    cls_method_desc = cls_method.doc.content
                else:
                    cls_method_desc = MISSING_DESCRIPTION
                if cls_method.deprecated:
                    (method_deprecated, _) = cls_method.deprecated_since
                else:
                    method_deprecated = None
                index_symbols.append({
                    "type": "class_method",
                    "name": cls_method.name,
                    "type_name": cls_struct.name,
                    "struct_for": cls_struct.struct_for,
                    "ident": cls_method.identifier,
                    "summary": utils.preprocess_docs(cls_method_desc, repository.namespace, summary=True, plain=True),
                    "deprecated": method_deprecated,
                })


def _gen_constants(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for const in symbols:
        if config.is_hidden(const.name):
            log.debug(f"Skipping hidden const {const.name}")
            continue
        if const.doc is not None:
            const_desc = const.doc.content
        else:
            const_desc = MISSING_DESCRIPTION
        if const.deprecated:
            (const_deprecated, _) = const.deprecated_since
        else:
            const_deprecated = None
        index_symbols.append({
            "type": "constant",
            "name": const.name,
            "ident": const.ctype,
            "summary": utils.preprocess_docs(const_desc, repository.namespace, summary=True, plain=True),
            "deprecated": const_deprecated,
        })


def _gen_domains(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for domain in symbols:
        if config.is_hidden(domain.name):
            log.debug(f"Skipping hidden type {domain.name}")
            continue
        if domain.doc is not None:
            domain_desc = domain.doc.content
        else:
            domain_desc = MISSING_DESCRIPTION
        if domain.deprecated:
            (domain_deprecated, _) = domain.deprecated_since
        else:
            domain_deprecated = None
        index_symbols.append({
            "type": "domain",
            "name": domain.name,
            "ctype": domain.base_ctype,
            "summary": utils.preprocess_docs(domain_desc, repository.namespace, summary=True, plain=True),
            "deprecated": domain_deprecated,
        })

        for func in domain.functions:
            if func.doc is not None:
                func_desc = func.doc.content
            else:
                func_desc = MISSING_DESCRIPTION
            if func.deprecated:
                (func_deprecated, _) = func.deprecated_since
            else:
                func_deprecated = None
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": domain.name,
                "ident": func.identifier,
                "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
                "deprecated": func_deprecated,
            })


def _gen_enums(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for enum in symbols:
        if config.is_hidden(enum.name):
            log.debug(f"Skipping hidden type {enum.name}")
            continue
        if enum.doc is not None:
            enum_desc = enum.doc.content
        else:
            enum_desc = MISSING_DESCRIPTION
        if enum.deprecated:
            (enum_deprecated, _) = enum.deprecated_since
        else:
            enum_deprecated = None
        index_symbols.append({
            "type": "enum",
            "name": enum.name,
            "ctype": enum.base_ctype,
            "summary": utils.preprocess_docs(enum_desc, repository.namespace, summary=True, plain=True),
            "deprecated": enum_deprecated,
        })

        for func in enum.functions:
            if func.doc is not None:
                func_desc = func.doc.content
            else:
                func_desc = MISSING_DESCRIPTION
            if func.deprecated:
                (func_deprecated, _) = func.deprecated_since
            else:
                func_deprecated = None
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": enum.name,
                "ident": func.identifier,
                "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
                "deprecated": func_deprecated,
            })


def _gen_functions(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for func in symbols:
        if config.is_hidden(func.name):
            log.debug(f"Skipping hidden function {func.name}")
            continue
        if func.doc is not None:
            func_desc = func.doc.content
        else:
            func_desc = MISSING_DESCRIPTION
        if func.deprecated:
            (func_deprecated, _) = func.deprecated_since
        else:
            func_deprecated = None
        index_symbols.append({
            "type": "function",
            "name": func.name,
            "ident": func.identifier,
            "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
            "deprecated": func_deprecated,
        })


def _gen_function_macros(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for func in symbols:
        if config.is_hidden(func.name):
            log.debug(f"Skipping hidden macro {func.name}")
            continue
        if func.doc is not None:
            func_desc = func.doc.content
        else:
            func_desc = MISSING_DESCRIPTION
        if func.deprecated:
            (func_deprecated, _) = func.deprecated_since
        else:
            func_deprecated = None
        index_symbols.append({
            "type": "function_macro",
            "name": func.name,
            "ident": func.identifier,
            "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
            "deprecated": func_deprecated,
        })


def _gen_interfaces(config, index, repository, symbols):
    namespace = repository.namespace
    index_symbols = index["symbols"]

    for iface in symbols:
        if config.is_hidden(iface.name):
            log.debug(f"Skipping hidden type {iface.name}")
            continue
        if iface.doc is not None:
            iface_desc = iface.doc.content
        else:
            iface_desc = MISSING_DESCRIPTION
        if iface.deprecated:
            (iface_deprecated, _) = iface.deprecated_since
        else:
            iface_deprecated = None
        index_symbols.append({
            "type": "interface",
            "name": iface.name,
            "ctype": iface.base_ctype,
            "summary": utils.preprocess_docs(iface_desc, repository.namespace, summary=True, plain=True),
            "deprecated": iface_deprecated,
        })

        for method in iface.methods:
            if method.doc is not None:
                method_desc = method.doc.content
            else:
                method_desc = MISSING_DESCRIPTION
            if method.deprecated:
                (method_deprecated, _) = method.deprecated_since
            else:
                method_deprecated = None
            index_symbols.append({
                "type": "method",
                "name": method.name,
                "type_name": iface.name,
                "ident": method.identifier,
                "summary": utils.preprocess_docs(method_desc, repository.namespace, summary=True, plain=True),
                "deprecated": method_deprecated,
            })

        for func in iface.functions:
            if func.doc is not None:
                func_desc = func.doc.content
            else:
                func_desc = MISSING_DESCRIPTION
            if func.deprecated:
                (func_deprecated, _) = func.deprecated_since
            else:
                func_deprecated = None
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": iface.name,
                "ident": func.identifier,
                "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
                "deprecated": func_deprecated,
            })

        for prop_name, prop in iface.properties.items():
            if config.is_hidden(iface.name, 'property', prop_name):
                log.debug(f"Skipping hidden property {iface.name}.{prop_name}")
                continue
            if prop.doc is not None:
                prop_desc = prop.doc.content
            else:
                prop_desc = MISSING_DESCRIPTION
            if prop.deprecated:
                (prop_deprecated, _) = prop.deprecated_since
            else:
                prop_deprecated = None
            index_symbols.append({
                "type": "property",
                "name": prop.name,
                "type_name": iface.name,
                "summary": utils.preprocess_docs(prop_desc, repository.namespace, summary=True, plain=True),
                "deprecated": prop_deprecated,
            })

        for signal_name, signal in iface.signals.items():
            if config.is_hidden(iface.name, 'signal', signal_name):
                log.debug(f"Skipping hidden signal {iface.name}.{signal_name}")
                continue
            if signal.doc is not None:
                signal_desc = signal.doc.content
            else:
                signal_desc = MISSING_DESCRIPTION
            if signal.deprecated:
                (signal_deprecated, _) = signal.deprecated_since
            else:
                signal_deprecated = None
            index_symbols.append({
                "type": "signal",
                "name": signal.name,
                "type_name": iface.name,
                "summary": utils.preprocess_docs(signal_desc, repository.namespace, summary=True, plain=True),
                "deprecated": signal_deprecated,
            })

        for vfunc in iface.virtual_methods:
            if vfunc.doc is not None:
                vfunc_desc = vfunc.doc.content
            else:
                vfunc_desc = MISSING_DESCRIPTION
            if vfunc.deprecated:
                (vfunc_deprecated, _) = vfunc.deprecated_since
            else:
                vfunc_deprecated = None
            index_symbols.append({
                "type": "vfunc",
                "name": vfunc.name,
                "type_name": iface.name,
                "summary": utils.preprocess_docs(vfunc_desc, repository.namespace, summary=True, plain=True),
                "deprecated": vfunc_deprecated,
            })

        if iface.type_struct is not None:
            iface_struct = namespace.find_record(iface.type_struct)
            for iface_method in iface_struct.methods:
                if iface_method.doc is not None:
                    iface_method_desc = iface_method.doc.content
                else:
                    iface_method_desc = MISSING_DESCRIPTION
                if iface_method.deprecated:
                    (method_deprecated, _) = iface_method.deprecated_since
                else:
                    method_deprecated = None
                index_symbols.append({
                    "type": "class_method",
                    "name": iface_method.name,
                    "type_name": iface_struct.name,
                    "struct_for": iface_struct.struct_for,
                    "ident": iface_method.identifier,
                    "summary": utils.preprocess_docs(iface_method_desc, repository.namespace, summary=True, plain=True),
                    "deprecated": method_deprecated,
                })


def _gen_records(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for record in symbols:
        if config.is_hidden(record.name):
            log.debug(f"Skipping hidden type {record.name}")
            continue
        if record.doc is not None:
            desc = record.doc.content
        else:
            desc = MISSING_DESCRIPTION
        if record.deprecated:
            (deprecated, _) = record.deprecated_since
        else:
            deprecated = None
        index_symbols.append({
            "type": "record",
            "name": record.name,
            "ctype": record.base_ctype,
            "summary": utils.preprocess_docs(desc, repository.namespace, summary=True, plain=True),
            "deprecated": deprecated,
        })

        for ctor in record.constructors:
            if ctor.doc is not None:
                ctor_desc = ctor.doc.content
            else:
                ctor_desc = MISSING_DESCRIPTION
            if ctor.deprecated:
                (ctor_deprecated, _) = ctor.deprecated_since
            else:
                ctor_deprecated = None
            index_symbols.append({
                "type": "ctor",
                "name": ctor.name,
                "type_name": record.name,
                "ident": ctor.identifier,
                "summary": utils.preprocess_docs(ctor_desc, repository.namespace, summary=True, plain=True),
                "deprecated": ctor_deprecated,
            })

        for method in record.methods:
            if method.doc is not None:
                method_desc = method.doc.content
            else:
                method_desc = MISSING_DESCRIPTION
            index_symbols.append({
                "type": "method",
                "name": method.name,
                "type_name": record.name,
                "ident": method.identifier,
                "summary": utils.preprocess_docs(method_desc, repository.namespace, summary=True, plain=True),
            })

        for func in record.functions:
            if func.doc is not None:
                func_desc = func.doc.content
            else:
                func_desc = MISSING_DESCRIPTION
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": record.name,
                "ident": func.identifier,
                "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
            })


def _gen_unions(config, index, repository, symbols):
    index_symbols = index["symbols"]

    for union in symbols:
        if config.is_hidden(union.name):
            log.debug(f"Skipping hidden type {union.name}")
            continue
        if union.doc is not None:
            desc = union.doc.content
        else:
            desc = MISSING_DESCRIPTION
        if union.deprecated:
            (deprecated, _) = union.deprecated_since
        else:
            deprecated = None
        index_symbols.append({
            "type": "union",
            "name": union.name,
            "ctype": union.base_ctype,
            "summary": utils.preprocess_docs(desc, repository.namespace, summary=True, plain=True),
            "deprecated": deprecated,
        })

        for ctor in union.constructors:
            if ctor.doc is not None:
                ctor_desc = ctor.doc.content
            else:
                ctor_desc = MISSING_DESCRIPTION
            if ctor.deprecated:
                (ctor_deprecated, _) = ctor.deprecated_since
            else:
                ctor_deprecated = None
            index_symbols.append({
                "type": "ctor",
                "name": ctor.name,
                "type_name": union.name,
                "ident": ctor.identifier,
                "summary": utils.preprocess_docs(ctor_desc, repository.namespace, summary=True, plain=True),
                "deprecated": ctor_deprecated,
            })

        for method in union.methods:
            if method.doc is not None:
                method_desc = method.doc.content
            else:
                method_desc = MISSING_DESCRIPTION
            if method.deprecated:
                (method_deprecated, _) = method.deprecated_since
            else:
                method_deprecated = None
            index_symbols.append({
                "type": "method",
                "name": method.name,
                "type_name": union.name,
                "ident": method.identifier,
                "summary": utils.preprocess_docs(method_desc, repository.namespace, summary=True, plain=True),
                "deprecated": method_deprecated,
            })

        for func in union.functions:
            if func.doc is not None:
                func_desc = func.doc.content
            else:
                func_desc = MISSING_DESCRIPTION
            if func.deprecated:
                (func_deprecated, _) = func.deprecated_since
            else:
                func_deprecated = None
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": union.name,
                "ident": func.identifier,
                "summary": utils.preprocess_docs(func_desc, repository.namespace, summary=True, plain=True),
                "deprecated": func_deprecated,
            })


def _gen_content_files(config, index, repository, content_dirs):
    index_symbols = index["symbols"]

    for file_name in config.content_files:
        src_file = utils.find_extra_content_file(content_dirs, file_name)

        src_data = ""
        with open(src_file, encoding='utf-8') as infile:
            source = []
            header = True
            title = None
            for line in infile:
                if header:
                    if line.startswith("Title: "):
                        title = line.replace("Title: ", "").strip()
                    if line == "\n":
                        header = False

                if not header:
                    source.append(line)
            src_data = "".join(source)

        if title is None:
            title = f"Untitled document '{file_name}'"

        index_symbols.append({
            "type": "content",
            "name": title,
            "href": file_name.replace(".md", ".html"),
            "summary": utils.preprocess_docs(src_data, repository.namespace, summary=True, plain=True),
        })


def gen_indices(config, repository, content_dirs, output_dir):
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

    index = {
        "meta": {
            "ns": namespace.name,
            "version": namespace.version,
            "generator": "gi-docgen",
            "generator-version": core.version,
        },
        "symbols": [],
        "terms": {},
    }

    # Each section is isolated, so we run it into a thread pool
    for section in all_indices:
        generator = all_indices.get(section, None)
        if generator is None:
            log.error(f"No generator for section {section}")
            continue

        s = symbols.get(section, None)
        if s is None:
            log.debug(f"No symbols for section {section}")
            continue

        log.debug(f"Generating symbols for section {section}")
        generator(config, index, repository, s)

    _gen_content_files(config, index, repository, content_dirs)

    # Ensure iteration order is reproducible by sorting symbols by type/name,
    # and terms by key. This has no overhead since values are not copied.
    index["symbols"].sort(key=lambda s: (s["type"], s["name"]))
    index["terms"] = {}

    data = json.dumps(index, separators=(',', ':'))
    index_file = os.path.join(output_dir, "index.json")
    log.info(f"Creating index file for {namespace.name}-{namespace.version}: {index_file}")
    with open(index_file, "w", encoding="utf-8") as out:
        out.write(data)


def add_args(parser):
    parser.add_argument("--add-include-path", action="append", dest="include_paths", default=[],
                        help="include paths for other GIR files")
    parser.add_argument("-C", "--config", metavar="FILE", help="the configuration file")
    parser.add_argument("--content-dir", action="append", dest="content_dirs", default=[],
                        help="the base directories with the extra content")
    parser.add_argument("--dry-run", action="store_true", help="parses the GIR file without generating files")
    parser.add_argument("--output-dir", default=None, help="the output directory for the index files")
    parser.add_argument("infile", metavar="GIRFILE", type=argparse.FileType('r', encoding='UTF-8'),
                        default=sys.stdin, help="the GIR file to parse")


def run(options):
    log.info(f"Loading config file: {options.config}")

    conf = config.GIDocConfig(options.config)

    output_dir = options.output_dir or os.getcwd()
    log.info(f"Output directory: {output_dir}")

    content_dirs = options.content_dirs
    if content_dirs == []:
        content_dirs = [os.getcwd()]

    paths = []
    paths.extend(options.include_paths)
    paths.extend(utils.default_search_paths())
    log.debug(f"Search paths: {paths}")

    log.info("Parsing GIR file")
    parser = gir.GirParser(search_paths=paths)
    parser.parse(options.infile)

    if not options.dry_run:
        log.checkpoint()
        gen_indices(conf, parser.get_repository(), content_dirs, output_dir)

    return 0
