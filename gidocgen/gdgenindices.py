# SPDX-FileCopyrightText: 2020 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import argparse
import os
import sys

from . import log

from .gir import *


HELP_MSG = "Generates the symbol indices"


def _gen_aliases(output_file, output_format, ns_name, ns_version, symbols):
    with open(output_file, 'w') as out:
        n_aliases = len(symbols)

        if output_format == "json":
            out.write("[")
            if n_aliases != 0:
                out.write("\n")

        for (i, alias) in enumerate(symbols):
            alias_name = f"{ns_name}.{alias.name}"
            alias_type = alias.ctype
            target_type = alias.target.ctype
            alias_link = f"[alias.{alias.name}]"

            if output_format == "csv":
                out.write(f"{alias_name},{alias_type},{target_type},{alias_link}\n")
            elif output_format == "json":
                l = f'  {{ "name": "{alias_name}", "ctype": "{alias_type}", "target-ctype": "{target_type}", "link": "{alias_link}" }}'
                out.write(l)
                if i == n_aliases - 1:
                    out.write("\n")
                else:
                    out.write(",\n")

        if output_format == "json":
            out.write("]\n")


def _gen_classes(output_file, output_format, ns_name, ns_version, symbols):
    with open(output_file, 'w') as out:
        n_classes = len(symbols)

        if output_format == "json":
            out.write("[")
            if n_classes != 0:
                out.write("\n")

        for (i, cls) in enumerate(symbols):
            class_name = f"{ns_name}.{cls.name}"
            class_type = cls.ctype
            class_link = f"[class.{cls.name}]"

            if output_format == "csv":
                out.write(f"{class_name},{class_type},{class_link}\n")
            elif output_format == "json":
                l = f'  {{ "name": "{class_name}", "ctype": "{class_type}", "link": "{class_link}" }}'
                out.write(l)
                if i == n_classes - 1:
                    out.write("\n")
                else:
                    out.write(",\n")

        if output_format == "json":
            out.write("]\n")


def _gen_constants(output_file, output_format, ns_name, ns_version, symbols):
    with open(output_file, 'w') as out:
        n_constants = len(symbols)

        if output_format == "json":
            out.write("[")
            if n_constants != 0:
                out.write("\n")

        for (i, constant) in enumerate(symbols):
            constant_name = f"{ns_name}.{constant.name}"
            constant_type = constant.ctype
            constant_link = f"[const.{constant.name}]"

            if output_format == "csv":
                out.write(f"{constant_name},{constant_type},{constant_link}\n")
            elif output_format == "json":
                l = f'  {{ "name": "{constant_name}", "ctype": "{constant_type}", "link": "{constant_link}"  }}'
                out.write(l)
                if i == n_constants - 1:
                    out.write("\n")
                else:
                    out.write(",\n")

        if output_format == "json":
            out.write("]\n")


def _gen_enums(output_file, output_format, ns_name, ns_version, symbols):
    with open(output_file, 'w') as out:
        n_enums = len(symbols)

        if output_format == "json":
            out.write("[")
            if n_enums != 0:
                out.write("\n")

        for (i, enum) in enumerate(symbols):
            enum_name = f"{ns_name}.{enum.name}"
            enum_type = enum.ctype
            enum_link = f"[enum.{enum.name}]"

            if output_format == "csv":
                out.write(f"{enum_name},{enum_type},{enum_link}\n")
            elif output_format == "json":
                l = f'  {{ "name": "{enum_name}", "ctype": "{enum_type}", "link": "{enum_link}" }}'
                out.write(l)
                if i == n_enums - 1:
                    out.write("\n")
                else:
                    out.write(",\n")

        if output_format == "json":
            out.write("]\n")


def _gen_domains(output_file, output_format, ns_name, ns_version, symbols):
    with open(output_file, 'w') as out:
        n_enums = len(symbols)

        if output_format == "json":
            out.write("[")
            if n_enums != 0:
                out.write("\n")

        for (i, enum) in enumerate(symbols):
            domain_name = f"{ns_name}.{enum.name}"
            domain_type = enum.ctype
            domain_quark = enum.domain 
            domain_link = f"[error.{enum.name}]"

            if output_format == "csv":
                out.write(f"{domain_name},{domain_type},{domain_link},{domain_quark}\n")
            elif output_format == "json":
                l = f'  {{ "name": "{domain_name}", "ctype": "{domain_type}", "domain": "{domain_quark}", "link": "{domain_link}" }}'
                out.write(l)
                if i == n_enums - 1:
                    out.write("\n")
                else:
                    out.write(",\n")

        if output_format == "json":
            out.write("]\n")


def _gen_interfaces(output_file, output_format, ns_name, ns_version, symbols):
    with open(output_file, 'w') as out:
        n_interfaces = len(symbols)

        if output_format == "json":
            out.write("[")
            if n_interfaces != 0:
                out.write("\n")

        for (i, iface) in enumerate(symbols):
            iface_name = f"{ns_name}.{iface.name}"
            iface_type = iface.ctype
            iface_link = f"[iface.{iface.name}]"

            if output_format == "csv":
                out.write(f"{iface_name},{iface_type},{iface_link}\n")
            elif output_format == "json":
                l = f'  {{ "name": "{iface_name}", "ctype": "{iface_type}", "link": "{iface_link}" }}'
                out.write(l)
                if i == n_interfaces - 1:
                    out.write("\n")
                else:
                    out.write(",\n")

        if output_format == "json":
            out.write("]\n")


