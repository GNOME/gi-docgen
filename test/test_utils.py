# SPDX-FileCopyrightText: 2021 Emmanuele Bassi
#
# SPDX-License-Identifier: GPL-3.0-or-later OR Apache-2.0

import xml.etree.ElementTree as ET
import os
import unittest

from gidocgen import gir, utils


class TestProcessLanguage(unittest.TestCase):

    def test_process_language(self):
        self.assertEqual(utils.process_language(None), "plain")
        self.assertEqual(utils.process_language('<!-- language="C" -->'), "c")
        self.assertEqual(utils.process_language('  <!-- language="xml" -->'), "xml")
        self.assertEqual(utils.process_language('<!--     language="plain"      -->'), "plain")


class TestLinkGenerator(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        paths = []
        paths.extend([os.path.join(os.getcwd(), "test/gir")])
        paths.extend(utils.default_search_paths())

        parser = gir.GirParser(search_paths=paths, error=False)
        parser.parse(os.path.join(os.getcwd(), "test/gir", "GObject-2.0.gir"))

        cls._repository = parser.get_repository()

    @classmethod
    def tearDownClass(cls):
        cls._repository = None

    def test_link_re(self):
        text = "Some text [type@GObject.Value] other text"
        res = utils.LINK_RE.search(text)
        self.assertIsNotNone(res)

        fragment = res.group('fragment')
        self.assertTrue(fragment == 'type')

        endpoint = res.group('endpoint')
        self.assertTrue(endpoint == 'GObject.Value')

        alt_text = res.group('text')
        self.assertIsNone(alt_text)

        text = "Some text [with some text][type@GObject.Binding] other text"
        res = utils.LINK_RE.search(text)
        self.assertIsNotNone(res)

        alt_text = res.group('text')
        self.assertTrue(alt_text == '[with some text]')

    def test_link_generator(self):
        text = "Some text [with some, amazing, text][type@GObject.Binding] other text"
        res = utils.LINK_RE.search(text)
        self.assertIsNotNone(res)

        fragment = res.group('fragment')
        endpoint = res.group('endpoint')
        alt_text = res.group('text')

        link = utils.LinkGenerator(line=text, start=res.start(), end=res.end(),
                                   namespace=self._repository.namespace,
                                   fragment=fragment, endpoint=endpoint, text=alt_text)
        self.assertIsNotNone(link)

        root = ET.fromstring(str(link))
        self.assertTrue(root.tag == 'a')
        self.assertTrue('href' in root.attrib)
        self.assertTrue(root.attrib['href'] == 'class.Binding.html')
        self.assertTrue(root.text == 'with some, amazing, text')
