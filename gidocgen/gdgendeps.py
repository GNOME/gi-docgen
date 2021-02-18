# SPDX-FileCopyrightText: 2021 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import argparse
import os
import sys

from . import config, gir, log


HELP_MSG = "Generates the build dependencies"


def _gen_content_files(config, content_dir):
    content_files = []
    for file_name in config.content_files:
        content_files.append(os.path.join(content_dir, file_name))
    return content_files


def _gen_content_images(config, content_dir):
    content_images = []
    for image_file in config.content_images:
        content_images.append(os.path.join(content_dir, image_file))
    return content_images


def gen_dependencies(repository, config, options):
    outfile = options.outfile

    outfile.write(options.config)
    outfile.write("\n")

    for include in repository.includes:
        if include.girfile is not None:
            outfile.write(include.girfile)
            outfile.write("\n")

    outfile.write(repository.girfile)
    outfile.write("\n")

    content_dir = options.content_dir or os.getcwd()

    content_files = _gen_content_files(config, content_dir)
    for f in content_files:
        outfile.write(f)
        outfile.write("\n")

    content_images = _gen_content_images(config, content_dir)
    for f in content_images:
        outfile.write(f)
        outfile.write("\n")


def add_args(parser):
    parser.add_argument("--add-include-path", action="append", dest="include_paths", default=[],
                        help="include paths for other GIR files")
    parser.add_argument("-C", "--config", metavar="FILE", help="the configuration file")
    parser.add_argument("--content-dir", default=None, help="the base directory with the extra content")
    parser.add_argument("--dry-run", action="store_true", help="parses the GIR file without generating files")
    parser.add_argument("infile", metavar="GIRFILE", type=argparse.FileType('r', encoding='UTF-8'),
                        default=sys.stdin, help="the GIR file to parse")
    parser.add_argument("outfile", metavar="DEPFILE", type=argparse.FileType('w', encoding='UTF-8'),
                        default=sys.stdout, help="the dependencies file to generate")


def run(options):
    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS", "/usr/share:/usr/local/share").split(":")
    xdg_data_home = os.environ.get("XDG_DATA_HOME", os.path.expanduser("~/.local/share"))

    # If we're sending output to stdout, we disable logging
    if options.outfile.name == "<stdout>":
        log.set_quiet(True)

    paths = []
    paths.append(os.getcwd())
    paths.append(os.path.join(xdg_data_home, "gir-1.0"))
    paths.extend([os.path.join(x, "gir-1.0") for x in xdg_data_dirs])
    log.info(f"Search paths: {paths}")

    log.info(f"Loading config file: {options.config}")
    conf = config.GIDocConfig(options.config)

    log.info("Parsing GIR file")
    parser = gir.GirParser(search_paths=paths)
    parser.parse(options.infile)

    if not options.dry_run:
        gen_dependencies(parser.get_repository(), conf, options)

    return 0
