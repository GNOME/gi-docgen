# SPDX-FileCopyrightText: 2021 Emmanuele Bassi
#
# SPDX-License-Identifier: GPL-3.0-or-later OR Apache-2.0

import unittest

from gidocgen import utils


class TestProcessLanguage(unittest.TestCase):

    def test_process_language(self):
        self.assertEqual(utils.process_language(None), "plain")
        self.assertEqual(utils.process_language('<!-- language="C" -->'), "c")
        self.assertEqual(utils.process_language('  <!-- language="xml" -->'), "xml")
        self.assertEqual(utils.process_language('<!--     language="plain"      -->'), "plain")
