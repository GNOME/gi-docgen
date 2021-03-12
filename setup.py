# SPDX-FileCopyrightText: 2020 GNOME Foundation <https://gnome.org>
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import sys

if sys.version_info < (3, 6, 0):
    raise SystemExit('ERROR: GI-DocGen requires Python 3.6.0')

from gidocgen.core import version
from setuptools import setup


def readme_md():
    '''Return the contents of the README.md file'''
    return open('README.md').read()


entries = {
    'console_scripts': ['gi-docgen=gidocgen.gidocmain:main'],
}

packages = [
    'gidocgen',
    'gidocgen.gir',
]

package_data = {
    'gidocgen': [
        "templates/basic/basic.toml",
        "templates/basic/*.css",
        "templates/basic/*.html",
        "templates/basic/*.js",
        "templates/basic/*.txt",
        "templates/basic/*.woff2",
        "templates/basic/*.woff",
    ],
}

data_files = []

if __name__ == '__main__':
    setup(
        name='gi-docgen',
        version=version,
        license='GPL-3.0-or-later AND Apache-2.0 AND CC0-1.0',
        long_description=readme_md(),
        long_description_content_type='text/markdown',
        include_package_data=True,
        packages=packages,
        package_data=package_data,
        data_files=data_files,
        entry_points=entries,
    )
