# SPDX-FileCopyrightText: 2020 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import argparse
import json
import os
import sys

from . import config, core, gir, log, porter, utils


HELP_MSG = "Generates the symbol indices for search"


def add_index_terms(index, terms, docid):
    for term in terms:
        docs = index.setdefault(term, [])
        if docid not in docs:
            docs.append(docid)


def _gen_aliases(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for alias in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "alias", "name": alias.name, "ctype": alias.base_ctype})
        add_index_terms(index_terms, utils.index_identifier(alias.name, stemmer), idx)
        if alias.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(alias.doc.content, stemmer), idx)


def _gen_bitfields(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for bitfield in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "bitfield", "name": bitfield.name, "ctype": bitfield.base_ctype})
        add_index_terms(index_terms, utils.index_identifier(bitfield.name, stemmer), idx)
        if bitfield.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(bitfield.doc.content, stemmer), idx)

        for member in bitfield.members:
            if member.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(member.doc.content, stemmer), idx)

        for func in bitfield.functions:
            func_idx = len(index_symbols)
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": bitfield.name,
                "ident": func.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), func_idx)
            if func.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), func_idx)


def _gen_callbacks(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for callback in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "callback", "name": callback.name})
        add_index_terms(index_terms, utils.index_identifier(callback.name, stemmer), idx)
        if callback.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(callback.doc.content, stemmer), idx)


def _gen_classes(config, stemmer, index, repository, symbols):
    namespace = repository.namespace

    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for cls in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "class", "name": cls.name, "ctype": cls.base_ctype})
        add_index_terms(index_terms, utils.index_identifier(cls.name, stemmer), idx)
        if cls.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(cls.doc.content, stemmer), idx)

        for ctor in cls.constructors:
            ctor_idx = len(index_symbols)
            index_symbols.append({"type": "ctor", "name": ctor.name, "type_name": cls.name, "ident": ctor.identifier})
            add_index_terms(index_terms, utils.index_symbol(ctor.name, stemmer), ctor_idx)
            if ctor.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(ctor.doc.content, stemmer), ctor_idx)

        for method in cls.methods:
            method_idx = len(index_symbols)
            index_symbols.append({"type": "method", "name": method.name, "type_name": cls.name, "ident": method.identifier})
            add_index_terms(index_terms, utils.index_symbol(method.name, stemmer), method_idx)
            if method.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(method.doc.content, stemmer), method_idx)

        for func in cls.functions:
            func_idx = len(index_symbols)
            index_symbols.append({"type": "type_func", "name": func.name, "type_name": cls.name, "ident": func.identifier})
            add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), func_idx)
            if func.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), func_idx)

        for prop_name, prop in cls.properties.items():
            prop_idx = len(index_symbols)
            index_symbols.append({"type": "property", "name": prop.name, "type_name": cls.name})
            add_index_terms(index_terms, utils.index_symbol(prop.name, stemmer), prop_idx)
            if prop.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(prop.doc.content, stemmer), prop_idx)

        for signal_name, signal in cls.signals.items():
            signal_idx = len(index_symbols)
            index_symbols.append({"type": "signal", "name": signal.name, "type_name": cls.name})
            add_index_terms(index_terms, utils.index_symbol(signal.name, stemmer), signal_idx)
            if signal.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(signal.doc.content, stemmer), signal_idx)

        for vfunc in cls.virtual_methods:
            vfunc_idx = len(index_symbols)
            index_symbols.append({"type": "vfunc", "name": vfunc.name, "type_name": cls.name})
            add_index_terms(index_terms, utils.index_symbol(vfunc.name, stemmer), vfunc_idx)
            if vfunc.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(vfunc.doc.content, stemmer), vfunc_idx)

        if cls.type_struct is not None:
            cls_struct = namespace.find_record(cls.type_struct)
            for cls_method in cls_struct.methods:
                cls_method_idx = len(index_symbols)
                index_symbols.append({
                    "type": "class_method",
                    "name": cls_method.name,
                    "type_name": cls_struct.name,
                    "struct_for": cls_struct.struct_for,
                    "ident": cls_method.identifier,
                })
                add_index_terms(index_terms, utils.index_symbol(cls_method.name, stemmer), cls_method_idx)
                if cls_method.doc is not None:
                    add_index_terms(index_terms, utils.preprocess_index(cls_method.doc.content, stemmer), cls_method_idx)


