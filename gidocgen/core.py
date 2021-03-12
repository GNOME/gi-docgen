# SPDX-FileCopyrightText: 2020 GNOME Foundation <https://gnome.org>
# SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:
    import importlib_metadata
try:
    version = importlib_metadata.version("gi-docgen")
except importlib_metadata.PackageNotFoundError:
    # when the package isn't installed.
    version = "0.0.0"