def _gen_records(output_file, output_format, ns_name, ns_version, symbols):
    with open(output_file, 'w') as out:
        n_records = len(symbols)

        if output_format == "json":
            out.write("[")
            if n_records != 0:
                out.write("\n")

        for (i, record) in enumerate(symbols):
            record_name = f"{ns_name}.{record.name}"
            record_type = record.ctype
            record_link = f"[struct.{record.name}]"

            if output_format == "csv":
                out.write(f"{record_name},{record_type},{record_link}\n")
            elif output_format == "json":
                l = f'  {{ "name": "{record_name}", "ctype": "{record_type}", "link": "{record_link}" }}'
                out.write(l)
                if i == n_records - 1:
                    out.write("\n")
                else:
                    out.write(",\n")

        if output_format == "json":
            out.write("]\n")


def _gen_unions(output_file, output_format, ns_name, ns_version, symbols):
    with open(output_file, 'w') as out:
        n_unions = len(symbols)

        if output_format == "json":
            out.write("[")
            if n_unions != 0:
                out.write("\n")

        for (i, union) in enumerate(symbols):
            union_name = f"{ns_name}.{union.name}"
            union_type = union.ctype
            union_link = f"[union.{union.name}]"

            if output_format == "csv":
                out.write(f"{union_name},{union_type},{union_link}\n")
            elif output_format == "json":
                l = f'  {{ "name": "{union_name}", "ctype": "{union_type}", "link": "{union_link}" }}'
                out.write(l)
                if i == n_unions - 1:
                    out.write("\n")
                else:
                    out.write(",\n")

        if output_format == "json":
            out.write("]\n")


def gen_indices(repository, options, output_dir):
    """
    Generates the indices of the symbols inside @repository.

    The default @output_format is JSON.

    If @output_dir is None, the current directory will be used.
    """
    namespace = repository.get_namespace()

    symbols = {
        "aliases": sorted(namespace.get_aliases(), key=lambda alias: alias.name.lower()),
        "bitfields": sorted(namespace.get_bitfields(), key=lambda bitfield: bitfield.name.lower()),
        "classes": sorted(namespace.get_classes(), key=lambda cls: cls.name.lower()),
        "constants": sorted(namespace.get_constants(), key=lambda const: const.name.lower()),
        "domains": sorted(namespace.get_error_domains(), key=lambda domain: domain.name.lower()),
        "enums": sorted(namespace.get_enumerations(), key=lambda enum: enum.name.lower()),
        "functions": sorted(namespace.get_functions(), key=lambda func: func.name.lower()),
        "interfaces": sorted(namespace.get_interfaces(), key=lambda interface: interface.name.lower()),
        "records": sorted(namespace.get_records(), key=lambda record: record.name.lower()),
        "unions": sorted(namespace.get_unions(), key=lambda union: union.name.lower()),
    }

    all_indices = {
        "aliases": _gen_aliases,
        "bitfields": _gen_enums,
        "classes": _gen_classes,
        "constants": _gen_constants,
        "domains": _gen_domains,
        "enums": _gen_enums,
        "interfaces": _gen_interfaces,
        "records": _gen_records,
        "unions": _gen_unions,
    }

    if options.sections == [] or options.sections == ["all"]:
        gen_indices = all_indices.keys()
    else:
        gen_indices = options.sections

    log.info(f"Generating references for: {gen_indices}")

    for section in gen_indices:
        generator = all_indices.get(section, None)
        if generator is None:
            log.warning(f"No generator for section {section}")
            continue

        s = symbols.get(section, [])
        if s is None:
            log.warning(f"No symbols for section {section}")
            continue

        output_file = os.path.join(output_dir, f"{namespace.name}-{namespace.version}.{section}")
        generator(output_file, options.format, namespace.name, namespace.version, s)


def add_args(parser):
    parser.add_argument("--add-include-path", action="append", dest="include_paths", default=[], help="include paths for other GIR files")
    parser.add_argument("--dry-run", action="store_true", help="parses the GIR file without generating files")
    parser.add_argument("--format", default="json", choices=["csv", "json"], help="output format")
    parser.add_argument("--section", action="append", dest="sections", default=[], help="the sections to generate, or 'all'")
    parser.add_argument("--output-dir", default=None, help="the output directory for the index files")
    parser.add_argument("infile", metavar="GIRFILE", type=argparse.FileType('r', encoding='UTF-8'), default=sys.stdin, help="the GIR file to parse")


def run(options):
    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/share:/usr/local/share").split(":")
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

    paths = []
    paths.append(os.getcwd())
    paths.append(os.path.join(xdg_data_home, "gir-1.0"))
    paths.extend([ os.path.join(x, "gir-1.0") for x in xdg_data_dirs ])

    log.info(f"Search paths: {paths}")

    output_dir = options.output_dir or os.getcwd()

    parser = GirParser(search_paths=paths)
    parser.parse(options.infile)

    if not options.dry_run:
        gen_indices(parser.get_repository(), options, output_dir)

    return 0