def _gen_constants(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for const in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "constant", "name": const.name, "ident": const.ctype})
        add_index_terms(index_terms, utils.index_symbol(const.name, stemmer), idx)
        if const.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(const.doc.content, stemmer), idx)


def _gen_domains(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for domain in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "domain", "name": domain.name, "ctype": domain.base_ctype})
        add_index_terms(index_terms, utils.index_identifier(domain.name, stemmer), idx)
        if domain.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(domain.doc.content, stemmer), idx)

        for member in domain.members:
            if member.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(member.doc.content, stemmer), idx)

        for func in domain.functions:
            func_idx = len(index_symbols)
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": domain.name,
                "ident": func.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), func_idx)
            if func.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), func_idx)


def _gen_enums(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for enum in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "enum", "name": enum.name, "ctype": enum.base_ctype})
        add_index_terms(index_terms, utils.index_identifier(enum.name, stemmer), idx)
        if enum.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(enum.doc.content, stemmer), idx)

        for member in enum.members:
            if member.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(member.doc.content, stemmer), idx)

        for func in enum.functions:
            func_idx = len(index_symbols)
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": enum.name,
                "ident": func.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), func_idx)
            if func.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), func_idx)


def _gen_functions(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for func in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "function", "name": func.name, "ident": func.identifier})
        add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), idx)
        if func.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), idx)


def _gen_function_macros(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for func in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "function_macro", "name": func.name, "ident": func.identifier})
        add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), idx)
        if func.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), idx)


def _gen_interfaces(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for iface in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "interface", "name": iface.name, "ctype": iface.base_ctype})
        add_index_terms(index_terms, utils.index_identifier(iface.name, stemmer), idx)
        if iface.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(iface.doc.content, stemmer), idx)

        for method in iface.methods:
            method_idx = len(index_symbols)
            index_symbols.append({
                "type": "method",
                "name": method.name,
                "type_name": iface.name,
                "ident": method.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(method.name, stemmer), method_idx)
            if method.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(method.doc.content, stemmer), method_idx)

        for func in iface.functions:
            func_idx = len(index_symbols)
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": iface.name,
                "ident": func.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), func_idx)
            if func.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), func_idx)

        for prop_name, prop in iface.properties.items():
            prop_idx = len(index_symbols)
            index_symbols.append({"type": "property", "name": prop.name, "type_name": iface.name})
            add_index_terms(index_terms, utils.index_symbol(prop.name, stemmer), prop_idx)
            if prop.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(prop.doc.content, stemmer), prop_idx)

        for signal_name, signal in iface.signals.items():
            signal_idx = len(index_symbols)
            index_symbols.append({"type": "signal", "name": signal.name, "type_name": iface.name})
            add_index_terms(index_terms, utils.index_symbol(signal.name, stemmer), signal_idx)
            if signal.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(signal.doc.content, stemmer), signal_idx)

        for vfunc in iface.virtual_methods:
            vfunc_idx = len(index_symbols)
            index_symbols.append({"type": "vfunc", "name": vfunc.name, "type_name": iface.name})
            add_index_terms(index_terms, utils.index_symbol(vfunc.name, stemmer), vfunc_idx)
            if vfunc.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(vfunc.doc.content, stemmer), vfunc_idx)


