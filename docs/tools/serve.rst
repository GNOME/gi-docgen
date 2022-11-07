.. SPDX-FileCopyrightText: 2022  Emmanuele Bassi
..
.. SPDX-License-Identifier: Apache-2.0 OR GPL-3.0-or-later

===============
gi-docgen serve
===============

Serves the API reference on a local web server
----------------------------------------------

SYNOPSIS
========

**gi-docgen serve** [OPTIONS...] [GIRFILE]

DESCRIPTION
===========

The **serve** command generates the API reference from a GIR file and then
serves the contents of the output directory via a local HTTP server.

OPTIONS
=======

See: the :doc:`generate` command.

``-b, --bind ADDRESS``
  The ``ADDRESS`` used by the HTTP server. The default is: 127.0.0.1.

``-p, --port PORT``
  The ``PORT`` used by the HTTP server. The default is: 8080.
