.. SPDX-FileCopyrightText: 2021 GNOME Foundation
..
.. SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

Welcome to gi-docgen's documentation!
=====================================

.. title:: Overview

.. toctree::
   :hidden:
   :maxdepth: 1
   :caption: Contents:

   tutorial
   project-configuration
   linking
   attributes
   templates
   content
   tools/index


GI-DocGen is a document generator for GObject-based libraries. GObject is
the base type system of the GNOME project. GI-Docgen reuses the
introspection data generated by GObject-based libraries to generate the API
reference of these libraries, as well as other ancillary documentation.

Installation
------------

Running GI-DocGen uninstalled
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can run GI-DocGen from its repository, by calling:

::

    ./gi-docgen.py

GI-DocGen will automatically detect this case.

Installing GI-DocGen via pip
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

To install GI-DocGen, you will need to have the following pieces of software
available on your computer:

- Python 3.6, or later
- pip

Run the following command:

::

    pip3 install --user gi-docgen

After running the command above, make sure to have the ``$HOME/.local/bin``
directory listed in your ``$PATH`` environment variable.

To update GI-DocGen, run the following command:

::

    pip3 install --user --upgrade gi-docgen

Usage
-----

First, read :doc:`tutorial`.

Additional documentation on how to control the generation of your project's
API reference is available in the :doc:`project-configuration` page.

Disclaimer
----------

GI-DocGen is **not** a general purpose documentation tool for C libraries.

While GI-DocGen can be used to generate API references for most GObject/C
libraries that expose introspection data, its main goal is to generate the
reference for GTK and its immediate dependencies. Any and all attempts at
making this tool more generic, or to cover more use cases, will be weighted
heavily against its primary goal.

If you need a general purpose documentation tool, I strongly recommend:

- `HotDoc <https://hotdoc.github.io/>`__
- `Doxygen <https://www.doxygen.nl/index.html>`__
- `GTK-Doc <https://gitlab.gnome.org/GNOME/gtk-doc/>`__

Copyright and Licensing terms
-----------------------------

Copyright 2021  GNOME Foundation

GI-DocGen is released under the terms of the Apache License, version 2.0, or
under the terms of the GNU General Publice License, either version 3.0 or,
at your option, any later version.