def _gen_records(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for record in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "record", "name": record.name, "ctype": record.base_ctype})
        add_index_terms(index_terms, utils.index_identifier(record.name, stemmer), idx)
        if record.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(record.doc.content, stemmer), idx)

        for ctor in record.constructors:
            ctor_idx = len(index_symbols)
            index_symbols.append({
                "type": "ctor",
                "name": ctor.name,
                "type_name": record.name,
                "ident": ctor.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(ctor.name, stemmer), ctor_idx)
            if ctor.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(ctor.doc.content, stemmer), ctor_idx)

        for method in record.methods:
            method_idx = len(index_symbols)
            index_symbols.append({
                "type": "method",
                "name": method.name,
                "type_name": record.name,
                "ident": method.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(method.name, stemmer), method_idx)
            if method.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(method.doc.content, stemmer), method_idx)

        for func in record.functions:
            func_idx = len(index_symbols)
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": record.name,
                "ident": func.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), func_idx)
            if func.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), func_idx)


def _gen_unions(config, stemmer, index, repository, symbols):
    index_symbols = index["symbols"]
    index_terms = index["terms"]

    for union in symbols:
        idx = len(index_symbols)
        index_symbols.append({"type": "union", "name": union.name, "ctype": union.base_ctype})
        add_index_terms(index_terms, utils.index_identifier(union.name, stemmer), idx)
        if union.doc is not None:
            add_index_terms(index_terms, utils.preprocess_index(union.doc.content, stemmer), idx)

        for ctor in union.constructors:
            ctor_idx = len(index_symbols)
            index_symbols.append({
                "type": "ctor",
                "name": ctor.name,
                "type_name": union.name,
                "ident": ctor.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(ctor.name, stemmer), ctor_idx)
            if ctor.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(ctor.doc.content, stemmer), ctor_idx)

        for method in union.methods:
            method_idx = len(index_symbols)
            index_symbols.append({
                "type": "method",
                "name": method.name,
                "type_name": union.name,
                "ident": method.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(method.name, stemmer), method_idx)
            if method.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(method.doc.content, stemmer), method_idx)

        for func in union.functions:
            func_idx = len(index_symbols)
            index_symbols.append({
                "type": "type_func",
                "name": func.name,
                "type_name": union.name,
                "ident": func.identifier,
            })
            add_index_terms(index_terms, utils.index_symbol(func.name, stemmer), func_idx)
            if func.doc is not None:
                add_index_terms(index_terms, utils.preprocess_index(func.doc.content, stemmer), func_idx)


def gen_indices(config, repository, content_dir, output_dir):
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

    stemmer = porter.PorterStemmer()

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
        generator(config, stemmer, index, repository, s)

    data = json.dumps(index, separators=(',', ':'))
    index_file = os.path.join(output_dir, "index.json")
    log.info(f"Creating index file for {namespace.name}-{namespace.version}: {index_file}")
    with open(index_file, "w") as out:
        out.write(data)


def add_args(parser):
    parser.add_argument("--add-include-path", action="append", dest="include_paths", default=[],
                        help="include paths for other GIR files")
    parser.add_argument("-C", "--config", metavar="FILE", help="the configuration file")
    parser.add_argument("--content-dir", default=None, help="the base directory with the extra content")
    parser.add_argument("--dry-run", action="store_true", help="parses the GIR file without generating files")
    parser.add_argument("--output-dir", default=None, help="the output directory for the index files")
    parser.add_argument("infile", metavar="GIRFILE", type=argparse.FileType('r', encoding='UTF-8'),
                        default=sys.stdin, help="the GIR file to parse")


def run(options):
    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/share:/usr/local/share").split(":")
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

    paths = []
    paths.extend(options.include_paths)
    paths.append(os.getcwd())
    paths.append(os.path.join(xdg_data_home, "gir-1.0"))
    paths.extend([os.path.join(x, "gir-1.0") for x in xdg_data_dirs])

    log.info(f"Loading config file: {options.config}")

    conf = config.GIDocConfig(options.config)

    output_dir = options.output_dir or os.getcwd()
    content_dir = options.content_dir or os.getcwd()

    log.debug(f"Search paths: {paths}")
    log.info(f"Output directory: {output_dir}")

    log.info("Parsing GIR file")
    parser = gir.GirParser(search_paths=paths)
    parser.parse(options.infile)

    if not options.dry_run:
        log.checkpoint()
        gen_indices(conf, parser.get_repository(), content_dir, output_dir)

    return 0
