# SPDX-FileCopyrightText: 2021 GNOME Foundation
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import os
import sys

if sys.version_info < (3, 6, 0):
    raise SystemExit('ERROR: GI-DocGen requires Python 3.6.0')

# For the gidocgen import below. setuptools.build_meta doesn't add
# the script dir to sys.path when building a wheel.
sys.path.insert(0, os.path.dirname(os.path.realpath(__file__)))

from gidocgen.core import version

from setuptools.command.build_py import build_py as _build_py
from setuptools import setup


class BuildCommand(_build_py):

    def generate_pkgconfig_file(self):
        lines = []
        with open('gi-docgen.pc.in', 'r', encoding='utf-8') as f:
            for line in f.readlines():
                new_line = line.strip().replace('@VERSION@', version)
                lines.append(new_line)
        with open('gi-docgen.pc', 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines))

    def run(self):
        self.generate_pkgconfig_file()
        return super().run()


if __name__ == '__main__':
    setup(
        cmdclass={
            'build_py': BuildCommand,
        },
    )
