# SPDX-FileCopyrightText: 2023 Purism SPC
#
# SPDX-License-Identifier: GPL-3.0-or-later OR Apache-2.0

import unittest

from gidocgen import gir, config


class TestConfig(unittest.TestCase):

    def test_is_unstable(self):
        conf = config.GIDocConfig("tests/data/config/gtk4.toml")
        self.assertFalse(conf.is_unstable("4.0"))
        self.assertFalse(conf.is_unstable("4.9"))
        self.assertTrue(conf.is_unstable("4.10"))
        self.assertTrue(conf.is_unstable("4.90"))
        self.assertTrue(conf.is_unstable("5.0"))

        conf = config.GIDocConfig("tests/data/config/gtk4-stable.toml")
        self.assertFalse(conf.is_unstable("4.0"))
        self.assertFalse(conf.is_unstable("4.9"))
        self.assertFalse(conf.is_unstable("4.10"))
        self.assertTrue(conf.is_unstable("4.90"))
        self.assertTrue(conf.is_unstable("5.0"))

        conf = config.GIDocConfig("tests/data/config/gtk5-beta.toml")
        self.assertFalse(conf.is_unstable("4.0"))
        self.assertFalse(conf.is_unstable("4.9"))
        self.assertFalse(conf.is_unstable("4.10"))
        self.assertFalse(conf.is_unstable("4.90"))
        self.assertTrue(conf.is_unstable("5.0"))

        conf = config.GIDocConfig("tests/data/config/libadwaita.toml")
        self.assertFalse(conf.is_unstable("0.3"))
        self.assertFalse(conf.is_unstable("1.2"))
        self.assertTrue(conf.is_unstable("1.3"))
        self.assertTrue(conf.is_unstable("2.0"))
