# SPDX-FileCopyrightText: 2021 Emmanuele Bassi
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

import os
import unittest

from gidocgen import gir, utils


class TestGir(unittest.TestCase):
    """Test suite for the GIR parser and AST"""

    def test_gir_regress(self):
        """Test the GIR parser by running it on various GIR files"""

        paths = []
        paths.extend([os.path.join(os.getcwd(), "test/gir")])
        paths.extend(utils.default_search_paths())

        parser = gir.GirParser(search_paths=paths, error=False)
        parser.parse(os.path.join(os.getcwd(), "test/gir", "Regress-1.0.gir"))

        repo = parser.get_repository()
        self.assertIsNotNone(repo, "Parser error in Regress-1.0")
        self.assertIsNotNone(repo.namespace, "Invalid namespace for Regress-1.0")
        self.assertEqual(f"{repo.namespace.name}-{repo.namespace.version}", "Regress-1.0")
