# SPDX-FileCopyrightText: 2021 Emmanuele Bassi
#
# SPDX-License-Identifier: GPL-3.0-or-later OR Apache-2.0

import xml.etree.ElementTree as ET
import os
import unittest

from gidocgen import gir, mdext, utils


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
        paths.extend([os.path.join(os.getcwd(), "tests/data/gir")])
        paths.extend(utils.default_search_paths())

        parser = gir.GirParser(search_paths=paths, error=False)
        parser.parse(os.path.join(os.getcwd(), "tests/data/gir", "GObject-2.0.gir"))

        cls._repository = parser.get_repository()

    @classmethod
    def tearDownClass(cls):
        cls._repository = None

    def test_link_re(self):
        """
        Test the link regular expression.
        """
        text = "Some text [type@GObject.Value] other text"
        res = utils.LINK_RE.search(text)
        self.assertIsNotNone(res)
        self.assertEqual(res.group('fragment'), 'type')
        self.assertEqual(res.group('endpoint'), 'GObject.Value')
        self.assertIsNone(res.group('anchor'))
        self.assertIsNone(res.group('text'))

        text = "Some text [with some text][type@GObject.Binding] other text"
        res = utils.LINK_RE.search(text)
        self.assertIsNotNone(res)
        self.assertEqual(res.group('fragment'), 'type')
        self.assertEqual(res.group('endpoint'), 'GObject.Binding')
        self.assertIsNone(res.group('anchor'))
        self.assertEqual(res.group('text'), '[with some text]')

        text = "Some text [struct@GLib.Variant#serialized-data-memory] other text"
        res = utils.LINK_RE.search(text)
        self.assertIsNotNone(res)
        self.assertEqual(res.group('fragment'), 'struct')
        self.assertEqual(res.group('endpoint'), 'GLib.Variant')
        self.assertEqual(res.group('anchor'), '#serialized-data-memory')
        self.assertIsNone(res.group('text'))

    def test_link_generator(self):
        """
        Test LinkGenerator
        """
        text = "Some text [with some, amazing, text][type@GObject.Binding#text] other text"
        res = utils.LINK_RE.search(text)
        self.assertIsNotNone(res)

        fragment = res.group('fragment')
        endpoint = res.group('endpoint')
        anchor = res.group('anchor')
        alt_text = res.group('text')

        link = utils.LinkGenerator(line=text, start=res.start(), end=res.end(),
                                   namespace=self._repository.namespace,
                                   fragment=fragment, endpoint=endpoint, anchor=anchor,
                                   text=alt_text)
        self.assertIsNotNone(link)

        root = ET.fromstring(str(link))
        self.assertEqual(root.tag, 'a')
        self.assertIn('href', root.attrib)
        self.assertEqual(root.attrib['href'], 'class.Binding.html#text')
        self.assertEqual(root.text, 'with some, amazing, text')

    def test_link_error(self):
        """
        Check that the LinkGenerator errors out when we expect it to.
        """
        checks = [
            "An [invalid fragment][enum@GObject.BindingFlags]",
            "An [unknown namespace][class@InvalidNamespace.Object]",
            "An [unknown fragment][foo@GObject.Object]",
            "An [unknown type][type@GObject.Unknown]",
            "An [unknown identifier][id@unknown_symbol]",
            "An [unknown component][type@GObject.Object.Foo]",
        ]

        for idx, c in enumerate(checks):
            with self.subTest(msg=f"Link '{c}' should fail", idx=idx):
                with self.assertRaises(utils.LinkParseError):
                    res = utils.LINK_RE.search(c)
                    self.assertIsNotNone(res)
                    utils.LinkGenerator(line=c, start=res.start(), end=res.end(),
                                        namespace=self._repository.namespace,
                                        fragment=res.group('fragment'),
                                        endpoint=res.group('endpoint'),
                                        text=res.group('text'),
                                        do_raise=True)

    def test_link_enum(self):
        """
        Check that the enum types link to the corresponding item.
        """
        text = "A value of [flags@GObject.BindingFlags]"
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
        self.assertEqual(root.tag, 'a')
        self.assertIn('href', root.attrib)
        self.assertEqual(root.attrib['href'], 'flags.BindingFlags.html')

        text = "A value of [flags@GObject.BindingFlags.SYNC_CREATE]"
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
        self.assertEqual(root.tag, 'a')
        self.assertIn('href', root.attrib)
        self.assertEqual(root.attrib['href'], 'flags.BindingFlags.html#sync-create')

        text = "A value of [flags@GObject.BindingFlags.INVALID_NAME]"
        res = utils.LINK_RE.search(text)
        self.assertIsNotNone(res)

        fragment = res.group('fragment')
        endpoint = res.group('endpoint')
        alt_text = res.group('text')

        with self.assertRaises(utils.LinkParseError):
            utils.LinkGenerator(line=text, start=res.start(), end=res.end(),
                                namespace=self._repository.namespace,
                                fragment=fragment, endpoint=endpoint, text=alt_text,
                                do_raise=True)


class TestGtkDocExtension(unittest.TestCase):

    def test_gtkdoc_sigils(self):

        self.assertTrue(mdext.process_gtkdoc_sigils("will emit the #GCancellable::cancelled signal."),
                        "will emit the `GCancellable::cancelled` signal.")
        self.assertTrue(mdext.process_gtkdoc_sigils("If @cancellable is %NULL,"),
                        "If `cancellable` is `NULL`,")
        self.assertTrue(mdext.process_gtkdoc_sigils("A #GCancellable object."),
                        "A `GCancellable` object.")
        self.assertTrue(mdext.process_gtkdoc_sigils("are two helper functions: g_cancellable_connect() and"),
                        "are two helper functions: `g_cancellable_connect()` and")
        self.assertTrue(mdext.process_gtkdoc_sigils("#GDBusProxy:g-connection must be %NULL and will be set to the"),
                        "`GDBusProxy:g-connection` must be `NULL` and will be set to the")
        self.assertTrue(mdext.process_gtkdoc_sigils("#GDBusProxy:g-name-owner. Connect to the #GObject::notify signal"),
                        "`GDBusProxy:g-name-owner`. Connect to the `GObject::notify` signal")
